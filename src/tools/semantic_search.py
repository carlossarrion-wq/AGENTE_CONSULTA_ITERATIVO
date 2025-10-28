#!/usr/bin/env python3
"""
Herramienta de búsqueda semántica usando embeddings vectoriales.
Busca contenido por significado conceptual, no solo por palabras exactas.
"""

import argparse
import json
import sys
from typing import Dict, List, Any, Optional

# Suprimir warnings de urllib3 sobre HTTPS no verificado
import warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

from common.common import (
    Config, OpenSearchClient, BedrockClient, Logger,
    handle_search_error, log_search_metrics, validate_parameters,
    get_cache, ValidationError
)

class SemanticSearch:
    """Clase principal para búsqueda semántica"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = Config(config_path)
        Logger.setup(self.config)
        self.logger = Logger.get_logger(__name__)
        
        # Inicializar clientes
        self.opensearch_client = OpenSearchClient(self.config).get_client()
        self.bedrock_client = BedrockClient(self.config)
        self.cache = get_cache(self.config)
        
        # Configuración específica
        self.index_name = self.config.get('opensearch.index_name')
        self.defaults = self.config.get('defaults.semantic_search', {})
    
    @handle_search_error
    @log_search_metrics
    @validate_parameters(['query'])
    def search(self, query: str, top_k: Optional[int] = None, 
               min_score: Optional[float] = None, 
               file_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Realiza búsqueda semántica usando embeddings vectoriales.
        
        Args:
            query: Descripción conceptual de lo que se busca
            top_k: Número de resultados más relevantes
            min_score: Puntuación mínima de similitud (0.0-1.0)
            file_types: Filtrar por tipos de archivo
            
        Returns:
            Dict con resultados de la búsqueda
        """
        # Aplicar valores por defecto
        top_k = top_k or self.defaults.get('top_k', 10)
        min_score = min_score or self.defaults.get('min_score', 0.5)
        
        # Validar parámetros
        if not isinstance(query, str) or len(query.strip()) == 0:
            raise ValidationError("Query debe ser una cadena no vacía")
        
        if not 0 <= min_score <= 1:
            raise ValidationError("min_score debe estar entre 0.0 y 1.0")
        
        if top_k <= 0 or top_k > self.defaults.get('max_results', 1000):
            raise ValidationError(f"top_k debe estar entre 1 y {self.defaults.get('max_results', 1000)}")
        
        # Verificar cache
        cache_key = f"semantic:{hash(query)}:{top_k}:{min_score}:{str(file_types)}"
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self.logger.info(f"Resultado obtenido del cache para query: {query[:50]}...")
                return cached_result
        
        try:
            # 1. Generar embedding
            self.logger.debug(f"Generando embedding para query: {query[:100]}...")
            query_embedding = self.bedrock_client.generate_embedding(query)
            
            # 2. Construir query de búsqueda KNN
            search_body = {
                "size": top_k,
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": query_embedding,
                            "k": top_k
                        }
                    }
                },
                "_source": ["content", "file_name", "metadata", "chunk_id"],
                "min_score": min_score
            }
            
            # 3. Filtrar por tipos de archivo si se especifica
            if file_types:
                search_body["query"] = {
                    "bool": {
                        "must": [search_body["query"]],
                        "filter": {
                            "terms": {"metadata.file_extension": file_types}
                        }
                    }
                }
            
            # 4. Ejecutar búsqueda
            self.logger.debug(f"Ejecutando búsqueda KNN en índice: {self.index_name}")
            response = self.opensearch_client.search(
                index=self.index_name, 
                body=search_body
            )
            
            # 5. Formatear resultados
            result = self._format_results(response, query)
            
            # 6. Guardar en cache
            if self.cache:
                self.cache.set(cache_key, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda semántica: {str(e)}")
            raise
    
    def _format_results(self, response: Dict, query: str) -> Dict[str, Any]:
        """Formatea los resultados de OpenSearch"""
        fragments = []
        
        for hit in response['hits']['hits']:
            source = hit['_source']
            fragments.append({
                "file_name": source['file_name'],
                "score": hit['_score'],  # Usar 'score' para consistencia con otras herramientas
                "content": source['content'],  # Contenido del chunk
                "chunk_id": source.get('chunk_id', 'unknown'),
                "metadata": source.get('metadata', {})
            })
        
        return {
            "query": query,
            "total_found": len(fragments),
            "fragments": fragments,
            "search_type": "semantic"
        }

def main():
    """Función principal para uso desde línea de comandos"""
    parser = argparse.ArgumentParser(
        description="Búsqueda semántica en la base de conocimiento Darwin"
    )
    
    parser.add_argument(
        "query",
        help="Consulta semántica a realizar"
    )
    
    parser.add_argument(
        "--top-k",
        type=int,
        help="Número máximo de resultados a devolver"
    )
    
    parser.add_argument(
        "--min-score",
        type=float,
        help="Puntuación mínima de similitud (0.0-1.0)"
    )
    
    parser.add_argument(
        "--file-types",
        nargs="+",
        help="Filtrar por tipos de archivo (ej: docx pdf xlsx)"
    )
    
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Ruta al archivo de configuración"
    )
    
    parser.add_argument(
        "--output",
        choices=["json", "pretty"],
        default="pretty",
        help="Formato de salida"
    )
    
    args = parser.parse_args()
    
    try:
        # Crear instancia de búsqueda
        search_tool = SemanticSearch(args.config)
        
        # Realizar búsqueda
        result = search_tool.search(
            query=args.query,
            top_k=args.top_k,
            min_score=args.min_score,
            file_types=args.file_types
        )
        
        # Mostrar resultados
        if args.output == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print_pretty_results(result)
            
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

def print_pretty_results(result: Dict[str, Any]):
    """Imprime los resultados en formato legible"""
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"🔍 Búsqueda semántica: '{result['query']}'")
    print(f"📊 Resultados encontrados: {result['total_found']}")
    print("=" * 80)
    
    for i, fragment in enumerate(result['fragments'], 1):
        print(f"\n{i}. 📄 {fragment['file_name']}")
        print(f"   🎯 Relevancia: {fragment['score']:.3f}")
        print(f"   🔗 Chunk ID: {fragment['chunk_id']}")
        
        # Mostrar resumen truncado
        content = fragment['content']
        if len(content) > 200:
            content = content[:200] + "..."
        print(f"   📝 Contenido: {content}")
        
        # Mostrar metadatos si están disponibles
        metadata = fragment.get('metadata', {})
        if metadata:
            file_ext = metadata.get('file_extension', 'N/A')
            file_size = metadata.get('file_size', 'N/A')
            print(f"   ℹ️  Tipo: {file_ext}, Tamaño: {file_size} bytes")

if __name__ == "__main__":
    main()
