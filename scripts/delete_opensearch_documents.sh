#!/bin/bash
# Script para borrar documentos de un índice de OpenSearch usando la API REST desde EC2

set -e

# Configuración
INSTANCE_ID="i-0aed93266a5823099"
OPENSEARCH_HOST="vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com"
REGION="eu-west-1"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Función para mostrar uso
show_usage() {
    echo -e "${BLUE}📖 Uso:${NC}"
    echo -e "   $0 list                          - Listar todos los índices"
    echo -e "   $0 delete-all <index>            - Borrar TODOS los documentos de un índice"
    echo -e "   $0 delete-by-query <index> <query> - Borrar documentos que coincidan con query"
    echo -e "   $0 delete-index <index>          - Borrar el índice completo"
    echo ""
    echo -e "${BLUE}📝 Ejemplos:${NC}"
    echo -e "   $0 list"
    echo -e "   $0 delete-all rag-documents-saplcorp"
    echo -e "   $0 delete-by-query rag-documents-saplcorp '{\"match\":{\"path\":\"documento.pdf\"}}'"
    echo -e "   $0 delete-index rag-documents-saplcorp"
}

# Función para ejecutar comando en EC2 con AWS Signature V4
run_on_ec2() {
    local command="$1"
    
    echo -e "${YELLOW}⏳ Ejecutando en EC2...${NC}"
    
    # Crear script temporal que use awscurl para autenticación AWS
    SCRIPT="#!/bin/bash
export AWS_DEFAULT_REGION=${REGION}
${command}
"
    
    COMMAND_ID=$(aws ssm send-command \
        --instance-ids "$INSTANCE_ID" \
        --document-name "AWS-RunShellScript" \
        --parameters "commands=[\"${SCRIPT}\"]" \
        --region "$REGION" \
        --query 'Command.CommandId' \
        --output text)
    
    sleep 3
    
    RESULT=$(aws ssm get-command-invocation \
        --command-id "$COMMAND_ID" \
        --instance-id "$INSTANCE_ID" \
        --region "$REGION" \
        --query '[Status,StandardOutputContent,StandardErrorContent]' \
        --output json)
    
    echo "$RESULT"
}

# Función para listar índices
list_indices() {
    echo -e "${BLUE}📋 Listando índices de OpenSearch...${NC}"
    
    # Usar awscurl si está disponible, sino usar curl con --aws-sigv4
    COMMAND="if command -v awscurl &> /dev/null; then
    awscurl --service es --region ${REGION} https://${OPENSEARCH_HOST}/_cat/indices?v
elif curl --help all 2>&1 | grep -q aws-sigv4; then
    curl -k -s --aws-sigv4 'aws:amz:${REGION}:es' --user \"\$(aws configure get aws_access_key_id):\$(aws configure get aws_secret_access_key)\" https://${OPENSEARCH_HOST}/_cat/indices?v
else
    echo 'ERROR: Necesitas awscurl o curl con soporte AWS SigV4'
    echo 'Instala awscurl: pip3 install awscurl'
fi"
    
    RESULT=$(run_on_ec2 "$COMMAND")
    
    STATUS=$(echo "$RESULT" | jq -r '.[0]' 2>/dev/null || echo "Error")
    OUTPUT=$(echo "$RESULT" | jq -r '.[1]' 2>/dev/null || echo "$RESULT")
    
    if [ "$STATUS" == "Success" ]; then
        echo -e "${GREEN}✅ Índices encontrados:${NC}"
        echo "$OUTPUT"
    else
        echo -e "${RED}❌ Error listando índices${NC}"
        echo "$OUTPUT"
    fi
}

