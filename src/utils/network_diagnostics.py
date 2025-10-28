#!/usr/bin/env python3
"""
Herramienta de diagnóstico de conectividad de red para los servicios AWS.
Verifica la conectividad a OpenSearch y Bedrock desde la máquina local.
"""

import argparse
import socket
import time
import sys
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import requests

def test_dns_resolution(hostname: str) -> Dict[str, Any]:
    """Prueba la resolución DNS de un hostname"""
    try:
        start_time = time.time()
        ip_address = socket.gethostbyname(hostname)
        resolution_time = time.time() - start_time
        return {
            "success": True,
            "ip_address": ip_address,
            "resolution_time_ms": round(resolution_time * 1000, 2)
        }
    except socket.gaierror as e:
        return {
            "success": False,
            "error": str(e)
        }

def test_tcp_connection(hostname: str, port: int, timeout: int = 10) -> Dict[str, Any]:
    """Prueba la conectividad TCP a un host y puerto"""
    try:
        start_time = time.time()
        sock = socket.create_connection((hostname, port), timeout)
        connection_time = time.time() - start_time
        sock.close()
        return {
            "success": True,
            "connection_time_ms": round(connection_time * 1000, 2)
        }
    except (socket.timeout, socket.error, OSError) as e:
        return {
            "success": False,
            "error": str(e)
        }

def test_aws_credentials() -> Dict[str, Any]:
    """Verifica las credenciales AWS"""
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        return {
            "success": True,
            "account": identity.get('Account'),
            "user_arn": identity.get('Arn'),
            "user_id": identity.get('UserId')
        }
    except NoCredentialsError:
        return {
            "success": False,
            "error": "No se encontraron credenciales AWS"
        }
    except ClientError as e:
        return {
            "success": False,
            "error": str(e)
        }

def test_bedrock_access(region: str = "eu-west-1") -> Dict[str, Any]:
    """Verifica el acceso a AWS Bedrock"""
    try:
        bedrock = boto3.client('bedrock', region_name=region)
        models = bedrock.list_foundation_models()
        return {
            "success": True,
            "models_count": len(models.get('modelSummaries', [])),
            "region": region
        }
    except ClientError as e:
        return {
            "success": False,
            "error": str(e),
            "region": region
        }

def test_opensearch_connectivity(host: str) -> Dict[str, Any]:
    """Prueba la conectividad completa a OpenSearch"""
    results = {}
    
    # 1. Resolución DNS
    print(f"🔍 Probando resolución DNS para {host}...")
    dns_result = test_dns_resolution(host)
    results["dns"] = dns_result
    
    if dns_result["success"]:
        print(f"✅ DNS resuelto: {dns_result['ip_address']} ({dns_result['resolution_time_ms']}ms)")
        
        # 2. Conectividad TCP
        print(f"🔌 Probando conectividad TCP a {host}:443...")
        tcp_result = test_tcp_connection(host, 443, timeout=30)
        results["tcp"] = tcp_result
        
        if tcp_result["success"]:
            print(f"✅ Conexión TCP exitosa ({tcp_result['connection_time_ms']}ms)")
        else:
            print(f"❌ Error de conexión TCP: {tcp_result['error']}")
    else:
        print(f"❌ Error de resolución DNS: {dns_result['error']}")
        results["tcp"] = {"success": False, "error": "DNS resolution failed"}
    
    return results

def diagnose_network_issues():
    """Ejecuta un diagnóstico completo de conectividad"""
    print("🚀 Iniciando diagnóstico de conectividad AWS...")
    print("=" * 60)
    
    # 1. Verificar credenciales AWS
    print("\n1️⃣ Verificando credenciales AWS...")
    creds_result = test_aws_credentials()
    if creds_result["success"]:
        print(f"✅ Credenciales válidas")
        print(f"   Cuenta: {creds_result['account']}")
        print(f"   Usuario: {creds_result['user_arn']}")
    else:
        print(f"❌ Error de credenciales: {creds_result['error']}")
        return
    
    # 2. Verificar acceso a Bedrock
    print("\n2️⃣ Verificando acceso a AWS Bedrock...")
    bedrock_result = test_bedrock_access()
    if bedrock_result["success"]:
        print(f"✅ Acceso a Bedrock exitoso")
        print(f"   Región: {bedrock_result['region']}")
        print(f"   Modelos disponibles: {bedrock_result['models_count']}")
    else:
        print(f"❌ Error de acceso a Bedrock: {bedrock_result['error']}")
    
    # 3. Verificar conectividad a OpenSearch
    print("\n3️⃣ Verificando conectividad a OpenSearch...")
    opensearch_host = "vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com"
    opensearch_result = test_opensearch_connectivity(opensearch_host)
    
    # 4. Resumen y recomendaciones
    print("\n" + "=" * 60)
    print("📋 RESUMEN DEL DIAGNÓSTICO")
    print("=" * 60)
    
    if not creds_result["success"]:
        print("❌ PROBLEMA CRÍTICO: Credenciales AWS no válidas")
        print("   Solución: Ejecutar 'aws configure' para configurar credenciales")
        return
    
    if not bedrock_result["success"]:
        print("⚠️  ADVERTENCIA: No se puede acceder a Bedrock")
        print("   Posibles causas:")
        print("   - Permisos IAM insuficientes")
        print("   - Bedrock no disponible en la región")
        print("   - Restricciones de red corporativa")
    
    if not opensearch_result["dns"]["success"]:
        print("❌ PROBLEMA CRÍTICO: No se puede resolver DNS de OpenSearch")
        print("   Posibles causas:")
        print("   - Problema de conectividad a internet")
        print("   - DNS corporativo bloqueando AWS")
    elif not opensearch_result["tcp"]["success"]:
        print("❌ PROBLEMA CRÍTICO: No se puede conectar a OpenSearch")
        print("   Causa más probable: Cluster en VPC privada")
        print("   Soluciones recomendadas:")
        print("   1. Usar una instancia EC2 en la misma VPC")
        print("   2. Configurar VPN o AWS Direct Connect")
        print("   3. Usar AWS Systems Manager Session Manager")
        print("   4. Configurar un proxy/bastion host")
    else:
        print("✅ Conectividad completa exitosa")
    
    print("\n💡 RECOMENDACIONES:")
    if not opensearch_result["tcp"]["success"]:
        print("   - Para desarrollo local: Usar modo mock/simulación")
        print("   - Para producción: Desplegar en EC2 dentro de la VPC")
        print("   - Considerar usar AWS Cloud9 como IDE en la nube")

def main():
    parser = argparse.ArgumentParser(
        description="Diagnóstico de conectividad para servicios AWS Darwin"
    )
    
    parser.add_argument(
        "--host",
        default="vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com",
        help="Host de OpenSearch a probar"
    )
    
    parser.add_argument(
        "--region",
        default="eu-west-1",
        help="Región AWS para Bedrock"
    )
    
    args = parser.parse_args()
    
    try:
        diagnose_network_issues()
    except KeyboardInterrupt:
        print("\n\n⏹️  Diagnóstico interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado durante el diagnóstico: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
