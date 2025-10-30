"""
LLM Communication Module - Comunicación con el modelo de lenguaje

Responsabilidad: Gestionar comunicación con AWS Bedrock
- Construcción de prompts con contexto
- Envío de requests a AWS Bedrock
- Recepción de respuestas (batch/stream)
- Manejo de errores y reintentos
- Integración con Prompt Cache Manager
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, BotoCoreError
import yaml
from pathlib import Path

from config_manager import ConfigManager
from prompt_cache_manager import PromptCacheManager
from conversation_manager import ConversationManager
from s3_summaries_loader import S3SummariesLoader
from color_utils import (
    llm_request, llm_response, info, error, success, header, dim_text
)


def generate_web_crawler_documentation(app_name: str) -> str:
    """
    Genera la documentación de la herramienta web crawler dinámicamente
    
    Args:
        app_name: Nombre de la aplicación (mulesoft, darwin, sap)
        
    Returns:
        String con la documentación formateada o string vacío si está deshabilitada
    """
    try:
        from pathlib import Path
        
        # Cargar el contenido del archivo de documentación
        doc_path = Path("config/web_crawler_tool_section.md")
        if not doc_path.exists():
            logging.getLogger(__name__).warning(f"Archivo de documentación no encontrado: {doc_path}")
            return ""
        
        with open(doc_path, 'r', encoding='utf-8') as f:
            documentation = f.read()
        
        logging.getLogger(__name__).info(f"✅ Documentación de web crawler cargada desde {doc_path}")
        return documentation
        
    except Exception as e:
        logging.getLogger(__name__).warning(f"Error generando documentación web crawler: {e}")
        return ""


@dataclass
class LLMRequest:
    """Estructura de un request al LLM"""
    session_id: str
    system_prompt: str
    user_input: str
    conversation_history: List[Dict[str, str]]
    max_tokens: int
    temperature: float
    use_cache: bool = True
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class LLMResponse:
    """Estructura de una respuesta del LLM"""
    content: str
    model: str
    stop_reason: str
    usage: Dict[str, int]
    execution_time_ms: float
    cache_stats: Optional[Dict[str, Any]] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class LLMCommunication:
    """Gestor de comunicación con AWS Bedrock"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Inicializa el módulo de comunicación LLM
        
        Args:
            config_path: Ruta al archivo de configuración principal
        """
        self.config = ConfigManager(config_path)
        self.logger = logging.getLogger(__name__)
        
        # Obtener configuración de S3 desde el archivo de configuración
        s3_config = self.config.get_section('s3')
        
        # Inicializar S3 Summaries Loader con la configuración correcta
        self.s3_loader = S3SummariesLoader(s3_config=s3_config)
        
        # Leer ruta del system prompt desde configuración
        agent_config = self.config.get_section('agent')
        system_prompt_file = agent_config.get('system_prompt_file', 'config/system_prompt_darwin.md')
        
        # Cargar system prompt desde archivo de texto (con resúmenes dinámicos desde S3)
        self.system_prompt = self._load_system_prompt(system_prompt_file)
        
        # Inicializar managers
        prompt_cache_config = self.config.get_section('prompt_caching')
        self.prompt_cache_manager = PromptCacheManager(prompt_cache_config)
        conversation_config = self.config.get_section('conversation')
        self.conversation_manager = ConversationManager(conversation_config)
        
        # Inicializar cliente Bedrock
        try:
            bedrock_config = self.config.get_section('bedrock')
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=bedrock_config.get('region_name', 'eu-west-1')
            )
            # Leer modelo_id desde sección llm
            llm_config = self.config.get_section('llm')
            self.model_id = llm_config.get('model_id', 'eu.anthropic.claude-haiku-4-5-20251001-v1:0')
            self.logger.info(f"Cliente Bedrock inicializado para modelo: {self.model_id}")
        except Exception as e:
            self.logger.error(f"Error inicializando cliente Bedrock: {str(e)}")
            raise
        
        # Configuración LLM
        llm_config = self.config.get_section('llm')
        self.max_tokens = llm_config.get('max_tokens', 4000)
        self.temperature = llm_config.get('temperature', 0.1)
        self.max_retries = llm_config.get('max_retries', 3)
        self.retry_delay_seconds = llm_config.get('retry_delay_seconds', 1)
    
    def _load_system_prompt(self, system_prompt_file: str) -> str:
        """
        Carga el prompt de sistema directamente desde un archivo de texto
        y popula dinámicamente la sección de documentos disponibles desde S3
        
        Args:
            system_prompt_file: Ruta al archivo de texto con el prompt de sistema
            
        Returns:
            String con el prompt de sistema completo con resúmenes dinámicos
        """
        try:
            prompt_path = Path(system_prompt_file)
            if not prompt_path.exists():
                self.logger.warning(f"Archivo de prompt no encontrado: {system_prompt_file}")
                return self._get_default_system_prompt()
            
            # Leer el contenido del archivo de texto directamente
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            
            # Buscar el marcador {{DYNAMIC_SUMMARIES}} y reemplazarlo con los resúmenes de S3
            if "{{DYNAMIC_SUMMARIES}}" in prompt_template:
                self.logger.info("📥 Cargando resúmenes dinámicamente desde S3...")
                summaries_section = self.s3_loader.get_summaries_section()
                prompt = prompt_template.replace("{{DYNAMIC_SUMMARIES}}", summaries_section)
                self.logger.info(f"✅ Resúmenes cargados y populados en el system prompt")
            else:
                # Si no hay marcador, usar el prompt tal cual
                prompt = prompt_template
                self.logger.warning("⚠️  No se encontró el marcador {{DYNAMIC_SUMMARIES}} en el system prompt")
            
            # Buscar el marcador {{WEB_CRAWLER_TOOL}} y reemplazarlo con la documentación del web crawler
            if "{{WEB_CRAWLER_TOOL}}" in prompt:
                self.logger.info("🌐 Cargando documentación de web crawler dinámicamente...")
                # Extraer el nombre de la app desde el nombre del archivo
                app_name = "darwin"  # Default
                if "mulesoft" in system_prompt_file.lower():
                    app_name = "mulesoft"
                elif "sap" in system_prompt_file.lower():
                    app_name = "sap"
                
                web_crawler_doc = generate_web_crawler_documentation(app_name)
                if web_crawler_doc:
                    prompt = prompt.replace("{{WEB_CRAWLER_TOOL}}", web_crawler_doc)
                    self.logger.info(f"✅ Documentación de web crawler cargada para {app_name}")
                else:
                    # Si está deshabilitada, remover el marcador
                    prompt = prompt.replace("{{WEB_CRAWLER_TOOL}}", "")
                    self.logger.info(f"ℹ️  Web crawler deshabilitado para {app_name}")
            
            self.logger.info(f"✅ System prompt cargado desde archivo: {system_prompt_file}")
            self.logger.info(f"   Tamaño: {len(prompt)} caracteres")
            self.logger.info(f"   Líneas: {len(prompt.splitlines())}")
            
            return prompt
        
        except Exception as e:
            self.logger.error(f"Error cargando system prompt desde {system_prompt_file}: {str(e)}")
            return self._get_default_system_prompt()
    
    def _get_default_system_prompt(self) -> str:
        """
        Retorna el prompt de sistema por defecto si no se puede cargar desde archivo
        
        Returns:
            String con el prompt de sistema por defecto
        """
        return """Eres un asistente especializado en consultas sobre la base de conocimiento Darwin.
