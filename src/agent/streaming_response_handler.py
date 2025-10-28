"""
Streaming Response Handler - Maneja el procesamiento de bloques de streaming

Responsabilidad: Procesar bloques según su tipo y coordinar acciones
- Recibir StreamingBlock objects del parser
- Enrutar bloques a métodos de display apropiados
- Ejecutar herramientas cuando se completan bloques TOOL_CALL
- Coordinar con streaming_display para visualización
- Mantener estado de herramientas pendientes
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from streaming_response_parser import StreamingBlock, BlockType
from tool_executor import ToolExecutor, ToolResult, ConsolidatedResults


@dataclass
class ToolExecution:
    """Representa la ejecución de una herramienta"""
    tool_name: str
    xml_content: str
    result: Optional[ToolResult] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class StreamingResponseHandler:
    """
    Maneja el procesamiento de bloques según su tipo
    Coordina entre parser, tool executor y display
    """
    
    def __init__(self, tool_executor: ToolExecutor, display=None):
        """
        Inicializa el handler de streaming
        
        Args:
            tool_executor: Ejecutor de herramientas
            display: Display de streaming (opcional, se puede inyectar después)
        """
        self.logger = logging.getLogger(__name__)
        self.tool_executor = tool_executor
        self.display = display
        
        # Estado interno
        self.pending_tools: List[ToolExecution] = []
        self.completed_tools: List[ToolExecution] = []
        self.current_section: Optional[str] = None
        
        # Acumuladores de contenido
        self.thinking_buffer = ""
        self.answer_buffer = ""
        
        self.logger.debug("StreamingResponseHandler inicializado")
    
    def set_display(self, display):
        """
        Establece el display de streaming
        
        Args:
            display: Display de streaming
        """
        self.display = display
        self.logger.debug("Display configurado en handler")
    
    def handle_block(self, block: StreamingBlock):
        """
        Procesa un bloque según su tipo
        
        Args:
            block: Bloque a procesar
        """
        self.logger.debug(f"Procesando bloque: {block.block_type.value}, "
                         f"completo: {block.is_complete}, "
                         f"contenido: {len(block.content)} caracteres")
        
        if block.block_type == BlockType.THINKING:
            self.handle_thinking_block(block)
        
        elif block.block_type == BlockType.TOOL_CALL:
            self.handle_tool_block(block)
        
        elif block.block_type == BlockType.PRESENT_ANSWER:
            self.handle_answer_block(block)
        
        elif block.block_type == BlockType.PLAIN_TEXT:
            self.handle_plain_text(block)
        
        else:
            self.logger.warning(f"Tipo de bloque desconocido: {block.block_type}")
    
    def handle_thinking_block(self, block: StreamingBlock):
        """
        Maneja bloques de thinking
        Muestra el contenido en streaming mientras se genera
        
        Args:
            block: Bloque de thinking
        """
        # Detectar si es el marcador de inicio
        if hasattr(block, 'is_start_marker') and block.is_start_marker:
            # Mostrar encabezado de sección
            if self.display:
                # Cambiar sección en display
                self.display.current_section = None  # Forzar nuevo encabezado
            self.logger.debug("Inicio de bloque thinking detectado")
            return
        
        # Detectar si es contenido incremental
        if hasattr(block, 'is_incremental') and block.is_incremental:
            # Mostrar contenido incremental inmediatamente
            if self.display:
                self.display.stream_thinking(block.content)
            else:
                print(block.content, end='', flush=True)
            
            self.thinking_buffer += block.content
            self.logger.debug(f"Thinking incremental: {len(block.content)} caracteres")
            return
        
        # Bloque completo (final)
        if block.is_complete:
            # Si hay contenido final, mostrarlo
            if block.content:
                if self.display:
                    self.display.stream_thinking(block.content)
                else:
                    print(block.content, flush=True)
            
            # Limpiar buffer
            self.thinking_buffer = ""
            self.logger.debug(f"Thinking completado")
    
    def handle_tool_block(self, block: StreamingBlock):
        """
        Maneja bloques de herramientas
        Muestra indicador y ejecuta la herramienta cuando está completa
        
        Args:
            block: Bloque de herramienta
        """
        if not block.is_complete:
            # Bloque incompleto, solo registrar
            self.logger.debug(f"Herramienta incompleta: {block.tool_name}")
            return
        
        # Bloque completo - ejecutar herramienta
        tool_name = block.tool_name
        xml_content = block.content
        
        self.logger.info(f"Ejecutando herramienta: {tool_name}")
        
        # Mostrar indicador
        if self.display:
            self.display.show_tool_indicator(tool_name)
        else:
            # Fallback si no hay display
            print(f"\n🔧 Ejecutando: {tool_name}")
        
        # Crear ejecución de herramienta
        tool_execution = ToolExecution(
            tool_name=tool_name,
            xml_content=xml_content
        )
        
        # Ejecutar herramienta
        try:
            # Parsear el XML completo de la herramienta
            full_xml = f"<{tool_name}>{xml_content}</{tool_name}>"
            
            # Usar el tool_executor para parsear y ejecutar
            tool_calls = self.tool_executor.parse_tool_calls_from_xml(full_xml)
            
            if tool_calls:
                # Ejecutar la primera (y debería ser única) herramienta
                tool_call = tool_calls[0]
                result = self.tool_executor.execute_tool(
                    tool_call['tool_type'],
                    tool_call['params']
                )
                
                tool_execution.result = result
                self.completed_tools.append(tool_execution)
                
                # Mostrar resultado si el display lo soporta
                if self.display and hasattr(self.display, 'show_tool_result'):
                    self.display.show_tool_result(tool_name, result)
                
                self.logger.info(f"Herramienta {tool_name} ejecutada: "
                               f"{'exitosa' if result.success else 'fallida'}")
            else:
                self.logger.warning(f"No se pudo parsear herramienta: {tool_name}")
        
        except Exception as e:
            self.logger.error(f"Error ejecutando herramienta {tool_name}: {str(e)}")
            
            # Mostrar error si el display lo soporta
            if self.display and hasattr(self.display, 'show_error'):
                self.display.show_error(f"Error en {tool_name}: {str(e)}")
    
    def handle_answer_block(self, block: StreamingBlock):
        """
        Maneja bloques de respuesta final
        Muestra el contenido en streaming mientras se genera
        
        Args:
            block: Bloque de respuesta
        """
        # Detectar si es el marcador de inicio
        if hasattr(block, 'is_start_marker') and block.is_start_marker:
            # Mostrar encabezado de sección
            if self.display:
                # Cambiar sección en display
                self.display.current_section = None  # Forzar nuevo encabezado
            self.logger.debug("Inicio de bloque answer detectado")
            return
        
        # Detectar si es contenido incremental
        if hasattr(block, 'is_incremental') and block.is_incremental:
            # Mostrar contenido incremental inmediatamente
            if self.display:
                self.display.stream_answer(block.content)
            else:
                print(block.content, end='', flush=True)
            
            self.answer_buffer += block.content
            self.logger.debug(f"Answer incremental: {len(block.content)} caracteres")
            return
        
        # Bloque completo (final)
        if block.is_complete:
            # Si hay contenido final, mostrarlo
            if block.content:
                if self.display:
                    self.display.stream_answer(block.content)
                else:
                    print(block.content, flush=True)
            
            # Limpiar buffer
            self.answer_buffer = ""
            self.logger.debug(f"Answer completado")
    
    def handle_plain_text(self, block: StreamingBlock):
        """
        Maneja bloques de texto plano
        Texto que no está dentro de ningún tag especial
        
        Args:
            block: Bloque de texto plano
        """
        content = block.content
        
        if self.display and hasattr(self.display, 'stream_plain_text'):
            self.display.stream_plain_text(content)
        else:
            # Fallback si no hay display
            print(content, end='', flush=True)
        
        self.logger.debug(f"Texto plano: {len(content)} caracteres")
    
    def get_tool_results(self) -> List[ToolResult]:
        """
        Obtiene los resultados de todas las herramientas ejecutadas
        
        Returns:
            Lista de resultados de herramientas
        """
        return [exec.result for exec in self.completed_tools if exec.result]
    
    def get_consolidated_results(self) -> Optional[ConsolidatedResults]:
        """
        Obtiene resultados consolidados de todas las herramientas
        
        Returns:
            ConsolidatedResults o None si no hay herramientas
        """
        results = self.get_tool_results()
        
        if not results:
            return None
        
        # Usar el método de consolidación del tool_executor
        consolidated_data = self.tool_executor._consolidate_results(results)
        
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        total_time = sum(r.execution_time_ms for r in results)
        
        return ConsolidatedResults(
            total_tools_executed=len(results),
            successful_executions=successful,
            failed_executions=failed,
            results=results,
            consolidated_data=consolidated_data,
            execution_time_ms=total_time
        )
    
    def get_execution_summary(self) -> str:
        """
        Genera un resumen de la ejecución
        
        Returns:
            String con resumen formateado
        """
        if not self.completed_tools:
            return "No se ejecutaron herramientas"
        
        lines = [
            "\n📊 Resumen de Ejecución:",
            f"  • Total de herramientas: {len(self.completed_tools)}"
        ]
        
        successful = sum(1 for t in self.completed_tools if t.result and t.result.success)
        failed = len(self.completed_tools) - successful
        
        lines.append(f"  • Exitosas: {successful}")
        lines.append(f"  • Fallidas: {failed}")
        
        # Detalles por herramienta
        lines.append("\n  Detalles:")
        for i, tool_exec in enumerate(self.completed_tools, 1):
            status = "✓" if tool_exec.result and tool_exec.result.success else "✗"
            time_ms = tool_exec.result.execution_time_ms if tool_exec.result else 0
            lines.append(f"    {i}. {status} {tool_exec.tool_name} ({time_ms:.2f}ms)")
        
        return "\n".join(lines)
    
    def reset(self):
        """Reinicia el estado del handler"""
        self.pending_tools.clear()
        self.completed_tools.clear()
        self.current_section = None
        self.thinking_buffer = ""
        self.answer_buffer = ""
        self.logger.debug("Handler reiniciado")
    
    def finalize(self) -> Dict[str, Any]:
        """
        Finaliza el procesamiento y retorna información de estado
        
        Returns:
            Diccionario con información de estado final
        """
        # Finalizar display si existe
        if self.display:
            self.display.finalize()
        
        # Recopilar información final
        state = {
            'total_tools': len(self.completed_tools),
            'successful_tools': sum(1 for t in self.completed_tools 
                                   if t.result and t.result.success),
            'failed_tools': sum(1 for t in self.completed_tools 
                               if t.result and not t.result.success),
            'tool_results': self.get_tool_results(),
            'consolidated_results': self.get_consolidated_results(),
            'thinking_buffer': self.thinking_buffer,
            'answer_buffer': self.answer_buffer
        }
        
        self.logger.info(f"Handler finalizado: {state['total_tools']} herramientas ejecutadas")
        
        return state


def main():
    """Función principal para testing"""
    import logging
    from streaming_response_parser import StreamingResponseParser
    
    # Configurar logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear componentes
    tool_executor = ToolExecutor()
    handler = StreamingResponseHandler(tool_executor)
    
    # Simular respuesta del LLM
    response = """
    <thinking>
    Voy a buscar información sobre autenticación.
    Primero haré una búsqueda semántica.
    </thinking>
    
    <tool_semantic_search>
    <query>autenticación usuarios login</query>
    <top_k>5</top_k>
    </tool_semantic_search>
    
    <present_answer>
    Basándome en los resultados, la autenticación se gestiona
    mediante tokens JWT en el archivo auth.js
    </present_answer>
    """
    
    # Crear parser y procesar
    parser = StreamingResponseParser()
    
    print("Procesando respuesta en streaming...")
    print("=" * 64)
    
    # Simular tokens
    tokens = [response[i:i+20] for i in range(0, len(response), 20)]
    
    for token in tokens:
        blocks = parser.feed_token(token)
        
        for block in blocks:
            handler.handle_block(block)
    
    # Finalizar
    remaining = parser.finalize()
    for block in remaining:
        handler.handle_block(block)
    
    # Mostrar resumen
    print("\n" + "=" * 64)
    print(handler.get_execution_summary())
    
    # Finalizar handler
    state = handler.finalize()
    print(f"\nEstado final: {state['total_tools']} herramientas ejecutadas")


if __name__ == "__main__":
    main()
