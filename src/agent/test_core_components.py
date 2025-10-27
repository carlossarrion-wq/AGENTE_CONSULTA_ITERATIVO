"""
Test de componentes core del agente

Valida el funcionamiento de:
- Prompt Cache Manager
- Conversation Manager
- Config Manager
"""

import sys
import logging
from prompt_cache_manager import PromptCacheManager
from conversation_manager import ConversationManager
from config_manager import ConfigManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_config_manager():
    """Probar Config Manager"""
    logger.info("=" * 60)
    logger.info("PRUEBA: Config Manager")
    logger.info("=" * 60)

    config = ConfigManager()
    
    # Validar configuración
    if not config.validate():
        logger.error("Configuración inválida")
        return False

    # Obtener valores
    logger.info(f"OpenSearch Host: {config.get('opensearch.host')}")
    logger.info(f"LLM Model: {config.get('llm.model_id')}")
    logger.info(f"Prompt Caching Enabled: {config.get('prompt_caching.enabled')}")

    # Obtener sección completa
    llm_config = config.get_section("llm")
    logger.info(f"LLM Config: {llm_config}")

    logger.info("✓ Config Manager OK\n")
    return True


def test_prompt_cache_manager():
    """Probar Prompt Cache Manager"""
    logger.info("=" * 60)
    logger.info("PRUEBA: Prompt Cache Manager")
    logger.info("=" * 60)

    config = ConfigManager()
    cache_config = config.get_section("prompt_caching")
    cache_manager = PromptCacheManager(cache_config)

    # Test 1: Cachear system prompt
    system_prompt = "Eres un agente especializado en consultas sobre la base de conocimiento Darwin..."
    prompt_hash = cache_manager.cache_system_prompt(system_prompt)
    logger.info(f"System prompt cacheado: {prompt_hash[:16]}...")

    # Test 2: Crear cache conversacional
    session_id = "test-session-001"
    cache_manager.update_conversation_cache(
        session_id,
        prompt_hash,
        {
            "role": "user",
            "content": "¿Cómo configurar OAuth?",
            "tokens": 25,
        }
    )
    logger.info(f"Turno usuario agregado a sesión {session_id}")

    # Test 3: Obtener cache
    cache = cache_manager.get_cached_conversation(session_id)
    if cache:
        logger.info(f"Cache recuperado: {len(cache.turns)} turnos, {cache.total_tokens} tokens")
    else:
        logger.error("No se pudo recuperar cache")
        return False

    # Test 4: Construir prompt incremental
    incremental_prompt = cache_manager.build_incremental_prompt(
        session_id,
        system_prompt,
        "¿Hay ejemplos de código?"
    )
    logger.info(f"Prompt incremental construido: {len(incremental_prompt)} caracteres")

    # Test 5: Estadísticas
    stats = cache_manager.get_cache_stats()
    logger.info(f"Estadísticas: {stats}")

    logger.info("✓ Prompt Cache Manager OK\n")
    return True


def test_conversation_manager():
    """Probar Conversation Manager"""
    logger.info("=" * 60)
    logger.info("PRUEBA: Conversation Manager")
    logger.info("=" * 60)

    config = ConfigManager()
    conv_config = config.get_section("conversation")
    conv_manager = ConversationManager(conv_config)

    # Test 1: Crear conversación
    session_id = conv_manager.create_conversation()
    logger.info(f"Conversación creada: {session_id}")

    # Test 2: Agregar turno del usuario
    conv_manager.add_user_turn(session_id, "¿Cómo configurar OAuth en aplicaciones web?")
    logger.info("Turno usuario agregado")

    # Test 3: Agregar turno del asistente
    conv_manager.add_assistant_turn(
        session_id,
        "Voy a buscar información sobre OAuth...",
        tools_used=["SEMANTIC_SEARCH"],
        tool_results={"SEMANTIC_SEARCH": {"results": 5}}
    )
    logger.info("Turno asistente agregado")

    # Test 4: Obtener contexto
    context = conv_manager.get_conversation_context(session_id)
    logger.info(f"Contexto conversacional:\n{context}\n")

    # Test 5: Estadísticas
    stats = conv_manager.get_conversation_stats(session_id)
    logger.info(f"Estadísticas: {stats}")

    # Test 6: Token count
    token_count = conv_manager.get_token_count(session_id)
    logger.info(f"Total tokens: {token_count}")

    logger.info("✓ Conversation Manager OK\n")
    return True


