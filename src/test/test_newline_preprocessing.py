#!/usr/bin/env python3
"""
Test de preprocesamiento de saltos de línea consecutivos en streaming

Este script prueba que la máquina de estados elimina correctamente
los saltos de línea consecutivos (\n\n -> \n) durante el streaming.
"""

import sys
import os

# Agregar el directorio padre al path para importar módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent'))

from streaming_state_machine import StreamingStateMachine, StreamState
from streaming_display import StreamingDisplay


def test_newline_preprocessing():
    """
    Prueba el preprocesamiento de saltos de línea consecutivos
    """
    print("=" * 80)
    print("TEST: Preprocesamiento de saltos de línea consecutivos")
    print("=" * 80)
    
    # Crear display (sin colores para facilitar la verificación)
    display = StreamingDisplay(enable_colors=False)
    
    # Crear máquina de estados
    machine = StreamingStateMachine(display)
    
    # Caso 1: Texto con múltiples \n\n consecutivos
    print("\n📝 Caso 1: Texto con múltiples \\n\\n")
    print("-" * 80)
    
    test_text_1 = "Línea 1\n\nLínea 2\n\n\nLínea 3\n\n\n\nLínea 4"
    
    print(f"Input: {repr(test_text_1)}")
    
    # Alimentar tokens
    for char in test_text_1:
        machine.feed_token(char)
    
    accumulated = machine.get_accumulated_text()
    print(f"Output: {repr(accumulated)}")
    
    # Verificar que \n\n se convirtió en \n
    expected = "Línea 1\nLínea 2\nLínea 3\nLínea 4"
    if accumulated == expected:
        print("✅ PASS: Los saltos de línea consecutivos se eliminaron correctamente")
    else:
        print(f"❌ FAIL: Esperado {repr(expected)}, obtenido {repr(accumulated)}")
    
    # Caso 2: Texto dentro de bloques <thinking>
    print("\n📝 Caso 2: Texto con \\n\\n dentro de <thinking>")
    print("-" * 80)
    
    # Reiniciar máquina
    display2 = StreamingDisplay(enable_colors=False)
    machine2 = StreamingStateMachine(display2)
    
    test_text_2 = "<thinking>\nPrimera línea\n\nSegunda línea\n\n\nTercera línea\n</thinking>"
    
    print(f"Input: {repr(test_text_2)}")
    
    # Alimentar tokens
    for char in test_text_2:
        machine2.feed_token(char)
    
    accumulated2 = machine2.get_accumulated_text()
    print(f"Output: {repr(accumulated2)}")
    
    # Verificar que \n\n se convirtió en \n dentro del bloque
    expected2 = "<thinking>\nPrimera línea\nSegunda línea\nTercera línea\n</thinking>"
    if accumulated2 == expected2:
        print("✅ PASS: Los saltos de línea consecutivos dentro de <thinking> se eliminaron correctamente")
    else:
        print(f"❌ FAIL: Esperado {repr(expected2)}, obtenido {repr(accumulated2)}")
    
    # Caso 3: Texto dentro de bloques <present_answer>
    print("\n📝 Caso 3: Texto con \\n\\n dentro de <present_answer>")
    print("-" * 80)
    
    # Reiniciar máquina
    display3 = StreamingDisplay(enable_colors=False)
    machine3 = StreamingStateMachine(display3)
    
    test_text_3 = "<present_answer>\nRespuesta línea 1\n\nRespuesta línea 2\n\n\nRespuesta línea 3\n</present_answer>"
    
    print(f"Input: {repr(test_text_3)}")
    
    # Alimentar tokens
    for char in test_text_3:
        machine3.feed_token(char)
    
    accumulated3 = machine3.get_accumulated_text()
    print(f"Output: {repr(accumulated3)}")
    
    # Verificar que \n\n se convirtió en \n dentro del bloque
    expected3 = "<present_answer>\nRespuesta línea 1\nRespuesta línea 2\nRespuesta línea 3\n</present_answer>"
    if accumulated3 == expected3:
        print("✅ PASS: Los saltos de línea consecutivos dentro de <present_answer> se eliminaron correctamente")
    else:
        print(f"❌ FAIL: Esperado {repr(expected3)}, obtenido {repr(accumulated3)}")
    
    # Caso 4: Mantener un solo \n
    print("\n📝 Caso 4: Mantener un solo \\n (no debe eliminarse)")
    print("-" * 80)
    
    # Reiniciar máquina
    display4 = StreamingDisplay(enable_colors=False)
    machine4 = StreamingStateMachine(display4)
    
    test_text_4 = "Línea 1\nLínea 2\nLínea 3"
    
    print(f"Input: {repr(test_text_4)}")
    
    # Alimentar tokens
    for char in test_text_4:
        machine4.feed_token(char)
    
    accumulated4 = machine4.get_accumulated_text()
    print(f"Output: {repr(accumulated4)}")
    
    # Verificar que un solo \n se mantiene
    expected4 = "Línea 1\nLínea 2\nLínea 3"
    if accumulated4 == expected4:
        print("✅ PASS: Un solo \\n se mantiene correctamente")
    else:
        print(f"❌ FAIL: Esperado {repr(expected4)}, obtenido {repr(accumulated4)}")
    
    # Caso 5: Streaming token por token (simulación real)
    print("\n📝 Caso 5: Streaming token por token (simulación real)")
    print("-" * 80)
    
    # Reiniciar máquina
    display5 = StreamingDisplay(enable_colors=False)
    machine5 = StreamingStateMachine(display5)
    
    # Simular que los tokens llegan de a uno
    tokens = ["Hola", " ", "mundo", "\n", "\n", "Segunda", " ", "línea", "\n", "\n", "\n", "Tercera", " ", "línea"]
    
    print(f"Input tokens: {tokens}")
    
    # Alimentar tokens uno por uno
    for token in tokens:
        machine5.feed_token(token)
    
    accumulated5 = machine5.get_accumulated_text()
    print(f"Output: {repr(accumulated5)}")
    
    # Verificar resultado
    expected5 = "Hola mundo\nSegunda línea\nTercera línea"
    if accumulated5 == expected5:
        print("✅ PASS: Streaming token por token funciona correctamente")
    else:
        print(f"❌ FAIL: Esperado {repr(expected5)}, obtenido {repr(accumulated5)}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETADO")
    print("=" * 80)


if __name__ == "__main__":
    test_newline_preprocessing()
