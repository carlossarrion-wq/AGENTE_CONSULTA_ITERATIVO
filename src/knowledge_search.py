#!/usr/bin/env python3
"""
Knowledge Base Search Tool
Herramienta simplificada para buscar fragmentos en la base de conocimiento OpenSearch
"""

import sys
import os
import json
import yaml
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime

# Configurar logging básico
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Intentar importar dependencias del sistema RAG
try:
    # Detectar si estamos en EC2 o local
    current_dir = os.getcwd()
    
    # Si estamos en el directorio RAG_SYSTEM_MULTI_v5, usar ruta relativa
    if 'RAG_SYSTEM_MULTI_v5' in current_dir:
        # Estamos en EC2 o en el directorio del sistema RAG
        rag_system_path = current_dir
        # Añadir el directorio actual al path
        if rag_system_path not in sys.path:
            sys.path.insert(0, rag_system_path)
        
        # Importar usando ruta absoluta desde el directorio actual
        sys.path.insert(0, os.path.join(rag_system_path, 'src'))
        from utils.connection_manager import ConnectionManager
    else:
        # Estamos en local, usar ruta absoluta
        rag_system_path = "/Users/csarrion/Cline/RAG_MULTI_APLICACION/RAG_SYSTEM_MULTI_v5"
        if rag_system_path not in sys.path:
            sys.path.append(rag_system_path)
        from src.utils.connection_manager import ConnectionManager
    
    DEPENDENCIES_AVAILABLE = True
    logger.info(f"Dependencias cargadas desde: {rag_system_path}")
    
except ImportError as e:
    logger.warning(f"No se pudieron importar las dependencias del sistema RAG: {e}")
    DEPENDENCIES_AVAILABLE = False


