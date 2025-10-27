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
from color_utils import (
    llm_request, llm_response, info, error, success, header, dim_text
)


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
    
    def __init__(self, config_path: str = "config/config.yaml", system_prompt_file: str = "config/system_prompt_darwin.txt"):
        """
        Inicializa el módulo de comunicación LLM
        
        Args:
            config_path: Ruta al archivo de configuración principal
            system_prompt_file: Ruta al archivo de texto con el prompt de sistema
        """
        self.config = ConfigManager(config_path)
        self.logger = logging.getLogger(__name__)
        
        # Cargar system prompt desde archivo de texto
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
        
        Args:
            system_prompt_file: Ruta al archivo de texto con el prompt de sistema
            
        Returns:
            String con el prompt de sistema completo
        """
        try:
            prompt_path = Path(system_prompt_file)
            if not prompt_path.exists():
                self.logger.warning(f"Archivo de prompt no encontrado: {system_prompt_file}")
                return self._get_default_system_prompt()
            
            # Leer el contenido del archivo de texto directamente
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt = f.read()
            
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
    
    def send_request(self, llm_request: LLMRequest) -> LLMResponse:
        """
        Envía un request a AWS Bedrock
        
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
        
        # Obtener historial conversacional
        conversation_context = self.conversation_manager.get_conversation_context(session_id)
        
        # Construir historial en formato Bedrock
        conversation_history = self._build_conversation_history(conversation_context)
        
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
        
        # Actualizar historial conversacional
        self.conversation_manager.add_user_turn(
            session_id=session_id,
            message=user_input,
            tokens=len(user_input.split())
        )
        
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
        # Parsear contexto conversacional
        # Formato esperado: "User: mensaje1\nAssistant: respuesta1\nUser: mensaje2\n..."
        
        history = []
        lines = conversation_context.strip().split('\n')
        
        current_role = None
        current_content = []
        
        for line in lines:
            if line.startswith('User:'):
                if current_role and current_content:
                    history.append({
                        'role': 'user' if current_role == 'User' else 'assistant',
                        'content': '\n'.join(current_content).replace(f'{current_role}: ', '', 1)
                    })
                current_role = 'User'
                current_content = [line]
            elif line.startswith('Assistant:'):
                if current_role and current_content:
                    history.append({
                        'role': 'user' if current_role == 'User' else 'assistant',
                        'content': '\n'.join(current_content).replace(f'{current_role}: ', '', 1)
                    })
                current_role = 'Assistant'
                current_content = [line]
            else:
                if current_role:
                    current_content.append(line)
        
        # Agregar último mensaje
        if current_role and current_content:
            history.append({
                'role': 'user' if current_role == 'User' else 'assistant',
                'content': '\n'.join(current_content).replace(f'{current_role}: ', '', 1)
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
