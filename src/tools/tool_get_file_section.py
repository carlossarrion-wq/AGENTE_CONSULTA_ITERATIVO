#!/usr/bin/env python3
"""
Herramienta para obtener secciones específicas de documentos grandes.
Permite acceso progresivo a contenido de archivos en OpenSearch/S3.
"""

import argparse
import json
import sys
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

# Importar dependencias de OpenSearch
from common.common import Config, OpenSearchClient
import boto3

# Importar el analizador de estructura
from tools.document_structure_analyzer import DocumentStructureAnalyzer, DocumentStructure

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class GetFileSection:
    """Clase para obtener secciones específicas de documentos desde OpenSearch/S3"""
    
    def __init__(self, config_path: str = "config/config.yaml", app_name: str = None):
        self.logger = logging.getLogger(__name__)
        self.analyzer = DocumentStructureAnalyzer()
        
        # Cargar configuración
        self.config = Config(config_path)
        self.app_name = app_name or self.config.config.get('app', {}).get('name', 'darwin')
        
        # Inicializar clientes
        opensearch_client_obj = OpenSearchClient(self.config)
        self.opensearch_client = opensearch_client_obj.get_client()
        
        # Inicializar cliente S3
        self.s3_client = boto3.client('s3')
        
        # Configuración de OpenSearch
        opensearch_config = self.config.config.get('opensearch', {})
        self.index_name = opensearch_config.get('index_name', f'{self.app_name}_knowledge_base')
        
        # Configuración de S3
        s3_config = self.config.config.get('s3', {})
        self.bucket_name = s3_config.get('bucket_name', f'{self.app_name}-knowledge-base')
        self.summaries_prefix = s3_config.get('summaries_prefix', 'summaries/')
        
        self.logger.info(f"GetFileSection inicializado para app: {self.app_name}")
        self.logger.info(f"  - Index: {self.index_name}")
        self.logger.info(f"  - Bucket: {self.bucket_name}")
    
    def get_section(
        self,
        file_path: str,
        section_id: str,
        include_context: bool = False
    ) -> Dict[str, Any]:
        """
        Obtiene el contenido de una sección específica de un documento desde OpenSearch/S3.
        
        Args:
            file_path: Nombre del archivo (se truncará si contiene path)
            section_id: ID de la sección (ej: "section_1", "chunk_1-5")
            include_context: Incluir información de contexto
            
        Returns:
            Dict con el contenido de la sección y metadatos
        """
        try:
            # Normalizar file_path (extraer solo el nombre del archivo)
            if '/' in file_path:
                file_path = file_path.split('/')[-1]
            
            self.logger.info(f"Obteniendo sección {section_id} de archivo: {file_path}")
            
            # OPTIMIZACIÓN: Si se solicita un rango de chunks, ir directamente a la query optimizada
            # sin descargar todos los chunks del archivo
            if section_id.startswith('chunk_'):
                self.logger.info(f"🚀 Detectado rango de chunks, usando acceso directo optimizado")
                # Formato: chunk_1-5 (rango de chunks)
                # Usar query optimizada directamente sin descargar todos los chunks
                content = self._extract_chunk_range(None, section_id, file_path)
                
                if "error" in content:
                    return content
                
                # Preparar respuesta
                result = {
                    "file_path": file_path,
                    "section_id": section_id,
                    "content": content["text"],
                    "chars": len(content["text"]),
                    "chunks_used": content.get("chunks_used", [])
                }
                
                return result
            
            # Para secciones jerárquicas, necesitamos la estructura completa
            # Obtener chunks del archivo desde OpenSearch
            chunks = self._get_chunks_from_opensearch(file_path)
            
            if not chunks:
                return {
                    "error": f"No se encontraron chunks para el archivo: {file_path}",
                    "file_path": file_path
                }
            
            # Intentar cargar estructura desde S3 (ahora que tenemos chunks)
            structure = self._load_structure_from_s3(file_path, chunks)
            
            # Si no hay estructura en S3, crear una estructura básica desde los chunks
            if not structure:
                self.logger.info(f"No hay estructura en S3, usando estructura básica para: {file_path}")
                structure = self._create_basic_structure(chunks)
            
            # Extraer contenido según el tipo de section_id
            if section_id.startswith('section_'):
                # Formato: section_1, section_2.1 (sección jerárquica)
                content = self._extract_section_by_id(chunks, structure, section_id)
            else:
                return {
                    "error": f"Formato de section_id no válido: {section_id}",
                    "file_path": file_path,
                    "valid_formats": ["chunk_1-5", "section_1", "section_2.1"]
                }
            
            if "error" in content:
                return content
            
            # Preparar respuesta
            result = {
                "file_path": file_path,
                "section_id": section_id,
                "content": content["text"],
                "chars": len(content["text"]),
                "chunks_used": content.get("chunks_used", [])
            }
            
            # Agregar contexto si se solicita
            if include_context and "section_info" in content:
                result["context"] = content["section_info"]
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error obteniendo sección: {e}", exc_info=True)
            return {
                "error": str(e),
                "file_path": file_path,
                "section_id": section_id
            }
    
    def _load_structure_from_s3(self, file_path: str, chunks: List[Dict] = None) -> Optional[Dict]:
        """
        Carga la estructura pre-calculada desde S3.
        Usa el mismo método que tool_get_file_content.py
        """
        try:
            # Obtener file_hash desde los chunks (igual que en tool_get_file_content)
            file_hash = None
            if chunks and len(chunks) > 0:
                # El primer chunk tiene el file_hash en su estructura
                # Intentar extraerlo del metadata o del chunk_id
                first_chunk = chunks[0]
                
                # Opción 1: Desde metadata
                if 'file_hash' in first_chunk:
                    file_hash = first_chunk['file_hash']
                # Opción 2: Desde chunk_id (formato: app_filehash_chunknum)
                elif 'chunk_id' in first_chunk:
                    chunk_id_str = str(first_chunk['chunk_id'])
                    parts = chunk_id_str.split('_')
                    if len(parts) >= 2:
                        file_hash = parts[1]
            
            if not file_hash:
                self.logger.debug(f"No se pudo extraer file_hash para {file_path}")
                return None
            
            # Construir key de S3 (igual que en tool_get_file_content)
            structure_key = f"{self.summaries_prefix.rstrip('/')}/{file_hash}.json"
            
            self.logger.debug(f"Cargando estructura desde S3: {structure_key}")
            
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=structure_key
            )
            
            # Parsear JSON
            structure_data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Verificar que tenga el campo 'document_structure'
            if 'document_structure' in structure_data:
                self.logger.info(f"✅ Estructura cargada desde S3: {structure_key}")
                return structure_data['document_structure']
            
            self.logger.debug(f"El resumen en S3 no contiene 'document_structure': {structure_key}")
            return None
            
        except self.s3_client.exceptions.NoSuchKey:
            self.logger.debug(f"Estructura no encontrada en S3 para {file_path}")
            return None
        except Exception as e:
            self.logger.debug(f"Error cargando estructura desde S3: {e}")
            return None
    
    def _create_basic_structure(self, chunks: List[Dict]) -> Dict[str, Any]:
        """
        Crea una estructura básica del documento cuando no hay estructura en S3.
        Divide el documento en secciones de ~5 chunks cada una para permitir acceso granular.
        
        Args:
            chunks: Lista de chunks del documento
            
        Returns:
            Dict con estructura básica dividida en secciones
        """
        total_chunks = len(chunks)
        chunks_per_section = 5  # Dividir en secciones de 5 chunks
        
        sections = []
        section_num = 1
        
        # Crear secciones dividiendo el documento
        for start_chunk in range(1, total_chunks + 1, chunks_per_section):
            end_chunk = min(start_chunk + chunks_per_section - 1, total_chunks)
            
            sections.append({
                "id": f"section_{section_num}",
                "title": f"Sección {section_num} (chunks {start_chunk}-{end_chunk})",
                "level": 1,
                "chunk_start": start_chunk,
                "chunk_end": end_chunk,
                "type": "auto_generated"
            })
            section_num += 1
        
        # Crear rangos de chunks sugeridos
        chunk_ranges = []
        for section in sections:
            chunk_ranges.append({
                "description": section["title"],
                "chunk_start": section["chunk_start"],
                "chunk_end": section["chunk_end"]
            })
        
        return {
            "sections": sections,
            "chunk_ranges": chunk_ranges,
            "total_sections_detected": len(sections),
            "analysis_note": f"Estructura básica generada: {len(sections)} secciones de ~{chunks_per_section} chunks (sin estructura pre-calculada en S3)"
        }
    
    def _get_chunks_from_opensearch(self, file_path: str) -> List[Dict]:
        """Obtiene todos los chunks de un archivo desde OpenSearch"""
        try:
            # Normalizar nombre del archivo
            normalized_path = ' '.join(file_path.split())
            
            # Buscar chunks usando scroll para obtener todos
            query = {
                "query": {
                    "bool": {
                        "should": [
                            {"term": {"file_name.keyword": file_path}},
                            {"term": {"file_name.keyword": normalized_path}},
                            {"match_phrase": {"file_name": file_path}}
                        ],
                        "minimum_should_match": 1
                    }
                },
                "sort": [{"chunk_index": "asc"}],
                "size": 1000  # Máximo por página
            }
            
            response = self.opensearch_client.search(
                index=self.index_name,
                body=query,
                scroll='2m'
            )
            
            chunks = []
            scroll_id = response['_scroll_id']
            hits = response['hits']['hits']
            
            while hits:
                for hit in hits:
                    chunks.append(hit['_source'])
                
                # Obtener siguiente página
                response = self.opensearch_client.scroll(
                    scroll_id=scroll_id,
                    scroll='2m'
                )
                hits = response['hits']['hits']
            
            # Limpiar scroll
            self.opensearch_client.clear_scroll(scroll_id=scroll_id)
            
            self.logger.info(f"✅ Obtenidos {len(chunks)} chunks de OpenSearch")
            return chunks
            
        except Exception as e:
            self.logger.error(f"Error obteniendo chunks de OpenSearch: {e}")
            return []
    
    def _get_chunks_in_range(self, file_path: str, start_index: int, end_index: int) -> List[Dict]:
        """
        Obtiene solo los chunks en un rango específico desde OpenSearch.
        OPTIMIZADO: Filtra directamente en la query en lugar de descargar todos los chunks.
        
        Args:
            file_path: Nombre del archivo
            start_index: Índice inicial del chunk (inclusive)
            end_index: Índice final del chunk (inclusive)
            
        Returns:
            Lista de chunks en el rango especificado
        """
        try:
            # Normalizar nombre del archivo
            normalized_path = ' '.join(file_path.split())
            
            # Query optimizada: filtra por file_name Y por rango de chunk_index
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "bool": {
                                    "should": [
                                        {"term": {"file_name.keyword": file_path}},
                                        {"term": {"file_name.keyword": normalized_path}},
                                        {"match_phrase": {"file_name": file_path}}
                                    ],
                                    "minimum_should_match": 1
                                }
                            },
                            {
                                "range": {
                                    "chunk_index": {
                                        "gte": start_index,
                                        "lte": end_index
                                    }
                                }
                            }
                        ]
                    }
                },
                "sort": [{"chunk_index": "asc"}],
                "size": max(100, end_index - start_index + 1)  # Tamaño suficiente para el rango
            }
            
            response = self.opensearch_client.search(
                index=self.index_name,
                body=query
            )
            
            chunks = [hit['_source'] for hit in response['hits']['hits']]
            
            self.logger.info(f"✅ Obtenidos {len(chunks)} chunks en rango [{start_index}-{end_index}] de OpenSearch")
            return chunks
            
        except Exception as e:
            self.logger.error(f"Error obteniendo chunks en rango de OpenSearch: {e}")
            return []
    
    def _extract_chunk_range(self, chunks: List[Dict], section_id: str, file_path: str = None) -> Dict[str, Any]:
        """
        Extrae contenido de un rango de chunks (ej: chunk_1-5).
        OPTIMIZADO: Si file_path está disponible, obtiene chunks directamente desde OpenSearch.
        """
        try:
            # Parsear rango: chunk_1-5
            range_part = section_id.replace('chunk_', '')
            start, end = map(int, range_part.split('-'))
            
            # OPTIMIZACIÓN: Si tenemos file_path, obtener chunks directamente desde OpenSearch
            # en lugar de filtrar todos los chunks en memoria
            if file_path:
                self.logger.info(f"🚀 Usando query optimizada para obtener chunks {start}-{end}")
                selected_chunks = self._get_chunks_in_range(file_path, start, end)
            else:
                # Fallback: Filtrar chunks en memoria (método antiguo)
                self.logger.info(f"⚠️  Filtrando chunks en memoria (método no optimizado)")
                selected_chunks = [c for c in chunks if start <= c.get('chunk_index', 0) <= end]
                selected_chunks.sort(key=lambda x: x.get('chunk_index', 0))
            
            if not selected_chunks:
                return {
                    "error": f"No se encontraron chunks en el rango {start}-{end}",
                    "total_chunks": len(chunks) if chunks else 0
                }
            
            # Concatenar contenido
            content = "\n\n".join([c.get('content', '') for c in selected_chunks])
            
            return {
                "text": content,
                "chunks_used": [c.get('chunk_index') for c in selected_chunks]
            }
            
        except ValueError as e:
            return {
                "error": f"Formato de rango inválido: {section_id}. Use formato chunk_1-5",
                "example": "chunk_1-5"
            }
    
    def _extract_section_by_id(self, chunks: List[Dict], structure: Dict, section_id: str) -> Dict[str, Any]:
        """Extrae contenido de una sección jerárquica (ej: section_1, section_2.1)"""
        try:
            # Buscar sección en la estructura
            sections = structure.get('sections', [])
            section_info = None
            
            for section in sections:
                if section.get('id') == section_id:
                    section_info = section
                    break
            
            if not section_info:
                available = [s.get('id') for s in sections[:10]]
                return {
                    "error": f"Sección no encontrada: {section_id}",
                    "available_sections": available,
                    "total_sections": len(sections)
                }
            
            # Obtener rango de chunks de la sección
            chunk_start = section_info.get('chunk_start', 1)
            chunk_end = section_info.get('chunk_end', chunk_start)
            
            # Filtrar chunks
            selected_chunks = [c for c in chunks if chunk_start <= c.get('chunk_index', 0) <= chunk_end]
            selected_chunks.sort(key=lambda x: x.get('chunk_index', 0))
            
            # Concatenar contenido
            content = "\n\n".join([c.get('content', '') for c in selected_chunks])
            
            return {
                "text": content,
                "chunks_used": [c.get('chunk_index') for c in selected_chunks],
                "section_info": {
                    "title": section_info.get('title', ''),
                    "level": section_info.get('level', 0),
                    "pages": f"{section_info.get('start_page', '')}-{section_info.get('end_page', '')}"
                }
            }
            
        except Exception as e:
            return {
                "error": f"Error extrayendo sección: {str(e)}"
            }
    
    def _extract_section_content(
        self,
        file_path: str,
        section: Any,
        structure: DocumentStructure
    ) -> str:
        """Extrae el contenido de una sección específica"""
        
        file_type = Path(file_path).suffix.lower()
        
        if file_type == '.pdf':
            return self._extract_pdf_section(file_path, section)
        elif file_type in ['.docx', '.doc']:
            return self._extract_docx_section(file_path, section)
        elif file_type in ['.txt', '.md']:
            return self._extract_text_section(file_path, section)
        else:
            raise ValueError(f"Formato no soportado: {file_type}")
    
    def _extract_pdf_section(self, file_path: str, section: Any) -> str:
        """Extrae contenido de una sección de PDF"""
        if not PDF_AVAILABLE:
            raise ImportError("PyPDF2 no está instalado")
        
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Si tenemos información de caracteres, usar eso
            if section.start_char is not None and section.end_char is not None:
                # Extraer todo el texto
                full_text = ""
                for page in reader.pages:
                    full_text += page.extract_text() + "\n"
                
                # Retornar la sección específica
                return full_text[section.start_char:section.end_char]
            
            # Si solo tenemos páginas, extraer por páginas
            else:
                content = ""
                start_page = section.start_page - 1  # PyPDF2 usa índice 0
                end_page = section.end_page
                
                for page_num in range(start_page, min(end_page, len(reader.pages))):
                    content += reader.pages[page_num].extract_text() + "\n"
                
                return content
    
    def _extract_docx_section(self, file_path: str, section: Any) -> str:
        """Extrae contenido de una sección de DOCX"""
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx no está instalado")
        
        doc = DocxDocument(file_path)
        
        # Extraer texto completo
        full_text = "\n".join([para.text for para in doc.paragraphs])
        
        # Usar posiciones de caracteres si están disponibles
        if section.start_char is not None and section.end_char is not None:
            return full_text[section.start_char:section.end_char]
        
        # Fallback: retornar todo el texto
        return full_text
    
    def _extract_text_section(self, file_path: str, section: Any) -> str:
        """Extrae contenido de una sección de archivo de texto"""
        with open(file_path, 'r', encoding='utf-8') as f:
            full_text = f.read()
        
        if section.start_char is not None and section.end_char is not None:
            return full_text[section.start_char:section.end_char]
        
        return full_text
    
    def _get_section_context(
        self,
        section: Any,
        structure: DocumentStructure
    ) -> Dict[str, Any]:
        """Obtiene información de contexto de una sección"""
        context = {}
        
        # Buscar sección padre
        if section.parent_id:
            parent = structure.get_section_by_id(section.parent_id)
            if parent:
                context["parent"] = {
                    "id": parent.id,
                    "title": parent.title,
                    "level": parent.level
                }
        
        # Buscar secciones hermanas (mismo nivel y mismo padre)
        siblings = []
        for s in structure.sections:
            if (s.level == section.level and 
                s.parent_id == section.parent_id and 
                s.id != section.id):
                siblings.append({
                    "id": s.id,
                    "title": s.title
                })
        
        if siblings:
            context["siblings"] = siblings[:5]  # Limitar a 5 hermanos
        
        # Buscar subsecciones
        children = []
        for s in structure.sections:
            if s.parent_id == section.id:
                children.append({
                    "id": s.id,
                    "title": s.title,
                    "level": s.level
                })
        
        if children:
            context["children"] = children
        
        return context


