"""
Color Utilities - Utilidades para colorear salida en terminal

Responsabilidad: Proporcionar funciones para colorear texto en terminal
- Códigos ANSI para colores
- Funciones helper para cada tipo de mensaje
- Soporte para deshabilitar colores si es necesario
"""


class Colors:
    """Códigos ANSI para colores en terminal"""
    
    # Colores básicos
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Colores brillantes
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Colores personalizados RGB (según especificación del usuario)
    DARK_BLUE = '\033[38;2;59;124;242m'      # #3B7CF2 - Para thinking del agente
    ORANGE = '\033[38;2;221;94;40m'          # #DD5E28 - Para XML de herramientas
    DARK_RED = '\033[38;2;229;4;6m'          # #E50406 - Para invocaciones de herramientas
    DARK_GREEN = '\033[38;2;79;136;63m'      # #4F883F - Para respuestas del LLM
    
    # Estilos
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    
    # Reset
    RESET = '\033[0m'
    
    # Flag para habilitar/deshabilitar colores
    ENABLED = True
    
    @classmethod
    def disable(cls):
        """Deshabilita los colores"""
        cls.ENABLED = False
    
    @classmethod
    def enable(cls):
        """Habilita los colores"""
        cls.ENABLED = True


def colorize(text: str, color: str, bold: bool = False) -> str:
    """
    Colorea un texto con el color especificado
    
    Args:
        text: Texto a colorear
        color: Código de color ANSI
        bold: Si debe aplicar negrita
        
    Returns:
        Texto coloreado
    """
    if not Colors.ENABLED:
        return text
    
    prefix = f"{Colors.BOLD}{color}" if bold else color
    return f"{prefix}{text}{Colors.RESET}"


# Funciones específicas para cada tipo de mensaje según especificación

def user_text(text: str, bold: bool = False) -> str:
    """
    Colorea texto del usuario en NEGRO
    
    Args:
        text: Texto del usuario
        bold: Si debe aplicar negrita
        
    Returns:
        Texto coloreado en negro
    """
    return colorize(text, Colors.BLACK, bold)


def llm_request(text: str, bold: bool = False) -> str:
    """
    Colorea texto enviado al LLM en AZUL
    
    Args:
        text: Texto enviado al LLM
        bold: Si debe aplicar negrita
        
    Returns:
        Texto coloreado en azul
    """
    return colorize(text, Colors.BLUE, bold)


def llm_response(text: str, bold: bool = False) -> str:
    """
    Colorea respuesta del LLM en VERDE
    
    Args:
        text: Respuesta del LLM
        bold: Si debe aplicar negrita
        
    Returns:
        Texto coloreado en verde
    """
    return colorize(text, Colors.GREEN, bold)


def tool_result(text: str, bold: bool = False) -> str:
    """
    Colorea resultado de herramientas en ROJO
    
    Args:
        text: Resultado de herramientas
        bold: Si debe aplicar negrita
        
    Returns:
        Texto coloreado en rojo
    """
    return colorize(text, Colors.RED, bold)


# Funciones personalizadas según especificación del usuario

def thinking_text(text: str, bold: bool = False) -> str:
    """
    Colorea el thinking del agente en AZUL OSCURO (#3B7CF2)
    
    Args:
        text: Texto del thinking
        bold: Si debe aplicar negrita
        
    Returns:
        Texto coloreado en azul oscuro
    """
    return colorize(text, Colors.DARK_BLUE, bold)


def tool_xml(text: str, bold: bool = False) -> str:
    """
    Colorea los textos XML de herramientas en NARANJA (#DD5E28)
    
    Args:
        text: Texto XML de herramientas
        bold: Si debe aplicar negrita
        
    Returns:
        Texto coloreado en naranja
    """
    return colorize(text, Colors.ORANGE, bold)


def tool_invocation(text: str, bold: bool = False) -> str:
    """
    Colorea las invocaciones a herramientas en ROJO OSCURO (#E50406)
    
    Args:
        text: Texto de invocación de herramienta
        bold: Si debe aplicar negrita
        
    Returns:
        Texto coloreado en rojo oscuro
    """
    return colorize(text, Colors.DARK_RED, bold)


def llm_response_custom(text: str, bold: bool = False) -> str:
    """
    Colorea las respuestas del LLM en VERDE OSCURO (#356D34)
    
    Args:
        text: Respuesta del LLM
        bold: Si debe aplicar negrita
        
    Returns:
        Texto coloreado en verde oscuro
    """
    return colorize(text, Colors.DARK_GREEN, bold)


