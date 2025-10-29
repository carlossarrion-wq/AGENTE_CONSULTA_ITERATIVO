# Control de Seguridad y Contenido para Web Crawler

## Problema Identificado

**Pregunta del usuario:**
> "¿Cómo se puede controlar que el contenido sea 'apto' y esté alineado con el objetivo del agente? Es decir, que la gente no se dedique a visitar sitios no debidos o consultar información de carácter general"

## 🎯 Estrategias de Control

---

## 1. 🔒 Whitelist de Dominios Permitidos

### Concepto
Solo permitir búsquedas y acceso a dominios específicos relacionados con el negocio.

### Implementación

```python
class DomainWhitelist:
    """Control de dominios permitidos"""
    
    # Dominios permitidos por aplicación
    ALLOWED_DOMAINS = {
        'darwin': [
            'docs.darwin.com',
            'support.darwin.com',
            'community.darwin.com',
            'github.com/darwin',
            'stackoverflow.com'  # Solo para tags específicos
        ],
        'mulesoft': [
            'docs.mulesoft.com',
            'help.mulesoft.com',
            'blogs.mulesoft.com',
            'developer.mulesoft.com',
            'support.mulesoft.com',
            'github.com/mulesoft',
            'stackoverflow.com'
        ],
        'sap': [
            'help.sap.com',
            'support.sap.com',
            'community.sap.com',
            'blogs.sap.com',
            'launchpad.support.sap.com'
        ]
    }
    
    @classmethod
    def is_allowed(cls, url: str, app_name: str) -> bool:
        """
        Verifica si una URL está permitida para la aplicación
        
        Args:
            url: URL a verificar
            app_name: Nombre de la aplicación (darwin, mulesoft, sap)
            
        Returns:
            True si está permitida, False en caso contrario
        """
        from urllib.parse import urlparse
        
        domain = urlparse(url).netloc
        
        # Remover www. si existe
        domain = domain.replace('www.', '')
        
        allowed = cls.ALLOWED_DOMAINS.get(app_name.lower(), [])
        
        # Verificar si el dominio está en la whitelist
        for allowed_domain in allowed:
            if domain == allowed_domain or domain.endswith('.' + allowed_domain):
                return True
        
        return False
    
    @classmethod
    def filter_urls(cls, urls: list, app_name: str) -> list:
        """Filtra lista de URLs dejando solo las permitidas"""
        return [url for url in urls if cls.is_allowed(url, app_name)]
```

### Uso

```python
# En tool_web_crawler.py
def _search_duckduckgo(self, query: str, app_name: str) -> list:
    """Busca URLs usando DuckDuckGo y filtra por whitelist"""
    from duckduckgo_search import DDGS
    
    # Búsqueda
    results = DDGS().text(query, max_results=10)
    urls = [r['href'] for r in results]
    
    # Filtrar por whitelist
    allowed_urls = DomainWhitelist.filter_urls(urls, app_name)
    
    if not allowed_urls:
        raise ValueError(f"No se encontraron URLs permitidas para {app_name}")
    
    return allowed_urls[:self.max_results]
```

---

## 2. 🎯 Validación de Queries (Relevancia)

### Concepto
Validar que las queries estén relacionadas con el dominio de la aplicación antes de ejecutar la búsqueda.

### Implementación

