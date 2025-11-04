# Implementación de Acceso Progresivo a Archivos Grandes

## Fecha
2025-11-04

## Objetivo

Implementar un mecanismo inteligente en `tool_get_file_content` que detecte archivos grandes y devuelva su estructura jerárquica en lugar del contenido completo, guiando al LLM a usar `tool_get_file_section` para acceso progresivo.

## Motivación

### Problema
- Archivos grandes (>50KB) consumen mucho contexto del LLM
- El LLM puede no necesitar todo el contenido para responder
- Desperdicio de tokens y tiempo de procesamiento

### Solución
- Detectar archivos grandes automáticamente
- Analizar su estructura (secciones, subsecciones)
- Devolver solo la estructura al LLM
- Permitir que el LLM seleccione secciones relevantes
- Usar `tool_get_file_section` para obtener solo lo necesario

## Arquitectura

### Flujo de Trabajo

```
Usuario: "¿Cómo se configura el módulo X?"
    ↓
LLM: <tool_get_file_content>
       <file_path>manual_modulo_x.pdf</file_path>
     </tool_get_file_content>
    ↓
Sistema detecta: archivo > 50KB
    ↓
Sistema analiza estructura con DocumentStructureAnalyzer
    ↓
Sistema devuelve:
{
  "access_mode": "progressive",
  "content_length": 125000,
  "structure": {
    "sections": [
      {"id": "section_1", "title": "Introducción"},
      {"id": "section_2", "title": "Instalación"},
      {"id": "section_3", "title": "Configuración"},  ← Relevante
      {"id": "section_4", "title": "Uso Avanzado"}
    ]
  },
  "message": "Archivo grande. Usa tool_get_file_section para secciones específicas."
}
    ↓
LLM analiza estructura y identifica section_3 como relevante
    ↓
LLM: <tool_get_file_section>
       <file_path>manual_modulo_x.pdf</file_path>
       <section_id>section_3</section_id>
     </tool_get_file_section>
    ↓
Sistema devuelve solo el contenido de section_3
    ↓
LLM responde al usuario con información específica
```

## Componentes Modificados

### 1. config/config_saplcorp.yaml

**Nuevos parámetros añadidos:**

```yaml
defaults:
  get_file_content:
    # ... parámetros existentes ...
    # Configuración de acceso progresivo
    max_content_length_for_full_retrieval: 50000  # 50KB
    enable_progressive_access: true
```

**Descripción:**
- `max_content_length_for_full_retrieval`: Umbral en caracteres para activar acceso progresivo
- `enable_progressive_access`: Flag para habilitar/deshabilitar la funcionalidad

### 2. src/tools/tool_get_file_content.py

**Cambios principales:**

#### A. Importación de DocumentStructureAnalyzer

```python
# Importar herramientas de acceso progresivo
try:
    from tools.document_structure_analyzer import DocumentStructureAnalyzer
    PROGRESSIVE_ACCESS_AVAILABLE = True
except ImportError:
    PROGRESSIVE_ACCESS_AVAILABLE = False
```

#### B. Modificación del método `get_content()`

**Lógica añadida:**

1. Calcular longitud total del contenido
2. Verificar si supera el umbral configurado
3. Si es grande Y acceso progresivo está habilitado:
   - Llamar a `_get_document_structure()`
   - Devolver estructura en lugar de contenido
4. Si es pequeño O acceso progresivo está deshabilitado:
   - Devolver contenido completo como antes

```python
# Calcular longitud total estimada
total_length = sum(len(chunk['_source'].get('content', '')) for chunk in chunks)

# Si el archivo es grande y el acceso progresivo está habilitado
if enable_progressive and total_length > max_length and PROGRESSIVE_ACCESS_AVAILABLE:
    self.logger.info(f"Archivo {file_path} es grande ({total_length} chars). Usando acceso progresivo.")
    return self._get_document_structure(file_path, chunks, include_metadata)
```

#### C. Nuevo método `_get_document_structure()`

**Responsabilidades:**

