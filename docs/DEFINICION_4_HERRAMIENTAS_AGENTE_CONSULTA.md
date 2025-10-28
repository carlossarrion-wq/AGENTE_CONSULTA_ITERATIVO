# DEFINICIÓN TÉCNICA Y FUNCIONAL DE LAS 4 HERRAMIENTAS DEL AGENTE DE CONSULTA

## ARQUITECTURA GENERAL

### Configuración Base
- **OpenSearch Endpoint**: `vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com`
- **Índice**: `rag-documents-darwin`
- **Región AWS**: `eu-west-1`
- **Modelo de Embeddings**: `amazon.titan-embed-image-v1` (1024 dimensiones) - Modelo multimodal para texto e imágenes

### Dependencias Python
```python
import boto3
import json
from opensearchpy import OpenSearch
import re
from typing import List, Dict, Optional, Any
```

---

## 1. SEMANTIC_SEARCH

### Descripción Funcional
Realiza búsquedas semánticas usando embeddings vectoriales para encontrar contenido por significado conceptual, no solo por palabras exactas.

### Entrada XML
```xml
<semantic_search>
<query>módulos principales Darwin arquitectura componentes</query>
<top_k>10</top_k>
<min_score>0.5</min_score>
<file_types>["docx", "pdf"]</file_types>
</semantic_search>
```

### Parámetros
- `query` (requerido): Descripción conceptual de lo que se busca
- `top_k` (opcional): Número de resultados más relevantes (default: 10)
- `min_score` (opcional): Puntuación mínima de similitud 0.0-1.0 (default: 0.5)
- `file_types` (opcional): Filtrar por tipos de archivo, array (ej: ["docx", "pdf", "xlsx"])

### Implementación Técnica
```python
def semantic_search(query: str, top_k: int = 10, min_score: float = 0.5, file_types: List[str] = None) -> Dict[str, Any]:
    try:
        # 1. Generar embedding con Bedrock
        bedrock_client = boto3.client('bedrock-runtime', region_name='eu-west-1')
        embedding_response = bedrock_client.invoke_model(
            modelId="amazon.titan-embed-image-v1",  # Modelo multimodal para texto e imágenes
            body=json.dumps({
                "inputText": query, 
                "embeddingConfig": {"outputEmbeddingLength": 1024}
            })
        )
        query_embedding = json.loads(embedding_response['body'].read())['embedding']
        
        # 2. Construir query de búsqueda KNN
        search_body = {
            "size": top_k,
            "query": {
                "knn": {
                    "embedding_vector": {
                        "vector": query_embedding,
                        "k": top_k
                    }
                }
            },
            "_source": ["content", "file_name", "metadata", "chunk_id"],
            "min_score": min_score
        }
        
        # 3. Filtrar por tipos de archivo si se especifica
        if file_types:
            search_body["query"] = {
                "bool": {
                    "must": [search_body["query"]],
                    "filter": {
                        "terms": {"metadata.file_extension": file_types}
                    }
                }
            }
        
        # 4. Ejecutar búsqueda en OpenSearch
        opensearch_client = OpenSearch([{
            'host': 'vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com', 
            'port': 443,
            'use_ssl': True
        }])
        
        response = opensearch_client.search(index="rag-documents-darwin", body=search_body)
        
        # 5. Formatear resultados
        return format_semantic_results(response, query)
        
    except Exception as e:
        return {"error": f"Error en semantic_search: {str(e)}"}

def format_semantic_results(response: Dict, query: str) -> Dict[str, Any]:
    fragments = []
    for hit in response['hits']['hits']:
        source = hit['_source']
        fragments.append({
            "file_name": source['file_name'],
            "relevance": hit['_score'],
            "summary": source['content'],  # Contenido del chunk, no resumen del documento
            "chunk_id": source.get('chunk_id', 'unknown'),
            "metadata": source.get('metadata', {})
        })
    
    return {
        "query": query,
        "total_found": len(fragments),
        "fragments": fragments
    }
```

### Salida JSON
```json
{
  "query": "módulos principales Darwin arquitectura componentes",
  "total_found": 5,
  "fragments": [
    {
      "file_name": "FD-Darwin_Funcional0_v2.9.docx",
      "relevance": 0.89,
      "summary": "El módulo de Contratación del sistema DARWIN incluye procesos de contratación asistida y no asistida, lógica de búsqueda de direcciones, validaciones y scoring, manejo del bono social e integración con sistemas externos como Siebel, Salesforce y Aviva...",
      "chunk_id": "chunk_001",
      "metadata": {
        "file_size": 14237785,
        "file_extension": "docx"
      }
    }
  ]
}
```

---

## 2. LEXICAL_SEARCH

### Descripción Funcional
Búsqueda textual tradicional (BM25) basada en coincidencias exactas de palabras y términos. Más precisa para palabras clave específicas.

