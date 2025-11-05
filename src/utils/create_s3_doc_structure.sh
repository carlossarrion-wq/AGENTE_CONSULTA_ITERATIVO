#!/bin/bash

################################################################################
# Script: create_s3_doc_structure.sh
# Descripción: Crea la estructura de documentación del sistema en un bucket S3
# Uso: ./create_s3_doc_structure.sh <bucket-name> [region]
# Ejemplo: ./create_s3_doc_structure.sh my-docs-bucket eu-west-1
################################################################################

set -e  # Salir si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para mostrar uso
show_usage() {
    echo -e "${BLUE}Uso:${NC}"
    echo "  $0 <bucket-name> [region] [path-prefix]"
    echo ""
    echo -e "${BLUE}Parámetros:${NC}"
    echo "  bucket-name : Nombre del bucket S3 (requerido)"
    echo "  region      : Región de AWS (opcional, por defecto: eu-west-1)"
    echo "  path-prefix : Prefijo de ruta dentro del bucket (opcional, ej: documents/)"
    echo ""
    echo -e "${BLUE}Ejemplos:${NC}"
    echo "  $0 my-docs-bucket"
    echo "  $0 my-docs-bucket eu-west-1"
    echo "  $0 my-docs-bucket eu-west-1 documents/"
    echo "  $0 rag-system-darwin-eu-west-1 eu-west-1 documents/"
    echo "  $0 arn:aws:s3:::my-docs-bucket eu-west-1 applications/sap/"
    exit 1
}

# Función para extraer nombre del bucket desde ARN
extract_bucket_name() {
    local input=$1
    if [[ $input == arn:aws:s3:::* ]]; then
        echo "${input#arn:aws:s3:::}"
    else
        echo "$input"
    fi
}

# Función para crear un "directorio" en S3 (objeto con trailing slash)
create_s3_folder() {
    local bucket=$1
    local folder_path=$2
    local region=$3
    local path_prefix=$4
    
    # Combinar prefijo con ruta de carpeta
    local full_path="${path_prefix}${folder_path}"
    
    echo -e "${YELLOW}Creando carpeta:${NC} $full_path"
    
    # Crear un objeto vacío con trailing slash para simular carpeta
    aws s3api put-object \
        --bucket "$bucket" \
        --key "${full_path}/" \
        --region "$region" \
        --content-length 0 \
        > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Carpeta creada: $full_path/"
    else
        echo -e "${RED}✗${NC} Error al crear carpeta: $full_path/"
        return 1
    fi
}

# Función para crear archivo README en S3
create_readme() {
    local bucket=$1
    local folder_path=$2
    local region=$3
    local content=$4
    local path_prefix=$5
    
    # Combinar prefijo con ruta de carpeta
    local full_path="${path_prefix}${folder_path}"
    
    echo -e "${YELLOW}Creando README:${NC} ${full_path}/README.md"
    
    # Crear archivo temporal
    local temp_file=$(mktemp)
    echo "$content" > "$temp_file"
    
    # Subir archivo a S3
    aws s3 cp "$temp_file" \
        "s3://${bucket}/${full_path}/README.md" \
        --region "$region" \
        > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} README creado: ${full_path}/README.md"
    else
        echo -e "${RED}✗${NC} Error al crear README: ${full_path}/README.md"
    fi
    
    # Limpiar archivo temporal
    rm -f "$temp_file"
}