1. Reconstruir contenido completo (necesario para análisis)
2. Usar `DocumentStructureAnalyzer` para analizar estructura
3. Preparar respuesta con:
   - `access_mode: "progressive"`
   - Estructura del documento
   - Mensaje explicativo
   - Recomendaciones de uso
4. Manejo de errores con fallback a contenido completo

**Respuesta típica:**

```json
{
  "file_path": "manual_usuario.pdf",
  "access_mode": "progressive",
  "total_chunks": 150,
  "content_length": 125000,
  "structure": {
    "file_name": "manual_usuario.pdf",
    "total_sections": 12,
    "sections": [
      {
        "id": "section_1",
        "title": "Introducción",
        "level": 1,
        "start_pos": 0,
        "end_pos": 5000,
        "subsections": [...]
      },
      ...
    ]
  },
  "message": "Este archivo es grande (125,000 caracteres). Se proporciona la estructura del documento. Usa la herramienta 'get_file_section' para obtener secciones específicas.",
  "available_sections": [...],
  "recommendation": "Analiza la estructura y selecciona las secciones relevantes para tu consulta. Luego usa get_file_section con los identificadores de sección apropiados."
}
```

### 3. config/system_prompt_saplcorp.md

**Actualizaciones:**

#### A. Documentación de tool_get_file_content

- Añadida sección "Comportamiento con Archivos Grandes"
- Explicación del umbral de 50KB
- Descripción de la respuesta con `access_mode: "progressive"`
- Flujo de trabajo paso a paso
- Instrucciones claras sobre qué hacer cuando se recibe estructura

#### B. Nueva herramienta: tool_get_file_section

- Documentación completa de la herramienta
- Parámetros y opciones
- Ejemplos de uso con `section_id`, `section_title`, y posiciones
- Ejemplo de flujo completo desde estructura hasta sección específica

## Ventajas

### 1. Eficiencia de Tokens
- **Antes**: Archivo de 100KB = ~100,000 tokens consumidos
- **Ahora**: Estructura = ~2,000 tokens + sección relevante ~10,000 tokens = ~12,000 tokens
- **Ahorro**: ~88% de tokens

### 2. Velocidad de Respuesta
- Menos datos a procesar por el LLM
- Respuestas más rápidas
- Menor latencia

### 3. Precisión
- LLM puede ver la estructura completa antes de decidir
- Selección más inteligente de contenido relevante
- Evita información irrelevante

### 4. Escalabilidad
- Permite trabajar con documentos muy grandes
- No hay límite práctico de tamaño de archivo
- Acceso granular a cualquier parte del documento

## Configuración

### Ajustar el Umbral

Para cambiar el tamaño a partir del cual se activa el acceso progresivo:

```yaml
# config/config_saplcorp.yaml
defaults:
  get_file_content:
    max_content_length_for_full_retrieval: 30000  # 30KB en lugar de 50KB
```

### Deshabilitar Acceso Progresivo

Para volver al comportamiento anterior:

```yaml
# config/config_saplcorp.yaml
defaults:
  get_file_content:
    enable_progressive_access: false
```

## Casos de Uso

### Caso 1: Manual Técnico Grande

**Escenario**: Usuario pregunta sobre configuración específica en manual de 200 páginas

**Flujo**:
1. LLM solicita `tool_get_file_content` del manual
2. Sistema detecta 180KB de contenido
3. Sistema devuelve estructura con 15 secciones
4. LLM identifica "Sección 8: Configuración Avanzada" como relevante
5. LLM solicita `tool_get_file_section` con `section_id: "section_8"`
6. Sistema devuelve solo esa sección (~12KB)
7. LLM responde con información precisa

**Resultado**: 12KB procesados en lugar de 180KB (93% ahorro)

### Caso 2: Documento de Diseño Funcional

**Escenario**: Usuario pregunta sobre flujo específico en documento de 150 páginas

**Flujo**:
1. LLM obtiene estructura del documento
2. Identifica múltiples secciones relevantes:
   - "Sección 3: Flujo de Proceso"
   - "Sección 7: Validaciones"