Tu objetivo es responder preguntas sobre aspectos funcionales y técnicos del sistema.
Cuando necesites información, solicita el uso de herramientas de búsqueda mediante XML.
Siempre proporciona respuestas claras, precisas y bien estructuradas."""
    
    def build_prompt(self, session_id: str, system_prompt: str, user_input: str, 
                    use_cache: bool = True) -> Tuple[str, Dict[str, Any]]:
        """
        Construye el prompt completo con contexto conversacional
        
        Args:
            session_id: ID de la sesión
            system_prompt: Prompt del sistema
            user_input: Input del usuario
            use_cache: Usar Prompt Caching
            
        Returns:
            Tupla (prompt_completo, cache_stats)
        """
        cache_stats = {
            'cache_enabled': use_cache,
            'system_prompt_cached': False,
            'conversation_cached': False,
            'tokens_saved': 0
        }
        
        if use_cache:
            # Cachear system prompt
            cached_system = self.prompt_cache_manager.cache_system_prompt(system_prompt)
            cache_stats['system_prompt_cached'] = True
            
            # Construir prompt incremental con cache
            prompt = self.prompt_cache_manager.build_incremental_prompt(
                session_id=session_id,
                system_prompt=system_prompt,
                user_input=user_input
            )
            
            # Obtener estadísticas de cache
            cache_info = self.prompt_cache_manager.get_cache_stats()
            cache_stats['conversation_cached'] = True
            cache_stats['cache_info'] = cache_info
        else:
            # Construir prompt sin cache
            conversation_context = self.conversation_manager.get_conversation_context(session_id)
            prompt = f"{system_prompt}\n\n{conversation_context}\n\nHuman: {user_input}\n\nAssistant:"
        
        return prompt, cache_stats
    
    def send_request_streaming(self, llm_request: LLMRequest, 
                              token_callback: callable) -> LLMResponse:
        """
        Envía un request a AWS Bedrock con streaming habilitado
        
        Args:
            llm_request: Request al LLM
            token_callback: Función callback que recibe cada token generado
            
        Returns:
            LLMResponse con respuesta completa del modelo
        """
        start_time = time.time()
        
        # Construir prompt
        prompt, cache_stats = self.build_prompt(
            session_id=llm_request.session_id,
            system_prompt=llm_request.system_prompt,
            user_input=llm_request.user_input,
            use_cache=llm_request.use_cache
        )
        
        # Construir body del request con streaming habilitado
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": llm_request.max_tokens,
            "system": llm_request.system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": llm_request.user_input
                }
            ],
            "temperature": llm_request.temperature
        }
        
        # Agregar historial de conversación si existe
        if llm_request.conversation_history:
            body["messages"] = llm_request.conversation_history + body["messages"]
        
        self.logger.debug(f"Enviando request STREAMING a Bedrock para sesión {llm_request.session_id}")
        self.logger.debug(f"Modelo: {self.model_id}")
        
        # 🔍 VUELQUE COMPLETO DEL MENSAJE AL LLM (SOLO AL LOG, NO A PANTALLA)
        separator = "="*80
        subseparator = "-"*80
        self.logger.info(separator)
        self.logger.info("📤 MENSAJE COMPLETO ENVIADO AL LLM (STREAMING)")
        self.logger.info(separator)
        self.logger.info(f"Sesión: {llm_request.session_id}")
        self.logger.info(f"Modelo: {self.model_id}")
        self.logger.info(f"Timestamp: {llm_request.timestamp}")
        self.logger.info(subseparator)
        self.logger.info("PROMPT DE SISTEMA:")
        self.logger.info(subseparator)
        self.logger.info(llm_request.system_prompt)
        self.logger.info(subseparator)
        self.logger.info("HISTORIAL DE CONVERSACIÓN:")
        self.logger.info(subseparator)
        if llm_request.conversation_history:
            for msg in llm_request.conversation_history:
                self.logger.info(f"[{msg['role'].upper()}]: {msg['content']}")
        else:
            self.logger.info("(Sin historial previo)")
        self.logger.info(subseparator)
        self.logger.info("INPUT DEL USUARIO:")
        self.logger.info(subseparator)
        self.logger.info(llm_request.user_input)
        self.logger.info(separator)
        
        # Reintentos
        for attempt in range(self.max_retries):
            try:
                # Usar invoke_model_with_response_stream para streaming
                response = self.bedrock_client.invoke_model_with_response_stream(
                    modelId=self.model_id,
                    body=json.dumps(body)
                )
                
                # Procesar stream
                full_content = ""
                stop_reason = "unknown"
                usage = {}
                
                # Iterar sobre eventos del stream
                for event in response['body']:
                    chunk = json.loads(event['chunk']['bytes'])
                    
                    # Procesar diferentes tipos de eventos
                    if chunk['type'] == 'message_start':
                        # Inicio del mensaje
                        usage = chunk.get('message', {}).get('usage', {})
                        self.logger.debug("Stream iniciado")
                    
                    elif chunk['type'] == 'content_block_start':
                        # Inicio de bloque de contenido
                        self.logger.debug("Bloque de contenido iniciado")
                    
                    elif chunk['type'] == 'content_block_delta':
                        # Delta de contenido - aquí vienen los tokens
                        if 'delta' in chunk and 'text' in chunk['delta']:
                            token = chunk['delta']['text']
                            full_content += token
                            
                            # Llamar callback con el token
                            try:
                                token_callback(token)
                            except Exception as e:
                                self.logger.error(f"Error en callback de token: {str(e)}")
                    
                    elif chunk['type'] == 'content_block_stop':
                        # Fin de bloque de contenido
                        self.logger.debug("Bloque de contenido finalizado")
                    
                    elif chunk['type'] == 'message_delta':
                        # Delta del mensaje (incluye stop_reason)
                        if 'delta' in chunk:
                            stop_reason = chunk['delta'].get('stop_reason', stop_reason)
                        if 'usage' in chunk:
                            # Actualizar usage con tokens de salida
                            usage.update(chunk['usage'])
                    
                    elif chunk['type'] == 'message_stop':
                        # Fin del mensaje
                        self.logger.debug("Stream finalizado")
                
                execution_time = (time.time() - start_time) * 1000
                
                llm_response = LLMResponse(
                    content=full_content,
                    model=self.model_id,
                    stop_reason=stop_reason,
                    usage=usage,
                    execution_time_ms=execution_time,
                    cache_stats=cache_stats
                )
                
                # 🔍 VUELQUE COMPLETO DE LA RESPUESTA DEL LLM (SOLO AL LOG, NO A PANTALLA)
                self.logger.info(separator)
                self.logger.info("📥 RESPUESTA COMPLETA DEL LLM (STREAMING)")
                self.logger.info(separator)
                self.logger.info(f"Sesión: {llm_request.session_id}")
                self.logger.info(f"Modelo: {self.model_id}")
                self.logger.info(f"Timestamp: {llm_response.timestamp}")
                self.logger.info(f"Tiempo de ejecución: {execution_time:.2f}ms")
                self.logger.info(f"Razón de parada: {llm_response.stop_reason}")
                self.logger.info(subseparator)
                self.logger.info("CONTENIDO DE LA RESPUESTA:")
                self.logger.info(subseparator)
                self.logger.info(llm_response.content)
                self.logger.info(subseparator)
                self.logger.info("ESTADÍSTICAS DE USO:")
                self.logger.info(subseparator)
                self.logger.info(f"Input tokens: {llm_response.usage.get('input_tokens', 0)}")
                self.logger.info(f"Output tokens: {llm_response.usage.get('output_tokens', 0)}")
                self.logger.info(f"Total tokens: {llm_response.usage.get('input_tokens', 0) + llm_response.usage.get('output_tokens', 0)}")
                if cache_stats:
                    self.logger.info(f"Cache habilitado: {cache_stats.get('cache_enabled', False)}")
                    self.logger.info(f"System prompt cacheado: {cache_stats.get('system_prompt_cached', False)}")
                    self.logger.info(f"Conversación cacheada: {cache_stats.get('conversation_cached', False)}")
                self.logger.info(separator)
                
                self.logger.info(
                    f"Response streaming recibida en {execution_time:.2f}ms "
                    f"(tokens: {llm_response.usage.get('output_tokens', 0)})"
                )
                
                return llm_response
            
            except (ClientError, BotoCoreError) as e:
                self.logger.warning(
                    f"Intento {attempt + 1}/{self.max_retries} falló: {str(e)}"
                )
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay_seconds)
                else:
                    self.logger.error(f"Todos los reintentos fallaron: {str(e)}")
                    raise
        
        raise RuntimeError("No se pudo completar el request después de reintentos")
    
    def send_request(self, llm_request: LLMRequest) -> LLMResponse:
        """
        Envía un request a AWS Bedrock (modo batch, sin streaming)
        
        Args:
            llm_request: Request al LLM
            
        Returns:
            LLMResponse con respuesta del modelo
        """
        start_time = time.time()
        
        # Construir prompt
        prompt, cache_stats = self.build_prompt(
            session_id=llm_request.session_id,
            system_prompt=llm_request.system_prompt,
            user_input=llm_request.user_input,
            use_cache=llm_request.use_cache
        )
        
        # Construir body del request
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": llm_request.max_tokens,
            "system": llm_request.system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": llm_request.user_input
                }
            ],
            "temperature": llm_request.temperature
        }
        
        # Agregar historial de conversación si existe
        if llm_request.conversation_history:
            body["messages"] = llm_request.conversation_history + body["messages"]
        
        self.logger.debug(f"Enviando request a Bedrock para sesión {llm_request.session_id}")
        self.logger.debug(f"Modelo: {self.model_id}")
        self.logger.debug(f"Body del request: {json.dumps(body, indent=2)}")
        self.logger.debug(f"Tokens en request: {len(prompt.split())}")
        
        # 🔍 VUELQUE COMPLETO DEL MENSAJE AL LLM (SOLO AL LOG, NO A PANTALLA)
        separator = "="*80
        subseparator = "-"*80
        self.logger.info(separator)
        self.logger.info("📤 MENSAJE COMPLETO ENVIADO AL LLM")
        self.logger.info(separator)
        self.logger.info(f"Sesión: {llm_request.session_id}")
        self.logger.info(f"Modelo: {self.model_id}")
        self.logger.info(f"Timestamp: {llm_request.timestamp}")
        self.logger.info(subseparator)
        self.logger.info("PROMPT DE SISTEMA:")
        self.logger.info(subseparator)
        self.logger.info(llm_request.system_prompt)
        self.logger.info(subseparator)
        self.logger.info("HISTORIAL DE CONVERSACIÓN:")
        self.logger.info(subseparator)
        if llm_request.conversation_history:
            for msg in llm_request.conversation_history:
                self.logger.info(f"[{msg['role'].upper()}]: {msg['content']}")
        else:
            self.logger.info("(Sin historial previo)")
        self.logger.info(subseparator)
        self.logger.info("INPUT DEL USUARIO:")
        self.logger.info(subseparator)
        self.logger.info(llm_request.user_input)
        self.logger.info(separator)
        
        # Reintentos
        for attempt in range(self.max_retries):
            try:
                response = self.bedrock_client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(body)
                )
                
                # Parsear respuesta
                response_body = json.loads(response['body'].read())
                
                execution_time = (time.time() - start_time) * 1000
                
                llm_response = LLMResponse(
                    content=response_body['content'][0]['text'],
                    model=self.model_id,
                    stop_reason=response_body.get('stop_reason', 'unknown'),
                    usage=response_body.get('usage', {}),
                    execution_time_ms=execution_time,
                    cache_stats=cache_stats
                )
                
                # 🔍 VUELQUE COMPLETO DE LA RESPUESTA DEL LLM (SOLO AL LOG, NO A PANTALLA)
                separator = "="*80
                subseparator = "-"*80
                self.logger.info(separator)
                self.logger.info("📥 RESPUESTA COMPLETA DEL LLM")
                self.logger.info(separator)
                self.logger.info(f"Sesión: {llm_request.session_id}")
                self.logger.info(f"Modelo: {self.model_id}")
                self.logger.info(f"Timestamp: {llm_response.timestamp}")
                self.logger.info(f"Tiempo de ejecución: {execution_time:.2f}ms")
                self.logger.info(f"Razón de parada: {llm_response.stop_reason}")
                self.logger.info(subseparator)
                self.logger.info("CONTENIDO DE LA RESPUESTA:")
                self.logger.info(subseparator)
                self.logger.info(llm_response.content)
                self.logger.info(subseparator)
                self.logger.info("ESTADÍSTICAS DE USO:")
                self.logger.info(subseparator)
                self.logger.info(f"Input tokens: {llm_response.usage.get('input_tokens', 0)}")
                self.logger.info(f"Output tokens: {llm_response.usage.get('output_tokens', 0)}")
                self.logger.info(f"Total tokens: {llm_response.usage.get('input_tokens', 0) + llm_response.usage.get('output_tokens', 0)}")
                if cache_stats:
                    self.logger.info(f"Cache habilitado: {cache_stats.get('cache_enabled', False)}")
                    self.logger.info(f"System prompt cacheado: {cache_stats.get('system_prompt_cached', False)}")
                    self.logger.info(f"Conversación cacheada: {cache_stats.get('conversation_cached', False)}")
                self.logger.info(separator)
                
                self.logger.info(
                    f"Response recibida en {execution_time:.2f}ms "
                    f"(tokens: {llm_response.usage.get('output_tokens', 0)})"
                )
                
                return llm_response
            
            except (ClientError, BotoCoreError) as e:
                self.logger.warning(
                    f"Intento {attempt + 1}/{self.max_retries} falló: {str(e)}"
                )
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay_seconds)
                else:
                    self.logger.error(f"Todos los reintentos fallaron: {str(e)}")
                    raise
        
        raise RuntimeError("No se pudo completar el request después de reintentos")
    
    def send_request_with_conversation(self, session_id: str, system_prompt: Optional[str] = None, 
                                      user_input: str = "") -> LLMResponse:
        """
        Envía un request integrando el historial conversacional
        
        Args:
            session_id: ID de la sesión
            system_prompt: Prompt del sistema (si es None, usa el cargado desde configuración)
            user_input: Input del usuario
            
        Returns:
            LLMResponse con respuesta del modelo
        """
        # Usar el prompt de sistema cargado desde configuración si no se proporciona uno
        if system_prompt is None:
            system_prompt = self.system_prompt
        
        # IMPORTANTE: Agregar el turno del usuario ANTES de obtener el historial
        # Esto asegura que el historial incluya el mensaje actual del usuario
        self.conversation_manager.add_user_turn(
            session_id=session_id,
            message=user_input,
            tokens=len(user_input.split())
        )
        
        # Obtener configuración de sliding window
        conversation_config = self.config.get_section('conversation')
        enable_sliding_window = conversation_config.get('enable_sliding_window', True)
        max_context_tokens = conversation_config.get('context_window_tokens', 180000)
        
        # Obtener estadísticas antes del trimming
        conv_stats = self.conversation_manager.get_conversation_stats(session_id)
        total_turns_before = conv_stats.get('total_turns', 0)
        total_tokens_before = conv_stats.get('total_tokens', 0)
        
        # Obtener historial conversacional con sliding window si está habilitado
        if enable_sliding_window:
            # Usar trim_context_to_window para limitar por tokens
            conversation_context = self.conversation_manager.trim_context_to_window(
                session_id=session_id,
                max_tokens=max_context_tokens
            )
            
            # Calcular cuántos turnos se mantuvieron
            turns_in_context = conversation_context.count('Human:')
            turns_removed = total_turns_before // 2 - turns_in_context  # Dividir por 2 porque cada turno tiene user+assistant
            
            self.logger.info(f"🔄 Sliding window aplicado:")
            self.logger.info(f"   • Límite de tokens: {max_context_tokens}")
            self.logger.info(f"   • Turnos totales en conversación: {total_turns_before}")
            self.logger.info(f"   • Turnos mantenidos en contexto: {turns_in_context}")
            self.logger.info(f"   • Turnos eliminados (más antiguos): {turns_removed}")
            self.logger.info(f"   • Tokens antes: {total_tokens_before}, después: ~{len(conversation_context.split())}")
        else:
            # Obtener historial completo (comportamiento anterior)
            conversation_context = self.conversation_manager.get_conversation_context(session_id)
            self.logger.info(f"ℹ️  Sliding window deshabilitado - usando historial completo ({total_turns_before} turnos)")
        
        # Construir historial en formato Bedrock
        conversation_history = self._build_conversation_history(conversation_context)
        
        # IMPORTANTE: El último mensaje del usuario ya está en el historial,
        # pero Bedrock espera que el último mensaje de usuario esté separado
        # Por lo tanto, si hay historial, debemos quitar el último mensaje de usuario
        # y pasarlo como user_input
        if conversation_history and conversation_history[-1]['role'] == 'user':
            # Quitar el último mensaje de usuario del historial
            conversation_history = conversation_history[:-1]
        
        # Crear request
        llm_request = LLMRequest(
            session_id=session_id,
            system_prompt=system_prompt,
            user_input=user_input,
            conversation_history=conversation_history,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            use_cache=True
        )
        
        # Enviar request
        response = self.send_request(llm_request)
        
        # Actualizar historial conversacional con la respuesta del asistente
        self.conversation_manager.add_assistant_turn(
            session_id=session_id,
            response=response.content,
            tools_used=[],
            tokens=response.usage.get('output_tokens', 0)
        )
        
        return response
    
    def _build_conversation_history(self, conversation_context: str) -> List[Dict[str, str]]:
        """
        Construye historial de conversación en formato Bedrock
        
        Args:
            conversation_context: Contexto conversacional formateado
            
        Returns:
            Lista de mensajes en formato Bedrock
        """
        if not conversation_context or not conversation_context.strip():
            return []
        
        # Parsear contexto conversacional buscando prefijos "Human:" y "Assistant:"
        # Esta implementación es más robusta que dividir por \n\n porque los resultados
        # de herramientas pueden contener \n\n internamente
        
        history = []
        current_role = None
        current_content = []
        
        for line in conversation_context.split('\n'):
            if line.startswith('Human:'):
                # Guardar el turno anterior si existe
                if current_role and current_content:
                    history.append({
                        'role': current_role,
                        'content': '\n'.join(current_content).strip()
                    })
                # Iniciar nuevo turno de usuario
                current_role = 'user'
                current_content = [line.replace('Human:', '', 1).strip()]
            elif line.startswith('Assistant:'):
                # Guardar el turno anterior si existe
                if current_role and current_content:
                    history.append({
                        'role': current_role,
                        'content': '\n'.join(current_content).strip()
                    })
                # Iniciar nuevo turno de asistente
                current_role = 'assistant'
                current_content = [line.replace('Assistant:', '', 1).strip()]
            else:
                # Continuar con el contenido del turno actual
                if current_role:
                    current_content.append(line)
        
        # Guardar el último turno
        if current_role and current_content:
            history.append({
                'role': current_role,
                'content': '\n'.join(current_content).strip()
            })
        
        return history
    
    def get_response_summary(self, llm_response: LLMResponse) -> str:
        """
        Genera un resumen de la respuesta del LLM
        
        Args:
            llm_response: Respuesta del LLM
            
        Returns:
            String con resumen formateado
        """
        summary = f"""
