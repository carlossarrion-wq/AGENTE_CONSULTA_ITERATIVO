# Estructura de los Logs JSON de Conversación

## Ubicación

Los logs se guardan en el directorio `logs/` con el formato:
```
conversation_{session_id}_{timestamp}.json
```

Ejemplo: `conversation_0a73a1ef-ccee-4872-9948-b8731baeb056_20251028_113010_352.json`

## Estructura Completa del JSON

```json
{
  "timestamp": "2025-10-28T11:30:10.352931",
  "session_id": "0a73a1ef-ccee-4872-9948-b8731baeb056",
  "user_input": "pregunta del usuario",
  "llm_response": "respuesta completa del LLM",
  "metrics": {
    "llm_time_ms": 21830.106,
    "tokens_input": 172470,
    "tokens_output": 1955,
    "cache_tokens_saved": 0,
    "iteration": 0,
    "interaction_type": "initial_request",
    "tools_executed": 0,
    "tools_successful": 0,
    "tools_failed": 0
  },
  "request_metadata": {
    "system_prompt": "prompt completo del sistema...",
    "conversation_history_sent_to_llm": [
      {
        "role": "user",
        "content": "mensaje anterior del usuario"
      },
      {
        "role": "assistant",
        "content": "respuesta anterior del asistente"
      }
    ],
    "sliding_window_info": {
      "enabled": true,
      "max_context_tokens": 180000,
      "total_turns_in_session": 20,
      "total_tokens_in_session": 600280,
      "turns_in_context": 5,
      "turns_removed": 15
    },
    "model_id": "eu.anthropic.claude-haiku-4-5-20251001-v1:0",
    "max_tokens": 4000,
    "temperature": 0.1,
    "stop_reason": "end_turn"
  }
}
```

## Descripción de Campos

### Campos Principales

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `timestamp` | string | Timestamp ISO 8601 de cuando se registró la interacción |
| `session_id` | string | UUID único de la sesión de conversación |
| `user_input` | string | El input del usuario en esta interacción |
| `llm_response` | string | La respuesta completa del LLM (puede incluir XML de herramientas) |

### Sección `metrics`

Métricas de rendimiento y ejecución:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `llm_time_ms` | float | Tiempo que tardó el LLM en responder (milisegundos) |
| `tokens_input` | int | Tokens de entrada enviados al LLM |
| `tokens_output` | int | Tokens de salida generados por el LLM |
| `cache_tokens_saved` | int | Tokens ahorrados por el sistema de caché |
| `iteration` | int | Número de iteración (0 = request inicial, 1+ = iteraciones con herramientas) |
| `interaction_type` | string | Tipo de interacción: `"initial_request"` o `"tool_results_response"` |
| `tools_executed` | int | Número de herramientas ejecutadas (solo en iteraciones) |
| `tools_successful` | int | Número de herramientas exitosas (solo en iteraciones) |
| `tools_failed` | int | Número de herramientas fallidas (solo en iteraciones) |

### Sección `request_metadata`

Metadatos completos del request enviado al LLM:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `system_prompt` | string | **Prompt de sistema completo** enviado al LLM |
| `conversation_history_sent_to_llm` | array | **Historial conversacional completo** enviado al LLM |
| `sliding_window_info` | object | **Información sobre el sliding window aplicado** |
| `model_id` | string | ID del modelo LLM utilizado |
| `max_tokens` | int | Máximo de tokens configurado para la respuesta |
| `temperature` | float | Temperatura configurada para el LLM |
| `stop_reason` | string | Razón por la que el LLM detuvo la generación |

### Subsección `conversation_history_sent_to_llm`

Array de mensajes en formato estructurado:

```json
[
  {
    "role": "user",
    "content": "mensaje del usuario"
  },
  {
    "role": "assistant",
    "content": "respuesta del asistente"
  }
]
```

**IMPORTANTE**: Este es el historial COMPLETO que se envió al LLM en esta interacción, después de aplicar el sliding window si estaba habilitado.

### Subsección `sliding_window_info`