```python
class QueryValidator:
    """Valida que las queries sean relevantes al dominio"""
    
    # Keywords obligatorias por aplicación
    REQUIRED_KEYWORDS = {
        'darwin': ['darwin', 'contrato', 'cliente', 'gestión'],
        'mulesoft': ['mulesoft', 'api', 'integration', 'runtime', 'anypoint'],
        'sap': ['sap', 'erp', 'hana', 'fiori', 's/4hana']
    }
    
    # Keywords prohibidas (contenido inapropiado)
    FORBIDDEN_KEYWORDS = [
        'porn', 'xxx', 'adult', 'casino', 'gambling',
        'torrent', 'pirate', 'crack', 'hack',
        'dating', 'escort', 'weapon', 'drug'
    ]
    
    @classmethod
    def is_valid_query(cls, query: str, app_name: str) -> tuple[bool, str]:
        """
        Valida si una query es apropiada
        
        Args:
            query: Query a validar
            app_name: Nombre de la aplicación
            
        Returns:
            (is_valid, reason)
        """
        query_lower = query.lower()
        
        # 1. Verificar keywords prohibidas
        for forbidden in cls.FORBIDDEN_KEYWORDS:
            if forbidden in query_lower:
                return False, f"Query contiene contenido prohibido: '{forbidden}'"
        
        # 2. Verificar que contenga al menos una keyword requerida
        required = cls.REQUIRED_KEYWORDS.get(app_name.lower(), [])
        has_required = any(keyword in query_lower for keyword in required)
        
        if not has_required:
            return False, f"Query debe contener al menos una de: {', '.join(required)}"
        
        # 3. Verificar longitud mínima
        if len(query.split()) < 3:
            return False, "Query demasiado corta. Debe ser más específica"
        
        return True, "Query válida"
    
    @classmethod
    def enhance_query(cls, query: str, app_name: str) -> str:
        """
        Mejora la query añadiendo contexto de la aplicación
        
        Args:
            query: Query original
            app_name: Nombre de la aplicación
            
        Returns:
            Query mejorada
        """
        # Añadir nombre de aplicación si no está presente
        app_lower = app_name.lower()
        query_lower = query.lower()
        
        if app_lower not in query_lower:
            query = f"{app_name} {query}"
        
        # Añadir términos técnicos para filtrar mejor
        technical_terms = {
            'mulesoft': 'documentation OR support OR release notes',
            'darwin': 'documentation OR manual OR guide',
            'sap': 'documentation OR help OR support'
        }
        
        if app_lower in technical_terms:
            query = f"{query} {technical_terms[app_lower]}"
        
        return query
```

### Uso

```python
# En tool_web_crawler.py
def search_and_extract(self, query: str, app_name: str) -> dict:
    """Busca con validación de query"""
    
    # 1. Validar query
    is_valid, reason = QueryValidator.is_valid_query(query, app_name)
    if not is_valid:
        return {
            'success': False,
            'error': f"Query rechazada: {reason}",
            'results_count': 0
        }
    
    # 2. Mejorar query
    enhanced_query = QueryValidator.enhance_query(query, app_name)
    
    # 3. Buscar
    urls = self._search_duckduckgo(enhanced_query, app_name)
    
    # ... resto del código
```

---

## 3. 🔍 Validación de Contenido Extraído

### Concepto
Analizar el contenido extraído para verificar que sea relevante y apropiado.

### Implementación

```python
class ContentValidator:
    """Valida contenido extraído"""
    
    @classmethod
    def is_relevant_content(cls, content: str, query: str, app_name: str) -> tuple[bool, float]:
        """
        Verifica si el contenido es relevante a la query
        
        Args:
            content: Contenido extraído
            query: Query original
            app_name: Nombre de la aplicación
            
        Returns:
            (is_relevant, relevance_score)
        """
        content_lower = content.lower()
        query_lower = query.lower()
        
        # 1. Calcular score de relevancia
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        
        # Palabras de la query presentes en el contenido
        matching_words = query_words.intersection(content_words)
        relevance_score = len(matching_words) / len(query_words) if query_words else 0
        
        # 2. Verificar keywords de la aplicación
        app_keywords = QueryValidator.REQUIRED_KEYWORDS.get(app_name.lower(), [])
        has_app_keywords = any(keyword in content_lower for keyword in app_keywords)
        
        # 3. Verificar contenido prohibido
        has_forbidden = any(
            forbidden in content_lower 
            for forbidden in QueryValidator.FORBIDDEN_KEYWORDS
        )
        
        # Decisión
        is_relevant = (
            relevance_score > 0.3 and  # Al menos 30% de palabras coinciden
            has_app_keywords and        # Contiene keywords de la app
            not has_forbidden           # No contiene contenido prohibido
        )
        
        return is_relevant, relevance_score
    
    @classmethod
    def sanitize_content(cls, content: str) -> str:
        """Limpia y sanitiza el contenido"""
        import re
        
        # Remover URLs
        content = re.sub(r'http[s]?://\S+', '[URL]', content)
        
        # Remover emails
        content = re.sub(r'\S+@\S+', '[EMAIL]', content)
        
        # Remover números de teléfono
        content = re.sub(r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}', '[PHONE]', content)
        
        # Limitar longitud de líneas muy largas
        lines = content.split('\n')
        cleaned_lines = [line[:500] if len(line) > 500 else line for line in lines]
        content = '\n'.join(cleaned_lines)
        
        return content
```

