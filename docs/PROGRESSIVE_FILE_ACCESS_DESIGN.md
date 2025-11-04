# Diseño: Acceso Progresivo a Contenido de Archivos Grandes

## Objetivo

Permitir al agente acceder a archivos grandes de forma progresiva, solicitando solo las secciones relevantes en lugar del contenido completo, evitando así exceder los límites de contexto del modelo LLM.

---

## Problema Actual

### Situación
- Archivos grandes (>100 páginas, >1M caracteres) exceden la ventana de contexto del LLM
- Error: `Input is too long for requested model`
- El agente no puede procesar el contenido completo de una vez

### Limitaciones
- Claude Haiku 4.5: ~200K tokens (≈150K palabras, ≈750K caracteres)
- Claude Sonnet 4: ~200K tokens (misma capacidad)
- Documentos pueden tener >1.7M caracteres

---

## Solución Propuesta: Acceso Progresivo con Navegación Inteligente

### Concepto

El agente podrá:
1. **Obtener estructura del documento** (tabla de contenidos, secciones)
2. **Solicitar secciones específicas** por nombre o número
3. **Navegar progresivamente** a través del documento
4. **Combinar información** de múltiples secciones

---

## Arquitectura de la Solución

### Componente 1: Analizador de Estructura de Documentos

**Responsabilidad**: Extraer la estructura jerárquica del documento

```python
class DocumentStructureAnalyzer:
    """
    Analiza la estructura de documentos grandes y genera un índice navegable
    """
    
    def analyze_structure(self, file_path: str) -> DocumentStructure:
        """
        Analiza el documento y extrae:
        - Tabla de contenidos
        - Secciones principales
        - Subsecciones
        - Páginas
        - Metadatos (total páginas, tamaño, etc.)
        """
        pass
    
    def get_section_boundaries(self, section_id: str) -> Tuple[int, int]:
        """
        Retorna los límites (inicio, fin) de una sección específica
        """
        pass
```

**Estructura de Datos**:

```python
@dataclass
class DocumentSection:
    id: str                    # "section_1", "section_1.1", etc.
    title: str                 # "1. Introducción"
    level: int                 # 1, 2, 3 (nivel de jerarquía)
    start_char: int            # Posición de inicio en el documento
    end_char: int              # Posición de fin
    start_page: int            # Página de inicio
    end_page: int              # Página de fin
    char_count: int            # Número de caracteres
    parent_id: Optional[str]   # ID de la sección padre
    children_ids: List[str]    # IDs de subsecciones

@dataclass
class DocumentStructure:
    file_path: str
    file_name: str
    total_pages: int
    total_chars: int
    sections: List[DocumentSection]
    toc: str                   # Tabla de contenidos formateada
```

### Componente 2: Herramienta Mejorada `tool_get_file_content`

**Nueva Funcionalidad**: Detección automática y manejo de archivos grandes

```python
def tool_get_file_content(
    file_path: str,
    section_id: Optional[str] = None,
    page_range: Optional[Tuple[int, int]] = None,
    char_range: Optional[Tuple[int, int]] = None,
    include_metadata: bool = False,
    max_chars: int = 100000  # Límite de seguridad
) -> Dict[str, Any]:
    """
    Obtiene contenido de archivo con soporte para acceso progresivo
    
    Args:
        file_path: Ruta del archivo
        section_id: ID de sección específica (ej: "section_2.1")
        page_range: Rango de páginas (inicio, fin)
        char_range: Rango de caracteres (inicio, fin)
        include_metadata: Incluir metadatos
        max_chars: Límite máximo de caracteres a retornar
    
    Returns:
        Dict con contenido y metadatos
    """
    pass
```

**Flujo de Trabajo**:

```
1. Usuario solicita archivo
   ↓
2. Sistema detecta tamaño
   ↓
3. ¿Es grande (>100K chars)?
   │
   ├─ NO → Retornar contenido completo
   │
   └─ SÍ → Analizar estructura
          ↓
          Retornar:
          - Resumen del documento
          - Tabla de contenidos
          - Instrucciones para navegación
          - Primeras 2-3 secciones como muestra
```

### Componente 3: Nueva Herramienta `tool_get_document_structure`

**Propósito**: Obtener solo la estructura sin contenido

```xml
<tool_get_document_structure>
<file_path>/path/to/large/document.pdf</file_path>
<include_summary>true</include_summary>
</tool_get_document_structure>
```

**Respuesta**:

