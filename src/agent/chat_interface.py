"""
Chat Interface Module - Interfaz de usuario para interacción conversacional

Responsabilidad: Interfaz de usuario para interacción conversacional
- Captura de consultas del usuario
- Visualización de respuestas formateadas
- Manejo de historial de conversación
- Soporte futuro para streaming progresivo
"""

import logging
import sys
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import traceback

from request_handler import RequestHandler, RequestResult, RequestState
from conversation_logger import ConversationLogger
from llm_communication import LLMCommunication, LLMRequest
from tool_executor import ToolExecutor
from streaming_state_machine import StreamingStateMachine
from streaming_display import StreamingDisplay
from config_manager import ConfigManager
from color_utils import (
    user_text, llm_response, tool_result, info, warning, error, success,
    header, dim_text, format_user_input_section, format_metrics_section
)


class ChatInterface:
    """Interfaz de chat para interacción con el agente"""
    
    def __init__(self, config_path: str = "config/config_darwin.yaml", app_name: str = "Darwin", enable_streaming: bool = True):
        """
        Inicializa la interfaz de chat
        
        Args:
            config_path: Ruta al archivo de configuración
            app_name: Nombre de la aplicación (Darwin, SAP, MuleSoft, etc.)
            enable_streaming: Si debe usar streaming para respuestas del LLM
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path
        self.app_name = app_name
        self.enable_streaming = enable_streaming
        
        # Cargar configuración
        self.config_manager = ConfigManager(config_path=config_path)
        
        # Inicializar manejador de requests (sin pasar system_prompt, se cargará desde configuración)
        self.request_handler = RequestHandler(config_path=config_path)
        
        # Inicializar logger de conversaciones
        self.conversation_logger = ConversationLogger(logs_dir="logs")
        
        # Inicializar componentes de streaming
        if enable_streaming:
            self.llm_comm = LLMCommunication(config_path=config_path)
            self.tool_executor = ToolExecutor(config_path=config_path)
            self.logger.info("Streaming habilitado")
        
        # Sesión actual
        self.session_id = str(uuid.uuid4())
        self.is_active = False
        
        self.logger.info(f"ChatInterface inicializado con sesión {self.session_id}")
        self.logger.info(f"Logs de conversación se guardarán en: logs/")
    
    def start(self) -> None:
        """Inicia la interfaz de chat"""
        self.is_active = True
        self._display_welcome_message()
    
    def stop(self) -> None:
        """Detiene la interfaz de chat"""
        self.is_active = False
        self.request_handler.end_session(self.session_id)
        self._display_goodbye_message()
    
    def _display_welcome_message(self) -> None:
        """Muestra mensaje de bienvenida"""
        welcome = f"""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║        AGENTE IA DE CONSULTA - {self.app_name.upper():^30}     ║
║                                                                ║
║  Bienvenido al asistente especializado en consultas sobre      ║
║  la base de conocimiento {self.app_name:<35} ║
║                                                                ║
║  Puedo ayudarte con:                                           ║
║  • Consultas funcionales sobre el sistema                      ║
║  • Consultas técnicas sobre implementación                     ║
║  • Búsquedas en la documentación                               ║
║                                                                ║
║  Escribe 'salir' para terminar la sesión                       ║
║  Escribe 'historial' para ver el historial de conversación     ║
║  Escribe 'estadísticas' para ver estadísticas de la sesión     ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
"""
        print(welcome)
    
    def _display_goodbye_message(self) -> None:
        """Muestra mensaje de despedida"""
        goodbye = f"""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║  ¡Gracias por usar el Agente IA de Consulta {self.app_name}!{' '*(18-len(self.app_name))}║
