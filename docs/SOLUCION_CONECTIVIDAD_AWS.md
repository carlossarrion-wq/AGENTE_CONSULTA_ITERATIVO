# Solución de Conectividad AWS - Agente Darwin

## 🚨 Problema Identificado

El cluster de OpenSearch está en una **VPC privada** y no es accesible directamente desde tu máquina local. Esto es una configuración de seguridad común en AWS.

### Diagnóstico Realizado

```bash
# Ejecutar diagnóstico
source venv/bin/activate
python3 src/network_diagnostics.py
```

**Resultado:**
- ✅ Credenciales AWS: Válidas
- ✅ Acceso a Bedrock: Exitoso (38 modelos disponibles)
- ✅ Resolución DNS OpenSearch: Exitosa (IP: 10.0.3.156)
- ❌ Conectividad TCP OpenSearch: **TIMEOUT** (VPC privada)

## 🔧 Soluciones Disponibles

### Opción 1: Túnel SSH con AWS Systems Manager (RECOMENDADO)

Esta es la solución más elegante y segura para acceder a recursos en VPC privada.

#### Paso 1: Instalar Session Manager Plugin

```bash
# Opción A: Con Homebrew (más fácil)
brew install --cask session-manager-plugin

# Opción B: Instalación manual
curl 'https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac/sessionmanager-bundle.zip' -o 'sessionmanager-bundle.zip'
unzip sessionmanager-bundle.zip
sudo ./sessionmanager-bundle/install -i /usr/local/sessionmanagerplugin -b /usr/local/bin/session-manager-plugin
```

#### Paso 2: Verificar Instancias Bastion Disponibles

```bash
source venv/bin/activate
python3 src/aws_tunnel.py --list-instances
```

#### Paso 3: Crear Túnel a OpenSearch

```bash
# Crear túnel (puerto local 9200)
python3 src/aws_tunnel.py

# O especificar puerto personalizado
python3 src/aws_tunnel.py --local-port 9443
```

#### Paso 4: Usar las Herramientas con Túnel

```bash
# Configurar host local
export OPENSEARCH_HOST=localhost:9200

# Usar herramientas normalmente
python3 src/semantic_search.py "NU_17"
python3 src/lexical_search.py "configuración"
```

### Opción 2: Crear Instancia Bastion (Si no existe)

Si no hay instancias bastion disponibles, puedes crear una:

#### Crear Instancia EC2 en la VPC

```bash
# 1. Obtener VPC ID del cluster OpenSearch
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=*opensearch*"

# 2. Crear instancia bastion
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.micro \
  --key-name tu-key-pair \
  --subnet-id subnet-xxxxxxxxx \
  --security-group-ids sg-xxxxxxxxx \
  --iam-instance-profile Name=SSMInstanceProfile \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=Darwin-Bastion}]'
```

#### Configurar SSM en la Instancia

```bash
# Conectar a la instancia y instalar SSM Agent
sudo yum update -y
sudo yum install -y amazon-ssm-agent
sudo systemctl enable amazon-ssm-agent
sudo systemctl start amazon-ssm-agent
```

### Opción 3: AWS Cloud9 (Alternativa en la Nube)

Usar AWS Cloud9 como IDE en la nube dentro de la misma VPC:

```bash
# Crear entorno Cloud9
aws cloud9 create-environment-ec2 \
  --name "Darwin-Development" \
  --description "Entorno de desarrollo para Darwin" \
  --instance-type t3.small \
  --subnet-id subnet-xxxxxxxxx \
  --automatic-stop-time-minutes 60
```

### Opción 4: Modo Simulado para Desarrollo Local

Para desarrollo y testing sin conectividad real:

```bash
# Usar configuración local con datos simulados
python3 src/semantic_search.py "test query" --config config/config_local.yaml
```

## 🛠️ Configuración Detallada

### Configurar Variables de Entorno

```bash
# Para túnel SSH
export OPENSEARCH_HOST=localhost:9200
export OPENSEARCH_USE_SSL=false
export OPENSEARCH_VERIFY_CERTS=false

# Para modo simulado
export DARWIN_MODE=local
export DARWIN_CONFIG=config/config_local.yaml
```

### Actualizar Configuración de Herramientas

Las herramientas ya están preparadas para usar variables de entorno:

```python
# En src/common.py
host = os.getenv('OPENSEARCH_HOST', self.config.get('opensearch.host'))
use_ssl = os.getenv('OPENSEARCH_USE_SSL', 'true').lower() == 'true'
```

## 🚀 Flujo de Trabajo Recomendado

### Para Desarrollo Local

1. **Instalar Session Manager Plugin**
   ```bash
   brew install --cask session-manager-plugin
   ```

2. **Crear Túnel**
   ```bash
   python3 src/aws_tunnel.py
   ```

3. **Configurar Variables**
   ```bash
   export OPENSEARCH_HOST=localhost:9200
   export OPENSEARCH_USE_SSL=false
   ```

4. **Usar Herramientas**
   ```bash
   python3 src/semantic_search.py "tu consulta"
   ```

### Para Producción

1. **Desplegar en EC2** dentro de la VPC
2. **Usar configuración original** (config/config.yaml)
3. **Ejecutar herramientas directamente** sin túneles

## 🔍 Comandos de Verificación

### Verificar Conectividad

```bash
# Diagnóstico completo
python3 src/network_diagnostics.py

# Verificar túnel activo
curl -k https://localhost:9200/_cluster/health

# Listar sesiones SSM activas
aws ssm describe-sessions --state Active
```

### Terminar Túneles

```bash
# Listar sesiones activas
aws ssm describe-sessions --state Active

# Terminar sesión específica
aws ssm terminate-session --session-id ses-xxxxxxxxx
```

## 🚨 Solución de Problemas

### Error: "Session Manager Plugin not found"

```bash
# Verificar instalación
session-manager-plugin

# Reinstalar si es necesario
brew reinstall --cask session-manager-plugin
```

### Error: "No bastion instances found"

```bash
# Buscar todas las instancias en running state
aws ec2 describe-instances --filters "Name=state-name,Values=running"

# Verificar SSM Agent en instancias
aws ssm describe-instance-information
```

### Error: "Permission denied"

```bash
# Verificar permisos IAM
aws iam get-user
aws iam list-attached-user-policies --user-name tu-usuario

# Permisos necesarios:
# - ssm:StartSession
# - ssm:TerminateSession
# - ec2:DescribeInstances
# - ssm:DescribeInstanceInformation
```

## 📚 Referencias

- [AWS Systems Manager Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)
- [Port Forwarding con SSM](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html#sessions-remote-port-forwarding)
- [OpenSearch VPC Access](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/vpc.html)

## 💡 Próximos Pasos

1. **Instalar Session Manager Plugin** (5 minutos)
2. **Probar túnel SSH** con instancia existente
3. **Si no hay bastion**: Crear instancia EC2 pequeña
4. **Configurar variables de entorno** para desarrollo local
5. **Probar herramientas** con conectividad real

¡Con estas soluciones podrás acceder al cluster OpenSearch desde tu máquina local de forma segura!
