# Modo Permisivo del Web Crawler

## Resumen

Se ha implementado un **modo permisivo** en la herramienta `web_crawler` para solucionar el problema de las listas blancas (whitelist) demasiado restrictivas que impedían acceder a muchas URLs relevantes.

## Problema Original

La configuración original del web crawler utilizaba listas blancas estrictas (`allowed_domains`) que solo permitían acceder a un conjunto muy limitado de dominios por aplicación. Esto causaba que muchas búsquedas fallaran con el error:

```
Error: No se encontraron fuentes permitidas
```

## Solución Implementada

### Modo Permisivo Configurable

Se ha añadido un sistema de dos modos de operación:

1. **Modo Estricto** (whitelist): Solo permite dominios explícitamente listados
2. **Modo Permisivo** (blacklist): Permite todos los dominios excepto los bloqueados

### Configuración

En `config/web_crawler_config.yaml`:

```yaml
global:
  # Modo permisivo: false = whitelist estricta, true = solo blacklist
  permissive_mode: true
  
  # Dominios bloqueados en modo permisivo (blacklist)
  blocked_domains:
    - porn.com
    - xxx.com
    - casino.com
    - gambling.com
    - torrent.com
    - piratebay.org
    - thepiratebay.org
```

### Comportamiento

#### Modo Permisivo (permissive_mode: true)
- ✅ Permite **cualquier dominio** por defecto
- ❌ Bloquea solo los dominios en `blocked_domains`
- 🔓 Más flexible para búsquedas generales
- ⚠️ Mantiene controles de seguridad con `forbidden_keywords`

#### Modo Estricto (permissive_mode: false)
- ✅ Permite solo dominios en `allowed_domains`
- ❌ Bloquea todo lo demás
- 🔒 Máxima seguridad
- 📋 Requiere mantenimiento manual de la whitelist

## Cambios en el Código

### Clase `DomainWhitelist`

```python
class DomainWhitelist:
    def __init__(self, config: WebCrawlerConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Obtener configuración de modo permisivo
        global_config = config.get_global_config()
        self.permissive_mode = global_config.get('permissive_mode', False)
        self.blocked_domains = global_config.get('blocked_domains', [])
        
        if self.permissive_mode:
            self.logger.info("🔓 Modo permisivo activado - usando blacklist")
        else:
            self.logger.info("🔒 Modo estricto activado - usando whitelist")
    
    def is_allowed(self, url: str, app_name: str) -> bool:
        """Verifica si una URL está permitida"""
        domain = urlparse(url).netloc.replace('www.', '')
        
        # Modo permisivo: bloquear solo dominios en blacklist
        if self.permissive_mode:
            return self._is_allowed_permissive(domain)
        
        # Modo estricto: permitir solo dominios en whitelist
        return self._is_allowed_strict(domain, app_name)
```

## Controles de Seguridad Mantenidos

Aunque el modo permisivo es más flexible, se mantienen múltiples capas de seguridad:

1. **Blacklist de dominios**: Bloquea sitios peligrosos conocidos
2. **Forbidden keywords**: Rechaza queries con contenido inapropiado
3. **Required keywords**: Asegura que las búsquedas sean relevantes a la aplicación
4. **Rate limiting**: Previene abuso del servicio
5. **Validación de queries**: Verifica longitud y contenido

## Pruebas

Se ha creado un script de prueba `test_permissive_mode.py` que verifica:

- ✅ Búsquedas funcionan con dominios variados
- ✅ Modo permisivo permite 10/10 URLs (vs 0/10 en modo estricto)
- ✅ Dominios bloqueados son rechazados correctamente
- ✅ Controles de seguridad siguen activos

### Resultados de Prueba

```
📝 Test 1: Búsqueda sobre MuleSoft latest version
✅ Éxito: 3 URLs encontradas
⏱️  Tiempo: 346ms

📋 URLs recomendadas:
  1. https://www.mulesoft.com/es
  2. https://en.wikipedia.org/wiki/MuleSoft
  3. https://www.salesforce.com/mulesoft/what-is-mulesoft/

📊 Configuración actual:
  - Modo permisivo: True
  - Dominios bloqueados: 7
  - Max resultados: 3
```

## Cómo Cambiar de Modo

### Activar Modo Permisivo (Recomendado)

```yaml
# config/web_crawler_config.yaml
global:
  permissive_mode: true
```

### Volver a Modo Estricto

```yaml
# config/web_crawler_config.yaml
global:
  permissive_mode: false
```

## Recomendaciones

1. **Usar modo permisivo por defecto**: Proporciona mejor experiencia de usuario
2. **Mantener blacklist actualizada**: Añadir dominios peligrosos según sea necesario
3. **Monitorear logs**: Revisar qué dominios se están accediendo
4. **Ajustar según necesidad**: Cambiar a modo estricto si se requiere más control

## Ventajas del Modo Permisivo

- ✅ **Más flexible**: Accede a cualquier fuente relevante
- ✅ **Menos mantenimiento**: No requiere actualizar whitelist constantemente
- ✅ **Mejor cobertura**: Encuentra información en más sitios
- ✅ **Mantiene seguridad**: Blacklist + validación de keywords
- ✅ **Fácil de configurar**: Un solo flag para cambiar de modo

## Archivos Modificados

1. `config/web_crawler_config.yaml` - Añadido `permissive_mode` y `blocked_domains`
2. `src/tools/tool_web_crawler.py` - Modificada clase `DomainWhitelist`
3. `test_permissive_mode.py` - Script de prueba (nuevo)
4. `docs/WEB_CRAWLER_PERMISSIVE_MODE.md` - Esta documentación (nuevo)

## Fecha de Implementación

30 de octubre de 2025
