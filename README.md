# Agente IA de Consulta Darwin

Sistema de agente conversacional inteligente para consulta de la base de conocimiento Darwin con capacidades de búsqueda semántica, léxica, regex, web crawler y gestión avanzada de conversaciones.

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
- **🔍 Búsqueda Multimodal**: 5 herramientas especializadas de búsqueda (semántica, léxica, regex, contenido de archivos, web crawler)
- **🌐 Web Crawler Integrado**: Búsqueda de información actualizada en internet con controles de seguridad
- **💾 Prompt Caching Avanzado**: Optimización de tokens con reducción del 60-80% en conversaciones largas
- **📊 Gestión de Contexto**: Sliding window inteligente para mantener conversaciones extensas
- **🔄 Carga Dinámica de Documentos**: Integración con S3 para actualización automática de catálogo
- **📝 Logging Estructurado**: Registro completo de interacciones LLM en formato JSON
- **🎨 Diagramas ASCII**: Visualización profesional de arquitecturas y flujos con caracteres ASCII
- **🔐 Gestión de Sesiones**: Soporte para múltiples sesiones de conversación
- **🌐 Conectividad AWS**: Soporte para túneles SSH y diagnósticos de red

### Casos de Uso

1. **Consultas Funcionales**: "¿Cómo funciona el módulo de autenticación en Darwin?"
2. **Búsqueda de Código**: "Encuentra todas las funciones que validan tokens OAuth"
3. **Análisis de Documentación**: "Resume el contenido del documento de especificaciones técnicas"
4. **Exploración de Arquitectura**: "Explica la arquitectura de microservicios de Darwin"
5. **Información Actualizada**: "¿Cuáles son las últimas actualizaciones de SAP S/4HANA?"

---

## 🏗️ Arquitectura del Sistema

### Diagrama de Arquitectura

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         AGENTE IA DARWIN                                   │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────┐    ┌─────────-─────┐    ┌─-─────────────┐                │
│  │Chat Interface│◄──►│Request Handler│◄──►│LLM Comm Module│                │
│  │              │    │(Orchestrator) │    │               │                │
│  │• Input Mgmt  │    │• Flow Control │    │• AWS Bedrock  │                │
│  │• Display     │    │• State Mgmt   │    │• Prompt Cache │                │
│  │• Streaming   │    │• XML Parser   │    │• Streaming    │                │
│  └──────────────┘    └──────────-────┘    └───-───────────┘                │
│         │                     │                     │                      │
│         │            ┌──────────────┐               │                      │
│         │            │Tool Execution│               │                      │
│         │            │    Engine    │               │                      │
│         │            │• XML Parser  │               │                      │
│         │            │• Tool Router │               │                      │
│         │            │• App Context │               │                      │
│         │            └──────────────┘               │                      │
│         │                     │                     │                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │Response      │    │Config Manager│    │Knowledge Base│                  │
│  │Formatter     │    │              │    │  Interface   │                  │
│  │• Formatting  │    │• YAML Config │    │• Semantic    │                  │
│  │• Filtering   │    │• Validation  │    │• Lexical     │                  │
│  │• Markdown    │    │• Multi-App   │    │• Regex       │                  │
│  └──────────────┘    └──────────────┘    │• File Content│                  │
│                                          │• Web Crawler │                  │
│                                          └──────────────┘                  │
└────────────────────────────────────────────────────────────────────────────┘
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
                    │ <web_crawler> → Internet          │
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
- Soporte multi-aplicación (Darwin, SAP, MuleSoft)

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
- **Streaming de respuestas**: Visualización en tiempo real

**Configuración**:
```yaml
llm:
  model_id: "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
  max_tokens: 4000
  temperature: 0.1
  max_retries: 3
```

### 4. Streaming State Machine (`src/agent/streaming_state_machine.py`)

**Responsabilidad**: Procesamiento de respuestas streaming del LLM

