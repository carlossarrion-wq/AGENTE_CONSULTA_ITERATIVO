#!/usr/bin/env python3
"""
Script de prueba para verificar que los logs del LLM se vuelquen correctamente
Demuestra el vuelque completo del mensaje enviado al LLM y la respuesta recibida
"""

import logging
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.llm_communication import LLMCommunication, LLMRequest


def setup_logging():
    """Configura el sistema de logging con nivel INFO para ver los vuelques"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('agent.log'),
            logging.StreamHandler()
        ]
    )


def test_llm_logging():
    """Prueba el vuelque de logs del LLM"""
    
    print("\n" + "="*80)
    print("🧪 PRUEBA DE VUELQUE DE LOGS DEL LLM")
    print("="*80 + "\n")
    
    # Configurar logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Iniciando prueba de vuelque de logs del LLM...")
    
    try:
        # Crear comunicador LLM
        llm_comm = LLMCommunication()
        
        # System prompt de ejemplo
        system_prompt = """Eres un asistente especializado en consultas sobre la base de conocimiento Darwin.
Tu objetivo es responder preguntas sobre aspectos funcionales y técnicos del sistema.
Cuando necesites información, solicita el uso de herramientas de búsqueda mediante XML.

INSTRUCCIONES IMPORTANTES:
1. Siempre proporciona respuestas claras y precisas
2. Estructura tus respuestas de forma legible
3. Cita fuentes cuando sea posible
4. Si no tienes información, indícalo claramente"""
        
        # Crear sesión
        session_id = "test-logging-session-001"
        
        # Crear request
        llm_request = LLMRequest(
            session_id=session_id,
            system_prompt=system_prompt,
            user_input="¿Cuáles son los principales módulos de Darwin?",
            conversation_history=[],
            max_tokens=1000,
            temperature=0.1,
            use_cache=True
        )
        
        logger.info(f"\n{'='*80}")
        logger.info("📋 INFORMACIÓN DE LA PRUEBA")
        logger.info(f"{'='*80}")
        logger.info(f"Sesión: {session_id}")
        logger.info(f"Modelo: {llm_comm.model_id}")
        logger.info(f"Max tokens: {llm_request.max_tokens}")
        logger.info(f"Temperature: {llm_request.temperature}")
        logger.info(f"{'='*80}\n")
        
        # Enviar request
        logger.info("Enviando request al LLM...")
        response = llm_comm.send_request(llm_request)
        
        # Mostrar resumen
        logger.info("\n" + llm_comm.get_response_summary(response))
        
        logger.info("\n✅ Prueba completada exitosamente")
        logger.info("📝 Revisa el archivo 'agent.log' para ver el vuelque completo de logs")
        
    except Exception as e:
        logger.error(f"❌ Error en la prueba: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    test_llm_logging()
