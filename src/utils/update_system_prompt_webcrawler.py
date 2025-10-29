"""
Update System Prompt with Web Crawler Tool

Script para actualizar dinámicamente los system prompts con la documentación
de la herramienta web crawler, basándose en la configuración.
"""

import yaml
from pathlib import Path
from typing import Dict, Any


def load_web_crawler_config(config_path: str = "config/web_crawler_config.yaml") -> Dict[str, Any]:
    """Carga la configuración del web crawler"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def generate_web_crawler_documentation(app_name: str, config: Dict[str, Any]) -> str:
    """
    Genera la documentación de la herramienta web crawler para un app específica
    
    Args:
        app_name: Nombre de la aplicación (mulesoft, darwin, sap)
        config: Configuración completa del web crawler
        
    Returns:
        String con la documentación formateada
    """
    app_config = config.get(app_name.lower(), {})
    
    # Verificar si está habilitada
    if not app_config.get('enabled', False):
        return ""
    
    global_config = config.get('global', {})
    
    # Obtener listas de configuración
    allowed_domains = app_config.get('allowed_domains', [])
    required_keywords = app_config.get('required_keywords', [])
    forbidden_keywords = app_config.get('forbidden_keywords', [])
    
    # Formatear dominios permitidos
    domains_list = "\n".join([f"     - {domain}" for domain in allowed_domains])
    
    # Formatear keywords requeridas
    required_list = ", ".join([f'"{kw}"' for kw in required_keywords])
    
    # Formatear keywords prohibidas
    forbidden_list = ", ".join([f'"{kw}"' for kw in forbidden_keywords]) if forbidden_keywords else "ninguna"
    
    documentation = f"""
## 5. tool_web_crawler - Búsqueda en Internet

**Propósito**: Buscar información actualizada en internet cuando la base de conocimiento interna no es suficiente.

**Cuándo usar**:
- Cuando necesites información sobre patches, actualizaciones o versiones recientes
- Para consultar documentación oficial actualizada
- Cuando la información en la base de conocimiento esté desactualizada
- Para verificar problemas conocidos o release notes recientes

**Restricciones de Seguridad**:
- **Dominios Permitidos**: Solo se pueden buscar en los siguientes dominios autorizados:
{domains_list}

- **Keywords Requeridas**: Toda búsqueda DEBE incluir al menos una de estas palabras: {required_list}

- **Keywords Prohibidas**: NO se permiten búsquedas con: {forbidden_list}

- **Rate Limiting**: Mínimo {app_config.get('rate_limit', {}).get('min_delay_seconds', 3)} segundos entre búsquedas

- **Límites**: Máximo {global_config.get('max_results_per_search', 3)} resultados por búsqueda, {global_config.get('max_content_length', 2000)} caracteres por resultado

**Formato XML**:
```xml
<tool_web_crawler>
<query>tu consulta de búsqueda aquí</query>
<app_name>{app_name.lower()}</app_name>
</tool_web_crawler>
```

**Parámetros**:
- `query` (requerido): Consulta de búsqueda. DEBE incluir keywords requeridas y estar relacionada con {app_name}
- `app_name` (opcional): Nombre de la aplicación. Default: "{app_name.lower()}"

**Ejemplo de Uso**:
```xml
<tool_web_crawler>
<query>{app_name.lower()} runtime 4.5.0 security patch latest</query>
<app_name>{app_name.lower()}</app_name>
</tool_web_crawler>
```

**Respuesta**:
La herramienta devuelve un JSON con:
- `query`: La consulta realizada
- `results_count`: Número de resultados encontrados
- `sources`: Array de fuentes con:
  - `number`: Número del resultado
  - `url`: URL de la fuente (siempre de dominios permitidos)
  - `content`: Contenido extraído (máximo {global_config.get('max_content_length', 2000)} caracteres)
  - `extraction_method`: Método usado (trafilatura, beautifulsoup, o cache)

**Ejemplo de Respuesta**:
```json
{{
  "query": "{app_name.lower()} api security patches",
  "results_count": 3,
  "sources": [
    {{
      "number": 1,
      "url": "https://docs.{app_name.lower()}.com/release-notes/...",
      "content": "Contenido extraído de la página...",
      "extraction_method": "trafilatura"
    }}
  ]
}}
```