class KnowledgeSearchTool:
    """
    Herramienta simplificada para búsqueda en base de conocimiento OpenSearch
    """
    
    def __init__(self, config_path: str = None, application: str = "darwin"):
        """
        Inicializar la herramienta de búsqueda
        
        Args:
            config_path: Ruta al archivo de configuración (opcional)
            application: Aplicación a usar (darwin por defecto)
        """
        self.application = application
        
        # Usar configuración por defecto si no se especifica
        if config_path is None:
            # Detectar si estamos en EC2 o local
            current_dir = os.getcwd()
            if 'RAG_SYSTEM_MULTI_v5' in current_dir:
                # Estamos en EC2 o en el directorio del sistema RAG
                config_path = os.path.join(current_dir, "config", "multi_app_config.yaml")
            else:
                # Estamos en local
                config_path = "/Users/csarrion/Cline/RAG_MULTI_APLICACION/RAG_SYSTEM_MULTI_v5/config/multi_app_config.yaml"
        
        self.config_path = config_path
        
        if not DEPENDENCIES_AVAILABLE:
            raise ImportError("Las dependencias del sistema RAG no están disponibles")
        
        logger.info(f"Inicializando KnowledgeSearchTool para aplicación: {application}")
        
        # Cargar configuración
        self._load_config()
        
        # Inicializar conexiones
        self._initialize_connections()
        
        logger.info("✅ KnowledgeSearchTool inicializado correctamente")
    
    def _load_config(self):
        """Cargar configuración desde YAML"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            # Validar estructura
            if 'opensearch' not in self.config:
                raise KeyError("'opensearch' key not found in configuration")
            if 'applications' not in self.config:
                raise KeyError("'applications' key not found in configuration")
            if self.application not in self.config['applications']:
                raise KeyError(f"Application '{self.application}' not found in configuration")
            
            # Extraer configuraciones importantes
            self.index_name = self.config['applications'][self.application]['opensearch']['index_name']
            self.embedding_model = self.config['bedrock']['embedding_model']
            
            logger.info(f"Configuración cargada - Índice: {self.index_name}")
            
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            raise
    
    def _initialize_connections(self):
        """Inicializar conexiones a OpenSearch y Bedrock"""
        try:
            # Procesar endpoint de OpenSearch
            opensearch_endpoint = self.config['opensearch']['endpoint']
            if opensearch_endpoint.startswith('https://'):
                opensearch_endpoint = opensearch_endpoint.replace('https://', '')
            elif opensearch_endpoint.startswith('http://'):
                opensearch_endpoint = opensearch_endpoint.replace('http://', '')
            
            # Crear configuración compatible
            compatible_config = {
                'aws': self.config['aws'],
                'bedrock': self.config['bedrock'],
                'services': {
                    'opensearch': {
                        'endpoint': f"https://{opensearch_endpoint}",
                        'use_ssl': self.config['opensearch'].get('use_ssl', True),
                        'verify_certs': self.config['opensearch'].get('verify_certs', True),
                        'connection_class': self.config['opensearch'].get('connection_class', 'RequestsHttpConnection'),
                        'vpc_access': self.config['opensearch'].get('vpc_access', True),
                        'timeout': self.config['opensearch'].get('timeout', 30)
                    },
                    's3': {
                        'bucket': self.config['applications'][self.application]['s3']['bucket']
                    }
                }
            }
            
            # Crear conexiones
            self.connection_manager = ConnectionManager(config_dict=compatible_config)
            self.opensearch_client = self.connection_manager.get_opensearch_client()
            self.bedrock_client = self.connection_manager.get_bedrock_client()
            
            logger.info("✅ Conexiones inicializadas correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando conexiones: {e}")
            raise
    
    def _get_embedding(self, text: str) -> List[float]:
        """Generar embedding para texto usando Bedrock"""
        try:
            body = json.dumps({
                'inputText': text,
                'embeddingConfig': {'outputEmbeddingLength': 1024}
            })

            response = self.bedrock_client.invoke_model(
                modelId=self.embedding_model,
                body=body,
                contentType='application/json',
                accept='application/json'
            )

            response_body = json.loads(response['body'].read())
            return response_body['embedding']

        except Exception as e:
            logger.error(f"Error generando embedding: {e}")
            raise
    
    def search(self, query: str, top_k: int = 10, min_score: float = 0.0) -> Dict[str, Any]:
        """
        Buscar fragmentos en la base de conocimiento
        
        Args:
            query: Texto a buscar (obligatorio)
            top_k: Número máximo de resultados (opcional, por defecto 10)
            min_score: Puntuación mínima (opcional, por defecto 0.0)
            
        Returns:
            JSON con los fragmentos encontrados
        """
        logger.info(f"🔍 Buscando: '{query}' (top_k={top_k}, min_score={min_score})")
        
        start_time = datetime.now()
        
        try:
            # Generar embedding para la query
            query_embedding = self._get_embedding(query)
            
            # Ejecutar búsqueda híbrida (vectorial + textual)
            vector_results = self._search_vector(query_embedding, top_k)
            text_results = self._search_text(query, top_k)
            
            # Combinar y procesar resultados
            combined_results = self._combine_results(vector_results, text_results, min_score)
            
            # Limitar a top_k
            final_results = combined_results[:top_k]
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Formatear salida
            output = {
                "query": query,
                "parameters": {
                    "top_k": top_k,
                    "min_score": min_score
                },
                "timestamp": start_time.isoformat(),
                "duration_seconds": round(duration, 3),
                "total_found": len(final_results),
                "fragments": []
            }
            
            for result in final_results:
                fragment = {
                    "file_name": result.get('file_name', 'unknown'),
                    "relevance": round(result.get('score', 0.0), 3),
                    "summary": result.get('summary', result.get('content', '')[:200] + '...' if len(result.get('content', '')) > 200 else result.get('content', ''))
                }
                output["fragments"].append(fragment)
            
            logger.info(f"✅ Búsqueda completada: {len(final_results)} fragmentos en {duration:.3f}s")
            
            return output
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda: {e}")
            raise
    
    def _search_vector(self, query_embedding: List[float], size: int) -> List[Dict]:
        """Ejecutar búsqueda vectorial"""
        search_body = {
            "size": size,
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {"query_vector": query_embedding}
                    }
                }
            },
            "_source": ["content", "title", "file_name", "chunk_id", "metadata"]
        }
        
        response = self.opensearch_client.search(
            index=self.index_name,
            body=search_body
        )
        
        results = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            metadata = source.get('metadata', {})
            
            result = {
                'doc_id': hit['_id'],
                'score': float(hit['_score']),
                'file_name': source.get('file_name', 'unknown'),
                'content': source.get('content', ''),
                'title': source.get('title', ''),
                'chunk_id': source.get('chunk_id', ''),
                'summary': metadata.get('summary', ''),
                'search_type': 'vector'
            }
            results.append(result)
        
        return results
    
    def _search_text(self, query: str, size: int) -> List[Dict]:
        """Ejecutar búsqueda textual"""
        search_body = {
            "size": size,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["content^2", "title", "file_name"],
                    "type": "best_fields"
                }
            },
            "_source": ["content", "title", "file_name", "chunk_id", "metadata"]
        }
        
        response = self.opensearch_client.search(
            index=self.index_name,
            body=search_body
        )
        
        results = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            metadata = source.get('metadata', {})
            
            result = {
                'doc_id': hit['_id'],
                'score': float(hit['_score']),
                'file_name': source.get('file_name', 'unknown'),
                'content': source.get('content', ''),
                'title': source.get('title', ''),
                'chunk_id': source.get('chunk_id', ''),
                'summary': metadata.get('summary', ''),
                'search_type': 'text'
            }
            results.append(result)
        
        return results
    
    def _combine_results(self, vector_results: List[Dict], text_results: List[Dict], min_score: float) -> List[Dict]:
        """Combinar resultados de búsqueda vectorial y textual"""
        # Crear diccionario para evitar duplicados
        combined = {}
        
        # Añadir resultados vectoriales
        for result in vector_results:
            if result['score'] >= min_score:
                doc_id = result['doc_id']
                if doc_id not in combined or result['score'] > combined[doc_id]['score']:
                    combined[doc_id] = result
        
        # Añadir resultados textuales
        for result in text_results:
            if result['score'] >= min_score:
                doc_id = result['doc_id']
                if doc_id not in combined or result['score'] > combined[doc_id]['score']:
                    combined[doc_id] = result
        
        # Convertir a lista y ordenar por puntuación
        results_list = list(combined.values())
        results_list.sort(key=lambda x: x['score'], reverse=True)
        
        return results_list


def main():
    """Función principal para uso desde línea de comandos"""
    parser = argparse.ArgumentParser(description='Knowledge Base Search Tool')
    parser.add_argument('query', help='Texto a buscar (obligatorio)')
    parser.add_argument('--top_k', type=int, default=10, help='Número máximo de resultados (por defecto: 10)')
    parser.add_argument('--min_score', type=float, default=0.0, help='Puntuación mínima (por defecto: 0.0)')
    parser.add_argument('--app', default='darwin', choices=['darwin', 'sap', 'mulesoft'], 
                       help='Aplicación a usar (por defecto: darwin)')
    parser.add_argument('--config', help='Ruta al archivo de configuración (opcional)')
    parser.add_argument('--output', help='Archivo de salida JSON (opcional)')
    parser.add_argument('--pretty', action='store_true', help='Mostrar salida formateada')
    
    args = parser.parse_args()
    
    try:
        # Inicializar herramienta
        search_tool = KnowledgeSearchTool(config_path=args.config, application=args.app)
        
        # Ejecutar búsqueda
        results = search_tool.search(args.query, top_k=args.top_k, min_score=args.min_score)
        
        # Guardar en archivo si se especifica
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Resultados guardados en: {args.output}")
        
        # Mostrar resultados
        if args.pretty:
            print("\n" + "="*60)
            print("🔍 RESULTADOS DE BÚSQUEDA")
            print("="*60)
            print(f"Query: {results['query']}")
            print(f"Fragmentos encontrados: {results['total_found']}")
            print(f"Duración: {results['duration_seconds']}s")
            print("-"*60)
            
            for i, fragment in enumerate(results['fragments'], 1):
                print(f"\n{i}. {fragment['file_name']}")
                print(f"   Relevancia: {fragment['relevance']}")
                print(f"   Resumen: {fragment['summary']}")
        else:
            # Salida JSON
            print(json.dumps(results, indent=2, ensure_ascii=False))
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
