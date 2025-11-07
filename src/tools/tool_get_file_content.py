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
    def get_content(self, file_path: str) -> Dict[str, Any]:
        """
        Obtiene el contenido completo de un archivo específico.
        Si el archivo es muy grande, devuelve la estructura del documento
        para acceso progresivo.
        
        Args:
            file_path: Nombre del archivo tal como aparece en el índice
            
        Returns:
            Dict con el contenido del archivo o su estructura si es muy grande
        """
        # FORZAR metadata a False para evitar overflow
        include_metadata = False
        
        # Validar parámetros
        if not isinstance(file_path, str) or len(file_path.strip()) == 0:
            raise ValidationError("file_path debe ser una cadena no vacía")
        
        # IMPORTANTE: Preservar el file_path original del usuario (puede incluir ruta S3)
        original_file_path = file_path
        
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
                    "error": f"Archivo no encontrado: {original_file_path}",
                    "available_files": available_files
                }
            
            # 3. Ordenar chunks
            chunks = sorted(all_chunks, key=lambda x: x['_source'].get('chunk_id', 0))
            
            # 4. Verificar si el archivo es muy grande y si el acceso progresivo está habilitado
            max_length = self.defaults.get('max_content_length_for_full_retrieval', 50000)
            enable_progressive = self.defaults.get('enable_progressive_access', True)
            
            # 5. OPTIMIZACIÓN: Intentar cargar estructura pre-calculada desde S3
            if enable_progressive and PROGRESSIVE_ACCESS_AVAILABLE:
                structure_from_s3 = self._load_structure_from_s3(file_path, chunks)
                if structure_from_s3:
                    self.logger.info(f"Estructura cargada desde S3 para: {file_path}")
                    return self._format_structure_response(original_file_path, chunks, structure_from_s3, include_metadata)
            
            # 6. Calcular longitud total estimada
            total_length = sum(len(chunk['_source'].get('content', '')) for chunk in chunks)
            
            # 7. Si el archivo es grande y el acceso progresivo está habilitado, devolver estructura
            if enable_progressive and total_length > max_length and PROGRESSIVE_ACCESS_AVAILABLE:
                self.logger.info(f"Archivo {original_file_path} es grande ({total_length} chars). Usando acceso progresivo.")
                return self._get_document_structure(original_file_path, chunks, include_metadata)
            
            # 6. Si el archivo es pequeño o el acceso progresivo está deshabilitado, devolver contenido completo
            full_content = self._reconstruct_content_with_overlap_handling(chunks)
            
            # 7. Preparar resultado
            result = {
                "file_path": original_file_path,
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
        OPTIMIZADO: Analiza estructura desde chunks sin reconstruir contenido completo.
        
        Args:
            file_path: Nombre del archivo
            chunks: Lista de chunks del documento
            include_metadata: Si incluir metadatos
            
        Returns:
            Dict con la estructura del documento
        """
        try:
            # Calcular longitud total estimada SIN reconstruir el contenido
            total_length = sum(len(chunk['_source'].get('content', '')) for chunk in chunks)
            
            # Analizar estructura desde los chunks directamente
            structure = self._analyze_structure_from_chunks(chunks)
            
            # Preparar resultado con estructura
            result = {
                "file_path": file_path,
                "access_mode": "progressive",
                "total_chunks": len(chunks),
                "content_length": total_length,
                "structure": structure,
                "message": (
                    f"📄 Este archivo es grande ({total_length:,} caracteres, {len(chunks)} chunks). "
                    f"Se proporciona la estructura del documento para acceso eficiente.\n\n"
                    f"💡 Usa la herramienta 'get_file_section' para obtener secciones específicas por:\n"
                    f"   • Rango de chunks (ej: chunks 1-10)\n"
                    f"   • Rango de páginas (ej: páginas 5-15)\n"
                    f"   • ID de sección (ej: section_3)"
                ),
                "available_sections": structure.get("sections", []),
                "chunk_ranges": structure.get("chunk_ranges", []),
                "recommendation": (
                    "1. Revisa la estructura y tabla de contenidos\n"
                    "2. Identifica las secciones relevantes para tu consulta\n"
                    "3. Usa get_file_section para obtener el contenido específico"
                )
            }
            
            # Incluir metadata si se solicita
            if include_metadata and chunks:
                result["metadata"] = chunks[0]['_source'].get('metadata', {})
                result["file_info"] = {
                    "first_chunk_id": chunks[0]['_source'].get('chunk_id'),
                    "last_chunk_id": chunks[-1]['_source'].get('chunk_id'),
                    "file_extension": chunks[0]['_source'].get('metadata', {}).get('file_extension'),
                    "file_size": chunks[0]['_source'].get('metadata', {}).get('file_size'),
                    "total_pages": chunks[0]['_source'].get('metadata', {}).get('total_pages')
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estructura del documento: {str(e)}")
            # Fallback simplificado: devolver información básica sin contenido
            total_length = sum(len(chunk['_source'].get('content', '')) for chunk in chunks)
            return {
                "file_path": file_path,
                "access_mode": "progressive",
                "total_chunks": len(chunks),
                "content_length": total_length,
                "message": (
                    f"📄 Archivo grande detectado ({total_length:,} caracteres, {len(chunks)} chunks).\n\n"
                    f"💡 Usa 'get_file_section' para obtener contenido por:\n"
                    f"   • Rango de chunks: chunks 1-10\n"
                    f"   • Rango de páginas: páginas 1-20"
                ),
                "chunk_ranges": [
                    {
                        "description": f"Chunks 1-{min(10, len(chunks))} (inicio del documento)",
                        "chunk_start": 1,
                        "chunk_end": min(10, len(chunks))
                    },
                    {
                        "description": f"Chunks {len(chunks)//2}-{len(chunks)//2+10} (mitad del documento)",
                        "chunk_start": len(chunks)//2,
                        "chunk_end": min(len(chunks)//2+10, len(chunks))
                    },
                    {
                        "description": f"Chunks {max(1, len(chunks)-10)}-{len(chunks)} (final del documento)",
                        "chunk_start": max(1, len(chunks)-10),
                        "chunk_end": len(chunks)
                    }
                ],
                "note": f"Error analyzing structure: {str(e)}. Use chunk ranges for access."
            }
    
    def _analyze_structure_from_chunks(self, chunks: List[Dict]) -> Dict[str, Any]:
        """
        Analiza la estructura del documento desde los chunks sin reconstruir contenido completo.
        OPTIMIZADO: Solo analiza los primeros chunks para detectar estructura rápidamente.
        
        Args:
            chunks: Lista de chunks del documento
            
        Returns:
            Dict con la estructura del documento
        """
        import re
        
        # Analizar solo los primeros N chunks para detectar estructura (más rápido)
        sample_size = min(20, len(chunks))
        sample_chunks = chunks[:sample_size]
        
        sections = []
        chunk_ranges = []
        
        # Patrones para detectar títulos/secciones
        patterns = [
            # Números con punto: "1. Título", "1.1 Título"
            (r'^(\d+(?:\.\d+)*)\s*[.\-:)]?\s+([A-ZÁÉÍÓÚÑ][^\n]{3,100})$', 'numbered'),
            # Capítulos: "CAPÍTULO 1", "CHAPTER 1"
            (r'^(CAP[ÍI]TULO|CHAPTER)\s+(\d+)[:\s]+([^\n]{3,100})$', 'chapter'),
            # Secciones: "SECCIÓN 1", "SECTION 1"
            (r'^(SECCI[ÓO]N|SECTION)\s+(\d+)[:\s]+([^\n]{3,100})$', 'section'),
            # Anexos: "ANEXO A", "APPENDIX A"
            (r'^(ANEXO|AP[ÉE]NDICE|APPENDIX)\s+([A-Z\d]+)[:\s]+([^\n]{3,100})$', 'appendix'),
            # Títulos en mayúsculas (al menos 5 palabras)
            (r'^([A-ZÁÉÍÓÚÑ\s]{10,80})$', 'title'),
        ]
        
        compiled_patterns = [(re.compile(p, re.MULTILINE | re.IGNORECASE), t) for p, t in patterns]
        
        section_counter = 0
        
        # Analizar chunks de muestra
        for chunk_idx, chunk in enumerate(sample_chunks):
            content = chunk['_source'].get('content', '')
            chunk_id = chunk['_source'].get('chunk_id', chunk_idx)
            
            lines = content.split('\n')
            
            for line in lines[:50]:  # Solo primeras 50 líneas de cada chunk
                line = line.strip()
                if len(line) < 5:
                    continue
                
                # Intentar match con cada patrón
                for pattern, section_type in compiled_patterns:
                    match = pattern.match(line)
                    if match:
                        section_counter += 1
                        
                        # Extraer título
                        if section_type == 'numbered':
                            section_num = match.group(1)
                            title = f"{section_num}. {match.group(2)}"
                            level = section_num.count('.') + 1
                        elif section_type in ['chapter', 'section', 'appendix']:
                            title = line
                            level = 1
                        else:  # title
                            title = line
                            level = 1
                        
                        sections.append({
                            "id": f"section_{section_counter}",
                            "title": title[:100],  # Limitar longitud
                            "level": level,
                            "chunk_start": chunk_id,
                            "chunk_end": chunk_id,  # Se actualizará si es necesario
                            "type": section_type
                        })
                        break
        
        # Crear rangos de chunks sugeridos
        total_chunks = len(chunks)
        chunk_ranges = [
            {
                "description": "Inicio del documento (primeros 10 chunks)",
                "chunk_start": 1,
                "chunk_end": min(10, total_chunks),
                "estimated_chars": sum(len(chunks[i]['_source'].get('content', '')) for i in range(min(10, total_chunks)))
            },
            {
                "description": "Primera mitad del documento",
                "chunk_start": 1,
                "chunk_end": total_chunks // 2,
                "estimated_chars": sum(len(chunks[i]['_source'].get('content', '')) for i in range(total_chunks // 2))
            },
            {
                "description": "Segunda mitad del documento",
                "chunk_start": total_chunks // 2 + 1,
                "chunk_end": total_chunks,
                "estimated_chars": sum(len(chunks[i]['_source'].get('content', '')) for i in range(total_chunks // 2, total_chunks))
            },
            {
                "description": "Final del documento (últimos 10 chunks)",
                "chunk_start": max(1, total_chunks - 9),
                "chunk_end": total_chunks,
                "estimated_chars": sum(len(chunks[i]['_source'].get('content', '')) for i in range(max(0, total_chunks - 10), total_chunks))
            }
        ]
        
        # Si hay metadata de páginas, agregar rangos por página
        if chunks and 'metadata' in chunks[0]['_source']:
            total_pages = chunks[0]['_source']['metadata'].get('total_pages')
            if total_pages:
                # Estimar chunks por página
                chunks_per_page = total_chunks / total_pages if total_pages > 0 else 1
                
                # Agregar algunos rangos de páginas útiles
                page_ranges = [
                    (1, min(10, total_pages), "Primeras 10 páginas"),
                    (1, min(20, total_pages), "Primeras 20 páginas"),
                    (max(1, total_pages // 2 - 5), min(total_pages, total_pages // 2 + 5), "Páginas centrales"),
                    (max(1, total_pages - 9), total_pages, "Últimas 10 páginas"),
                ]
                
                for start_page, end_page, desc in page_ranges:
                    start_chunk = int((start_page - 1) * chunks_per_page) + 1
                    end_chunk = min(int(end_page * chunks_per_page), total_chunks)
                    
                    chunk_ranges.append({
                        "description": f"{desc} (páginas {start_page}-{end_page})",
                        "chunk_start": start_chunk,
                        "chunk_end": end_chunk,
                        "page_start": start_page,
                        "page_end": end_page,
                        "estimated_chars": sum(len(chunks[i]['_source'].get('content', '')) 
                                             for i in range(max(0, start_chunk-1), min(end_chunk, total_chunks)))
                    })
        
        return {
            "sections": sections if sections else [{
                "id": "section_1",
                "title": "Documento completo (sin estructura detectada)",
                "level": 1,
                "chunk_start": 1,
                "chunk_end": total_chunks,
                "type": "default"
            }],
            "chunk_ranges": chunk_ranges,
            "total_sections_detected": len(sections),
            "analysis_note": f"Estructura analizada desde los primeros {sample_size} chunks de {total_chunks} totales"
        }
    
    def _get_all_chunks(self, file_path: str) -> List[Dict]:
        """Obtiene todos los chunks de un archivo usando scroll"""
        # IMPORTANTE: El file_name en OpenSearch solo contiene el nombre del archivo,
        # no el path completo de S3. Si el usuario proporciona un path completo
        # (ej: "documents/archivo.pdf"), extraemos solo el nombre del archivo.
        if '/' in file_path:
            file_path = file_path.split('/')[-1]  # Tomar solo el nombre del archivo
        
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
    
    def _load_structure_from_s3(self, file_path: str, chunks: List[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Carga la estructura pre-calculada del documento desde S3.
        
        La estructura está almacenada en:
        s3://{bucket}/summaries/{file_hash}.json
        
        Args:
            file_path: Nombre del archivo
            chunks: Lista de chunks del documento (para obtener file_hash)
            
        Returns:
            Dict con la estructura del documento o None si no existe
        """
        try:
            import boto3
            
            # Obtener file_hash desde los chunks (es más confiable que calcular hash del nombre)
            file_hash = None
            if chunks and len(chunks) > 0:
                # Extraer file_hash del chunk_id (formato: app_filehash_chunknum)
                chunk_id = chunks[0]['_id']
                parts = chunk_id.split('_')
                if len(parts) >= 2:
                    # El file_hash está en la segunda parte (después del app_name)
                    file_hash = parts[1]
            
            if not file_hash:
                self.logger.debug(f"No se pudo extraer file_hash de los chunks para {file_path}")
                return None
            
            # Obtener configuración de S3
            s3_config = self.config.get('s3', {})
            bucket_name = s3_config.get('bucket_name')
            summaries_prefix = s3_config.get('summaries_prefix', 'summaries/')
            
            if not bucket_name:
                self.logger.debug("No S3 bucket configured")
                return None
            
            # Construir ruta del archivo de estructura
            structure_key = f"{summaries_prefix.rstrip('/')}/{file_hash}.json"
            
            # Intentar cargar desde S3
            s3_client = boto3.client('s3', region_name=s3_config.get('region_name', 'eu-west-1'))
            response = s3_client.get_object(Bucket=bucket_name, Key=structure_key)
            
            # Parsear JSON
            structure_data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Verificar que tenga el campo 'document_structure'
            if 'document_structure' in structure_data:
                self.logger.info(f"✅ Estructura cargada desde S3: {structure_key}")
                return structure_data['document_structure']
            
            self.logger.debug(f"El resumen en S3 no contiene 'document_structure': {structure_key}")
            return None
            
        except Exception as e:
            self.logger.debug(f"No se pudo cargar estructura desde S3 para {file_path}: {str(e)}")
            return None
    
    def _format_structure_response(self, file_path: str, chunks: List[Dict],
                                   structure: Dict[str, Any], include_metadata: bool) -> Dict[str, Any]:
        """
        Formatea la respuesta con estructura pre-calculada desde S3.
        
        Args:
            file_path: Nombre del archivo
            chunks: Lista de chunks del documento
            structure: Estructura pre-calculada
            include_metadata: Si incluir metadatos
            
        Returns:
            Dict con la respuesta formateada
        """
        # OPTIMIZACIÓN: Usar file_size de metadata en lugar de calcular iterando chunks
        # Esto evita procesar todo el contenido de los chunks
        total_length = 0
        if chunks and chunks[0]['_source'].get('metadata'):
            total_length = chunks[0]['_source']['metadata'].get('file_size', 0)
        
        # Fallback: si no hay metadata, calcular (pero esto debería ser raro)
        if total_length == 0:
            total_length = sum(len(chunk['_source'].get('content', '')) for chunk in chunks)
        
        result = {
            "file_path": file_path,
            "access_mode": "progressive",
            "total_chunks": len(chunks),
            "content_length": total_length,
            "structure": structure,
            "message": (
                f"📄 Este archivo es grande ({total_length:,} caracteres, {len(chunks)} chunks). "
                f"Se proporciona la estructura del documento (pre-calculada) para acceso eficiente.\n\n"
                f"💡 Usa la herramienta 'get_file_section' para obtener secciones específicas por:\n"
                f"   • Rango de chunks (ej: chunks 1-10)\n"
                f"   • Rango de páginas (ej: páginas 5-15)\n"
                f"   • ID de sección (ej: section_3)"
            ),
            "available_sections": structure.get("sections", []),
            "chunk_ranges": structure.get("chunk_ranges", []),
            "recommendation": (
                "1. Revisa la estructura y tabla de contenidos\n"
                "2. Identifica las secciones relevantes para tu consulta\n"
                "3. Usa get_file_section para obtener el contenido específico"
            ),
            "structure_source": "s3_precalculated"
        }
        
        # Incluir metadata si se solicita
        if include_metadata and chunks:
            result["metadata"] = chunks[0]['_source'].get('metadata', {})
            result["file_info"] = {
                "first_chunk_id": chunks[0]['_source'].get('chunk_id'),
                "last_chunk_id": chunks[-1]['_source'].get('chunk_id'),
                "file_extension": chunks[0]['_source'].get('metadata', {}).get('file_extension'),
                "file_size": chunks[0]['_source'].get('metadata', {}).get('file_size'),
                "total_pages": chunks[0]['_source'].get('metadata', {}).get('total_pages')
            }
        
        return result
    
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
