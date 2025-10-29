"""
Punto de entrada principal del Agente IA de Consulta Multi-Aplicación

Ejecuta la interfaz de chat interactiva para consultar bases de conocimiento
de diferentes aplicaciones (Darwin, SAP, MuleSoft, etc.)

Uso:
    python3 src/agent/main.py --app darwin
    python3 src/agent/main.py --app sap
    python3 src/agent/main.py --app mulesoft
"""

import logging
import sys
import argparse
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.chat_interface import ChatInterface


# Aplicaciones soportadas y sus configuraciones
SUPPORTED_APPS = {
    'darwin': {
        'name': 'Darwin',
        'config_file': 'config/config_darwin.yaml',
        'system_prompt': 'config/system_prompt_darwin.md',
        'description': 'Sistema Darwin - Gestión de clientes y contratos'
    },
    'sap': {
        'name': 'SAP',
        'config_file': 'config/config_sap.yaml',
        'system_prompt': 'config/system_prompt_sap.md',
        'description': 'Sistema SAP - ERP empresarial'
    },
    'mulesoft': {
        'name': 'MuleSoft',
        'config_file': 'config/config_mulesoft.yaml',
        'system_prompt': 'config/system_prompt_mulesoft.md',
        'description': 'MuleSoft - Plataforma de integración'
    }
}


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


def parse_arguments():
    """Parsear argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description='Agente IA de Consulta Multi-Aplicación',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Aplicaciones soportadas:
{chr(10).join(f"  {app}: {info['description']}" for app, info in SUPPORTED_APPS.items())}

Ejemplos:
  python3 src/agent/main.py --app darwin
  python3 src/agent/main.py --app sap
  python3 src/agent/main.py --app mulesoft
        """
    )
    
    parser.add_argument(
        '--app',
        type=str,
        choices=list(SUPPORTED_APPS.keys()),
        default='darwin',
        help='Aplicación a consultar (default: darwin)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Ruta personalizada al archivo de configuración (opcional)'
    )
    
    parser.add_argument(
        '--system-prompt',
        type=str,
        help='Ruta personalizada al system prompt (opcional)'
    )
    
    return parser.parse_args()


def validate_app_config(app_name: str, config_file: str, system_prompt: str) -> bool:
    """
    Validar que existan los archivos de configuración para la aplicación
    
    Args:
        app_name: Nombre de la aplicación
        config_file: Ruta al archivo de configuración
        system_prompt: Ruta al system prompt
        
    Returns:
        True si la configuración es válida
    """
    logger = logging.getLogger(__name__)
    
    # Verificar archivo de configuración
    if not Path(config_file).exists():
        logger.error(f"Archivo de configuración no encontrado: {config_file}")
        logger.info(f"Crea el archivo {config_file} basándote en config/config_darwin.yaml")
        return False
    
    # Verificar system prompt
    if not Path(system_prompt).exists():
        logger.error(f"System prompt no encontrado: {system_prompt}")
        logger.info(f"Crea el archivo {system_prompt} basándote en config/system_prompt_darwin.md")
        return False
    
    return True


def main():
    """Función principal"""
    # Configurar logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Parsear argumentos
    args = parse_arguments()
    
    # Obtener configuración de la aplicación
    app_config = SUPPORTED_APPS[args.app]
    app_name = app_config['name']
    
    # Usar rutas personalizadas si se proporcionan, sino usar las por defecto
    config_file = args.config or app_config['config_file']
    system_prompt = args.system_prompt or app_config['system_prompt']
    
    logger.info("="*64)
    logger.info(f"Iniciando Agente IA de Consulta - {app_name}")
    logger.info("="*64)
    logger.info(f"Aplicación: {args.app}")
    logger.info(f"Configuración: {config_file}")
    logger.info(f"System Prompt: {system_prompt}")
    
    # Validar configuración
    if not validate_app_config(args.app, config_file, system_prompt):
        logger.error(f"Configuración inválida para aplicación '{args.app}'")
        sys.exit(1)
    
    try:
        # Crear interfaz de chat con configuración específica de la aplicación
        chat = ChatInterface(
            config_path=config_file,
            app_name=app_name
        )
        
        # Mostrar mensaje de bienvenida personalizado
        print(f"\n{'='*64}")
        print(f"  Agente IA de Consulta - {app_name}")
        print(f"  {app_config['description']}")
        print(f"{'='*64}\n")
        
        # Ejecutar en modo interactivo
        chat.run_interactive()
        
        logger.info("Agente finalizado correctamente")
    
    except KeyboardInterrupt:
        logger.info("Agente interrumpido por el usuario")
        print("\n\n¡Hasta pronto!")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Error fatal: {str(e)}", exc_info=True)
        print(f"\n❌ Error fatal: {str(e)}")
        print("Revisa los logs en logs/agent.log para más detalles")
        sys.exit(1)


if __name__ == "__main__":
    main()
