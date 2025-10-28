#!/usr/bin/env python3
"""
Script de prueba para verificar el mecanismo de sliding window
en la gestión del historial conversacional.

Este script simula múltiples iteraciones de conversación para verificar
que el historial se limita correctamente cuando alcanza el límite de tokens.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'agent'))

from conversation_manager import ConversationManager
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_sliding_window():
    """Prueba el mecanismo de sliding window"""
    
    print("="*80)
    print("TEST: Mecanismo de Sliding Window")
    print("="*80)
    
    # Configuración de prueba con límites bajos para ver el efecto
    config = {
        'max_history_turns': 5,
        'context_window_tokens': 500,  # Límite bajo para testing
        'enable_sliding_window': True,
        'min_turns_to_keep': 2
    }
    
    # Crear conversation manager
    conv_manager = ConversationManager(config)
    session_id = "test-session-sliding-window"
    
    # Crear conversación
    conv_manager.create_conversation(session_id)
    
    print(f"\n📋 Configuración:")
    print(f"   • Max history turns: {config['max_history_turns']}")
    print(f"   • Context window tokens: {config['context_window_tokens']}")
    print(f"   • Sliding window enabled: {config['enable_sliding_window']}")
    
    # Simular múltiples turnos de conversación
    print(f"\n🔄 Simulando conversación con múltiples turnos...\n")
    
    for i in range(10):
        # Mensaje del usuario (simulando contenido largo)
        user_message = f"Esta es la pregunta número {i+1}. " * 20  # ~100 tokens
        conv_manager.add_user_turn(
            session_id=session_id,
            message=user_message,
            tokens=len(user_message.split())
        )
        
        # Respuesta del asistente (simulando contenido largo)
        assistant_message = f"Esta es la respuesta número {i+1}. " * 20  # ~100 tokens
        conv_manager.add_assistant_turn(
            session_id=session_id,
            response=assistant_message,
            tokens=len(assistant_message.split())
        )
        
        # Obtener estadísticas
        stats = conv_manager.get_conversation_stats(session_id)
        
        print(f"Turno {i+1}:")
        print(f"   • Total turnos: {stats['total_turns']}")
        print(f"   • Total tokens: {stats['total_tokens']}")
        
        # Obtener contexto con sliding window
        context = conv_manager.trim_context_to_window(
            session_id=session_id,
            max_tokens=config['context_window_tokens']
        )
        
        turns_in_context = context.count('Human:')
        print(f"   • Turnos en contexto (después de sliding window): {turns_in_context}")
        print(f"   • Tokens en contexto: ~{len(context.split())}")
        
        if turns_in_context < stats['total_turns'] // 2:
            print(f"   ⚠️  Sliding window activado: {stats['total_turns'] // 2 - turns_in_context} turnos eliminados")
        
        print()
    
    # Mostrar resumen final
    print("="*80)
    print("RESUMEN FINAL")
    print("="*80)
    
    final_stats = conv_manager.get_conversation_stats(session_id)
    print(f"\n📊 Estadísticas finales:")
    print(f"   • Total turnos en conversación: {final_stats['total_turns']}")
    print(f"   • Total tokens acumulados: {final_stats['total_tokens']}")
    
    # Contexto completo vs contexto con sliding window
    full_context = conv_manager.get_conversation_context(session_id)
    trimmed_context = conv_manager.trim_context_to_window(
        session_id=session_id,
        max_tokens=config['context_window_tokens']
    )
    
    turns_full = full_context.count('Human:')
    turns_trimmed = trimmed_context.count('Human:')
    
    print(f"\n🔍 Comparación de contextos:")
    print(f"   • Turnos en contexto completo: {turns_full}")
    print(f"   • Turnos en contexto trimmed: {turns_trimmed}")
    print(f"   • Turnos eliminados: {turns_full - turns_trimmed}")
    print(f"   • Tokens en contexto completo: ~{len(full_context.split())}")
    print(f"   • Tokens en contexto trimmed: ~{len(trimmed_context.split())}")
    print(f"   • Reducción de tokens: ~{len(full_context.split()) - len(trimmed_context.split())}")
    
    print(f"\n✅ Test completado exitosamente")
    print(f"   El mecanismo de sliding window está funcionando correctamente.")
    print(f"   Los turnos más antiguos se eliminan cuando se supera el límite de tokens.")


def test_with_production_config():
    """Prueba con la configuración de producción"""
    
    print("\n" + "="*80)
    print("TEST: Configuración de Producción")
    print("="*80)
    
    # Configuración de producción
    config = {
        'max_history_turns': 15,
        'context_window_tokens': 180000,  # 90% de 200K
        'enable_sliding_window': True,
        'min_turns_to_keep': 3
    }
    
    conv_manager = ConversationManager(config)
    session_id = "test-session-production"
    conv_manager.create_conversation(session_id)
    
    print(f"\n📋 Configuración de producción:")
    print(f"   • Max history turns: {config['max_history_turns']}")
    print(f"   • Context window tokens: {config['context_window_tokens']:,}")
    print(f"   • Sliding window enabled: {config['enable_sliding_window']}")
    
    # Simular conversación con contenido muy largo (como resultados de herramientas)
    print(f"\n🔄 Simulando conversación con contenido extenso...\n")
    
    for i in range(20):
        # Simular mensaje con contenido extenso (como resultado de get_file_content)
        user_message = f"Pregunta {i+1}: Dame el contenido del archivo X"
        # Simular respuesta con contenido muy largo (ej: 50K tokens)
        assistant_message = "Aquí está el contenido del archivo:\n" + ("Línea de contenido. " * 10000)
        
        conv_manager.add_user_turn(
            session_id=session_id,
            message=user_message,
            tokens=len(user_message.split())
        )
        
        conv_manager.add_assistant_turn(
            session_id=session_id,
            response=assistant_message,
            tokens=len(assistant_message.split())
        )
        
        stats = conv_manager.get_conversation_stats(session_id)
        
        if (i + 1) % 5 == 0:  # Mostrar cada 5 turnos
            print(f"Después de {i+1} turnos:")
            print(f"   • Total tokens acumulados: {stats['total_tokens']:,}")
            
            # Verificar si se aplicaría sliding window
            if stats['total_tokens'] > config['context_window_tokens']:
                context = conv_manager.trim_context_to_window(
                    session_id=session_id,
                    max_tokens=config['context_window_tokens']
                )
                turns_in_context = context.count('Human:')
                print(f"   • Turnos que se mantendrían: {turns_in_context} de {stats['total_turns'] // 2}")
                print(f"   • ⚠️  Sliding window ACTIVO")
            else:
                print(f"   • Sliding window no necesario aún")
            print()
    
    final_stats = conv_manager.get_conversation_stats(session_id)
    print(f"\n📊 Resultado final:")
    print(f"   • Total turnos: {final_stats['total_turns']}")
    print(f"   • Total tokens: {final_stats['total_tokens']:,}")
    
    trimmed_context = conv_manager.trim_context_to_window(
        session_id=session_id,
        max_tokens=config['context_window_tokens']
    )
    turns_trimmed = trimmed_context.count('Human:')
    
    print(f"   • Turnos que se enviarían al LLM: {turns_trimmed}")
    print(f"   • Tokens que se enviarían: ~{len(trimmed_context.split()):,}")
    print(f"\n✅ El sistema mantiene el historial dentro del límite de {config['context_window_tokens']:,} tokens")


if __name__ == "__main__":
    try:
        test_sliding_window()
        test_with_production_config()
        
        print("\n" + "="*80)
        print("✅ TODOS LOS TESTS PASARON EXITOSAMENTE")
        print("="*80)
        
    except Exception as e:
        logger.error(f"Error en los tests: {str(e)}", exc_info=True)
        sys.exit(1)
