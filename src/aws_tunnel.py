#!/usr/bin/env python3
"""
Herramienta para crear túneles SSH a OpenSearch usando AWS Systems Manager.
Permite acceso local a recursos en VPC privada a través de Session Manager.
"""

import argparse
import subprocess
import sys
import time
import json
import boto3
from botocore.exceptions import ClientError
from typing import Dict, List, Any, Optional

class AWSSSMTunnel:
    """Clase para gestionar túneles SSH a través de AWS SSM"""
    
    def __init__(self, region: str = "eu-west-1"):
        self.region = region
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.ssm_client = boto3.client('ssm', region_name=region)
        
    def find_bastion_instances(self) -> List[Dict[str, Any]]:
        """Busca instancias EC2 que puedan servir como bastion hosts"""
        try:
            # Buscar instancias con SSM Agent instalado y en running state
            response = self.ec2_client.describe_instances(
                Filters=[
                    {'Name': 'instance-state-name', 'Values': ['running']}
                ]
            )
            
            instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    # Verificar si tiene SSM Agent
                    ssm_status = self.check_ssm_status(instance['InstanceId'])
                    if ssm_status:
                        instances.append({
                            'instance_id': instance['InstanceId'],
                            'name': self.get_instance_name(instance),
                            'private_ip': instance.get('PrivateIpAddress'),
                            'vpc_id': instance.get('VpcId'),
                            'subnet_id': instance.get('SubnetId'),
                            'ssm_status': ssm_status
                        })
            
            return instances
            
        except ClientError as e:
            print(f"Error buscando instancias: {e}")
            return []
    
    def get_instance_name(self, instance: Dict) -> str:
        """Obtiene el nombre de una instancia EC2"""
        for tag in instance.get('Tags', []):
            if tag['Key'] == 'Name':
                return tag['Value']
        return instance['InstanceId']
    
    def check_ssm_status(self, instance_id: str) -> bool:
        """Verifica si una instancia tiene SSM Agent activo"""
        try:
            response = self.ssm_client.describe_instance_information(
                Filters=[
                    {'Key': 'InstanceIds', 'Values': [instance_id]}
                ]
            )
            return len(response['InstanceInformationList']) > 0
        except ClientError:
            return False
    
    def create_port_forward_session(self, instance_id: str, 
                                  remote_host: str, remote_port: int,
                                  local_port: int = 9201) -> Optional[str]:
        """Crea una sesión de port forwarding usando SSM"""
        try:
            # Parámetros para el port forwarding
            parameters = {
                'portNumber': [str(remote_port)],
                'localPortNumber': [str(local_port)],
                'host': [remote_host]
            }
            
            # Crear sesión SSM
            response = self.ssm_client.start_session(
                Target=instance_id,
                DocumentName='AWS-StartPortForwardingSessionToRemoteHost',
                Parameters=parameters
            )
            
            return response['SessionId']
            
        except ClientError as e:
            print(f"Error creando sesión SSM: {e}")
            return None
    
    def setup_opensearch_tunnel(self, opensearch_host: str, 
                               local_port: int = 9201) -> bool:
        """Configura un túnel completo a OpenSearch"""
        print("🔍 Buscando instancias bastion disponibles...")
        
        # Buscar instancias bastion
        instances = self.find_bastion_instances()
        
        if not instances:
            print("❌ No se encontraron instancias bastion con SSM habilitado")
            print("\n💡 Alternativas:")
            print("1. Crear una instancia EC2 en la misma VPC que OpenSearch")
            print("2. Habilitar SSM en una instancia existente")
            print("3. Usar AWS Cloud9 en la misma VPC")
            return False
        
        print(f"✅ Encontradas {len(instances)} instancias disponibles:")
        for i, instance in enumerate(instances, 1):
            print(f"   {i}. {instance['name']} ({instance['instance_id']})")
            print(f"      IP privada: {instance['private_ip']}")
            print(f"      VPC: {instance['vpc_id']}")
        
        # Usar la primera instancia disponible
        selected_instance = instances[0]
        print(f"\n🚀 Usando instancia: {selected_instance['name']}")
        
        # Crear túnel
        session_id = self.create_port_forward_session(
            selected_instance['instance_id'],
            opensearch_host,
            443,
            local_port
        )
        
        if session_id:
            print(f"✅ Túnel creado exitosamente!")
            print(f"   Sesión ID: {session_id}")
            print(f"   OpenSearch accesible en: https://localhost:{local_port}")
            print(f"   Para terminar: aws ssm terminate-session --session-id {session_id}")
            
            # Guardar session_id para poder terminarlo después
            self.session_id = session_id
            return True
        else:
            print("❌ Error creando el túnel")
            return False
    
    def keep_tunnel_alive(self):
        """Mantiene el túnel activo esperando señal de terminación"""
        print(f"\n⏳ Túnel activo. Presiona Ctrl+C para terminar...")
        try:
            # Mantener el proceso corriendo indefinidamente
            while True:
                time.sleep(60)
                # Verificar que la sesión sigue activa
                try:
                    response = self.ssm_client.describe_sessions(
                        State='Active',
                        Filters=[
                            {'key': 'SessionId', 'value': self.session_id}
                        ]
                    )
                    if not response['Sessions']:
                        print("\n⚠️  La sesión SSM se cerró inesperadamente")
                        break
                except Exception as e:
                    print(f"\n⚠️  Error verificando sesión: {e}")
                    break
        except KeyboardInterrupt:
            print("\n\n🛑 Terminando túnel...")
            try:
                self.ssm_client.terminate_session(SessionId=self.session_id)
                print("✅ Túnel terminado correctamente")
            except Exception as e:
                print(f"⚠️  Error terminando sesión: {e}")

