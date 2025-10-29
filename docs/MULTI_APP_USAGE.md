# Guía de Uso Multi-Aplicación

## Descripción

El Agente IA de Consulta ahora soporta múltiples aplicaciones, permitiendo consultar diferentes bases de conocimiento (Darwin, SAP ISU, MuleSoft) con una sola herramienta.

## Aplicaciones Soportadas

### 1. Darwin
- **Descripción**: Sistema Darwin - Gestión de clientes y contratos
- **Índice OpenSearch**: `rag-documents-darwin`
- **Repositorio S3**: `applications/darwin/`
- **Configuración**: `config/config_darwin.yaml`
- **System Prompt**: `config/system_prompt_darwin.md`

### 2. SAP ISU
- **Descripción**: Sistema SAP ISU - ERP empresarial
- **Índice OpenSearch**: `rag-documents-sap`
- **Repositorio S3**: `applications/sap/`
- **Configuración**: `config/config_sap.yaml`
- **System Prompt**: `config/system_prompt_sap.md`

### 3. MuleSoft
- **Descripción**: MuleSoft - Plataforma de integración
- **Índice OpenSearch**: `rag-documents-mulesoft`
- **Repositorio S3**: `applications/mulesoft/`
- **Configuración**: `config/config_mulesoft.yaml`
- **System Prompt**: `config/system_prompt_mulesoft.md`

## Uso

### Sintaxis Básica

```bash
python3 src/agent/main.py --app <nombre_aplicacion>
```

### Ejemplos

#### Consultar Darwin (por defecto)
```bash
python3 src/agent/main.py --app darwin
```

o simplemente:
```bash
python3 src/agent/main.py
```

#### Consultar SAP ISU
```bash
python3 src/agent/main.py --app sap
```

#### Consultar MuleSoft
```bash
python3 src/agent/main.py --app mulesoft
```

### Opciones Avanzadas

#### Usar configuración personalizada
```bash
python3 src/agent/main.py --app darwin --config /ruta/a/mi_config.yaml
```

#### Usar system prompt personalizado
```bash
python3 src/agent/main.py --app sap --system-prompt /ruta/a/mi_prompt.md
```

#### Combinar opciones
```bash
python3 src/agent/main.py --app mulesoft \
  --config config/config_custom.yaml \
  --system-prompt config/system_prompt_custom.md
```

## Ver Ayuda

Para ver todas las opciones disponibles:

```bash
python3 src/agent/main.py --help
```

Salida:
```
usage: main.py [-h] [--app {darwin,sap,mulesoft}] [--config CONFIG] [--system-prompt SYSTEM_PROMPT]

Agente IA de Consulta Multi-Aplicación

optional arguments:
  -h, --help            show this help message and exit
  --app {darwin,sap,mulesoft}
                        Aplicación a consultar (default: darwin)
  --config CONFIG       Ruta personalizada al archivo de configuración (opcional)
  --system-prompt SYSTEM_PROMPT
                        Ruta personalizada al system prompt (opcional)

Aplicaciones soportadas:
  darwin: Sistema Darwin - Gestión de clientes y contratos
  sap: Sistema SAP - ERP empresarial
  mulesoft: MuleSoft - Plataforma de integración

Ejemplos:
  python3 src/agent/main.py --app darwin
  python3 src/agent/main.py --app sap
  python3 src/agent/main.py --app mulesoft
```

## Estructura de Archivos

```
AGENTE_CONSULTA_ITERATIVO/
├── config/
│   ├── config_darwin.yaml          # Configuración Darwin
│   ├── config_sap.yaml             # Configuración SAP
│   ├── config_mulesoft.yaml        # Configuración MuleSoft
│   ├── system_prompt_darwin.md     # Prompt Darwin
│   ├── system_prompt_sap.md        # Prompt SAP
│   └── system_prompt_mulesoft.md   # Prompt MuleSoft
├── src/
│   └── agent/
│       ├── main.py                 # Punto de entrada con --app
│       └── chat_interface.py       # Interfaz adaptada
└── docs/
    └── MULTI_APP_USAGE.md          # Esta guía
```

## Configuración por Aplicación

Cada aplicación tiene su propia configuración que especifica:

1. **Índice de OpenSearch**: Dónde buscar los documentos
2. **Repositorio S3**: Dónde están los resúmenes
3. **System Prompt**: Instrucciones específicas del dominio
4. **Parámetros del LLM**: Configuración del modelo

### Ejemplo de Configuración (config_darwin.yaml)

```yaml
opensearch:
  index_name: "rag-documents-darwin"
  
s3:
  prefix: "applications/darwin/"
  
agent:
  system_prompt_file: "config/system_prompt_darwin.md"
```

## Añadir Nueva Aplicación

Para añadir una nueva aplicación (ej: "erp"):

### 1. Crear archivos de configuración

```bash
# Copiar plantilla
cp config/config_darwin.yaml config/config_erp.yaml
cp config/system_prompt_darwin.md config/system_prompt_erp.md
```

### 2. Editar config_erp.yaml

```yaml
opensearch:
  index_name: "rag-documents-erp"  # Cambiar índice

s3:
  prefix: "applications/erp/"       # Cambiar prefijo

agent:
  system_prompt_file: "config/system_prompt_erp.md"
```

### 3. Personalizar system_prompt_erp.md

Adaptar el prompt al dominio específico de la nueva aplicación.

### 4. Registrar en main.py

Editar `src/agent/main.py` y añadir en `SUPPORTED_APPS`:

```python
SUPPORTED_APPS = {
    'darwin': {...},
    'sap': {...},
    'mulesoft': {...},
    'erp': {  # Nueva aplicación
        'name': 'ERP',
        'config_file': 'config/config_erp.yaml',
        'system_prompt': 'config/system_prompt_erp.md',
        'description': 'Sistema ERP - Gestión empresarial'
    }
}
```

### 5. Usar la nueva aplicación

```bash
python3 src/agent/main.py --app erp
```

## Validación

El sistema valida automáticamente que existan:
- ✅ Archivo de configuración
- ✅ System prompt
- ✅ Índice de OpenSearch (en runtime)
- ✅ Repositorio S3 (en runtime)

Si falta algún archivo, mostrará un error descriptivo:

```
ERROR: Archivo de configuración no encontrado: config/config_erp.yaml
INFO: Crea el archivo config/config_erp.yaml basándote en config/config_darwin.yaml
```

## Troubleshooting

### Error: "Archivo de configuración no encontrado"
**Solución**: Verifica que el archivo existe en la ruta especificada.

### Error: "System prompt no encontrado"
**Solución**: Crea el archivo de system prompt o especifica una ruta válida con `--system-prompt`.

### Error: "Índice no encontrado en OpenSearch"
**Solución**: Verifica que el índice existe en OpenSearch y que el nombre es correcto en la configuración.

### Warning: "Connecting to localhost:9201 using SSL with verify_certs=False is insecure"
**Solución**: Este warning es normal en desarrollo local con túnel SSH. No afecta el funcionamiento.

## Mejores Prácticas

1. **Mantén consistencia**: Usa la misma estructura para todas las aplicaciones
2. **Documenta cambios**: Actualiza los system prompts cuando cambies el dominio
3. **Prueba configuraciones**: Valida cada nueva aplicación antes de usarla en producción
4. **Usa nombres descriptivos**: Los nombres de aplicación deben ser claros y concisos
5. **Versiona configuraciones**: Mantén las configuraciones en control de versiones

## Soporte

Para más información o reportar problemas:
- Revisa los logs en `logs/agent.log`
- Consulta la documentación en `docs/`
- Contacta al equipo de desarrollo