### Entrada XML
```xml
<lexical_search>
<query>authenticateUser validateToken</query>
<fields>["content", "filename"]</fields>
<operator>AND</operator>
<top_k>20</top_k>
<fuzzy>false</fuzzy>
</lexical_search>
```

### Parámetros
- `query` (requerido): Términos de búsqueda exactos
- `fields` (opcional): Campos donde buscar: ["content", "filename", "summary"] (default: ["content"])
- `operator` (opcional): Operador lógico "AND" | "OR" (default: "OR")
- `top_k` (opcional): Número de resultados (default: 10)
- `fuzzy` (opcional): Permitir coincidencias aproximadas (true/false, default: false)

### Implementación Técnica
```python
def lexical_search(query: str, fields: List[str] = ["content"], operator: str = "OR", 
                  top_k: int = 10, fuzzy: bool = False) -> Dict[str, Any]:
    try:
        # 1. Configurar query multi_match
        query_config = {
            "query": query,
            "fields": fields,
            "operator": operator.lower(),
            "type": "best_fields"
        }
        
        # 2. Añadir fuzzy matching si se solicita
        if fuzzy:
            query_config["fuzziness"] = "AUTO"
        
        # 3. Construir búsqueda con highlighting
        search_body = {
            "size": top_k,
            "query": {"multi_match": query_config},
            "_source": ["content", "file_name", "metadata", "chunk_id"],
            "highlight": {
                "fields": {field: {"fragment_size": 150, "number_of_fragments": 3} for field in fields}
            }
        }
        
        # 4. Ejecutar búsqueda
        opensearch_client = OpenSearch([{
            'host': 'vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com', 
            'port': 443,
            'use_ssl': True
        }])
        
        response = opensearch_client.search(index="rag-documents-darwin", body=search_body)
        
        # 5. Formatear resultados
        return format_lexical_results(response, query)
        
    except Exception as e:
        return {"error": f"Error en lexical_search: {str(e)}"}

def format_lexical_results(response: Dict, query: str) -> Dict[str, Any]:
    results = []
    for hit in response['hits']['hits']:
        source = hit['_source']
        highlights = hit.get('highlight', {})
        
        matches = []
        for field, highlight_list in highlights.items():
            for highlight in highlight_list:
                matches.append({
                    "field": field,
                    "snippet": highlight
                })
        
        results.append({
            "file_name": source['file_name'],
            "score": hit['_score'],
            "chunk_id": source.get('chunk_id', 'unknown'),
            "matches": matches,
            "metadata": source.get('metadata', {})
        })
    
    return {
        "query": query,
        "total_results": len(results),
        "results": results,
        "query_terms": query.split()
    }
```

### Salida JSON
```json
{
  "query": "authenticateUser validateToken",
  "total_results": 3,
  "results": [
    {
      "file_name": "auth_middleware.js",
      "score": 12.4,
      "chunk_id": "chunk_045",
      "matches": [
        {
          "field": "content",
          "snippet": "function <em>authenticateUser</em>(token) { ... <em>validateToken</em>(token) ..."
        }
      ],
      "metadata": {
        "file_extension": "js"
      }
    }
  ],
  "query_terms": ["authenticateUser", "validateToken"]
}
```

---

## 3. REGEX_SEARCH

### Descripción Funcional
Búsqueda mediante expresiones regulares para patrones específicos de código o texto.

### Entrada XML
```xml
<regex_search>
<pattern>function\s+\w+\s*\([^)]*\)\s*\{</pattern>
<file_types>["js", "ts"]</file_types>
<case_sensitive>false</case_sensitive>
<max_matches_per_file>50</max_matches_per_file>
<context_lines>3</context_lines>
</regex_search>
```

### Parámetros
- `pattern` (requerido): Expresión regular (sintaxis estándar)
- `file_types` (opcional): Filtrar por extensiones de archivo (array)
- `case_sensitive` (opcional): Sensible a mayúsculas (true/false, default: true)
- `max_matches_per_file` (opcional): Máximo de coincidencias por archivo (default: 50)
- `context_lines` (opcional): Líneas de contexto antes/después (default: 2)