# Función para borrar todos los documentos de un índice
delete_all_documents() {
    local index="$1"
    
    echo -e "${YELLOW}⚠️  ADVERTENCIA: Vas a borrar TODOS los documentos del índice: ${index}${NC}"
    read -p "¿Estás seguro? (yes/no): " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        echo -e "${RED}❌ Operación cancelada${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}🗑️  Borrando todos los documentos de ${index}...${NC}"
    
    # Usar delete_by_query con match_all (con autenticación AWS)
    COMMAND="if command -v awscurl &> /dev/null; then
    awscurl --service es --region ${REGION} -X POST 'https://${OPENSEARCH_HOST}/${index}/_delete_by_query?conflicts=proceed&refresh=true' -H 'Content-Type: application/json' -d '{\"query\":{\"match_all\":{}}}'
else
    echo 'ERROR: awscurl no está instalado. Instala con: pip3 install awscurl'
fi"
    
    RESULT=$(run_on_ec2 "$COMMAND")
    
    STATUS=$(echo "$RESULT" | jq -r '.[0]')
    OUTPUT=$(echo "$RESULT" | jq -r '.[1]')
    
    if [ "$STATUS" == "Success" ]; then
        echo -e "${GREEN}✅ Documentos borrados:${NC}"
        echo "$OUTPUT" | python3 -m json.tool 2>/dev/null || echo "$OUTPUT"
        
        # Verificar conteo
        echo ""
        echo -e "${BLUE}📊 Verificando conteo de documentos...${NC}"
        COUNT_COMMAND="if command -v awscurl &> /dev/null; then
    awscurl --service es --region ${REGION} https://${OPENSEARCH_HOST}/${index}/_count
else
    echo '{\"count\": \"unknown - awscurl not installed\"}'
fi"
        COUNT_RESULT=$(run_on_ec2 "$COUNT_COMMAND")
        COUNT_OUTPUT=$(echo "$COUNT_RESULT" | jq -r '.[1]')
        echo "$COUNT_OUTPUT" | python3 -m json.tool 2>/dev/null || echo "$COUNT_OUTPUT"
    else
        echo -e "${RED}❌ Error borrando documentos${NC}"
        echo "$OUTPUT"
    fi
}

# Función para borrar documentos con query específica
delete_by_query() {
    local index="$1"
    local query="$2"
    
    echo -e "${BLUE}🔍 Borrando documentos que coincidan con query en ${index}...${NC}"
    echo -e "${YELLOW}Query: ${query}${NC}"
    
    COMMAND="if command -v awscurl &> /dev/null; then
    awscurl --service es --region ${REGION} -X POST 'https://${OPENSEARCH_HOST}/${index}/_delete_by_query?conflicts=proceed&refresh=true' -H 'Content-Type: application/json' -d '{\"query\":${query}}'
else
    echo 'ERROR: awscurl no está instalado. Instala con: pip3 install awscurl'
fi"
    
    RESULT=$(run_on_ec2 "$COMMAND")
    
    STATUS=$(echo "$RESULT" | jq -r '.[0]')
    OUTPUT=$(echo "$RESULT" | jq -r '.[1]')
    
    if [ "$STATUS" == "Success" ]; then
        echo -e "${GREEN}✅ Documentos borrados:${NC}"
        echo "$OUTPUT" | python3 -m json.tool 2>/dev/null || echo "$OUTPUT"
    else
        echo -e "${RED}❌ Error borrando documentos${NC}"
        echo "$OUTPUT"
    fi
}

# Función para borrar índice completo
delete_index() {
    local index="$1"
    
    echo -e "${RED}⚠️  ADVERTENCIA: Vas a borrar el ÍNDICE COMPLETO: ${index}${NC}"
    echo -e "${RED}   Esto incluye todos los documentos Y la configuración del índice${NC}"
    read -p "¿Estás seguro? (yes/no): " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        echo -e "${RED}❌ Operación cancelada${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}🗑️  Borrando índice ${index}...${NC}"
    
    COMMAND="if command -v awscurl &> /dev/null; then
    awscurl --service es --region ${REGION} -X DELETE https://${OPENSEARCH_HOST}/${index}
else
    echo 'ERROR: awscurl no está instalado. Instala con: pip3 install awscurl'
fi"
    
    RESULT=$(run_on_ec2 "$COMMAND")
    
    STATUS=$(echo "$RESULT" | jq -r '.[0]')
    OUTPUT=$(echo "$RESULT" | jq -r '.[1]')
    
    if [ "$STATUS" == "Success" ]; then
        echo -e "${GREEN}✅ Índice borrado:${NC}"
        echo "$OUTPUT" | python3 -m json.tool 2>/dev/null || echo "$OUTPUT"
    else
        echo -e "${RED}❌ Error borrando índice${NC}"
        echo "$OUTPUT"
    fi
}

# Main
case "${1:-help}" in
    "list")
        list_indices
        ;;
    "delete-all")
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Error: Debes especificar el nombre del índice${NC}"
            show_usage
            exit 1
        fi
        delete_all_documents "$2"
        ;;
    "delete-by-query")
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo -e "${RED}❌ Error: Debes especificar el índice y la query${NC}"
            show_usage
            exit 1
        fi
        delete_by_query "$2" "$3"
        ;;
    "delete-index")
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Error: Debes especificar el nombre del índice${NC}"
            show_usage
            exit 1
        fi
        delete_index "$2"
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        echo -e "${RED}❌ Comando no reconocido: $1${NC}"
        show_usage
        exit 1
        ;;
esac
