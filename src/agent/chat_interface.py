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
from color_utils import (
    user_text, llm_response, tool_result, info, warning, error, success,
    header, dim_text, format_user_input_section, format_metrics_section
)


class ChatInterface:
    """Interfaz de chat para interacción con el agente"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Inicializa la interfaz de chat
        
        Args:
            config_path: Ruta al archivo de configuración
        """
        self.logger = logging.getLogger(__name__)
        
        # Inicializar manejador de requests (sin pasar system_prompt, se cargará desde configuración)
        self.request_handler = RequestHandler(config_path=config_path)
        
        # Inicializar logger de conversaciones
        self.conversation_logger = ConversationLogger(logs_dir="logs")
        
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
        welcome = """
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║        🤖 AGENTE IA DE CONSULTA - BASE DE CONOCIMIENTO DARWIN  ║
║                                                                ║
║  Bienvenido al asistente especializado en consultas sobre      ║
║  la base de conocimiento Darwin.                              ║
║                                                                ║
║  Puedo ayudarte con:                                          ║
║  • Consultas funcionales sobre el sistema                     ║
║  • Consultas técnicas sobre implementación                    ║
║  • Búsquedas en la documentación                              ║
║                                                                ║
║  Escribe 'salir' para terminar la sesión                      ║
║  Escribe 'historial' para ver el historial de conversación    ║
║  Escribe 'estadísticas' para ver estadísticas de la sesión    ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
"""
        print(welcome)
    
    def _display_goodbye_message(self) -> None:
        """Muestra mensaje de despedida"""
        goodbye = """
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║  ¡Gracias por usar el Agente IA de Consulta Darwin!          ║
║                                                                ║
║  Sesión finalizada correctamente.                             ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
"""
        print(goodbye)
    
    def process_user_input(self, user_input: str) -> Optional[RequestResult]:
        """
        Procesa input del usuario
        
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
                    
                    # Procesar input
                    result = self.process_user_input(user_input)
                    
                    # No mostrar nada aquí, request_handler ya muestra todas las respuestas
                
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
