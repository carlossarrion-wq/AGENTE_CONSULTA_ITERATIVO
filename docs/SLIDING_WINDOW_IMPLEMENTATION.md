# Implementación del Mecanismo de Sliding Window

## Problema Identificado

Al realizar múltiples iteraciones de consulta al LLM, especialmente cuando se utilizan herramientas que devuelven grandes cantidades de contenido (como `get_file_content`), el historial conversacional crece indefinidamente hasta superar el límite del modelo, generando el siguiente error:

```
ValidationException: Input is too long for requested model.
```

## Solución Implementada

Se ha implementado un **mecanismo de sliding window** que mantiene automáticamente el historial conversacional dentro de los límites del modelo, eliminando las iteraciones más antiguas cuando se alcanza el límite de tokens.

## Características

### 1. Configuración Flexible

En `config/config.yaml`:

```yaml
conversation:
  max_history_turns: 15  # Número máximo de turnos a mantener
  context_window_tokens: 180000  # 90% de 200K tokens (límite del modelo)
  system_prompt_caching: true
  tool_results_caching: true
  enable_sliding_window: true  # Habilitar ventana deslizante
  min_turns_to_keep: 3  # Mínimo de turnos a mantener siempre
```

### 2. Límite de Tokens Configurable

- **Modelo Claude Haiku 4.5**: Soporta 200,000 tokens
- **Configuración actual**: 180,000 tokens (90% del límite)
- **Margen de seguridad**: 20,000 tokens para system prompt y respuesta del modelo

### 3. Funcionamiento Automático

El sistema aplica automáticamente el sliding window en cada request al LLM:

1. **Antes de enviar el request**: Se calcula el total de tokens en el historial
2. **Si supera el límite**: Se mantienen solo los turnos más recientes que caben en la ventana
3. **Turnos eliminados**: Los más antiguos se descartan automáticamente
4. **Logging detallado**: Se registra cuántos turnos se mantienen y cuántos se eliminan

### 4. Logging Informativo

Cuando se aplica el sliding window, se registra en los logs:

```
🔄 Sliding window aplicado:
   • Límite de tokens: 180000
   • Turnos totales en conversación: 20
   • Turnos mantenidos en contexto: 5
   • Turnos eliminados (más antiguos): 15
   • Tokens antes: 600280, después: ~150080
```

## Archivos Modificados

### 1. `config/config.yaml`
- Añadida configuración `enable_sliding_window: true`
- Ajustado `context_window_tokens: 180000` (90% de 200K)
- Añadido `min_turns_to_keep: 3`

### 2. `src/agent/llm_communication.py`
- Modificado método `send_request_with_conversation()`
- Integración con `ConversationManager.trim_context_to_window()`
- Añadido logging detallado del proceso de trimming

### 3. `src/agent/conversation_manager.py`
- Ya contenía el método `trim_context_to_window()` implementado
- Utiliza un algoritmo de sliding window basado en tokens

## Cómo Funciona

### Algoritmo de Sliding Window

```python
def trim_context_to_window(session_id, max_tokens):
    """
    1. Obtener todos los turnos de la conversación
    2. Iterar desde el turno más reciente hacia atrás
    3. Acumular tokens hasta alcanzar el límite
    4. Descartar turnos más antiguos que no caben
    5. Retornar contexto trimmed
    """
```

### Ejemplo de Uso

```python
# Conversación con 20 turnos (600K tokens)
# Límite: 180K tokens

# Resultado:
# - Se mantienen los últimos 5 turnos (~150K tokens)
# - Se eliminan los primeros 15 turnos
# - El LLM recibe solo el contexto reciente relevante
```

## Ventajas

1. **Prevención de errores**: Evita el error "Input is too long for requested model"
2. **Automático**: No requiere intervención manual
3. **Configurable**: Límites ajustables según necesidades
4. **Eficiente**: Mantiene solo el contexto relevante más reciente
5. **Transparente**: Logging detallado del proceso

## Pruebas

Se ha creado un script de prueba completo: `test_sliding_window.py`

### Ejecutar pruebas:

```bash
python3 test_sliding_window.py
```

### Resultados esperados:

```
✅ TODOS LOS TESTS PASARON EXITOSAMENTE
```

## Monitoreo

Para verificar el funcionamiento en producción, revisar los logs:

```bash
tail -f logs/agent.log | grep "Sliding window"
```

Buscar líneas como:

```
🔄 Sliding window aplicado:
   • Límite de tokens: 180000
   • Turnos totales en conversación: 25
   • Turnos mantenidos en contexto: 6
   • Turnos eliminados (más antiguos): 19
```

## Recomendaciones

1. **Ajustar límite según modelo**: Si cambias de modelo, ajusta `context_window_tokens`
2. **Monitorear logs**: Revisa periódicamente cuántos turnos se eliminan
3. **Optimizar herramientas**: Si una herramienta devuelve demasiado contenido, considera resumirlo
4. **Balance**: Mantener suficiente contexto pero sin saturar el modelo

## Desactivar Sliding Window (No Recomendado)

Si por alguna razón necesitas desactivar el sliding window:

```yaml
conversation:
  enable_sliding_window: false  # Desactivar (no recomendado)
```

**Advertencia**: Desactivar el sliding window puede causar errores cuando el historial crezca demasiado.

## Soporte

Para más información o problemas:
- Revisar logs en `logs/agent.log`
- Ejecutar tests: `python3 test_sliding_window.py`
- Verificar configuración en `config/config.yaml`
