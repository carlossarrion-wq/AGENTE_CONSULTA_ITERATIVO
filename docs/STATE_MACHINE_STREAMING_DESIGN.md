# Diseño de Máquina de Estados para Streaming Robusto

## Problema Actual
La solución actual intenta detectar fragmentos parciales de tags XML, pero es frágil y propensa a errores porque:
- Depende de heurísticas para detectar fragmentos
- No tiene certeza sobre qué mostrar y qué ocultar
- Puede mostrar contenido incorrecto si el LLM escribe de forma inesperada

## Solución: Máquina de Estados Determinista

### Principio Fundamental
**"Acumular tokens hasta tener certeza absoluta de qué hacer con ellos"**

El usuario prefiere esperar 1-2 segundos más a cambio de una salida correcta y limpia.

## Estados de la Máquina

```
┌─────────────────────────────────────────────────────────────┐
│                    ESTADO: NEUTRAL                          │
│  - Acumula tokens en buffer                                 │
│  - Busca inicio de tags conocidos                          │
│  - Libera texto plano cuando está seguro                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ├──── Detecta <thinking> ────────┐
                            │                                 │
                            │                                 ▼
                            │                    ┌────────────────────────┐
                            │                    │  ESTADO: IN_THINKING   │
                            │                    │  - Libera tokens       │
                            │                    │  - Color: amarillo     │
                            │                    │  - Hasta </thinking>   │
                            │                    └────────────────────────┘
                            │
                            ├──── Detecta <present_answer> ──┐
                            │                                 │
                            │                                 ▼
                            │                    ┌────────────────────────┐
                            │                    │ ESTADO: IN_ANSWER      │
                            │                    │  - Libera tokens       │
                            │                    │  - Color: verde        │
                            │                    │  - Hasta </present_..> │
                            │                    └────────────────────────┘
                            │
                            ├──── Detecta <tool_ ────────────┐
                            │                                 │
                            │                                 ▼
                            │                    ┌────────────────────────┐
                            │                    │  ESTADO: IN_TOOL       │
                            │                    │  - NO libera tokens    │
                            │                    │  - Acumula XML         │
                            │                    │  - Hasta </tool_...>   │
                            │                    └────────────────────────┘
                            │
                            └──── Detecta <answer>, <sources>, etc. ──┐
                                                                       │
                                                                       ▼
                                                          ┌────────────────────────┐
                                                          │ ESTADO: IN_METADATA    │
                                                          │  - NO libera tokens    │
                                                          │  - Acumula para parseo │
                                                          │  - Hasta </...>        │
                                                          └────────────────────────┘
```

## Implementación de la Máquina de Estados

### Clase: `StreamingStateMachine`

