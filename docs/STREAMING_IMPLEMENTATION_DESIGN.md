# Diseño de Implementación de Streaming con Procesamiento Diferenciado

## 📋 Resumen Ejecutivo

Este documento describe la implementación de streaming para respuestas del LLM con procesamiento diferenciado según el tipo de bloque XML. El objetivo es mostrar en tiempo real el contenido de bloques `<thinking>` y `<present_answer>`, mientras que los bloques de herramientas se procesan sin mostrar el XML al usuario.

## 🎯 Objetivos

1. **Streaming en tiempo real**: Mostrar contenido al usuario mientras se genera
2. **Procesamiento diferenciado**: Tratar cada tipo de bloque de manera específica
3. **Experiencia de usuario mejorada**: Feedback visual inmediato
4. **Compatibilidad**: Mantener compatibilidad con el sistema actual

## 🏗️ Arquitectura de la Solución

### Componentes Principales

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS Bedrock (LLM)                        │
│                  (Streaming Response)                       │
└────────────────────┬────────────────────────────────────────┘
                     │ Stream de tokens
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              StreamingResponseParser                        │
│  • Detecta inicio/fin de bloques XML                       │
│  • Clasifica bloques (thinking/tool/answer)                │
│  • Emite eventos por tipo de bloque                        │
└────────────────────┬────────────────────────────────────────┘
                     │ Eventos tipados
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           StreamingResponseHandler                          │
│  • Procesa eventos según tipo                              │
│  • Ejecuta herramientas cuando se completan                │
│  • Formatea contenido para display                         │
└────────────────────┬────────────────────────────────────────┘
                     │ Contenido formateado
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              StreamingDisplay                               │
│  • Muestra contenido en tiempo real                        │
│  • Aplica colores y formato                                │
│  • Gestiona indicadores de progreso                        │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Nuevos Módulos a Crear

### 1. `streaming_response_parser.py`

**Responsabilidad**: Parser de streaming que detecta y clasifica bloques XML en tiempo real.

```python
class BlockType(Enum):
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    PRESENT_ANSWER = "present_answer"
    PLAIN_TEXT = "plain_text"

class StreamingBlock:
    block_type: BlockType
    content: str
    tool_name: Optional[str]
    is_complete: bool

class StreamingResponseParser:
    """
    Parser incremental que procesa el stream token por token
    y detecta bloques XML en tiempo real
    """
    
    def __init__(self):
        self.buffer = ""
        self.current_block = None
        self.block_stack = []
        
    def feed_token(self, token: str) -> List[StreamingBlock]:
        """
        Alimenta el parser con un nuevo token
        Retorna bloques completados
        """
        
    def detect_block_start(self) -> Optional[BlockType]:
        """Detecta inicio de bloque XML"""
        
    def detect_block_end(self) -> bool:
        """Detecta fin de bloque XML"""
        
    def extract_tool_name(self, xml_tag: str) -> str:
        """Extrae nombre de herramienta del tag XML"""
```

### 2. `streaming_response_handler.py`

**Responsabilidad**: Maneja eventos de streaming y coordina acciones según tipo de bloque.

```python
class StreamingResponseHandler:
    """
    Maneja el procesamiento de bloques según su tipo
    """
    
    def __init__(self, tool_executor, display):
        self.tool_executor = tool_executor
        self.display = display
        self.pending_tools = []
        
    async def handle_block(self, block: StreamingBlock):
        """
        Procesa un bloque según su tipo
        """
        if block.block_type == BlockType.THINKING:
            await self.handle_thinking_block(block)
        elif block.block_type == BlockType.TOOL_CALL:
            await self.handle_tool_block(block)
        elif block.block_type == BlockType.PRESENT_ANSWER:
            await self.handle_answer_block(block)
        else:
            await self.handle_plain_text(block)
    
    async def handle_thinking_block(self, block: StreamingBlock):
        """Muestra contenido de thinking en streaming"""
        self.display.stream_thinking(block.content)
    
    async def handle_tool_block(self, block: StreamingBlock):
        """Procesa llamada a herramienta"""
        # Mostrar indicador
        self.display.show_tool_indicator(block.tool_name)
        
        # Ejecutar herramienta
        result = await self.tool_executor.execute(
            block.tool_name, 
            block.content
        )
        
        # Guardar resultado para contexto
        self.pending_tools.append(result)
    
    async def handle_answer_block(self, block: StreamingBlock):
        """Muestra respuesta final en streaming"""
        self.display.stream_answer(block.content)
```

### 3. `streaming_display.py`

**Responsabilidad**: Gestiona la visualización en tiempo real del contenido.

