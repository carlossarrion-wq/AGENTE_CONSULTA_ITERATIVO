#!/bin/bash
# Script para reiniciar el dominio OpenSearch forzando un redespliegue

set -e

DOMAIN_NAME="rag-opensearch-clean"
REGION="eu-west-1"

echo "🔍 Verificando estado actual del dominio OpenSearch..."

# Obtener configuración actual
CURRENT_CONFIG=$(aws opensearch describe-domain \
  --domain-name "$DOMAIN_NAME" \
  --region "$REGION" \
  --query 'DomainStatus.ClusterConfig' \
  --output json)

echo "📋 Configuración actual:"
echo "$CURRENT_CONFIG" | python3 -m json.tool

echo ""
echo "⚠️  IMPORTANTE: Este proceso reiniciará el dominio OpenSearch"
echo "   - Causará downtime temporal (5-15 minutos)"
echo "   - Forzará un redespliegue blue/green"
echo "   - Los datos NO se perderán"
echo ""
read -p "¿Deseas continuar? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Operación cancelada"
    exit 1
fi

echo ""
echo "🔄 Iniciando redespliegue del dominio..."

# Forzar redespliegue modificando la configuración (mismo valor)
aws opensearch update-domain-config \
  --domain-name "$DOMAIN_NAME" \
  --region "$REGION" \
  --cluster-config \
    InstanceType=t3.small.search,\
InstanceCount=1,\
DedicatedMasterEnabled=false,\
ZoneAwarenessEnabled=false

echo ""
echo "✅ Redespliegue iniciado"
echo ""
echo "⏳ Monitoreando el progreso..."
echo "   Esto puede tomar 10-15 minutos..."
echo ""

# Monitorear el progreso
while true; do
    STATUS=$(aws opensearch describe-domain \
      --domain-name "$DOMAIN_NAME" \
      --region "$REGION" \
      --query 'DomainStatus.Processing' \
      --output text)
    
    if [ "$STATUS" == "True" ]; then
        echo "   🔄 Procesando... ($(date '+%H:%M:%S'))"
        sleep 30
    else
        echo ""
        echo "✅ Redespliegue completado!"
        break
    fi
done

echo ""
echo "🧪 Verificando conectividad desde EC2..."

# Probar conectividad desde EC2
COMMAND_ID=$(aws ssm send-command \
  --instance-ids i-0aed93266a5823099 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["curl -k -s --max-time 5 https://vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com/_cluster/health"]' \
  --region "$REGION" \
  --query 'Command.CommandId' \
  --output text)

sleep 5

RESULT=$(aws ssm get-command-invocation \
  --command-id "$COMMAND_ID" \
  --instance-id i-0aed93266a5823099 \
  --region "$REGION" \
  --query 'StandardOutputContent' \
  --output text)

if echo "$RESULT" | grep -q "cluster_name"; then
    echo "✅ OpenSearch está respondiendo correctamente!"
    echo ""
    echo "📊 Estado del cluster:"
    echo "$RESULT" | python3 -m json.tool
    echo ""
    echo "🎉 ¡Problema resuelto! Ahora puedes usar el túnel SSH:"
    echo "   ./src/ssh_tunnel/start_tunnel_direct.sh"
else
    echo "❌ OpenSearch aún no responde"
    echo "   Resultado: $RESULT"
    echo ""
    echo "💡 Acciones adicionales:"
    echo "   1. Espera 5 minutos más y vuelve a probar"
    echo "   2. Verifica los logs de CloudWatch"
    echo "   3. Contacta con AWS Support si el problema persiste"
fi
