# Instrucciones para Re-indexar después del Fix del campo file_name

## Problema Corregido

Se ha corregido el mapping del campo `file_name` en OpenSearch para permitir búsquedas léxicas por palabras individuales.

### Cambio Aplicado

**Antes:**
```python
"file_name": {
    "type": "keyword"  # Solo coincidencias exactas completas
}
```

**Después:**
```python
"file_name": {
    "type": "text",
    "analyzer": "standard",
    "fields": {
        "keyword": {
            "type": "keyword"
        }
    }
}
```

### Beneficios

- ✅ Búsquedas léxicas por palabras individuales (ej: "Devoluciones" encuentra "1.2.5.5_DF- Devoluciones a proveedor.pdf")
- ✅ Búsquedas exactas siguen disponibles usando `file_name.keyword`
- ✅ Mejor experiencia de usuario en búsquedas por nombre de archivo

## Pasos para Re-indexar

### Opción 1: Re-indexar una aplicación específica (Recomendado)

```bash
# 1. Eliminar documentos de la aplicación
python3 -c "
from src.indexing.multi_app_opensearch_indexer import MultiAppOpenSearchIndexer
indexer = MultiAppOpenSearchIndexer(app_name='saplcorp')
indexer.delete_application_documents()
print('Documentos eliminados')
"

# 2. Eliminar y re-crear el índice con el nuevo mapping
python3 -c "
from src.indexing.multi_app_opensearch_indexer import MultiAppOpenSearchIndexer
indexer = MultiAppOpenSearchIndexer(app_name='saplcorp')
indexer.delete_index()
print('Índice eliminado')
indexer.create_index()
print('Índice re-creado con nuevo mapping')
"

# 3. Re-indexar documentos desde S3
python3 src/utils/multi_app_aws_ingestion_manager_with_summarization.py \
    --app saplcorp \
    --action index \
    --source s3
```

### Opción 2: Re-indexar todas las aplicaciones

```bash
# Para cada aplicación (darwin, saplcorp, mulesoft, deltasmile)
for app in darwin saplcorp mulesoft deltasmile; do
    echo "Re-indexando $app..."
    
    # Eliminar índice
    python3 -c "
from src.indexing.multi_app_opensearch_indexer import MultiAppOpenSearchIndexer
indexer = MultiAppOpenSearchIndexer(app_name='$app')
indexer.delete_index()
indexer.create_index()
print('Índice $app re-creado')
"
    
    # Re-indexar
    python3 src/utils/multi_app_aws_ingestion_manager_with_summarization.py \
        --app $app \
        --action index \
        --source s3
done
```

### Opción 3: Verificar el mapping actual sin re-indexar

```bash
# Ver el mapping actual del índice
python3 -c "
from src.indexing.multi_app_opensearch_indexer import MultiAppOpenSearchIndexer
indexer = MultiAppOpenSearchIndexer(app_name='saplcorp')
mapping = indexer.opensearch_client.indices.get_mapping(index=indexer.index_name)
import json
print(json.dumps(mapping, indent=2))
"
```

## Verificación Post Re-indexación

### 1. Verificar que el índice tiene el nuevo mapping

```bash
python3 -c "
from src.indexing.multi_app_opensearch_indexer import MultiAppOpenSearchIndexer
indexer = MultiAppOpenSearchIndexer(app_name='saplcorp')
mapping = indexer.opensearch_client.indices.get_mapping(index=indexer.index_name)
file_name_mapping = mapping[indexer.index_name]['mappings']['properties']['file_name']
print('Mapping de file_name:', file_name_mapping)
assert file_name_mapping['type'] == 'text', 'ERROR: file_name no es tipo text'
assert 'keyword' in file_name_mapping['fields'], 'ERROR: falta el campo keyword'
print('✅ Mapping correcto')
"
```

### 2. Probar búsqueda léxica por nombre de archivo

```bash
# Desde el agente
python3 src/agent/main.py --app saplcorp

# Luego ejecutar:
# "haz una búsqueda léxica por archivos que tengan en el título la palabra Devoluciones"
```

### 3. Verificar estadísticas del índice

```bash
python3 -c "
from src.indexing.multi_app_opensearch_indexer import MultiAppOpenSearchIndexer
indexer = MultiAppOpenSearchIndexer(app_name='saplcorp')
stats = indexer.get_index_stats()
import json
print(json.dumps(stats, indent=2))
"
```

## Notas Importantes

1. **Backup**: Antes de eliminar el índice, considera hacer un backup si es necesario
2. **Tiempo**: La re-indexación puede tardar dependiendo del número de documentos
3. **Downtime**: Durante la re-indexación, las búsquedas no funcionarán
4. **Orden**: Re-indexa primero en desarrollo/test antes de producción

## Troubleshooting

### Error: "Index already exists"

```bash
# Eliminar el índice manualmente
python3 -c "
from src.indexing.multi_app_opensearch_indexer import MultiAppOpenSearchIndexer
indexer = MultiAppOpenSearchIndexer(app_name='saplcorp')
indexer.delete_index()
"
```

### Error: "No documents found in S3"

Verifica que los documentos estén en el bucket correcto:
```bash
aws s3 ls s3://rag-system-saplcorp-eu-west-1/documents/ --recursive
```

### Búsquedas siguen sin funcionar

1. Verifica el mapping con el comando de verificación
2. Revisa los logs de la herramienta lexical_search
3. Confirma que los documentos se indexaron correctamente

## Contacto

Para dudas o problemas, contactar al equipo de desarrollo.