```json
{
  "file_name": "DF_LOG_ZEUS_INT_33&34_ENVIO ALTA Y MOV DE NS_v0.1.pdf",
  "total_pages": 109,
  "total_chars": 1706830,
  "is_large": true,
  "summary": "Este documento describe las integraciones INT_33 e INT_34...",
  "table_of_contents": [
    {
      "id": "section_1",
      "title": "1. Introducción",
      "level": 1,
      "pages": "1-3",
      "chars": 5420
    },
    {
      "id": "section_1.1",
      "title": "1.1 Objetivo del Documento",
      "level": 2,
      "pages": "1-2",
      "chars": 2100
    },
    {
      "id": "section_2",
      "title": "2. Integración INT_33 - Envío de Altas de NS",
      "level": 1,
      "pages": "4-45",
      "chars": 680000
    },
    {
      "id": "section_2.1",
      "title": "2.1 Descripción General",
      "level": 2,
      "pages": "4-8",
      "chars": 82000
    }
  ],
  "navigation_instructions": "Para acceder a una sección específica, usa:\n<tool_get_file_content>\n<file_path>...</file_path>\n<section_id>section_2.1</section_id>\n</tool_get_file_content>"
}
```

### Componente 4: Nueva Herramienta `tool_get_file_section`

**Propósito**: Acceso directo a secciones específicas

```xml
<tool_get_file_section>
<file_path>/path/to/document.pdf</file_path>
<section_id>section_2.1</section_id>
<include_context>true</include_context>
</tool_get_file_section>
```

**Parámetros**:
- `section_id`: ID de la sección (de la tabla de contenidos)
- `include_context`: Incluir secciones padre/hermanas para contexto

**Respuesta**:

```json
{
  "section": {
    "id": "section_2.1",
    "title": "2.1 Descripción General",
    "content": "... contenido de la sección ...",
    "pages": "4-8",
    "chars": 82000
  },
  "context": {
    "parent": {
      "id": "section_2",
      "title": "2. Integración INT_33"
    },
    "siblings": [
      {"id": "section_2.2", "title": "2.2 Flujo de Datos"},
      {"id": "section_2.3", "title": "2.3 Validaciones"}
    ]
  }
}
```

---

## Flujo de Interacción del Agente

### Escenario 1: Usuario Solicita Contenido General de Archivo Grande

```
👤 Usuario: "Explícame el contenido del fichero DF_LOG_ZEUS_INT_33&34"

🤖 Agente (thinking):
Usuario solicita contenido del archivo.
Primero voy a obtener la estructura del documento para entender qué contiene.

🔧 Agente ejecuta:
<tool_get_file_content>
<file_path>DF_LOG_ZEUS_INT_33&34_ENVIO ALTA Y MOV DE NS_v0.1.pdf</file_path>
</tool_get_file_content>

📥 Sistema responde:
{
  "is_large_file": true,
  "file_name": "DF_LOG_ZEUS_INT_33&34_ENVIO ALTA Y MOV DE NS_v0.1.pdf",
  "total_pages": 109,
  "total_chars": 1706830,
  "message": "Este archivo es demasiado grande para mostrarlo completo. Aquí está su estructura:",
  "summary": "Documento que describe las integraciones INT_33 e INT_34 entre SAP S/4HANA y ZEUS...",
  "table_of_contents": [
    {"id": "section_1", "title": "1. Introducción", "pages": "1-3"},
    {"id": "section_2", "title": "2. INT_33 - Envío Altas NS", "pages": "4-45"},
    {"id": "section_3", "title": "3. INT_34 - Envío Movimientos NS", "pages": "46-89"},
    {"id": "section_4", "title": "4. Casos de Uso", "pages": "90-105"},
    {"id": "section_5", "title": "5. Anexos", "pages": "106-109"}
  ]
}

🤖 Agente (thinking):
El archivo es muy grande. El usuario pidió "el contenido", lo cual es general.
Voy a obtener las secciones principales para darle una visión completa:
- Introducción (section_1) - para contexto
- Secciones principales (section_2, section_3) - contenido core
- Casos de uso (section_4) - ejemplos prácticos

🔧 Agente ejecuta (iterativamente):
<tool_get_file_section>
<file_path>DF_LOG_ZEUS_INT_33&34_ENVIO ALTA Y MOV DE NS_v0.1.pdf</file_path>
<section_id>section_1</section_id>
</tool_get_file_section>

[Recibe contenido de introducción]

<tool_get_file_section>
<file_path>DF_LOG_ZEUS_INT_33&34_ENVIO ALTA Y MOV DE NS_v0.1.pdf</file_path>
<section_id>section_2</section_id>
</tool_get_file_section>

[Recibe contenido de INT_33]

<tool_get_file_section>
<file_path>DF_LOG_ZEUS_INT_33&34_ENVIO ALTA Y MOV DE NS_v0.1.pdf</file_path>
<section_id>section_3</section_id>
</tool_get_file_section>

[Recibe contenido de INT_34]

💬 Agente responde:
<present_answer>
El documento "DF_LOG_ZEUS_INT_33&34_ENVIO ALTA Y MOV DE NS_v0.1.pdf" describe las integraciones entre SAP S/4HANA y ZEUS para la gestión de números de serie.

**1. Introducción**
[Contenido de la sección 1...]

**2. INT_33 - Envío de Altas de Números de Serie**
[Contenido resumido de la sección 2...]
- Descripción general del proceso
- Flujo de datos desde SAP a ZEUS
- Validaciones aplicadas
- Estructura de mensajes

**3. INT_34 - Envío de Movimientos de Números de Serie**
[Contenido resumido de la sección 3...]
- Tipos de movimientos soportados
- Procesamiento de actualizaciones
- Manejo de errores

El documento también incluye casos de uso prácticos y anexos técnicos.
</present_answer>

<sources>["DF_LOG_ZEUS_INT_33&34_ENVIO ALTA Y MOV DE NS_v0.1.pdf:section_1,section_2,section_3"]</sources>
```

