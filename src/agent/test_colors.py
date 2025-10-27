#!/usr/bin/env python3
"""
Script de prueba para verificar la implementación de colores en el agente
"""

import sys
import os

# Agregar el directorio padre al path para importar los módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from color_utils import (
    user_text, llm_request, llm_response, tool_result,
    info, warning, error, success, header, dim_text,
    format_user_input_section, format_llm_request_section,
    format_llm_response_section, format_tool_result_section,
    format_metrics_section, Colors
)


def test_basic_colors():
    """Prueba los colores básicos"""
    print("\n" + "="*80)
    print("PRUEBA DE COLORES BÁSICOS")
    print("="*80 + "\n")
    
    print(user_text("👤 Texto del usuario (negro)"))
    print(llm_request("📤 Texto de request al LLM (azul)"))
    print(llm_response("📥 Texto de respuesta del LLM (verde)"))
    print(tool_result("🔧 Texto de resultado de herramientas (rojo)"))
    print()


def test_helper_colors():
    """Prueba los colores auxiliares"""
    print("\n" + "="*80)
    print("PRUEBA DE COLORES AUXILIARES")
    print("="*80 + "\n")
    
    print(info("ℹ️  Mensaje informativo (cian)"))
    print(warning("⚠️  Mensaje de advertencia (amarillo)"))
    print(error("❌ Mensaje de error (rojo brillante)"))
    print(success("✅ Mensaje de éxito (verde brillante)"))
    print(header("📋 Encabezado (negrita)"))
    print(dim_text("Texto atenuado (gris)"))
    print()


def test_formatted_sections():
    """Prueba las secciones formateadas"""
    print("\n" + "="*80)
    print("PRUEBA DE SECCIONES FORMATEADAS")
    print("="*80 + "\n")
    
    # Sección de input del usuario
    print(format_user_input_section("¿Cuáles son los principales módulos de Darwin?"))
    
    # Sección de request al LLM
    print(format_llm_request_section(
        system_prompt="Eres un asistente especializado...",
        user_input="¿Cuáles son los principales módulos de Darwin?",
        conversation_history=["User: Hola", "Assistant: Hola, ¿en qué puedo ayudarte?"]
    ))
    
    # Sección de respuesta del LLM
    print(format_llm_response_section(
        content="Los principales módulos de Darwin son...",
        model="claude-haiku-4-5",
        tokens_input=150,
        tokens_output=200,
        execution_time_ms=1234.56
    ))
    
    # Sección de resultado de herramientas
    print(format_tool_result_section(
        tool_name="semantic_search",
        success=True,
        execution_time_ms=567.89,
        result_data={"fragments": [{"file_name": "test.md", "content": "contenido..."}]}
    ))
    
    # Sección de métricas
    print(format_metrics_section(
        total_time_ms=2500.0,
        llm_time_ms=1500.0,
        tools_time_ms=800.0,
        tokens_input=150,
        tokens_output=200,
        cache_tokens_saved=50,
        tools_executed=2,
        tools_successful=2
    ))


def test_color_toggle():
    """Prueba el toggle de colores"""
    print("\n" + "="*80)
    print("PRUEBA DE TOGGLE DE COLORES")
    print("="*80 + "\n")
    
    print("Colores habilitados:")
    print(user_text("Texto del usuario"))
    print(llm_response("Respuesta del LLM"))
    print(tool_result("Resultado de herramienta"))
    
    print("\nDeshabilitando colores...")
    Colors.disable()
    
    print("\nColores deshabilitados:")
    print(user_text("Texto del usuario"))
    print(llm_response("Respuesta del LLM"))
    print(tool_result("Resultado de herramienta"))
    
    print("\nHabilitando colores nuevamente...")
    Colors.enable()
    
    print("\nColores habilitados:")
    print(user_text("Texto del usuario"))
    print(llm_response("Respuesta del LLM"))
    print(tool_result("Resultado de herramienta"))
    print()


def test_mixed_content():
    """Prueba contenido mixto simulando una conversación real"""
    print("\n" + "="*80)
    print("SIMULACIÓN DE CONVERSACIÓN CON COLORES")
    print("="*80 + "\n")
    
    # Usuario hace una pregunta
    print(header("👤 USUARIO:"))
    print(user_text("¿Cuáles son los principales módulos de Darwin?"))
    print()
    
    # Sistema envía request al LLM
    print(header("📤 ENVIANDO AL LLM:"))
    print(llm_request("System: Eres un asistente especializado..."))
    print(llm_request("User: ¿Cuáles son los principales módulos de Darwin?"))
    print()
    
    # LLM solicita herramientas
    print(header("📥 RESPUESTA DEL LLM:"))
    print(llm_response("Para responder tu pregunta, necesito buscar información."))
    print(llm_response("<semantic_search>"))
    print(llm_response("  <query>módulos principales Darwin</query>"))
    print(llm_response("</semantic_search>"))
    print()
    
    # Ejecución de herramientas
    print(header("🔧 EJECUTANDO HERRAMIENTAS:"))
    print(tool_result("Herramienta: semantic_search"))
    print(tool_result("Estado: ✅ Exitosa"))
    print(tool_result("Tiempo: 567.89ms"))
    print(tool_result("Resultados: 5 fragmentos encontrados"))
    print()
    
    # Respuesta final del LLM
    print(header("📥 RESPUESTA FINAL DEL LLM:"))
    print(llm_response("Los principales módulos de Darwin son:"))
    print(llm_response("1. Módulo de Gestión de Usuarios"))
    print(llm_response("2. Módulo de Procesamiento de Datos"))
    print(llm_response("3. Módulo de Reportes"))
    print()
    
    # Métricas
    print(header("📊 MÉTRICAS:"))
    print(info(f"⏱️  Tiempo total: 2500.00ms"))
    print(info(f"🤖 Tiempo LLM: 1500.00ms"))
    print(info(f"🔧 Tiempo herramientas: 800.00ms"))
    print(success(f"✅ Procesamiento completado exitosamente"))
    print()


def main():
    """Función principal"""
    print("\n" + "="*80)
    print("PRUEBA DE IMPLEMENTACIÓN DE COLORES EN EL AGENTE")
    print("="*80)
    
    try:
        test_basic_colors()
        test_helper_colors()
        test_formatted_sections()
        test_color_toggle()
        test_mixed_content()
        
        print("\n" + "="*80)
        print(success("✅ TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE"))
        print("="*80 + "\n")
        
    except Exception as e:
        print("\n" + "="*80)
        print(error(f"❌ ERROR EN LAS PRUEBAS: {str(e)}"))
        print("="*80 + "\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
