"""
Request Handler/Orchestrator - Coordinación central del flujo de procesamiento

Responsabilidad: Orquestar el flujo completo de procesamiento
- Recepción de consultas del chat interface
- Coordinación de LLM communication
- Parsing de respuestas XML del LLM
- Coordinación de ejecución de herramientas
- Gestión de estado conversacional
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from config_manager import ConfigManager
from conversation_manager import ConversationManager
from llm_communication import LLMCommunication, LLMResponse
from tool_executor import ToolExecutor, ConsolidatedResults
from response_formatter import ResponseFormatter, FormattedResponse
from color_utils import (
    tool_result, info, warning, error, success, header, dim_text
)


class RequestState(Enum):
    """Estados posibles de un request"""
    PENDING = "pending"
    PROCESSING = "processing"
    LLM_RESPONSE_RECEIVED = "llm_response_received"
    TOOLS_EXECUTING = "tools_executing"
    FORMATTING = "formatting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ProcessingMetrics:
    """Métricas de procesamiento de un request"""
    total_time_ms: float
    llm_time_ms: float
    tools_time_ms: float
    formatting_time_ms: float
    tokens_input: int
    tokens_output: int
    tools_executed: int
    tools_successful: int
    tools_failed: int
    cache_tokens_saved: int


@dataclass
class RequestResult:
    """Resultado completo de un request"""
    session_id: str
    user_input: str
    llm_response: LLMResponse
    tool_results: Optional[ConsolidatedResults]
    formatted_response: FormattedResponse
    metrics: ProcessingMetrics
    state: RequestState
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class RequestHandler:
    """Orquestador central del flujo de procesamiento"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Inicializa el manejador de requests
        
        Args:
            config_path: Ruta al archivo de configuración
        """
        self.config = ConfigManager(config_path)
        self.logger = logging.getLogger(__name__)
        
        # Inicializar componentes
        conversation_config = self.config.get_section('conversation')
        self.conversation_manager = ConversationManager(conversation_config)
        self.llm_communication = LLMCommunication(config_path)
        self.tool_executor = ToolExecutor(config_path)
        self.response_formatter = ResponseFormatter()
        
        # Configuración
        self.max_tool_iterations = self.config.get('agent.max_tool_iterations', 3)
        self.enable_tool_execution = self.config.get('agent.enable_tool_execution', True)
        
        self.logger.info("RequestHandler inicializado correctamente")
        self.logger.info("System prompt se cargará desde LLMCommunication (config/system_prompt.yaml)")
    
    def _format_tool_results_for_llm(self, tool_results: ConsolidatedResults) -> str:
        """
        Formatea los resultados de las herramientas para enviarlos al LLM
        
        Args:
            tool_results: Resultados consolidados de las herramientas
            
        Returns:
            String formateado con los resultados
        """
        message = "## Resultados de las Herramientas Ejecutadas\n\n"
        
        for result in tool_results.results:
            tool_name = result.tool_type.value  # Obtener el valor del Enum
            message += f"### Herramienta: {tool_name}\n"
            message += f"- Estado: {'✅ Exitosa' if result.success else '❌ Fallida'}\n"
            message += f"- Tiempo de ejecución: {result.execution_time_ms:.2f}ms\n"
            
            if result.success and result.data:  # Usar 'data' en lugar de 'result'
                message += f"\n**Resultados:**\n"
                
                # Formatear según el tipo de herramienta
                if tool_name == "semantic_search":
                    message += self._format_search_results(result.data)
                elif tool_name == "lexical_search":
                    message += self._format_search_results(result.data)
                elif tool_name == "regex_search":
                    message += self._format_search_results(result.data)
                elif tool_name == "get_file_content":
                    message += self._format_file_content(result.data)
                else:
                    message += f"```\n{str(result.data)}\n```\n"
            elif not result.success:
                message += f"\n**Error:** {result.error}\n"  # Usar 'error' en lugar de 'error_message'
            
            message += "\n---\n\n"
        
        message += f"\n**Resumen:**\n"
        message += f"- Total de herramientas ejecutadas: {tool_results.total_tools_executed}\n"
        message += f"- Exitosas: {tool_results.successful_executions}\n"
        message += f"- Fallidas: {tool_results.failed_executions}\n"
        message += f"\nPor favor, analiza estos resultados y proporciona una respuesta completa y útil al usuario.\n"
        
        return message
    
    def _format_search_results(self, results: Dict[str, Any]) -> str:
        """Formatea resultados de búsqueda con TODA la información de OpenSearch"""
        formatted = ""
        
        if 'fragments' in results and results['fragments']:
            formatted += f"Se encontraron {len(results['fragments'])} fragmentos relevantes:\n\n"
            
            # INCLUIR TODOS LOS FRAGMENTOS (no limitar a 5)
            for i, fragment in enumerate(results['fragments'], 1):
                formatted += f"{i}. **{fragment.get('file_name', 'Desconocido')}**\n"
                
                # Incluir score de relevancia
                if 'score' in fragment:
                    formatted += f"   - Relevancia: {fragment['score']:.4f}\n"
                
                # Incluir file_path si existe
                if 'file_path' in fragment:
                    formatted += f"   - Ruta: {fragment['file_path']}\n"
                
                # Incluir summary si existe
                if 'summary' in fragment:
                    formatted += f"   - Resumen: {fragment['summary']}\n"
                
                # INCLUIR CONTENIDO COMPLETO (sin truncar)
                content = fragment.get('content', '')
                if content:
                    formatted += f"   - Contenido completo:\n```\n{content}\n```\n"
                
                formatted += "\n"
        else:
            formatted += "No se encontraron resultados.\n"
        
        return formatted
    
    def _format_file_content(self, results: Dict[str, Any]) -> str:
        """Formatea contenido de archivo con TODA la información"""
        formatted = ""
        
        if 'content' in results:
            formatted += f"Contenido del archivo:\n\n"
            # INCLUIR CONTENIDO COMPLETO (sin truncar)
            formatted += f"```\n{results['content']}\n```\n"
            
            # Incluir metadata si existe
            if 'metadata' in results:
                formatted += f"\n**Metadata del archivo:**\n"
                for key, value in results['metadata'].items():
                    formatted += f"- {key}: {value}\n"
        
        return formatted
    
    def process_request(self, session_id: str, user_input: str) -> RequestResult:
        """
        Procesa un request completo del usuario con ejecución iterativa de herramientas
        
        Flujo:
        1. Crear/obtener sesión
        2. Enviar request al LLM
        3. Parsear respuesta y extraer herramientas
        4. Ejecutar herramientas si es necesario
        5. Enviar resultados al LLM
        6. Repetir pasos 3-5 hasta que LLM no solicite más herramientas (máx iteraciones)
        7. Formatear respuesta final
        
        Args:
            session_id: ID de la sesión
            user_input: Input del usuario
            
        Returns:
            RequestResult con resultado completo
        """
        start_time = time.time()
        metrics = ProcessingMetrics(
            total_time_ms=0,
            llm_time_ms=0,
            tools_time_ms=0,
            formatting_time_ms=0,
            tokens_input=0,
            tokens_output=0,
            tools_executed=0,
            tools_successful=0,
            tools_failed=0,
            cache_tokens_saved=0
        )
        
        try:
            # Crear sesión si no existe
            if not self.conversation_manager.get_conversation_context(session_id):
                self.conversation_manager.create_conversation(session_id)
            
            self.logger.info(f"Procesando request para sesión {session_id}")
            
            # 1. Enviar request inicial al LLM
            self.logger.debug("Enviando request inicial al LLM...")
            llm_start = time.time()
            
            current_llm_response = self.llm_communication.send_request_with_conversation(
                session_id=session_id,
                user_input=user_input
            )
            
            metrics.llm_time_ms = (time.time() - llm_start) * 1000
            metrics.tokens_input = current_llm_response.usage.get('input_tokens', 0)
            metrics.tokens_output = current_llm_response.usage.get('output_tokens', 0)
            
            if current_llm_response.cache_stats:
                metrics.cache_tokens_saved = current_llm_response.cache_stats.get('tokens_saved', 0)
            
            self.logger.info(f"Respuesta LLM inicial recibida en {metrics.llm_time_ms:.2f}ms")
            
            # Mostrar la respuesta inicial del LLM en pantalla (verde)
            from color_utils import llm_response as color_llm_response
            print(color_llm_response("\n🤖 Agente (respuesta inicial):"))
            print(color_llm_response(current_llm_response.content))
            print()
            
            # 2. CICLO ITERATIVO: Ejecutar herramientas mientras el LLM las solicite
            all_tool_results = []
            iteration = 0
            max_iterations = self.max_tool_iterations
            
            while iteration < max_iterations and self.enable_tool_execution:
                iteration += 1
                
                # Verificar si hay herramientas en la respuesta actual
                tool_calls = self.tool_executor.parse_tool_calls_from_xml(current_llm_response.content)
                
                if not tool_calls:
                    # No hay más herramientas, salir del ciclo
                    self.logger.info(f"✅ No se encontraron más herramientas en iteración {iteration}. Finalizando ciclo.")
                    break
                
                self.logger.info(f"🔧 Iteración {iteration}/{max_iterations}: Encontradas {len(tool_calls)} herramientas a ejecutar")
                
                # Mostrar en pantalla las herramientas que se van a ejecutar (breve)
                for tool_call in tool_calls:
                    tool_name = tool_call.get('tool_type', 'unknown')
                    if hasattr(tool_name, 'value'):
                        tool_name = tool_name.value
                    params = tool_call.get('params', {})
                    # Crear línea breve con parámetros principales
                    if params:
                        params_str = ", ".join([f"{k}={str(v)[:50] if isinstance(v, str) else v}" for k, v in params.items()])
                        print(info(f"  🔧 Ejecutando: {tool_name}({params_str})"))
                    else:
                        print(info(f"  🔧 Ejecutando: {tool_name}()"))
                
                # Ejecutar herramientas
                tools_start = time.time()
                tool_results = self.tool_executor.execute_tool_calls(tool_calls)
                iteration_tools_time = (time.time() - tools_start) * 1000
                
                metrics.tools_time_ms += iteration_tools_time
                metrics.tools_executed += tool_results.total_tools_executed
                metrics.tools_successful += tool_results.successful_executions
                metrics.tools_failed += tool_results.failed_executions
                
                all_tool_results.append(tool_results)
                
                # Log DETALLADO al archivo (no a pantalla)
                separator = "="*80
                self.logger.info(separator)
                self.logger.info(f"🔧 RESULTADOS DE EJECUCIÓN - ITERACIÓN {iteration}")
                self.logger.info(separator)
                self.logger.info(f"Tiempo de ejecución: {iteration_tools_time:.2f}ms")
                self.logger.info(f"Total ejecutadas: {tool_results.total_tools_executed}")
                self.logger.info(f"Exitosas: {tool_results.successful_executions}")
                self.logger.info(f"Fallidas: {tool_results.failed_executions}")
                
                # Detalles de cada herramienta al log
                for result in tool_results.results:
                    tool_name = result.tool_type.value
                    self.logger.info("-"*80)
                    self.logger.info(f"Herramienta: {tool_name}")
                    self.logger.info(f"Estado: {'✅ Exitosa' if result.success else '❌ Fallida'}")
                    self.logger.info(f"Tiempo: {result.execution_time_ms:.2f}ms")
                    if not result.success and result.error:
                        self.logger.info(f"Error: {result.error}")
                    # Log del contenido de resultados (solo al archivo)
                    if result.success and result.data:
                        self.logger.debug(f"Datos: {str(result.data)[:500]}...")
                
                self.logger.info(separator)
                
                # Enviar resultados al LLM para siguiente iteración
                self.logger.info(f"🔄 Enviando resultados de iteración {iteration} al LLM...")
                
                tool_results_message = self._format_tool_results_for_llm(tool_results)
                
                llm_start_iter = time.time()
                current_llm_response = self.llm_communication.send_request_with_conversation(
                    session_id=session_id,
                    user_input=tool_results_message
                )
                
                llm_time_iter = (time.time() - llm_start_iter) * 1000
                metrics.llm_time_ms += llm_time_iter
                metrics.tokens_input += current_llm_response.usage.get('input_tokens', 0)
                metrics.tokens_output += current_llm_response.usage.get('output_tokens', 0)
                
                if current_llm_response.cache_stats:
                    metrics.cache_tokens_saved += current_llm_response.cache_stats.get('tokens_saved', 0)
                
                self.logger.info(f"✅ Respuesta LLM iteración {iteration} recibida en {llm_time_iter:.2f}ms")
                
                # Mostrar la respuesta del LLM de esta iteración en pantalla (verde)
                print(color_llm_response(f"\n🤖 Agente (después de iteración {iteration}):"))
                print(color_llm_response(current_llm_response.content))
                print()
            
            # Verificar si se alcanzó el máximo de iteraciones
            if iteration >= max_iterations and self.enable_tool_execution:
                tool_calls_remaining = self.tool_executor.parse_tool_calls_from_xml(current_llm_response.content)
                if tool_calls_remaining:
                    self.logger.warning(f"⚠️  Alcanzado máximo de iteraciones ({max_iterations}). Aún hay {len(tool_calls_remaining)} herramientas pendientes.")
            
            # Consolidar todos los resultados de herramientas
            final_tool_results = None
            if all_tool_results:
                # Usar el último resultado como referencia principal
                final_tool_results = all_tool_results[-1]
                self.logger.info(f"📊 Total de iteraciones de herramientas: {len(all_tool_results)}")
            
            # 3. Formatear respuesta final
            self.logger.debug("Formateando respuesta final...")
            formatting_start = time.time()
            
            formatted_response = self.response_formatter.format_static_response(
                llm_content=current_llm_response.content,
                tool_results=final_tool_results.__dict__ if final_tool_results else None
            )
            
            metrics.formatting_time_ms = (time.time() - formatting_start) * 1000
            
            self.logger.info(f"📝 Respuesta formateada en {metrics.formatting_time_ms:.2f}ms")
            
            # Calcular tiempo total
            metrics.total_time_ms = (time.time() - start_time) * 1000
            
            # Crear resultado (usar la respuesta final del LLM)
            result = RequestResult(
                session_id=session_id,
                user_input=user_input,
                llm_response=current_llm_response,
                tool_results=final_tool_results,
                formatted_response=formatted_response,
                metrics=metrics,
                state=RequestState.COMPLETED
            )
            
            self.logger.info(f"✅ Request completado en {metrics.total_time_ms:.2f}ms")
            self.logger.info(f"📊 Resumen: {iteration} iteraciones, {metrics.tools_executed} herramientas ejecutadas")
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error procesando request: {str(e)}", exc_info=True)
            
            # Retornar resultado de error
            metrics.total_time_ms = (time.time() - start_time) * 1000
            
            return RequestResult(
                session_id=session_id,
                user_input=user_input,
                llm_response=None,
                tool_results=None,
                formatted_response=None,
                metrics=metrics,
                state=RequestState.ERROR
            )
    
    def process_request_with_iterations(self, session_id: str, user_input: str,
                                       max_iterations: Optional[int] = None) -> RequestResult:
        """
        Procesa un request con posibles iteraciones (si el LLM solicita más herramientas)
        
        Args:
            session_id: ID de la sesión
            user_input: Input del usuario
            max_iterations: Máximo número de iteraciones
            
        Returns:
            RequestResult con resultado final
        """
        max_iterations = max_iterations or self.max_tool_iterations
        iteration = 0
        
        self.logger.info(f"Iniciando procesamiento iterativo (máx {max_iterations} iteraciones)")
        
        while iteration < max_iterations:
            iteration += 1
            self.logger.debug(f"Iteración {iteration}/{max_iterations}")
            
            result = self.process_request(session_id, user_input)
            
            if result.state == RequestState.ERROR:
                self.logger.error(f"Error en iteración {iteration}")
                return result
            
            # Si no hay herramientas o todas fueron ejecutadas, terminar
            if not result.tool_results or result.tool_results.failed_executions == 0:
                self.logger.info(f"Procesamiento completado en iteración {iteration}")
                return result
            
            # Si hay herramientas fallidas, continuar iterando
            self.logger.warning(
                f"Herramientas fallidas en iteración {iteration}, "
                f"continuando con siguiente iteración..."
            )
        
        self.logger.warning(f"Alcanzado máximo de iteraciones ({max_iterations})")
        return result
    
    def get_processing_summary(self, result: RequestResult) -> str:
        """
        Genera un resumen del procesamiento
        
        Args:
            result: Resultado del procesamiento
            
        Returns:
            String con resumen formateado
        """
        summary = f"""
