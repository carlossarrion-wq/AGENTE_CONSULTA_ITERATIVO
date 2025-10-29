# Estrategias Anti-Bot para Web Crawler

## Pregunta del Usuario
> "¿Piensas que en los propios sites de consulta (ej.: docs.mulesoft.com) habrá controles anti-bot?"

## Respuesta: Sí, muy probablemente

Los sitios de documentación empresarial como docs.mulesoft.com, help.sap.com, etc., suelen tener protecciones anti-bot para:
- Prevenir scraping masivo
- Proteger su infraestructura
- Cumplir con términos de servicio
- Evitar abuso de recursos

---

## 🛡️ Tipos de Protecciones Anti-Bot Comunes

### 1. **Cloudflare / Akamai**
- Verificación de JavaScript
- Captchas
- Rate limiting por IP
- Análisis de comportamiento

### 2. **Rate Limiting**
- Límite de requests por minuto/hora
- Bloqueo temporal por exceso de requests
- Throttling progresivo

### 3. **User-Agent Filtering**
- Bloqueo de user-agents conocidos de bots
- Requiere user-agent de navegador real

### 4. **Headers Validation**
- Verificación de headers HTTP completos
- Detección de headers inconsistentes

### 5. **IP Reputation**
- Bloqueo de IPs de datacenters conocidos
- Listas negras de IPs

---

## ✅ Estrategias para Evitar Bloqueos

### 1. 🎭 User-Agent Realista

```python
class BotAvoidance:
    """Estrategias para evitar detección como bot"""
    
    # User-agents realistas
    USER_AGENTS = [
        # Chrome en Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        # Chrome en Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        # Firefox en Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        # Safari en Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
    ]
    
    @classmethod
    def get_random_user_agent(cls) -> str:
        """Obtiene un user-agent aleatorio"""
        import random
        return random.choice(cls.USER_AGENTS)
    
    @classmethod
    def get_realistic_headers(cls) -> dict:
        """Genera headers HTTP realistas"""
        return {
            'User-Agent': cls.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
```

### 2. ⏱️ Rate Limiting Inteligente

```python
import time
import random
from datetime import datetime, timedelta

class RateLimiter:
    """Control de rate limiting para evitar bloqueos"""
    
    def __init__(self):
        self.request_times = {}  # {domain: [timestamps]}
        self.min_delay = 2.0  # Mínimo 2 segundos entre requests
        self.max_delay = 5.0  # Máximo 5 segundos
        self.max_requests_per_minute = 10
    
    def wait_if_needed(self, domain: str):
        """Espera si es necesario para respetar rate limits"""
        
        now = datetime.now()
        
        # Inicializar si es primera vez
        if domain not in self.request_times:
            self.request_times[domain] = []
        
        # Limpiar requests antiguos (> 1 minuto)
        cutoff = now - timedelta(minutes=1)
        self.request_times[domain] = [
            t for t in self.request_times[domain] 
            if t > cutoff
        ]
        
        # Verificar límite por minuto
        if len(self.request_times[domain]) >= self.max_requests_per_minute:
            # Esperar hasta que el request más antiguo tenga > 1 minuto
            oldest = self.request_times[domain][0]
            wait_time = 60 - (now - oldest).total_seconds()
            if wait_time > 0:
                print(f"⏳ Rate limit alcanzado. Esperando {wait_time:.1f}s...")
                time.sleep(wait_time + 1)
        
        # Esperar delay aleatorio entre requests
        if self.request_times[domain]:
            last_request = self.request_times[domain][-1]
            time_since_last = (now - last_request).total_seconds()
            
            if time_since_last < self.min_delay:
                delay = random.uniform(self.min_delay, self.max_delay)
                time.sleep(delay)
        
        # Registrar este request
        self.request_times[domain].append(datetime.now())
```

### 3. 🔄 Retry con Backoff Exponencial

```python
import time
from typing import Callable, Any

class RetryStrategy:
    """Estrategia de reintentos con backoff exponencial"""
    
    @staticmethod
    def retry_with_backoff(
        func: Callable,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0
    ) -> Any:
        """
        Reintenta una función con backoff exponencial
        
        Args:
            func: Función a ejecutar
            max_retries: Número máximo de reintentos
            initial_delay: Delay inicial en segundos
            backoff_factor: Factor de multiplicación del delay
            max_delay: Delay máximo en segundos
            
        Returns:
            Resultado de la función
        """
        delay = initial_delay
        
        for attempt in range(max_retries + 1):
            try:
                return func()
            
            except Exception as e:
                if attempt == max_retries:
                    raise
                
                # Calcular delay con backoff exponencial
                wait_time = min(delay * (backoff_factor ** attempt), max_delay)
                
                # Añadir jitter aleatorio (±20%)
                jitter = wait_time * 0.2 * (2 * random.random() - 1)
                wait_time += jitter
                
                print(f"⚠️  Intento {attempt + 1} falló: {str(e)}")
                print(f"⏳ Reintentando en {wait_time:.1f}s...")
                
                time.sleep(wait_time)
        
        raise Exception("Max retries exceeded")
```