### Escenario 2: Usuario Solicita Sección Específica

```
👤 Usuario: "Explícame la sección sobre INT_33"

🤖 Agente (thinking):
Usuario quiere información sobre INT_33.
Del índice anterior, sé que es la sección 2.
Voy a solicitar esa sección específica.

🔧 Agente ejecuta:
<tool_get_file_section>
<file_path>DF_LOG_ZEUS_INT_33&34_ENVIO ALTA Y MOV DE NS_v0.1.pdf</file_path>
<section_id>section_2</section_id>
<include_context>true</include_context>
</tool_get_file_section>

📥 Sistema responde:
{
  "section": {
    "id": "section_2",
    "title": "2. INT_33 - Envío de Altas de Números de Serie",
    "content": "... contenido completo de la sección 2 (42 páginas) ...",
    "subsections": [
      {"id": "section_2.1", "title": "2.1 Descripción General"},
      {"id": "section_2.2", "title": "2.2 Flujo de Datos"},
      {"id": "section_2.3", "title": "2.3 Validaciones"}
    ]
  }
}

💬 Agente responde con el contenido de la sección 2...
```

### Escenario 3: Navegación Progresiva

```
👤 Usuario: "¿Y qué hay sobre las validaciones en INT_33?"

🤖 Agente (thinking):
Usuario pregunta por validaciones en INT_33.
De la estructura anterior, sé que hay una subsección 2.3 sobre validaciones.
Voy a solicitar esa subsección específica.

🔧 Agente ejecuta:
<tool_get_file_section>
<file_path>DF_LOG_ZEUS_INT_33&34_ENVIO ALTA Y MOV DE NS_v0.1.pdf</file_path>
<section_id>section_2.3</section_id>
</tool_get_file_section>

💬 Agente responde con información específica sobre validaciones...
```

---

## Implementación Técnica

### Paso 1: Extracción de Estructura

**Para PDFs**:
```python
import PyPDF2
import re

def extract_pdf_structure(pdf_path: str) -> DocumentStructure:
    """
    Extrae estructura de PDF usando:
    1. Bookmarks/Outlines del PDF
    2. Análisis de texto para detectar títulos (regex patterns)
    3. Análisis de formato (tamaño de fuente, negrita)
    """
    
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        
        # Intentar obtener bookmarks
        outlines = reader.outline
        
        # Si no hay bookmarks, analizar texto
        if not outlines:
            sections = extract_sections_from_text(reader)
        else:
            sections = parse_bookmarks(outlines, reader)
    
    return DocumentStructure(
        file_path=pdf_path,
        sections=sections,
        total_pages=len(reader.pages),
        ...
    )
```

**Para DOCX**:
```python
from docx import Document

def extract_docx_structure(docx_path: str) -> DocumentStructure:
    """
    Extrae estructura de DOCX usando:
    1. Estilos de párrafo (Heading 1, Heading 2, etc.)
    2. Numeración de secciones
    """
    
    doc = Document(docx_path)
    sections = []
    
    for para in doc.paragraphs:
        if para.style.name.startswith('Heading'):
            level = int(para.style.name[-1])
            sections.append(DocumentSection(
                title=para.text,
                level=level,
                ...
            ))
    
    return DocumentStructure(...)
```

### Paso 2: Extracción de Contenido por Sección

