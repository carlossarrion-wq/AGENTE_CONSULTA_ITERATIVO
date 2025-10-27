# Agente IA de Consulta Darwin - Diseño Arquitectónico

Sistema de agente conversacional inteligente para consulta de la base de conocimiento Darwin con capacidades de streaming y procesamiento de herramientas.

## 🎯 Objetivo

Diseñar un agente IA modular que permita la consulta interactiva de la base de conocimiento Darwin mediante:
- Interfaz de chat en modo texto
- Procesamiento inteligente de respuestas LLM
- Ejecución automática de herramientas de búsqueda
- Soporte futuro para streaming de respuestas

## 🏗️ Arquitectura General

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              AGENTE IA DARWIN                                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                │
│  │  Chat Interface │    │ Request Handler │    │ LLM Comm Module │                │
│  │                 │◄──►│  (Orchestrator) │◄──►│                 │                │
│  │ • Input Handler │    │ • Flow Control  │    │ • Request Mgmt  │                │
│  │ • Display Mgmt  │    │ • State Mgmt    │    │ • Response Hdlr │                │
│  │ • User Interact │    │ • Tool Parsing  │    │ • Connection    │                │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘                │
│           │                       │                       │                        │
│           │              ┌─────────────────┐              │                        │
│           │              │ Tool Execution  │              │                        │
│           │              │     Engine      │              │                        │
│           │              │ • XML Parser    │              │                        │
│           │              │ • Tool Router   │              │                        │
│           │              │ • Result Merger │              │                        │
│           │              └─────────────────┘              │                        │
│           │                       │                       │                        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                │
│  │Response Formatter│    │ Config Manager  │    │Knowledge Base   │                │
│  │                 │    │                 │    │   Interface     │                │
│  │ • Static Format │    │ • Settings Load │    │ • Semantic      │                │
│  │ • Stream Format │    │ • Env Variables │    │ • Lexical       │                │
│  │ • XML Filter    │    │ • Validation    │    │ • Regex         │                │
│  └─────────────────┘    └─────────────────┘    │ • File Content  │                │
│                                                 └─────────────────┘                │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 📋 Módulos Principales

### 1. Chat Interface Module
**Responsabilidad**: Interfaz de usuario para interacción conversacional

**Componentes**:
- **Input Handler**: Captura y valida entrada del usuario
- **Display Manager**: 
  - Static Display (implementación actual)
  - Streaming Display (futuro)
- **User Interaction**: Gestión de sesión y contexto

**Funcionalidades**:
- Captura de consultas del usuario
- Visualización de respuestas formateadas
- Manejo de historial de conversación
- Soporte futuro para streaming progresivo

### 2. Request Handler/Orchestrator
**Responsabilidad**: Coordinación central del flujo de procesamiento

**Componentes**:
- **Flow Control**: Gestión del flujo de conversación
- **State Management**: Mantenimiento del estado de la sesión
- **Tool Parsing**: Análisis de respuestas LLM para identificar herramientas

**Funcionalidades**:
- Recepción de consultas del chat interface
- Envío de requests al LLM
- Parsing de respuestas XML del LLM
- Coordinación de ejecución de herramientas
- Gestión de estado conversacional

### 3. LLM Communication Module
**Responsabilidad**: Comunicación con el modelo de lenguaje

**Componentes**:
- **Request Manager**: Construcción y envío de requests
- **Response Handler**:
  - Batch Response (implementación actual)
  - Stream Response (futuro)
- **Connection Manager**: Gestión de conexiones y autenticación
- **Prompt Cache Manager**: Gestión de cache de prompts (CRÍTICO)

**Funcionalidades**:
- Construcción de prompts con contexto
- **Prompt Caching**: Cache inteligente de contexto conversacional
- Envío de requests a AWS Bedrock
- Recepción de respuestas (batch/stream)
- Manejo de errores y reintentos
- Optimización de tokens mediante cache

### 4. Tool Execution Engine
**Responsabilidad**: Ejecución de herramientas de búsqueda