### 4. 🌐 Rotación de IPs (Opcional - Avanzado)

```python
class ProxyRotator:
    """Rotación de proxies para evitar bloqueos por IP"""
    
    def __init__(self, proxy_list: list = None):
        """
        Args:
            proxy_list: Lista de proxies en formato 'http://ip:port'
        """
        self.proxies = proxy_list or []
        self.current_index = 0
    
    def get_next_proxy(self) -> dict:
        """Obtiene el siguiente proxy de la lista"""
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        
        return {
            'http': proxy,
            'https': proxy
        }
    
    def mark_proxy_as_bad(self, proxy: str):
        """Marca un proxy como no funcional"""
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            print(f"❌ Proxy removido: {proxy}")
```

**NOTA**: Para uso corporativo, NO recomiendo usar proxies públicos. En su lugar:
- Usar la IP corporativa (generalmente permitida)
- Contactar con el proveedor para whitelist
- Usar APIs oficiales si están disponibles

### 5. 🍪 Manejo de Cookies y Sesiones

```python
import requests

class SessionManager:
    """Gestión de sesiones HTTP persistentes"""
    
    def __init__(self):
        self.sessions = {}  # {domain: session}
    
    def get_session(self, domain: str) -> requests.Session:
        """Obtiene o crea una sesión para un dominio"""
        
        if domain not in self.sessions:
            session = requests.Session()
            
            # Configurar headers realistas
            session.headers.update(BotAvoidance.get_realistic_headers())
            
            # Configurar timeouts
            session.timeout = 30
            
            self.sessions[domain] = session
        
        return self.sessions[domain]
    
    def close_all(self):
        """Cierra todas las sesiones"""
        for session in self.sessions.values():
            session.close()
```

### 6. 📊 Detección de Bloqueos

```python
class BlockDetector:
    """Detecta si hemos sido bloqueados"""
    
    @staticmethod
    def is_blocked(response: requests.Response, content: str) -> tuple[bool, str]:
        """
        Detecta si la respuesta indica un bloqueo
        
        Returns:
            (is_blocked, reason)
        """
        # 1. Status codes de bloqueo
        if response.status_code in [403, 429, 503]:
            return True, f"Status code {response.status_code}"
        
        # 2. Cloudflare challenge
        if 'cloudflare' in content.lower() and 'challenge' in content.lower():
            return True, "Cloudflare challenge detected"
        
        # 3. Captcha
        if any(word in content.lower() for word in ['captcha', 'recaptcha', 'hcaptcha']):
            return True, "Captcha detected"
        
        # 4. Mensajes de bloqueo comunes
        block_messages = [
            'access denied',
            'blocked',
            'too many requests',
            'rate limit exceeded',
            'suspicious activity'
        ]
        
        content_lower = content.lower()
        for msg in block_messages:
            if msg in content_lower:
                return True, f"Block message: {msg}"
        
        # 5. Contenido vacío o muy corto
        if len(content.strip()) < 100:
            return True, "Suspiciously short content"
        
        return False, "OK"
```

---

## 🔧 Implementación Completa con Anti-Bot

```python
# src/tools/tool_web_crawler.py

class RobustWebCrawler:
    """Web Crawler con protección anti-bot"""
    
    def __init__(self, app_name: str):
        self.app_name = app_name
        self.rate_limiter = RateLimiter()
        self.session_manager = SessionManager()
        self.block_detector = BlockDetector()
        self.logger = logging.getLogger(__name__)
    
    def fetch_url(self, url: str) -> tuple[bool, str, str]:
        """
        Descarga una URL con protecciones anti-bot
        
        Returns:
            (success, content, error_message)
        """
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        
        # 1. Rate limiting
        self.rate_limiter.wait_if_needed(domain)
        
        # 2. Obtener sesión persistente
        session = self.session_manager.get_session(domain)
        
        # 3. Intentar descarga con retry
        def download():
            response = session.get(url, timeout=30)
            response.raise_for_status()
            return response
        
        try:
            response = RetryStrategy.retry_with_backoff(
                download,
                max_retries=3,
                initial_delay=2.0
            )
            
            content = response.text
            
            # 4. Detectar bloqueos
            is_blocked, reason = self.block_detector.is_blocked(response, content)
            
            if is_blocked:
                self.logger.warning(f"⚠️  Posible bloqueo en {url}: {reason}")
                return False, "", f"Blocked: {reason}"
            
            return True, content, ""
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error descargando {url}: {str(e)}")
            return False, "", str(e)
    
    def extract_content_safe(self, url: str) -> dict:
        """Extrae contenido con todas las protecciones"""
        
        # Descargar con protecciones
        success, html_content, error = self.fetch_url(url)
        
        if not success:
            return {
                'success': False,
                'error': error,
                'url': url
            }
        
        # Extraer contenido con Trafilatura
        try:
            import trafilatura
            text = trafilatura.extract(html_content)
            
            if text:
                return {
                    'success': True,
                    'url': url,
                    'content': text,
                    'method': 'trafilatura'
                }
        except Exception as e:
            self.logger.warning(f"Trafilatura falló: {e}")
        
        # Fallback a Beautiful Soup
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remover scripts y estilos
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            
            return {
                'success': True,
                'url': url,
                'content': text,
                'method': 'beautifulsoup'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'url': url
            }
```

