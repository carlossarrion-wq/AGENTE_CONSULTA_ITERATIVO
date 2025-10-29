"""
Streaming Display - Gestiona la visualización en tiempo real del contenido

Responsabilidad: Mostrar contenido del LLM en streaming
- Visualización diferenciada por tipo de bloque
- Aplicación de colores y formato
- Indicadores de progreso para herramientas
- Gestión de secciones y transiciones
"""

import sys
import logging
from typing import Optional
from datetime import datetime

from color_utils import (
    thinking_text,
    tool_invocation,
    llm_response_custom,
    info,
    success,
    warning,
    error,
    dim_text
)


class StreamingDisplay:
    """
    Gestiona la visualización en tiempo real del contenido
    Aplica colores y formato según el tipo de contenido
    """
    
    def __init__(self, enable_colors: bool = True):
        """
        Inicializa el display de streaming
        
        Args:
            enable_colors: Si debe usar colores en la salida
        """
        self.logger = logging.getLogger(__name__)
        self.enable_colors = enable_colors
        self.current_section: Optional[str] = None
        self.is_paused = False
        
        # Mensajes de herramientas
        self.tool_messages = {
            'tool_semantic_search': '🔍 Realizando búsqueda semántica...',
            'tool_lexical_search': '📝 Realizando búsqueda léxica...',
            'tool_regex_search': '🔎 Buscando patrones con regex...',
            'tool_get_file_content': '📄 Obteniendo contenido del archivo...',
            'tool_web_crawler': '🌐 Buscando información en internet...'
        }
        
        self.logger.debug("StreamingDisplay inicializado")
    
    def stream_thinking(self, content: str):
        """
        Muestra contenido de thinking en tiempo real
        
        Args:
            content: Contenido del bloque thinking
        """
        if self.is_paused:
            return
        
        # Mostrar encabezado si es una nueva sección
        if self.current_section != "thinking":
            print(f"\n{warning('🔍 Reflexionando...')}")
            self.current_section = "thinking"
        
        # Mostrar contenido en amarillo (usando warning que es amarillo)
        colored_content = warning(content) if self.enable_colors else content
        print(colored_content, end='', flush=True)
        
        self.logger.debug(f"Thinking mostrado: {len(content)} caracteres")
    
    def show_tool_indicator(self, tool_name: str, params: dict = None):
        """
        Muestra indicador de ejecución de herramienta con parámetros
        
        Args:
            tool_name: Nombre de la herramienta
            params: Parámetros de la herramienta (opcional)
        """
        if self.is_paused:
            return
        
        # Construir mensaje en formato compacto sin comillas
        if params:
            params_str = self._format_tool_params_compact(params)
            message = f"🔧 Ejecutando {tool_name} ({params_str})"
        else:
            message = f"🔧 Ejecutando {tool_name}"
        
        # Mostrar con color (sin bloque de código)
        colored_message = tool_invocation(message) if self.enable_colors else message
        print(f"\n{colored_message}", flush=True)
        
        self.current_section = "tool"
        self.logger.debug(f"Indicador de herramienta mostrado: {tool_name}")
    
    def _format_tool_params_compact(self, params: dict) -> str:
        """
        Formatea los parámetros de una herramienta en formato compacto
        
        Args:
            params: Diccionario de parámetros
            
        Returns:
            String formateado con los parámetros en formato compacto
        """
        formatted_parts = []
        
        # El primer parámetro (generalmente 'query') se muestra sin nombre de clave
        first_param = True
        for key, value in params.items():
            if first_param and key == 'query':
                # Primer parámetro (query) sin nombre de clave y sin comillas
                if isinstance(value, str):
                    if len(value) > 50:
                        formatted_parts.append(f'{value[:50]}...')
                    else:
                        formatted_parts.append(value)
                first_param = False
            else:
                # Resto de parámetros con nombre de clave pero sin comillas
                if isinstance(value, str) and len(value) > 50:
                    value_str = f'{value[:50]}...'
                elif isinstance(value, str):
                    value_str = value
                elif isinstance(value, list):
                    value_str = str(value)
                else:
                    value_str = str(value)
                
                formatted_parts.append(f"{key}={value_str}")
        
        return ", ".join(formatted_parts)
    
    def show_tool_result(self, tool_name: str, result):
        """
        Muestra resultado de herramienta (opcional, breve)
        
        Args:
            tool_name: Nombre de la herramienta
            result: Resultado de la herramienta
        """
        if self.is_paused:
            return
        
        # Mostrar solo un indicador breve de éxito/fallo
        if result.success:
            message = f"  ✓ {tool_name} completada"
            colored_message = success(message) if self.enable_colors else message
        else:
            message = f"  ✗ {tool_name} falló"
            colored_message = error(message) if self.enable_colors else message
        
        print(colored_message, flush=True)
        
        self.logger.debug(f"Resultado de herramienta mostrado: {tool_name}")
    
    def stream_answer(self, content: str):
        """
        Muestra respuesta final en tiempo real
        
        Args:
            content: Contenido de la respuesta
        """
        if self.is_paused:
            return
        
        # Mostrar encabezado si es una nueva sección
        if self.current_section != "answer":
            print(f"\n{llm_response_custom('💬 Respuesta...')}")
            self.current_section = "answer"
        
        # Mostrar contenido en verde oscuro (usando llm_response_custom que es verde oscuro #4F883F)
        colored_content = llm_response_custom(content) if self.enable_colors else content
        print(colored_content, end='', flush=True)
        
        self.logger.debug(f"Answer mostrado: {len(content)} caracteres")
    
    def stream_plain_text(self, content: str):
        """
        Muestra texto plano en tiempo real
        
        Args:
            content: Contenido de texto plano
        """
        if self.is_paused:
            return
        
        # Texto plano sin color especial
        print(content, end='', flush=True)
        
        self.current_section = "plain"
        self.logger.debug(f"Texto plano mostrado: {len(content)} caracteres")
    
    def show_error(self, error_message: str):
        """
        Muestra un mensaje de error
        
        Args:
            error_message: Mensaje de error
        """
        colored_message = error(f"\n❌ Error: {error_message}") if self.enable_colors else f"\n❌ Error: {error_message}"
        print(colored_message, flush=True)
        
        self.logger.error(f"Error mostrado: {error_message}")
    
    def show_warning(self, warning_message: str):
        """
        Muestra un mensaje de advertencia
        
        Args:
            warning_message: Mensaje de advertencia
        """
        colored_message = warning(f"\n⚠️  {warning_message}") if self.enable_colors else f"\n⚠️  {warning_message}"
        print(colored_message, flush=True)
        
        self.logger.warning(f"Advertencia mostrada: {warning_message}")
    
    def show_info(self, info_message: str):
        """
        Muestra un mensaje informativo
        
        Args:
            info_message: Mensaje informativo
        """
        colored_message = info(f"\nℹ️  {info_message}") if self.enable_colors else f"\nℹ️  {info_message}"
        print(colored_message, flush=True)
        
        self.logger.info(f"Info mostrada: {info_message}")
    
    def pause(self):
        """Pausa la visualización"""
        self.is_paused = True
        self.logger.debug("Display pausado")
    
    def resume(self):
        """Reanuda la visualización"""
        self.is_paused = False
        self.logger.debug("Display reanudado")
    
    def finalize(self):
        """
        Finaliza el display
        Asegura que haya un salto de línea final
        """
        if self.current_section:
            print()  # Salto de línea final
        
        self.current_section = None
        self.logger.debug("Display finalizado")
    
    def clear_section(self):
        """Limpia la sección actual"""
        self.current_section = None
    
    def show_separator(self, char: str = "─", length: int = 64):
        """
        Muestra un separador visual
        
        Args:
            char: Carácter para el separador
            length: Longitud del separador
        """
        separator = char * length
        colored_separator = dim_text(separator) if self.enable_colors else separator
        print(f"\n{colored_separator}", flush=True)
    
    def show_header(self, text: str):
        """
        Muestra un encabezado destacado
        
        Args:
            text: Texto del encabezado
        """
        self.show_separator()
        colored_text = success(f"  {text}") if self.enable_colors else f"  {text}"
        print(colored_text, flush=True)
        self.show_separator()
    
    def show_progress(self, current: int, total: int, description: str = ""):
        """
        Muestra una barra de progreso simple
        
        Args:
            current: Valor actual
            total: Valor total
            description: Descripción del progreso
        """
        if total == 0:
            return
        
        percentage = (current / total) * 100
        bar_length = 30
        filled = int(bar_length * current / total)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        progress_text = f"\r{description} [{bar}] {percentage:.1f}% ({current}/{total})"
        colored_text = info(progress_text) if self.enable_colors else progress_text
        
        print(colored_text, end='', flush=True)
        
        if current == total:
            print()  # Nueva línea al completar
    
    def show_streaming_indicator(self):
        """Muestra un indicador de que el streaming está activo"""
        indicator = "⋯"
        colored_indicator = dim_text(indicator) if self.enable_colors else indicator
        print(colored_indicator, end='', flush=True)
    
    def show_completion_message(self, duration_ms: float = None):
        """
        Muestra mensaje de finalización
        
        Args:
            duration_ms: Duración total en milisegundos
        """
        message = "\n✅ Procesamiento completado"
        if duration_ms:
            message += f" ({duration_ms:.2f}ms)"
        
        colored_message = success(message) if self.enable_colors else message
        print(colored_message, flush=True)


