# Diseño: Pre-cálculo de Estructura de Documentos

## Problema Identificado

Cuando el LLM solicita información sobre archivos grandes (como IFRS16 de 16.8 MB), el sistema tarda mucho tiempo porque:

1. Obtiene TODOS los chunks del archivo desde OpenSearch (operación lenta con scroll)
2. Calcula la longitud total sumando todos los chunks
3. Analiza la estructura leyendo los primeros 20 chunks

Esto resulta en tiempos de espera de varios segundos o minutos para archivos grandes.

## Solución Propuesta

**Pre-calcular la estructura del documento durante la ingestión** y almacenarla en S3 junto con los summaries existentes.

### Arquitectura

```
Fase de Ingestión:
┌─────────────────┐
│  Documento PDF  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Procesamiento de Documento     │
│  - Extracción de texto          │
│  - Chunking                     │
│  - Embeddings                   │
│  - **NUEVO: Análisis estructura**│
└────────┬────────────────────────┘
         │
         ├──────────────┬─────────────────┐
         ▼              ▼                 ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│  OpenSearch  │ │  S3 Summary  │ │ S3 Structure     │
│  (chunks)    │ │  (resumen)   │ │ (NUEVO)          │
└──────────────┘ └──────────────┘ └──────────────────┘

Fase de Consulta:
┌─────────────────────────────────┐
│  LLM solicita archivo grande    │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  tool_get_file_content          │
│  1. Busca estructura en S3      │ ← RÁPIDO (1 request)
│  2. Si existe, devuelve         │
│  3. Si no, calcula on-the-fly   │
└─────────────────────────────────┘
```

### Estructura del Archivo en S3

**Ubicación:** `s3://{bucket}/summaries/{file_hash}.json`

**Formato JSON:**
```json
{
  "file_name": "UFD_Manual_IFRS16_v1.1.pdf",
  "file_hash": "4665e27fb53135ed13147e0ffee5d5b97ef7e8f01796ba29f62b4db77bbd754d",
  "summary": "Resumen del documento...",
  "metadata": {
    "file_size": 16881899,
    "total_pages": 157,
    "total_chunks": 542,
    "file_extension": "pdf"
  },
  "document_structure": {
    "sections": [
      {
        "id": "section_1",
        "title": "1. Introducción",
        "level": 1,
        "chunk_start": 1,
        "chunk_end": 15,
        "page_start": 1,
        "page_end": 5,
        "type": "numbered"
      },
      {
        "id": "section_2",
        "title": "1.1 Objetivo del Manual",
        "level": 2,
        "chunk_start": 5,
        "chunk_end": 10,
        "page_start": 2,
        "page_end": 3,
        "type": "numbered"
      }
    ],
    "chunk_ranges": [
      {
        "description": "Inicio del documento (primeros 10 chunks)",
        "chunk_start": 1,
        "chunk_end": 10,
        "estimated_chars": 25000
      },
      {
        "description": "Primeras 10 páginas",
        "chunk_start": 1,
        "chunk_end": 35,
        "page_start": 1,
        "page_end": 10,
        "estimated_chars": 87500
      }
    ],
    "total_sections_detected": 45,
    "analysis_timestamp": "2025-11-04T10:00:00Z"
  }
}
```

## Implementación

### Fase 1: Modificar Proceso de Ingestión

**Archivo a modificar:** Script de procesamiento de documentos (probablemente en `src/utils/`)

```python
def process_document(file_path: str):
    # ... código existente ...
    
    # NUEVO: Analizar estructura del documento
    structure = analyze_document_structure(file_path, chunks)
    
    # Guardar en S3 junto con el summary
    save_to_s3_summary(
        file_hash=file_hash,
        summary=summary,
        metadata=metadata,
        document_structure=structure  # NUEVO campo
    )
```

### Fase 2: Modificar tool_get_file_content (YA IMPLEMENTADO)