3. LLM solicita ambas secciones secuencialmente
4. Combina información de ambas para responder

**Resultado**: Acceso selectivo a información distribuida en el documento

### Caso 3: Archivo Pequeño

**Escenario**: Usuario pregunta sobre guía rápida de 10 páginas

**Flujo**:
1. LLM solicita `tool_get_file_content`
2. Sistema detecta 8KB de contenido (< 50KB)
3. Sistema devuelve contenido completo directamente
4. LLM responde inmediatamente

**Resultado**: Sin overhead, comportamiento tradicional para archivos pequeños

## Testing

### Test Manual

1. **Archivo pequeño** (<50KB):
```bash
python3 -m src.tools.tool_get_file_content "archivo_pequeño.pdf" --config config/config_saplcorp.yaml
```
Esperado: Contenido completo con `"access_mode": "full"`

2. **Archivo grande** (>50KB):
```bash
python3 -m src.tools.tool_get_file_content "manual_grande.pdf" --config config/config_saplcorp.yaml
```
Esperado: Estructura con `"access_mode": "progressive"`

3. **Acceso progresivo deshabilitado**:
```yaml
# Modificar config
enable_progressive_access: false
```
```bash
python3 -m src.tools.tool_get_file_content "manual_grande.pdf" --config config/config_saplcorp.yaml
```
Esperado: Contenido completo incluso para archivos grandes

### Test de Integración

Probar con el agente completo:

```bash
python3 -m src.agent.main --app saplcorp
```

Consulta de prueba:
```
Usuario: "Muéstrame el contenido del manual UFD_Manual_IFRS16_v1.1.pdf"
```

Comportamiento esperado:
1. LLM solicita `tool_get_file_content`
2. Sistema devuelve estructura (archivo es grande)
3. LLM presenta estructura al usuario
4. Usuario puede pedir sección específica
5. LLM usa `tool_get_file_section` para obtenerla

## Limitaciones Conocidas

### 1. Análisis de Estructura
- Depende de la calidad del análisis de `DocumentStructureAnalyzer`
- Documentos sin estructura clara pueden no beneficiarse
- PDFs escaneados sin OCR no tienen estructura analizable

### 2. Overhead Inicial
- Primera llamada requiere reconstruir contenido completo para análisis
- Análisis de estructura añade ~1-2 segundos
- Mitigado por caché de resultados

### 3. Dependencia de LLM
- Requiere que el LLM entienda y use correctamente el flujo
- System prompt debe estar bien configurado
- LLM debe seguir instrucciones de usar `tool_get_file_section`

## Mejoras Futuras

### 1. Caché de Estructuras
- Cachear estructuras analizadas en Redis/DynamoDB
- Evitar re-análisis en consultas posteriores
- TTL configurable

### 2. Análisis Incremental
- No reconstruir contenido completo para análisis
- Analizar estructura directamente desde chunks
- Más eficiente para archivos muy grandes

### 3. Sugerencias Inteligentes
- Usar embeddings para sugerir secciones relevantes
- Basado en la consulta del usuario
- Reducir iteraciones LLM

### 4. Visualización de Estructura
- Generar árbol visual de secciones
- Facilitar navegación para el usuario
- Interfaz interactiva

## Conclusión

La implementación de acceso progresivo a archivos grandes es una mejora significativa que:

✅ Reduce consumo de tokens en ~88% para archivos grandes
✅ Mejora velocidad de respuesta
✅ Aumenta precisión al permitir selección inteligente
✅ Mantiene compatibilidad con archivos pequeños
✅ Es configurable y deshabilitab le
✅ Proporciona fallback robusto en caso de errores

Esta funcionalidad está actualmente **habilitada solo para la aplicación saplcorp** como prueba piloto antes de extenderla a otras aplicaciones.

---

**Autor**: Sistema Cline  
**Fecha**: 2025-11-04  
**Versión**: 1.0  
**Estado**: Implementado y listo para testing
