#!/usr/bin/env python3
"""
Herramienta para obtener el contenido completo de archivos.
Reconstruye archivos completos desde chunks indexados, manejando overlaps.
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
    Config, OpenSearchClient, Logger,
    handle_search_error, log_search_metrics, validate_parameters,
    get_cache, ValidationError, find_overlap_length, calculate_text_similarity,
    remove_duplicate_chunks_by_hash
)

# Importar herramientas de acceso progresivo
try:
    from tools.document_structure_analyzer import DocumentStructureAnalyzer
    PROGRESSIVE_ACCESS_AVAILABLE = True
except ImportError:
    PROGRESSIVE_ACCESS_AVAILABLE = False

class GetFileContent:
    """Clase principal para obtener contenido de archivos"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = Config(config_path)
        Logger.setup(self.config)
        self.logger = Logger.get_logger(__name__)
        
        # Inicializar cliente
        self.opensearch_client = OpenSearchClient(self.config).get_client()
        self.cache = get_cache(self.config)
        
        # Configuración específica
        self.index_name = self.config.get('opensearch.index_name')
        self.defaults = self.config.get('defaults.get_file_content', {})
    
    @handle_search_error
    @log_search_metrics
    @validate_parameters(['file_path'])
    def get_content(self, file_path: str, 
                   include_metadata: Optional[bool] = None) -> Dict[str, Any]:
        """
        Obtiene el contenido completo de un archivo específico.
        Si el archivo es muy grande, devuelve la estructura del documento
        para acceso progresivo.
        
        Args:
            file_path: Nombre del archivo tal como aparece en el índice
            include_metadata: Incluir metadatos adicionales
            
        Returns:
            Dict con el contenido del archivo o su estructura si es muy grande
        """
        # Aplicar valores por defecto
        include_metadata = include_metadata if include_metadata is not None else self.defaults.get('include_metadata', False)
        
        # Validar parámetros
        if not isinstance(file_path, str) or len(file_path.strip()) == 0:
            raise ValidationError("file_path debe ser una cadena no vacía")
        
        # Verificar cache
        cache_key = f"file_content:{hash(file_path)}:{include_metadata}"
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self.logger.info(f"Contenido obtenido del cache para archivo: {file_path}")
                return cached_result
        
        try:
            # 1. Buscar todos los chunks del archivo usando scroll
            all_chunks = self._get_all_chunks(file_path)
            
            # 2. Verificar si se encontró el archivo
            if not all_chunks:
                available_files = self._get_available_files_sample()
                return {
                    "error": f"Archivo no encontrado: {file_path}",
                    "available_files": available_files
                }
            
            # 3. Ordenar chunks
            chunks = sorted(all_chunks, key=lambda x: x['_source'].get('chunk_id', 0))
            
            # 4. Verificar si el archivo es muy grande y si el acceso progresivo está habilitado
            max_length = self.defaults.get('max_content_length_for_full_retrieval', 50000)
            enable_progressive = self.defaults.get('enable_progressive_access', True)
            
            # Calcular longitud total estimada
            total_length = sum(len(chunk['_source'].get('content', '')) for chunk in chunks)
            
            # 5. Si el archivo es grande y el acceso progresivo está habilitado, devolver estructura
            if enable_progressive and total_length > max_length and PROGRESSIVE_ACCESS_AVAILABLE:
                self.logger.info(f"Archivo {file_path} es grande ({total_length} chars). Usando acceso progresivo.")
                return self._get_document_structure(file_path, chunks, include_metadata)
            
            # 6. Si el archivo es pequeño o el acceso progresivo está deshabilitado, devolver contenido completo
            full_content = self._reconstruct_content_with_overlap_handling(chunks)
            
            # 7. Preparar resultado
            result = {
                "file_path": file_path,
                "content": full_content,
                "total_chunks": len(chunks),
                "content_length": len(full_content),
                "overlap_handling": "applied",
                "access_mode": "full"
            }
            
            # 8. Incluir metadata si se solicita
            if include_metadata and chunks:
                result["metadata"] = chunks[0]['_source'].get('metadata', {})
                result["file_info"] = {
                    "first_chunk_id": chunks[0]['_source'].get('chunk_id'),
                    "last_chunk_id": chunks[-1]['_source'].get('chunk_id'),
                    "file_extension": chunks[0]['_source'].get('metadata', {}).get('file_extension'),
                    "file_size": chunks[0]['_source'].get('metadata', {}).get('file_size')
                }
            
            # 9. Guardar en cache
            if self.cache:
                self.cache.set(cache_key, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error al obtener contenido del archivo: {str(e)}")
            raise
    
    def _get_document_structure(self, file_path: str, chunks: List[Dict], 
                               include_metadata: bool) -> Dict[str, Any]:
        """
        Obtiene la estructura del documento para acceso progresivo.
        
        Args:
            file_path: Nombre del archivo
            chunks: Lista de chunks del documento
            include_metadata: Si incluir metadatos
            
        Returns:
            Dict con la estructura del documento
        """
        try:
            # Reconstruir contenido completo para análisis de estructura
            full_content = self._reconstruct_content_with_overlap_handling(chunks)
            
            # Usar DocumentStructureAnalyzer para obtener la estructura
            analyzer = DocumentStructureAnalyzer(self.config)
            structure_result = analyzer.analyze_structure(file_path)
            
            if "error" in structure_result:
                # Si hay error en el análisis, devolver contenido completo como fallback
                self.logger.warning(f"Error analizando estructura de {file_path}, devolviendo contenido completo")
                return {
                    "file_path": file_path,
                    "content": full_content,
                    "total_chunks": len(chunks),
                    "content_length": len(full_content),
                    "access_mode": "full",
                    "note": "Progressive access failed, returning full content"
                }
            
            # Preparar resultado con estructura
            result = {
                "file_path": file_path,
                "access_mode": "progressive",
                "total_chunks": len(chunks),
                "content_length": len(full_content),
                "structure": structure_result.get("structure", {}),
                "message": (
                    f"Este archivo es grande ({len(full_content):,} caracteres). "
                    f"Se proporciona la estructura del documento. "
                    f"Usa la herramienta 'get_file_section' para obtener secciones específicas."
                ),
                "available_sections": structure_result.get("structure", {}).get("sections", []),
                "recommendation": (
                    "Analiza la estructura y selecciona las secciones relevantes para tu consulta. "
                    "Luego usa get_file_section con los identificadores de sección apropiados."
                )
            }
            
            # Incluir metadata si se solicita
            if include_metadata and chunks:
                result["metadata"] = chunks[0]['_source'].get('metadata', {})
                result["file_info"] = {
                    "first_chunk_id": chunks[0]['_source'].get('chunk_id'),
                    "last_chunk_id": chunks[-1]['_source'].get('chunk_id'),
                    "file_extension": chunks[0]['_source'].get('metadata', {}).get('file_extension'),
                    "file_size": chunks[0]['_source'].get('metadata', {}).get('file_size')
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estructura del documento: {str(e)}")
            # Fallback: devolver contenido completo
            full_content = self._reconstruct_content_with_overlap_handling(chunks)
            return {
                "file_path": file_path,
                "content": full_content,
                "total_chunks": len(chunks),
                "content_length": len(full_content),
                "access_mode": "full",
                "note": f"Progressive access error: {str(e)}"
            }
    
    def _get_all_chunks(self, file_path: str) -> List[Dict]:
        """Obtiene todos los chunks de un archivo usando scroll"""
        # Normalizar el nombre del archivo (eliminar espacios extras)
        normalized_path = ' '.join(file_path.split())
        
        # Intentar múltiples estrategias de búsqueda
        search_strategies = [
            # Estrategia 1: Búsqueda exacta con keyword
            {
                "term": {
                    "file_name.keyword": file_path
                }
            },
            # Estrategia 2: Búsqueda exacta normalizada con keyword
            {
                "term": {
                    "file_name.keyword": normalized_path
                }
            },
            # Estrategia 3: Búsqueda exacta sin keyword
            {
                "term": {
                    "file_name": file_path
                }
            },
            # Estrategia 4: Búsqueda con match (más flexible, ignora espacios extras)
            {
                "match": {
                    "file_name": {
                        "query": file_path,
                        "operator": "and"
                    }
                }
            },
            # Estrategia 5: Búsqueda con match_phrase (frase exacta)
            {
                "match_phrase": {
                    "file_name": file_path
                }
            },
            # Estrategia 6: Búsqueda fuzzy para manejar variaciones
            {
                "match": {
                    "file_name": {
                        "query": file_path,
                        "fuzziness": "AUTO"
                    }
                }
            },
            # Estrategia 7: Wildcard para manejar espacios variables
            {
                "wildcard": {
                    "file_name.keyword": {
                        "value": f"*{file_path.replace(' ', '*')}*"
                    }
                }
            }
        ]
        
        all_chunks = []
        
        # Probar cada estrategia hasta encontrar resultados
        for i, query in enumerate(search_strategies):
            search_body = {
                "size": self.defaults.get('batch_size', 100),
                "query": query,
                "sort": [{"chunk_id": {"order": "asc"}}],
                "_source": ["content", "file_name", "metadata", "chunk_id", "chunk_start", "chunk_end", "overlap_info"]
            }
            
            try:
                scroll_timeout = self.config.get('opensearch.scroll_timeout', '2m')
                
                # Iniciar scroll
                response = self.opensearch_client.search(
                    index=self.index_name,
                    body=search_body,
                    scroll=scroll_timeout
                )
                
                # Si encontramos resultados, procesarlos
                if response['hits']['hits']:
                    # Solo loggear si es la primera estrategia que no funciona (para debugging)
                    if i > 0:
                        self.logger.debug(f"Archivo encontrado con estrategia {i+1} para: {file_path}")
                    
                    while len(response['hits']['hits']) > 0:
                        all_chunks.extend(response['hits']['hits'])
                        
                        if '_scroll_id' in response:
                            response = self.opensearch_client.scroll(
                                scroll_id=response['_scroll_id'],
                                scroll=scroll_timeout
                            )
                        else:
                            break
                    
                    # Si encontramos chunks, salir del bucle
                    if all_chunks:
                        break
                        
            except Exception as e:
                # Solo loggear errores si es la última estrategia
                if i == len(search_strategies) - 1 and not all_chunks:
                    self.logger.warning(f"No se pudo encontrar archivo {file_path} después de {len(search_strategies)} estrategias")
                continue
        
        return all_chunks
    
    def _reconstruct_content_with_overlap_handling(self, chunks: List[Dict]) -> str:
        """
        Reconstruye el contenido del archivo manejando overlaps entre chunks.
        """
        if not chunks:
            return ""
        
        if len(chunks) == 1:
            return chunks[0]['_source']['content']
        
        # Estrategia 1: Si tenemos información de posición, usarla
        if all('chunk_start' in chunk['_source'] and 'chunk_end' in chunk['_source'] for chunk in chunks):
            return self._reconstruct_by_position(chunks)
        
        # Estrategia 2: Detección de overlap por similitud de texto
        return self._reconstruct_by_overlap_detection(chunks)
    
    def _reconstruct_by_position(self, chunks: List[Dict]) -> str:
        """Reconstruye usando información de posición de caracteres"""
        content_map = {}
        
        for chunk in chunks:
            source = chunk['_source']
            start = source.get('chunk_start', 0)
            content = source['content']
            
            # Mapear cada posición al contenido correspondiente
            for i, char in enumerate(content):
                pos = start + i
                if pos not in content_map:  # Evitar sobrescribir
                    content_map[pos] = char
        
        # Reconstruir en orden de posición
        if content_map:
            max_pos = max(content_map.keys())
            result = []
            for i in range(max_pos + 1):
                if i in content_map:
                    result.append(content_map[i])
            return ''.join(result)
        
        # Fallback si no hay posiciones válidas
        return self._reconstruct_by_overlap_detection(chunks)
    
    def _reconstruct_by_overlap_detection(self, chunks: List[Dict]) -> str:
        """Reconstruye detectando overlaps por similitud de texto"""
        if not chunks:
            return ""
        
        # Comenzar con el primer chunk
        result_content = chunks[0]['_source']['content']
        
        min_overlap = self.defaults.get('min_overlap', 50)
        similarity_threshold = self.defaults.get('similarity_threshold', 0.85)
        
        for i in range(1, len(chunks)):
            current_chunk = chunks[i]['_source']['content']
            
            # Buscar overlap entre el final del contenido actual y el inicio del nuevo chunk
            overlap_length = find_overlap_length(result_content, current_chunk, min_overlap)
            
            if overlap_length > 0:
                # Hay overlap, añadir solo la parte no duplicada
                unique_part = current_chunk[overlap_length:]
                result_content += unique_part
                # Logging reducido: solo loggear overlaps grandes
                if overlap_length > 500:
                    self.logger.debug(f"Overlap grande detectado: {overlap_length} caracteres en chunk {i}")
            else:
                # No hay overlap detectado, añadir separador y contenido completo
                if not result_content.endswith('\n'):
                    result_content += '\n'
                result_content += current_chunk
        
        return result_content
    
    def _get_available_files_sample(self) -> List[str]:
        """Obtiene una muestra de archivos disponibles para ayudar al usuario"""
        try:
            search_body = {
                "size": 0,
                "aggs": {
                    "unique_files": {
                        "terms": {
                            "field": "file_name.keyword",
                            "size": 20
                        }
                    }
                }
            }
            
            response = self.opensearch_client.search(
                index=self.index_name,
                body=search_body
            )
            
            files = []
            for bucket in response['aggregations']['unique_files']['buckets']:
                files.append(bucket['key'])
            
            return files
            
        except Exception as e:
            self.logger.error(f"Error obteniendo lista de archivos: {str(e)}")
            return ["Error retrieving file list"]

def main():
    """Función principal para uso desde línea de comandos"""
    parser = argparse.ArgumentParser(
        description="Obtener contenido completo de archivos de la base de conocimiento Darwin"
    )
    
    parser.add_argument(
        "file_path",
        help="Nombre del archivo a obtener"
    )
    
    parser.add_argument(
        "--include-metadata",
        action="store_true",
        help="Incluir metadatos adicionales del archivo"
    )
    
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Ruta al archivo de configuración"
    )
    
    parser.add_argument(
        "--output",
        choices=["json", "pretty", "content-only"],
        default="pretty",
        help="Formato de salida"
    )
    
    parser.add_argument(
        "--save-to",
        help="Guardar contenido en archivo especificado"
    )
    
    args = parser.parse_args()
    
    try:
        # Crear instancia de la herramienta
        file_tool = GetFileContent(args.config)
        
        # Obtener contenido
        result = file_tool.get_content(
            file_path=args.file_path,
            include_metadata=args.include_metadata
        )
        
        # Guardar en archivo si se especifica
        if args.save_to and "content" in result:
            with open(args.save_to, 'w', encoding='utf-8') as f:
                f.write(result['content'])
            print(f"Contenido guardado en: {args.save_to}")
        
        # Mostrar resultados
        if args.output == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif args.output == "content-only":
            if "content" in result:
                print(result['content'])
            else:
                print(f"Error: {result.get('error', 'Contenido no disponible')}", file=sys.stderr)
        else:
            print_pretty_results(result)
            
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

def print_pretty_results(result: Dict[str, Any]):
    """Imprime los resultados en formato legible"""
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        if "available_files" in result:
            print("\n📁 Archivos disponibles (muestra):")
            for i, file_name in enumerate(result['available_files'][:10], 1):
                print(f"   {i}. {file_name}")
            if len(result['available_files']) > 10:
                print(f"   ... y {len(result['available_files']) - 10} archivos más")
        return
    
    print(f"📄 Archivo: {result['file_path']}")
    print(f"📊 Estadísticas:")
    print(f"   • Total chunks: {result['total_chunks']}")
    print(f"   • Longitud contenido: {result['content_length']:,} caracteres")
    print(f"   • Manejo de overlaps: {result['overlap_handling']}")
    
    # Mostrar metadatos si están disponibles
    if "metadata" in result:
        metadata = result['metadata']
        print(f"   • Tipo: {metadata.get('file_extension', 'N/A')}")
        print(f"   • Tamaño original: {metadata.get('file_size', 'N/A')} bytes")
    
    if "file_info" in result:
        file_info = result['file_info']
        print(f"   • Rango chunks: {file_info['first_chunk_id']} - {file_info['last_chunk_id']}")
    
    print("\n" + "=" * 80)
    print("📝 CONTENIDO:")
    print("=" * 80)
    
    # Mostrar preview del contenido (primeras 1000 caracteres)
    content = result['content']
    if len(content) > 1000:
        print(content[:1000])
        print(f"\n... [Contenido truncado. Total: {len(content):,} caracteres]")
        print("💡 Usa --output content-only para ver el contenido completo")
        print("💡 Usa --save-to archivo.txt para guardar en archivo")
    else:
        print(content)

if __name__ == "__main__":
    main()