---

## 🎯 Mejores Prácticas

### 1. **Respetar robots.txt**

```python
from urllib.robotparser import RobotFileParser

class RobotsChecker:
    """Verifica robots.txt antes de acceder"""
    
    def __init__(self):
        self.parsers = {}  # {domain: RobotFileParser}
    
    def can_fetch(self, url: str, user_agent: str = '*') -> bool:
        """Verifica si podemos acceder a la URL"""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # Obtener o crear parser
        if domain not in self.parsers:
            parser = RobotFileParser()
            parser.set_url(f"{domain}/robots.txt")
            try:
                parser.read()
                self.parsers[domain] = parser
            except:
                # Si falla, asumir que está permitido
                return True
        
        return self.parsers[domain].can_fetch(user_agent, url)
```

### 2. **Identificarse Correctamente**

```python
# En lugar de ocultar que somos un bot, identificarnos honestamente
CUSTOM_USER_AGENT = (
    'MulesoftDocBot/1.0 '
    '(+https://tu-empresa.com/bot-info; bot@tu-empresa.com) '
    'Python-requests/2.31.0'
)
```

### 3. **Usar APIs Oficiales Cuando Existan**

Muchos proveedores tienen APIs oficiales:

```python
# Ejemplo: MuleSoft tiene APIs
# https://anypoint.mulesoft.com/exchange/portals/anypoint-platform/

# SAP tiene APIs
# https://api.sap.com/

# Preferir APIs sobre scraping
```

### 4. **Caché Agresivo**

```python
import hashlib
import json
from pathlib import Path

class ContentCache:
    """Caché de contenido descargado"""
    
    def __init__(self, cache_dir: str = "cache/web_crawler"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = 24  # Cache válido por 24 horas
    
    def get_cache_key(self, url: str) -> str:
        """Genera key de caché para una URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def get(self, url: str) -> tuple[bool, str]:
        """
        Obtiene contenido del caché
        
        Returns:
            (found, content)
        """
        key = self.get_cache_key(url)
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return False, ""
        
        # Verificar edad del caché
        age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if age_hours > self.ttl_hours:
            return False, ""
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return True, data['content']
    
    def set(self, url: str, content: str):
        """Guarda contenido en caché"""
        key = self.get_cache_key(url)
        cache_file = self.cache_dir / f"{key}.json"
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                'url': url,
                'content': content,
                'cached_at': datetime.now().isoformat()
            }, f, ensure_ascii=False)
```

---

## 📋 Resumen de Estrategias

| Estrategia | Importancia | Dificultad | Efectividad |
|------------|-------------|------------|-------------|
| **User-Agent Realista** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐ |
| **Rate Limiting** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Retry con Backoff** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **Headers Completos** | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ |
| **Sesiones Persistentes** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **Detección de Bloqueos** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **Caché Agresivo** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Respetar robots.txt** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## ✅ Recomendación Final

Para un uso corporativo legítimo:

1. **Contactar con el proveedor**: Informar que usarás scraping moderado
2. **Whitelist de IP**: Solicitar que añadan tu IP corporativa
3. **Usar APIs oficiales**: Cuando estén disponibles
4. **Rate limiting conservador**: 1-2 requests por minuto máximo
5. **Caché agresivo**: Cachear todo por 24-48 horas
6. **Identificarse honestamente**: User-agent que identifique tu empresa

**Esto es mejor que intentar "engañar" al sistema**, ya que:
- ✅ Es legal y ético
- ✅ Evita problemas futuros
- ✅ Puede dar acceso a APIs mejores
- ✅ Construye buena relación con proveedores

¿Te gustaría que implemente la herramienta con todas estas protecciones anti-bot?