**Componentes**:
- **XML Parser**: Análisis de tags XML en respuestas LLM
- **Tool Router**: Enrutamiento a herramientas específicas
- **Result Merger**: Consolidación de resultados múltiples

**Funcionalidades**:
- Parsing de `<SEMANTIC_SEARCH>`, `<LEXICAL_SEARCH>`, etc.
- Ejecución de herramientas con parámetros extraídos
- Consolidación de resultados múltiples
- Manejo de errores de herramientas

### 5. Configuration Manager
**Responsabilidad**: Gestión de configuración del sistema

**Componentes**:
- **Settings Loader**: Carga de archivos de configuración
- **Environment Variables**: Gestión de variables de entorno
- **Validation**: Validación de configuración

**Funcionalidades**:
- Carga de `config.yaml`
- Gestión de credenciales AWS
- Configuración de herramientas de búsqueda
- Configuración de streaming (futuro)

### 6. Knowledge Base Interface
**Responsabilidad**: Interfaz con herramientas de búsqueda existentes

**Componentes**:
- **Semantic Search**: Integración con `semantic_search.py`
- **Lexical Search**: Integración con `lexical_search.py`
- **Regex Search**: Integración con `regex_search.py`
- **File Content**: Integración con `get_file_content.py`

**Funcionalidades**:
- Abstracción de herramientas de búsqueda
- Normalización de parámetros
- Estandarización de respuestas

### 7. Response Formatter
**Responsabilidad**: Formateo de respuestas para presentación

**Componentes**:
- **Static Formatter**: Formateo tradicional (actual)
- **Stream Processor**: Procesamiento de streaming (futuro)
- **XML Filter**: Filtrado de contenido técnico

**Funcionalidades**:
- Formateo de respuestas LLM
- Integración de resultados de herramientas
- Filtrado de contenido técnico (streaming)

## 🔄 Flujo de Datos

### Flujo Principal con Prompt Caching
```
Usuario Input → Chat Interface → Request Handler → LLM Communication
                                        ↓
                              Prompt Cache Manager
                                        ↓
                    ┌─────────────────────────────────────┐
                    │         GESTIÓN DE CACHE            │
                    ├─────────────────────────────────────┤
                    │ • Verificar cache existente         │
                    │ • Construir prompt incremental      │
                    │ • Aplicar cache de contexto         │
                    │ • Optimizar tokens enviados         │
                    └─────────────────────────────────────┘
                                        ↓
                              Respuesta LLM con XML
                                        ↓
                              Tool Execution Engine
                                        ↓
                    ┌─────────────────────────────────────┐
                    │        EJECUCIÓN HERRAMIENTAS       │
                    ├─────────────────────────────────────┤
                    │ <SEMANTIC_SEARCH> → semantic_search │
                    │ <LEXICAL_SEARCH> → lexical_search   │
                    │ <REGEX_SEARCH> → regex_search       │
                    │ <GET_FILE_CONTENT> → get_file_content│
                    └─────────────────────────────────────┘
                                        ↓
                              Consolidación Resultados
                                        ↓
                              Response Formatter
                                        ↓
                              Chat Interface → Usuario
                                        ↓
                              Actualizar Cache Conversacional
```

### Flujo con Streaming (Futuro)
```
Usuario Input → Chat Interface → Request Handler → LLM Communication
                                        ↓
                                 Stream Response
                                        ↓
                              Response Parser
                                        ↓
                    ┌─────────────────────────────────────┐
                    │        FILTRADO EN TIEMPO REAL      │
                    ├─────────────────────────────────────┤
                    │ XML Tags → [OCULTAR]                │
                    │ <SEMANTIC_SEARCH> → 'Búsqueda...'   │
                    │ <LEXICAL_SEARCH> → 'Búsqueda...'    │
                    │ <REGEX_SEARCH> → 'Búsqueda...'      │
                    │ <GET_FILE_CONTENT> → 'Obteniendo...'│
                    │ Texto normal → [MOSTRAR]            │
                    └─────────────────────────────────────┘
                                        ↓
                              Stream Processor
                                        ↓
                            Display Manager (Streaming)
                                        ↓
                              Chat Interface → Usuario
```

