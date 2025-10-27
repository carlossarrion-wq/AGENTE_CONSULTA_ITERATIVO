# Agente de Consulta Darwin - Herramientas de Búsqueda

Sistema de herramientas de búsqueda para la base de conocimiento Darwin, implementado con OpenSearch y AWS Bedrock.

## 🚀 Características

- **Búsqueda Semántica**: Búsqueda por significado conceptual usando embeddings vectoriales
- **Búsqueda Léxica**: Búsqueda textual tradicional con BM25 y highlighting
- **Búsqueda por Regex**: Patrones de expresiones regulares con contexto
- **Obtención de Archivos**: Reconstrucción completa de archivos desde chunks indexados

## 📋 Requisitos Previos

- Python 3.8+
- AWS CLI configurado con credenciales válidas
- Acceso a OpenSearch cluster Darwin
- Acceso a AWS Bedrock (región eu-west-1)

## 🛠️ Instalación

### 1. Clonar o descargar el proyecto

```bash
git clone <repository-url>
cd AGENTE_CONSULTA_ITERATIVO
```

### 2. Crear entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip3 install -r requirements.txt
```

### 4. Configurar AWS CLI

```bash
aws configure
# Introducir:
# - AWS Access Key ID
# - AWS Secret Access Key  
# - Default region: eu-west-1
# - Default output format: json
```

### 5. Verificar configuración

```bash
aws sts get-caller-identity
```

## ⚙️ Configuración

El archivo `config/config.yaml` contiene toda la configuración necesaria. Los valores por defecto están optimizados para el entorno Darwin.

### Configuración Principal

```yaml
opensearch:
  host: "vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com"
  index_name: "rag-documents-darwin"

bedrock:
  region_name: "eu-west-1"
  model_id: "amazon.titan-embed-image-v1"

s3:
  bucket_name: "rag-system-darwin-eu-west-1"
  region_name: "eu-west-1"
```

## 🔍 Herramientas de Búsqueda

### 1. Búsqueda Semántica

Busca contenido por significado conceptual usando embeddings vectoriales.

#### Uso Básico

```bash
python3 src/semantic_search.py "¿Cómo configurar autenticación OAuth?"
```

#### Opciones Avanzadas

```bash
python3 src/semantic_search.py "machine learning algorithms" \
  --top-k 20 \
  --min-score 0.7 \
  --file-types pdf docx \
  --output json
```

#### Parámetros

- `query`: Consulta semántica (requerido)
- `--top-k`: Número máximo de resultados (default: 10)
- `--min-score`: Puntuación mínima de similitud 0.0-1.0 (default: 0.5)
- `--file-types`: Filtrar por extensiones de archivo
- `--output`: Formato de salida `json|pretty` (default: pretty)

#### Ejemplo de Salida

```
🔍 Búsqueda semántica: '¿Cómo configurar autenticación OAuth?'
📊 Resultados encontrados: 5
================================================================================

1. 📄 oauth_configuration_guide.pdf
   🎯 Relevancia: 0.892
   🔗 Chunk ID: chunk_001
   📝 Contenido: Para configurar OAuth 2.0 en tu aplicación, primero debes...
   ℹ️  Tipo: pdf, Tamaño: 245760 bytes
```

### 2. Búsqueda Léxica

Búsqueda textual tradicional usando BM25 con highlighting de coincidencias.

#### Uso Básico

```bash
python3 src/lexical_search.py "configuración base de datos"
```

#### Opciones Avanzadas

```bash
python3 src/lexical_search.py "API REST endpoint" \
  --fields content file_name \
  --operator AND \
  --top-k 15 \
  --fuzzy \
  --output json
```

#### Parámetros

- `query`: Términos de búsqueda exactos (requerido)
- `--fields`: Campos donde buscar `content|file_name|metadata.summary`
- `--operator`: Operador lógico `AND|OR` (default: OR)
- `--top-k`: Número máximo de resultados (default: 10)
- `--fuzzy`: Permitir coincidencias aproximadas
- `--output`: Formato de salida `json|pretty`

#### Ejemplo de Salida

```
🔍 Búsqueda léxica: 'configuración base de datos'
🏷️  Términos: configuración, base, de, datos
📊 Resultados encontrados: 8
================================================================================

