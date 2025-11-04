#!/usr/bin/env python3
"""
Script de prueba para el analizador de estructura de documentos.
Permite probar la extracción de estructura de PDFs.
"""

import sys
import os
import json
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.tools.document_structure_analyzer import DocumentStructureAnalyzer
import logging


def test_pdf_structure(pdf_path: str):
    """
    Prueba el análisis de estructura de un PDF específico.
    
    Args:
        pdf_path: Ruta al archivo PDF a analizar
    """
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    print("\n" + "=" * 80)
    print("TEST: ANÁLISIS DE ESTRUCTURA DE DOCUMENTO")
    print("=" * 80)
    
    # Verificar que el archivo existe
    if not os.path.exists(pdf_path):
        print(f"❌ Error: El archivo no existe: {pdf_path}")
        return False
    
    print(f"\n📄 Analizando: {pdf_path}")
    print("-" * 80)
    
    try:
        # Crear analizador
        analyzer = DocumentStructureAnalyzer()
        
        # Analizar documento
        print("\n⏳ Extrayendo estructura del documento...")
        structure = analyzer.analyze(pdf_path)
        
        # Mostrar resultados
        print("\n✅ Análisis completado exitosamente!")
        print("\n" + "=" * 80)
        print("INFORMACIÓN DEL DOCUMENTO")
        print("=" * 80)
        print(f"Nombre: {structure.file_name}")
        print(f"Tipo: {structure.file_type}")
        print(f"Páginas totales: {structure.total_pages}")
        print(f"Caracteres totales: {structure.total_chars:,}")
        print(f"Método de extracción: {structure.extraction_method}")
        print(f"Secciones encontradas: {len(structure.sections)}")
        
        # Mostrar tabla de contenidos
        print("\n" + "=" * 80)
        print("TABLA DE CONTENIDOS")
        print("=" * 80)
        
        if structure.sections:
            for section in structure.sections:
                indent = "  " * (section.level - 1)
                print(f"\n{indent}📌 {section.id}: {section.title}")
                print(f"{indent}   ├─ Nivel: {section.level}")
                print(f"{indent}   ├─ Páginas: {section.start_page} - {section.end_page}")
                if section.char_count:
                    print(f"{indent}   ├─ Caracteres: {section.char_count:,}")
                if section.parent_id:
                    print(f"{indent}   └─ Padre: {section.parent_id}")
        else:
            print("⚠️  No se encontraron secciones en el documento")
        
        # Guardar estructura en JSON
        output_file = f"{pdf_path}.structure.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(structure.to_dict(), f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 80)
        print(f"💾 Estructura guardada en: {output_file}")
        print("=" * 80)
        
        # Mostrar estadísticas adicionales
        print("\n" + "=" * 80)
        print("ESTADÍSTICAS")
        print("=" * 80)
        
        if structure.sections:
            # Calcular estadísticas
            avg_chars = sum(s.char_count or 0 for s in structure.sections) / len(structure.sections)
            max_section = max(structure.sections, key=lambda s: s.char_count or 0)
            min_section = min(structure.sections, key=lambda s: s.char_count or 0)
            
            print(f"Promedio de caracteres por sección: {avg_chars:,.0f}")
            print(f"\nSección más grande:")
            print(f"  • {max_section.title}")
            print(f"  • Caracteres: {max_section.char_count:,}")
            print(f"\nSección más pequeña:")
            print(f"  • {min_section.title}")
            print(f"  • Caracteres: {min_section.char_count:,}")
            
            # Distribución por niveles
            levels = {}
            for section in structure.sections:
                levels[section.level] = levels.get(section.level, 0) + 1
            
            print(f"\nDistribución por niveles:")
            for level in sorted(levels.keys()):
                print(f"  • Nivel {level}: {levels[level]} secciones")
        
        print("\n" + "=" * 80)
        print("✅ TEST COMPLETADO EXITOSAMENTE")
        print("=" * 80 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error durante el análisis: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Función principal"""
    if len(sys.argv) < 2:
        print("\n" + "=" * 80)
        print("USO: python3 test_document_structure.py <ruta_al_pdf>")
        print("=" * 80)
        print("\nEjemplo:")
        print("  python3 src/test/test_document_structure.py /ruta/a/documento.pdf")
        print("\nEste script:")
        print("  1. Analiza la estructura del PDF")
        print("  2. Extrae secciones y tabla de contenidos")
        print("  3. Muestra estadísticas del documento")
        print("  4. Guarda la estructura en formato JSON")
        print("=" * 80 + "\n")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    success = test_pdf_structure(pdf_path)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