# Funciones adicionales para otros tipos de mensajes

def info(text: str, bold: bool = False) -> str:
    """Colorea mensajes informativos en cyan"""
    return colorize(text, Colors.CYAN, bold)


def warning(text: str, bold: bool = False) -> str:
    """Colorea advertencias en amarillo"""
    return colorize(text, Colors.YELLOW, bold)


def error(text: str, bold: bool = False) -> str:
    """Colorea errores en rojo brillante"""
    return colorize(text, Colors.BRIGHT_RED, bold)


def success(text: str, bold: bool = False) -> str:
    """Colorea mensajes de éxito en verde brillante"""
    return colorize(text, Colors.BRIGHT_GREEN, bold)


def header(text: str) -> str:
    """Colorea encabezados en negrita"""
    return colorize(text, Colors.WHITE, bold=True)


def dim_text(text: str) -> str:
    """Colorea texto atenuado"""
    if not Colors.ENABLED:
        return text
    return f"{Colors.DIM}{text}{Colors.RESET}"


# Funciones para formatear secciones completas

def format_user_input_section(user_input: str) -> str:
    """
    Formatea una sección de input del usuario
    
    Args:
        user_input: Input del usuario
        
    Returns:
        Sección formateada con colores
    """
    separator = "=" * 64
    return f"""
{dim_text(separator)}
{header("👤 USUARIO:")}
{dim_text(separator)}
{user_text(user_input)}
{dim_text(separator)}
"""


def format_llm_request_section(system_prompt: str = None, user_input: str = None, 
                               conversation_history: list = None, model: str = None,
                               tokens_input: int = None, tokens_output: int = None,
                               execution_time_ms: float = None, truncate: int = 500) -> str:
    """
    Formatea una sección de request al LLM con detalles completos
    
    Args:
        system_prompt: Prompt del sistema
        user_input: Input del usuario
        conversation_history: Historial de conversación
        model: Modelo utilizado
        tokens_input: Tokens de entrada
        tokens_output: Tokens de salida
        execution_time_ms: Tiempo de ejecución
        truncate: Número de caracteres para truncar (0 = sin truncar)
        
    Returns:
        Sección formateada con colores
    """
    separator = "=" * 64
    subseparator = "-" * 64
    
    lines = [
        dim_text(separator),
        header("📤 REQUEST AL LLM:"),
        dim_text(separator)
    ]
    
    if model:
        lines.append(llm_request(f"Modelo: {model}"))
    
    if system_prompt:
        lines.append(llm_request(subseparator))
        lines.append(llm_request("SYSTEM PROMPT:"))
        prompt_text = system_prompt[:truncate] + "..." if truncate > 0 and len(system_prompt) > truncate else system_prompt
        lines.append(llm_request(prompt_text))
    
    if conversation_history:
        lines.append(llm_request(subseparator))
        lines.append(llm_request("HISTORIAL:"))
        for msg in conversation_history:
            lines.append(llm_request(f"  {msg}"))
    
    if user_input:
        lines.append(llm_request(subseparator))
        lines.append(llm_request("USER INPUT:"))
        lines.append(llm_request(user_input))
    
    if tokens_input or tokens_output or execution_time_ms:
        lines.append(llm_request(subseparator))
        if tokens_input:
            lines.append(llm_request(f"Tokens input: {tokens_input}"))
        if tokens_output:
            lines.append(llm_request(f"Tokens output: {tokens_output}"))
        if execution_time_ms:
            lines.append(llm_request(f"Tiempo: {execution_time_ms:.2f}ms"))
    
    lines.append(dim_text(separator))
    
    return "\n".join(lines)


