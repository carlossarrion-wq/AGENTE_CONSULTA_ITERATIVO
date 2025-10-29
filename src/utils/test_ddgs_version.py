#!/usr/bin/env python3
"""
Script para diagnosticar problemas con duckduckgo-search
"""

import sys

print("=" * 80)
print("DIAGNÓSTICO DE DUCKDUCKGO-SEARCH")
print("=" * 80)

# 1. Verificar si está instalado
try:
    import duckduckgo_search
    print(f"✅ duckduckgo-search está instalado")
    print(f"   Versión: {duckduckgo_search.__version__ if hasattr(duckduckgo_search, '__version__') else 'desconocida'}")
except ImportError as e:
    print(f"❌ duckduckgo-search NO está instalado: {e}")
    sys.exit(1)

# 2. Verificar qué clases están disponibles
print("\n📦 Clases disponibles:")
for attr in dir(duckduckgo_search):
    if not attr.startswith('_'):
        print(f"   - {attr}")

# 3. Intentar importar DDGS
print("\n🔍 Intentando importar DDGS...")
try:
    from duckduckgo_search import DDGS
    print("✅ DDGS importado correctamente")
    
    # 4. Verificar firma del constructor
    import inspect
    sig = inspect.signature(DDGS.__init__)
    print(f"\n📝 Firma del constructor DDGS.__init__:")
    print(f"   {sig}")
    
    # 5. Intentar crear instancia
    print("\n🧪 Intentando crear instancia DDGS()...")
    try:
        ddgs = DDGS()
        print("✅ DDGS() creado sin parámetros")
    except TypeError as e:
        print(f"❌ DDGS() falló: {e}")
        
        # Intentar con timeout
        print("\n🧪 Intentando DDGS(timeout=20)...")
        try:
            ddgs = DDGS(timeout=20)
            print("✅ DDGS(timeout=20) creado")
        except TypeError as e2:
            print(f"❌ DDGS(timeout=20) falló: {e2}")
    
    # 6. Verificar métodos disponibles
    if 'ddgs' in locals():
        print("\n📋 Métodos disponibles en instancia DDGS:")
        for method in dir(ddgs):
            if not method.startswith('_') and callable(getattr(ddgs, method)):
                print(f"   - {method}")
                
except ImportError as e:
    print(f"❌ No se pudo importar DDGS: {e}")

print("\n" + "=" * 80)
print("FIN DEL DIAGNÓSTICO")
print("=" * 80)
