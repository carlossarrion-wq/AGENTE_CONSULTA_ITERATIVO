# Instrucciones para usar Knowledge Search Tool en EC2

## Pasos para copiar y ejecutar en EC2

### 1. Copiar el archivo a EC2

```bash
# Desde tu máquina local, copiar el archivo a EC2
scp -i ~/.ssh/ec2_new_key knowledge_search_ec2.py ec2-user@18.202.140.248:/home/ec2-user/RAG_SYSTEM_MULTI_v5/scripts/
```

### 2. Conectar a EC2 y navegar al directorio

```bash
# Conectar a EC2
ssh -i ~/.ssh/ec2_new_key ec2-user@18.202.140.248

# Navegar al directorio del sistema RAG
cd /home/ec2-user/RAG_SYSTEM_MULTI_v5

# Verificar que el archivo se copió correctamente
ls -la scripts/knowledge_search_ec2.py
```

### 3. Hacer el archivo ejecutable

```bash
chmod +x scripts/knowledge_search_ec2.py
```

### 4. Ejecutar la herramienta

#### Ejemplos de uso básico:

```bash
# Búsqueda básica
python3 scripts/knowledge_search_ec2.py "alta de usuarios"

# Con parámetros específicos
python3 scripts/knowledge_search_ec2.py "módulos principales Darwin arquitectura componentes estructura sistema funcionalidades" --app darwin --top_k 5

# Salida formateada
python3 scripts/knowledge_search_ec2.py "configuración canal" --pretty

# Con puntuación mínima
python3 scripts/knowledge_search_ec2.py "integración siebel" --min_score 1.0 --pretty

# Guardar resultados en archivo
python3 scripts/knowledge_search_ec2.py "dashboard" --output resultados.json

# Con información de debug
python3 scripts/knowledge_search_ec2.py "consulta" --debug --pretty
```

#### Ejemplo completo del comando que falló:

```bash
# El comando original que falló
python3 scripts/knowledge_search_ec2.py --app darwin "módulos principales Darwin arquitectura componentes estructura sistema funcionalidades"

# Versión mejorada con más opciones
python3 scripts/knowledge_search_ec2.py "módulos principales Darwin arquitectura componentes estructura sistema funcionalidades" --app darwin --top_k 10 --min_score 0.5 --pretty
```

### 5. Verificar que funciona correctamente

#### Test rápido:

```bash
# Test simple
python3 scripts/knowledge_search_ec2.py "test" --top_k 3 --pretty

# Si funciona, deberías ver algo como:
# 2025-10-26 16:XX:XX,XXX - INFO - Paths configurados desde: /home/ec2-user/RAG_SYSTEM_MULTI_v5
# 2025-10-26 16:XX:XX,XXX - INFO - ✅ Dependencias importadas correctamente
# 2025-10-26 16:XX:XX,XXX - INFO - Inicializando KnowledgeSearchTool para aplicación: darwin
# ...
```

## Estructura de salida esperada

### Salida JSON (por defecto):
```json
{
  "query": "módulos principales Darwin",
  "parameters": {
    "top_k": 10,
    "min_score": 0.0,
    "application": "darwin",
    "index": "rag-documents-darwin"
  },
  "timestamp": "2025-10-26T16:49:09.972000",
  "duration_seconds": 2.345,
  "total_found": 5,
  "search_stats": {
    "vector_results": 8,
    "text_results": 7,
    "combined_before_filter": 12
  },
  "fragments": [
    {
      "file_name": "FD-Darwin_Funcional0_v2.9.docx",
      "relevance": 0.95,
      "summary": "Este documento describe en detalle la especificación funcional del módulo de Contratación del sistema DARWIN...",
      "search_type": "vector",
      "chunk_id": "chunk_001"
    }
  ]
}
```

