#!/usr/bin/env python3
"""
Script de prueba para depurar el acceso progresivo a archivos grandes
"""

import sys
import os

# Agregar el directorio raíz y src al path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, project_root)
sys.path.insert(0, src_dir)
sys.path.insert(0, os.path.join(src_dir, 'tools'))
sys.path.insert(0, os.path.join(src_dir, 'agent'))

from tool_get_file_content import GetFileContent
from request_handler import RequestHandler
import logging

# Configurar logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_large_file_formatting():
    """Prueba el formateo de archivos grandes"""
    print("="*80)
    print("TEST: Formateo de archivo grande en modo progresivo")
    print("="*80)
    
    # Crear herramienta
    tool = GetFileContent(config_path="config/config_darwin.yaml")
    
    # Buscar un archivo grande en el proyecto
    test_file = "src/agent/request_handler.py"  # Este archivo es grande
    
    print(f"\n1. Obteniendo contenido de: {test_file}")
    result = tool.get_content(file_path=test_file)
    
    print(f"\n2. Resultado de get_content:")
    print(f"   - Tipo: {type(result)}")
    print(f"   - Keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
    
    if 'access_mode' in result:
        print(f"   - access_mode: {result['access_mode']}")
        print(f"   - content_length: {result.get('content_length', 'N/A')}")
        
        if result['access_mode'] == 'progressive':
            print(f"\n3. ✅ Modo progresivo detectado correctamente")
            print(f"   - Estructura disponible: {'structure' in result}")
            print(f"   - Secciones disponibles: {'available_sections' in result}")
            print(f"   - Rangos de chunks: {'chunk_ranges' in result}")
            
            # Simular el formateo que hace request_handler
            print(f"\n4. Simulando formateo en _format_file_content:")
            handler = RequestHandler(config_path="config/config_darwin.yaml")
            formatted = handler._format_file_content(result)
            
            print(f"\n5. Resultado del formateo:")
            print(f"   - Longitud: {len(formatted)} caracteres")
            print(f"   - Contiene 'ESTRUCTURA DEL DOCUMENTO': {'ESTRUCTURA DEL DOCUMENTO' in formatted}")
            print(f"   - Contiene 'Secciones disponibles': {'Secciones disponibles' in formatted}")
            print(f"   - Contiene 'tool_get_file_section': {'tool_get_file_section' in formatted}")
            
            print(f"\n6. Vista previa del mensaje formateado (primeros 500 caracteres):")
            print("-"*80)
            print(formatted[:500])
            print("-"*80)
            
            print(f"\n✅ TEST COMPLETADO - El formateo parece correcto")
            print(f"   Si el LLM no recibe esto, el problema está en otro lugar del flujo")
        else:
            print(f"\n3. ⚠️  Modo completo (archivo pequeño)")
    else:
        print(f"\n3. ❌ ERROR: No se encontró 'access_mode' en el resultado")

if __name__ == "__main__":
    test_large_file_formatting()