```python
class StreamingDisplay:
    """
    Gestiona la visualización en tiempo real
    """
    
    def __init__(self):
        self.current_section = None
        
    def stream_thinking(self, content: str):
        """
        Muestra contenido de thinking en tiempo real
        """
        if self.current_section != "thinking":
            print(f"\n{dim_text('💭 Reflexionando...')}")
            self.current_section = "thinking"
        
        # Imprimir contenido sin salto de línea
        print(content, end='', flush=True)
    
    def show_tool_indicator(self, tool_name: str):
        """
        Muestra indicador de ejecución de herramienta
        """
        tool_messages = {
            'semantic_search': '🔍 Realizando búsqueda semántica...',
            'lexical_search': '📝 Realizando búsqueda léxica...',
            'regex_search': '🔎 Buscando patrones...',
            'get_file_content': '📄 Obteniendo contenido del archivo...'
        }
        
        message = tool_messages.get(tool_name, f'🔧 Ejecutando {tool_name}...')
        print(f"\n{info(message)}")
    
    def stream_answer(self, content: str):
        """
        Muestra respuesta final en tiempo real
        """
        if self.current_section != "answer":
            print(f"\n{success('✨ Respuesta:')}")
            self.current_section = "answer"
        
        # Imprimir contenido sin salto de línea
        print(content, end='', flush=True)
    
    def finalize(self):
        """Finaliza el display"""
        print("\n")  # Salto de línea final
```

## 🔄 Modificaciones a Módulos Existentes

### 1. `llm_communication.py`

Agregar método para streaming:

```python
def send_request_streaming(self, llm_request: LLMRequest, 
                          callback: Callable[[str], None]) -> LLMResponse:
    """
    Envía request con streaming habilitado
    
    Args:
        llm_request: Request al LLM
        callback: Función callback para cada token recibido
    """
    # Modificar body para habilitar streaming
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": llm_request.max_tokens,
        "system": llm_request.system_prompt,
        "messages": [...],
        "temperature": llm_request.temperature,
        "stream": True  # ← HABILITAR STREAMING
    }
    
    # Usar invoke_model_with_response_stream
    response = self.bedrock_client.invoke_model_with_response_stream(
        modelId=self.model_id,
        body=json.dumps(body)
    )
    
    # Procesar stream
    full_content = ""
    for event in response['body']:
        chunk = json.loads(event['chunk']['bytes'])
        
        if chunk['type'] == 'content_block_delta':
            token = chunk['delta']['text']
            full_content += token
            callback(token)  # ← Llamar callback con cada token
    
    return LLMResponse(...)
```

### 2. `chat_interface.py`

Integrar streaming en el flujo principal:

```python
def process_user_input_streaming(self, user_input: str):
    """
    Procesa input del usuario con streaming
    """
    # Crear parser y handler
    parser = StreamingResponseParser()
    display = StreamingDisplay()
    handler = StreamingResponseHandler(self.tool_executor, display)
    
    # Callback para procesar tokens
    async def token_callback(token: str):
        # Alimentar parser
        blocks = parser.feed_token(token)
        
        # Procesar bloques completados
        for block in blocks:
            await handler.handle_block(block)
    
    # Enviar request con streaming
    response = self.llm_comm.send_request_streaming(
        llm_request=...,
        callback=token_callback
    )
    
    # Finalizar display
    display.finalize()
    
    # Actualizar conversación con respuesta completa
    self.conversation_manager.add_assistant_turn(...)
```

## 🎨 Ejemplo de Flujo Completo

### Input del Usuario
```
"¿Cómo funciona la autenticación en Darwin?"
```

### Respuesta del LLM (streaming)
```xml
<thinking>
Necesito buscar información sobre autenticación en Darwin.
Voy a realizar una búsqueda semántica primero.
</thinking>

<semantic_search>
<query>autenticación login usuarios Darwin</query>
<top_k>5</top_k>
</semantic_search>

<thinking>
Ahora voy a buscar implementaciones específicas en el código.
</thinking>

<lexical_search>
<query>authenticateUser validateToken</query>
</lexical_search>

<present_answer>
Basándome en la información encontrada, la autenticación en Darwin funciona así:

## Sistema de Autenticación

1. **Validación de Credenciales**
   - Se validan usuario y contraseña contra la base de datos
   - Se utiliza bcrypt para hash de contraseñas

2. **Generación de Tokens**
   - Se generan JWT tokens con expiración de 24 horas
   - Los tokens incluyen información del usuario y permisos

3. **Middleware de Protección**
   - Todas las rutas protegidas validan el token
   - Se verifica la firma y expiración del token
</present_answer>
```