# Validar parámetros
if [ $# -lt 1 ]; then
    echo -e "${RED}Error: Faltan parámetros${NC}"
    show_usage
fi

# Parámetros
BUCKET_INPUT=$1
REGION=${2:-eu-west-1}
PATH_PREFIX=${3:-""}

# Extraer nombre del bucket (por si viene como ARN)
BUCKET_NAME=$(extract_bucket_name "$BUCKET_INPUT")

# Normalizar path prefix (asegurar que termine con / si no está vacío)
if [ -n "$PATH_PREFIX" ]; then
    # Remover / inicial si existe
    PATH_PREFIX="${PATH_PREFIX#/}"
    # Asegurar / final si no existe
    if [[ ! "$PATH_PREFIX" =~ /$ ]]; then
        PATH_PREFIX="${PATH_PREFIX}/"
    fi
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Creación de Estructura de Documentación en S3${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Bucket:${NC} $BUCKET_NAME"
echo -e "${BLUE}Región:${NC} $REGION"
if [ -n "$PATH_PREFIX" ]; then
    echo -e "${BLUE}Prefijo de ruta:${NC} $PATH_PREFIX"
fi
echo ""

# Verificar que AWS CLI está instalado
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI no está instalado${NC}"
    echo "Instala AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Verificar que el bucket existe
echo -e "${YELLOW}Verificando bucket...${NC}"
if ! aws s3 ls "s3://${BUCKET_NAME}" --region "$REGION" > /dev/null 2>&1; then
    echo -e "${RED}Error: El bucket '$BUCKET_NAME' no existe o no tienes permisos${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Bucket verificado"
echo ""

# Definir estructura de carpetas (solo primer nivel)
declare -a FOLDERS=(
    "01_Arquitectura_Sistema"
    "02_Especificaciones_Funcionales"
    "03_Diseño_Técnico_y_APIs"
    "04_Guías_de_Desarrollo"
    "05_Pruebas_y_Calidad"
    "06_Operaciones_y_Despliegue"
    "07_Seguridad_y_Cumplimiento"
    "08_Manual_Usuario_y_Soporte"
    "09_Histórico_y_Lecciones_Aprendidas"
    "10_Contactos_Clave"
    "11_Documentación_Código"
    "99_Referencias_Generales"
)

# Crear estructura de carpetas
echo -e "${BLUE}Creando estructura de carpetas...${NC}"
echo ""

TOTAL_FOLDERS=${#FOLDERS[@]}
CURRENT=0

for folder in "${FOLDERS[@]}"; do
    CURRENT=$((CURRENT + 1))
    echo -e "${BLUE}[$CURRENT/$TOTAL_FOLDERS]${NC}"
    create_s3_folder "$BUCKET_NAME" "$folder" "$REGION" "$PATH_PREFIX"
    echo ""
done

# Crear README principal
echo -e "${BLUE}Creando documentos README...${NC}"
echo ""

MAIN_README="# Estructura de Documentación del Sistema

Este bucket contiene la documentación completa del sistema organizada en las siguientes secciones:

- 01_Arquitectura_Sistema/
- 02_Especificaciones_Funcionales/
- 03_Diseño_Técnico_y_APIs/
- 04_Guías_de_Desarrollo/
- 05_Pruebas_y_Calidad/
- 06_Operaciones_y_Despliegue/
- 07_Seguridad_y_Cumplimiento/
- 08_Manual_Usuario_y_Soporte/
- 09_Histórico_y_Lecciones_Aprendidas/
- 10_Contactos_Clave/
- 11_Documentación_Código/
- 99_Referencias_Generales/

Para más información, consulte ESTRUCTURA_DOCUMENTACION.md
"

create_readme "$BUCKET_NAME" "" "$REGION" "$MAIN_README" "$PATH_PREFIX"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✓ Estructura creada exitosamente${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Bucket S3:${NC} s3://${BUCKET_NAME}"
echo -e "${BLUE}Región:${NC} $REGION"
if [ -n "$PATH_PREFIX" ]; then
    echo -e "${BLUE}Prefijo de ruta:${NC} $PATH_PREFIX"
    echo -e "${BLUE}Ruta completa:${NC} s3://${BUCKET_NAME}/${PATH_PREFIX}"
fi
echo -e "${BLUE}Total de carpetas creadas:${NC} $TOTAL_FOLDERS"
echo ""
echo -e "${YELLOW}Para ver la estructura:${NC}"
if [ -n "$PATH_PREFIX" ]; then
    echo "  aws s3 ls s3://${BUCKET_NAME}/${PATH_PREFIX} --recursive --region $REGION"
else
    echo "  aws s3 ls s3://${BUCKET_NAME}/ --recursive --region $REGION"
fi
echo ""
echo -e "${YELLOW}Para subir archivos:${NC}"
if [ -n "$PATH_PREFIX" ]; then
    echo "  aws s3 cp archivo.pdf s3://${BUCKET_NAME}/${PATH_PREFIX}01_Arquitectura_Sistema/Diagramas/ --region $REGION"
else
    echo "  aws s3 cp archivo.pdf s3://${BUCKET_NAME}/01_Arquitectura_Sistema/Diagramas/ --region $REGION"
fi
echo ""