**Funcionalidades**:
- Máquina de estados para procesamiento de bloques XML
- Detección de tags de herramientas
- Limpieza de markdown (```xml, ``` `)
- Visualización en tiempo real de respuestas

### 5. Streaming Display (`src/agent/streaming_display.py`)

**Responsabilidad**: Visualización de respuestas streaming

**Funcionalidades**:
- Display de texto en tiempo real
- Indicadores visuales de herramientas
- Formateo de colores
- Limpieza de líneas extra

### 6. Tool Executor (`src/agent/tool_executor.py`)

**Responsabilidad**: Ejecución de herramientas de búsqueda

**Funcionalidades**:
- Parsing de tags XML en respuestas LLM
- Enrutamiento a herramientas específicas
- **Inyección automática de app_name** para web_crawler
- Consolidación de resultados múltiples
- Manejo de errores de herramientas
- Logging detallado de ejecuciones

### 7. Session Manager (`src/agent/session_manager.py`)

**Responsabilidad**: Gestión de sesiones de conversación

**Funcionalidades**:
- Creación y gestión de sesiones
- Persistencia de historial conversacional
- Recuperación de sesiones anteriores
- Limpieza de sesiones antiguas

### 8. S3 Summaries Loader (`src/agent/s3_summaries_loader.py`)

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

### 9. Configuration Manager (`src/agent/config_manager.py`)

**Responsabilidad**: Gestión centralizada de configuración

**Funcionalidades**:
- Carga de configuración multi-aplicación
- Validación de configuración
- Acceso a configuración por secciones
- Soporte para valores por defecto

---

## 🔍 Herramientas de Búsqueda

### 1. Semantic Search

**Descripción**: Búsqueda semántica usando embeddings vectoriales (Amazon Titan)

**Uso en XML**:
```xml
<tool_semantic_search>
<query>módulos principales Darwin arquitectura componentes</query>
<top_k>10</top_k>
<min_score>0.2</min_score>
<file_types>["docx", "pdf"]</file_types>
</tool_semantic_search>
```

**Parámetros**:
- `query` (requerido): Descripción conceptual de lo que se busca
- `top_k` (opcional): Número de resultados (default: 10)
- `min_score` (opcional): Puntuación mínima 0.0-1.0 (default: 0.5, recomendado: 0.0-0.3 para KNN)
- `file_types` (opcional): Filtrar por tipos de archivo

**Casos de Uso**:
- Búsquedas conceptuales: "¿Cómo funciona la autenticación?"
- Búsquedas por significado, no palabras exactas
- Encontrar documentación relacionada

### 2. Lexical Search

**Descripción**: Búsqueda textual tradicional (BM25) con coincidencias exactas

**Uso en XML**:
```xml
<tool_lexical_search>
<query>authenticateUser validateToken</query>
<fields>["content", "file_name"]</fields>
<operator>AND</operator>
<top_k>20</top_k>
<fuzzy>false</fuzzy>
</tool_lexical_search>
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
<tool_regex_search>
<pattern>function\s+\w+\s*\([^)]*\)\s*\{</pattern>
<file_types>["js", "ts"]</file_types>
<case_sensitive>false</case_sensitive>
<max_matches_per_file>50</max_matches_per_file>
<context_lines>3</context_lines>
</tool_regex_search>
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
<tool_get_file_content>
<file_path>FD-Darwin_Funcional0_v2.9.docx</file_path>
<include_metadata>true</include_metadata>
</tool_get_file_content>
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

### 5. Web Crawler (NUEVO)

**Descripción**: Búsqueda de información actualizada en internet con controles de seguridad

**Uso en XML**:
```xml
<tool_web_crawler>
<url>https://docs.mulesoft.com/mule-runtime/latest</url>
<max_pages>3</max_pages>
<keywords>["API", "integration", "connector"]</keywords>
</tool_web_crawler>
```

**Parámetros**:
- `url` (requerido): URL a explorar
- `max_pages` (opcional): Máximo de páginas a seguir (default: 1)
- `keywords` (opcional): Palabras clave para filtrar contenido relevante

**Características de Seguridad**:
- **Validación de URLs**: Solo dominios permitidos por aplicación
- **Filtrado de keywords**: Validación de términos relacionados con la aplicación
- **Caching**: Almacenamiento de resultados para evitar requests duplicados
- **Rate limiting**: Control de frecuencia de requests
- **Anti-bot detection**: Estrategias para evitar bloqueos

**Configuración por Aplicación**:
```yaml
web_crawler:
  darwin:
    allowed_domains:
      - "docs.oracle.com"
      - "developer.salesforce.com"
    required_keywords:
      - "darwin"
      - "naturgy"
  
  mulesoft:
    allowed_domains:
      - "docs.mulesoft.com"
      - "help.mulesoft.com"
    required_keywords:
      - "mulesoft"
      - "anypoint"
  
  sap:
    allowed_domains:
      - "help.sap.com"
      - "support.sap.com"
    required_keywords:
      - "sap"
      - "s/4hana"
```

**Casos de Uso**:
- Obtener información actualizada de documentación oficial
- Buscar release notes y actualizaciones
- Consultar mejores prácticas actuales
- Verificar información de APIs y servicios

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

2. **Configurar archivos de configuración por aplicación**:
   - `config/config_darwin.yaml` - Configuración para Darwin
   - `config/config_mulesoft.yaml` - Configuración para MuleSoft
   - `config/config_sap.yaml` - Configuración para SAP

3. **Configurar System Prompts**:
   - `config/system_prompt_darwin.md` - Prompt para Darwin
   - `config/system_prompt_mulesoft.md` - Prompt para MuleSoft
   - `config/system_prompt_sap.md` - Prompt para SAP

4. **Configurar Web Crawler** (opcional):
   - `config/web_crawler_config.yaml` - Configuración de dominios y keywords permitidos

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
# Darwin (por defecto)
python3 src/agent/main.py

# MuleSoft
python3 src/agent/main.py --app mulesoft

# SAP
python3 src/agent/main.py --app sap
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

#### Ejemplo 3: Información Actualizada de Internet
```
Usuario: ¿Cuáles son las últimas actualizaciones de MuleSoft Runtime?

Agente: Voy a buscar información actualizada en la documentación oficial...
[Ejecuta web_crawler internamente]

Agente: Las últimas actualizaciones de MuleSoft Runtime incluyen:
1. Mule 4.5 - Mejoras en performance
2. Nuevos conectores para servicios cloud
...
```

#### Ejemplo 4: Diagrama de Arquitectura
```
Usuario: Explica la arquitectura de integración entre Salesforce, MuleSoft y SAP

Agente: La arquitectura de integración sigue este flujo:

┌─────────────────────────────────────────────────────────────────┐
│                  ARQUITECTURA DE INTEGRACIONES                  │
└─────────────────────────────────────────────────────────────────┘

                    SALESFORCE (Front-End)
                            │
                            │ JSON con datos del proceso
                            │
                            ▼
              ┌──────────────────────────────┐
              │   MULESOFT (Orquestación)    │
              │  - Gestión de errores        │
              │  - Reprocesamiento           │
              └──────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Cliente  │  │  Punto   │  │  Cuenta  │
        │          │  │Suministro│  │ Contrato │
        └──────────┘  └──────────┘  └──────────┘
                            │
                            ▼
                    SAP ISU (Back-End)
              ┌──────────────────────────┐
              │   Base de Datos SAP ISU  │
              └──────────────────────────┘
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

### 3. Streaming de Respuestas

Visualización en tiempo real de las respuestas del LLM:

- **Máquina de estados**: Procesamiento de bloques XML
- **Indicadores visuales**: Herramientas en ejecución
- **Limpieza automática**: Eliminación de markdown innecesario
- **Experiencia fluida**: Respuestas progresivas

### 4. Diagramas ASCII Profesionales

El agente genera diagramas profesionales usando caracteres ASCII:

**Caracteres disponibles**:
- Cajas: `┌─┐ └─┘`
- Líneas: `│ ─`
- Conectores: `├─┤ ┬ ┴ ┼`
- Flechas: `→ ← ↑ ↓ ▶ ◀ ▲ ▼`

**Tipos de diagramas**:
- Flujos secuenciales
- Flujos con decisiones
- Arquitecturas de capas
- Componentes relacionados

### 5. Gestión de Sesiones

Soporte para múltiples sesiones de conversación:

- **Persistencia**: Historial guardado entre sesiones
- **Recuperación**: Continuar conversaciones anteriores
- **Limpieza**: Eliminación automática de sesiones antiguas
- **Aislamiento**: Cada sesión mantiene su propio contexto

### 6. Carga Dinámica de Documentos

Los resúmenes de documentos se cargan dinámicamente desde S3:

- **Bucket S3**: `rag-system-darwin-eu-west-1`
- **Actualización automática**: Al iniciar el agente
- **Simplificación**: Solo campos esenciales
- **Integración**: Marcador `{{DYNAMIC_SUMMARIES}}` en system prompt

### 7. Logging Estructurado

Registro completo de todas las interacciones:

- **Formato JSON**: Logs estructurados en `src/agent/logs/`
- **Información completa**: Requests, responses, herramientas ejecutadas
- **Timestamps**: Marca temporal de cada interacción
- **Métricas**: Tokens usados, tiempo de ejecución

### 8. Diagnósticos de Red

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
│   ├── config_darwin.yaml             # Configuración Darwin
│   ├── config_mulesoft.yaml           # Configuración MuleSoft
│   ├── config_sap.yaml                # Configuración SAP
│   ├── system_prompt_darwin.md        # System prompt Darwin
│   ├── system_prompt_mulesoft.md      # System prompt MuleSoft
│   ├── system_prompt_sap.md           # System prompt SAP
│   └── web_crawler_config.yaml        # Configuración web crawler
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
│   │   ├── session_manager.py         # Gestión de sesiones
│   │   ├── streaming_state_machine.py # Máquina de estados streaming
│   │   ├── streaming_display.py       # Display de streaming
│   │   ├── color_utils.py             # Utilidades de colores
│   │   └── logs/                      # Logs de conversaciones
│   │
│   ├── tools/                         # Herramientas de búsqueda
│   │   ├── __init__.py
│   │   ├── tool_semantic_search.py    # Búsqueda semántica
│   │   ├── tool_lexical_search.py     # Búsqueda léxica
│   │   ├── tool_regex_search.py       # Búsqueda por regex
│   │   ├── tool_get_file_content.py   # Obtención de archivos
│   │   ├── tool_web_crawler.py        # Web crawler (NUEVO)
│   │   └── cache/                     # Cache de web crawler
│   │
│   ├── common/                        # Utilidades compartidas
│   │   ├── __init__.py
│   │   └── common.py                  # Config, OpenSearch, Bedrock clients
│   │
│   ├── utils/                         # Utilidades del sistema
│   │   ├── __init__.py
│   │   ├── network_diagnostics.py     # Diagnósticos de red
│   │   ├── update_system_prompt.py    # Actualización de prompt
│   │   ├── update_system_prompt_webcrawler.py  # Actualización web crawler
│   │   ├── generate_system_prompt_example.py   # Generación de ejemplos
│   │   └── process_summaries.py       # Procesamiento de resúmenes
│   │
│   └── ssh_tunnel/                    # Herramientas de tunelización
│       ├── __init__.py
│       ├── aws_tunnel.py              # Cliente de túnel SSH
│       ├── setup_tunnel.sh            # Script de configuración
│       ├── start_tunnel_background.sh # Túnel en background
│       └── start_tunnel_direct.sh     #