```python
def extract_section_content(
    file_path: str,
    section: DocumentSection
) -> str:
    """
    Extrae el contenido de una sección específica
    """
    
    if file_path.endswith('.pdf'):
        return extract_pdf_section(file_path, section)
    elif file_path.endswith('.docx'):
        return extract_docx_section(file_path, section)
    else:
        # Para archivos de texto plano
        with open(file_path, 'r') as f:
            content = f.read()
            return content[section.start_char:section.end_char]
```

### Paso 3: Consideración Futura - Almacenamiento de Estructuras en S3

**NOTA**: Por el momento, NO se implementará caché de estructuras de documentos.

En el futuro, se podría considerar realizar un análisis previo de los documentos y almacenar sus estructuras en un directorio S3 dedicado. Esto permitiría:
- Acceso más rápido a la estructura de documentos
- Análisis previo de documentos al subirlos
- Reducción de procesamiento en tiempo real

Esta funcionalidad se evaluará en fases posteriores del proyecto.

---

## Modificaciones al System Prompt

Agregar al system prompt del agente:

```markdown
## MANEJO DE ARCHIVOS GRANDES

### Detección Automática

Cuando solicites el contenido de un archivo con `tool_get_file_content` y el archivo sea demasiado grande (>100K caracteres), recibirás:

1. **Estructura del documento** en lugar del contenido completo:
   - Resumen general del documento
   - Tabla de contenidos con todas las secciones
   - Metadatos (páginas, tamaño, etc.)

2. **Ejemplo de respuesta para archivo grande**:
```json
{
  "is_large_file": true,
  "file_name": "documento_grande.pdf",
  "total_pages": 109,
  "total_chars": 1706830,
  "summary": "Resumen del documento...",
  "table_of_contents": [
    {"id": "section_1", "title": "1. Introducción", "pages": "1-3"},
    {"id": "section_2", "title": "2. Contenido Principal", "pages": "4-45"},
    {"id": "section_3", "title": "3. Conclusiones", "pages": "46-50"}
  ]
}
```

### Tu Responsabilidad: Determinar Qué Secciones Necesitas

**IMPORTANTE**: Cuando recibas la estructura de un archivo grande, **TÚ debes decidir** qué secciones son relevantes para responder la pregunta del usuario. **NO preguntes al usuario qué sección quiere**.

### Estrategia de Navegación Inteligente

1. **Analiza la pregunta del usuario** y la tabla de contenidos
2. **Identifica las secciones relevantes** basándote en:
   - Títulos de secciones que coincidan con la pregunta
   - Contexto de la conversación
   - Conocimiento del dominio

3. **Solicita las secciones necesarias** usando `tool_get_file_section`:
   ```xml
   <tool_get_file_section>
   <file_path>ruta/al/archivo.pdf</file_path>
   <section_id>section_2</section_id>
   </tool_get_file_section>
   ```

4. **Combina información** de múltiples secciones si es necesario

### Ejemplos de Comportamiento Correcto

#### ❌ INCORRECTO (No hagas esto):
```
Usuario: "Explícame el documento X"
Tú: "El documento tiene 5 secciones. ¿Cuál te interesa?"
```

#### ✅ CORRECTO (Haz esto):
```
Usuario: "Explícame el documento X"

[Recibes estructura con 5 secciones]

Tú (thinking):
Usuario pide explicación general del documento.
Voy a obtener las secciones principales para dar una visión completa:
- section_1 (Introducción) - para contexto
- section_2 (Contenido principal) - core del documento
- section_5 (Conclusiones) - cierre

[Solicitas section_1, section_2, section_5]
[Recibes contenido]

Tú: [Presentas resumen completo basado en las secciones obtenidas]
```

#### ✅ CORRECTO (Pregunta específica):
```
Usuario: "¿Cómo funciona la validación de datos en el sistema?"

[Recibes estructura]

Tú (thinking):
Usuario pregunta por validación de datos.
En la tabla de contenidos veo:
- section_2.3: "Validaciones de Datos"
Esta es claramente la sección relevante.

[Solicitas section_2.3]
[Recibes contenido]