║                                                                ║
║  Sesión finalizada correctamente.                              ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
"""
        print(goodbye)
    
    def _format_tool_results_for_llm(self, tool_results, original_question: str = None) -> str:
        """
        Formatea los resultados de las herramientas para enviarlos al LLM
        
        Args:
            tool_results: Lista de ToolResult
            original_question: Pregunta original del usuario
            
        Returns:
            String formateado con los resultados
        """
        message = "[RESULTADOS DE TUS HERRAMIENTAS]\n\n"
        
        if original_question:
            message += f"RECORDATORIO - Pregunta original del usuario: \"{original_question}\"\n\n"
        
        message += "IMPORTANTE: Analiza estos resultados y presenta tu respuesta al usuario usando <present_answer>.\n"
        message += "NO solicites más herramientas a menos que la información sea claramente insuficiente.\n\n"
        
        for result in tool_results:
            tool_name = result.tool_type.value if hasattr(result.tool_type, 'value') else str(result.tool_type)
            
            if result.success and result.data:
                # Formatear según el tipo de herramienta
                if tool_name in ["semantic_search", "lexical_search", "regex_search"]:
                    message += self._format_search_results(result.data)
                elif tool_name == "get_file_content":
                    message += self._format_file_content(result.data)
                else:
                    message += f"{str(result.data)}\n\n"
            elif not result.success:
                message += f"Error en {tool_name}: {result.error}\n\n"
        
        return message
    
    def _format_search_results(self, results: Dict[str, Any]) -> str:
        """Formatea resultados de búsqueda de forma resumida"""
        formatted = ""
        
        if 'fragments' in results and results['fragments']:
            total_fragments = len(results['fragments'])
            formatted += f"Se encontraron {total_fragments} fragmentos relevantes.\n\n"
            formatted += "**Información resumida de los fragmentos:**\n\n"
            
            # Agrupar por archivo
            files_dict = {}
            for fragment in results['fragments']:
                file_name = fragment.get('file_name', 'Desconocido')
                if file_name not in files_dict:
                    files_dict[file_name] = {
                        'count': 0,
                        'max_score': 0,
                        'content_preview': ''
                    }
                files_dict[file_name]['count'] += 1
                score = fragment.get('score', 0)
                if score > files_dict[file_name]['max_score']:
                    files_dict[file_name]['max_score'] = score
                    content = fragment.get('content', '')
                    files_dict[file_name]['content_preview'] = content[:500] if content else ''
            
            # Formatear resumen por archivo
            for i, (file_name, info) in enumerate(sorted(files_dict.items(), key=lambda x: x[1]['max_score'], reverse=True), 1):
                formatted += f"{i}. **{file_name}**\n"
                formatted += f"   - Fragmentos encontrados: {info['count']}\n"
                formatted += f"   - Relevancia máxima: {info['max_score']:.4f}\n"
                if info['content_preview']:
                    formatted += f"   - Vista previa: {info['content_preview'][:200]}...\n"
                formatted += "\n"
        else:
            formatted += "No se encontraron resultados.\n"
        
        return formatted
    
    def _format_file_content(self, results: Dict[str, Any]) -> str:
        """Formatea contenido de archivo completo"""
        formatted = ""
        
        if 'content' in results:
            content = results['content']
            file_name = results.get('file_name', 'archivo')
            
            formatted += f"Archivo: {file_name}\n"
            formatted += f"Tamaño del contenido: {len(content)} caracteres\n\n"
            formatted += f"Contenido completo del archivo:\n\n"
            formatted += f"```\n{content}\n```\n"
            
            if 'metadata' in results:
                formatted += f"\n**Metadata del archivo:**\n"
                for key, value in results['metadata'].items():
                    formatted += f"- {key}: {value}\n"
        
        return formatted
    
    def process_user_input_streaming(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        Procesa input del usuario con streaming habilitado e iteración de herramientas
        
        Args:
            user_input: Input del usuario
            
        Returns:
            Diccionario con resultado del procesamiento o None si es comando especial
        """
        # Procesar comandos especiales
        if user_input.lower() == 'salir':
            self.stop()
            return None
        
        if user_input.lower() == 'historial':
            self._display_conversation_history()
            return None
        
        if user_input.lower() == 'estadísticas':
            self._display_conversation_stats()
            return None
        
        if user_input.lower() == 'limpiar':
            self._clear_screen()
            return None
        
        if not user_input.strip():
            print(warning("⚠️  Por favor, ingresa una consulta válida.\n"))
            return None
        
        # Procesar consulta con streaming
        self.logger.debug(f"Procesando input con streaming: {user_input[:50]}...")
        
        try:
            import time
            start_time = time.time()
            
            # Agregar turno del usuario al historial
            self.llm_comm.conversation_manager.add_user_turn(
                session_id=self.session_id,
                message=user_input,
                tokens=len(user_input.split())
            )
            
            # Variables para el ciclo iterativo
            max_iterations = self.config_manager.get('agent.max_tool_iterations', 5)
            iteration = 0
            all_tool_results = []
            total_llm_time = 0
            total_tools_time = 0
            total_tokens_input = 0
            total_tokens_output = 0
            
            # Mensaje actual para enviar al LLM (inicialmente la pregunta del usuario)
            current_message = user_input
            
            # CICLO ITERATIVO: Continuar mientras haya herramientas que ejecutar
            while iteration < max_iterations:
                iteration += 1
                self.logger.info(f"🔄 Iteración {iteration}/{max_iterations}")
                
                # Crear componentes de streaming para esta iteración con máquina de estados
                display = StreamingDisplay(enable_colors=True)
                state_machine = StreamingStateMachine(display)
                
                # Callback para procesar tokens con la máquina de estados
                def token_callback(token: str):
                    state_machine.feed_token(token)
                
                # Obtener historial conversacional (sin el último turno de usuario)
                conversation_context = self.llm_comm.conversation_manager.get_conversation_context(self.session_id)
                conversation_history = self.llm_comm._build_conversation_history(conversation_context)
                if conversation_history and conversation_history[-1]['role'] == 'user':
                    conversation_history = conversation_history[:-1]
                
                # Crear request
                llm_request = LLMRequest(
                    session_id=self.session_id,
                    system_prompt=self.llm_comm.system_prompt,
                    user_input=current_message,
                    conversation_history=conversation_history,
                    max_tokens=self.llm_comm.max_tokens,
                    temperature=self.llm_comm.temperature,
                    use_cache=True
                )
                
                # Enviar request con streaming
                llm_start = time.time()
                response = self.llm_comm.send_request_streaming(
                    llm_request=llm_request,
                    token_callback=token_callback
                )
                llm_time = (time.time() - llm_start) * 1000
                total_llm_time += llm_time
                
                # Finalizar máquina de estados (libera buffer pendiente)
                accumulated_text = state_machine.finalize()
                
                # Parsear el texto acumulado para extraer y ejecutar herramientas
                # Usar el método del tool_executor que parsea XML directamente
                tool_results = []
                try:
                    tool_calls = self.tool_executor.parse_tool_calls_from_xml(accumulated_text)
                    
                    if tool_calls:
                        self.logger.info(f"🔧 Ejecutando {len(tool_calls)} herramientas...")
                        for tool_call in tool_calls:
                            try:
                                result = self.tool_executor.execute_tool(
                                    tool_call['tool_type'],
                                    tool_call['params']
                                )
                                tool_results.append(result)
                                
                                # Mostrar resultado de herramienta
                                if result.success:
                                    print(success(f"  ✅ {result.tool_type.value}: {result.execution_time_ms:.0f}ms"))
                                else:
                                    print(error(f"  ❌ {result.tool_type.value}: {result.error}"))
                            except Exception as e:
                                self.logger.error(f"Error ejecutando herramienta: {e}")
                                print(error(f"  ❌ Error ejecutando herramienta: {str(e)}"))
                except Exception as e:
                    self.logger.error(f"Error parseando herramientas: {e}")
                
                # Actualizar historial con respuesta del asistente
                tools_used = [result.tool_type.value if hasattr(result.tool_type, 'value') else str(result.tool_type) 
                             for result in tool_results]
                self.llm_comm.conversation_manager.add_assistant_turn(
                    session_id=self.session_id,
                    response=response.content,
                    tools_used=tools_used,
                    tokens=response.usage.get('output_tokens', 0)
                )
                
                # Acumular métricas
                total_tokens_input += response.usage.get('input_tokens', 0)
                total_tokens_output += response.usage.get('output_tokens', 0)
                
                if tool_results:
                    all_tool_results.extend(tool_results)
                    total_tools_time += sum(r.execution_time_ms for r in tool_results)
                    
                    self.logger.info(f"✅ Iteración {iteration}: {len(tool_results)} herramientas ejecutadas")
                    
                    # Formatear resultados para enviar al LLM
                    tool_results_message = self._format_tool_results_for_llm(
                        tool_results,
                        original_question=user_input
                    )
                    
                    # Mostrar info al usuario
                    print(info(f"\n  ℹ️  Resultados enviados al LLM ({len(tool_results_message)} caracteres)\n"))
                    
                    # Preparar mensaje para siguiente iteración
                    current_message = tool_results_message
                    
                    # Agregar turno del usuario (resultados de herramientas) al historial
                    self.llm_comm.conversation_manager.add_user_turn(
                        session_id=self.session_id,
                        message=tool_results_message,
                        tokens=len(tool_results_message.split())
                    )
                else:
                    # No hay más herramientas, salir del ciclo
                    self.logger.info(f"✅ No hay más herramientas en iteración {iteration}. Finalizando.")
                    break
            
            # Verificar si se alcanzó el máximo de iteraciones
            if iteration >= max_iterations:
                self.logger.warning(f"⚠️  Alcanzado máximo de iteraciones ({max_iterations})")
            
            execution_time = (time.time() - start_time) * 1000
            
            # Registrar en log
            try:
                metrics = {
                    "total_time_ms": execution_time,
                    "llm_time_ms": total_llm_time,
                    "tools_time_ms": total_tools_time,
                    "tokens_input": total_tokens_input,
                    "tokens_output": total_tokens_output,
                    "cache_tokens_saved": 0,
                    "tools_executed": len(all_tool_results),
                    "tools_successful": sum(1 for r in all_tool_results if r.success),
                    "iterations": iteration
                }
                
                self.conversation_logger.log_conversation_turn(
                    session_id=self.session_id,
                    user_input=user_input,
                    llm_response=response.content,
                    metrics=metrics
                )
                
                self.logger.info(f"✅ Turno registrado en logs/")
            
            except Exception as log_error:
                self.logger.warning(f"Error registrando turno en log: {log_error}")
            
            return {
                'response': response,
                'tool_results': all_tool_results,
                'execution_time_ms': execution_time,
                'iterations': iteration
            }
        
        except Exception as e:
            self.logger.error(f"Error procesando input con streaming: {str(e)}")
            
            # Registrar error en log
            try:
                self.conversation_logger.log_error(
                    session_id=self.session_id,
                    error_message=str(e),
                    error_type=type(e).__name__,
                    user_input=user_input,
                    traceback_info=traceback.format_exc()
                )
            except Exception as log_error:
                self.logger.warning(f"Error registrando error en log: {log_error}")
            
            print(error(f"❌ Error procesando tu consulta: {str(e)}\n"))
            return None
    
    def process_user_input(self, user_input: str) -> Optional[RequestResult]:
        """
        Procesa input del usuario (modo batch, sin streaming)
        
        Args:
            user_input: Input del usuario
            
        Returns:
            RequestResult o None si es comando especial
        """
        # Procesar comandos especiales
        if user_input.lower() == 'salir':
            self.stop()
            return None
        
        if user_input.lower() == 'historial':
            self._display_conversation_history()
            return None
        
        if user_input.lower() == 'estadísticas':
            self._display_conversation_stats()
            return None
        
        if user_input.lower() == 'limpiar':
            self._clear_screen()
            return None
        
        if not user_input.strip():
            print(warning("⚠️  Por favor, ingresa una consulta válida.\n"))
            return None
        
        # Procesar consulta normal
        self.logger.debug(f"Procesando input del usuario: {user_input[:50]}...")
        
        try:
            result = self.request_handler.process_request(
                session_id=self.session_id,
                user_input=user_input
            )
            
            # Registrar petición y respuesta en log
            if result and result.state != RequestState.ERROR:
                try:
                    llm_response = result.formatted_response.filtered_content if result.formatted_response else "Sin respuesta"
                    metrics = {
                        "total_time_ms": result.metrics.total_time_ms,
                        "llm_time_ms": result.metrics.llm_time_ms,
                        "tools_time_ms": result.metrics.tools_time_ms,
                        "tokens_input": result.metrics.tokens_input,
                        "tokens_output": result.metrics.tokens_output,
                        "cache_tokens_saved": result.metrics.cache_tokens_saved,
                        "tools_executed": result.metrics.tools_executed,
                        "tools_successful": result.metrics.tools_successful
                    }
                    
                    self.conversation_logger.log_conversation_turn(
                        session_id=self.session_id,
                        user_input=user_input,
                        llm_response=llm_response,
                        metrics=metrics
                    )
                    
                    self.logger.info(f"✅ Turno registrado en logs/")
                
                except Exception as log_error:
                    self.logger.warning(f"Error registrando turno en log: {log_error}")
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error procesando input: {str(e)}")
            
            # Registrar error en log
            try:
                self.conversation_logger.log_error(
                    session_id=self.session_id,
                    error_message=str(e),
                    error_type=type(e).__name__,
                    user_input=user_input,
                    traceback_info=traceback.format_exc()
                )
            except Exception as log_error:
                self.logger.warning(f"Error registrando error en log: {log_error}")
            
            print(error(f"❌ Error procesando tu consulta: {str(e)}\n"))
            return None
    
    def display_result(self, result: RequestResult) -> None:
        """
        Muestra el resultado de un request (solo respuesta del LLM en pantalla)
        
        Args:
            result: Resultado del procesamiento
        """
        if result.state == RequestState.ERROR:
            print(error("❌ Error procesando la consulta. Por favor, intenta de nuevo.\n"))
            return
        
        # Mostrar respuesta formateada con color verde (respuesta del LLM)
        if result.formatted_response:
            print(llm_response(result.formatted_response.filtered_content))
            print()  # Línea en blanco
    
    
    def _display_conversation_history(self) -> None:
        """Muestra el historial de conversación"""
        history = self.request_handler.get_conversation_history(self.session_id)
        
        print("\n" + "="*64)
        print("📜 HISTORIAL DE CONVERSACIÓN:")
        print("="*64 + "\n")
        
        if history.strip():
            print(history)
        else:
            print("No hay historial de conversación aún.\n")
        
        print("="*64 + "\n")
    
    def _display_conversation_stats(self) -> None:
        """Muestra estadísticas de la conversación"""
        stats = self.request_handler.get_conversation_stats(self.session_id)
        
        print("\n" + "="*64)
        print("📊 ESTADÍSTICAS DE LA SESIÓN:")
        print("="*64 + "\n")
        
        for key, value in stats.items():
            print(f"  • {key}: {value}")
        
        print("\n" + "="*64 + "\n")
    
    def _clear_screen(self) -> None:
        """Limpia la pantalla"""
        import os
        os.system('clear' if os.name == 'posix' else 'cls')
        self._display_welcome_message()
    
    def run_interactive(self) -> None:
        """Ejecuta la interfaz en modo interactivo"""
        self.start()
        
        try:
            while self.is_active:
                try:
                    # Capturar input del usuario
                    user_input = input(user_text("\n👤 Tú: ")).strip()
                    
                    if not user_input:
                        continue
                    
                    # Procesar input con o sin streaming
                    if self.enable_streaming:
                        result = self.process_user_input_streaming(user_input)
                    else:
                        result = self.process_user_input(user_input)
                        # Mostrar resultado si no es streaming
                        if result:
                            self.display_result(result)
                
                except KeyboardInterrupt:
                    print(warning("\n\n⚠️  Sesión interrumpida por el usuario."))
                    self.stop()
                    break
                
                except EOFError:
                    print(warning("\n\n⚠️  Fin de entrada detectado."))
                    self.stop()
                    break
        
        except Exception as e:
            self.logger.error(f"Error en modo interactivo: {str(e)}", exc_info=True)
            print(error(f"❌ Error: {str(e)}"))
    
    def run_batch(self, queries: list) -> None:
        """
        Ejecuta la interfaz en modo batch
        
        Args:
            queries: Lista de consultas a procesar
        """
        self.start()
        
        for i, query in enumerate(queries, 1):
            print(f"\n{'='*64}")
            print(f"📝 Consulta {i}/{len(queries)}: {query}")
            print('='*64)
            
            result = self.process_user_input(query)
            
            if result:
                self.display_result(result)
        
        self.stop()


def main():
    """Función principal para testing"""
    import logging
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # System prompt
    system_prompt = """Eres un asistente especializado en consultas sobre la base de conocimiento Darwin.
Tu objetivo es responder preguntas sobre aspectos funcionales y técnicos del sistema.
Cuando necesites información, solicita el uso de herramientas de búsqueda mediante XML.
Siempre proporciona respuestas claras, precisas y bien estructuradas."""
    
    # Crear interfaz de chat
    chat = ChatInterface(system_prompt=system_prompt)
    
    # Ejecutar en modo interactivo
    chat.run_interactive()


if __name__ == "__main__":
    main()