### Implementación Técnica
```python
def regex_search(pattern: str, file_types: List[str] = None, case_sensitive: bool = True,
                max_matches_per_file: int = 50, context_lines: int = 2) -> Dict[str, Any]:
    try:
        # 1. Validar que el patrón regex es válido
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            re.compile(pattern, flags)
        except re.error as e:
            return {"error": f"Invalid regex pattern: {str(e)}"}
        
        # 2. Construir query de búsqueda
        search_body = {
            "size": 1000,  # Buscar en muchos documentos
            "query": {
                "regexp": {
                    "content": {
                        "value": pattern,
                        "flags": "ALL" if not case_sensitive else "NONE"
                    }
                }
            },
            "_source": ["content", "file_name", "metadata", "chunk_id"]
        }
        
        # 3. Filtrar por tipos de archivo si se especifica
        if file_types:
            search_body["query"] = {
                "bool": {
                    "must": [search_body["query"]],
                    "filter": {
                        "terms": {"metadata.file_extension": file_types}
                    }
                }
            }
        
        # 4. Ejecutar búsqueda
        opensearch_client = OpenSearch([{
            'host': 'vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com', 
            'port': 443,
            'use_ssl': True
        }])
        
        response = opensearch_client.search(index="rag-documents-darwin", body=search_body)
        
        # 5. Procesar matches con contexto
        return format_regex_results(response, pattern, context_lines, max_matches_per_file, flags)
        
    except Exception as e:
        return {"error": f"Error en regex_search: {str(e)}"}

def format_regex_results(response: Dict, pattern: str, context_lines: int, 
                        max_matches_per_file: int, flags: int) -> Dict[str, Any]:
    results = []
    total_matches = 0
    
    for hit in response['hits']['hits']:
        source = hit['_source']
        content = source['content']
        lines = content.split('\n')
        
        # Buscar matches en el contenido
        matches = []
        compiled_pattern = re.compile(pattern, flags)
        
        for line_num, line in enumerate(lines):
            for match in compiled_pattern.finditer(line):
                if len(matches) >= max_matches_per_file:
                    break
                
                # Extraer contexto
                start_line = max(0, line_num - context_lines)
                end_line = min(len(lines), line_num + context_lines + 1)
                
                context_before = lines[start_line:line_num]
                context_after = lines[line_num + 1:end_line]
                
                matches.append({
                    "line_number": line_num + 1,
                    "match": match.group(),
                    "context_before": context_before,
                    "context_after": context_after,
                    "full_line": line
                })
                total_matches += 1
        
        if matches:
            results.append({
                "file_name": source['file_name'],
                "chunk_id": source.get('chunk_id', 'unknown'),
                "matches": matches,
                "match_count": len(matches),
                "metadata": source.get('metadata', {})
            })
    
    return {
        "pattern": pattern,
        "total_matches": total_matches,
        "total_files": len(results),
        "results": results
    }
```

### Salida JSON
```json
{
  "pattern": "function\\s+\\w+\\s*\\([^)]*\\)\\s*\\{",
  "total_matches": 47,
  "total_files": 8,
  "results": [
    {
      "file_name": "utils_helpers.js",
      "chunk_id": "chunk_015",
      "matches": [
        {
          "line_number": 15,
          "match": "function validateEmail(email) {",
          "context_before": ["", "// Email validation utility", ""],
          "context_after": ["  const regex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;", "  return regex.test(email);", "}"],
          "full_line": "function validateEmail(email) {"
        }
      ],
      "match_count": 12,
      "metadata": {
        "file_extension": "js"
      }
    }
  ]
}
```

---

## 4. GET_FILE_CONTENT

### Descripción Funcional
Obtiene el contenido completo de un archivo específico del índice, reconstruyendo todos sus chunks.

### Entrada XML
```xml
<get_file_content>
<file_path>FD-Darwin_Funcional0_v2.9.docx</file_path>
<include_metadata>true</include_metadata>
</get_file_content>
```

### Parámetros
- `file_path` (requerido): Nombre del archivo tal como aparece en el índice
- `include_metadata` (opcional): Incluir metadatos adicionales (true/false, default: false)

