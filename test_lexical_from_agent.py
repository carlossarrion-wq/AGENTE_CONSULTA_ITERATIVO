#!/usr/bin/env python3
"""
Test para replicar exactamente cómo el agente ejecuta lexical_search
"""

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from lexical_search import LexicalSearch

def main():
    print("="*80)
    print("TEST: Replicando ejecución del agente")
    print("="*80)
    
    # Crear instancia exactamente como lo hace el agente
    config_path = "config/config.yaml"
    lexical_search = LexicalSearch(config_path)
    
    # Ejecutar búsqueda con los mismos parámetros que usa el agente
    params = {
        'query': 'NU_07',
        'fields': ['content', 'file_name', 'metadata.summary'],
        'operator': 'OR',
        'top_k': 20
    }
    
    print(f"\nParámetros: {params}")
    print("-"*80)
    
    try:
        result = lexical_search.search(**params)
        
        print(f"\n✅ Búsqueda exitosa!")
        print(f"Total de resultados: {result.get('total_results', 0)}")
        
        if result.get('results'):
            print(f"\nPrimeros resultados:")
            for i, item in enumerate(result['results'][:3], 1):
                print(f"\n{i}. {item.get('file_name', 'N/A')}")
                print(f"   Score: {item.get('score', 0):.3f}")
                if item.get('matches'):
                    for match in item['matches'][:2]:
                        print(f"   Match: {match.get('snippet', '')[:100]}...")
        else:
            print("\n⚠️  No se encontraron resultados")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
