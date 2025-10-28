# Implementación de Carga Dinámica de Resúmenes desde S3

## Resumen

Se ha implementado un sistema de carga dinámica de resúmenes de documentos desde S3 para popular el system prompt del agente. Esto permite que el agente siempre tenga acceso a la información más actualizada sobre los documentos disponibles sin necesidad de actualizar manualmente el archivo de configuración.

## Cambios Realizados

### 1. Nuevo Módulo: `src/agent/s3_summaries_loader.py`

**Responsabilidad**: Consultar S3 y obtener los resúmenes de documentos para popular el system prompt.

**Características**:
- Conecta con S3 bucket: `rag-system-darwin-eu-west-1`
- Lee resúmenes desde: `applications/darwin/summaries/`
- Formatea los datos en el formato esperado por el system prompt
- **Filtra el campo `file_path`** de los JSON de S3 (contiene rutas temporales como `/tmp/` que confunden al LLM)
- Manejo de errores con fallback automático

**Métodos principales**:
- `load_summaries_from_s3()`: Carga todos los resúmenes desde S3 y elimina campos innecesarios
- `format_summaries_for_prompt()`: Formatea los resúmenes para el system prompt
- `get_summaries_section()`: Obtiene la sección completa formateada

### 2. Modificaciones en `src/agent/llm_communication.py`

**Cambios**:
1. Importación del nuevo módulo `S3SummariesLoader`
2. Inicialización del loader en `__init__`
3. Modificación de `_load_system_prompt()` para:
   - Buscar el marcador `{{DYNAMIC_SUMMARIES}}`
   - Consultar S3 para obtener resúmenes actuales
   - Reemplazar el marcador con los datos de S3

**Código clave**:
```python
# Inicializar S3 Summaries Loader
self.s3_loader = S3SummariesLoader()

# En _load_system_prompt()
if "{{DYNAMIC_SUMMARIES}}" in prompt_template:
    self.logger.info("📥 Cargando resúmenes dinámicamente desde S3...")
    summaries_section = self.s3_loader.get_summaries_section()
    prompt = prompt_template.replace("{{DYNAMIC_SUMMARIES}}", summaries_section)
```

### 3. Actualización de `config/system_prompt_darwin.txt`

**Cambio**: Reemplazo de la sección estática de documentos (247 líneas) con el marcador dinámico:
```
{{DYNAMIC_SUMMARIES}}
```

**Antes**: 
- Líneas 52-299: Sección JSON estática con 28 archivos
- Total: ~247 líneas de contenido estático

**Después**:
- Línea 52: Marcador `{{DYNAMIC_SUMMARIES}}`
- Se carga dinámicamente desde S3 al iniciar el agente

### 4. Scripts de Utilidad

#### `update_system_prompt.py`
Script para actualizar el system prompt reemplazando la sección estática con el marcador dinámico.

**Uso**:
```bash
python3 update_system_prompt.py
```

#### `test_dynamic_summaries.py`
Script de prueba completo para verificar que la carga dinámica funciona correctamente.

**Uso**:
```bash
python3 test_dynamic_summaries.py
```

## Flujo de Funcionamiento

### Al Iniciar el Agente

1. Se crea una instancia de `LLMCommunication`
2. En el `__init__`:
   - Se inicializa `S3SummariesLoader`
   - Se llama a `_load_system_prompt()`
3. En `_load_system_prompt()`:
   - Lee `config/system_prompt_darwin.txt`
   - Detecta el marcador `{{DYNAMIC_SUMMARIES}}`
   - **Consulta S3** para obtener resúmenes actuales
   - Reemplaza el marcador con los datos de S3
   - Retorna el prompt completo con datos frescos

### Durante la Ejecución

- El system prompt ya está cargado en memoria con los datos de S3
- Se usa ese prompt para todas las conversaciones de esa sesión
- **No hay overhead** durante las conversaciones

### Para Actualizar los Datos

- **Simplemente reinicia el agente**
- Volverá a consultar S3 y cargar los resúmenes más recientes

## Resultados de las Pruebas

### Test Exitoso (28/10/2025 18:39:41)

```
✅ TEST EXITOSO: La carga dinámica funciona correctamente

Estadísticas:
• Tamaño total del system prompt: 106,291 caracteres
• Líneas: 2,849
• Archivos indexados: 30 (vs 28 en versión estática)
• Fuente: s3://rag-system-darwin-eu-west-1/applications/darwin/summaries/
• Tiempo de carga desde S3: ~3 segundos
```

