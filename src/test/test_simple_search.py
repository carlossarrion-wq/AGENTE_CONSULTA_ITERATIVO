#!/usr/bin/env python3
"""
Test simple del web crawler con búsqueda que seguro devuelve resultados
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

def test_simple_search():
    """Test con búsqueda simple que debería devolver resultados"""
    print("\n" + "="*80)
    print("TEST: Web Crawler - Búsqueda simple de MuleSoft")
    print("="*80 + "\n")
    
    # Búsqueda simple de MuleSoft que debería funcionar
    params = {
        'query': 'MuleSoft runtime latest version',
        'app_name': 'mulesoft'
    }
    
    print(f"📝 Query: {params['query']}")
    print(f"🏢 App: {params['app_name']}")
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

def test_sap_simple():
    """Test con búsqueda simple de SAP"""
    print("\n" + "="*80)
    print("TEST: Web Crawler - Búsqueda simple de SAP")
    print("="*80 + "\n")
    
    # Búsqueda simple de SAP
    params = {
        'query': 'SAP HANA latest features',
        'app_name': 'sap'
    }
    
    print(f"📝 Query: {params['query']}")
    print(f"🏢 App: {params['app_name']}")
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
                url = rec['url']
                # Verificar dominio
                domain = url.split('/')[2] if len(url.split('/')) > 2 else 'unknown'
                print(f"  {rec['number']}. {url}")
                print(f"     Dominio: {domain}")
                print(f"     {rec['description']}\n")
        elif 'sources' in data:
            print("📄 Fuentes con contenido:")
            for source in data['sources']:
                url = source['url']
                domain = url.split('/')[2] if len(url.split('/')) > 2 else 'unknown'
                print(f"  {source['number']}. {url}")
                print(f"     Dominio: {domain}")
                print(f"     Método: {source['extraction_method']}")
                print(f"     Contenido: {source['content'][:150]}...\n")
    else:
        print(f"❌ ERROR: {result.error}")
        print(f"⏱️  Tiempo: {result.execution_time_ms:.0f}ms")
    
    print("\n" + "="*80 + "\n")
    
    return result.success

if __name__ == "__main__":
    print("\n🔍 EJECUTANDO TESTS DE WEB CRAWLER\n")
    
    # Test 1: MuleSoft
    success1 = test_simple_search()
    
    # Test 2: SAP
    success2 = test_sap_simple()
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN DE TESTS")
    print("="*80)
    print(f"Test MuleSoft: {'✅ ÉXITO' if success1 else '❌ FALLO'}")
    print(f"Test SAP: {'✅ ÉXITO' if success2 else '❌ FALLO'}")
    print("="*80 + "\n")
    
    sys.exit(0 if (success1 and success2) else 1)