```python
class StreamState(Enum):
    NEUTRAL = "neutral"
    IN_THINKING = "in_thinking"
    IN_ANSWER = "in_answer"
    IN_TOOL = "in_tool"
    IN_METADATA = "in_metadata"
    WAITING_FOR_TAG_COMPLETION = "waiting_for_tag_completion"

class StreamingStateMachine:
    def __init__(self, display: StreamingDisplay):
        self.state = StreamState.NEUTRAL
        self.buffer = ""
        self.display = display
        
        # Configuración de tags
        self.opening_tags = {
            '<thinking>': StreamState.IN_THINKING,
            '<present_answer>': StreamState.IN_ANSWER,
            '<tool_semantic_search>': StreamState.IN_TOOL,
            '<tool_lexical_search>': StreamState.IN_TOOL,
            '<tool_regex_search>': StreamState.IN_TOOL,
            '<tool_get_file_content>': StreamState.IN_TOOL,
            '<answer>': StreamState.IN_METADATA,
            '<sources>': StreamState.IN_METADATA,
            '<confidence>': StreamState.IN_METADATA,
            '<suggestions>': StreamState.IN_METADATA,
        }
        
        self.closing_tags = {
            StreamState.IN_THINKING: '</thinking>',
            StreamState.IN_ANSWER: '</present_answer>',
            StreamState.IN_TOOL: ['</tool_semantic_search>', '</tool_lexical_search>', 
                                  '</tool_regex_search>', '</tool_get_file_content>'],
            StreamState.IN_METADATA: ['</answer>', '</sources>', '</confidence>', '</suggestions>'],
        }
        
        # Tamaño mínimo del buffer antes de decidir
        self.min_buffer_size = 50
        
    def feed_token(self, token: str):
        """
        Alimenta un token a la máquina de estados
        """
        self.buffer += token
        
        # Procesar según el estado actual
        if self.state == StreamState.NEUTRAL:
            self._process_neutral_state()
        elif self.state == StreamState.IN_THINKING:
            self._process_thinking_state()
        elif self.state == StreamState.IN_ANSWER:
            self._process_answer_state()
        elif self.state == StreamState.IN_TOOL:
            self._process_tool_state()
        elif self.state == StreamState.IN_METADATA:
            self._process_metadata_state()
        elif self.state == StreamState.WAITING_FOR_TAG_COMPLETION:
            self._process_waiting_state()
    
    def _process_neutral_state(self):
        """
        En estado NEUTRAL: busca tags de apertura
        """
        # Buscar tags de apertura
        for tag, next_state in self.opening_tags.items():
            if tag in self.buffer:
                # Encontrado tag completo
                before_tag = self.buffer.split(tag)[0]
                after_tag = self.buffer.split(tag, 1)[1]
                
                # Liberar texto antes del tag (si hay)
                if before_tag.strip():
                    self.display.stream_plain_text(before_tag)
                
                # Cambiar de estado
                self.state = next_state
                self.buffer = after_tag
                
                # Mostrar indicador según el nuevo estado
                if next_state == StreamState.IN_THINKING:
                    # Ya no mostramos nada aquí, se mostrará en _process_thinking_state
                    pass
                elif next_state == StreamState.IN_ANSWER:
                    # Ya no mostramos nada aquí, se mostrará en _process_answer_state
                    pass
                elif next_state == StreamState.IN_TOOL:
                    # Extraer nombre de herramienta del tag
                    tool_name = tag.replace('<tool_', '').replace('>', '')
                    self.display.show_tool_indicator(tool_name, {})
                
                return
        
        # Si el buffer contiene '<' pero no un tag completo, esperar
        if '<' in self.buffer:
            # Si el buffer es muy grande y aún no encontramos tag, liberar parte
            if len(self.buffer) > self.min_buffer_size:
                # Liberar todo hasta el último '<'
                last_bracket = self.buffer.rfind('<')
                to_release = self.buffer[:last_bracket]
                self.buffer = self.buffer[last_bracket:]
                
                if to_release.strip():
                    self.display.stream_plain_text(to_release)
        else:
            # No hay '<', liberar todo el buffer
            if self.buffer.strip():
                self.display.stream_plain_text(self.buffer)
            self.buffer = ""
    
    def _process_thinking_state(self):
        """
        En estado IN_THINKING: libera tokens hasta encontrar </thinking>
        """
        closing_tag = self.closing_tags[StreamState.IN_THINKING]
        
        if closing_tag in self.buffer:
            # Encontrado tag de cierre
            before_close = self.buffer.split(closing_tag)[0]
            after_close = self.buffer.split(closing_tag, 1)[1]
            
            # Liberar contenido antes del cierre
            if before_close:
                self.display.stream_thinking(before_close)
            
            # Volver a estado NEUTRAL
            self.state = StreamState.NEUTRAL
            self.buffer = after_close
        else:
            # No hay tag de cierre aún, liberar todo el buffer
            if self.buffer:
                self.display.stream_thinking(self.buffer)
            self.buffer = ""
    
    def _process_answer_state(self):
        """
        En estado IN_ANSWER: libera tokens hasta encontrar </present_answer>
        """
        closing_tag = self.closing_tags[StreamState.IN_ANSWER]
        
        if closing_tag in self.buffer:
            # Encontrado tag de cierre
            before_close = self.buffer.split(closing_tag)[0]
            after_close = self.buffer.split(closing_tag, 1)[1]
            
            # Liberar contenido antes del cierre
            if before_close:
                self.display.stream_answer(before_close)
            
            # Volver a estado NEUTRAL
            self.state = StreamState.NEUTRAL
            self.buffer = after_close
        else:
            # No hay tag de cierre aún, liberar todo el buffer
            if self.buffer:
                self.display.stream_answer(self.buffer)
            self.buffer = ""
    
    def _process_tool_state(self):
        """
        En estado IN_TOOL: NO libera tokens, solo acumula
        """
        closing_tags = self.closing_tags[StreamState.IN_TOOL]
        
        for closing_tag in closing_tags:
            if closing_tag in self.buffer:
                # Encontrado tag de cierre, volver a NEUTRAL
                after_close = self.buffer.split(closing_tag, 1)[1]
                self.state = StreamState.NEUTRAL
                self.buffer = after_close
                return
        
        # No hacer nada, solo acumular
    
    def _process_metadata_state(self):
        """
        En estado IN_METADATA: NO libera tokens, solo acumula
        """
        closing_tags = self.closing_tags[StreamState.IN_METADATA]
        
        for closing_tag in closing_tags:
            if closing_tag in self.buffer:
                # Encontrado tag de cierre, volver a NEUTRAL
                after_close = self.buffer.split(closing_tag, 1)[1]
                self.state = StreamState.NEUTRAL
                self.buffer = after_close
                return
        
        # No hacer nada, solo acumular
```

## Ventajas de esta Solución

1. **Determinista**: Cada estado tiene reglas claras sobre qué hacer
2. **Robusta**: No depende de heurísticas frágiles
3. **Certeza**: Solo libera tokens cuando está 100% seguro
4. **Mantenible**: Fácil agregar nuevos estados o tags
5. **Testeable**: Cada estado se puede probar independientemente

## Flujo de Ejemplo

```
Token: "Voy"     → NEUTRAL → Acumula en buffer
Token: " a"      → NEUTRAL → Acumula en buffer
Token: " buscar" → NEUTRAL → Acumula en buffer
Token: " <"      → NEUTRAL → Acumula (podría ser inicio de tag)
Token: "thin"    → NEUTRAL → Acumula (esperando tag completo)
Token: "king>"   → NEUTRAL → Detecta <thinking>, libera "Voy a buscar ", cambia a IN_THINKING
Token: "Nece"    → IN_THINKING → Libera "Nece" en amarillo
Token: "sito"    → IN_THINKING → Libera "sito" en amarillo
Token: "</th"    → IN_THINKING → Acumula (esperando tag completo)
Token: "inking>" → IN_THINKING → Detecta </thinking>, vuelve a NEUTRAL
```

## Implementación

La implementación se hará en un nuevo archivo: `src/agent/streaming_state_machine.py`

Este reemplazará la lógica actual en `simple_streaming_handler.py` con una solución mucho más robusta y mantenible.
