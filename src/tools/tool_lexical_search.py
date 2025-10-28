#!/usr/bin/env python3
"""
Herramienta de búsqueda léxica usando BM25.
Búsqueda textual tradicional basada en coincidencias exactas de palabras y términos.
"""

import argparse
import json
import sys
from typing import Dict, List, Any, Optional

from common.common import (
    Config, OpenSearchClient, Logger,
    handle_search_error, log_search_metrics, validate_parameters,
    get_cache, ValidationError
)

class LexicalSearch:
    """Clase principal para búsqueda léxica"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = Config(config_path)
        Logger.setup(self.config)
        self.logger = Logger.get_logger(__name__)
        
        # Inicializar cliente
        self.opensearch_client = OpenSearchClient(self.config).get_client()
        self.cache = get_cache(self.config)
        
        # Configuración específica
        self.index_name = self.config.get('opensearch.index_name')
        self.defaults = self.config.get('defaults.lexical_search', {})
    
    @handle_search_error
    @log_search_metrics
    @validate_parameters(['query'])
    def search(self, query: str, fields: Optional[List[str]] = None,
               operator: Optional[str] = None, top_k: Optional[int] = None,
               fuzzy: Optional[bool] = None) -> Dict[str, Any]:
        """
        Realiza búsqueda léxica usando BM25.
        
        Args:
            query: Términos de búsqueda exactos
            fields: Campos donde buscar
            operator: Operador lógico "AND" | "OR"
            top_k: Número de resultados
            fuzzy: Permitir coincidencias aproximadas
            
        Returns:
            Dict con resultados de la búsqueda
        """
        # Log de entrada con parámetros recibidos
        self.logger.info("="*80)
        self.logger.info("🔍 ENTRADA A BÚSQUEDA LÉXICA")
        self.logger.info("="*80)
        self.logger.info(f"📝 Query recibida: '{query}'")
        self.logger.info(f"📋 Fields recibidos: {fields}")
        self.logger.info(f"🔧 Operator recibido: {operator}")
        self.logger.info(f"🔢 Top_k recibido: {top_k}")
        self.logger.info(f"🎯 Fuzzy recibido: {fuzzy}")
        self.logger.info("-"*80)
        
        # Aplicar valores por defecto
        fields = fields or self.defaults.get('fields', ['content'])
        operator = operator or self.defaults.get('operator', 'OR')
        top_k = top_k or self.defaults.get('top_k', 10)
        fuzzy = fuzzy if fuzzy is not None else self.defaults.get('fuzzy', False)
        
        # Log de parámetros finales después de aplicar defaults
        self.logger.info("📊 PARÁMETROS FINALES (después de defaults):")
        self.logger.info(f"   Query: '{query}'")
        self.logger.info(f"   Fields: {fields}")
        self.logger.info(f"   Operator: {operator}")
        self.logger.info(f"   Top_k: {top_k}")
        self.logger.info(f"   Fuzzy: {fuzzy}")
        self.logger.info("="*80)
        
        # Validar parámetros
        if not isinstance(query, str) or len(query.strip()) == 0:
            raise ValidationError("Query debe ser una cadena no vacía")
        
        if operator not in ['AND', 'OR']:
            raise ValidationError("operator debe ser 'AND' o 'OR'")
        
        if top_k <= 0 or top_k > 1000:
            raise ValidationError("top_k debe estar entre 1 y 1000")
        
        valid_fields = ['content', 'file_name', 'metadata.summary']
        for field in fields:
            if field not in valid_fields:
                raise ValidationError(f"Campo inválido: {field}. Campos válidos: {valid_fields}")
        
        # Verificar cache
        cache_key = f"lexical:{hash(query)}:{str(fields)}:{operator}:{top_k}:{fuzzy}"
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self.logger.info(f"Resultado obtenido del cache para query: {query[:50]}...")
                return cached_result
        
        try:
            # 1. Configurar query multi_match
            query_config = {
                "query": query,
                "fields": fields,
                "operator": operator.lower(),
                "type": "best_fields"
            }
            
            # 2. Añadir fuzzy matching si se solicita
            if fuzzy:
                query_config["fuzziness"] = "AUTO"
            
            # 3. Construir búsqueda con highlighting
            search_body = {
                "size": top_k,
                "query": {"multi_match": query_config},
                "_source": ["content", "file_name", "metadata", "chunk_id"],
                "highlight": {
                    "fields": {
                        field: {
                            "fragment_size": self.defaults.get('fragment_size', 150),
                            "number_of_fragments": self.defaults.get('number_of_fragments', 3)
                        } for field in fields
                    }
                }
            }
            
            # 4. Ejecutar búsqueda
            self.logger.debug(f"Ejecutando búsqueda léxica en índice: {self.index_name}")
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
            self.logger.error(f"Error en búsqueda léxica: {str(e)}")
            raise
    
    def _format_results(self, response: Dict, query: str) -> Dict[str, Any]:
        """Formatea los resultados de OpenSearch en formato compatible con tool_executor"""
        fragments = []
        
        for hit in response['hits']['hits']:
            source = hit['_source']
            highlights = hit.get('highlight', {})
            
            # Procesar highlights
            matches = []
            for field, highlight_list in highlights.items():
                for highlight in highlight_list:
                    matches.append({
                        "field": field,
                        "snippet": highlight
                    })
            
            # Formato compatible con semantic_search (usa 'fragments' y 'content')
            fragments.append({
                "file_name": source['file_name'],
                "score": hit['_score'],
                "chunk_id": source.get('chunk_id', 'unknown'),
                "matches": matches,
                "metadata": source.get('metadata', {}),
                "content": source['content'],  # Contenido completo, no preview
                "content_preview": source['content'][:300] + "..." if len(source['content']) > 300 else source['content']
            })
        
        return {
            "query": query,
            "total_found": len(fragments),  # Compatible con semantic_search
            "total_results": len(fragments),  # Mantener para compatibilidad
            "fragments": fragments,  # Formato esperado por tool_executor
            "results": fragments,  # Mantener para compatibilidad con CLI
            "query_terms": query.split(),
            "search_type": "lexical"
        }

def main():
    """Función principal para uso desde línea de comandos"""
    parser = argparse.ArgumentParser(
        description="Búsqueda léxica en la base de conocimiento Darwin"
    )
    
    parser.add_argument(
        "query",
        help="Términos de búsqueda exactos"
    )
    
    parser.add_argument(
        "--fields",
        nargs="+",
        choices=["content", "file_name", "metadata.summary"],
        help="Campos donde buscar"
    )
    
    parser.add_argument(
        "--operator",
        choices=["AND", "OR"],
        help="Operador lógico entre términos"
    )
    
    parser.add_argument(
        "--top-k",
        type=int,
        help="Número máximo de resultados a devolver"
    )
    
    parser.add_argument(
        "--fuzzy",
        action="store_true",
        help="Permitir coincidencias aproximadas"
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
        search_tool = LexicalSearch(args.config)
        
        # Realizar búsqueda
        result = search_tool.search(
            query=args.query,
            fields=args.fields,
            operator=args.operator,
            top_k=args.top_k,
            fuzzy=args.fuzzy
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
    
    print(f"🔍 Búsqueda léxica: '{result['query']}'")
    print(f"🏷️  Términos: {', '.join(result['query_terms'])}")
    print(f"📊 Resultados encontrados: {result['total_results']}")
    print("=" * 80)
    
    for i, item in enumerate(result['results'], 1):
        print(f"\n{i}. 📄 {item['file_name']}")
        print(f"   🎯 Score: {item['score']:.3f}")
        print(f"   🔗 Chunk ID: {item['chunk_id']}")
        
        # Mostrar matches con highlighting
        if item['matches']:
            print("   🎯 Coincidencias:")
            for match in item['matches'][:3]:  # Mostrar máximo 3 matches
                field = match['field']
                snippet = match['snippet']
                print(f"      • {field}: {snippet}")
        
        # Mostrar preview del contenido
        print(f"   📝 Vista previa: {item['content_preview']}")
        
        # Mostrar metadatos si están disponibles
        metadata = item.get('metadata', {})
        if metadata:
            file_ext = metadata.get('file_extension', 'N/A')
            file_size = metadata.get('file_size', 'N/A')
            print(f"   ℹ️  Tipo: {file_ext}, Tamaño: {file_size} bytes")

if __name__ == "__main__":
    main()