def check_aws_cli_plugin():
    """Verifica si el plugin de Session Manager está instalado"""
    try:
        result = subprocess.run(['session-manager-plugin'], 
                              capture_output=True, text=True)
        return True
    except FileNotFoundError:
        return False

def install_session_manager_plugin():
    """Proporciona instrucciones para instalar el plugin"""
    print("❌ AWS Session Manager Plugin no está instalado")
    print("\n📥 Para instalarlo en macOS:")
    print("   curl 'https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac/sessionmanager-bundle.zip' -o 'sessionmanager-bundle.zip'")
    print("   unzip sessionmanager-bundle.zip")
    print("   sudo ./sessionmanager-bundle/install -i /usr/local/sessionmanagerplugin -b /usr/local/bin/session-manager-plugin")
    print("\n📥 Para instalarlo con Homebrew:")
    print("   brew install --cask session-manager-plugin")
    print("\n📥 Para otros sistemas operativos:")
    print("   https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html")

def main():
    parser = argparse.ArgumentParser(
        description="Crear túnel SSH a OpenSearch usando AWS SSM"
    )
    
    parser.add_argument(
        "--opensearch-host",
        default="vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com",
        help="Host de OpenSearch"
    )
    
    parser.add_argument(
        "--local-port",
        type=int,
        default=9201,
        help="Puerto local para el túnel"
    )
    
    parser.add_argument(
        "--region",
        default="eu-west-1",
        help="Región AWS"
    )
    
    parser.add_argument(
        "--list-instances",
        action="store_true",
        help="Solo listar instancias disponibles"
    )
    
    args = parser.parse_args()
    
    # Verificar plugin de Session Manager
    if not check_aws_cli_plugin():
        install_session_manager_plugin()
        return 1
    
    try:
        tunnel = AWSSSMTunnel(args.region)
        
        if args.list_instances:
            instances = tunnel.find_bastion_instances()
            if instances:
                print("🖥️  Instancias disponibles para túnel:")
                for instance in instances:
                    print(f"   • {instance['name']} ({instance['instance_id']})")
                    print(f"     IP: {instance['private_ip']}, VPC: {instance['vpc_id']}")
            else:
                print("❌ No se encontraron instancias bastion disponibles")
            return 0
        
        # Crear túnel
        success = tunnel.setup_opensearch_tunnel(
            args.opensearch_host, 
            args.local_port
        )
        
        if success:
            print(f"\n🎉 ¡Túnel establecido exitosamente!")
            print(f"   Ahora puedes usar las herramientas con:")
            print(f"   export OPENSEARCH_HOST=localhost:{args.local_port}")
            print(f"   python3 src/semantic_search.py 'tu consulta'")
            
            # Mantener el túnel activo
            tunnel.keep_tunnel_alive()
            return 0
        else:
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Operación cancelada por el usuario")
        return 1
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
