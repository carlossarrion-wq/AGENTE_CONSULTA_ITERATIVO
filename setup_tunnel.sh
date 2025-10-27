#!/bin/bash
# Script para configurar el túnel SSH a OpenSearch y probar las herramientas Darwin

set -e

echo "🚀 Configurando túnel SSH a OpenSearch Darwin..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
SSH_KEY="~/.ssh/ec2_new_key"
EC2_HOST="ec2-user@52.18.245.120"
OPENSEARCH_HOST="vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com"
LOCAL_PORT="9201"

echo -e "${BLUE}📋 Configuración:${NC}"
echo -e "   SSH Key: ${SSH_KEY}"
echo -e "   EC2 Host: ${EC2_HOST}"
echo -e "   OpenSearch: ${OPENSEARCH_HOST}"
echo -e "   Puerto local: ${LOCAL_PORT}"
echo ""

# Función para verificar si el túnel está activo
check_tunnel() {
    if pgrep -f "ssh.*${LOCAL_PORT}:${OPENSEARCH_HOST}:443" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Función para crear el túnel
create_tunnel() {
    echo -e "${YELLOW}🔧 Creando túnel SSH...${NC}"
    ssh -i ${SSH_KEY} -L ${LOCAL_PORT}:${OPENSEARCH_HOST}:443 -N -f ${EC2_HOST}
    
    # Esperar un momento para que se establezca
    sleep 2
    
    if check_tunnel; then
        echo -e "${GREEN}✅ Túnel SSH creado exitosamente${NC}"
        return 0
    else
        echo -e "${RED}❌ Error creando el túnel SSH${NC}"
        return 1
    fi
}

# Función para terminar túneles existentes
kill_existing_tunnels() {
    echo -e "${YELLOW}🔄 Terminando túneles SSH existentes...${NC}"
    pkill -f "ssh.*${LOCAL_PORT}:${OPENSEARCH_HOST}:443" 2>/dev/null || true
    sleep 1
}

# Función para verificar conectividad
test_connectivity() {
    echo -e "${YELLOW}🔍 Verificando conectividad...${NC}"
    
    # Test básico con curl
    if curl -k -s --max-time 5 https://localhost:${LOCAL_PORT}/_cluster/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Conectividad a OpenSearch verificada${NC}"
        return 0
    else
        echo -e "${RED}❌ No se puede conectar a OpenSearch${NC}"
        return 1
    fi
}

# Función para configurar variables de entorno
setup_environment() {
    echo -e "${YELLOW}🌍 Configurando variables de entorno...${NC}"
    
    export OPENSEARCH_HOST="localhost:${LOCAL_PORT}"
    export OPENSEARCH_USE_SSL="true"
    export OPENSEARCH_VERIFY_CERTS="false"
    
    echo -e "${GREEN}✅ Variables de entorno configuradas:${NC}"
    echo -e "   OPENSEARCH_HOST=${OPENSEARCH_HOST}"
    echo -e "   OPENSEARCH_USE_SSL=${OPENSEARCH_USE_SSL}"
    echo -e "   OPENSEARCH_VERIFY_CERTS=${OPENSEARCH_VERIFY_CERTS}"
}

# Función para probar las herramientas
test_tools() {
    echo -e "${YELLOW}🧪 Probando herramientas Darwin...${NC}"
    
    # Activar entorno virtual
    if [ -d "venv" ]; then
        source venv/bin/activate
        echo -e "${GREEN}✅ Entorno virtual activado${NC}"
    else
        echo -e "${RED}❌ Entorno virtual no encontrado${NC}"
        return 1
    fi
    
    # Test 1: Búsqueda léxica
    echo -e "${BLUE}🔍 Test 1: Búsqueda léxica...${NC}"
    if python3 src/lexical_search.py "darwin" --top-k 2 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Búsqueda léxica: OK${NC}"
    else
        echo -e "${RED}❌ Búsqueda léxica: FALLO${NC}"
    fi
    
    # Test 2: Búsqueda semántica
    echo -e "${BLUE}🔍 Test 2: Búsqueda semántica...${NC}"
    if python3 src/semantic_search.py "sistema" --top-k 2 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Búsqueda semántica: OK${NC}"
    else
        echo -e "${RED}❌ Búsqueda semántica: FALLO${NC}"
    fi
    
    # Test 3: Búsqueda regex
    echo -e "${BLUE}🔍 Test 3: Búsqueda regex...${NC}"
    if python3 src/regex_search.py "Darwin" --max-matches-per-file 2 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Búsqueda regex: OK${NC}"
    else
        echo -e "${RED}❌ Búsqueda regex: FALLO${NC}"
    fi
    
    echo -e "${GREEN}🎉 Todas las herramientas están funcionando correctamente!${NC}"
}

# Función para mostrar ayuda
show_help() {
    echo -e "${BLUE}📖 Uso del script:${NC}"
    echo -e "   $0 start    - Crear túnel y configurar entorno"
    echo -e "   $0 stop     - Terminar túnel SSH"
    echo -e "   $0 status   - Verificar estado del túnel"
    echo -e "   $0 test     - Probar herramientas"
    echo -e "   $0 restart  - Reiniciar túnel"
    echo ""
    echo -e "${BLUE}📝 Ejemplos de uso de herramientas:${NC}"
    echo -e "   python3 src/semantic_search.py 'configuración usuarios'"
    echo -e "   python3 src/lexical_search.py 'darwin' --top-k 10"
    echo -e "   python3 src/regex_search.py 'NU\\d+' --context-lines 3"
    echo -e "   python3 src/get_file_content.py 'archivo.docx'"
}

# Función principal
main() {
    case "${1:-start}" in
        "start")
            echo -e "${BLUE}🚀 Iniciando configuración completa...${NC}"
            kill_existing_tunnels
            if create_tunnel && test_connectivity; then
                setup_environment
                echo ""
                echo -e "${GREEN}🎉 ¡Configuración completada exitosamente!${NC}"
                echo -e "${BLUE}💡 Ahora puedes usar las herramientas Darwin:${NC}"
                echo -e "   source venv/bin/activate"
                echo -e "   python3 src/lexical_search.py 'darwin'"
                echo ""
                echo -e "${YELLOW}⚠️  Para terminar el túnel: $0 stop${NC}"
            else
                echo -e "${RED}❌ Error en la configuración${NC}"
                exit 1
            fi
            ;;
        "stop")
            echo -e "${YELLOW}🛑 Terminando túnel SSH...${NC}"
            kill_existing_tunnels
            echo -e "${GREEN}✅ Túnel terminado${NC}"
            ;;
        "status")
            if check_tunnel; then
                echo -e "${GREEN}✅ Túnel SSH activo${NC}"
                test_connectivity
            else
                echo -e "${RED}❌ Túnel SSH no activo${NC}"
            fi
            ;;
        "test")
            if check_tunnel; then
                setup_environment
                test_tools
            else
                echo -e "${RED}❌ Túnel no activo. Ejecuta: $0 start${NC}"
                exit 1
            fi
            ;;
        "restart")
            echo -e "${YELLOW}🔄 Reiniciando túnel...${NC}"
            kill_existing_tunnels
            sleep 2
            create_tunnel
            test_connectivity
            setup_environment
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            echo -e "${RED}❌ Comando no reconocido: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

# Ejecutar función principal
main "$@"
