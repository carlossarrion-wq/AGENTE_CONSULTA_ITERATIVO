# Fix: Web Crawler App-Specific Keyword Validation

## Problema Identificado

Al usar el agente con `--app sap`, la herramienta `web_crawler` estaba validando las queries contra las keywords de MuleSoft en lugar de las keywords específicas de SAP, resultando en el error:

```
ERROR: Error ejecutando web_crawler: Query rechazada: Query debe estar relacionada con mulesoft
```

## Causa Raíz

El problema tenía dos partes:

1. **En `tool_web_crawler.py`**: La función `execute_web_crawler()` tenía un parámetro `app_name` con valor por defecto `'mulesoft'`:
   ```python
   app_name = params.get('app_name', 'mulesoft')  # Default a mulesoft
   ```

2. **En `tool_executor.py`**: Al ejecutar la herramienta `web_crawler`, no se estaba inyectando el parámetro `app_name`, por lo que siempre usaba el valor por defecto ('mulesoft').

3. **En `chat_interface.py`**: Aunque recibía el `app_name` como parámetro, no lo pasaba al `ToolExecutor`.

## Solución Implementada

### 1. Modificación en `tool_executor.py`

**Cambio en `__init__`**: Añadir parámetro `app_name`
```python
def __init__(self, config_path: str = "config/config.yaml", app_name: str = "mulesoft"):
    """
    Inicializa el ejecutor de herramientas
    
    Args:
        config_path: Ruta al archivo de configuración
        app_name: Nombre de la aplicación (mulesoft, darwin, sap)
    """
    self.config_path = config_path
    self.app_name = app_name  # <-- NUEVO
    self.logger = logging.getLogger(__name__)
```

**Cambio en `execute_tool`**: Inyectar `app_name` antes de ejecutar web_crawler
```python
elif tool_type == ToolType.WEB_CRAWLER:
    # Inyectar app_name en los parámetros si no está presente
    if 'app_name' not in params:
        params['app_name'] = self.app_name  # <-- NUEVO
    
    # Ejecutar web crawler
    crawler_result = execute_web_crawler(params)
    if crawler_result.success:
        result = crawler_result.data
    else:
        raise Exception(crawler_result.error)
```

### 2. Modificación en `chat_interface.py`

**Cambio en `__init__`**: Pasar `app_name` al crear `ToolExecutor`
```python
# Inicializar componentes de streaming
if enable_streaming:
    self.llm_comm = LLMCommunication(config_path=config_path)
    self.tool_executor = ToolExecutor(
        config_path=config_path, 
        app_name=app_name.lower()  # <-- NUEVO: pasar app_name
    )
    self.logger.info("Streaming habilitado")
```

## Flujo de Datos Corregido

```
main.py (--app sap)
    ↓
ChatInterface(app_name="SAP")
    ↓
ToolExecutor(app_name="sap")
    ↓
execute_web_crawler(params={'query': '...', 'app_name': 'sap'})
    ↓
WebCrawlerTool(app_name='sap')
    ↓
QueryValidator.is_valid_query() 
    → Valida contra keywords de SAP: [sap, erp, hana, fiori, s/4hana]
```

## Configuración por Aplicación

El archivo `config/web_crawler_config.yaml` define keywords específicas para cada app:

```yaml
sap:
  enabled: true
  allowed_domains:
    - help.sap.com
    - support.sap.com
    - community.sap.com
    - blogs.sap.com
    - launchpad.support.sap.com
    - stackoverflow.com
  required_keywords:
    - sap
    - erp
    - hana
    - fiori
    - s/4hana

mulesoft:
  enabled: true
  allowed_domains:
    - docs.mulesoft.com
    - help.mulesoft.com
    - blogs.mulesoft.com
  required_keywords:
    - mulesoft
    - api
    - integration
    - runtime
    - anypoint

darwin:
  enabled: true
  allowed_domains:
    - docs.darwin.com
    - support.darwin.com
  required_keywords:
    - darwin
    - contrato
    - cliente
    - gestión
```

## Validación

Ahora cuando se ejecuta:
```bash
python3 src/agent/main.py --app sap
```

Y el usuario pregunta sobre SAP, la herramienta `web_crawler`:
1. Recibe `app_name='sap'` correctamente
2. Valida la query contra las keywords de SAP
3. Busca solo en dominios permitidos para SAP
4. Devuelve URLs relevantes de documentación oficial de SAP

## Testing

Para probar el fix:

```bash
# Activar entorno virtual
source venv/bin/activate

# Ejecutar con SAP
python3 src/agent/main.py --app sap

# Probar query sobre SAP
> SAP ISU latest version release notes 2024 2025
```

Debería funcionar correctamente sin el error de validación contra MuleSoft.

## Archivos Modificados

1. `src/agent/tool_executor.py`
   - Añadido parámetro `app_name` en `__init__`
   - Inyección de `app_name` en params antes de ejecutar web_crawler

2. `src/agent/chat_interface.py`
   - Pasar `app_name` al crear instancia de `ToolExecutor`

## Fecha de Implementación

29 de octubre de 2025
