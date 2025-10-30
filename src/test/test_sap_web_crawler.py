#!/usr/bin/env python3
"""
Test del web crawler en modo permisivo para SAP ISU
"""

import sys
import logging
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from tools.tool_web_crawler import execute_web_crawler

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_sap_search():
    """Test de búsqueda SAP ISU"""
    print("\n" + "="*80)
    print("TEST: Web Crawler - SAP ISU en modo permisivo")
    print("="*80 + "\n")
    
    # Parámetros de búsqueda
    params = {
        'query': 'SAP ISU latest version 2024 2025 release notes',
        'app_name': 'sap'
    }
    
    print(f"📝 Query: {params['query']}")
    print(f"🏢 App: {params['app_name']}")
    print(f"🌐 Sitio esperado: help.sap.com")
    print("\n" + "-"*80 + "\n")
    
    # Ejecutar búsqueda
    result = execute_web_crawler(params)
    
    # Mostrar resultados
    if result.success:
        print(f"✅ ÉXITO - Tiempo: {result.execution_time_ms:.0f}ms\n")
        
        data = result.data
        print(f"📊 Resultados encontrados: {data['results_count']}")
        print(f"🔍 Query procesada: {data['query']}\n")
        
        if 'recommended_urls' in data:
            print("🔗 URLs recomendadas:")
            for rec in data['recommended_urls']:
                print(f"  {rec['number']}. {rec['url']}")
                print(f"     {rec['description']}\n")
        elif 'sources' in data:
            print("📄 Fuentes con contenido:")
            for source in data['sources']:
                print(f"  {source['number']}. {source['url']}")
                print(f"     Método: {source['extraction_method']}")
                print(f"     Contenido: {source['content'][:150]}...\n")
    else:
        print(f"❌ ERROR: {result.error}")
        print(f"⏱️  Tiempo: {result.execution_time_ms:.0f}ms")
    
    print("\n" + "="*80 + "\n")
    
    return result.success

if __name__ == "__main__":
    success = test_sap_search()
    sys.exit(0 if success else 1)