class StreamingDisplayWithBuffer(StreamingDisplay):
    """
    Versión del display que acumula contenido en buffer
    Útil para testing o cuando se necesita el contenido completo
    """
    
    def __init__(self, enable_colors: bool = True):
        """Inicializa el display con buffer"""
        super().__init__(enable_colors)
        self.thinking_buffer = []
        self.answer_buffer = []
        self.plain_text_buffer = []
        self.tool_indicators = []
    
    def stream_thinking(self, content: str):
        """Muestra y guarda thinking"""
        super().stream_thinking(content)
        self.thinking_buffer.append(content)
    
    def stream_answer(self, content: str):
        """Muestra y guarda answer"""
        super().stream_answer(content)
        self.answer_buffer.append(content)
    
    def stream_plain_text(self, content: str):
        """Muestra y guarda texto plano"""
        super().stream_plain_text(content)
        self.plain_text_buffer.append(content)
    
    def show_tool_indicator(self, tool_name: str, params: dict = None):
        """Muestra y guarda indicador de herramienta"""
        super().show_tool_indicator(tool_name, params)
        self.tool_indicators.append((tool_name, params))
    
    def get_thinking_content(self) -> str:
        """Obtiene todo el contenido de thinking"""
        return "".join(self.thinking_buffer)
    
    def get_answer_content(self) -> str:
        """Obtiene todo el contenido de answer"""
        return "".join(self.answer_buffer)
    
    def get_plain_text_content(self) -> str:
        """Obtiene todo el texto plano"""
        return "".join(self.plain_text_buffer)
    
    def get_all_content(self) -> str:
        """Obtiene todo el contenido acumulado"""
        return (
            self.get_thinking_content() +
            self.get_answer_content() +
            self.get_plain_text_content()
        )
    
    def clear_buffers(self):
        """Limpia todos los buffers"""
        self.thinking_buffer.clear()
        self.answer_buffer.clear()
        self.plain_text_buffer.clear()
        self.tool_indicators.clear()


