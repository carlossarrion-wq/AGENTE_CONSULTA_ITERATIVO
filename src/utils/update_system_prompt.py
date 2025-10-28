#!/usr/bin/env python3
"""
Script para actualizar el system prompt reemplazando la sección estática
de documentos disponibles con el marcador dinámico {{DYNAMIC_SUMMARIES}}
"""

import os
from pathlib import Path

def update_system_prompt():
    """Actualiza el system prompt con el marcador dinámico"""
    
    # Obtener la ruta raíz del proyecto (2 niveles arriba desde este script)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    prompt_file = project_root / 'config' / 'system_prompt_darwin.md'
    
    # Leer el archivo original
    with open(prompt_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Encontrar las líneas de inicio y fin de la sección a reemplazar
    start_line = None
    end_line = None
    
    for i, line in enumerate(lines):
        if '### Archivos Indexados Disponibles' in line:
            start_line = i
        if start_line is not None and line.strip() == '---' and i > start_line + 10:
            end_line = i
            break
    
    if start_line is None or end_line is None:
        print("❌ No se pudo encontrar la sección a reemplazar")
        return False
    
    print(f"📍 Sección encontrada: líneas {start_line + 1} a {end_line}")
    print(f"   Total de líneas a reemplazar: {end_line - start_line}")
    
    # Crear el nuevo contenido
    new_content = lines[:start_line]
    
    # Agregar el marcador dinámico
    new_content.append("{{DYNAMIC_SUMMARIES}}\n")
    new_content.append("\n")
    
    # Agregar el resto del archivo (desde la línea ---)
    new_content.extend(lines[end_line:])
    
    # Escribir el archivo actualizado
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.writelines(new_content)
    
    print("✅ System prompt actualizado correctamente")
    print(f"   Marcador {{{{DYNAMIC_SUMMARIES}}}} insertado en línea {start_line + 1}")
    print(f"   Líneas eliminadas: {end_line - start_line - 2}")
    
    return True


if __name__ == "__main__":
    success = update_system_prompt()
    exit(0 if success else 1)
