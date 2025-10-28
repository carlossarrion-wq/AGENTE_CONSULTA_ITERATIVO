#!/usr/bin/env python3
"""
Herramienta de búsqueda por expresiones regulares.
Búsqueda mediante patrones regex para encontrar estructuras específicas de código o texto.
"""

import argparse
import json
import sys
import re
from typing import Dict, List, Any, Optional

from common.common import (
    Config, OpenSearchClient, Logger,
    handle_search_error, log_search_metrics, validate_parameters,
    get_cache, ValidationError
)

class RegexSearch:
    """Clase principal para búsqueda por regex"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = Config(config_path)
        Logger.setup(self.config)
        self.logger = Logger.get_logger(__name__)
        
        # Inicializar cliente
        self.opensearch_client = OpenSearchClient(self.config).get_client()
        self.cache = get_cache(self.config)
        
        # Configuración específica
        self.index_name = self.config.get('opensearch.index_name')
        self.defaults = self.config.get('defaults.regex_search', {})
    
    @handle_search_error
    @log_search_metrics
    @validate_parameters(['pattern'])
    def search(self, pattern: str, file_types: Optional[List[str]] = None,
               case_sensitive: Optional[bool] = None, 
               max_matches_per_file: Optional[int] = None,
               context_lines: Optional[int] = None) -> Dict[str, Any]:
        """
        Realiza búsqueda por expresiones regulares.
        
        Args:
            pattern: Expresión regular (sintaxis estándar)
            file_types: Filtrar por extensiones de archivo
            case_sensitive: Sensible a mayúsculas
            max_matches_per_file: Máximo de coincidencias por archivo
            context_lines: Líneas de contexto antes/después
            
        Returns:
            Dict con resultados de la búsqueda
        """
        # Aplicar valores por defecto
        case_sensitive = case_sensitive if case_sensitive is not None else self.defaults.get('case_sensitive', True)
        max_matches_per_file = max_matches_per_file or self.defaults.get('max_matches_per_file', 50)
        context_lines = context_lines or self.defaults.get('context_lines', 2)
        
        # Validar parámetros
        if not isinstance(pattern, str) or len(pattern.strip()) == 0:
            raise ValidationError("Pattern debe ser una cadena no vacía")
        
        # Validar que el patrón regex es válido
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            re.compile(pattern, flags)
        except re.error as e:
            raise ValidationError(f"Patrón regex inválido: {str(e)}")
        
        if max_matches_per_file <= 0 or max_matches_per_file > 1000:
            raise ValidationError("max_matches_per_file debe estar entre 1 y 1000")
        
        if context_lines < 0 or context_lines > 20:
            raise ValidationError("context_lines debe estar entre 0 y 20")
        
        # Verificar cache
        cache_key = f"regex:{hash(pattern)}:{str(file_types)}:{case_sensitive}:{max_matches_per_file}:{context_lines}"
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self.logger.info(f"Resultado obtenido del cache para pattern: {pattern[:50]}...")
                return cached_result
        
        try:
            # 1. Construir query de búsqueda
            # Para patrones simples sin caracteres especiales de regex, usar wildcard
            # Para patrones complejos, usar regexp
            is_simple_pattern = all(c.isalnum() or c.isspace() for c in pattern)
            
            if is_simple_pattern:
                # Usar wildcard query para patrones simples (más eficiente y confiable)
                search_body = {
                    "size": self.defaults.get('max_documents', 1000),
                    "query": {
                        "wildcard": {
                            "content": {
                                "value": f"*{pattern}*",
                                "case_insensitive": not case_sensitive
                            }
                        }
                    },
                    "_source": ["content", "file_name", "metadata", "chunk_id"]
                }
            else:
                # Usar regexp query para patrones complejos
                search_body = {
                    "size": self.defaults.get('max_documents', 1000),
                    "query": {
                        "regexp": {
                            "content": {
                                "value": pattern,
                                "flags": "ALL" if not case_sensitive else "NONE"
                            }
                        }
                    },
                    "_source": ["content", "file_name", "metadata", "chunk_id"]
                }
            
            # 2. Filtrar por tipos de archivo si se especifica
            if file_types:
                search_body["query"] = {
                    "bool": {
                        "must": [search_body["query"]],
                        "filter": {
                            "terms": {"metadata.file_extension": file_types}
                        }
                    }
                }
            
            # 3. Ejecutar búsqueda
            self.logger.debug(f"Ejecutando búsqueda regex en índice: {self.index_name}")
            response = self.opensearch_client.search(
                index=self.index_name,
                body=search_body
            )
            
            # 4. Procesar matches con contexto
            result = self._format_regex_results(
                response, pattern, context_lines, max_matches_per_file, flags
            )
            
            # 5. Guardar en cache
            if self.cache:
                self.cache.set(cache_key, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda regex: {str(e)}")
            raise
    
    def _format_regex_results(self, response: Dict, pattern: str, context_lines: int,
                             max_matches_per_file: int, flags: int) -> Dict[str, Any]:
        """Formatea los resultados de la búsqueda regex"""
        results = []
        total_matches = 0
        
        # Intentar compilar el patrón, pero si falla, mostrar los resultados de OpenSearch sin procesamiento adicional
        try:
            compiled_pattern = re.compile(pattern, flags)
            use_python_regex = True
        except re.error:
            use_python_regex = False
            self.logger.warning(f"No se pudo compilar el patrón regex en Python: {pattern}")
        
        for hit in response['hits']['hits']:
            source = hit['_source']
            content = source['content']
            lines = content.split('\n')
            
            # Buscar matches en el contenido
            matches = []
            
            if use_python_regex:
                # Usar regex de Python para encontrar matches exactos
                for line_num, line in enumerate(lines):
                    for match in compiled_pattern.finditer(line):
                        if len(matches) >= max_matches_per_file:
                            break
                        
                        # Extraer contexto
                        start_line = max(0, line_num - context_lines)
                        end_line = min(len(lines), line_num + context_lines + 1)
                        
                        context_before = lines[start_line:line_num]
                        context_after = lines[line_num + 1:end_line]
                        
                        matches.append({
                            "line_number": line_num + 1,
                            "match": match.group(),
                            "match_start": match.start(),
                            "match_end": match.end(),
                            "context_before": context_before,
                            "context_after": context_after,
                            "full_line": line
                        })
                        total_matches += 1
                    
                    if len(matches) >= max_matches_per_file:
                        break
            else:
                # Si no se puede usar regex de Python, mostrar el contenido completo que OpenSearch encontró
                # Esto es útil cuando OpenSearch encuentra resultados pero Python no puede procesar el patrón
                matches.append({
                    "line_number": 1,
                    "match": f"Contenido encontrado por OpenSearch (patrón: {pattern})",
                    "match_start": 0,
                    "match_end": len(content),
                    "context_before": [],
                    "context_after": [],
                    "full_line": content[:500] + "..." if len(content) > 500 else content
                })
                total_matches += 1
            
            # Solo agregar si hay matches o si OpenSearch encontró el documento
            if matches or not use_python_regex:
                if not matches and not use_python_regex:
                    # Crear un match genérico para mostrar que OpenSearch encontró algo
                    matches.append({
                        "line_number": 1,
                        "match": f"Contenido encontrado por OpenSearch",
                        "match_start": 0,
                        "match_end": 0,
                        "context_before": [],
                        "context_after": [],
                        "full_line": content[:200] + "..." if len(content) > 200 else content
                    })
                    total_matches += 1
                
                results.append({
                    "file_name": source['file_name'],
                    "chunk_id": source.get('chunk_id', 'unknown'),
                    "matches": matches,
                    "match_count": len(matches),
                    "metadata": source.get('metadata', {})
                })
        
        return {
            "pattern": pattern,
            "total_matches": total_matches,
            "total_files": len(results),
            "total_found": len(results),  # Compatible con otras herramientas
            "results": results,  # Mantener para CLI
            "fragments": results,  # Compatible con request_handler
            "search_type": "regex"
        }

def main():
    """Función principal para uso desde línea de comandos"""
    parser = argparse.ArgumentParser(
        description="Búsqueda por expresiones regulares en la base de conocimiento Darwin"
    )
    
    parser.add_argument(
        "pattern",
        help="Expresión regular a buscar"
    )
    
    parser.add_argument(
        "--file-types",
        nargs="+",
        help="Filtrar por tipos de archivo (ej: js ts py)"
    )
    
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Búsqueda sensible a mayúsculas"
    )
    
    parser.add_argument(
        "--max-matches-per-file",
        type=int,
        help="Máximo número de coincidencias por archivo"
    )
    
    parser.add_argument(
        "--context-lines",
        type=int,
        help="Número de líneas de contexto antes y después"
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
        search_tool = RegexSearch(args.config)
        
        # Realizar búsqueda
        result = search_tool.search(
            pattern=args.pattern,
            file_types=args.file_types,
            case_sensitive=args.case_sensitive,
            max_matches_per_file=args.max_matches_per_file,
            context_lines=args.context_lines
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
    
    print(f"🔍 Búsqueda regex: '{result['pattern']}'")
    print(f"📊 Total coincidencias: {result['total_matches']} en {result['total_files']} archivos")
    print("=" * 80)
    
    for i, file_result in enumerate(result['results'], 1):
        print(f"\n{i}. 📄 {file_result['file_name']}")
        print(f"   🔗 Chunk ID: {file_result['chunk_id']}")
        print(f"   🎯 Coincidencias: {file_result['match_count']}")
        
        # Mostrar metadatos si están disponibles
        metadata = file_result.get('metadata', {})
        if metadata:
            file_ext = metadata.get('file_extension', 'N/A')
            print(f"   ℹ️  Tipo: {file_ext}")
        
        # Mostrar matches (máximo 3 por archivo para no saturar)
        for j, match in enumerate(file_result['matches'][:3], 1):
            print(f"\n   Match {j} (línea {match['line_number']}):")
            print(f"   🎯 Coincidencia: '{match['match']}'")
            
            # Mostrar contexto
            if match['context_before']:
                print("   📝 Contexto anterior:")
                for line in match['context_before'][-2:]:  # Máximo 2 líneas antes
                    if line.strip():
                        print(f"      {line}")
            
            print(f"   ➤  {match['full_line']}")
            
            if match['context_after']:
                print("   📝 Contexto posterior:")
                for line in match['context_after'][:2]:  # Máximo 2 líneas después
                    if line.strip():
                        print(f"      {line}")
        
        if file_result['match_count'] > 3:
            print(f"   ... y {file_result['match_count'] - 3} coincidencias más")

if __name__ == "__main__":
    main()