Información detallada sobre el mecanismo de sliding window:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `enabled` | boolean | Si el sliding window está habilitado |
| `max_context_tokens` | int | Límite máximo de tokens configurado (ej: 180000) |
| `total_turns_in_session` | int | Total de turnos acumulados en la sesión |
| `total_tokens_in_session` | int | Total de tokens acumulados en la sesión |
| `turns_in_context` | int | Turnos que se enviaron al LLM (después de sliding window) |
| `turns_removed` | int | Turnos eliminados por el sliding window |

## Tipos de Interacciones

### 1. Request Inicial (`interaction_type: "initial_request"`)

Primera interacción del usuario en un turno de conversación.

**Características**:
- `iteration: 0`
- `user_input`: Pregunta o comando del usuario
- `llm_response`: Puede contener XML de herramientas o respuesta final
- `conversation_history_sent_to_llm`: Historial de turnos anteriores (puede estar vacío en primera interacción)

### 2. Respuesta a Herramientas (`interaction_type: "tool_results_response"`)

Interacción donde se envían resultados de herramientas al LLM.

**Características**:
- `iteration: 1, 2, 3...`
- `user_input`: Resultados de las herramientas formateados
- `llm_response`: Análisis del LLM de los resultados
- `tools_executed`, `tools_successful`, `tools_failed`: Métricas de ejecución
- `conversation_history_sent_to_llm`: Incluye toda la conversación hasta este punto

## Ejemplo de Uso del Sliding Window

### Escenario: Conversación larga que supera el límite

```json
{
  "sliding_window_info": {
    "enabled": true,
    "max_context_tokens": 180000,
    "total_turns_in_session": 20,
    "total_tokens_in_session": 600280,
    "turns_in_context": 5,
    "turns_removed": 15
  }
}
```

**Interpretación**:
- La sesión tiene 20 turnos totales (40 mensajes: 20 user + 20 assistant)
- Acumulan 600,280 tokens en total
- El sliding window está habilitado con límite de 180,000 tokens
- Solo se enviaron los últimos 5 turnos al LLM (~150,000 tokens)
- Se eliminaron los 15 turnos más antiguos para no saturar el modelo

## Análisis de Logs

### Ver historial completo enviado al LLM

```bash
cat logs/conversation_*.json | jq '.request_metadata.conversation_history_sent_to_llm'
```

### Ver información de sliding window

```bash
cat logs/conversation_*.json | jq '.request_metadata.sliding_window_info'
```

### Ver métricas de tokens

```bash
cat logs/conversation_*.json | jq '{
  tokens_input: .metrics.tokens_input,
  tokens_output: .metrics.tokens_output,
  total: (.metrics.tokens_input + .metrics.tokens_output),
  session_tokens: .request_metadata.sliding_window_info.total_tokens_in_session
}'
```

### Verificar si se aplicó sliding window

```bash
cat logs/conversation_*.json | jq 'select(.request_metadata.sliding_window_info.turns_removed > 0) | {
  timestamp: .timestamp,
  turns_removed: .request_metadata.sliding_window_info.turns_removed,
  turns_kept: .request_metadata.sliding_window_info.turns_in_context
}'
```

## Beneficios de esta Estructura

1. **Trazabilidad Completa**: Se puede reconstruir exactamente qué se envió al LLM
2. **Debug de Sliding Window**: Se puede verificar cuándo y cómo se aplicó el trimming
3. **Análisis de Tokens**: Métricas detalladas para optimización de costos
4. **Reproducibilidad**: Con el system_prompt y el historial completo, se puede reproducir cualquier interacción
5. **Auditoría**: Registro completo de todas las interacciones para compliance

## Notas Importantes

- Los logs JSON son **independientes** de los logs de texto en `agent.log`
- Cada interacción con el LLM genera un archivo JSON separado
- El `conversation_history_sent_to_llm` refleja el estado DESPUÉS de aplicar sliding window
- Los archivos JSON pueden ser grandes si el historial es extenso
- Se recomienda implementar rotación de logs para gestionar el espacio en disco