def format_llm_response_section(content: str, model: str = None, tokens_input: int = None,
                                tokens_output: int = None, execution_time_ms: float = None,
                                truncate: int = 1000) -> str:
    """
    Formatea una sección de respuesta del LLM con detalles completos
    
    Args:
        content: Contenido de la respuesta
        model: Modelo utilizado
        tokens_input: Tokens de entrada
        tokens_output: Tokens de salida
        execution_time_ms: Tiempo de ejecución
        truncate: Número de caracteres para truncar (0 = sin truncar)
        
    Returns:
        Sección formateada con colores
    """
    separator = "=" * 64
    subseparator = "-" * 64
    
    lines = [
        dim_text(separator),
        header("📥 RESPUESTA DEL LLM:"),
        dim_text(separator)
    ]
    
    if model:
        lines.append(llm_response(f"Modelo: {model}"))
    
    if tokens_input or tokens_output or execution_time_ms:
        if tokens_input:
            lines.append(llm_response(f"Tokens input: {tokens_input}"))
        if tokens_output:
            lines.append(llm_response(f"Tokens output: {tokens_output}"))
        if execution_time_ms:
            lines.append(llm_response(f"Tiempo: {execution_time_ms:.2f}ms"))
        lines.append(llm_response(subseparator))
    
    response_text = content[:truncate] + f"\n... [truncado, total: {len(content)} caracteres]" if truncate > 0 and len(content) > truncate else content
    lines.append(llm_response(response_text))
    lines.append(dim_text(separator))
    
    return "\n".join(lines)


def format_tool_result_section(tool_name: str, success: bool = True, 
                               execution_time_ms: float = None, result_data: dict = None,
                               error_message: str = None, truncate: int = 500) -> str:
    """
    Formatea una sección de resultado de herramienta con detalles completos
    
    Args:
        tool_name: Nombre de la herramienta
        success: Si la ejecución fue exitosa
        execution_time_ms: Tiempo de ejecución
        result_data: Datos del resultado
        error_message: Mensaje de error si falló
        truncate: Número de caracteres para truncar (0 = sin truncar)
        
    Returns:
        Sección formateada con colores
    """
    separator = "=" * 64
    subseparator = "-" * 64
    
    lines = [
        dim_text(separator),
        header(f"🔧 RESULTADO DE HERRAMIENTA: {tool_name}"),
        dim_text(separator)
    ]
    
    status = "✅ Exitosa" if success else "❌ Fallida"
    lines.append(tool_result(f"Estado: {status}"))
    
    if execution_time_ms:
        lines.append(tool_result(f"Tiempo: {execution_time_ms:.2f}ms"))
    
    if success and result_data:
        lines.append(tool_result(subseparator))
        result_str = str(result_data)
        result_text = result_str[:truncate] + f"\n... [truncado, total: {len(result_str)} caracteres]" if truncate > 0 and len(result_str) > truncate else result_str
        lines.append(tool_result(result_text))
    elif not success and error_message:
        lines.append(tool_result(subseparator))
        lines.append(tool_result(f"Error: {error_message}"))
    
    lines.append(dim_text(separator))
    
    return "\n".join(lines)


def format_metrics_section(total_time_ms: float = None, llm_time_ms: float = None,
                           tools_time_ms: float = None, tokens_input: int = None,
                           tokens_output: int = None, cache_tokens_saved: int = None,
                           tools_executed: int = None, tools_successful: int = None) -> str:
    """
    Formatea una sección de métricas con detalles completos
    
    Args:
        total_time_ms: Tiempo total
        llm_time_ms: Tiempo LLM
        tools_time_ms: Tiempo herramientas
        tokens_input: Tokens de entrada
        tokens_output: Tokens de salida
        cache_tokens_saved: Tokens ahorrados por cache
        tools_executed: Herramientas ejecutadas
        tools_successful: Herramientas exitosas
        
    Returns:
        Sección formateada con colores
    """
    lines = [
        "",
        info("📊 MÉTRICAS DE PROCESAMIENTO:")
    ]
    
    if total_time_ms is not None:
        lines.append(info(f"  ⏱️  Tiempo total: {total_time_ms:.2f}ms"))
    if llm_time_ms is not None:
        lines.append(info(f"  🤖 Tiempo LLM: {llm_time_ms:.2f}ms"))
    if tools_time_ms is not None:
        lines.append(info(f"  🔧 Tiempo herramientas: {tools_time_ms:.2f}ms"))
    if tokens_input is not None and tokens_output is not None:
        lines.append(info(f"  📝 Tokens input: {tokens_input} | output: {tokens_output}"))
    if cache_tokens_saved is not None:
        lines.append(info(f"  💾 Tokens ahorrados (cache): {cache_tokens_saved}"))
    if tools_executed is not None and tools_successful is not None:
        lines.append(info(f"  🔍 Herramientas ejecutadas: {tools_executed} ({tools_successful} exitosas)"))
    
    return "\n".join(lines)
