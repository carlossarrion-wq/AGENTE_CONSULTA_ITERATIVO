# Fix: Semantic Search Returning 0.0000 Relevance Scores

## Problema Identificado

El usuario reportó que `semantic_search` estaba devolviendo scores de relevancia de 0.0000 para todos los resultados, lo cual es inusual y sugiere un problema en la captura o formateo de los scores.

## Causa Raíz

Había un **desajuste en los nombres de campos** entre `semantic_search.py` y `request_handler.py`:

### En semantic_search.py (ANTES):
```python
fragments.append({
    "file_name": source['file_name'],
    "relevance": hit['_score'],  # ❌ Usaba 'relevance'
    "summary": source['content'],
    ...
})
```

### En request_handler.py:
```python
def _format_search_results(self, results: Dict[str, Any]) -> str:
    ...
    score = fragment.get('score', 0)  # ❌ Buscaba 'score', no 'relevance'
    ...
    formatted += f"   - Relevancia máxima: {info['max_score']:.4f}\n"
```

**Resultado:** Como `request_handler.py` buscaba el campo `'score'` pero `semantic_search.py` devolvía `'relevance'`, el método `get('score', 0)` siempre devolvía el valor por defecto `0`, mostrando 0.0000 en todos los casos.

## Solución Implementada

### 1. Estandarización del campo de score en semantic_search.py

**Cambio principal:**
```python
# ANTES
"relevance": hit['_score'],
"summary": source['content'],

# DESPUÉS
"score": hit['_score'],  # ✅ Ahora usa 'score' para consistencia
"content": source['content'],  # ✅ También estandarizado a 'content'
```

### 2. Actualización de print_pretty_results

```python
# ANTES
print(f"   🎯 Relevancia: {fragment['relevance']:.3f}")
summary = fragment['summary']

# DESPUÉS
print(f"   🎯 Relevancia: {fragment['score']:.3f}")
content = fragment['content']
```

### 3. Verificación de consistencia en otras herramientas

- ✅ **lexical_search.py**: Ya usaba `"score"` correctamente
- ✅ **regex_search.py**: Actualizado para incluir campo `"fragments"` para compatibilidad

## Archivos Modificados

1. **src/semantic_search.py**
   - Cambio de `"relevance"` a `"score"` en `_format_results()`
   - Cambio de `"summary"` a `"content"` para consistencia
   - Actualización de `print_pretty_results()` para usar los nuevos nombres

2. **src/regex_search.py**
   - Añadido campo `"fragments"` para compatibilidad con `request_handler.py`
   - Añadido campo `"total_found"` para consistencia

## Resultado Esperado

Después de este fix, cuando el agente ejecute `semantic_search`, los scores de relevancia deberían mostrarse correctamente:

```
ANTES:
1. **FD-Darwin_Funcional0_v2.9.docx**
   - Fragmentos encontrados: 3
   - Relevancia máxima: 0.0000  ❌

DESPUÉS:
1. **FD-Darwin_Funcional0_v2.9.docx**
   - Fragmentos encontrados: 3
   - Relevancia máxima: 0.8542  ✅
```

## Campos Estandarizados Entre Herramientas

| Campo | semantic_search | lexical_search | regex_search | get_file_content |
|-------|----------------|----------------|--------------|------------------|
| `score` | ✅ | ✅ | N/A* | N/A |
| `content` | ✅ | ✅ | ✅ | ✅ |
| `file_name` | ✅ | ✅ | ✅ | ✅ |
| `fragments` | ✅ | ✅ | ✅ | N/A |
| `total_found` | ✅ | ✅ | ✅ | N/A |

*regex_search no tiene scores de relevancia porque solo busca coincidencias de patrones

## Testing

Para verificar el fix:

1. Ejecutar el agente con una consulta semántica
2. Verificar que los scores mostrados sean > 0.0000
3. Confirmar que los scores reflejan la similitud coseno de OpenSearch

```bash
# Test directo de la herramienta
python3 src/semantic_search.py "integraciones MuleSoft" --top-k 5

# Test a través del agente
python3 src/agent/main.py
# Luego hacer una consulta que active semantic_search
```

## Notas Técnicas

- Los scores de OpenSearch para búsqueda KNN (semántica) representan la similitud coseno entre vectores
- Los valores típicos están entre 0.0 y 1.0, donde valores más altos indican mayor similitud
- El campo `min_score` en la configuración filtra resultados por debajo de un umbral
