#!/usr/bin/env python3
"""
Script de prueba para verificar la carga condicional de resúmenes

Este script prueba que:
1. Cuando load_summaries=true, se cargan los resúmenes desde S3
2. Cuando load_summaries=false, NO se cargan los resúmenes
3. El encabezado correcto se incluye cuando se cargan los resúmenes
"""

import sys
import os
import logging
from pathlib import Path

# Agregar el directorio src/agent al path
sys.path.insert(0, str(Path(__file__).parent / 'src' / 'agent'))

from llm_communication import LLMCommunication

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_config(config_file: str, expected_load_summaries: bool):
    """
    Prueba la carga de resúmenes con un archivo de configuración específico
    
    Args:
        config_file: Ruta al archivo de configuración
        expected_load_summaries: Valor esperado de load_summaries
    """
    logger.info("="*80)
    logger.info(f"PROBANDO CONFIGURACIÓN: {config_file}")
    logger.info("="*80)
    
    try:
        # Crear instancia de LLMCommunication
        llm_comm = LLMCommunication(config_path=config_file)
        
        # Verificar el valor de load_summaries
        logger.info(f"✓ load_summaries = {llm_comm.load_summaries}")
        
        if llm_comm.load_summaries != expected_load_summaries:
            logger.error(f"✗ ERROR: Se esperaba load_summaries={expected_load_summaries}, pero se obtuvo {llm_comm.load_summaries}")
            return False
        
        # Verificar si s3_loader está inicializado correctamente
        if expected_load_summaries:
            if llm_comm.s3_loader is None:
                logger.error("✗ ERROR: s3_loader debería estar inicializado pero es None")
                return False
            logger.info("✓ s3_loader está inicializado correctamente")
        else:
            if llm_comm.s3_loader is not None:
                logger.error("✗ ERROR: s3_loader NO debería estar inicializado pero no es None")
                return False
            logger.info("✓ s3_loader NO está inicializado (correcto)")
        
        # Verificar el contenido del system prompt
        logger.info(f"✓ System prompt cargado ({len(llm_comm.system_prompt)} caracteres)")
        
        # Verificar si el encabezado está presente
        if expected_load_summaries:
            if "TIENES A TU DISPOSICIÓN LOS SIGUIENTES DOCUMENTOS DE CONTEXTO DEL SISTEMA" in llm_comm.system_prompt:
                logger.info("✓ Encabezado de contexto encontrado en el system prompt")
            else:
                logger.warning("⚠ Encabezado de contexto NO encontrado (puede ser que no haya resúmenes en S3)")
        else:
            if "TIENES A TU DISPOSICIÓN LOS SIGUIENTES DOCUMENTOS DE CONTEXTO DEL SISTEMA" in llm_comm.system_prompt:
                logger.error("✗ ERROR: El encabezado de contexto NO debería estar presente")
                return False
            logger.info("✓ Encabezado de contexto NO presente (correcto)")
        
        logger.info("="*80)
        logger.info(f"✅ PRUEBA EXITOSA PARA: {config_file}")
        logger.info("="*80)
        return True
        
    except Exception as e:
        logger.error(f"✗ ERROR durante la prueba: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Función principal"""
    logger.info("\n" + "="*80)
    logger.info("INICIANDO PRUEBAS DE CARGA CONDICIONAL DE RESÚMENES")
    logger.info("="*80 + "\n")
    
    # Configuraciones a probar
    configs_to_test = [
        ("config/config_darwin.yaml", True),
        ("config/config_sap.yaml", True),
        ("config/config_mulesoft.yaml", True),
        ("config/config_deltasmile.yaml", True),
        ("config/config_saplcorp.yaml", True),
    ]
    
    results = []
    
    for config_file, expected_load_summaries in configs_to_test:
        if not Path(config_file).exists():
            logger.warning(f"⚠ Archivo de configuración no encontrado: {config_file}")
            continue
        
        result = test_config(config_file, expected_load_summaries)
        results.append((config_file, result))
        print("\n")
    
    # Resumen final
    logger.info("\n" + "="*80)
    logger.info("RESUMEN DE PRUEBAS")
    logger.info("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for config_file, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        logger.info(f"{status}: {config_file}")
    
    logger.info("="*80)
    logger.info(f"RESULTADO FINAL: {passed}/{total} pruebas pasaron")
    logger.info("="*80)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