1. 📄 database_setup.md
   🎯 Score: 12.456
   🔗 Chunk ID: chunk_042
   🎯 Coincidencias:
      • content: La <em>configuración</em> de la <em>base</em> <em>de</em> <em>datos</em> requiere...
   📝 Vista previa: Para establecer la conexión con la base de datos...
```

### 3. Búsqueda por Regex

Búsqueda mediante patrones de expresiones regulares con contexto.

#### Uso Básico

```bash
python3 src/regex_search.py "function\s+\w+\s*\("
```

#### Opciones Avanzadas

```bash
python3 src/regex_search.py "class\s+(\w+)" \
  --file-types py js ts \
  --case-sensitive \
  --max-matches-per-file 10 \
  --context-lines 3 \
  --output json
```

#### Parámetros

- `pattern`: Expresión regular (requerido)
- `--file-types`: Filtrar por extensiones de archivo
- `--case-sensitive`: Búsqueda sensible a mayúsculas
- `--max-matches-per-file`: Máximo coincidencias por archivo (default: 50)
- `--context-lines`: Líneas de contexto antes/después (default: 2)
- `--output`: Formato de salida `json|pretty`

#### Patrones Útiles

```bash
# Buscar funciones JavaScript/Python
python3 src/regex_search.py "function\s+\w+|def\s+\w+"

# Buscar URLs
python3 src/regex_search.py "https?://[^\s]+"

# Buscar emails
python3 src/regex_search.py "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

# Buscar números de teléfono
python3 src/regex_search.py "\+?[0-9]{1,4}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}"
```

#### Ejemplo de Salida

```
🔍 Búsqueda regex: 'function\s+\w+\s*\('
📊 Total coincidencias: 15 en 6 archivos
================================================================================