## 🗂️ Estructura de Archivos Propuesta

```
AGENTE_CONSULTA_ITERATIVO/
├── src/
│   ├── agent/                          # Módulos del agente IA
│   │   ├── __init__.py
│   │   ├── chat_interface.py           # Interfaz de chat
│   │   ├── request_handler.py          # Orquestador principal
│   │   ├── llm_communication.py        # Comunicación LLM
│   │   ├── prompt_cache_manager.py     # Gestión cache prompts (NUEVO)
│   │   ├── conversation_manager.py     # Gestión historial conversacional (NUEVO)
│   │   ├── tool_executor.py            # Ejecución de herramientas
│   │   ├── config_manager.py           # Gestión de configuración
│   │   ├── knowledge_interface.py      # Interfaz herramientas búsqueda
│   │   └── response_formatter.py       # Formateo de respuestas
│   ├── streaming/                      # Módulos streaming (futuro)
│   │   ├── __init__.py
│   │   ├── response_parser.py          # Parser streaming
│   │   ├── stream_processor.py         # Procesador streaming
│   │   ├── display_manager.py          # Gestor display streaming
│   │   └── filter_rules.py             # Reglas de filtrado
│   ├── [herramientas existentes...]    # Herramientas de búsqueda actuales
│   │   ├── semantic_search.py
│   │   ├── lexical_search.py
│   │   ├── regex_search.py
│   │   ├── get_file_content.py
│   │   └── common.py
│   └── main.py                         # Punto de entrada principal
├── config/
│   ├── config.yaml                     # Configuración principal
│   └── streaming_config.yaml           # Configuración streaming (futuro)
├── prompts/
│   └── system_prompt.md                # Prompt del sistema (desde ejemplo_llamada_003.md)
└── [archivos existentes...]
```

## ⚙️ Configuración del Sistema

### Configuración Principal (config.yaml)
```yaml
# Configuración existente de herramientas de búsqueda
opensearch:
  host: "vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com"
  index_name: "rag-documents-darwin"

bedrock:
  region_name: "eu-west-1"
  model_id: "amazon.titan-embed-image-v1"

# Nueva configuración del agente
agent:
  max_conversation_turns: 50
  max_tools_per_response: 5
  response_timeout_seconds: 120
  
llm:
  model_id: "anthropic.claude-3-sonnet-20240229-v1:0"
  max_tokens: 4000
  temperature: 0.1
  
# Configuración crítica de Prompt Caching
prompt_caching:
  enabled: true                         # FUNDAMENTAL para rendimiento
  cache_ttl_minutes: 60                 # Tiempo de vida del cache
  max_cached_conversations: 100         # Máximo conversaciones en cache
  cache_compression: true               # Compresión de prompts largos
  incremental_updates: true             # Updates incrementales del contexto
  cache_strategy: "sliding_window"      # Estrategia de cache
  
conversation:
  max_history_turns: 20                 # Máximo turnos en historial
  context_window_tokens: 100000         # Ventana de contexto máxima
  system_prompt_caching: true           # Cache del system prompt
  tool_results_caching: true            # Cache de resultados de herramientas
  
chat:
  welcome_message: "¡Hola! Soy el agente Darwin. ¿En qué puedo ayudarte?"
  max_history_length: 20
```

### Configuración Streaming (streaming_config.yaml - Futuro)
```yaml
streaming:
  enabled: false                        # Por defecto deshabilitado
  buffer_size: 1024
  update_interval: 0.1
  
  # Traducciones de herramientas
  tool_translations:
    SEMANTIC_SEARCH: 'VOY A REALIZAR UNA BÚSQUEDA SEMÁNTICA SOBRE {document}'
    LEXICAL_SEARCH: 'VOY A REALIZAR UNA BÚSQUEDA LEXICAL SOBRE {query}'
    REGEX_SEARCH: 'VOY A REALIZAR UNA BÚSQUEDA POR PATRONES SOBRE {pattern}'
    GET_FILE_CONTENT: 'VOY A OBTENER EL CONTENIDO DEL ARCHIVO {filename}'
  
  # Tags a ocultar
  hidden_tags:
    - 'thinking'
    - 'internal_state'
    - 'debug_info'
  
  # Configuración de filtros
  filters:
    show_xml_tags: false
    translate_tool_calls: true
    progressive_display: true
```