def test_integration():
    """Probar integración de componentes"""
    logger.info("=" * 60)
    logger.info("PRUEBA: Integración de componentes")
    logger.info("=" * 60)

    config = ConfigManager()
    cache_manager = PromptCacheManager(config.get_section("prompt_caching"))
    conv_manager = ConversationManager(config.get_section("conversation"))

    # Simular flujo de conversación
    system_prompt = "Eres un agente especializado en consultas sobre la base de conocimiento Darwin..."
    prompt_hash = cache_manager.cache_system_prompt(system_prompt)

    session_id = conv_manager.create_conversation()
    logger.info(f"Sesión iniciada: {session_id}")

    # Turno 1
    user_input_1 = "¿Cómo configurar OAuth?"
    conv_manager.add_user_turn(session_id, user_input_1)
    cache_manager.update_conversation_cache(
        session_id, prompt_hash, {"role": "user", "content": user_input_1, "tokens": 25}
    )

    assistant_response_1 = "Voy a buscar información sobre OAuth..."
    conv_manager.add_assistant_turn(session_id, assistant_response_1, tools_used=["SEMANTIC_SEARCH"])
    cache_manager.update_conversation_cache(
        session_id, prompt_hash, {"role": "assistant", "content": assistant_response_1, "tokens": 50}
    )

    # Turno 2
    user_input_2 = "¿Hay ejemplos de código?"
    conv_manager.add_user_turn(session_id, user_input_2)
    cache_manager.update_conversation_cache(
        session_id, prompt_hash, {"role": "user", "content": user_input_2, "tokens": 20}
    )

    # Construir prompt optimizado
    optimized_prompt = cache_manager.build_incremental_prompt(
        session_id, system_prompt, user_input_2
    )

    logger.info(f"Prompt optimizado construido: {len(optimized_prompt)} caracteres")
    logger.info(f"Conversación: {len(conv_manager.get_conversation_context(session_id))} caracteres")

    # Estadísticas finales
    cache_stats = cache_manager.get_cache_stats()
    conv_stats = conv_manager.get_conversation_stats(session_id)

    logger.info(f"Cache stats: {cache_stats}")
    logger.info(f"Conversation stats: {conv_stats}")

    logger.info("✓ Integración OK\n")
    return True


def main():
    """Ejecutar todas las pruebas"""
    logger.info("\n" + "=" * 60)
    logger.info("INICIANDO PRUEBAS DE COMPONENTES CORE")
    logger.info("=" * 60 + "\n")

    results = []

    try:
        results.append(("Config Manager", test_config_manager()))
    except Exception as e:
        logger.error(f"Error en Config Manager: {e}")
        results.append(("Config Manager", False))

    try:
        results.append(("Prompt Cache Manager", test_prompt_cache_manager()))
    except Exception as e:
        logger.error(f"Error en Prompt Cache Manager: {e}")
        results.append(("Prompt Cache Manager", False))

    try:
        results.append(("Conversation Manager", test_conversation_manager()))
    except Exception as e:
        logger.error(f"Error en Conversation Manager: {e}")
        results.append(("Conversation Manager", False))

    try:
        results.append(("Integración", test_integration()))
    except Exception as e:
        logger.error(f"Error en Integración: {e}")
        results.append(("Integración", False))

    # Resumen
    logger.info("=" * 60)
    logger.info("RESUMEN DE PRUEBAS")
    logger.info("=" * 60)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{test_name}: {status}")

    all_passed = all(result for _, result in results)
    logger.info("=" * 60)

    if all_passed:
        logger.info("✓ TODAS LAS PRUEBAS PASARON")
        return 0
    else:
        logger.error("✗ ALGUNAS PRUEBAS FALLARON")
        return 1


if __name__ == "__main__":
    sys.exit(main())