def main():
    """Función principal para uso desde línea de comandos"""
    parser = argparse.ArgumentParser(
        description="Obtener sección específica de un documento"
    )
    
    parser.add_argument(
        "file_path",
        help="Ruta al archivo"
    )
    
    parser.add_argument(
        "section_id",
        help="ID de la sección a obtener (ej: section_2, section_2.1)"
    )
    
    parser.add_argument(
        "--include-context",
        action="store_true",
        help="Incluir información de contexto (padre, hermanos, hijos)"
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
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Crear instancia de la herramienta
        tool = GetFileSection()
        
        # Obtener sección
        result = tool.get_section(
            file_path=args.file_path,
            section_id=args.section_id,
            include_context=args.include_context
        )
        
        # Guardar en archivo si se especifica
        if args.save_to and "section" in result:
            with open(args.save_to, 'w', encoding='utf-8') as f:
                f.write(result['section']['content'])
            print(f"Contenido guardado en: {args.save_to}")
        
        # Mostrar resultados
        if args.output == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif args.output == "content-only":
            if "section" in result:
                print(result['section']['content'])
            else:
                print(f"Error: {result.get('error', 'Contenido no disponible')}", 
                      file=sys.stderr)
        else:
            print_pretty_results(result)
            
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def print_pretty_results(result: Dict[str, Any]):
    """Imprime los resultados en formato legible"""
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        if "available_sections" in result:
            print(f"\n📋 Secciones disponibles (primeras 10 de {result['total_sections']}):")
            for section_id in result['available_sections']:
                print(f"   • {section_id}")
        return
    
    section = result['section']
    
    print("\n" + "=" * 80)
    print(f"📄 Archivo: {result['file_name']}")
    print("=" * 80)
    print(f"\n📌 Sección: {section['id']}")
    print(f"📝 Título: {section['title']}")
    print(f"📊 Nivel: {section['level']}")
    print(f"📄 Páginas: {section['pages']}")
    print(f"📏 Caracteres: {section['chars']:,}")
    
    # Mostrar contexto si está disponible
    if "context" in result:
        context = result['context']
        print("\n" + "-" * 80)
        print("🔗 CONTEXTO")
        print("-" * 80)
        
        if "parent" in context:
            parent = context['parent']
            print(f"\n⬆️  Sección padre:")
            print(f"   {parent['id']}: {parent['title']}")
        
        if "siblings" in context:
            print(f"\n↔️  Secciones hermanas:")
            for sibling in context['siblings']:
                print(f"   • {sibling['id']}: {sibling['title']}")
        
        if "children" in context:
            print(f"\n⬇️  Subsecciones:")
            for child in context['children']:
                print(f"   • {child['id']}: {child['title']}")
    
    print("\n" + "=" * 80)
    print("📝 CONTENIDO")
    print("=" * 80)
    
    content = section['content']
    if len(content) > 2000:
        print(content[:2000])
        print(f"\n... [Contenido truncado. Total: {len(content):,} caracteres]")
        print("💡 Usa --output content-only para ver el contenido completo")
        print("💡 Usa --save-to archivo.txt para guardar en archivo")
    else:
        print(content)
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
