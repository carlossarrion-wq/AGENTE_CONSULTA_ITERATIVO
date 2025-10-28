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
from conversation_logger import ConversationLogger
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
        self.conversation_logger = ConversationLogger(logs_dir="logs")
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
        Formatea los resultados de las herramientas para enviarlos al LLM.
        IMPORTANTE: Este método envía información resumida al LLM para que pueda analizarla.
        
        Args:
            tool_results: Resultados consolidados de las herramientas
            
        Returns:
            String formateado con los resultados para el LLM
        """
        # Mensaje claro indicando que debe analizar y responder
        message = "[RESULTADOS DE TUS HERRAMIENTAS]\n\n"
        message += "IMPORTANTE: Analiza estos resultados y presenta tu respuesta al usuario usando <present_answer>.\n"
        message += "NO solicites más herramientas a menos que la información sea claramente insuficiente.\n\n"
        
        for result in tool_results.results:
            tool_name = result.tool_type.value
            
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
        """
        Formatea resultados de búsqueda SOLO CON INFORMACIÓN RESUMIDA para el LLM.
        NO se envía el contenido completo para evitar que el LLM lo repita en pantalla.
        El contenido completo está disponible en los logs para debugging.
        """
        formatted = ""
        
        if 'fragments' in results and results['fragments']:
            total_fragments = len(results['fragments'])
            formatted += f"Se encontraron {total_fragments} fragmentos relevantes.\n\n"
            formatted += "**Información resumida de los fragmentos:**\n\n"
            
            # Agrupar por archivo para evitar repetición
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
                    # Solo guardar un preview del contenido más relevante
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
        """
        Formatea contenido de archivo COMPLETO para el LLM.
        IMPORTANTE: Este contenido se envía al LLM pero NO se muestra en pantalla.
        Solo va a los logs para debugging.
        """
        formatted = ""
        
        if 'content' in results:
            content = results['content']
            file_name = results.get('file_name', 'archivo')
            
            # Información básica
            formatted += f"Archivo: {file_name}\n"
            formatted += f"Tamaño del contenido: {len(content)} caracteres\n\n"
            
            # ENVIAR CONTENIDO COMPLETO AL LLM (no se mostrará en pantalla)
            formatted += f"Contenido completo del archivo:\n\n"
            formatted += f"```\n{content}\n```\n"
            
            # Incluir metadata si existe
            if 'metadata' in results:
                formatted += f"\n**Metadata del archivo:**\n"
                for key, value in results['metadata'].items():
                    formatted += f"- {key}: {value}\n"
        
        return formatted
    
    def _get_conversation_history_for_logging(self, session_id: str) -> List[Dict[str, str]]:
        """
        Obtiene el historial de conversación en formato estructurado para logging
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Lista de mensajes en formato [{"role": "user/assistant", "content": "..."}]
        """
        # Obtener el contexto conversacional como string
        conversation_context = self.conversation_manager.get_conversation_context(session_id)
        
        if not conversation_context:
            return []
        
        # Parsear el contexto para convertirlo en lista estructurada
        history = []
        lines = conversation_context.strip().split('\n\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('Human:'):
                content = line.replace('Human:', '', 1).strip()
                history.append({"role": "user", "content": content})
            elif line.startswith('Assistant:'):
                content = line.replace('Assistant:', '', 1).strip()
                history.append({"role": "assistant", "content": content})
        
        return history
    
    def _filter_tool_results_text(self, content: str) -> str:
        """
        Filtra el texto de resultados de herramientas que el LLM puede copiar
        
        ESTRATEGIA: Si hay etiquetas XML de herramientas, truncar TODO después de la etiqueta de cierre
        
        Args:
            content: Contenido de la respuesta del LLM
            
        Returns:
            Contenido filtrado sin el texto de resultados
        """
        import re
        
        # PASO 1: Buscar etiquetas de cierre de herramientas XML
        # Si encontramos una, truncamos TODO lo que viene después
        tool_closing_tags = [
            r'</semantic_search>',
            r'</lexical_search>',
            r'</regex_search>',
            r'</get_file_content>'
        ]
        
        # Buscar la ÚLTIMA etiqueta de cierre de herramienta en el contenido
        last_tool_end = -1
        for tag_pattern in tool_closing_tags:
            matches = list(re.finditer(tag_pattern, content, re.IGNORECASE))
            if matches:
                # Obtener la posición del final de la última coincidencia
                last_match_end = matches[-1].end()
                if last_match_end > last_tool_end:
                    last_tool_end = last_match_end
        
        # Si encontramos alguna etiqueta de cierre, truncar TODO después de ella
        if last_tool_end > 0:
            content = content[:last_tool_end].rstrip()
        
        # PASO 2: Adicionalmente, buscar y eliminar el patrón "H: [RESULTADOS..." si aparece
        pattern = r'(?:H:\s*)?\[RESULTADOS\s+DE\s+HERRAMIENTAS[^\]]*\].*'
        content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        return content
    
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
            
            # 1. CAPTURAR HISTORIAL ANTES de enviar al LLM
            # IMPORTANTE: Debe hacerse ANTES porque send_request_with_conversation
            # agrega el turno actual al historial
            conversation_history_before_request = self._get_conversation_history_for_logging(session_id)
            
            # 2. Enviar request inicial al LLM
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
            
            # TRUNCAR INMEDIATAMENTE el contenido para evitar ejecutar herramientas de la parte descartada
            # IMPORTANTE: Esto debe hacerse ANTES de parsear herramientas
            current_llm_response.content = self._filter_tool_results_text(current_llm_response.content)
            
            # REGISTRAR interacción inicial con el LLM en logs/
            try:
                # Usar el historial capturado ANTES del request
                # Este es el historial que realmente se envió al LLM
                conversation_history = conversation_history_before_request
                
                # Obtener estadísticas de conversación para sliding window info
                conv_stats = self.conversation_manager.get_conversation_stats(session_id)
                
                # Obtener configuración de sliding window
                conversation_config = self.config.get_section('conversation')
                enable_sliding_window = conversation_config.get('enable_sliding_window', True)
                max_context_tokens = conversation_config.get('context_window_tokens', 180000)
                
                # Calcular información de sliding window
                sliding_window_info = {
                    "enabled": enable_sliding_window,
                    "max_context_tokens": max_context_tokens,
                    "total_turns_in_session": conv_stats.get('total_turns', 0),
                    "total_tokens_in_session": conv_stats.get('total_tokens', 0),
                    "turns_in_context": len(conversation_history),
                    "turns_removed": max(0, (conv_stats.get('total_turns', 0) // 2) - len(conversation_history))
                }
                
                self.conversation_logger.log_conversation_turn(
                    session_id=session_id,
                    user_input=user_input,
                    llm_response=current_llm_response.content,
                    metrics={
                        "llm_time_ms": metrics.llm_time_ms,
                        "tokens_input": metrics.tokens_input,
                        "tokens_output": metrics.tokens_output,
                        "cache_tokens_saved": metrics.cache_tokens_saved,
                        "iteration": 0,
                        "interaction_type": "initial_request"
                    },
                    request_metadata={
                        "system_prompt": self.llm_communication.system_prompt,
                        "conversation_history_sent_to_llm": conversation_history,
                        "sliding_window_info": sliding_window_info,
                        "model_id": self.llm_communication.model_id,
                        "max_tokens": self.llm_communication.max_tokens,
                        "temperature": self.llm_communication.temperature,
                        "stop_reason": current_llm_response.stop_reason
                    }
                )
            except Exception as log_error:
                self.logger.warning(f"Error registrando interacción inicial: {log_error}")
            
            # Mostrar la respuesta inicial del LLM en pantalla
            from color_utils import llm_response_custom, thinking_text, tool_xml
            
            # Parsear y colorear la respuesta según su contenido
            # NOTA: Ya está truncado arriba, no necesitamos filtrar de nuevo
            response_content = current_llm_response.content
            
            # Detectar y colorear secciones de thinking
            if '<thinking>' in response_content:
                parts = response_content.split('<thinking>')
                colored_response = parts[0]
                for part in parts[1:]:
                    if '</thinking>' in part:
                        thinking_content, rest = part.split('</thinking>', 1)
                        colored_response += thinking_text(f"<thinking>{thinking_content}</thinking>")
                        colored_response += rest
                    else:
                        colored_response += thinking_text(f"<thinking>{part}")
                response_content = colored_response
            
            # Detectar y colorear bloques XML de herramientas
            import re
            tool_pattern = r'(<(?:semantic_search|lexical_search|regex_search|get_file_content)>.*?</(?:semantic_search|lexical_search|regex_search|get_file_content)>)'
            response_content = re.sub(tool_pattern, lambda m: tool_xml(m.group(1)), response_content, flags=re.DOTALL)
            
            # Detectar y colorear bloques <present_answer> (respuesta final del LLM en verde)
            # IMPORTANTE: Este bloque debe mostrarse en verde oscuro (#356D34)
            present_answer_pattern = r'(<present_answer>.*?</present_answer>)'
            response_content = re.sub(present_answer_pattern, lambda m: llm_response_custom(m.group(1)), response_content, flags=re.DOTALL)
            
            print(llm_response_custom("\n🤖 Agente (respuesta inicial):"))
            print(response_content)  # Ya no necesita llm_response_custom aquí porque ya está coloreado
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
                
                # Mostrar en pantalla las herramientas que se van a ejecutar (en rojo oscuro)
                from color_utils import tool_invocation
                for tool_call in tool_calls:
                    tool_name = tool_call.get('tool_type', 'unknown')
                    if hasattr(tool_name, 'value'):
                        tool_name = tool_name.value
                    params = tool_call.get('params', {})
                    # Crear línea breve con parámetros principales
                    if params:
                        # Para file_path, mostrar el nombre completo sin truncar
                        # Para otros parámetros, truncar a 100 caracteres
                        params_str = ", ".join([
                            f"{k}={str(v)}" if k == 'file_path' else f"{k}={str(v)[:100] if isinstance(v, str) else v}" 
                            for k, v in params.items()
                        ])
                        print(tool_invocation(f"  🔧 Ejecutando: {tool_name}({params_str})"))
                    else:
                        print(tool_invocation(f"  🔧 Ejecutando: {tool_name}()"))
                
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
                        self.logger.debug(f"Datos completos: {str(result.data)[:1000]}...")
                        # Log específico para semantic_search para debug de scores
                        if tool_name == "semantic_search" and 'fragments' in result.data:
                            self.logger.info(f"DEBUG SCORES - Total fragments: {len(result.data['fragments'])}")
                            for idx, frag in enumerate(result.data['fragments'][:3]):  # Primeros 3
                                self.logger.info(f"  Fragment {idx+1}: file={frag.get('file_name', 'N/A')}, score={frag.get('score', 'MISSING')}")
                
                self.logger.info(separator)
                
                # Enviar resultados al LLM para siguiente iteración
                self.logger.info(f"🔄 Enviando resultados de iteración {iteration} al LLM...")
                
                tool_results_message = self._format_tool_results_for_llm(tool_results)
                
                # IMPORTANTE: Los resultados se envían al LLM pero NO se muestran en pantalla
                # Solo mostramos un resumen breve al usuario
                print(info(f"  ℹ️  Resultados enviados al LLM ({len(tool_results_message)} caracteres)"))
                
                # CAPTURAR HISTORIAL ANTES de enviar al LLM (para iteraciones)
                conversation_history_before_iter = self._get_conversation_history_for_logging(session_id)
                
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
                
                # TRUNCAR INMEDIATAMENTE el contenido para evitar ejecutar herramientas de la parte descartada
                # IMPORTANTE: Esto debe hacerse ANTES de parsear herramientas en la siguiente iteración
                current_llm_response.content = self._filter_tool_results_text(current_llm_response.content)
                
                # REGISTRAR interacción iterativa con el LLM en logs/
                try:
                    # Usar el historial capturado ANTES del request iterativo
                    conversation_history_iter = conversation_history_before_iter
                    
                    # Obtener estadísticas actualizadas de conversación para sliding window info
                    conv_stats_iter = self.conversation_manager.get_conversation_stats(session_id)
                    
                    # Calcular información de sliding window para esta iteración
                    sliding_window_info_iter = {
                        "enabled": enable_sliding_window,
                        "max_context_tokens": max_context_tokens,
                        "total_turns_in_session": conv_stats_iter.get('total_turns', 0),
                        "total_tokens_in_session": conv_stats_iter.get('total_tokens', 0),
                        "turns_in_context": len(conversation_history_iter),
                        "turns_removed": max(0, (conv_stats_iter.get('total_turns', 0) // 2) - len(conversation_history_iter))
                    }
                    
                    self.conversation_logger.log_conversation_turn(
                        session_id=session_id,
                        user_input=tool_results_message,
                        llm_response=current_llm_response.content,
                        metrics={
                            "llm_time_ms": llm_time_iter,
                            "tokens_input": current_llm_response.usage.get('input_tokens', 0),
                            "tokens_output": current_llm_response.usage.get('output_tokens', 0),
                            "cache_tokens_saved": current_llm_response.cache_stats.get('tokens_saved', 0) if current_llm_response.cache_stats else 0,
                            "iteration": iteration,
                            "interaction_type": "tool_results_response",
                            "tools_executed": tool_results.total_tools_executed,
                            "tools_successful": tool_results.successful_executions,
                            "tools_failed": tool_results.failed_executions
                        },
                        request_metadata={
                            "system_prompt": self.llm_communication.system_prompt,
                            "conversation_history_sent_to_llm": conversation_history_iter,
                            "sliding_window_info": sliding_window_info_iter,
                            "model_id": self.llm_communication.model_id,
                            "max_tokens": self.llm_communication.max_tokens,
                            "temperature": self.llm_communication.temperature,
                            "stop_reason": current_llm_response.stop_reason
                        }
                    )
                except Exception as log_error:
                    self.logger.warning(f"Error registrando interacción iteración {iteration}: {log_error}")
                
                # Mostrar la respuesta del LLM de esta iteración en pantalla
                # NOTA: Ya está truncado arriba, no necesitamos filtrar de nuevo
                response_content_iter = current_llm_response.content
                
                # Detectar y colorear secciones de thinking
                if '<thinking>' in response_content_iter:
                    parts = response_content_iter.split('<thinking>')
                    colored_response = parts[0]
                    for part in parts[1:]:
                        if '</thinking>' in part:
                            thinking_content, rest = part.split('</thinking>', 1)
                            colored_response += thinking_text(f"<thinking>{thinking_content}</thinking>")
                            colored_response += rest
                        else:
                            colored_response += thinking_text(f"<thinking>{part}")
                    response_content_iter = colored_response
                
                # Detectar y colorear bloques XML de herramientas
                response_content_iter = re.sub(tool_pattern, lambda m: tool_xml(m.group(1)), response_content_iter, flags=re.DOTALL)
                
                # Detectar y colorear bloques <present_answer> en iteraciones
                response_content_iter = re.sub(present_answer_pattern, lambda m: llm_response_custom(m.group(1)), response_content_iter, flags=re.DOTALL)
                
                print(llm_response_custom(f"\n🤖 Agente (después de iteración {iteration}):"))
                print(response_content_iter)  # Ya está coloreado
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
