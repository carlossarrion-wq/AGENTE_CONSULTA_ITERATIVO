#!/usr/bin/env python3
"""
Herramienta para obtener secciones específicas de documentos grandes.
Permite acceso progresivo a contenido de archivos PDF, DOCX, etc.
"""

import argparse
import json
import sys
from typing import Dict, Any, Optional
from pathlib import Path
import logging

# Importar el analizador de estructura
from document_structure_analyzer import DocumentStructureAnalyzer, DocumentStructure

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
    """Clase para obtener secciones específicas de documentos"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.analyzer = DocumentStructureAnalyzer()
    
    def get_section(
        self,
        file_path: str,
        section_id: str,
        include_context: bool = False
    ) -> Dict[str, Any]:
        """
        Obtiene el contenido de una sección específica de un documento.
        
        Args:
            file_path: Ruta al archivo
            section_id: ID de la sección (ej: "section_2", "section_2.1")
            include_context: Incluir información de contexto (padre, hermanos)
            
        Returns:
            Dict con el contenido de la sección y metadatos
        """
        try:
            # Verificar que el archivo existe
            if not Path(file_path).exists():
                return {
                    "error": f"Archivo no encontrado: {file_path}",
                    "file_path": file_path
                }
            
            # Analizar estructura del documento
            self.logger.info(f"Analizando estructura de: {file_path}")
            structure = self.analyzer.analyze(file_path)
            
            # Buscar la sección solicitada
            section = structure.get_section_by_id(section_id)
            
            if not section:
                available_sections = [s.id for s in structure.sections[:10]]
                return {
                    "error": f"Sección no encontrada: {section_id}",
                    "file_path": file_path,
                    "available_sections": available_sections,
                    "total_sections": len(structure.sections)
                }
            
            # Extraer contenido de la sección
            self.logger.info(f"Extrayendo contenido de sección: {section_id}")
            content = self._extract_section_content(file_path, section, structure)
            
            # Preparar respuesta
            result = {
                "file_path": file_path,
                "file_name": structure.file_name,
                "section": {
                    "id": section.id,
                    "title": section.title,
                    "level": section.level,
                    "content": content,
                    "pages": f"{section.start_page}-{section.end_page}",
                    "chars": len(content)
                }
            }
            
            # Agregar contexto si se solicita
            if include_context:
                result["context"] = self._get_section_context(section, structure)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error obteniendo sección: {e}")
            return {
                "error": str(e),
                "file_path": file_path,
                "section_id": section_id
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