### Implementación Técnica
```python
def get_file_content(file_path: str, include_metadata: bool = False) -> Dict[str, Any]:
    try:
        # 1. Buscar todos los chunks del archivo usando scroll para archivos grandes
        opensearch_client = OpenSearch([{
            'host': 'vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com', 
            'port': 443,
            'use_ssl': True
        }])
        
        search_body = {
            "size": 100,  # Procesar en lotes
            "query": {
                "term": {
                    "file_name.keyword": file_path
                }
            },
            "sort": [{"chunk_id": {"order": "asc"}}],
            "_source": ["content", "file_name", "metadata", "chunk_id", "chunk_start", "chunk_end", "overlap_info"]
        }
        
        # 2. Usar scroll para manejar archivos con muchos chunks
        all_chunks = []
        response = opensearch_client.search(
            index="rag-documents-darwin", 
            body=search_body, 
            scroll='2m'
        )
        
        while len(response['hits']['hits']) > 0:
            all_chunks.extend(response['hits']['hits'])
            if '_scroll_id' in response:
                response = opensearch_client.scroll(
                    scroll_id=response['_scroll_id'], 
                    scroll='2m'
                )
            else:
                break
        
        # 3. Verificar si se encontró el archivo
        if not all_chunks:
            return {
                "error": f"File not found: {file_path}",
                "available_files": get_available_files_sample()
            }
        
        # 4. Reconstruir contenido completo manejando overlaps
        chunks = sorted(all_chunks, key=lambda x: x['_source'].get('chunk_id', 0))
        full_content = reconstruct_content_with_overlap_handling(chunks)
        
        # 5. Preparar resultado
        result = {
            "file_path": file_path,
            "content": full_content,
            "total_chunks": len(chunks),
            "content_length": len(full_content),
            "overlap_handling": "applied"
        }
        
        # 6. Incluir metadata si se solicita
        if include_metadata and chunks:
            result["metadata"] = chunks[0]['_source'].get('metadata', {})
            result["file_info"] = {
                "first_chunk_id": chunks[0]['_source'].get('chunk_id'),
                "last_chunk_id": chunks[-1]['_source'].get('chunk_id'),
                "file_extension": chunks[0]['_source'].get('metadata', {}).get('file_extension'),
                "file_size": chunks[0]['_source'].get('metadata', {}).get('file_size')
            }
        
        return result
        
    except Exception as e:
        return {"error": f"Error en get_file_content: {str(e)}"}

def reconstruct_content_with_overlap_handling(chunks: List[Dict]) -> str:
    """
    Reconstruye el contenido del archivo manejando overlaps entre chunks.
    
    Estrategias implementadas:
    1. Detección de overlap por similitud de texto
    2. Uso de metadatos de posición si están disponibles
    3. Eliminación de duplicados por hash de contenido
    """
    if not chunks:
        return ""
    
    if len(chunks) == 1:
        return chunks[0]['_source']['content']
    
    # Estrategia 1: Si tenemos información de posición, usarla
    if all('chunk_start' in chunk['_source'] and 'chunk_end' in chunk['_source'] for chunk in chunks):
        return reconstruct_by_position(chunks)
    
    # Estrategia 2: Detección de overlap por similitud de texto
    return reconstruct_by_overlap_detection(chunks)

def reconstruct_by_position(chunks: List[Dict]) -> str:
    """Reconstruye usando información de posición de caracteres"""
    content_map = {}
    
    for chunk in chunks:
        source = chunk['_source']
        start = source.get('chunk_start', 0)
        end = source.get('chunk_end', len(source['content']))
        content = source['content']
        
        # Mapear cada posición al contenido correspondiente
        for i, char in enumerate(content):
            pos = start + i
            if pos not in content_map:  # Evitar sobrescribir
                content_map[pos] = char
    
    # Reconstruir en orden de posición
    if content_map:
        max_pos = max(content_map.keys())
        result = []
        for i in range(max_pos + 1):
            if i in content_map:
                result.append(content_map[i])
        return ''.join(result)
    
    # Fallback si no hay posiciones válidas
    return reconstruct_by_overlap_detection(chunks)

def reconstruct_by_overlap_detection(chunks: List[Dict]) -> str:
    """Reconstruye detectando overlaps por similitud de texto"""
    if not chunks:
        return ""
    
    # Comenzar con el primer chunk
    result_content = chunks[0]['_source']['content']
    
    for i in range(1, len(chunks)):
        current_chunk = chunks[i]['_source']['content']
        
        # Buscar overlap entre el final del contenido actual y el inicio del nuevo chunk
        overlap_length = find_overlap_length(result_content, current_chunk)
        
        if overlap_length > 0:
            # Hay overlap, añadir solo la parte no duplicada
            unique_part = current_chunk[overlap_length:]
            result_content += unique_part
        else:
            # No hay overlap detectado, añadir separador y contenido completo
            # Verificar si ya termina con salto de línea
            if not result_content.endswith('\n'):
                result_content += '\n'
            result_content += current_chunk
    
    return result_content

def find_overlap_length(text1: str, text2: str, min_overlap: int = 50) -> int:
    """
    Encuentra la longitud del overlap entre el final de text1 y el inicio de text2.
    
    Args:
        text1: Texto base
        text2: Texto a comparar
        min_overlap: Mínima longitud de overlap a considerar válida
    
    Returns:
        Longitud del overlap encontrado
    """
    max_overlap = min(len(text1), len(text2), 500)  # Limitar búsqueda a 500 chars
    
    for overlap_len in range(max_overlap, min_overlap - 1, -1):
        # Comparar final de text1 con inicio de text2
        end_of_text1 = text1[-overlap_len:]
        start_of_text2 = text2[:overlap_len]
        
        # Calcular similitud (permitir pequeñas diferencias por espacios/saltos)
        similarity = calculate_text_similarity(end_of_text1, start_of_text2)
        
        if similarity > 0.85:  # 85% de similitud
            return overlap_len
    
    return 0

def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calcula similitud entre dos textos normalizando espacios y saltos de línea"""
    # Normalizar textos
    norm1 = ' '.join(text1.split())
    norm2 = ' '.join(text2.split())
    
    if not norm1 or not norm2:
        return 0.0
    
    # Calcular similitud por caracteres coincidentes
    min_len = min(len(norm1), len(norm2))
    if min_len == 0:
        return 0.0
    
    matches = sum(1 for i in range(min_len) if norm1[i] == norm2[i])
    return matches / min_len

def remove_duplicate_chunks_by_hash(chunks: List[Dict]) -> List[Dict]:
    """Elimina chunks duplicados basándose en hash del contenido"""
    import hashlib
    
    seen_hashes = set()
    unique_chunks = []
    
    for chunk in chunks:
        content = chunk['_source']['content']
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            unique_chunks.append(chunk)
    
    return unique_chunks

def get_available_files_sample() -> List[str]:
    """Obtiene una muestra de archivos disponibles para ayudar al usuario"""
    try:
        opensearch_client = OpenSearch([{
            'host': 'vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com', 
            'port': 443,
            'use_ssl': True
        }])
        
        search_body = {
            "size": 0,
            "aggs": {
                "unique_files": {
                    "terms": {
                        "field": "file_name.keyword",
                        "size": 10
                    }
                }
            }
        }
        
        response = opensearch_client.search(index="rag-documents-darwin", body=search_body)
        
        files = []
        for bucket in response['aggregations']['unique_files']['buckets']:
            files.append(bucket['key'])
        
        return files
        
    except:
        return ["Error retrieving file list"]
```