## 💾 Sistema de Prompt Caching (CRÍTICO)

### Prompt Cache Manager
**Responsabilidad**: Gestión inteligente del cache de prompts para optimizar rendimiento y costos

**Funcionalidades**:
- **Cache de System Prompt**: El prompt del sistema se cachea una sola vez
- **Cache Conversacional**: Historial de conversación se mantiene en cache
- **Updates Incrementales**: Solo se envían los nuevos mensajes al LLM
- **Compresión Inteligente**: Compresión de contexto cuando se acerca al límite
- **Sliding Window**: Mantiene ventana deslizante de contexto relevante

**Métodos principales**:
```python
def cache_system_prompt(prompt: str) -> str  # Cachea prompt del sistema
def get_cached_conversation(session_id: str) -> ConversationCache
def update_conversation_cache(session_id: str, new_turn: Turn) -> None
def build_incremental_prompt(session_id: str, user_input: str) -> str
def compress_context_if_needed(context: str) -> str
def invalidate_cache(session_id: str) -> None
```

### Conversation Manager
**Responsabilidad**: Gestión del historial conversacional y contexto

**Funcionalidades**:
- **Historial Estructurado**: Mantiene estructura de turnos usuario/asistente
- **Gestión de Tokens**: Monitoreo de uso de tokens por conversación
- **Context Window Management**: Gestión inteligente de ventana de contexto
- **Tool Results Integration**: Integración de resultados de herramientas en historial

**Métodos principales**:
```python
def add_user_turn(session_id: str, message: str) -> None
def add_assistant_turn(session_id: str, response: str, tools_used: List[Tool]) -> None
def get_conversation_context(session_id: str) -> str
def trim_context_to_window(context: str, max_tokens: int) -> str
def get_token_count(text: str) -> int
```

### Estrategias de Cache

#### 1. Cache de System Prompt
```python
# El system prompt se cachea una sola vez por sesión
CACHED_SYSTEM_PROMPT = """
Eres un agente especializado en consultas sobre la base de conocimiento Darwin...
[Prompt completo desde ejemplo_llamada_003.md]
"""
```

#### 2. Cache Conversacional Incremental
```python
# Estructura de cache conversacional
ConversationCache = {
    "session_id": "uuid-session",
    "system_prompt_hash": "hash-del-system-prompt",
    "turns": [
        {
            "role": "user",
            "content": "¿Cómo configurar OAuth?",
            "timestamp": "2025-10-27T09:00:00Z",
            "tokens": 25
        },
        {
            "role": "assistant", 
            "content": "Voy a buscar información sobre OAuth...",
            "tools_used": ["SEMANTIC_SEARCH"],
            "tool_results": {...},
            "timestamp": "2025-10-27T09:00:15Z",
            "tokens": 150
        }
    ],
    "total_tokens": 175,
    "last_updated": "2025-10-27T09:00:15Z",
    "cache_ttl": "2025-10-27T10:00:15Z"
}
```

#### 3. Optimización de Tokens
```python
# Solo se envía al LLM:
# 1. System prompt (cacheado)
# 2. Contexto conversacional necesario
# 3. Nuevo input del usuario

def build_optimized_prompt(session_id: str, new_input: str) -> str:
    cache = get_cached_conversation(session_id)
    
    # Construir prompt incremental
    prompt_parts = [
        get_cached_system_prompt(),  # Cacheado
        build_conversation_context(cache.turns[-10:]),  # Últimos 10 turnos
        f"Human: {new_input}",
        "Assistant:"
    ]
    
    return "\n\n".join(prompt_parts)
```

