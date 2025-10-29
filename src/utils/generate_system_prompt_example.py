#!/usr/bin/env python3
"""
Script para generar un ejemplo instanciado del system prompt con todos los placeholders reemplazados

Uso:
    python3 src/utils/generate_system_prompt_example.py mulesoft
    python3 src/utils/generate_system_prompt_example.py darwin
    python3 src/utils/generate_system_prompt_example.py sap
"""

import sys
from pathlib import Path


def load_web_crawler_documentation() -> str:
    """Carga la documentación del web crawler desde el archivo"""
    doc_path = Path("config/web_crawler_tool_section.md")
    if not doc_path.exists():
        return ""
    
    with open(doc_path, 'r', encoding='utf-8') as f:
        return f.read()


def generate_system_prompt_example(app_name: str) -> str:
    """
    Genera un ejemplo del system prompt con todos los placeholders reemplazados
    
    Args:
        app_name: Nombre de la aplicación (mulesoft, darwin, sap)
        
    Returns:
        String con el prompt completo
    """
    # Determinar el archivo de system prompt
    prompt_file = f"config/system_prompt_{app_name.lower()}.md"
    prompt_path = Path(prompt_file)
    
    if not prompt_path.exists():
        print(f"❌ Error: Archivo no encontrado: {prompt_file}")
        return ""
    
    # Leer el template del system prompt
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    # Reemplazar {{DYNAMIC_SUMMARIES}} con un ejemplo
    summaries_example = """
## RESÚMENES DE DOCUMENTOS DISPONIBLES

A continuación se listan los resúmenes de los documentos más relevantes indexados en la base de conocimiento:

### 1. "Modelo de Eventos de integración.pdf"
- **Tamaño**: 637 KB
- **Tipo**: PDF
- **Resumen**: Este documento describe la arquitectura de integración event-driven que se implementa en MuleSoft. Incluye patrones de diseño, mejores prácticas y ejemplos de implementación de eventos asíncronos entre sistemas.

### 2. "Guía de Conectores MuleSoft.pdf"
- **Tamaño**: 1.2 MB
- **Tipo**: PDF
- **Resumen**: Documentación completa sobre los conectores disponibles en MuleSoft, incluyendo configuración, parámetros, ejemplos de uso y troubleshooting común.

### 3. "DataWeave Transformations.pdf"
- **Tamaño**: 890 KB
- **Tipo**: PDF
- **Resumen**: Guía de referencia de DataWeave con ejemplos de transformaciones comunes, funciones built-in, y patrones de mapeo de datos.

*Nota: Esta es una lista de ejemplo. En producción, estos resúmenes se cargan dinámicamente desde S3.*
"""
    
    prompt = prompt_template.replace("{{DYNAMIC_SUMMARIES}}", summaries_example)
    
    # Reemplazar {{WEB_CRAWLER_TOOL}} con la documentación real
    web_crawler_doc = load_web_crawler_documentation()
    if web_crawler_doc:
        prompt = prompt.replace("{{WEB_CRAWLER_TOOL}}", web_crawler_doc)
        print(f"✅ Documentación de web_crawler incluida ({len(web_crawler_doc)} caracteres)")
    else:
        prompt = prompt.replace("{{WEB_CRAWLER_TOOL}}", "")
        print(f"ℹ️  Web crawler no disponible o deshabilitado")
    
    return prompt


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 generate_system_prompt_example.py <app_name>")
        print("Ejemplo: python3 generate_system_prompt_example.py mulesoft")
        sys.exit(1)
    
    app_name = sys.argv[1].lower()
    
    if app_name not in ['mulesoft', 'darwin', 'sap']:
        print(f"❌ Error: app_name debe ser 'mulesoft', 'darwin' o 'sap'")
        sys.exit(1)
    
    print(f"🔧 Generando system prompt de ejemplo para: {app_name}")
    print("="*80)
    
    prompt = generate_system_prompt_example(app_name)
    
    if not prompt:
        print("❌ Error generando el prompt")
        sys.exit(1)
    
    # Guardar en archivo de salida
    output_file = f"config/system_prompt_{app_name}_EXAMPLE.md"
    output_path = Path(output_file)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"✅ Prompt generado exitosamente")
    print(f"📄 Archivo guardado en: {output_file}")
    print(f"📊 Tamaño: {len(prompt):,} caracteres")
    print(f"📊 Líneas: {len(prompt.splitlines()):,}")
    print("="*80)
    print("\n💡 Puedes revisar el archivo generado para ver cómo se ve el prompt completo")


if __name__ == "__main__":
    main()
