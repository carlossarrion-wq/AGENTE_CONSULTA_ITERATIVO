#!/bin/bash
# Script para iniciar el túnel SSH a OpenSearch en segundo plano

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TUNNEL_LOG="${SCRIPT_DIR}/tunnel.log"
TUNNEL_PID="${SCRIPT_DIR}/tunnel.pid"
LOCAL_PORT="9201"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Función para verificar si el túnel está activo
check_tunnel() {
    if [ -f "$TUNNEL_PID" ]; then
        PID=$(cat "$TUNNEL_PID")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Función para terminar el túnel
stop_tunnel() {
    if [ -f "$TUNNEL_PID" ]; then
        PID=$(cat "$TUNNEL_PID")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo -e "${YELLOW}🛑 Terminando túnel (PID: $PID)...${NC}"
            kill "$PID" 2>/dev/null || true
            sleep 2
            # Force kill si aún está corriendo
            if ps -p "$PID" > /dev/null 2>&1; then
                kill -9 "$PID" 2>/dev/null || true
            fi
            rm -f "$TUNNEL_PID"
            echo -e "${GREEN}✅ Túnel terminado${NC}"
        else
            rm -f "$TUNNEL_PID"
        fi
    else
        echo -e "${YELLOW}⚠️  No hay túnel activo${NC}"
    fi
}

# Función para iniciar el túnel
start_tunnel() {
    echo -e "${BLUE}🚀 Iniciando túnel SSH a OpenSearch...${NC}"
    
    # Activar entorno virtual si existe
    if [ -d "${SCRIPT_DIR}/venv" ]; then
        source "${SCRIPT_DIR}/venv/bin/activate"
    fi
    
    # Iniciar túnel en segundo plano
    nohup python3 "${SCRIPT_DIR}/aws_tunnel.py" > "$TUNNEL_LOG" 2>&1 &
    TUNNEL_PID_VALUE=$!
    echo "$TUNNEL_PID_VALUE" > "$TUNNEL_PID"
    
    echo -e "${YELLOW}⏳ Esperando a que el túnel se establezca...${NC}"
    sleep 5
    
    # Verificar que el proceso sigue corriendo
    if ! ps -p "$TUNNEL_PID_VALUE" > /dev/null 2>&1; then
        echo -e "${RED}❌ El túnel falló al iniciar${NC}"
        echo -e "${YELLOW}📋 Últimas líneas del log:${NC}"
        tail -20 "$TUNNEL_LOG"
        rm -f "$TUNNEL_PID"
        return 1
    fi
    
    # Verificar que el puerto está escuchando
    MAX_RETRIES=10
    RETRY=0
    while [ $RETRY -lt $MAX_RETRIES ]; do
        if lsof -i :${LOCAL_PORT} > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Túnel establecido exitosamente!${NC}"
            echo -e "${BLUE}   PID: $TUNNEL_PID_VALUE${NC}"
            echo -e "${BLUE}   Puerto: ${LOCAL_PORT}${NC}"
            echo -e "${BLUE}   Log: $TUNNEL_LOG${NC}"
            echo ""
            echo -e "${GREEN}🎉 Ahora puedes ejecutar el agente:${NC}"
            echo -e "   cd ${SCRIPT_DIR}"
            echo -e "   source venv/bin/activate"
            echo -e "   python3 src/agent/main.py"
            echo ""
            echo -e "${YELLOW}⚠️  Para terminar el túnel:${NC}"
            echo -e "   $0 stop"
            return 0
        fi
        RETRY=$((RETRY + 1))
        echo -e "${YELLOW}   Intento $RETRY/$MAX_RETRIES...${NC}"
        sleep 2
    done
    
    echo -e "${RED}❌ El túnel no pudo establecerse en el puerto ${LOCAL_PORT}${NC}"
    echo -e "${YELLOW}📋 Últimas líneas del log:${NC}"
    tail -20 "$TUNNEL_LOG"
    stop_tunnel
    return 1
}

# Función para mostrar el estado
status_tunnel() {
    if check_tunnel; then
        PID=$(cat "$TUNNEL_PID")
        echo -e "${GREEN}✅ Túnel activo${NC}"
        echo -e "   PID: $PID"
        echo -e "   Puerto: ${LOCAL_PORT}"
        
        # Verificar puerto
        if lsof -i :${LOCAL_PORT} > /dev/null 2>&1; then
            echo -e "   Estado puerto: ${GREEN}ESCUCHANDO${NC}"
            
            # Probar conexión
            if curl -k -s --max-time 2 https://localhost:${LOCAL_PORT}/_cluster/health > /dev/null 2>&1; then
                echo -e "   Conexión OpenSearch: ${GREEN}OK${NC}"
            else
                echo -e "   Conexión OpenSearch: ${RED}FALLO${NC}"
            fi
        else
            echo -e "   Estado puerto: ${RED}NO ESCUCHANDO${NC}"
        fi
    else
        echo -e "${RED}❌ Túnel no activo${NC}"
    fi
}

# Función para mostrar el log
show_log() {
    if [ -f "$TUNNEL_LOG" ]; then
        echo -e "${BLUE}📋 Log del túnel:${NC}"
        tail -50 "$TUNNEL_LOG"
    else
        echo -e "${YELLOW}⚠️  No hay log disponible${NC}"
    fi
}

# Función principal
main() {
    case "${1:-start}" in
        "start")
            if check_tunnel; then
                echo -e "${YELLOW}⚠️  El túnel ya está activo${NC}"
                status_tunnel
            else
                start_tunnel
            fi
            ;;
        "stop")
            stop_tunnel
            ;;
        "restart")
            stop_tunnel
            sleep 2
            start_tunnel
            ;;
        "status")
            status_tunnel
            ;;
        "log")
            show_log
            ;;
        "help"|"-h"|"--help")
            echo -e "${BLUE}📖 Uso:${NC}"
            echo -e "   $0 start    - Iniciar túnel en segundo plano"
            echo -e "   $0 stop     - Terminar túnel"
            echo -e "   $0 restart  - Reiniciar túnel"
            echo -e "   $0 status   - Ver estado del túnel"
            echo -e "   $0 log      - Ver log del túnel"
            ;;
        *)
            echo -e "${RED}❌ Comando no reconocido: $1${NC}"
            echo -e "   Usa: $0 help"
            exit 1
            ;;
    esac
}

# Ejecutar
main "$@"