### Beneficios del Prompt Caching

#### Rendimiento
- **Reducción 60-80% en tokens enviados** por request después del primer turno
- **Latencia reducida** al no reenviar contexto completo
- **Throughput mejorado** del sistema

#### Costos
- **Ahorro significativo en costos de tokens** (especialmente en conversaciones largas)
- **Optimización de uso de API** de AWS Bedrock
- **ROI mejorado** del sistema

#### Escalabilidad
- **Soporte para más conversaciones concurrentes**
- **Menor carga en infraestructura LLM**
- **Mejor experiencia de usuario**

## 🔧 Componentes de Streaming (Futuro)

### Response Parser
**Funcionalidades**:
- Análisis de chunks de streaming en tiempo real
- Detección de tags XML parciales
- Extracción de información de herramientas
- Filtrado de contenido para display

**Métodos principales**:
```python
def parse_streaming_chunk(chunk: str) -> ParsedChunk
def extract_tool_info(xml_content: str) -> ToolInfo
def filter_display_content(content: str) -> str
```

### Stream Processor
**Funcionalidades**:
- Gestión de buffer para chunks parciales
- Aplicación de filtros en tiempo real
- Envío progresivo al display manager
- Mantenimiento de estado de parsing

**Métodos principales**:
```python
def process_stream_chunk(chunk: str) -> None
def apply_real_time_filters(content: str) -> str
def manage_display_buffer() -> None
def track_parsing_state() -> None
```

### Display Manager (Streaming)
**Funcionalidades**:
- Actualización progresiva de la interfaz
- Manejo de traducciones de herramientas
- Gestión de buffer de display
- Sincronización con chat interface

**Métodos principales**:
```python
def append_filtered_content(content: str) -> None
def handle_tool_translation(tool_info: ToolInfo) -> None
def update_interface_progressive() -> None
```

## 🎯 Patrones de Uso

### Ejemplo de Conversación con Prompt Caching

#### Turno 1 (Sin Cache)
```
Usuario: "¿Cómo configurar OAuth en aplicaciones web?"

[SISTEMA - Primer request]
Tokens enviados: ~8,000 (System Prompt completo + User Input)
Cache: System Prompt cacheado para sesión

Agente: Voy a buscar información sobre configuración OAuth en aplicaciones web.

[Internamente ejecuta: <SEMANTIC_SEARCH>configuración OAuth aplicaciones web</SEMANTIC_SEARCH>]

Agente: He encontrado información relevante sobre OAuth. Según la documentación:

1. **Configuración básica de OAuth 2.0**:
   - Registrar aplicación en el proveedor OAuth
   - Configurar redirect URIs
   - Obtener client_id y client_secret

2. **Implementación en aplicaciones web**:
   - Usar flujo Authorization Code
   - Implementar endpoints de callback
   - Gestionar tokens de acceso y refresh

¿Te gustaría que busque información más específica sobre algún aspecto?
```

#### Turno 2 (Con Cache - OPTIMIZADO)
```
Usuario: "Sí, busca ejemplos de código para implementar OAuth"

[SISTEMA - Request optimizado con cache]
Tokens enviados: ~1,500 (Solo contexto conversacional + nuevo input)
Ahorro: ~6,500 tokens (81% reducción)
Cache: Reutiliza System Prompt + contexto previo

Agente: [Con streaming futuro mostraría: "VOY A REALIZAR UNA BÚSQUEDA POR PATRONES SOBRE código OAuth"]

[Ejecuta búsquedas y presenta resultados...]
```

#### Turno 3+ (Cache Optimizado)
```
Usuario: "¿Hay algún ejemplo específico para Node.js?"

[SISTEMA - Request ultra-optimizado]
Tokens enviados: ~800 (Contexto mínimo + nuevo input)
Ahorro: ~7,200 tokens (90% reducción)
Cache: Ventana deslizante de contexto relevante
```

### Impacto del Prompt Caching en Conversaciones Largas