### Salida JSON
```json
{
  "file_path": "FD-Darwin_Funcional0_v2.9.docx",
  "content": "# ESPECIFICACIÓN FUNCIONAL DEL MÓDULO DE CONTRATACIÓN\n\n## 1. OBJETIVOS\n\nEl módulo de Contratación del sistema DARWIN tiene como objetivo...\n\n[CONTENIDO COMPLETO DEL ARCHIVO RECONSTRUIDO]",
  "total_chunks": 45,
  "content_length": 125678,
  "metadata": {
    "file_size": 14237785,
    "file_extension": "docx",
    "processed_date": "2025-10-26T17:18:41.355171"
  },
  "file_info": {
    "first_chunk_id": "chunk_001",
    "last_chunk_id": "chunk_045",
    "file_extension": "docx",
    "file_size": 14237785
  }
}
```

---

## CONFIGURACIÓN Y MANEJO DE ERRORES

### Configuración de Conexiones
```python
# Configuración OpenSearch
OPENSEARCH_CONFIG = {
    'host': 'vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com',
    'port': 443,
    'use_ssl': True,
    'verify_certs': True,
    'timeout': 30,
    'max_retries': 3
}

# Configuración Bedrock
BEDROCK_CONFIG = {
    'region_name': 'eu-west-1',
    'model_id': 'amazon.titan-embed-image-v1',  # Modelo multimodal para texto e imágenes
    'embedding_dimensions': 1024
}

# Configuración del índice
INDEX_CONFIG = {
    'name': 'rag-documents-darwin',
    'max_results': 1000,
    'scroll_timeout': '2m'
}
```

### Manejo de Errores Estándar
```python
class SearchError(Exception):
    """Excepción base para errores de búsqueda"""
    pass

class ConnectionError(SearchError):
    """Error de conexión con OpenSearch o Bedrock"""
    pass

class ValidationError(SearchError):
    """Error de validación de parámetros"""
    pass

def handle_search_error(func):
    """Decorador para manejo estándar de errores"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ConnectionError as e:
            return {"error": f"Connection error: {str(e)}", "type": "connection"}
        except ValidationError as e:
            return {"error": f"Validation error: {str(e)}", "type": "validation"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}", "type": "unexpected"}
    return wrapper
```

### Logging y Métricas
```python
import logging
import time

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_search_metrics(func):
    """Decorador para logging de métricas de búsqueda"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        func_name = func.__name__
        
        logger.info(f"Starting {func_name} with args: {args[:1]}")  # Solo el primer arg (query)
        
        result = func(*args, **kwargs)
        
        duration = time.time() - start_time
        
        if "error" in result:
            logger.error(f"{func_name} failed in {duration:.2f}s: {result['error']}")
        else:
            results_count = result.get('total_found', result.get('total_results', result.get('total_matches', 1)))
            logger.info(f"{func_name} completed in {duration:.2f}s, found {results_count} results")
        
        return result
    return wrapper
```

---

## HERRAMIENTAS ADICIONALES PARA ARCHIVOS GRANDES

### 5. GET_FILE_CHUNKS

**Descripción Funcional**: Obtiene chunks específicos de un archivo sin reconstruir el contenido completo. Ideal para archivos grandes donde solo se necesita una sección específica.

**Entrada XML**:
```xml
<get_file_chunks>
<file_path>FD-Darwin_Funcional0_v2.9.docx</file_path>
<chunk_range>{"start": 5, "end": 15}</chunk_range>
<include_context>true</include_context>
</get_file_chunks>
```

