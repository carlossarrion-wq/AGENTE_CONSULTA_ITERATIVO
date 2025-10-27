#!/usr/bin/env python3
"""
Knowledge Base Search Tool - EC2 Version
Herramienta simplificada para buscar fragmentos en la base de conocimiento OpenSearch
Versión optimizada para ejecutar en EC2 dentro del directorio RAG_SYSTEM_MULTI_v5
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

# Configurar paths para EC2
def setup_paths():
    """Configurar paths para importar dependencias en EC2"""
    current_dir = os.getcwd()
    
    # Verificar que estamos en el directorio correcto
    if not current_dir.endswith('RAG_SYSTEM_MULTI_v5'):
        logger.error("Este script debe ejecutarse desde el directorio RAG_SYSTEM_MULTI_v5")
        sys.exit(1)
    
    # Añadir paths necesarios
    src_path = os.path.join(current_dir, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    logger.info(f"Paths configurados desde: {current_dir}")
    return current_dir

# Configurar paths
BASE_DIR = setup_paths()

# Importar dependencias
try:
    from utils.connection_manager import ConnectionManager
    DEPENDENCIES_AVAILABLE = True
    logger.info("✅ Dependencias importadas correctamente")
except ImportError as e:
    logger.error(f"❌ Error importando dependencias: {e}")
    logger.error("Asegúrate de estar en el directorio RAG_SYSTEM_MULTI_v5 y que las dependencias estén instaladas")
    DEPENDENCIES_AVAILABLE = False


class KnowledgeSearchTool:
    """
    Herramienta simplificada para búsqueda en base de conocimiento OpenSearch
    Versión EC2
    """
    
    def __init__(self, config_path: str = None, application: str = "darwin"):
        """
        Inicializar la herramienta de búsqueda
        
        Args:
            config_path: Ruta al archivo de configuración (opcional)
            application: Aplicación a usar (darwin por defecto)
        """
        self.application = application
        
        # Usar configuración por defecto
        if config_path is None:
            config_path = os.path.join(BASE_DIR, "config", "multi_app_config.yaml")
        
        self.config_path = config_path
        
        if not DEPENDENCIES_AVAILABLE:
            raise ImportError("Las dependencias del sistema RAG no están disponibles")
        
        logger.info(f"Inicializando KnowledgeSearchTool para aplicación: {application}")
        logger.info(f"Usando configuración: {config_path}")
        
        # Cargar configuración
        self._load_config()
        
        # Inicializar conexiones
        self._initialize_connections()
        
        logger.info("✅ KnowledgeSearchTool inicializado correctamente")
    
    def _load_config(self):
        """Cargar configuración desde YAML"""
        try:
            if not os.path.exists(self.config_path):
                raise FileNotFoundError(f"Archivo de configuración no encontrado: {self.config_path}")
            
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
            logger.info(f"Modelo embedding: {self.embedding_model}")
            
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
            logger.info("🧠 Generando embedding...")
            query_embedding = self._get_embedding(query)
            
            # Ejecutar búsqueda híbrida (vectorial + textual)
            logger.info("🔍 Ejecutando búsqueda vectorial...")
            vector_results = self._search_vector(query_embedding, top_k * 2)  # Buscar más para mejor combinación
            
            logger.info("📝 Ejecutando búsqueda textual...")
            text_results = self._search_text(query, top_k * 2)
            
            # Combinar y procesar resultados
            logger.info("🔄 Combinando resultados...")
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
                    "min_score": min_score,
                    "application": self.application,
                    "index": self.index_name
                },
                "timestamp": start_time.isoformat(),
                "duration_seconds": round(duration, 3),
                "total_found": len(final_results),
                "search_stats": {
                    "vector_results": len(vector_results),
                    "text_results": len(text_results),
                    "combined_before_filter": len(combined_results)
                },
                "fragments": []
            }
            
            for result in final_results:
                # Obtener resumen de metadata o contenido
                summary = result.get('summary', '')
                if not summary:
                    content = result.get('content', '')
                    summary = content[:300] + '...' if len(content) > 300 else content
                
                fragment = {
                    "file_name": result.get('file_name', 'unknown'),
                    "relevance": round(result.get('score', 0.0), 3),
                    "summary": summary,
                    "search_type": result.get('search_type', 'unknown'),
                    "chunk_id": result.get('chunk_id', '')
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
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": size
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
        
        logger.info(f"Vector search: {len(results)} resultados")
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
        
        logger.info(f"Text search: {len(results)} resultados")
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
    parser = argparse.ArgumentParser(description='Knowledge Base Search Tool - EC2 Version')
    parser.add_argument('query', help='Texto a buscar (obligatorio)')
    parser.add_argument('--top_k', type=int, default=10, help='Número máximo de resultados (por defecto: 10)')
    parser.add_argument('--min_score', type=float, default=0.0, help='Puntuación mínima (por defecto: 0.0)')
    parser.add_argument('--app', default='darwin', choices=['darwin', 'sap', 'mulesoft'], 
                       help='Aplicación a usar (por defecto: darwin)')
    parser.add_argument('--config', help='Ruta al archivo de configuración (opcional)')
    parser.add_argument('--output', help='Archivo de salida JSON (opcional)')
    parser.add_argument('--pretty', action='store_true', help='Mostrar salida formateada')
    parser.add_argument('--debug', action='store_true', help='Mostrar información de debug')
    
    args = parser.parse_args()
    
    # Configurar nivel de logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
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
            print("\n" + "="*80)
            print("🔍 RESULTADOS DE BÚSQUEDA")
            print("="*80)
            print(f"Query: {results['query']}")
            print(f"Aplicación: {results['parameters']['application']}")
            print(f"Índice: {results['parameters']['index']}")
            print(f"Fragmentos encontrados: {results['total_found']}")
            print(f"Duración: {results['duration_seconds']}s")
            print(f"Stats: Vector={results['search_stats']['vector_results']}, Text={results['search_stats']['text_results']}")
            print("-"*80)
            
            for i, fragment in enumerate(results['fragments'], 1):
                print(f"\n{i}. {fragment['file_name']} ({fragment['search_type']})")
                print(f"   Relevancia: {fragment['relevance']}")
                print(f"   Chunk ID: {fragment['chunk_id']}")
                print(f"   Resumen: {fragment['summary'][:200]}{'...' if len(fragment['summary']) > 200 else ''}")
        else:
            # Salida JSON
            print(json.dumps(results, indent=2, ensure_ascii=False))
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