╔════════════════════════════════════════════════════════════════╗
║              RESUMEN DE PROCESAMIENTO DE REQUEST               ║
╚════════════════════════════════════════════════════════════════╝

📋 Información General:
  • Sesión: {result.session_id}
  • Estado: {result.state.value}
  • Timestamp: {result.timestamp}

📝 Input del Usuario:
  {result.user_input[:100]}...

⏱️  Métricas de Tiempo:
  • Tiempo total: {result.metrics.total_time_ms:.2f}ms
  • Tiempo LLM: {result.metrics.llm_time_ms:.2f}ms
  • Tiempo herramientas: {result.metrics.tools_time_ms:.2f}ms
  • Tiempo formateo: {result.metrics.formatting_time_ms:.2f}ms

📊 Uso de Tokens:
  • Input tokens: {result.metrics.tokens_input}
  • Output tokens: {result.metrics.tokens_output}
  • Total: {result.metrics.tokens_input + result.metrics.tokens_output}
  • Tokens ahorrados (cache): {result.metrics.cache_tokens_saved}

🔧 Ejecución de Herramientas:
  • Total ejecutadas: {result.metrics.tools_executed}
  • Exitosas: {result.metrics.tools_successful}
  • Fallidas: {result.metrics.tools_failed}

📄 Respuesta Formateada:
  • Herramientas encontradas: {result.formatted_response.tool_calls_count if result.formatted_response else 'N/A'}
  • Longitud contenido: {len(result.formatted_response.filtered_content) if result.formatted_response else 0} caracteres
