"""
Punto de entrada principal del Agente IA de Consulta Darwin

Ejecuta la interfaz de chat interactiva para consultar la base de conocimiento Darwin
"""

import logging
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.chat_interface import ChatInterface


def setup_logging():
    """Configura el sistema de logging"""
    # Configurar el logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Crear directorio logs si no existe
    logs_dir = Path(__file__).parent.parent.parent / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Handler para archivo: TODO el detalle (DEBUG level)
    log_file = logs_dir / 'agent.log'
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Handler para consola: solo mensajes WARNING y superiores (errores críticos)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Agregar handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def main():
    """Función principal"""
    # Configurar logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("="*64)
    logger.info("Iniciando Agente IA de Consulta Darwin")
    logger.info("="*64)
    logger.info("System prompt se cargará desde config/system_prompt.yaml")
    
    try:
        # Crear interfaz de chat (sin pasar system_prompt, se cargará desde configuración)
        chat = ChatInterface()
        
        # Ejecutar en modo interactivo
        chat.run_interactive()
        
        logger.info("Agente finalizado correctamente")
    
    except KeyboardInterrupt:
        logger.info("Agente interrumpido por el usuario")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Error fatal: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