### Salida formateada (--pretty):
```
================================================================================
🔍 RESULTADOS DE BÚSQUEDA
================================================================================
Query: módulos principales Darwin arquitectura componentes estructura sistema funcionalidades
Aplicación: darwin
Índice: rag-documents-darwin
Fragmentos encontrados: 5
Duración: 2.345s
Stats: Vector=8, Text=7
--------------------------------------------------------------------------------

1. FD-Darwin_Funcional0_v2.9.docx (vector)
   Relevancia: 0.95
   Chunk ID: chunk_001
   Resumen: Este documento describe en detalle la especificación funcional del módulo de Contratación del sistema DARWIN, el Frontal Único de Ventas (FUV) de Naturgy...

2. Embalsados.docx (text)
   Relevancia: 0.87
   Chunk ID: chunk_045
   Resumen: Este documento proporciona instrucciones detalladas sobre el uso de la plataforma Anypoint de MuleSoft para monitorizar y gestionar los flujos...
```

## Parámetros disponibles

| Parámetro | Descripción | Valor por defecto | Ejemplo |
|-----------|-------------|-------------------|---------|
| `query` | Texto a buscar (obligatorio) | - | `"alta de usuarios"` |
| `--top_k` | Número máximo de resultados | 10 | `--top_k 5` |
| `--min_score` | Puntuación mínima | 0.0 | `--min_score 1.0` |
| `--app` | Aplicación (darwin/sap/mulesoft) | darwin | `--app darwin` |
| `--config` | Ruta a configuración personalizada | auto | `--config /path/config.yaml` |
| `--output` | Archivo de salida JSON | - | `--output results.json` |
| `--pretty` | Salida formateada | false | `--pretty` |
| `--debug` | Información de debug | false | `--debug` |

## Troubleshooting

### Error: "Este script debe ejecutarse desde el directorio RAG_SYSTEM_MULTI_v5"

**Solución:**
```bash
cd /home/ec2-user/RAG_SYSTEM_MULTI_v5
python3 scripts/knowledge_search_ec2.py "tu consulta"
```

### Error: "❌ Error importando dependencias"

**Solución:**
```bash
# Verificar que estás en el directorio correcto
pwd
# Debe mostrar: /home/ec2-user/RAG_SYSTEM_MULTI_v5

# Verificar que existe el directorio src
ls -la src/

# Si falta, verificar la estructura del proyecto
ls -la
```

### Error de conexión a OpenSearch

**Solución:**
```bash
# Verificar credenciales AWS
aws sts get-caller-identity

# Verificar conectividad
ping vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com
```

### Error: "Archivo de configuración no encontrado"

**Solución:**
```bash
# Verificar que existe el archivo de configuración
ls -la config/multi_app_config.yaml

# Si no existe, verificar la estructura
ls -la config/
```

## Casos de uso típicos

### 1. Búsqueda de documentación técnica
```bash
python3 scripts/knowledge_search_ec2.py "migración base de datos doctrine" --top_k 5 --pretty
```

### 2. Búsqueda de procesos específicos
```bash
python3 scripts/knowledge_search_ec2.py "alta canal ventas" --min_score 0.5 --output canal_docs.json
```

### 3. Búsqueda de configuraciones
```bash
python3 scripts/knowledge_search_ec2.py "configuración opensearch elasticsearch" --app darwin --pretty
```

### 4. Búsqueda de integraciones
```bash
python3 scripts/knowledge_search_ec2.py "integración siebel salesforce" --top_k 8 --min_score 1.0 --pretty
```

### 5. Análisis de arquitectura
```bash
python3 scripts/knowledge_search_ec2.py "arquitectura sistema componentes módulos" --debug --pretty
```

## Notas importantes

1. **Directorio de ejecución**: Siempre ejecutar desde `/home/ec2-user/RAG_SYSTEM_MULTI_v5`
2. **Permisos**: El archivo debe tener permisos de ejecución (`chmod +x`)
3. **Conectividad**: Requiere acceso a OpenSearch y Bedrock en AWS
4. **Credenciales**: Las credenciales AWS deben estar configuradas en EC2
5. **Rendimiento**: Las búsquedas pueden tardar 2-10 segundos dependiendo de la complejidad

## Comandos útiles para monitoreo

```bash
# Ver logs en tiempo real (si hay logging a archivo)
tail -f /var/log/knowledge_search.log

# Monitorear uso de recursos
htop

# Verificar conectividad de red
netstat -an | grep 443

# Ver procesos Python activos
ps aux | grep python3