### Verificaciones Realizadas

✅ El marcador `{{DYNAMIC_SUMMARIES}}` fue reemplazado correctamente  
✅ La sección de archivos indexados está presente  
✅ Los datos de S3 están presentes en el system prompt  
✅ Se cargaron 30 archivos (2 más que la versión estática)  
✅ El formato JSON es correcto  
✅ Los metadatos incluyen la fuente de S3  

## Ventajas de esta Implementación

### 1. Datos Siempre Actualizados
- Cada vez que inicias el agente, obtiene los últimos resúmenes de S3
- No necesitas actualizar manualmente el archivo de configuración

### 2. Sin Overhead Durante Conversación
- La consulta a S3 solo ocurre al inicio
- No impacta el rendimiento durante las conversaciones

### 3. Fácil Actualización
- Solo reinicia el agente para refrescar los datos
- No requiere cambios en código o configuración

### 4. Fallback Automático
- Si S3 falla, usa un mensaje de error en lugar de romper el sistema
- El agente puede seguir funcionando con funcionalidad reducida

### 5. Escalabilidad
- Soporta cualquier número de documentos en S3
- El formato JSON se genera automáticamente

### 6. Trazabilidad
- Los logs muestran claramente cuándo se cargan los resúmenes
- Incluye timestamp y fuente de los datos

## Configuración

### Bucket S3
```python
bucket_name = "rag-system-darwin-eu-west-1"
summaries_prefix = "applications/darwin/summaries/"
region_name = "eu-west-1"
```

### Credenciales AWS
El sistema usa las credenciales configuradas en `~/.aws/credentials`

## Mantenimiento

### Agregar Nuevos Documentos

1. Sube el resumen JSON a S3:
   ```
   s3://rag-system-darwin-eu-west-1/applications/darwin/summaries/
   ```

2. Reinicia el agente para que cargue el nuevo documento

### Actualizar Resúmenes Existentes

1. Actualiza el archivo JSON en S3
2. Reinicia el agente

### Verificar Carga

Ejecuta el script de prueba:
```bash
python3 test_dynamic_summaries.py
```

## Logs Relevantes

Al iniciar el agente, verás estos logs:

```
📥 Cargando resúmenes dinámicamente desde S3...
Cargando resúmenes desde s3://rag-system-darwin-eu-west-1/applications/darwin/summaries/
✅ Cargados 30 resúmenes desde S3
✅ Resúmenes cargados y populados en el system prompt
✅ System prompt cargado desde archivo: config/system_prompt_darwin.txt
   Tamaño: 106291 caracteres
   Líneas: 2849
```

## Troubleshooting

### Error: No se pueden cargar los resúmenes

**Síntoma**: Mensaje de error en logs sobre S3

**Soluciones**:
1. Verificar credenciales AWS: `aws s3 ls s3://rag-system-darwin-eu-west-1/`
2. Verificar permisos de lectura en el bucket
3. Verificar conectividad de red

### El marcador no se reemplaza

**Síntoma**: El system prompt contiene `{{DYNAMIC_SUMMARIES}}`

**Soluciones**:
1. Verificar que el marcador existe en `config/system_prompt_darwin.txt`
2. Revisar logs para ver si hay errores de S3
3. Ejecutar `python3 test_dynamic_summaries.py` para diagnóstico

## Archivos Modificados

```
src/agent/
├── s3_summaries_loader.py          [NUEVO]
├── llm_communication.py            [MODIFICADO]

config/
├── system_prompt_darwin.txt        [MODIFICADO]

[RAÍZ]
├── update_system_prompt.py         [NUEVO]
├── test_dynamic_summaries.py       [NUEVO]
├── DYNAMIC_SUMMARIES_IMPLEMENTATION.md [NUEVO]
```

## Próximos Pasos (Opcional)

### Mejoras Futuras Posibles

1. **Cache de resúmenes**: Cachear los resúmenes en disco para evitar consultar S3 en cada inicio
2. **Recarga periódica**: Opción para recargar resúmenes cada X horas sin reiniciar
3. **Versionado**: Mantener historial de versiones de resúmenes
4. **Métricas**: Tracking de cuándo se actualizan los resúmenes

## Conclusión

La implementación de carga dinámica de resúmenes desde S3 proporciona un sistema robusto, escalable y fácil de mantener que asegura que el agente siempre tenga acceso a la información más actualizada sobre los documentos disponibles.

**Estado**: ✅ Implementado y probado exitosamente
**Fecha**: 28/10/2025
**Versión**: 1.0