---

## 4. 📊 Sistema de Logging y Auditoría

### Concepto
Registrar todas las búsquedas web para auditoría y detección de uso indebido.

### Implementación

```python
class WebCrawlerAudit:
    """Sistema de auditoría para web crawler"""
    
    def __init__(self, logs_dir="logs/web_crawler"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def log_search(
        self,
        session_id: str,
        username: str,
        app_name: str,
        query: str,
        urls_found: list,
        urls_allowed: list,
        urls_blocked: list,
        success: bool,
        reason: str = None
    ):
        """Registra una búsqueda web"""
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'username': username,
            'app_name': app_name,
            'query': query,
            'urls_found': len(urls_found),
            'urls_allowed': urls_allowed,
            'urls_blocked': urls_blocked,
            'success': success,
            'reason': reason
        }
        
        # Guardar en archivo diario
        log_file = self.logs_dir / f"web_crawler_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        
        # Alertar si hay comportamiento sospechoso
        if urls_blocked:
            self._alert_blocked_urls(username, query, urls_blocked)
    
    def _alert_blocked_urls(self, username: str, query: str, urls_blocked: list):
        """Alerta sobre URLs bloqueadas"""
        logger = logging.getLogger(__name__)
        logger.warning(
            f"⚠️  Usuario {username} intentó acceder a URLs bloqueadas: "
            f"Query='{query}', URLs={urls_blocked}"
        )
    
    def get_user_stats(self, username: str, days: int = 7) -> dict:
        """Obtiene estadísticas de uso de un usuario"""
        
        stats = {
            'total_searches': 0,
            'blocked_attempts': 0,
            'queries': [],
            'blocked_urls': []
        }
        
        # Leer logs de los últimos N días
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            log_file = self.logs_dir / f"web_crawler_{date.strftime('%Y%m%d')}.jsonl"
            
            if not log_file.exists():
                continue
            
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    entry = json.loads(line)
                    if entry['username'] == username:
                        stats['total_searches'] += 1
                        stats['queries'].append(entry['query'])
                        
                        if entry['urls_blocked']:
                            stats['blocked_attempts'] += 1
                            stats['blocked_urls'].extend(entry['urls_blocked'])
        
        return stats
```

---

## 5. 🚨 Sistema de Alertas y Límites

### Concepto
Establecer límites de uso y alertas para detectar abuso.

### Implementación

