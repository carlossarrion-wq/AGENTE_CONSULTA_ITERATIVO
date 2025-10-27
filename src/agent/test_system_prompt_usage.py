"""
Script de prueba para verificar que el system prompt desde JSON se usa correctamente

Este script verifica que:
1. El prompt se carga desde config/system_prompt_full.json
2. El prompt completo se envía al LLM
3. Los logs muestran el prompt completo
"""

import logging
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.llm_communication import LLMCommunication
from agent.request_handler import RequestHandler


def setup_logging():
    """Configura logging detallado"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
