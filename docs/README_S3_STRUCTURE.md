# Script de Creación de Estructura de Documentación en S3

## Descripción

Script bash que utiliza AWS CLI para crear automáticamente la estructura completa de documentación del sistema en un bucket de Amazon S3.

## Requisitos Previos

1. **AWS CLI instalado**: 
   ```bash
   # Verificar instalación
   aws --version
   
   # Instalar si es necesario (macOS)
   brew install awscli
   ```

2. **Credenciales AWS configuradas**:
   ```bash
   aws configure
   ```

3. **Permisos necesarios**:
   - `s3:ListBucket`
   - `s3:PutObject`
   - `s3:GetObject`

## Uso

### Sintaxis Básica

```bash
./create_s3_doc_structure.sh <bucket-name> [region]
```

### Parámetros

- **bucket-name** (requerido): Nombre del bucket S3 o ARN completo
- **region** (opcional): Región de AWS (por defecto: `eu-west-1`)

### Ejemplos

#### Ejemplo 1: Bucket con región por defecto (eu-west-1)
```bash
./src/utils/create_s3_doc_structure.sh my-docs-bucket
```

#### Ejemplo 2: Bucket con región específica
```bash
./src/utils/create_s3_doc_structure.sh my-docs-bucket us-east-1
```

#### Ejemplo 3: Usando ARN completo
```bash
./src/utils/create_s3_doc_structure.sh arn:aws:s3:::my-docs-bucket eu-west-1
```

## Estructura Creada

El script crea la siguiente estructura de carpetas de primer nivel en S3:

```
s3://bucket-name/
├── 01_Arquitectura_Sistema/
├── 02_Especificaciones_Funcionales/
├── 03_Diseño_Técnico_y_APIs/
├── 04_Guías_de_Desarrollo/
├── 05_Pruebas_y_Calidad/
├── 06_Operaciones_y_Despliegue/
├── 07_Seguridad_y_Cumplimiento/
├── 08_Manual_Usuario_y_Soporte/
├── 09_Histórico_y_Lecciones_Aprendidas/
├── 10_Contactos_Clave/
├── 11_Documentación_Código/
└── 99_Referencias_Generales/
```

**Nota**: El script crea únicamente las carpetas de primer nivel. Las subcarpetas pueden ser creadas posteriormente según las necesidades específicas de cada proyecto.

## Características

### ✅ Validaciones
- Verifica que AWS CLI esté instalado
- Valida que el bucket existe y es accesible
- Extrae automáticamente el nombre del bucket desde ARN
- Manejo de errores con mensajes claros

### 🎨 Output Colorizado
- Mensajes informativos en azul
- Éxitos en verde
- Advertencias en amarillo
- Errores en rojo

### 📁 Creación de Carpetas
- Crea objetos con trailing slash (`/`) para simular carpetas en S3
- Total de 12 carpetas de primer nivel creadas
- Progreso visible durante la ejecución

### 📄 README Automático
- Crea un README.md en la raíz del bucket
- Documenta la estructura creada

## Verificación Post-Ejecución

### Ver estructura completa
```bash
aws s3 ls s3://my-docs-bucket/ --recursive --region eu-west-1
```

### Ver solo carpetas principales
```bash
aws s3 ls s3://my-docs-bucket/ --region eu-west-1
```

### Descargar README
```bash
aws s3 cp s3://my-docs-bucket/README.md . --region eu-west-1
```

## Subir Documentos

### Subir un archivo individual
```bash
aws s3 cp documento.pdf s3://my-docs-bucket/01_Arquitectura_Sistema/Diagramas/ --region eu-west-1
```

### Subir una carpeta completa
```bash
aws s3 sync ./local-docs/ s3://my-docs-bucket/01_Arquitectura_Sistema/ --region eu-west-1
```

### Subir con metadatos
```bash
aws s3 cp documento.pdf s3://my-docs-bucket/01_Arquitectura_Sistema/Diagramas/ \
  --metadata "author=John Doe,version=1.0" \
  --region eu-west-1
```

## Gestión de Permisos

### Hacer un archivo público
```bash
aws s3api put-object-acl \
  --bucket my-docs-bucket \
  --key 01_Arquitectura_Sistema/Diagramas/diagram.png \
  --acl public-read \
  --region eu-west-1
```

### Configurar política de bucket
```bash
aws s3api put-bucket-policy \
  --bucket my-docs-bucket \
  --policy file://bucket-policy.json \
  --region eu-west-1
```

## Troubleshooting

### Error: "AWS CLI no está instalado"
```bash
# macOS
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### Error: "El bucket no existe o no tienes permisos"
```bash
# Verificar credenciales
aws sts get-caller-identity

# Verificar acceso al bucket
aws s3 ls s3://my-docs-bucket --region eu-west-1

# Verificar permisos
aws s3api get-bucket-acl --bucket my-docs-bucket --region eu-west-1
```

### Error: "Access Denied"
Asegúrate de tener los siguientes permisos en tu política IAM:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::my-docs-bucket",
        "arn:aws:s3:::my-docs-bucket/*"
      ]
    }
  ]
}
```

## Limpieza

### Eliminar toda la estructura
```bash
aws s3 rm s3://my-docs-bucket/ --recursive --region eu-west-1
```

### Eliminar una carpeta específica
```bash
aws s3 rm s3://my-docs-bucket/01_Arquitectura_Sistema/ --recursive --region eu-west-1
```

## Notas Importantes

1. **Costos**: Ten en cuenta que S3 cobra por almacenamiento y operaciones
2. **Versionado**: Considera habilitar versionado en el bucket para mantener historial
3. **Backup**: Configura replicación cross-region para backups críticos
4. **Lifecycle**: Define políticas de lifecycle para archivar documentos antiguos

## Referencias

- [AWS CLI S3 Documentation](https://docs.aws.amazon.com/cli/latest/reference/s3/)
- [S3 Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/best-practices.html)
- [IAM Policies for S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-policy-language-overview.html)
