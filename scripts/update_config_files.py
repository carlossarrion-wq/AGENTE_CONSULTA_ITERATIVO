#!/usr/bin/env python3
"""Script para actualizar archivos de configuración con settings de ingestión"""

import yaml
import sys

# Configuración por aplicación
APP_CONFIGS = {
    'sap': {
        'name': 'SAP System',
        'description': 'Sistema SAP empresarial',
        'bucket': 'rag-system-sap-eu-west-1',
        'prefix': 'applications/sap/'
    },
    'saplcorp': {
        'name': 'SAPLCORP System',
        'description': 'Sistema SAP LCS',
        'bucket': 'rag-system-saplcorp-eu-west-1',
        'prefix': 'documents/'
    },
    'deltasmile': {
        'name': 'DeltaSmile System',
        'description': 'Sistema de gestión dental DeltaSmile',
        'bucket': 'rag-system-deltasmile-eu-west-1',
        'prefix': 'applications/deltasmile/'
    }
}

def update_config_file(app_name):
    """Actualizar archivo de configuración para una aplicación"""
    config_file = f'config/config_{app_name}.yaml'
    app_config = APP_CONFIGS[app_name]
    
    try:
        # Leer archivo existente
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Actualizar Bedrock con configuración de resúmenes
        if 'bedrock' in config:
            config['bedrock']['llm_model'] = 'eu.anthropic.claude-3-haiku-20240307-v1:0'
            config['bedrock']['max_tokens'] = 500
            config['bedrock']['temperature'] = 0.3
            config['bedrock']['top_p'] = 0.9
        
        # Actualizar S3 con prefijos
        if 's3' in config:
            prefix = app_config['prefix']
            config['s3']['documents_prefix'] = f"{prefix}documents/"
            config['s3']['summaries_prefix'] = f"{prefix}summaries/"
            config['s3']['inventory_prefix'] = f"{prefix}inventory/"
        
        # Agregar configuración de chunking
        config['chunking'] = {
            'chunk_size': 6000,
            'chunk_overlap': 600
        }
        
        # Agregar información de aplicación
        config['application'] = {
            'name': app_config['name'],
            'description': app_config['description']
        }
        
        # Guardar archivo actualizado
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        print(f"✅ {config_file} actualizado correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error actualizando {config_file}: {e}")
        return False

def main():
    print("🔄 Actualizando archivos de configuración...")
    
    success_count = 0
    for app_name in APP_CONFIGS.keys():
        if update_config_file(app_name):
            success_count += 1
    
    print(f"\n✅ {success_count}/{len(APP_CONFIGS)} archivos actualizados")
    return 0 if success_count == len(APP_CONFIGS) else 1

if __name__ == '__main__':
    sys.exit(main())