╔════════════════════════════════════════════════════════════════╗
║              RESUMEN DE RESPUESTA DEL LLM                      ║
╚════════════════════════════════════════════════════════════════╝

🤖 Modelo: {llm_response.model}
⏱️  Tiempo de ejecución: {llm_response.execution_time_ms:.2f}ms
🛑 Razón de parada: {llm_response.stop_reason}

📊 Uso de Tokens:
  • Input tokens: {llm_response.usage.get('input_tokens', 0)}
  • Output tokens: {llm_response.usage.get('output_tokens', 0)}
  • Total: {llm_response.usage.get('input_tokens', 0) + llm_response.usage.get('output_tokens', 0)}

💾 Cache Stats:
"""
        
        if llm_response.cache_stats:
            cache = llm_response.cache_stats
            summary += f"  • Cache habilitado: {cache.get('cache_enabled', False)}\n"
            summary += f"  • System prompt cacheado: {cache.get('system_prompt_cached', False)}\n"
            summary += f"  • Conversación cacheada: {cache.get('conversation_cached', False)}\n"
            summary += f"  • Tokens ahorrados: {cache.get('tokens_saved', 0)}\n"
        
        summary += f"\n📝 Contenido (primeros 200 caracteres):\n"
        summary += f"  {llm_response.content[:200]}...\n"
        
        return summary


def main():
    """Función principal para testing"""
    import logging
    
    # Configurar logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear comunicador LLM
    llm_comm = LLMCommunication()
    
    # System prompt de ejemplo
    system_prompt = """Eres un asistente especializado en consultas sobre la base de conocimiento Darwin.
Tu objetivo es responder preguntas sobre aspectos funcionales y técnicos del sistema.
Cuando necesites información, solicita el uso de herramientas de búsqueda mediante XML."""
    
    # Crear sesión
    session_id = "test-session-001"
    
    # Enviar request
    print("Enviando request al LLM...")
    try:
        response = llm_comm.send_request_with_conversation(
            session_id=session_id,
            system_prompt=system_prompt,
            user_input="¿Cuáles son los principales módulos de Darwin?"
        )
        
        # Mostrar resumen
        print(llm_comm.get_response_summary(response))
        
        # Mostrar contenido completo
        print("\n📄 Respuesta Completa:")
        print(response.content)
    
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