"""
        
        return summary
    
    def get_conversation_history(self, session_id: str) -> str:
        """
        Obtiene el historial de conversación
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            String con historial formateado
        """
        return self.conversation_manager.get_conversation_context(session_id)
    
    def get_conversation_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la conversación
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Diccionario con estadísticas
        """
        return self.conversation_manager.get_conversation_stats(session_id)
    
    def end_session(self, session_id: str) -> None:
        """
        Finaliza una sesión
        
        Args:
            session_id: ID de la sesión
        """
        self.conversation_manager.delete_conversation(session_id)
        self.logger.info(f"Sesión {session_id} finalizada")


def main():
    """Función principal para testing"""
    import logging
    
    # Configurar logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # System prompt
    system_prompt = """Eres un asistente especializado en consultas sobre la base de conocimiento Darwin.
Tu objetivo es responder preguntas sobre aspectos funcionales y técnicos del sistema.
Cuando necesites información, solicita el uso de herramientas de búsqueda mediante XML."""
    
    # Crear manejador de requests
    handler = RequestHandler(system_prompt=system_prompt)
    
    # Procesar request
    session_id = "test-session-001"
    user_input = "¿Cuáles son los principales módulos de Darwin?"
    
    print("Procesando request...")
    try:
        result = handler.process_request(session_id, user_input)
        
        # Mostrar resumen
        print(handler.get_processing_summary(result))
        
        # Mostrar respuesta formateada
        if result.formatted_response:
            print("\n📄 Respuesta Formateada:")
            print(result.formatted_response.filtered_content)
        
        # Mostrar estadísticas de conversación
        print("\n📊 Estadísticas de Conversación:")
        stats = handler.get_conversation_stats(session_id)
        for key, value in stats.items():
            print(f"  • {key}: {value}")
    
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
