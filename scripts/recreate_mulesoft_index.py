#!/usr/bin/env python3
"""
Script para recrear el índice de MuleSoft con filename como keyword
"""

import sys
import json
import os
import yaml
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.connection_manager import ConnectionManager
from loguru import logger

def load_mulesoft_config():
    """Cargar configuración de MuleSoft"""
    config_path = "config/config_mulesoft.yaml"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error cargando configuración: {e}")
        return None

def get_opensearch_client():
    """Crear cliente OpenSearch directamente desde la configuración de MuleSoft"""
    try:
        config = load_mulesoft_config()
        if not config:
            return None
        
        opensearch_config = config['opensearch']
        bedrock_config = config['bedrock']
        
        # Importar dependencias necesarias
        import boto3
        from opensearchpy import OpenSearch, RequestsHttpConnection
        from aws_requests_auth.aws_auth import AWSRequestsAuth
        
        # Obtener credenciales AWS
        credentials = boto3.Session().get_credentials()
        if not credentials:
            logger.error("AWS credentials not found. Please configure your AWS credentials.")
            return None
        
        # Configurar autenticación AWS
        host = opensearch_config['host']
        port = opensearch_config['port']
        region = bedrock_config['region_name']
        
        awsauth = AWSRequestsAuth(
            aws_access_key=credentials.access_key,
            aws_secret_access_key=credentials.secret_key,
            aws_token=credentials.token,
            aws_host=host,
            aws_region=region,
            aws_service='es'
        )
        
        # Crear cliente OpenSearch
        client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_auth=awsauth,
            use_ssl=opensearch_config['use_ssl'],
            verify_certs=opensearch_config['verify_certs'],
            connection_class=RequestsHttpConnection,
            timeout=opensearch_config['timeout']
        )
        
        logger.info(f"OpenSearch client created for {host}:{port}")
        return client
        
    except Exception as e:
        logger.error(f"Error creando cliente OpenSearch: {e}")
        return None

def backup_index_mapping(client, index_name):
    """Hacer backup del mapping actual del índice"""
    try:
        if not client.indices.exists(index=index_name):
            logger.info(f"El índice {index_name} no existe, no hay nada que respaldar")
            return True
        
        # Obtener mapping actual
        mapping = client.indices.get_mapping(index=index_name)
        
        # Guardar backup
        backup_file = f"backup_mapping_{index_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Backup del mapping guardado en: {backup_file}")
        return True
    except Exception as e:
        logger.error(f"Error haciendo backup del mapping: {e}")
        return False

def get_document_count(client, index_name):
    """Obtener el número de documentos en el índice"""
    try:
        if not client.indices.exists(index=index_name):
            return 0
        
        count_response = client.count(index=index_name)
        return count_response['count']
    except Exception as e:
        logger.error(f"Error obteniendo conteo de documentos: {e}")
        return 0

def delete_index(client, index_name):
    """Borrar el índice existente"""
    try:
        if client.indices.exists(index=index_name):
            logger.info(f"🗑️  Borrando índice existente: {index_name}")
            response = client.indices.delete(index=index_name)
            logger.info(f"✅ Índice borrado: {response}")
            return True
        else:
            logger.info(f"El índice {index_name} no existe")
            return True
    except Exception as e:
        logger.error(f"Error borrando índice: {e}")
        return False

def create_index_with_keyword_filename(client, index_name):
    """Crear el índice con filename como keyword"""
    try:
        # Mapping actualizado con filename como keyword
        mapping = {
            "mappings": {
                "properties": {
                    "content": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "title": {
                        "type": "text"
                    },
                    "file_path": {
                        "type": "keyword"
                    },
                    "file_name": {
                        "type": "keyword"  # CAMBIO PRINCIPAL: ahora es keyword directo
                    },
                    "chunk_id": {
                        "type": "keyword"
                    },
                    "chunk_index": {
                        "type": "integer"
                    },
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 1024
                    },
                    "image_base64": {
                        "type": "text",
                        "index": False
                    },
                    "metadata": {
                        "type": "object"
                    },
                    "timestamp": {
                        "type": "date"
                    },
                    "document_type": {
                        "type": "keyword"
                    },
                    "has_images": {
                        "type": "boolean"
                    },
                    "image_count": {
                        "type": "integer"
                    },
                    # Application-specific fields
                    "application_id": {
                        "type": "keyword"
                    },
                    "application_name": {
                        "type": "keyword"
                    },
                    "s3_bucket": {
                        "type": "keyword"
                    },
                    "s3_prefix": {
                        "type": "keyword"
                    }
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 100
                }
            }
        }
        
        logger.info(f"🔧 Creando índice {index_name} con filename como keyword...")
        response = client.indices.create(
            index=index_name,
            body=mapping
        )
        
        logger.info(f"✅ Índice creado exitosamente: {response}")
        
        # Verificar el mapping
        new_mapping = client.indices.get_mapping(index=index_name)
        filename_mapping = new_mapping[index_name]['mappings']['properties']['file_name']
        logger.info(f"📋 Mapping de file_name: {filename_mapping}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creando índice: {e}")
        return False

