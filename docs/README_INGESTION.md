# Script de Ingestión de Documentos con Estructura

## Descripción

Este script procesa documentos que ya están indexados en OpenSearch y genera:
1. **Resúmenes** usando Claude (Bedrock)
2. **Estructura del documento** (secciones, rangos de chunks, etc.)
3. **Metadata completa**

Todo se almacena en S3 en formato JSON para acceso rápido.

## Requisitos

```bash
pip3 install boto3 opensearch-py requests-aws4auth
```

## Configuración

El script usa la configuración de `config/config_saplcorp.yaml`:
- Conexión a OpenSearch
- Bucket de S3
- Región de AWS
- Modelo de Bedrock

## Uso

### 1. Procesar un archivo específico

```bash
python3 src/utils/document_ingestion_with_structure.py \
  --file "UFD_Manual_IFRS16_v1.1.pdf"
```

### 2. Procesar todos los documentos del índice

```bash
python3 src/utils/document_ingestion_with_structure.py --all
```

### 3. Forzar reprocesamiento (sobrescribir existentes)

```bash
python3 src/utils/document_ingestion_with_structure.py \
  --file "UFD_Manual_IFRS16_v1.1.pdf" \
  --force
```

### 4. Usar configuración personalizada

```bash
python3 src/utils/document_ingestion_with_structure.py \
  --config config/config_custom.yaml \
  --all
```

## Estructura del Output en S3

**Ubicación:** `s3://rag-system-saplcorp-eu-west-1/summaries/{file_hash}.json`

**Formato:**
```json
{
  "file_name": "UFD_Manual_IFRS16_v1.1.pdf",
  "file_hash": "4665e27fb53135ed13147e0ffee5d5b97ef7e8f01796ba29f62b4db77bbd754d",
  "summary": "Resumen generado por Claude...",
  "metadata": {
    "file_extension": "pdf",
    "file_size": 16881899,
    "total_pages": 157,
    "total_chunks": 542,
    "content_length": 1234567
  },
  "document_structure": {
    "sections": [
      {
        "id": "section_1",
        "title": "1. Introducción",
        "level": 1,
        "chunk_start": 1,
        "chunk_end": 15,
        "type": "numbered"
      }
    ],
    "chunk_ranges": [
      {
        "description": "Inicio del documento (primeros 10 chunks)",
        "chunk_start": 1,
        "chunk_end": 10,
        "estimated_chars": 25000
      }
    ],
    "total_sections_detected": 45,
    "analysis_timestamp": "2025-11-04T10:00:00Z",
    "total_chunks": 542
  },
  "created_at": "2025-11-04T10:00:00Z",
  "version": "1.0"
}
```

## Proceso de Ingestión

1. **Obtener chunks** desde OpenSearch (usando scroll)
2. **Extraer metadata** del primer chunk
3. **Calcular estructura**:
   - Detectar secciones (títulos numerados, capítulos, etc.)
   - Crear rangos de chunks sugeridos
   - Calcular rangos por páginas
4. **Generar resumen** usando Claude (Bedrock)
5. **Guardar en S3** en formato JSON

## Ventajas

- ✅ **Rápido**: Estructura pre-calculada, no se calcula en cada consulta
- ✅ **Escalable**: Funciona con archivos de cualquier tamaño
- ✅ **Inteligente**: Detecta automáticamente secciones y estructura
- ✅ **Completo**: Incluye resumen, metadata y estructura
- ✅ **Idempotente**: Puede ejecutarse múltiples veces sin problemas

## Logs

Los logs se guardan en `logs/search_tools.log` según la configuración.

## Ejemplo de Salida

```bash
$ python3 src/utils/document_ingestion_with_structure.py --file "UFD_Manual_IFRS16_v1.1.pdf"

{
  "status": "success",
  "file_name": "UFD_Manual_IFRS16_v1.1.pdf",
  "file_hash": "4665e27fb53135ed13147e0ffee5d5b97ef7e8f01796ba29f62b4db77bbd754d",
  "total_chunks": 542,
  "sections_detected": 45,
  "summary_length": 856
}
```

## Troubleshooting

### Error: "No se encontraron chunks"
- Verificar que el archivo existe en OpenSearch
- Verificar el nombre exacto del archivo (case-sensitive)

### Error de conexión a OpenSearch
- Verificar túnel SSH si estás en desarrollo local
- Verificar credenciales AWS

### Error de Bedrock
- Verificar que tienes acceso al modelo Claude
- Verificar región configurada (eu-west-1)

## Integración con tool_get_file_content

Una vez procesados los documentos, `tool_get_file_content.py` automáticamente:
1. Intenta cargar la estructura desde S3 (rápido)
2. Si no existe, calcula on-the-fly (lento)
3. Devuelve estructura para acceso progresivo

Esto hace que archivos grandes como IFRS16 respondan instantáneamente.