```python
class UsageLimiter:
    """Control de límites de uso"""
    
    def __init__(self):
        self.usage_cache = {}  # {username: {date: count}}
    
    def check_limits(self, username: str) -> tuple[bool, str]:
        """
        Verifica si el usuario ha excedido límites
        
        Returns:
            (allowed, reason)
        """
        today = datetime.now().date().isoformat()
        
        # Obtener uso del día
        if username not in self.usage_cache:
            self.usage_cache[username] = {}
        
        daily_usage = self.usage_cache[username].get(today, 0)
        
        # Límites
        MAX_DAILY_SEARCHES = 20
        MAX_HOURLY_SEARCHES = 5
        
        # Verificar límite diario
        if daily_usage >= MAX_DAILY_SEARCHES:
            return False, f"Límite diario excedido ({MAX_DAILY_SEARCHES} búsquedas)"
        
        # Verificar límite por hora
        hourly_usage = self._get_hourly_usage(username)
        if hourly_usage >= MAX_HOURLY_SEARCHES:
            return False, f"Límite por hora excedido ({MAX_HOURLY_SEARCHES} búsquedas)"
        
        return True, "OK"
    
    def increment_usage(self, username: str):
        """Incrementa contador de uso"""
        today = datetime.now().date().isoformat()
        
        if username not in self.usage_cache:
            self.usage_cache[username] = {}
        
        self.usage_cache[username][today] = self.usage_cache[username].get(today, 0) + 1
    
    def _get_hourly_usage(self, username: str) -> int:
        """Obtiene uso en la última hora"""
        # Implementación simplificada
        # En producción, usar Redis o similar
        return 0
```

---

## 6. 🎯 Configuración por Aplicación

### Concepto
Cada aplicación tiene su propia configuración de seguridad.

### Implementación

```yaml
# config/web_crawler_config.yaml

darwin:
  enabled: true
  allowed_domains:
    - docs.darwin.com
    - support.darwin.com
  required_keywords:
    - darwin
    - contrato
    - cliente
  max_daily_searches: 20
  max_results_per_search: 3
  content_max_length: 2000

mulesoft:
  enabled: true
  allowed_domains:
    - docs.mulesoft.com
    - help.mulesoft.com
    - blogs.mulesoft.com
    - developer.mulesoft.com
  required_keywords:
    - mulesoft
    - api
    - integration
  max_daily_searches: 30
  max_results_per_search: 5
  content_max_length: 3000

sap:
  enabled: true
  allowed_domains:
    - help.sap.com
    - support.sap.com
    - community.sap.com
  required_keywords:
    - sap
    - erp
  max_daily_searches: 20
  max_results_per_search: 3
  content_max_length: 2000
```

---

## 7. 🔐 Implementación Completa con Controles