**Parámetros**:
- `file_path` (requerido): Nombre del archivo
- `chunk_range` (opcional): Rango de chunks {"start": N, "end": M} o lista [1,3,7,12]
- `chunk_ids` (opcional): IDs específicos de chunks ["chunk_001", "chunk_005"]
- `include_context` (opcional): Incluir chunks adyacentes para contexto (true/false)

**Implementación Técnica**:
```python
def get_file_chunks(file_path: str, chunk_range: Dict = None, chunk_ids: List[str] = None, 
                   include_context: bool = False) -> Dict[str, Any]:
    try:
        opensearch_client = OpenSearch([{
            'host': 'vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com', 
            'port': 443,
            'use_ssl': True
        }])
        
        # Construir query base
        base_query = {"term": {"file_name.keyword": file_path}}
        
        # Añadir filtros específicos
        if chunk_ids:
            query = {
                "bool": {
                    "must": [base_query],
                    "filter": {"terms": {"chunk_id.keyword": chunk_ids}}
                }
            }
        elif chunk_range:
            start = chunk_range.get('start', 0)
            end = chunk_range.get('end', 999999)
            query = {
                "bool": {
                    "must": [base_query],
                    "filter": {"range": {"chunk_id": {"gte": start, "lte": end}}}
                }
            }
        else:
            query = base_query
        
        search_body = {
            "size": 100,
            "query": query,
            "sort": [{"chunk_id": {"order": "asc"}}],
            "_source": ["content", "file_name", "metadata", "chunk_id", "chunk_start", "chunk_end"]
        }
        
        response = opensearch_client.search(index="rag-documents-darwin", body=search_body)
        chunks = response['hits']['hits']
        
        if not chunks:
            return {"error": f"No chunks found for file: {file_path}"}
        
        # Incluir contexto si se solicita
        if include_context:
            chunks = add_context_chunks(opensearch_client, chunks, file_path)
        
        return format_chunks_response(chunks, file_path)
        
    except Exception as e:
        return {"error": f"Error en get_file_chunks: {str(e)}"}
```

### 6. GET_FILE_SECTION

**Descripción Funcional**: Obtiene una sección específica de un archivo basada en criterios semánticos o estructurales (capítulos, secciones, etc.).

**Entrada XML**:
```xml
<get_file_section>
<file_path>FD-Darwin_Funcional0_v2.9.docx</file_path>
<section_query>módulo de autenticación</section_query>
<section_type>semantic</section_type>
<max_chunks>10</max_chunks>
</get_file_section>
```

**Parámetros**:
- `file_path` (requerido): Nombre del archivo
- `section_query` (requerido): Descripción de la sección buscada
- `section_type` (opcional): "semantic" | "structural" | "keyword" (default: "semantic")
- `max_chunks` (opcional): Máximo número de chunks a devolver (default: 20)
- `expand_context` (opcional): Expandir con chunks adyacentes (true/false)

**Implementación Técnica**:
```python
def get_file_section(file_path: str, section_query: str, section_type: str = "semantic", 
                    max_chunks: int = 20, expand_context: bool = False) -> Dict[str, Any]:
    try:
        if section_type == "semantic":
            return get_semantic_section(file_path, section_query, max_chunks, expand_context)
        elif section_type == "structural":
            return get_structural_section(file_path, section_query, max_chunks)
        elif section_type == "keyword":
            return get_keyword_section(file_path, section_query, max_chunks, expand_context)
        else:
            return {"error": f"Invalid section_type: {section_type}"}
            
    except Exception as e:
        return {"error": f"Error en get_file_section: {str(e)}"}

def get_semantic_section(file_path: str, section_query: str, max_chunks: int, expand_context: bool) -> Dict[str, Any]:
    """Busca sección usando similitud semántica"""
    # 1. Generar embedding de la query
    bedrock_client = boto3.client('bedrock-runtime', region_name='eu-west-1')
    embedding_response = bedrock_client.invoke_model(
        modelId="amazon.titan-embed-image-v1",
        body=json.dumps({
            "inputText": section_query, 
            "embeddingConfig": {"outputEmbeddingLength": 1024}
        })
    )
    query_embedding = json.loads(embedding_response['body'].read())['embedding']
    
    # 2. Buscar chunks más relevantes del archivo específico
    opensearch_client = OpenSearch([{
        'host': 'vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com', 
        'port': 443,
        'use_ssl': True
    }])
    
    search_body = {
        "size": max_chunks,
        "query": {
            "bool": {
                "must": [
                    {"term": {"file_name.keyword": file_path}},
                    {"knn": {"embedding_vector": {"vector": query_embedding, "k": max_chunks}}}
                ]
            }
        },
        "sort": [{"chunk_id": {"order": "asc"}}],
        "_source": ["content", "file_name", "metadata", "chunk_id"]
    }
    
    response = opensearch_client.search(index="rag-documents-darwin", body=search_body)
    chunks = response['hits']['hits']
    
    if expand_context:
        chunks = add_context_chunks(opensearch_client, chunks, file_path)
    
    return format_section_response(chunks, section_query, "semantic")
```

