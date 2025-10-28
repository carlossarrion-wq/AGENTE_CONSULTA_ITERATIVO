# Knowledge Base Search Tool

Herramienta simplificada para buscar fragmentos en la base de conocimiento OpenSearch del sistema DARWIN.

## Descripción

Esta herramienta permite realizar búsquedas híbridas (vectoriales + textuales) en la base de conocimiento OpenSearch, devolviendo fragmentos relevantes con información del documento origen y puntuación de relevancia.

## Características

- **Búsqueda híbrida**: Combina búsqueda vectorial (embeddings) y textual (keywords)
- **Parámetros configurables**: `top_k` y `min_score` opcionales
- **Salida JSON estructurada**: Formato consistente para integración
- **Múltiples aplicaciones**: Soporte para darwin, sap, mulesoft
- **Logging detallado**: Información de debug y rendimiento

## Instalación

### Requisitos

- Python 3.8+
- Acceso a AWS (credenciales configuradas)
- Acceso a la VPC donde está OpenSearch
- Dependencias del sistema RAG

### Dependencias

La herramienta utiliza las dependencias del sistema RAG ubicado en:
```
/Users/csarrion/Cline/RAG_MULTI_APLICACION/RAG_SYSTEM_MULTI_v5
```

## Uso

### Línea de comandos

```bash
# Búsqueda básica
python3 knowledge_search.py "alta de usuarios"

# Con parámetros opcionales
python3 knowledge_search.py "configuración canal" --top_k 5 --min_score 1.0

# Salida formateada
python3 knowledge_search.py "integración siebel" --pretty

# Guardar en archivo
python3 knowledge_search.py "dashboard" --output resultados.json

# Especificar aplicación
python3 knowledge_search.py "consulta" --app sap
```

### Parámetros

- **query** (obligatorio): Texto a buscar
- **--top_k** (opcional): Número máximo de resultados (por defecto: 10)
- **--min_score** (opcional): Puntuación mínima (por defecto: 0.0)
- **--app** (opcional): Aplicación (darwin, sap, mulesoft) (por defecto: darwin)
- **--config** (opcional): Ruta al archivo de configuración
- **--output** (opcional): Archivo de salida JSON
- **--pretty** (opcional): Mostrar salida formateada

### Uso programático

```python
from knowledge_search import KnowledgeSearchTool

# Inicializar herramienta
search_tool = KnowledgeSearchTool(application="darwin")

# Realizar búsqueda
results = search_tool.search(
    query="alta de usuarios",
    top_k=5,
    min_score=1.0
)

# Procesar resultados
for fragment in results["fragments"]:
    print(f"Archivo: {fragment['file_name']}")
    print(f"Relevancia: {fragment['relevance']}")
    print(f"Resumen: {fragment['summary']}")
```

## Formato de salida

### Estructura JSON

```json
{
  "query": "texto buscado",
  "parameters": {
    "top_k": 10,
    "min_score": 0.0
  },
  "timestamp": "2025-10-26T17:47:53.236000",
  "duration_seconds": 2.345,
  "total_found": 5,
  "fragments": [
    {
      "file_name": "Manual alta usuarios PRE.docx",
      "relevance": 0.95,
      "summary": "Este documento describe el proceso de alta de usuarios en el sistema DARWIN PRE..."
    }
  ]
}
```

### Campos de salida

- **query**: Texto de búsqueda utilizado
- **parameters**: Parámetros de búsqueda aplicados
- **timestamp**: Momento de ejecución de la búsqueda
- **duration_seconds**: Tiempo de ejecución en segundos
- **total_found**: Número total de fragmentos encontrados
- **fragments**: Lista de fragmentos encontrados
  - **file_name**: Nombre del documento origen
  - **relevance**: Puntuación de relevancia (0.0 - 1.0+)
  - **summary**: Resumen del fragmento (de metadata o contenido truncado)

## Ejemplos de uso

### Búsqueda de documentación técnica

```bash
python3 knowledge_search.py "migración base de datos" --top_k 3 --pretty
```

### Búsqueda de procesos específicos

```bash
python3 knowledge_search.py "alta canal ventas" --min_score 0.5 --output canal_docs.json
```

### Búsqueda en aplicación específica

```bash
python3 knowledge_search.py "configuración" --app mulesoft --top_k 10
```

## Configuración

La herramienta utiliza el archivo de configuración del sistema RAG:
```
/Users/csarrion/Cline/RAG_MULTI_APLICACION/RAG_SYSTEM_MULTI_v5/config/multi_app_config.yaml
```

### Configuración personalizada

```bash
python3 knowledge_search.py "query" --config /path/to/custom/config.yaml
```

## Troubleshooting

### Error de conexión a OpenSearch

```
ConnectionTimeout: Connection to vpc-rag-opensearch-... timed out
```

**Solución**: Verificar que tienes acceso a la VPC donde está OpenSearch. Esto requiere:
- Conexión VPN a AWS
- Permisos de acceso a la VPC
- Configuración correcta de security groups

### Error de importación

```
ImportError: Las dependencias del sistema RAG no están disponibles
```

**Solución**: Verificar que el sistema RAG está disponible en la ruta esperada:
```
/Users/csarrion/Cline/RAG_MULTI_APLICACION/RAG_SYSTEM_MULTI_v5
```

### Error de credenciales AWS

```
NoCredentialsError: Unable to locate credentials
```

**Solución**: Configurar credenciales AWS:
```bash
aws configure
# o
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

## Rendimiento

- **Búsqueda típica**: 2-5 segundos
- **Búsqueda compleja**: 5-10 segundos
- **Factores que afectan**: tamaño del índice, complejidad de la query, latencia de red

## Limitaciones

- Requiere acceso a la VPC de AWS donde está OpenSearch
- Dependiente del sistema RAG existente
- Limitado por los documentos indexados en OpenSearch
- Puntuaciones de relevancia pueden variar según el tipo de búsqueda

## Desarrollo

### Estructura del código

- `KnowledgeSearchTool`: Clase principal
- `search()`: Método principal de búsqueda
- `_search_vector()`: Búsqueda vectorial
- `_search_text()`: Búsqueda textual
- `_combine_results()`: Combinación y deduplicación

### Extensiones posibles

- Filtros por tipo de documento
- Búsqueda por fechas
- Agrupación por documentos
- Cache de resultados
- Métricas de uso