```python
# src/tools/tool_web_crawler.py

class SecureWebCrawlerTool:
    """Web Crawler con controles de seguridad"""
    
    def __init__(self, app_name: str, config_path: str = "config/web_crawler_config.yaml"):
        self.app_name = app_name
        self.config = self._load_config(config_path)
        self.audit = WebCrawlerAudit()
        self.limiter = UsageLimiter()
        self.logger = logging.getLogger(__name__)
    
    def search_and_extract(
        self,
        query: str,
        session_id: str,
        username: str
    ) -> dict:
        """
        Busca en internet con todos los controles de seguridad
        
        Args:
            query: Consulta de búsqueda
            session_id: ID de sesión
            username: Nombre de usuario
            
        Returns:
            dict con resultados o error
        """
        try:
            # 1. Verificar si está habilitado
            if not self.config.get('enabled', False):
                return self._error_response("Web crawler deshabilitado para esta aplicación")
            
            # 2. Verificar límites de uso
            allowed, reason = self.limiter.check_limits(username)
            if not allowed:
                self.logger.warning(f"Límite excedido para {username}: {reason}")
                return self._error_response(reason)
            
            # 3. Validar query
            is_valid, validation_reason = QueryValidator.is_valid_query(query, self.app_name)
            if not is_valid:
                self.audit.log_search(
                    session_id, username, self.app_name,
                    query, [], [], [], False, validation_reason
                )
                return self._error_response(validation_reason)
            
            # 4. Mejorar query
            enhanced_query = QueryValidator.enhance_query(query, self.app_name)
            
            # 5. Buscar URLs
            all_urls = self._search_duckduckgo(enhanced_query)
            
            # 6. Filtrar por whitelist
            allowed_urls = DomainWhitelist.filter_urls(all_urls, self.app_name)
            blocked_urls = [url for url in all_urls if url not in allowed_urls]
            
            if not allowed_urls:
                self.audit.log_search(
                    session_id, username, self.app_name,
                    query, all_urls, [], blocked_urls, False,
                    "No se encontraron URLs permitidas"
                )
                return self._error_response("No se encontraron fuentes permitidas")
            
            # 7. Extraer contenido
            results = []
            for url in allowed_urls[:self.config.get('max_results_per_search', 3)]:
                content = self._extract_and_validate_content(url, query)
                if content:
                    results.append(content)
            
            # 8. Registrar en auditoría
            self.audit.log_search(
                session_id, username, self.app_name,
                query, all_urls, allowed_urls, blocked_urls, True
            )
            
            # 9. Incrementar contador
            self.limiter.increment_usage(username)
            
            # 10. Retornar resultados
            return self._format_results(results, query)
        
        except Exception as e:
            self.logger.error(f"Error en web crawler: {str(e)}")
            return self._error_response(f"Error: {str(e)}")
    
    def _extract_and_validate_content(self, url: str, query: str) -> dict:
        """Extrae y valida contenido"""
        
        # Extraer contenido
        content_dict = self._extract_content(url)
        if not content_dict:
            return None
        
        # Validar relevancia
        is_relevant, score = ContentValidator.is_relevant_content(
            content_dict['content'],
            query,
            self.app_name
        )
        
        if not is_relevant:
            self.logger.info(f"Contenido no relevante de {url} (score: {score:.2f})")
            return None
        
        # Sanitizar
        content_dict['content'] = ContentValidator.sanitize_content(
            content_dict['content']
        )
        content_dict['relevance_score'] = score
        
        return content_dict
    
    def _error_response(self, message: str) -> dict:
        """Genera respuesta de error"""
        return {
            'success': False,
            'error': message,
            'results_count': 0,
            'sources': []
        }
```

---

## 8. 📋 Resumen de Controles Implementados

| Control | Descripción | Nivel de Seguridad |
|---------|-------------|-------------------|
| **Whitelist de Dominios** | Solo dominios aprobados | ⭐⭐⭐⭐⭐ |
| **Validación de Queries** | Keywords requeridas y prohibidas | ⭐⭐⭐⭐⭐ |
| **Validación de Contenido** | Relevancia y sanitización | ⭐⭐⭐⭐ |
| **Auditoría Completa** | Log de todas las búsquedas | ⭐⭐⭐⭐⭐ |
| **Límites de Uso** | Rate limiting por usuario | ⭐⭐⭐⭐ |
| **Configuración por App** | Controles específicos | ⭐⭐⭐⭐ |
| **Alertas Automáticas** | Notificación de intentos sospechosos | ⭐⭐⭐⭐ |

---

## 9. 🚀 Beneficios

✅ **Seguridad**: Solo acceso a fuentes autorizadas
✅ **Trazabilidad**: Auditoría completa de uso
✅ **Control**: Límites y alertas automáticas
✅ **Relevancia**: Solo contenido relacionado con el negocio
✅ **Compliance**: Cumplimiento de políticas corporativas

---

## 10. 📊 Dashboard de Monitoreo (Opcional)

```python
def generate_usage_report(days: int = 7) -> dict:
    """Genera reporte de uso del web crawler"""
    
    audit = WebCrawlerAudit()
    
    report = {
        'period_days': days,
        'total_searches': 0,
        'blocked_attempts': 0,
        'top_users': [],
        'top_queries': [],
        'blocked_domains': []
    }
    
    # Analizar logs
    # ... implementación
    
    return report
```

---

## ✅ Conclusión

Con estos controles, el web crawler es:
- **Seguro**: Solo accede a fuentes autorizadas
- **Controlado**: Límites y validaciones múltiples
- **Auditable**: Registro completo de actividad
- **Relevante**: Solo contenido relacionado con el negocio

¿Te gustaría que implemente la herramienta con todos estos controles de seguridad?
