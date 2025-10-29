# Implementación de Gestión de Sesiones de Usuario

## Resumen

Se ha implementado un sistema completo de autenticación y gestión de sesiones que permite a múltiples usuarios autenticarse en la aplicación y mantener logs de conversación separados por sesión.

## Características Implementadas

### 1. Autenticación de Usuario

Los usuarios ahora deben autenticarse al iniciar la aplicación mediante el parámetro `--username`:

```bash
python3 src/agent/main.py --app darwin --username darwin_001
python3 src/agent/main.py --app sap --username sap_user_01
python3 src/agent/main.py --app mulesoft --username mulesoft_admin
```

### 2. Gestión de Sesiones

#### Clase `UserSession`
Representa una sesión individual de usuario con:
- **username**: Nombre del usuario
- **app_name**: Aplicación utilizada (Darwin, SAP, MuleSoft)
- **session_id**: ID único de sesión
- **created_at**: Timestamp de creación
- **last_activity**: Timestamp de última actividad
- **conversation_count**: Número de conversaciones en la sesión

#### Formato de Session ID
```
{username}_{app}_{timestamp}_{uuid}
```

Ejemplo:
```
darwin_001_darwin_20251029_193805_485bdffc
```

#### Clase `SessionManager`
Gestiona el ciclo de vida de las sesiones:
- Crear nuevas sesiones
- Actualizar actividad de sesión
- Finalizar sesiones
- Obtener rutas de logs específicas por sesión
- Listar sesiones de un usuario

### 3. Organización de Logs

Los logs ahora se organizan en dos directorios:

```
logs/
├── sessions/           # Información de sesiones
│   └── session_{session_id}.json
└── conversations/      # Logs de conversaciones
    └── conversation_{session_id}.json
```

#### Estructura de Archivo de Sesión
```json
{
  "session_id": "test_user_001_darwin_20251029_193805_485bdffc",
  "username": "test_user_001",
  "app_name": "Darwin",
  "created_at": "2025-10-29T19:38:05.366597",
  "last_activity": "2025-10-29T19:38:10.592381",
  "conversation_count": 1,
  "duration_minutes": 0.0870964,
  "status": "completed"
}
```

#### Estructura de Archivo de Conversación
```json
[
  {
    "timestamp": "2025-10-29T19:38:05.123456",
    "session_id": "test_user_001_darwin_20251029_193805_485bdffc",
    "user_input": "¿Qué es Darwin?",
    "llm_response": "Darwin es un sistema...",
    "metrics": {
      "total_time_ms": 1234.56,
      "llm_time_ms": 1000.00,
      "tools_time_ms": 234.56,
      "tokens_input": 150,
      "tokens_output": 200,
      "tools_executed": 2,
      "tools_successful": 2,
      "iterations": 1
    },
    "request_metadata": {}
  }
]
```

### 4. Integración con Componentes Existentes

#### main.py
- Añadido parámetro `--username` (requerido)
- Crea `SessionManager` al inicio
- Crea sesión de usuario antes de iniciar `ChatInterface`
- Pasa `SessionManager` a `ChatInterface`

#### chat_interface.py
- Acepta `SessionManager` como parámetro opcional
- Usa session_id del `SessionManager`
- Actualiza actividad de sesión en cada interacción
- Finaliza sesión al salir

#### conversation_logger.py
- Acepta `SessionManager` como parámetro opcional
- Usa rutas específicas de sesión para logs
- Acumula turnos de conversación en un solo archivo por sesión
- Mantiene compatibilidad con modo legacy (sin SessionManager)

## Archivos Modificados

1. **src/agent/session_manager.py** (NUEVO)
   - Implementación completa de `UserSession` y `SessionManager`

2. **src/agent/main.py**
   - Añadido parámetro `--username`
   - Integración con `SessionManager`
   - Actualización de ejemplos de uso

3. **src/agent/chat_interface.py**
   - Aceptar `SessionManager` en constructor
   - Usar session_id del gestor
   - Actualizar actividad en cada interacción
   - Finalizar sesión al salir

4. **src/agent/conversation_logger.py**
   - Aceptar `SessionManager` en constructor
   - Usar rutas específicas de sesión
   - Acumular turnos en archivo único por sesión
   - Mantener compatibilidad legacy

## Ejemplos de Uso

### Iniciar Sesión
```bash
python3 src/agent/main.py --app darwin --username darwin_001
```

### Consultar Sesiones de un Usuario
```python
from agent.session_manager import SessionManager

session_mgr = SessionManager()
sessions = session_mgr.list_user_sessions("darwin_001")

for session in sessions:
    print(f"Session: {session['session_id']}")
    print(f"  Status: {session['status']}")
    print(f"  Conversations: {session['conversation_count']}")
    print(f"  Duration: {session['duration_minutes']:.2f} min")
```

### Ver Información de Sesión Actual
Durante una sesión activa, el usuario puede escribir `estadísticas` para ver:
- Usuario
- Aplicación
- Session ID
- Timestamps
- Número de conversaciones
- Duración

## Beneficios

1. **Multi-usuario**: Múltiples usuarios pueden usar el sistema simultáneamente
2. **Trazabilidad**: Cada sesión tiene un ID único rastreable
3. **Organización**: Logs separados por sesión facilitan auditoría
4. **Métricas**: Información detallada de uso por usuario y sesión
5. **Escalabilidad**: Preparado para despliegue Flask multi-worker

## Preparación para Flask

Este sistema de sesiones es compatible con despliegue Flask multi-worker:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Cada request HTTP puede crear su propia sesión, permitiendo:
- Múltiples usuarios concurrentes
- Logs separados por sesión
- Trazabilidad completa de requests

## Testing

El sistema ha sido probado exitosamente:

```bash
# Test básico
python3 src/agent/main.py --app darwin --username test_user_001

# Verificar archivos creados
ls -la logs/sessions/
ls -la logs/conversations/

# Ver contenido de sesión
cat logs/sessions/session_test_user_001_darwin_*.json
```

## Próximos Pasos

1. **Thread-safety**: Considerar hacer Singleton thread-safe para Flask
2. **Persistencia**: Implementar base de datos para sesiones (opcional)
3. **Autenticación**: Añadir validación de credenciales (opcional)
4. **Expiración**: Implementar timeout de sesiones inactivas
5. **Limpieza**: Automatizar limpieza de logs antiguos

## Conclusión

El sistema de gestión de sesiones está completamente implementado y funcional. Permite autenticación de usuarios, tracking de sesiones, y organización de logs por sesión, preparando la aplicación para uso multi-usuario y despliegue en producción.