1. 📄 utils.js
   🔗 Chunk ID: chunk_089
   🎯 Coincidencias: 3

   Match 1 (línea 42):
   🎯 Coincidencia: 'function validateInput('
   📝 Contexto anterior:
      // Validación de entrada de usuario
      
   ➤  function validateInput(data) {
   📝 Contexto posterior:
      if (!data || typeof data !== 'object') {
        return false;
```

### 4. Obtención de Contenido de Archivos

Reconstruye archivos completos desde chunks indexados, manejando overlaps automáticamente.

#### Uso Básico

```bash
python3 src/get_file_content.py "manual_usuario.pdf"
```

#### Opciones Avanzadas

```bash
python3 src/get_file_content.py "api_documentation.md" \
  --include-metadata \
  --save-to "local_copy.md" \
  --output content-only
```

#### Parámetros

- `file_path`: Nombre del archivo (requerido)
- `--include-metadata`: Incluir metadatos adicionales
- `--save-to`: Guardar contenido en archivo local
- `--output`: Formato `json|pretty|content-only`

#### Ejemplo de Salida

```
📄 Archivo: manual_usuario.pdf
📊 Estadísticas:
   • Total chunks: 24
   • Longitud contenido: 45,678 caracteres
   • Manejo de overlaps: applied
   • Tipo: pdf
   • Tamaño original: 2,456,789 bytes
   • Rango chunks: 1 - 24

================================================================================
📝 CONTENIDO:
================================================================================
# Manual de Usuario - Sistema Darwin

## Introducción

Este manual proporciona una guía completa para el uso del sistema...

... [Contenido truncado. Total: 45,678 caracteres]
💡 Usa --output content-only para ver el contenido completo
💡 Usa --save-to archivo.txt para guardar en archivo
```

## 📊 Ejemplos de Uso Práctico

### Flujo de Trabajo Típico

1. **Búsqueda exploratoria** (semántica):
```bash
python3 src/semantic_search.py "configuración de seguridad en aplicaciones web"
```

2. **Búsqueda específica** (léxica):
```bash
python3 src/lexical_search.py "HTTPS SSL certificate" --operator AND
```

3. **Búsqueda de patrones** (regex):
```bash
python3 src/regex_search.py "password.*=.*['\"].*['\"]" --file-types js py
```

4. **Obtener archivo completo**:
```bash
python3 src/get_file_content.py "security_best_practices.md" --save-to security.md
```

### Casos de Uso Específicos

#### Análisis de Código
```bash
# Buscar todas las funciones
python3 src/regex_search.py "def\s+\w+|function\s+\w+" --file-types py js

# Buscar imports/includes
python3 src/regex_search.py "import\s+.*|#include\s+.*|require\s*\(" --context-lines 1
```

#### Documentación Técnica
```bash
# Buscar conceptos relacionados
python3 src/semantic_search.py "microservicios arquitectura contenedores" --top-k 20

# Buscar términos específicos
python3 src/lexical_search.py "Docker Kubernetes deployment" --fuzzy
```

#### Configuración y Setup
```bash
# Buscar archivos de configuración
python3 src/regex_search.py "\.env|config\..*|settings\..*" --file-types env yaml json

# Buscar procedimientos de instalación
python3 src/semantic_search.py "instalación configuración inicial setup"
```

## 🔧 Configuración Avanzada

### Variables de Entorno

Puedes sobrescribir la configuración usando variables de entorno:

```bash
export OPENSEARCH_HOST="tu-cluster.es.amazonaws.com"
export BEDROCK_REGION="eu-west-1"
export LOG_LEVEL="DEBUG"
```

### Configuración de Cache

El sistema incluye cache automático para mejorar el rendimiento:

```yaml
cache:
  enabled: true
  max_size_mb: 100
  ttl_seconds: 3600
```

### Configuración de Logging

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "logs/search_tools.log"
```

## 🚨 Solución de Problemas

### Error de Autenticación AWS

```bash
# Verificar credenciales
aws sts get-caller-identity

# Reconfigurar si es necesario
aws configure
```

### Error de Conexión a OpenSearch

```bash
# Verificar conectividad
curl -I https://vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com

# Verificar permisos IAM
aws iam get-user
```

### Error de Bedrock

```bash
# Verificar acceso a Bedrock
aws bedrock list-foundation-models --region eu-west-1
```

### Problemas de Rendimiento

1. **Ajustar límites de tiempo**:
```yaml
limits:
  max_search_time_seconds: 60  # Aumentar timeout
```

2. **Optimizar cache**:
```yaml
cache:
  max_size_mb: 200  # Aumentar tamaño de cache
```

3. **Reducir resultados**:
```bash
python3 src/semantic_search.py "query" --top-k 5 --min-score 0.8
```

### Logs de Debug

Para obtener información detallada:

```bash
# Activar logging debug
export LOG_LEVEL=DEBUG

# Ejecutar herramienta
python3 src/semantic_search.py "test query"

# Ver logs
tail -f logs/search_tools.log
```

## 📁 Estructura del Proyecto

```
AGENTE_CONSULTA_ITERATIVO/
├── config/
│   └── config.yaml              # Configuración principal
├── src/
│   ├── common.py               # Utilidades compartidas
│   ├── semantic_search.py      # Búsqueda semántica
│   ├── lexical_search.py       # Búsqueda léxica
│   ├── regex_search.py         # Búsqueda regex
│   └── get_file_content.py     # Obtención de archivos
├── logs/                       # Logs del sistema (auto-creado)
├── requirements.txt            # Dependencias Python
└── README.md                   # Esta documentación
```

## 🔒 Seguridad

- Las credenciales AWS se obtienen del AWS CLI configurado
- No se almacenan credenciales en el código
- Todas las conexiones usan HTTPS/TLS
- Los logs no incluyen información sensible

## 🚀 Rendimiento

### Optimizaciones Implementadas

- **Cache inteligente**: Resultados frecuentes se cachean automáticamente
- **Scroll API**: Para archivos grandes con muchos chunks
- **Batch processing**: Procesamiento eficiente de múltiples chunks
- **Timeouts configurables**: Evita consultas que cuelguen

### Métricas de Rendimiento

Las herramientas registran automáticamente:
- Tiempo de respuesta
- Número de resultados
- Uso de cache
- Errores y reintentos

## 🤝 Contribución

Para contribuir al proyecto:

1. Crear rama feature: `git checkout -b feature/nueva-funcionalidad`
2. Realizar cambios y tests
3. Commit: `git commit -m "Descripción del cambio"`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

## 📄 Licencia

Este proyecto es parte del sistema Darwin y está sujeto a las políticas internas de la organización.

## 📞 Soporte

Para soporte técnico:
- Revisar logs en `logs/search_tools.log`
- Verificar configuración AWS
- Consultar documentación de OpenSearch
- Contactar al equipo de desarrollo Darwin

---

**Versión**: 1.0.0  
**Última actualización**: Octubre 2025  
**Compatibilidad**: Python 3.8+, AWS SDK v2