```
Conversación de 10 turnos SIN cache:
- Turno 1: 8,000 tokens
- Turno 2: 8,500 tokens (contexto crece)
- Turno 3: 9,000 tokens
- ...
- Turno 10: 15,000 tokens
TOTAL: ~105,000 tokens

Conversación de 10 turnos CON cache:
- Turno 1: 8,000 tokens (inicial)
- Turno 2: 1,500 tokens (cache activo)
- Turno 3: 1,200 tokens
- ...
- Turno 10: 1,000 tokens
TOTAL: ~20,000 tokens

AHORRO: 85,000 tokens (81% reducción)
AHORRO ECONÓMICO: ~$170 por conversación larga (estimado)
```

### Flujo de Herramientas
```python
# Ejemplo de ejecución de herramientas
tools_executed = [
    {
        "type": "SEMANTIC_SEARCH",
        "query": "configuración OAuth aplicaciones web",
        "results": [...],
        "display_message": "Búsqueda semántica sobre OAuth"
    },
    {
        "type": "REGEX_SEARCH", 
        "pattern": "oauth.*client.*secret",
        "results": [...],
        "display_message": "Búsqueda de patrones OAuth"
    }
]
```

## 🚀 Ventajas del Diseño

### Modularidad
- **Separación clara de responsabilidades**
- **Componentes intercambiables**
- **Fácil testing unitario**
- **Escalabilidad horizontal**

### Extensibilidad
- **Nuevas herramientas fáciles de agregar**
- **Soporte para diferentes LLMs**
- **Configuración flexible**
- **Plugins de formateo**

### Mantenibilidad
- **Código organizado por funcionalidad**
- **Configuración centralizada**
- **Logging estructurado**
- **Documentación integrada**

### Compatibilidad
- **No afecta herramientas existentes**
- **Streaming opcional (futuro)**
- **Configuración backward-compatible**
- **Migración gradual**

## 🔮 Roadmap de Implementación

### Fase 1: Core Agent (Actual)
- ✅ Diseño arquitectónico
- ✅ Diseño Prompt Caching (CRÍTICO)
- ⏳ Implementación módulos básicos
- ⏳ **Implementación Prompt Cache Manager (PRIORITARIO)**
- ⏳ **Implementación Conversation Manager (PRIORITARIO)**
- ⏳ Integración con herramientas existentes
- ⏳ Testing básico

### Fase 2: Funcionalidades Avanzadas
- ⏳ Optimización avanzada de cache
- ⏳ Gestión de estado conversacional
- ⏳ Manejo de errores robusto
- ⏳ Métricas de rendimiento de cache
- ⏳ Logging y monitoreo

### Fase 3: Streaming (Futuro)
- ⏳ Implementación response parser
- ⏳ Stream processor
- ⏳ Display manager streaming
- ⏳ Configuración streaming

### Fase 4: Mejoras y Optimización
- ⏳ Cache inteligente
- ⏳ Métricas y analytics
- ⏳ UI/UX mejorado
- ⏳ Documentación completa

## 📊 Consideraciones Técnicas

### Rendimiento
- **Prompt Caching (CRÍTICO)**: Reducción 60-80% tokens por request
- **Cache de respuestas LLM**
- **Pool de conexiones**
- **Procesamiento asíncrono**
- **Optimización de queries**
- **Context Window Management**: Gestión inteligente de ventana de contexto

### Seguridad
- **Validación de inputs**
- **Sanitización de outputs**
- **Gestión segura de credenciales**
- **Logging sin información sensible**

### Escalabilidad
- **Arquitectura stateless**
- **Configuración por entorno**
- **Métricas de uso**
- **Balanceador de carga ready**

### Monitoreo
- **Logs estructurados**
- **Métricas de rendimiento**
- **Alertas de errores**
- **Dashboard de uso**

---

**Versión**: 1.0.0  
**Fecha**: Octubre 2025  
**Estado**: Diseño Completado  
**Próximo paso**: Implementación Fase 1