### Output Mostrado al Usuario (en tiempo real)

```
💭 Reflexionando...
Necesito buscar información sobre autenticación en Darwin.
Voy a realizar una búsqueda semántica primero.

🔍 Realizando búsqueda semántica...

💭 Reflexionando...
Ahora voy a buscar implementaciones específicas en el código.

📝 Realizando búsqueda léxica...

✨ Respuesta:
Basándome en la información encontrada, la autenticación en Darwin funciona así:

## Sistema de Autenticación

1. **Validación de Credenciales**
   - Se validan usuario y contraseña contra la base de datos
   - Se utiliza bcrypt para hash de contraseñas

2. **Generación de Tokens**
   - Se generan JWT tokens con expiración de 24 horas
   - Los tokens incluyen información del usuario y permisos

3. **Middleware de Protección**
   - Todas las rutas protegidas validan el token
   - Se verifica la firma y expiración del token
```

## 🔧 Implementación por Fases

### Fase 1: Parser de Streaming (1-2 días)
- [ ] Crear `streaming_response_parser.py`
- [ ] Implementar detección de bloques XML
- [ ] Implementar buffer incremental
- [ ] Tests unitarios del parser

### Fase 2: Handler de Streaming (1-2 días)
- [ ] Crear `streaming_response_handler.py`
- [ ] Implementar lógica de procesamiento por tipo
- [ ] Integrar con tool_executor
- [ ] Tests de integración

### Fase 3: Display de Streaming (1 día)
- [ ] Crear `streaming_display.py`
- [ ] Implementar visualización en tiempo real
- [ ] Aplicar colores y formato
- [ ] Tests de visualización

### Fase 4: Integración (2-3 días)
- [ ] Modificar `llm_communication.py` para streaming
- [ ] Actualizar `chat_interface.py`
- [ ] Integrar todos los componentes
- [ ] Tests end-to-end

### Fase 5: Refinamiento (1-2 días)
- [ ] Manejo de errores en streaming
- [ ] Optimización de performance
- [ ] Documentación completa
- [ ] Tests de estrés

## 🎯 Consideraciones Técnicas

### 1. Detección de Bloques XML en Streaming

**Desafío**: Los tokens pueden llegar fragmentados, cortando tags XML.

**Solución**: Buffer incremental que mantiene contexto:

```python
class XMLBlockDetector:
    def __init__(self):
        self.buffer = ""
        self.in_tag = False
        self.tag_name = ""
        
    def feed(self, token: str):
        self.buffer += token
        
        # Detectar inicio de tag
        if '<' in token and not self.in_tag:
            self.in_tag = True
            # Extraer nombre de tag
            match = re.search(r'<(\w+)', self.buffer)
            if match:
                self.tag_name = match.group(1)
        
        # Detectar fin de tag
        if self.in_tag and f'</{self.tag_name}>' in self.buffer:
            # Bloque completo detectado
            return self.extract_block()
```

### 2. Sincronización de Herramientas

**Desafío**: Las herramientas deben ejecutarse antes de continuar con el streaming.

**Solución**: Sistema de eventos asíncronos:

```python
async def handle_tool_block(self, block):
    # Pausar streaming visual
    self.display.pause()
    
    # Ejecutar herramienta
    result = await self.tool_executor.execute_async(block)
    
    # Reanudar streaming
    self.display.resume()
```

### 3. Manejo de Errores

**Desafío**: Errores durante streaming pueden dejar el display en estado inconsistente.

**Solución**: Context managers y cleanup:

```python
class StreamingSession:
    def __enter__(self):
        self.display.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.display.show_error(exc_val)
        self.display.finalize()
```

## 📊 Métricas de Éxito

1. **Latencia**: Primera palabra visible en < 500ms
2. **Fluidez**: Actualización visual cada 50-100ms
3. **Precisión**: 100% de bloques XML detectados correctamente
4. **Robustez**: Manejo graceful de errores en 100% de casos

## 🔐 Consideraciones de Seguridad

1. **Validación de XML**: Sanitizar contenido antes de mostrar
2. **Límites de Buffer**: Prevenir memory exhaustion
3. **Timeout**: Límite de tiempo para streaming (ej: 60s)

## 📚 Referencias

- [AWS Bedrock Streaming API](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-claude.html)
- [Anthropic Claude Streaming](https://docs.anthropic.com/claude/reference/streaming)
- [Python AsyncIO](https://docs.python.org/3/library/asyncio.html)

## 🎓 Próximos Pasos

1. Revisar y aprobar este diseño
2. Crear branch `feature/streaming-implementation`
3. Implementar Fase 1 (Parser)
4. Iterar con feedback