def verify_index_structure(client, index_name):
    """Verificar la estructura del nuevo índice"""
    try:
        if not client.indices.exists(index=index_name):
            logger.error(f"El índice {index_name} no existe")
            return False
        
        # Obtener mapping
        mapping = client.indices.get_mapping(index=index_name)
        properties = mapping[index_name]['mappings']['properties']
        
        # Verificar que file_name sea keyword
        filename_mapping = properties.get('file_name', {})
        if filename_mapping.get('type') == 'keyword':
            logger.info("✅ file_name está correctamente configurado como keyword")
        else:
            logger.error(f"❌ file_name no es keyword: {filename_mapping}")
            return False
        
        # Mostrar información del índice
        stats = client.indices.stats(index=index_name)
        logger.info(f"📊 Estadísticas del índice:")
        logger.info(f"   - Documentos: {stats['indices'][index_name]['total']['docs']['count']}")
        logger.info(f"   - Tamaño: {stats['indices'][index_name]['total']['store']['size_in_bytes']} bytes")
        
        return True
        
    except Exception as e:
        logger.error(f"Error verificando estructura del índice: {e}")
        return False

def main():
    """Función principal"""
    logger.info("🚀 Iniciando recreación del índice MuleSoft con filename como keyword")
    
    # Cargar configuración
    config = load_mulesoft_config()
    if not config:
        logger.error("❌ No se pudo cargar la configuración")
        return 1
    
    index_name = config['opensearch']['index_name']
    logger.info(f"📋 Índice a recrear: {index_name}")
    
    # Crear cliente OpenSearch
    client = get_opensearch_client()
    if not client:
        logger.error("❌ No se pudo crear el cliente OpenSearch")
        return 1
    
    try:
        # Verificar conexión
        info = client.info()
        logger.info(f"✅ Conectado a OpenSearch: {info['version']['number']}")
    except Exception as e:
        logger.error(f"❌ Error conectando a OpenSearch: {e}")
        return 1
    
    # Obtener información del índice actual
    doc_count = get_document_count(client, index_name)
    logger.info(f"📊 Documentos actuales en el índice: {doc_count}")
    
    if doc_count > 0:
        logger.warning(f"⚠️  ADVERTENCIA: El índice contiene {doc_count} documentos")
        logger.warning("   Estos documentos se perderán al recrear el índice")
        logger.warning("   Asegúrate de tener un backup o poder reindexar los documentos")
        
        confirm = input("\n¿Continuar con la recreación del índice? (yes/no): ")
        if confirm.lower() != 'yes':
            logger.info("❌ Operación cancelada por el usuario")
            return 0
    
    # Paso 1: Hacer backup del mapping actual
    logger.info("\n📋 Paso 1: Haciendo backup del mapping actual...")
    if not backup_index_mapping(client, index_name):
        logger.error("❌ Error haciendo backup, abortando")
        return 1
    
    # Paso 2: Borrar índice existente
    logger.info("\n🗑️  Paso 2: Borrando índice existente...")
    if not delete_index(client, index_name):
        logger.error("❌ Error borrando índice, abortando")
        return 1
    
    # Paso 3: Crear nuevo índice con filename como keyword
    logger.info("\n🔧 Paso 3: Creando nuevo índice con filename como keyword...")
    if not create_index_with_keyword_filename(client, index_name):
        logger.error("❌ Error creando nuevo índice")
        return 1
    
    # Paso 4: Verificar estructura
    logger.info("\n✅ Paso 4: Verificando estructura del nuevo índice...")
    if not verify_index_structure(client, index_name):
        logger.error("❌ Error verificando estructura")
        return 1
    
    logger.info("\n🎉 ¡Recreación del índice completada exitosamente!")
    logger.info(f"   - Índice: {index_name}")
    logger.info(f"   - file_name ahora es de tipo: keyword")
    logger.info(f"   - El índice está listo para recibir documentos")
    
    if doc_count > 0:
        logger.info(f"\n📝 NOTA: Necesitarás reindexar los {doc_count} documentos que tenías anteriormente")
        logger.info("   Puedes usar el script de ingestión para volver a cargar los documentos desde S3")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