### 7. GET_FILE_SUMMARY

**Descripción Funcional**: Obtiene un resumen estructurado de un archivo grande, incluyendo tabla de contenidos, secciones principales y estadísticas.

**Entrada XML**:
```xml
<get_file_summary>
<file_path>FD-Darwin_Funcional0_v2.9.docx</file_path>
<summary_type>detailed</summary_type>
<include_toc>true</include_toc>
</get_file_summary>
```

**Parámetros**:
- `file_path` (requerido): Nombre del archivo
- `summary_type` (opcional): "brief" | "detailed" | "structural" (default: "brief")
- `include_toc` (opcional): Incluir tabla de contenidos (true/false)
- `max_sections` (opcional): Máximo número de secciones a incluir (default: 10)

**Implementación Técnica**:
```python
def get_file_summary(file_path: str, summary_type: str = "brief", include_toc: bool = False, 
                    max_sections: int = 10) -> Dict[str, Any]:
    try:
        opensearch_client = OpenSearch([{
            'host': 'vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com', 
            'port': 443,
            'use_ssl': True
        }])
        
        # 1. Obtener estadísticas básicas del archivo
        stats_query = {
            "size": 0,
            "query": {"term": {"file_name.keyword": file_path}},
            "aggs": {
                "total_chunks": {"value_count": {"field": "chunk_id"}},
                "avg_chunk_size": {"avg": {"script": "doc['content'].value.length()"}},
                "file_metadata": {"terms": {"field": "metadata.file_extension", "size": 1}}
            }
        }
        
        stats_response = opensearch_client.search(index="rag-documents-darwin", body=stats_query)
        
        # 2. Obtener chunks representativos
        sample_query = {
            "size": max_sections,
            "query": {"term": {"file_name.keyword": file_path}},
            "sort": [{"chunk_id": {"order": "asc"}}],
            "_source": ["content", "chunk_id"]
        }
        
        sample_response = opensearch_client.search(index="rag-documents-darwin", body=sample_query)
        
        # 3. Generar resumen
        return generate_file_summary(stats_response, sample_response, file_path, summary_type, include_toc)
        
    except Exception as e:
        return {"error": f"Error en get_file_summary: {str(e)}"}
```

### 8. STREAM_FILE_CONTENT

**Descripción Funcional**: Transmite el contenido de un archivo en chunks secuenciales, permitiendo procesamiento streaming para archivos muy grandes.

**Entrada XML**:
```xml
<stream_file_content>
<file_path>FD-Darwin_Funcional0_v2.9.docx</file_path>
<batch_size>5</batch_size>
<start_chunk>0</start_chunk>
</stream_file_content>
```

**Parámetros**:
- `file_path` (requerido): Nombre del archivo
- `batch_size` (opcional): Número de chunks por lote (default: 10)
- `start_chunk` (opcional): Chunk inicial (default: 0)
- `end_chunk` (opcional): Chunk final (default: último chunk)

**Implementación Técnica**:
```python
def stream_file_content(file_path: str, batch_size: int = 10, start_chunk: int = 0, 
                       end_chunk: int = None) -> Dict[str, Any]:
    try:
        opensearch_client = OpenSearch([{
            'host': 'vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com', 
            'port': 443,
            'use_ssl': True
        }])
        
        # 1. Determinar rango total si end_chunk no se especifica
        if end_chunk is None:
            count_query = {
                "size": 0,
                "query": {"term": {"file_name.keyword": file_path}},
                "aggs": {"max_chunk": {"max": {"field": "chunk_id"}}}
            }
            count_response = opensearch_client.search(index="rag-documents-darwin", body=count_query)
            end_chunk = int(count_response['aggregations']['max_chunk']['value'] or 0)
        
        # 2. Obtener lote actual
        search_body = {
            "size": batch_size,
            "query": {
                "bool": {
                    "must": [{"term": {"file_name.keyword": file_path}}],
                    "filter": {"range": {"chunk_id": {"gte": start_chunk, "lte": min(start_chunk + batch_size - 1, end_chunk)}}}
                }
            },
            "sort": [{"chunk_id": {"order": "asc"}}],
            "_source": ["content", "chunk_id", "metadata"]
        }
        
        response = opensearch_client.search(index="rag-documents-darwin", body=search_body)
        chunks = response['hits']['hits']
        
        # 3. Preparar respuesta con información de streaming
        next_chunk = start_chunk + batch_size
        has_more = next_chunk <= end_chunk
        
        return {
            "file_path": file_path,
            "batch_info": {
                "current_batch": start_chunk // batch_size + 1,
                "batch_size": batch_size,
                "start_chunk": start_chunk,
                "end_chunk": min(start_chunk + batch_size - 1, end_chunk),
                "total_chunks": end_chunk + 1,
                "has_more": has_more,
                "next_start_chunk": next_chunk if has_more else None
            },
            "chunks": [{"chunk_id": chunk['_source']['chunk_id'], "content": chunk['_source']['content']} for chunk in chunks],
            "streaming": True
        }
        
    except Exception as e:
        return {"error": f"Error en stream_file_content: {str(e)}"}
```

