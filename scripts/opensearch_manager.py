#!/usr/bin/env python3
"""
Script para gestionar documentos en OpenSearch desde EC2 con autenticación AWS
"""

import sys
import json
import argparse
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth

def get_opensearch_client():
    """Crear cliente OpenSearch con autenticación AWS"""
    region = 'eu-west-1'
    host = 'vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com'
    service = 'es'
    
    credentials = boto3.Session().get_credentials()
    awsauth = AWSRequestsAuth(
        aws_access_key=credentials.access_key,
        aws_secret_access_key=credentials.secret_key,
        aws_token=credentials.token,
        aws_host=host,
        aws_region=region,
        aws_service=service
    )
    
    client = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30
    )
    
    return client

def list_indices(client):
    """Listar todos los índices"""
    try:
        indices = client.cat.indices(format='json')
        print("\n📋 Índices en OpenSearch:")
        print("-" * 100)
        print(f"{'Index':<40} {'Health':<10} {'Status':<10} {'Docs':<15} {'Size':<10}")
        print("-" * 100)
        for idx in indices:
            print(f"{idx['index']:<40} {idx['health']:<10} {idx['status']:<10} {idx['docs.count']:<15} {idx['store.size']:<10}")
        print("-" * 100)
        return True
    except Exception as e:
        print(f"❌ Error listando índices: {e}")
        return False

def delete_all_documents(client, index_name):
    """Borrar todos los documentos de un índice"""
    try:
        # Confirmar
        print(f"\n⚠️  ADVERTENCIA: Vas a borrar TODOS los documentos del índice: {index_name}")
        confirm = input("¿Estás seguro? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Operación cancelada")
            return False
        
        print(f"\n🗑️  Borrando todos los documentos de {index_name}...")
        
        # Usar delete_by_query
        response = client.delete_by_query(
            index=index_name,
            body={"query": {"match_all": {}}},
            conflicts='proceed',
            refresh=True
        )
        
        print(f"✅ Documentos borrados: {response['deleted']}")
        print(f"   Total procesados: {response['total']}")
        print(f"   Tiempo: {response['took']}ms")
        
        # Verificar conteo
        count = client.count(index=index_name)
        print(f"\n📊 Documentos restantes en el índice: {count['count']}")
        
        return True
    except Exception as e:
        print(f"❌ Error borrando documentos: {e}")
        return False

def delete_by_query(client, index_name, query):
    """Borrar documentos que coincidan con una query"""
    try:
        print(f"\n🔍 Borrando documentos que coincidan con query en {index_name}...")
        print(f"Query: {json.dumps(query, indent=2)}")
        
        response = client.delete_by_query(
            index=index_name,
            body={"query": query},
            conflicts='proceed',
            refresh=True
        )
        
        print(f"✅ Documentos borrados: {response['deleted']}")
        print(f"   Total procesados: {response['total']}")
        
        return True
    except Exception as e:
        print(f"❌ Error borrando documentos: {e}")
        return False

def delete_index(client, index_name):
    """Borrar un índice completo"""
    try:
        print(f"\n⚠️  ADVERTENCIA: Vas a borrar el ÍNDICE COMPLETO: {index_name}")
        print("   Esto incluye todos los documentos Y la configuración del índice")
        confirm = input("¿Estás seguro? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Operación cancelada")
            return False
        
        print(f"\n🗑️  Borrando índice {index_name}...")
        
        response = client.indices.delete(index=index_name)
        
        print(f"✅ Índice borrado exitosamente")
        print(f"   Response: {response}")
        
        return True
    except Exception as e:
        print(f"❌ Error borrando índice: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Gestionar documentos en OpenSearch')
    parser.add_argument('action', choices=['list', 'delete-all', 'delete-by-query', 'delete-index'],
                       help='Acción a realizar')
    parser.add_argument('--index', help='Nombre del índice')
    parser.add_argument('--query', help='Query JSON para delete-by-query')
    
    args = parser.parse_args()
    
    # Crear cliente
    try:
        client = get_opensearch_client()
        print("✅ Conectado a OpenSearch")
    except Exception as e:
        print(f"❌ Error conectando a OpenSearch: {e}")
        return 1
    
    # Ejecutar acción
    if args.action == 'list':
        success = list_indices(client)
    elif args.action == 'delete-all':
        if not args.index:
            print("❌ Error: Debes especificar --index")
            return 1
        success = delete_all_documents(client, args.index)
    elif args.action == 'delete-by-query':
        if not args.index or not args.query:
            print("❌ Error: Debes especificar --index y --query")
            return 1
        try:
            query = json.loads(args.query)
        except json.JSONDecodeError as e:
            print(f"❌ Error parseando query JSON: {e}")
            return 1
        success = delete_by_query(client, args.index, query)
    elif args.action == 'delete-index':
        if not args.index:
            print("❌ Error: Debes especificar --index")
            return 1
        success = delete_index(client, args.index)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
