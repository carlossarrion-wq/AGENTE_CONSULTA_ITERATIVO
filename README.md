# Agente IA de Consulta Darwin

Sistema de agente conversacional inteligente para consulta de la base de conocimiento Darwin con capacidades de búsqueda semántica, léxica, regex y gestión avanzada de conversaciones.

## 📋 Tabla de Contenidos

- [Descripción General](#descripción-general)
- [Arquitectura del Sistema](#arquitectura-del-sistema)
- [Componentes Principales](#componentes-principales)
- [Herramientas de Búsqueda](#herramientas-de-búsqueda)
- [Instalación y Configuración](#instalación-y-configuración)
- [Uso del Sistema](#uso-del-sistema)
- [Características Avanzadas](#características-avanzadas)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Documentación Técnica](#documentación-técnica)

---

## 🎯 Descripción General

El **Agente IA de Consulta Darwin** es un sistema conversacional avanzado diseñado para facilitar la consulta y exploración de la base de conocimiento Darwin. Utiliza modelos de lenguaje de última generación (AWS Bedrock/Anthropic Claude) combinados con múltiples estrategias de búsqueda para proporcionar respuestas precisas y contextuales.

### Características Principales

- **🤖 Agente Conversacional Inteligente**: Interfaz de chat natural con gestión de contexto conversacional
- **🔍 Búsqueda Multimodal**: 4 herramientas especializadas de búsqueda (semántica, léxica, regex, contenido de archivos)
- **💾 Prompt Caching Avanzado**: Optimización de tokens con reducción del 60-80% en conversaciones largas
- **📊 Gestión de Contexto**: Sliding window inteligente para mantener conversaciones extensas
- **🔄 Carga Dinámica de Documentos**: Integración con S3 para actualización automática de catálogo
- **📝 Logging Estructurado**: Registro completo de interacciones LLM en formato JSON
- **🌐 Conectividad AWS**: Soporte para túneles SSH y diagnósticos de red

### Casos de Uso

1. **Consultas Funcionales**: "¿Cómo funciona el módulo de autenticación en Darwin?"
2. **Búsqueda de Código**: "Encuentra todas las funciones que validan tokens OAuth"
3. **Análisis de Documentación**: "Resume el contenido del documento de especificaciones técnicas"
4. **Exploración de Arquitectura**: "Explica la arquitectura de microservicios de Darwin"

---

## 🏗️ Arquitectura del Sistema

### Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENTE IA DARWIN                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│  │Chat Interface│◄──►│Request Handler│◄──►│LLM Comm Module│                │
│  │              │    │(Orchestrator) │    │               │                │
│  │• Input Mgmt  │    │• Flow Control │    │• AWS Bedrock  │                │
│  │• Display     │    │• State Mgmt   │    │• Prompt Cache │                │
│  └──────────────┘    └──────────────┘    └──────────────┘                 │
│         │                     │                     │                       │
│         │            ┌──────────────┐              │                       │
│         │            │Tool Execution│              │                       │
│         │            │    Engine    │              │                       │
│         │            │• XML Parser  │              │                       │
│         │            │• Tool Router │              │                       │
│         │            └──────────────┘              │                       │
│         │                     │                     │                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│  │Response      │    │Config Manager│    │Knowledge Base│                 │
│  │Formatter     │    │              │    │  Interface   │                 │
│  │• Formatting  │    │• YAML Config │    │• Semantic    │                 │
│  │• Filtering   │    │• Validation  │    │• Lexical     │                 │
│  └──────────────┘    └──────────────┘    │• Regex       │                 │
│                                           │• File Content│                 │
│                                           └──────────────┘                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │     INFRAESTRUCTURA AWS       │
                    ├───────────────────────────────┤
                    │• OpenSearch (VPC)             │
                    │• Bedrock (Claude/Titan)       │
                    │• S3 (Documentos/Resúmenes)    │
                    └───────────────────────────────┘
```

### Flujo de Datos Principal

```
Usuario → Chat Interface → Request Handler → Prompt Cache Manager
                                    ↓
                          LLM Communication (AWS Bedrock)
                                    ↓
                          Respuesta con XML de herramientas
                                    ↓
                          Tool Execution Engine
                                    ↓
                    ┌───────────────────────────────────┐
                    │   EJECUCIÓN DE HERRAMIENTAS       │
                    ├───────────────────────────────────┤
                    │ <semantic_search> → OpenSearch    │
                    │ <lexical_search> → OpenSearch     │
                    │ <regex_search> → OpenSearch       │
                    │ <get_file_content> → OpenSearch   │
                    └───────────────────────────────────┘
                                    ↓
                          Consolidación de Resultados
                                    ↓
                          Response Formatter
                                    ↓
                          Chat Interface → Usuario
                                    ↓
                          Actualizar Cache Conversacional
```

---

## 🧩 Componentes Principales

### 1. Chat Interface (`src/agent/chat_interface.py`)

**Responsabilidad**: Interfaz de usuario para interacción conversacional

**Funcionalidades**:
- Captura de consultas del usuario
- Visualización de respuestas formateadas con colores
- Manejo de historial de conversación
- Comandos especiales (/help, /history, /clear, /exit)

### 2. Request Handler (`src/agent/request_handler.py`)

**Responsabilidad**: Orquestador central del flujo de procesamiento

**Funcionalidades**:
- Coordinación del flujo de conversación
- Gestión del estado de la sesión
- Parsing de respuestas XML del LLM
- Coordinación de ejecución de herramientas

### 3. LLM Communication (`src/agent/llm_communication.py`)

**Responsabilidad**: Comunicación con AWS Bedrock

**Funcionalidades**:
- Construcción de prompts con contexto
- **Prompt Caching**: Optimización de tokens (reducción 60-80%)
- Envío de requests a AWS Bedrock
- Manejo de errores y reintentos
- Logging completo de interacciones

**Configuración**:
```yaml
llm:
  model_id: "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
  max_tokens: 4000
  temperature: 0.1
  max_retries: 3
```

### 4. Prompt Cache Manager (`src/agent/prompt_cache_manager.py`)

**Responsabilidad**: Gestión inteligente del cache de prompts

**Funcionalidades Clave**:
- Cache de System Prompt (una sola vez por sesión)
- Cache Conversacional con updates incrementales
- Compresión inteligente de contexto
- Sliding window para contexto relevante

**Beneficios**:
- **Reducción 60-80% en tokens** por request después del primer turno
- **Ahorro significativo en costos** de API
- **Latencia reducida** al no reenviar contexto completo
- **Mejor experiencia de usuario**

### 5. Conversation Manager (`src/agent/conversation_manager.py`)

**Responsabilidad**: Gestión del historial conversacional

**Funcionalidades**:
- Historial estructurado de turnos usuario/asistente
- Monitoreo de uso de tokens
- Context Window Management (180K tokens)
- Sliding window con mínimo de turnos a mantener

**Configuración**:
```yaml
conversation:
  max_history_turns: 15
  context_window_tokens: 180000
  system_prompt_caching: true
  tool_results_caching: true
  enable_sliding_window: true
  min_turns_to_keep: 3
```

### 6. Tool Executor (`src/agent/tool_executor.py`)

**Responsabilidad**: Ejecución de herramientas de búsqueda

**Funcionalidades**:
- Parsing de tags XML en respuestas LLM
- Enrutamiento a herramientas específicas
- Consolidación de resultados múltiples
- Manejo de errores de herramientas
- Logging detallado de ejecuciones

### 7. S3 Summaries Loader (`src/agent/s3_summaries_loader.py`)

**Responsabilidad**: Carga dinámica de resúmenes de documentos desde S3

**Funcionalidades**:
- Carga de catálogo desde S3 bucket
- Simplificación de estructura JSON
- Filtrado de campos innecesarios
- Integración con system prompt dinámico

**Configuración**:
```yaml
s3:
  bucket_name: "rag-system-darwin-eu-west-1"
  region_name: "eu-west-1"
  prefix: "applications/darwin/"
```

### 8. Configuration Manager (`src/agent/config_manager.py`)

**Responsabilidad**: Gestión centralizada de configuración

**Funcionalidades**:
- Carga de `config/config.yaml`
- Validación de configuración
- Acceso a configuración por secciones
- Soporte para valores por defecto

---

## 🔍 Herramientas de Búsqueda

### 1. Semantic Search

**Descripción**: Búsqueda semántica usando embeddings vectoriales (Amazon Titan)

**Uso en XML**:
```xml
<semantic_search>
<query>módulos principales Darwin arquitectura componentes</query>
<top_k>10</top_k>
<min_score>0.5</min_score>
<file_types>["docx", "pdf"]</file_types>
</semantic_search>
```

**Parámetros**:
- `query` (requerido): Descripción conceptual de lo que se busca
- `top_k` (opcional): Número de resultados (default: 10)
- `min_score` (opcional): Puntuación mínima 0.0-1.0 (default: 0.5)
- `file_types` (opcional): Filtrar por tipos de archivo

**Casos de Uso**:
- Búsquedas conceptuales: "¿Cómo funciona la autenticación?"
- Búsquedas por significado, no palabras exactas
- Encontrar documentación relacionada

### 2. Lexical Search

**Descripción**: Búsqueda textual tradicional (BM25) con coincidencias exactas

**Uso en XML**:
```xml
<lexical_search>
<query>authenticateUser validateToken</query>
<fields>["content", "file_name"]</fields>
<operator>AND</operator>
<top_k>20</top_k>
<fuzzy>false</fuzzy>
</lexical_search>
```

**Parámetros**:
- `query` (requerido): Términos de búsqueda exactos
- `fields` (opcional): Campos donde buscar (default: ["content"])
- `operator` (opcional): "AND" | "OR" (default: "OR")
- `top_k` (opcional): Número de resultados (default: 10)
- `fuzzy` (opcional): Coincidencias aproximadas (default: false)

**Casos de Uso**:
- Búsqueda de palabras clave específicas
- Búsqueda de nombres de funciones o variables
- Búsqueda con operadores lógicos

### 3. Regex Search

**Descripción**: Búsqueda mediante expresiones regulares para patrones específicos

**Uso en XML**:
```xml
<regex_search>
<pattern>function\s+\w+\s*\([^)]*\)\s*\{</pattern>
<file_types>["js", "ts"]</file_types>
<case_sensitive>false</case_sensitive>
<max_matches_per_file>50</max_matches_per_file>
<context_lines>3</context_lines>
</regex_search>
```

**Parámetros**:
- `pattern` (requerido): Expresión regular
- `file_types` (opcional): Filtrar por extensiones
- `case_sensitive` (opcional): Sensible a mayúsculas (default: true)
- `max_matches_per_file` (opcional): Máximo coincidencias (default: 50)
- `context_lines` (opcional): Líneas de contexto (default: 2)

**Casos de Uso**:
- Búsqueda de patrones de código
- Búsqueda de estructuras específicas
- Análisis de código con regex

### 4. Get File Content

**Descripción**: Obtiene el contenido completo de un archivo reconstruyendo chunks

**Uso en XML**:
```xml
<get_file_content>
<file_path>FD-Darwin_Funcional0_v2.9.docx</file_path>
<include_metadata>true</include_metadata>
</get_file_content>
```

**Parámetros**:
- `file_path` (requerido): Nombre del archivo
- `include_metadata` (opcional): Incluir metadatos (default: false)

**Características Avanzadas**:
- Reconstrucción inteligente de chunks con manejo de overlaps
- Detección de duplicados por hash
- Uso de información de posición cuando está disponible
- Scroll de OpenSearch para archivos grandes

**Casos de Uso**:
- Obtener documento completo para análisis
- Leer especificaciones técnicas completas
- Extraer contenido para procesamiento

---

## 🚀 Instalación y Configuración

### Requisitos Previos

- Python 3.9+
- AWS CLI configurado con credenciales
- Acceso a AWS Bedrock y OpenSearch
- Conexión a VPC (o túnel SSH configurado)

### Instalación

```bash
# Clonar el repositorio
git clone https://github.com/carlossarrion-wq/AGENTE_CONSULTA_ITERATIVO.git
cd AGENTE_CONSULTA_ITERATIVO

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip3 install -r requirements.txt
```

### Configuración

1. **Configurar AWS Credentials**:
```bash
aws configure
# Ingresar Access Key ID, Secret Access Key, Region (eu-west-1)
```

2. **Configurar `config/config.yaml`**:
```yaml
# Configuración de OpenSearch
opensearch:
  host: "localhost"  # o VPC endpoint
  port: 9201
  use_ssl: true
  verify_certs: false
  region: "eu-west-1"
  index_name: "rag-documents-darwin"

# Configuración de AWS Bedrock
bedrock:
  region_name: "eu-west-1"
  model_id: "amazon.titan-embed-image-v1"

# Configuración del LLM
llm:
  model_id: "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
  max_tokens: 4000
  temperature: 0.1

# Configuración de conversación
conversation:
  max_history_turns: 15
  context_window_tokens: 180000
  enable_sliding_window: true
```

3. **Configurar System Prompt** (opcional):
   - El system prompt se carga desde `config/system_prompt_darwin.md`
   - Incluye marcador `{{DYNAMIC_SUMMARIES}}` para carga dinámica desde S3

### Configuración de Túnel SSH (Desarrollo Local)

Si necesitas acceder a OpenSearch en VPC desde local:

```bash
# Opción 1: Script automático
./src/ssh_tunnel/setup_tunnel.sh

# Opción 2: Script en background
./src/ssh_tunnel/start_tunnel_background.sh

# Opción 3: Usar aws_tunnel.py
python3 src/ssh_tunnel/aws_tunnel.py --local-port 9201
```

---

## 💻 Uso del Sistema

### Iniciar el Agente

```bash
# Desde la raíz del proyecto
python3 src/agent/main.py
```

### Comandos Disponibles

- `/help` - Muestra ayuda y comandos disponibles
- `/history` - Muestra historial de conversación
- `/clear` - Limpia el historial
- `/exit` o `/quit` - Sale del agente

### Ejemplos de Uso

#### Ejemplo 1: Consulta Funcional
```
Usuario: ¿Cómo funciona el módulo de autenticación en Darwin?

Agente: Voy a buscar información sobre el módulo de autenticación...
[Ejecuta semantic_search internamente]

Agente: El módulo de autenticación en Darwin incluye:
1. Autenticación mediante OAuth 2.0
2. Validación de tokens JWT
3. Gestión de sesiones
...
```

#### Ejemplo 2: Búsqueda de Código
```
Usuario: Encuentra todas las funciones que validan tokens

Agente: Voy a buscar patrones de código relacionados con validación de tokens...
[Ejecuta regex_search internamente]

Agente: He encontrado 15 funciones que validan tokens:
1. validateToken() en auth_middleware.js
2. verifyJWT() en token_utils.js
...
```

#### Ejemplo 3: Análisis de Documento
```
Usuario: Resume el contenido del documento FD-Darwin_Funcional0_v2.9.docx

Agente: Voy a obtener el contenido del documento...
[Ejecuta get_file_content internamente]

Agente: El documento contiene la especificación funcional del módulo de Contratación:
- Procesos de contratación asistida y no asistida
- Lógica de búsqueda de direcciones
...
```

---

## ⚡ Características Avanzadas

### 1. Prompt Caching

El sistema implementa un sofisticado sistema de cache de prompts que reduce significativamente el uso de tokens:

**Beneficios**:
- **Reducción 60-80%** en tokens por request después del primer turno
- **Ahorro económico** significativo en conversaciones largas
- **Latencia reducida** al no reenviar contexto completo

**Ejemplo de Ahorro**:
```
Conversación de 10 turnos SIN cache:
- Total: ~105,000 tokens
- Costo estimado: ~$210

Conversación de 10 turnos CON cache:
- Total: ~20,000 tokens
- Costo estimado: ~$40

AHORRO: 85,000 tokens (81% reducción)
AHORRO ECONÓMICO: ~$170 por conversación
```

### 2. Sliding Window Conversacional

Gestión inteligente de ventana de contexto para conversaciones extensas:

- **Context Window**: 180K tokens (90% de 200K)
- **Mínimo de turnos**: 3 turnos siempre mantenidos
- **Eliminación inteligente**: Turnos más antiguos se eliminan primero
- **Preservación de contexto**: Información crítica se mantiene

### 3. Carga Dinámica de Documentos

Los resúmenes de documentos se cargan dinámicamente desde S3:

- **Bucket S3**: `rag-system-darwin-eu-west-1`
- **Actualización automática**: Al iniciar el agente
- **Simplificación**: Solo campos esenciales (file_name, summary, topics, key_terms)
- **Integración**: Marcador `{{DYNAMIC_SUMMARIES}}` en system prompt

### 4. Logging Estructurado

Registro completo de todas las interacciones:

- **Formato JSON**: Logs estructurados en `src/agent/logs/`
- **Información completa**: Requests, responses, herramientas ejecutadas
- **Timestamps**: Marca temporal de cada interacción
- **Métricas**: Tokens usados, tiempo de ejecución

**Estructura de Logs**:
```json
{
  "timestamp": "2025-10-28T19:00:00Z",
  "session_id": "uuid-session",
  "request": {
    "user_input": "¿Cómo funciona OAuth?",
    "system_prompt_hash": "abc123",
    "conversation_history_length": 5
  },
  "response": {
    "content": "OAuth es un protocolo...",
    "tools_used": ["semantic_search"],
    "tokens": {
      "input": 1500,
      "output": 800,
      "total": 2300
    }
  }
}
```

### 5. Diagnósticos de Red

Herramientas para diagnosticar conectividad:

```bash
# Diagnóstico completo
python3 src/utils/network_diagnostics.py

# Tests incluidos:
# - Credenciales AWS
# - Conectividad OpenSearch
# - Acceso a Bedrock
# - Resolución DNS
# - Conexiones TCP
```

---

## 📁 Estructura del Proyecto

```
AGENTE_CONSULTA_ITERATIVO/
├── config/
│   ├── config.yaml                    # Configuración principal
│   └── system_prompt_darwin.md        # System prompt con marcador dinámico
│
├── src/
│   ├── agent/                         # Módulos del agente IA
│   │   ├── __init__.py
│   │   ├── main.py                    # Punto de entrada
│   │   ├── chat_interface.py          # Interfaz de chat
│   │   ├── request_handler.py         # Orquestador principal
│   │   ├── llm_communication.py       # Comunicación con Bedrock
│   │   ├── prompt_cache_manager.py    # Gestión de cache de prompts
│   │   ├── conversation_manager.py    # Gestión de historial
│   │   ├── conversation_logger.py     # Logging de conversaciones
│   │   ├── tool_executor.py           # Ejecución de herramientas
│   │   ├── config_manager.py          # Gestión de configuración
│   │   ├── response_formatter.py      # Formateo de respuestas
│   │   ├── s3_summaries_loader.py     # Carga dinámica desde S3
│   │   ├── color_utils.py             # Utilidades de colores
│   │   └── logs/                      # Logs de conversaciones
│   │
│   ├── tools/                         # Herramientas de búsqueda
│   │   ├── __init__.py
│   │   ├── semantic_search.py         # Búsqueda semántica
│   │   ├── lexical_search.py          # Búsqueda léxica
│   │   ├── regex_search.py            # Búsqueda por regex
│   │   └── get_file_content.py        # Obtención de archivos
│   │
│   ├── common/                        # Utilidades compartidas
│   │   ├── __init__.py
│   │   └── common.py                  # Config, OpenSearch, Bedrock clients
│   │
│   ├── utils/                         # Utilidades del sistema
│   │   ├── __init__.py
│   │   ├── network_diagnostics.py     # Diagnósticos de red
│   │   ├── update_system_prompt.py    # Actualización de prompt
│   │   └── process_summaries.py       # Procesamiento de resúmenes
│   │
│   └── ssh_tunnel/                    # Herramientas de tunelización
│       ├── __init__.py
│       ├── aws_tunnel.py              # Cliente de túnel SSH
│       ├── setup_tunnel.sh            # Script de configuración
│       ├── start_tunnel_background.sh # Túnel en background
│       └── start_tunnel_direct.sh     # Túnel directo
│
├── docs/                              # Documentación técnica
│   ├── README.md                      # Este archivo
│   ├── README_AGENTE_IA_DESIGN.md     # Diseño arquitectónico
│   ├── DEFINICION_4_HERRAMIENTAS_AGENTE_CONSULTA.md
│   ├── DYNAMIC_SUMMARIES_IMPLEMENTATION.md
│   ├── SLIDING_WINDOW_IMPLEMENTATION.md
│   ├── LOGS_JSON_STRUCTURE.md
│   └── [otros documentos técnicos]
│
├── requirements.txt                   # Dependencias Python
├── .gitignore                        # Archivos ignorados por Git
└── README.md                         # Este archivo
```

---

## 📚 Documentación Técnica

### Documentos Disponibles

1. **[README_AGENTE_IA_DESIGN.md](docs/README_AGENTE_IA_DESIGN.md)**: Diseño arquitectónico completo del agente
2. **[DEFINICION_4_HERRAMIENTAS_AGENTE_CONSULTA.md](docs/DEFINICION_4_HERRAMIENTAS_AGENTE_CONSULTA.md)**: Especificación técnica de las 4 herramientas
3. **[DYNAMIC_SUMMARIES_IMPLEMENTATION.md](docs/DYNAMIC_SUMMARIES_IMPLEMENTATION.md)**: Implementación de carga dinámica desde S3
4. **[SLIDING_WINDOW_IMPLEMENTATION.md](docs/SLIDING_WINDOW_IMPLEMENTATION.md)**: Implementación de sliding window conversacional
5. **[LOGS_JSON_STRUCTURE.md](docs/LOGS_JSON_STRUCTURE.md)**: Estructura de logs JSON
6. **[SOLUCION_CONECTIVIDAD_AWS.md](docs/SOLUCION_CONECTIVIDAD_AWS.md)**: Soluciones de conectividad AWS

### Tecnologías Utilizadas

- **Python 3.9+**: Lenguaje principal
- **AWS Bedrock**: Servicio de LLM (Claude Haiku)
- **AWS S3**: Almacenamiento de documentos y resúmenes
- **OpenSearch**: Motor de búsqueda y vectorial
- **Amazon Titan**: Modelo de embeddings (1024 dimensiones)
- **boto3**: SDK de AWS para Python
- **opensearchpy**: Cliente de OpenSearch
- **PyYAML**: Parsing de configuración

### Infraestructura AWS

- **Región**: eu-west-1 (Irlanda)
- **OpenSearch**: VPC endpoint en red privada
- **Bedrock**: Modelos Claude Haiku y Titan Embeddings
- **S3 Bucket**: rag-system-darwin-eu-west-1
- **Índice OpenSearch**: rag-documents-darwin

---

## 🔧 Mantenimiento y Desarrollo

### Actualizar System Prompt

```bash
# Si necesitas actualizar el system prompt con nuevos documentos
python3 src/utils/update_system_prompt.py
```

### Procesar Nuevos Resúmenes

```bash
# Procesar archivos JSON de resúmenes
python3 src/utils/process_summaries.py
```

### Ejecutar Tests

```bash
# Tests de componentes core
python3 src/agent/test_core_components.py

# Tests de colores
python3 src/agent/test_colors.py

# Tests de logging
python3 src/agent/test_llm_logging.py
```

### Diagnósticos

```bash
# Diagnóstico completo de conectividad
python3 src/utils/network_diagnostics.py

# Test de búsqueda léxica
python3 test_lexical_from_agent.py
```

---

## 🤝 Contribución

Para contribuir al proyecto:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## 📝 Licencia

Este proyecto es propiedad de [Tu Organización]. Todos los derechos reservados.

---

## 👥 Autores

- **Equipo Darwin** - Desarrollo y mantenimiento

---

## 📞 Soporte

Para soporte técnico o preguntas:
- Consulta la documentación en `docs/`
- Revisa los logs en `src/agent/logs/`
- Ejecuta diagnósticos con `network_diagnostics.py`

---

## 🔄 Changelog

### Versión 1.0.0 (Octubre 2025)
- ✅ Implementación completa del agente conversacional
- ✅ 4 herramientas de búsqueda integradas
- ✅ Prompt caching con optimización de tokens
- ✅ Sliding window conversacional
- ✅ Carga dinámica de documentos desde S3
- ✅ Logging estructurado en JSON
- ✅ Diagnósticos de red y conectividad
- ✅ Soporte para túneles SSH

---

**Última actualización**: Octubre 2025  
**Versión**: 1.0.0  
**Estado**: Producción