## ESTRATEGIAS DE OPTIMIZACIÓN PARA ARCHIVOS GRANDES

### 1. Estrategia de Acceso Inteligente

```python
def intelligent_file_access(file_path: str, user_intent: str) -> Dict[str, Any]:
    """
    Determina automáticamente la mejor estrategia de acceso basada en:
    - Tamaño del archivo
    - Intención del usuario
    - Recursos disponibles
    """
    
    # 1. Obtener metadatos del archivo
    file_stats = get_file_statistics(file_path)
    
    if file_stats['total_chunks'] <= 10:
        # Archivo pequeño: contenido completo
        return get_file_content(file_path, include_metadata=True)
    
    elif file_stats['total_chunks'] <= 50:
        # Archivo mediano: resumen + secciones relevantes
        summary = get_file_summary(file_path, summary_type="detailed")
        relevant_section = get_file_section(file_path, user_intent, max_chunks=15)
        return {"strategy": "summary_plus_section", "summary": summary, "relevant_section": relevant_section}
    
    else:
        # Archivo grande: resumen + streaming bajo demanda
        summary = get_file_summary(file_path, summary_type="brief", include_toc=True)
        return {"strategy": "summary_plus_streaming", "summary": summary, "streaming_available": True}
```

### 2. Cache Inteligente

```python
class FileContentCache:
    """Cache inteligente para contenido de archivos grandes"""
    
    def __init__(self, max_size_mb: int = 100):
        self.cache = {}
        self.max_size = max_size_mb * 1024 * 1024  # Convertir a bytes
        self.current_size = 0
    
    def get_cached_section(self, file_path: str, section_key: str) -> Optional[Dict]:
        """Obtiene sección cacheada si existe"""
        cache_key = f"{file_path}:{section_key}"
        return self.cache.get(cache_key)
    
    def cache_section(self, file_path: str, section_key: str, content: Dict):
        """Cachea una sección con gestión de memoria"""
        cache_key = f"{file_path}:{section_key}"
        content_size = len(str(content))
        
        # Limpiar cache si es necesario
        while self.current_size + content_size > self.max_size and self.cache:
            oldest_key = next(iter(self.cache))
            self._remove_from_cache(oldest_key)
        
        self.cache[cache_key] = content
        self.current_size += content_size
```

### 3. Índice de Navegación

```python
def create_file_navigation_index(file_path: str) -> Dict[str, Any]:
    """Crea un índice de navegación para archivos grandes"""
    
    # 1. Detectar estructura (títulos, secciones, etc.)
    structure_patterns = [
        r'^#{1,6}\s+(.+)$',  # Markdown headers
        r'^\d+\.\s+(.+)$',   # Numbered sections
        r'^[A-Z][A-Z\s]+$',  # ALL CAPS titles
    ]
    
    # 2. Extraer tabla de contenidos
    toc = extract_table_of_contents(file_path, structure_patterns)
    
    # 3. Crear mapa de chunks por sección
    section_map = map_chunks_to_sections(file_path, toc)
    
    return {
        "file_path": file_path,
        "table_of_contents": toc,
        "section_chunk_map": section_map,
        "navigation_available": True
    }
```

## NOTAS DE IMPLEMENTACIÓN

### Consideraciones de Rendimiento
1. **Timeouts**: Configurar timeouts apropiados para evitar bloqueos
2. **Scroll**: Usar scroll de OpenSearch para archivos con muchos chunks
3. **Batch Processing**: Procesar resultados en lotes para optimizar memoria
4. **Caching**: Considerar cache para embeddings de queries frecuentes
5. **Streaming**: Implementar streaming para archivos muy grandes
6. **Índices de navegación**: Crear índices para acceso rápido a secciones

### Validaciones Requeridas
1. **Parámetros de entrada**: Validar tipos y rangos de todos los parámetros
2. **Patrones regex**: Validar sintaxis antes de ejecutar búsquedas
3. **Límites de resultados**: Aplicar límites máximos para evitar sobrecarga
4. **Sanitización**: Limpiar inputs para evitar inyecciones
5. **Límites de memoria**: Controlar uso de memoria en archivos grandes

### Extensibilidad
1. **Filtros adicionales**: Preparado para añadir más filtros (fecha, tamaño, etc.)
2. **Nuevos modelos**: Fácil cambio de modelo de embeddings
3. **Múltiples índices**: Soporte para búsqueda en múltiples índices
4. **Formatos de salida**: Posibilidad de múltiples formatos de respuesta
5. **Estrategias de acceso**: Nuevas estrategias basadas en tipo de archivo y uso
