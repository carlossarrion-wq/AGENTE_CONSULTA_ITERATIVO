#!/usr/bin/env python3
"""
Script simple para probar el acceso progresivo sin imports complejos
"""

import sys
import os
import json

# Agregar paths
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(project_root, 'src/tools'))
sys.path.insert(0, os.path.join(project_root, 'src/common'))

from tool_get_file_content import GetFileContent

def test_progressive_mode():
    """Prueba el modo progresivo directamente"""
    print("="*80)
    print("TEST: Acceso progresivo a archivo grande")
    print("="*80)
    
    # Crear herramienta
    tool = GetFileContent(config_path="config/config_darwin.yaml")
    
    # Probar con archivo grande
    test_file = "src/agent/request_handler.py"
    
    print(f"\n1. Obteniendo contenido de: {test_file}")
    result = tool.get_content(file_path=test_file)
    
    print(f"\n2. Resultado:")
    print(f"   - Tipo: {type(result)}")
    print(f"   - Keys: {list(result.keys())}")
    
    if 'access_mode' in result:
        print(f"\n3. Modo de acceso: {result['access_mode']}")
        
        if result['access_mode'] == 'progressive':
            print(f"\n✅ MODO PROGRESIVO ACTIVADO")
            print(f"   - Tamaño del archivo: {result.get('content_length', 0):,} caracteres")
            print(f"   - Estructura disponible: {'structure' in result}")
            print(f"   - Secciones disponibles: {result.get('available_sections', 'N/A')}")
            print(f"   - Rangos de chunks: {result.get('chunk_ranges', 'N/A')}")
            
            # Mostrar estructura
            if 'structure' in result:
                print(f"\n4. Estructura del documento:")
                print(json.dumps(result['structure'], indent=2, ensure_ascii=False)[:1000])
                print("...")
            
            # Simular el formateo que haría request_handler
            print(f"\n5. Simulando formateo para el LLM:")
            formatted = f"📄 **Archivo**: {result.get('file_path', 'archivo')}\n"
            formatted += f"⚠️  **Modo de acceso**: PROGRESIVO (archivo grande)\n"
            formatted += f"📏 **Tamaño**: {result.get('content_length', 0):,} caracteres\n\n"
            formatted += f"**Mensaje**: {result.get('message', '')}\n\n"
            
            if 'structure' in result:
                formatted += f"📋 **ESTRUCTURA DEL DOCUMENTO**:\n\n"
                formatted += f"```json\n{json.dumps(result['structure'], indent=2, ensure_ascii=False)}\n```\n\n"
            
            if 'available_sections' in result:
                formatted += f"📑 **Secciones disponibles**: {result['available_sections']}\n\n"
            
            if 'chunk_ranges' in result:
                formatted += f"📊 **Rangos de chunks**: {result['chunk_ranges']}\n\n"
            
            if 'recommendation' in result:
                formatted += f"💡 **Recomendación**: {result['recommendation']}\n\n"
            
            formatted += "**INSTRUCCIÓN**: Analiza la estructura y usa `tool_get_file_section` para obtener las secciones relevantes.\n"
            
            print(f"\n6. Mensaje formateado (longitud: {len(formatted)} caracteres):")
            print("-"*80)
            print(formatted[:800])
            print("...")
            print("-"*80)
            
            print(f"\n✅ TEST COMPLETADO")
            print(f"   El mensaje formateado contiene toda la información necesaria")
            print(f"   Si el LLM no lo recibe, el problema está en el envío al LLM")
            
        else:
            print(f"\n⚠️  Modo completo (archivo pequeño)")
    else:
        print(f"\n❌ ERROR: No se encontró 'access_mode' en el resultado")

if __name__ == "__main__":
    test_progressive_mode()