El código ya está preparado con los métodos:
- `_load_structure_from_s3()`: Carga estructura desde S3
- `_format_structure_response()`: Formatea respuesta con estructura pre-calculada

### Fase 3: Crear Utilidad para Re-procesar Documentos Existentes

**Nuevo archivo:** `src/utils/add_structure_to_summaries.py`

```python
#!/usr/bin/env python3
"""
Utilidad para agregar estructura de documentos a summaries existentes en S3.
Procesa todos los archivos en S3 y agrega el campo document_structure.
"""

import boto3
import json
from pathlib import Path
from document_structure_analyzer import DocumentStructureAnalyzer

def process_existing_summaries():
    """
    Procesa todos los summaries existentes y agrega estructura
    """
    s3 = boto3.client('s3')
    bucket = 'rag-system-saplcorp-eu-west-1'
    prefix = 'summaries/'
    
    # Listar todos los summaries
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    
    for obj in response.get('Contents', []):
        key = obj['Key']
        
        # Cargar summary existente
        response = s3.get_object(Bucket=bucket, Key=key)
        summary_data = json.loads(response['Body'].read())
        
        # Si ya tiene estructura, skip
        if 'document_structure' in summary_data:
            continue
        
        # Analizar estructura
        file_name = summary_data.get('file_name')
        structure = analyze_structure_for_file(file_name)
        
        # Agregar estructura
        summary_data['document_structure'] = structure
        
        # Guardar de vuelta en S3
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(summary_data, ensure_ascii=False),
            ContentType='application/json'
        )
        
        print(f"✓ Procesado: {file_name}")
```

## Beneficios

1. **Velocidad:** Respuesta instantánea (1 request a S3 vs múltiples scrolls a OpenSearch)
2. **Escalabilidad:** No importa el tamaño del archivo, siempre es rápido
3. **Consistencia:** La estructura se calcula una vez durante ingestión
4. **Fallback:** Si no existe estructura pre-calculada, se calcula on-the-fly

## Métricas Esperadas

| Operación | Antes | Después |
|-----------|-------|---------|
| Archivo pequeño (<1000 chars) | ~500ms | ~500ms (sin cambio) |
| Archivo mediano (1000-50000 chars) | ~2s | ~2s (sin cambio) |
| Archivo grande (>50000 chars) | **30-60s** | **<1s** ✅ |

## Plan de Implementación

### Paso 1: Actualizar Proceso de Ingestión
- [ ] Modificar script de procesamiento para calcular estructura
- [ ] Agregar campo `document_structure` al JSON de summary
- [ ] Probar con un documento nuevo

### Paso 2: Re-procesar Documentos Existentes
- [ ] Crear script `add_structure_to_summaries.py`
- [ ] Ejecutar para todos los documentos en S3
- [ ] Verificar que se agregó correctamente

### Paso 3: Validación
- [ ] Probar con archivo IFRS16
- [ ] Verificar que carga desde S3
- [ ] Medir tiempo de respuesta
- [ ] Confirmar que estructura es correcta

### Paso 4: Monitoreo
- [ ] Agregar métricas de uso (S3 hit/miss)
- [ ] Monitorear tiempos de respuesta
- [ ] Ajustar según necesidad

## Notas Técnicas

### Cálculo del Hash
```python
import hashlib
file_hash = hashlib.sha256(file_name.encode()).hexdigest()
```

### Ruta en S3
```
s3://rag-system-saplcorp-eu-west-1/summaries/{file_hash}.json
```

### Compatibilidad
- El código actual ya soporta fallback si no existe estructura
- No rompe funcionalidad existente
- Se puede implementar gradualmente

## Conclusión

Esta solución resuelve el problema de rendimiento de manera elegante:
- Pre-calcula durante ingestión (cuando el tiempo no es crítico)
- Consulta rápida durante uso (cuando el tiempo es crítico)
- Mantiene compatibilidad con sistema existente
- Escalable a cualquier tamaño de documento
