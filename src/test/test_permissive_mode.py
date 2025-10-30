#!/usr/bin/env python3
"""
Script de prueba para verificar el modo permisivo del web crawler
"""

import sys
import logging
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from tools.tool_web_crawler import WebCrawlerTool

def test_permissive_mode():
    """Prueba el modo permisivo con diferentes queries"""
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 80)
    print("TEST: Modo Permisivo del Web Crawler")
    print("=" * 80)
    
    # Crear instancia del tool
    tool = WebCrawlerTool(app_name='mulesoft')
    
    # Test 1: Query sobre MuleSoft (debería funcionar con cualquier dominio)
    print("\n📝 Test 1: Búsqueda sobre MuleSoft latest version")
    print("-" * 80)
    
    result = tool.search_and_extract("MuleSoft latest version Mule Runtime current release")
    
    if result.success:
        print(f"✅ Éxito: {result.data['results_count']} URLs encontradas")
        print(f"⏱️  Tiempo: {result.execution_time_ms:.0f}ms")
        print("\n📋 URLs recomendadas:")
        for url_info in result.data['recommended_urls']:
            print(f"  {url_info['number']}. {url_info['url']}")
    else:
        print(f"❌ Error: {result.error}")
    
    # Test 2: Query con dominio que antes estaba bloqueado
    print("\n📝 Test 2: Búsqueda que incluiría dominios no oficiales")
    print("-" * 80)
    
    result2 = tool.search_and_extract("MuleSoft API integration best practices tutorial")
    
    if result2.success:
        print(f"✅ Éxito: {result2.data['results_count']} URLs encontradas")
        print(f"⏱️  Tiempo: {result2.execution_time_ms:.0f}ms")
        print("\n📋 URLs recomendadas:")
        for url_info in result2.data['recommended_urls']:
            print(f"  {url_info['number']}. {url_info['url']}")
    else:
        print(f"❌ Error: {result2.error}")
    
    print("\n" + "=" * 80)
    print("✅ Tests completados")
    print("=" * 80)
    
    # Verificar configuración
    print("\n📊 Configuración actual:")
    print(f"  - Modo permisivo: {tool.domain_whitelist.permissive_mode}")
    print(f"  - Dominios bloqueados: {len(tool.domain_whitelist.blocked_domains)}")
    print(f"  - Max resultados: {tool.max_results}")

if __name__ == "__main__":
    test_permissive_mode()