Tú: [Respondes con información específica sobre validaciones]
```

### Herramientas Disponibles

1. **tool_get_file_content**: 
   - Para archivos pequeños: retorna contenido completo
   - Para archivos grandes: retorna estructura

2. **tool_get_file_section**:
   - Obtiene contenido de una sección específica
   - Parámetros:
     - `file_path`: Ruta del archivo
     - `section_id`: ID de la sección (ej: "section_2.1")
     - `include_context`: true/false (incluir contexto de secciones relacionadas)

3. **tool_get_document_structure** (opcional):
   - Obtiene solo la estructura sin intentar cargar contenido
   - Útil si solo necesitas ver la organización del documento

### Reglas Importantes

1. **Autonomía**: TÚ decides qué secciones necesitas, no el usuario
2. **Eficiencia**: Solicita solo las secciones necesarias para responder
3. **Completitud**: Si la pregunta es general, obtén múltiples secciones clave
4. **Iteración**: Puedes solicitar secciones adicionales si necesitas más información
5. **Transparencia**: Menciona en tu respuesta qué secciones consultaste

### Casos de Uso Típicos

| Pregunta del Usuario | Secciones a Solicitar | Razonamiento |
|---------------------|----------------------|--------------|
| "Explícame el documento" | Introducción + Secciones principales + Conclusiones | Visión completa |
| "¿Cómo funciona X?" | Sección específica sobre X | Pregunta específica |
| "Compara X e Y" | Secciones sobre X y Y | Comparación |
| "¿Qué dice sobre validaciones?" | Secciones con "validación" en título | Búsqueda por tema |
| "Dame un resumen" | Introducción + Conclusiones | Resumen ejecutivo |
```

---

## Ventajas de Esta Solución

1. **Eficiencia**: Solo se carga el contenido necesario
2. **Escalabilidad**: Funciona con documentos de cualquier tamaño
3. **Flexibilidad**: El agente puede navegar libremente
4. **Contexto preservado**: El agente mantiene el contexto de la estructura
5. **User-friendly**: El usuario puede hacer preguntas naturales
6. **Inteligente**: El agente decide qué secciones necesita

---

## Casos de Uso

### Caso 1: Exploración General
```
Usuario: "¿Qué contiene el documento X?"
→ Agente muestra estructura y resumen
→ Usuario puede profundizar en secciones específicas
```

### Caso 2: Búsqueda Específica
```
Usuario: "¿Cómo funciona la validación de datos en INT_33?"
→ Agente identifica sección relevante (2.3)
→ Solicita solo esa sección
→ Responde con información específica
```

### Caso 3: Comparación de Secciones
```
Usuario: "Compara INT_33 e INT_34"
→ Agente solicita section_2 (INT_33)
→ Agente solicita section_3 (INT_34)
→ Agente compara y presenta diferencias
```

### Caso 4: Navegación Iterativa
```
Usuario: "Explícame el documento paso a paso"
→ Agente presenta sección 1
→ Usuario: "Siguiente"
→ Agente presenta sección 2
→ Y así sucesivamente...
```

---

## Implementación por Fases

### Fase 1: Detección y Estructura Básica (1-2 días)
- Implementar detección de archivos grandes
- Extraer estructura básica (secciones principales)
- Modificar `tool_get_file_content` para retornar estructura

### Fase 2: Navegación por Secciones (2-3 días)
- Implementar `tool_get_file_section`
- Implementar `tool_get_document_structure`
- Extracción de contenido por sección

### Fase 3: Extracción Avanzada (3-4 días)
- Soporte para múltiples formatos (PDF, DOCX, TXT)
- Detección inteligente de secciones
- Manejo de documentos sin estructura clara

### Fase 4: Optimizaciones (2-3 días)
- Mejoras en el análisis de estructura
- Optimización de cache
- Manejo de casos edge

---

## Métricas de Éxito

1. **Funcionalidad**:
   - ✅ Archivos >100K caracteres manejados correctamente
   - ✅ Estructura extraída con >90% precisión
   - ✅ Navegación fluida entre secciones

2. **Rendimiento**:
   - ⏱️ Análisis de estructura: <5 segundos
   - ⏱️ Extracción de sección: <2 segundos
   - 📊 Precisión en extracción: >90%

3. **Usabilidad**:
   - 👤 Usuario puede explorar documentos grandes naturalmente
   - 🤖 Agente navega inteligentemente
   - 📊 Respuestas completas sin exceder límites

---

## Consideraciones Adicionales

### Seguridad
- Validar que las secciones solicitadas existen
- Limitar tamaño máximo de sección (ej: 200K caracteres)
- Prevenir ataques de denegación de servicio

### Compatibilidad
- Soportar documentos sin estructura clara
- Fallback a división por páginas si no hay secciones
- Manejo de formatos legacy

### Experiencia de Usuario
- Mensajes claros cuando un archivo es grande
- Sugerencias de navegación
- Indicadores de progreso

---

## Conclusión

Esta solución permite al agente manejar documentos de cualquier tamaño de forma inteligente y eficiente, manteniendo una experiencia de usuario natural y fluida. El agente puede explorar, navegar y extraer información de documentos grandes sin limitaciones técnicas.
