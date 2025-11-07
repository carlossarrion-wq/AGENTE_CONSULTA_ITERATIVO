# Preprocesamiento de Saltos de Línea en Streaming

## Problema Identificado

Al mostrar las respuestas del LLM por el chat, aparecían demasiados retornos de carro consecutivos (ej: `\n\n`, `\n\n\n`, etc.), lo que generaba espacios en blanco excesivos en la visualización.

## Solución Implementada

Se ha agregado un preprocesamiento automático en la máquina de estados de streaming (`StreamingStateMachine`) que elimina saltos de línea consecutivos durante el proceso de streaming.

### Cambios Realizados

#### 1. Modificación en `src/agent/streaming_state_machine.py`

Se agregaron los siguientes componentes:

**a) Buffer de preprocesamiento:**
```python
# Buffer para preprocesamiento de saltos de línea
self._newline_buffer = ""
```

**b) Método de preprocesamiento:**
```python
def _preprocess_token(self, token: str) -> str:
    """
    Preprocesa un token para eliminar saltos de línea consecutivos
    
    Estrategia: Acumula caracteres en un buffer temporal y solo libera
    cuando está seguro de que no hay más saltos de línea consecutivos.
    
    Convierte secuencias de \n\n (o más) en un solo \n
    """
```

**c) Integración en feed_token:**
```python
def feed_token(self, token: str) -> None:
    # Preprocesar token para eliminar saltos de línea consecutivos
    token = self._preprocess_token(token)
    
    # Acumular en buffer y en texto completo
    self.buffer += token
    self.accumulated_text += token
    # ...
```

### Comportamiento

El preprocesamiento funciona de la siguiente manera:

1. **Acumulación**: Cuando llegan caracteres `\n`, se acumulan en un buffer temporal
2. **Detección**: Cuando llega un carácter que NO es `\n`, se procesa el buffer acumulado
3. **Reducción**: Si hay 2 o más `\n` consecutivos, se reducen a un solo `\n`
4. **Preservación**: Si hay solo un `\n`, se mantiene tal cual

### Ejemplos

| Input | Output |
|-------|--------|
| `"Línea 1\n\nLínea 2"` | `"Línea 1\nLínea 2"` |
| `"Línea 1\n\n\nLínea 2"` | `"Línea 1\nLínea 2"` |
| `"Línea 1\nLínea 2"` | `"Línea 1\nLínea 2"` (sin cambios) |

### Ventajas de la Implementación

1. **Transparente**: El preprocesamiento ocurre automáticamente sin necesidad de cambios en otros módulos
2. **Eficiente**: Se procesa durante el streaming, sin necesidad de post-procesamiento
3. **Universal**: Funciona en todos los estados de la máquina (NEUTRAL, IN_THINKING, IN_ANSWER, etc.)
4. **Preserva formato**: Mantiene los saltos de línea simples que son necesarios para el formato

### Testing

Se creó un test completo en `src/test/test_newline_preprocessing.py` que verifica:

1. ✅ Eliminación de múltiples `\n\n` en texto plano
2. ✅ Eliminación de `\n\n` dentro de bloques `<thinking>`
3. ✅ Eliminación de `\n\n` dentro de bloques `<present_answer>`
4. ✅ Preservación de un solo `\n`
5. ✅ Funcionamiento correcto con streaming token por token

Todos los tests pasan exitosamente.

### Ejecución del Test

```bash
python3 src/test/test_newline_preprocessing.py
```

## Impacto

- **Mejora visual**: Las respuestas del LLM se muestran con espaciado apropiado
- **Sin efectos secundarios**: No afecta la funcionalidad existente
- **Rendimiento**: Impacto mínimo en el rendimiento del streaming

## Archivos Modificados

1. `src/agent/streaming_state_machine.py` - Agregado preprocesamiento de newlines
2. `src/test/test_newline_preprocessing.py` - Nuevo archivo de tests

## Fecha de Implementación

6 de noviembre de 2025