**Notas Importantes**:
1. La herramienta valida automáticamente que las URLs estén en dominios permitidos
2. Las búsquedas se cachean por {global_config.get('cache_ttl_hours', 24)} horas para reducir requests
3. Si una búsqueda no cumple con las restricciones, será rechazada automáticamente
4. Usa esta herramienta solo cuando la información interna no sea suficiente o esté desactualizada
"""
    
    return documentation


def update_system_prompt(app_name: str, prompt_path: str, web_crawler_config: Dict[str, Any]) -> bool:
    """
    Actualiza un system prompt con la documentación del web crawler
    
    Args:
        app_name: Nombre de la aplicación
        prompt_path: Ruta al archivo de system prompt
        web_crawler_config: Configuración del web crawler
        
    Returns:
        True si se actualizó correctamente
    """
    try:
        # Leer el prompt actual
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Generar documentación
        web_crawler_doc = generate_web_crawler_documentation(app_name, web_crawler_config)
        
        # Si no está habilitada, remover cualquier documentación existente
        if not web_crawler_doc:
            # Buscar y remover sección existente
            start_marker = "## 5. tool_web_crawler"
            if start_marker in content:
                # Encontrar el inicio de la siguiente sección o el final
                start_idx = content.find(start_marker)
                # Buscar la siguiente sección que empiece con ##
                next_section_idx = content.find("\n## ", start_idx + 1)
                
                if next_section_idx != -1:
                    content = content[:start_idx] + content[next_section_idx:]
                else:
                    content = content[:start_idx]
                
                # Guardar
                with open(prompt_path, 'w', encoding='utf-8') as f:
                    f.write(content.rstrip() + "\n")
                
                print(f"✅ Removida documentación de web_crawler de {prompt_path} (herramienta deshabilitada)")
            else:
                print(f"ℹ️  {prompt_path} no contiene documentación de web_crawler")
            
            return True
        
        # Buscar dónde insertar la documentación
        # Buscar la sección de herramientas
        tools_section_marker = "# HERRAMIENTAS DISPONIBLES"
        
        if tools_section_marker not in content:
            print(f"⚠️  No se encontró la sección de herramientas en {prompt_path}")
            return False
        
        # Verificar si ya existe documentación del web crawler
        web_crawler_marker = "## 5. tool_web_crawler"
        
        if web_crawler_marker in content:
            # Reemplazar documentación existente
            start_idx = content.find(web_crawler_marker)
            # Buscar la siguiente sección o el final
            next_section_idx = content.find("\n## ", start_idx + 1)
            
            if next_section_idx != -1:
                content = content[:start_idx] + web_crawler_doc.strip() + "\n\n" + content[next_section_idx:]
            else:
                content = content[:start_idx] + web_crawler_doc.strip() + "\n"
            
            print(f"✅ Actualizada documentación de web_crawler en {prompt_path}")
        else:
            # Insertar nueva documentación después de la herramienta 4
            tool4_marker = "## 4. tool_get_file_content"
            
            if tool4_marker in content:
                # Encontrar el final de la sección de tool_get_file_content
                start_idx = content.find(tool4_marker)
                # Buscar la siguiente sección que empiece con ##
                next_section_idx = content.find("\n## ", start_idx + 1)
                
                if next_section_idx != -1:
                    # Insertar antes de la siguiente sección
                    content = content[:next_section_idx] + "\n" + web_crawler_doc.strip() + "\n" + content[next_section_idx:]
                else:
                    # Insertar al final
                    content = content.rstrip() + "\n\n" + web_crawler_doc.strip() + "\n"
                
                print(f"✅ Añadida documentación de web_crawler a {prompt_path}")
            else:
                print(f"⚠️  No se encontró la sección de tool_get_file_content en {prompt_path}")
                return False
        
        # Guardar el archivo actualizado
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
        
    except Exception as e:
        print(f"❌ Error actualizando {prompt_path}: {e}")
        return False


def main():
    """Función principal"""
    print("🔧 Actualizando system prompts con documentación de web crawler...\n")
    
    # Cargar configuración del web crawler
    web_crawler_config = load_web_crawler_config()
    
    # Definir los prompts a actualizar
    prompts = {
        'mulesoft': 'config/system_prompt_mulesoft.md',
        'darwin': 'config/system_prompt_darwin.md',
        'sap': 'config/system_prompt_sap.md'
    }
    
    success_count = 0
    
    for app_name, prompt_path in prompts.items():
        print(f"\n📝 Procesando {app_name}...")
        
        # Verificar si el archivo existe
        if not Path(prompt_path).exists():
            print(f"⚠️  Archivo no encontrado: {prompt_path}")
            continue
        
        # Verificar si está habilitado
        app_config = web_crawler_config.get(app_name.lower(), {})
        enabled = app_config.get('enabled', False)
        
        if enabled:
            print(f"   ✓ Web crawler habilitado para {app_name}")
        else:
            print(f"   ✗ Web crawler deshabilitado para {app_name}")
        
        # Actualizar prompt
        if update_system_prompt(app_name, prompt_path, web_crawler_config):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Actualizados {success_count}/{len(prompts)} system prompts")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