def main():
    """Función principal para testing"""
    import time
    import logging
    
    # Configurar logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear display
    display = StreamingDisplay(enable_colors=True)
    
    print("=" * 64)
    print("DEMO DE STREAMING DISPLAY")
    print("=" * 64)
    
    # Simular thinking
    thinking_content = """Voy a buscar información sobre autenticación.
Primero realizaré una búsqueda semántica para encontrar
documentación relevante."""
    
    for line in thinking_content.split('\n'):
        display.stream_thinking(line + '\n')
        time.sleep(0.3)
    
    # Simular herramienta
    time.sleep(0.5)
    display.show_tool_indicator('tool_semantic_search')
    time.sleep(1.0)
    
    # Simular resultado de herramienta (mock)
    class MockResult:
        success = True
    
    display.show_tool_result('tool_semantic_search', MockResult())
    
    # Simular answer
    time.sleep(0.5)
    answer_content = """Basándome en los resultados encontrados, la autenticación
en el sistema se gestiona mediante tokens JWT.

El proceso incluye:
1. Validación de credenciales
2. Generación de token
3. Verificación en cada request"""
    
    for line in answer_content.split('\n'):
        display.stream_answer(line + '\n')
        time.sleep(0.3)
    
    # Finalizar
    display.finalize()
    
    print("\n" + "=" * 64)
    print("DEMO COMPLETADA")
    print("=" * 64)
    
    # Demo de display con buffer
    print("\n\nDEMO DE DISPLAY CON BUFFER:")
    print("=" * 64)
    
    buffered_display = StreamingDisplayWithBuffer(enable_colors=True)
    
    buffered_display.stream_thinking("Reflexionando...")
    buffered_display.show_tool_indicator('tool_lexical_search')
    buffered_display.stream_answer("Respuesta final")
    
    buffered_display.finalize()
    
    print("\n\nContenido acumulado:")
    print(f"Thinking: {buffered_display.get_thinking_content()}")
    print(f"Answer: {buffered_display.get_answer_content()}")
    print(f"Tools: {buffered_display.tool_indicators}")


if __name__ == "__main__":
    main()
