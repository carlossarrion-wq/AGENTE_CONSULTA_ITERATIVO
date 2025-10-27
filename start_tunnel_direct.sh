#!/bin/bash
# Script simplificado para crear túnel SSH usando AWS CLI directamente

set -e

# Configuración
INSTANCE_ID="i-0aed93266a5823099"
OPENSEARCH_HOST="vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com"
LOCAL_PORT="9201"
REMOTE_PORT="443"
REGION="eu-west-1"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Iniciando túnel SSH a OpenSearch...${NC}"
echo -e "${BLUE}   Instancia: ${INSTANCE_ID}${NC}"
echo -e "${BLUE}   Puerto local: ${LOCAL_PORT}${NC}"
echo -e "${BLUE}   Destino: ${OPENSEARCH_HOST}:${REMOTE_PORT}${NC}"
echo ""

# Crear túnel usando AWS CLI
echo -e "${YELLOW}⏳ Creando túnel (mantén esta terminal abierta)...${NC}"
echo -e "${YELLOW}   Presiona Ctrl+C para terminar el túnel${NC}"
echo ""

aws ssm start-session \
    --target "${INSTANCE_ID}" \
    --document-name AWS-StartPortForwardingSessionToRemoteHost \
    --parameters "{\"host\":[\"${OPENSEARCH_HOST}\"],\"portNumber\":[\"${REMOTE_PORT}\"],\"localPortNumber\":[\"${LOCAL_PORT}\"]}" \
    --region "${REGION}"

echo ""
echo -e "${GREEN}✅ Túnel terminado${NC}"
