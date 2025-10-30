"""
Web Crawler Tool - Búsqueda de información en internet

Herramienta para buscar información actualizada en internet cuando
la base de conocimiento interna no es suficiente.

Características:
- Búsqueda con DuckDuckGo (sin API key)
- Extracción de contenido con Trafilatura y Beautiful Soup
- Controles de seguridad (whitelist, validación, rate limiting)
- Caché de resultados
"""

import logging
import time
import hashlib
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Tuple
from urllib.parse import urlparse
import random


class ToolResult:
    """Resultado de ejecución de herramienta"""
    
    def __init__(self, success: bool, data: Any = None, error: str = None, execution_time_ms: float = 0):
        self.success = success
        self.data = data
        self.error = error
        self.execution_time_ms = execution_time_ms


class WebCrawlerConfig:
    """Carga y gestiona configuración del web crawler"""
    
    def __init__(self, config_path: str = "config/web_crawler_config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logging.getLogger(__name__).error(f"Error cargando configuración: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Configuración por defecto si falla la carga"""
        return {
            'global': {
                'cache_ttl_hours': 24,
                'max_results_per_search': 3,
                'max_content_length': 2000,
                'min_delay_seconds': 3.0
            },
            'mulesoft': {
                'enabled': True,
                'allowed_domains': ['docs.mulesoft.com', 'help.mulesoft.com'],
                'required_keywords': ['mulesoft', 'api'],
                'forbidden_keywords': []
            }
        }
    
    def get_app_config(self, app_name: str) -> Dict[str, Any]:
        """Obtiene configuración de una aplicación"""
        return self.config.get(app_name.lower(), {})
    
    def get_global_config(self) -> Dict[str, Any]:
        """Obtiene configuración global"""
        return self.config.get('global', {})
    
    def get_user_agents(self) -> List[str]:
        """Obtiene lista de user-agents"""
        return self.config.get('user_agents', [
            # Chrome en Windows (más reciente)
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # Chrome en Mac (más reciente)
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # Firefox en Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            # Safari en Mac
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            # Edge en Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
        ])


class DomainWhitelist:
    """Control de dominios permitidos por aplicación"""
    
    def __init__(self, config: WebCrawlerConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Obtener configuración de modo permisivo
        global_config = config.get_global_config()
        self.permissive_mode = global_config.get('permissive_mode', False)
        self.blocked_domains = global_config.get('blocked_domains', [])
        
        if self.permissive_mode:
            self.logger.info("🔓 Modo permisivo activado - usando blacklist en lugar de whitelist")
        else:
            self.logger.info("🔒 Modo estricto activado - usando whitelist")
    
    def is_allowed(self, url: str, app_name: str) -> bool:
        """Verifica si una URL está permitida"""
        try:
            domain = urlparse(url).netloc.replace('www.', '')
            
            # Modo permisivo: bloquear solo dominios en blacklist
            if self.permissive_mode:
                return self._is_allowed_permissive(domain)
            
            # Modo estricto: permitir solo dominios en whitelist
            return self._is_allowed_strict(domain, app_name)
        except Exception as e:
            self.logger.debug(f"Error verificando dominio: {e}")
            return False
    
    def _is_allowed_permissive(self, domain: str) -> bool:
        """Verifica si un dominio está permitido en modo permisivo (blacklist)"""
        # Verificar si el dominio está en la blacklist
        for blocked_domain in self.blocked_domains:
            if domain == blocked_domain or domain.endswith('.' + blocked_domain):
                self.logger.debug(f"❌ Dominio bloqueado (blacklist): {domain}")
                return False
        
        # Si no está bloqueado, está permitido
        return True
    
    def _is_allowed_strict(self, domain: str, app_name: str) -> bool:
        """Verifica si un dominio está permitido en modo estricto (whitelist)"""
        app_config = self.config.get_app_config(app_name)
        allowed = app_config.get('allowed_domains', [])
        
        for allowed_domain in allowed:
            if domain == allowed_domain or domain.endswith('.' + allowed_domain):
                return True
        
        self.logger.debug(f"❌ Dominio no está en whitelist: {domain}")
        return False
    
    def filter_urls(self, urls: List[str], app_name: str) -> List[str]:
        """Filtra URLs dejando solo las permitidas"""
        filtered = [url for url in urls if self.is_allowed(url, app_name)]
        
        if self.permissive_mode:
            self.logger.info(f"🔓 Modo permisivo: {len(filtered)}/{len(urls)} URLs permitidas (bloqueadas: {len(urls) - len(filtered)})")
        else:
            self.logger.info(f"🔒 Modo estricto: {len(filtered)}/{len(urls)} URLs en whitelist")
        
        return filtered


class QueryValidator:
    """Validación de queries de búsqueda"""
    
    def __init__(self, config: WebCrawlerConfig):
        self.config = config
    
    def is_valid_query(self, query: str, app_name: str) -> Tuple[bool, str]:
        """Valida si una query es apropiada"""
        query_lower = query.lower()
        app_config = self.config.get_app_config(app_name)
        
        # Verificar keywords prohibidas
        forbidden = app_config.get('forbidden_keywords', [])
        for forbidden_word in forbidden:
            if forbidden_word in query_lower:
                return False, f"Query contiene contenido prohibido"
        
        # Verificar keywords requeridas
        required = app_config.get('required_keywords', [])
        has_required = any(keyword in query_lower for keyword in required)
        
        if not has_required:
            return False, f"Query debe estar relacionada con {app_name}"
        
        # Verificar longitud mínima
        if len(query.split()) < 3:
            return False, "Query demasiado corta. Debe ser más específica"
        
        return True, "OK"
    
    def enhance_query(self, query: str, app_name: str, site: str = None) -> str:
        """Mejora la query añadiendo contexto y restricción de sitio"""
        app_lower = app_name.lower()
        query_lower = query.lower()
        
        # Añadir nombre de aplicación si no está
        if app_lower not in query_lower:
            query = f"{app_name} {query}"
        
        # Añadir términos técnicos desde configuración
        enhancements = self.config.config.get('search_enhancements', {})
        if app_lower in enhancements:
            query = f"{query} {enhancements[app_lower]}"
        
        # Si se especifica un sitio, añadir operador site:
        if site:
            query = f"site:{site} {query}"
        
        return query


class RateLimiter:
    """Control de rate limiting simple"""
    
    def __init__(self, config: WebCrawlerConfig, app_name: str):
        self.request_times = {}
        app_config = config.get_app_config(app_name)
        rate_limit = app_config.get('rate_limit', {})
        self.min_delay = rate_limit.get('min_delay_seconds', 3.0)
    
    def wait_if_needed(self, domain: str):
        """Espera si es necesario"""
        now = time.time()
        
        if domain in self.request_times:
            elapsed = now - self.request_times[domain]
            if elapsed < self.min_delay:
                wait_time = self.min_delay - elapsed
                time.sleep(wait_time)
        
        self.request_times[domain] = time.time()


class ContentCache:
    """Caché simple de contenido"""
    
    def __init__(self, config: WebCrawlerConfig, cache_dir: str = "cache/web_crawler"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        global_config = config.get_global_config()
        self.ttl_hours = global_config.get('cache_ttl_hours', 24)
    
    def get_cache_key(self, url: str) -> str:
        """Genera key de caché"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def get(self, url: str) -> Tuple[bool, str]:
        """Obtiene contenido del caché"""
        try:
            key = self.get_cache_key(url)
            cache_file = self.cache_dir / f"{key}.json"
            
            if not cache_file.exists():
                return False, ""
            
            # Verificar edad
            age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
            if age_hours > self.ttl_hours:
                return False, ""
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return True, data['content']
        except:
            return False, ""
    
    def set(self, url: str, content: str):
        """Guarda contenido en caché"""
        try:
            key = self.get_cache_key(url)
            cache_file = self.cache_dir / f"{key}.json"
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'url': url,
                    'content': content,
                    'cached_at': datetime.now().isoformat()
                }, f, ensure_ascii=False)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error guardando caché: {e}")


class WebCrawlerTool:
    """Herramienta de web crawling con controles de seguridad"""
    
    def __init__(self, app_name: str, config_path: str = "config/web_crawler_config.yaml"):
        self.app_name = app_name
        self.logger = logging.getLogger(__name__)
        
        # Cargar configuración
        self.config = WebCrawlerConfig(config_path)
        global_config = self.config.get_global_config()
        
        # Parámetros desde configuración
        self.max_results = global_config.get('max_results_per_search', 3)
        self.max_content_length = global_config.get('max_content_length', 2000)
        self.timeout = global_config.get('request_timeout_seconds', 15)
        
        # Componentes
        self.domain_whitelist = DomainWhitelist(self.config)
        self.query_validator = QueryValidator(self.config)
        self.rate_limiter = RateLimiter(self.config, app_name)
        self.cache = ContentCache(self.config)
        
        # User-agents desde configuración
        self.user_agents = self.config.get_user_agents()
    
    def search_and_extract(self, query: str, site: str = None) -> ToolResult:
        """
        Busca URLs relevantes en internet (sin extraer contenido)
        
        Estrategia: Devolver URLs relevantes para que el usuario las visite,
        evitando problemas con protecciones anti-bot.
        
        Args:
            query: Consulta de búsqueda
            site: (Opcional) Dominio específico para limitar la búsqueda (ej: help.sap.com)
            
        Returns:
            ToolResult con URLs recomendadas
        """
        start_time = time.time()
        
        try:
            # 1. Validar query
            is_valid, reason = self.query_validator.is_valid_query(query, self.app_name)
            if not is_valid:
                return ToolResult(
                    success=False,
                    error=f"Query rechazada: {reason}",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # 2. Mejorar query (con site si se especifica)
            enhanced_query = self.query_validator.enhance_query(query, self.app_name, site=site)
            self.logger.info(f"Búsqueda web: {enhanced_query}")
            
            # 3. Buscar URLs
            urls = self._search_duckduckgo(enhanced_query)
            
            # Si no hay URLs, el problema es que DuckDuckGo no devolvió resultados
            if not urls:
                return ToolResult(
                    success=False,
                    error="No se encontraron fuentes de información válidas para esta consulta.",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # 4. Filtrar por whitelist/blacklist
            allowed_urls = self.domain_whitelist.filter_urls(urls, self.app_name)
            
            # Si hay URLs pero todas fueron bloqueadas
            if not allowed_urls:
                if self.domain_whitelist.permissive_mode:
                    # En modo permisivo, esto significa que todas las URLs están en la blacklist
                    return ToolResult(
                        success=False,
                        error="No se encontraron fuentes de información válidas para esta consulta. Los resultados encontrados están en la lista de sitios bloqueados.",
                        execution_time_ms=(time.time() - start_time) * 1000
                    )
                else:
                    # En modo estricto, esto significa que ninguna URL está en la whitelist
                    return ToolResult(
                        success=False,
                        error="No se encontraron fuentes de información válidas para esta consulta. Los resultados no están en la lista de sitios permitidos para esta aplicación.",
                        execution_time_ms=(time.time() - start_time) * 1000
                    )
            
            self.logger.info(f"URLs permitidas: {len(allowed_urls)}/{len(urls)}")
            
            # 5. Formatear URLs como recomendaciones (sin extraer contenido)
            formatted_data = self._format_url_recommendations(allowed_urls[:self.max_results], query)
            
            execution_time = (time.time() - start_time) * 1000
            self.logger.info(f"Búsqueda completada: {len(allowed_urls[:self.max_results])} URLs encontradas en {execution_time:.0f}ms")
            
            return ToolResult(
                success=True,
                data=formatted_data,
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            self.logger.error(f"Error en web crawler: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def _search_duckduckgo(self, query: str) -> List[str]:
        """Busca URLs usando DuckDuckGo"""
        try:
            # Usar el paquete duckduckgo-search
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                self.logger.error(
                    "El paquete 'duckduckgo-search' no está instalado. "
                    "Por favor ejecuta: pip3 install duckduckgo-search"
                )
                raise ImportError(
                    "Paquete 'duckduckgo-search' no encontrado. "
                    "Ejecuta: pip3 install duckduckgo-search"
                )
            
            # Realizar búsqueda
            # IMPORTANTE: En duckduckgo-search 3.9.x hay un bug con el parámetro 'proxies'
            # El constructor DDGS.__init__ acepta proxies pero Client.__init__ no
            # Solución: Pasar headers=None explícitamente para evitar el bug
            ddgs = None
            
            try:
                # Versión 3.9.x: Pasar headers=None evita el bug de proxies
                ddgs = DDGS(headers=None)
                self.logger.debug("DDGS inicializado con headers=None")
            except (TypeError, Exception) as e:
                self.logger.debug(f"DDGS(headers=None) falló: {e}")
                
                # Fallback: Intentar sin ningún parámetro
                try:
                    ddgs = DDGS()
                    self.logger.debug("DDGS inicializado sin parámetros")
                except (TypeError, Exception) as e2:
                    self.logger.error(f"No se pudo crear instancia de DDGS: {e2}")
                    return []
            
            if ddgs is None:
                self.logger.error("No se pudo inicializar DDGS")
                return []
            
            # text() devuelve un generador y acepta parámetros de búsqueda
            results = []
            try:
                # Iterar sobre el generador con límite manual
                for result in ddgs.text(query, region='wt-wt', safesearch='moderate', timelimit=None):
                    results.append(result)
                    if len(results) >= 10:
                        break
            except StopIteration:
                pass
            except Exception as e:
                self.logger.error(f"Error iterando resultados DuckDuckGo: {e}")
                # Intentar sin parámetros opcionales
                try:
                    for result in ddgs.text(query):
                        results.append(result)
                        if len(results) >= 10:
                            break
                except Exception as e2:
                    self.logger.error(f"Error en búsqueda simplificada: {e2}")
            
            if not results:
                self.logger.debug(f"DuckDuckGo no devolvió resultados para: {query}")
                return []
            
            urls = [r.get('href') or r.get('link') for r in results if r.get('href') or r.get('link')]
            
            self.logger.info(f"DuckDuckGo encontró {len(urls)} URLs")
            return urls
        
        except Exception as e:
            self.logger.debug(f"Error en búsqueda DuckDuckGo: {e}")
            return []
    
    def _extract_content(self, url: str) -> Dict[str, Any]:
        """Extrae contenido de una URL"""
        # Verificar caché primero
        cached, content = self.cache.get(url)
        if cached:
            self.logger.info(f"Contenido de caché: {url}")
            return {
                'url': url,
                'content': content[:self.max_content_length],
                'method': 'cache'
            }
        
        # Rate limiting
        domain = urlparse(url).netloc
        self.rate_limiter.wait_if_needed(domain)
        
        # Intentar con Trafilatura
        content_dict = self._extract_with_trafilatura(url)
        if content_dict:
            # Guardar en caché
            self.cache.set(url, content_dict['content'])
            return content_dict
        
        # Fallback a Beautiful Soup
        content_dict = self._extract_with_beautifulsoup(url)
        if content_dict:
            # Guardar en caché
            self.cache.set(url, content_dict['content'])
            return content_dict
        
        return None
    
    def _extract_with_trafilatura(self, url: str) -> Dict[str, Any]:
        """Extrae contenido con Trafilatura (opcional)"""
        try:
            # Trafilatura es opcional - puede no estar instalado
            try:
                import trafilatura
                from trafilatura.settings import use_config
            except ImportError:
                self.logger.debug("Trafilatura no está instalado, usando BeautifulSoup")
                return None
            
            # Configurar trafilatura con límite de redirecciones
            config = use_config()
            config.set("DEFAULT", "MAX_REDIRECTS", "5")
            
            downloaded = trafilatura.fetch_url(url, config=config)
            if not downloaded:
                self.logger.debug(f"Trafilatura no pudo descargar: {url}")
                return None
            
            text = trafilatura.extract(downloaded, config=config)
            if text and len(text) > 100:
                return {
                    'url': url,
                    'content': text[:self.max_content_length],
                    'method': 'trafilatura'
                }
        except Exception as e:
            self.logger.debug(f"Trafilatura falló para {url}: {e}")
        
        return None
    
    def _extract_with_beautifulsoup(self, url: str) -> Dict[str, Any]:
        """Extrae contenido con Beautiful Soup con protección anti-bot mejorada"""
        try:
            import requests
            from bs4 import BeautifulSoup
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            # Headers más realistas y completos para evitar detección
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'Pragma': 'no-cache'
            }
            
            # Crear sesión persistente con configuración robusta
            session = requests.Session()
            
            # Configurar reintentos
            retry = Retry(
                total=2,
                backoff_factor=1.0,
                status_forcelist=(500, 502, 503, 504),
                allowed_methods=["GET"]
            )
            adapter = HTTPAdapter(max_retries=retry, pool_connections=1, pool_maxsize=1)
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            
            # Delay aleatorio antes del request (2-4 segundos)
            delay = random.uniform(2.0, 4.0)
            time.sleep(delay)
            
            # Realizar request con límite de redirecciones
            response = session.get(
                url, 
                headers=headers, 
                timeout=self.timeout,
                allow_redirects=True,
                verify=True
            )
            
            # Detectar bloqueos comunes
            if response.status_code in [403, 429, 503]:
                self.logger.debug(f"Posible bloqueo (status {response.status_code}): {url}")
                return None
            
            response.raise_for_status()
            
            content = response.text
            
            # Detectar páginas de bloqueo por contenido
            content_lower = content.lower()
            block_indicators = [
                'cloudflare',
                'access denied',
                'captcha',
                'too many requests',
                'rate limit'
            ]
            
            if any(indicator in content_lower for indicator in block_indicators):
                self.logger.debug(f"Posible página de bloqueo detectada: {url}")
                return None
            
            # Verificar que el contenido no esté vacío
            if len(content.strip()) < 200:
                self.logger.debug(f"Contenido sospechosamente corto: {url}")
                return None
            
            # Usar html.parser (nativo de Python) en lugar de lxml
            # lxml es opcional y puede causar problemas de compilación en algunos sistemas
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remover scripts y estilos
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            text = soup.get_text(separator='\n', strip=True)
            
            if text and len(text) > 100:
                return {
                    'url': url,
                    'content': text[:self.max_content_length],
                    'method': 'beautifulsoup'
                }
        except requests.exceptions.TooManyRedirects:
            self.logger.debug(f"Demasiadas redirecciones para {url}")
        except requests.exceptions.Timeout:
            self.logger.debug(f"Timeout al acceder a {url}")
        except Exception as e:
            self.logger.debug(f"BeautifulSoup falló para {url}: {e}")
        
        return None
    
    def _format_url_recommendations(self, urls: List[str], query: str) -> Dict[str, Any]:
        """
        Formatea URLs como recomendaciones para el LLM
        
        Args:
            urls: Lista de URLs relevantes
            query: Query de búsqueda original
            
        Returns:
            Diccionario con URLs recomendadas
        """
        formatted = {
            'query': query,
            'results_count': len(urls),
            'recommended_urls': []
        }
        
        for i, url in enumerate(urls, 1):
            formatted['recommended_urls'].append({
                'number': i,
                'url': url,
                'description': f"Recurso oficial sobre: {query}"
            })
        
        return formatted
    
    def _format_results(self, results: List[Dict], query: str) -> Dict[str, Any]:
        """Formatea resultados para el LLM (legacy - para compatibilidad)"""
        formatted = {
            'query': query,
            'results_count': len(results),
            'sources': []
        }
        
        for i, result in enumerate(results, 1):
            formatted['sources'].append({
                'number': i,
                'url': result['url'],
                'content': result['content'],
                'extraction_method': result['method']
            })
        
        return formatted


def execute_web_crawler(params: Dict[str, Any], config_path: str = "config/web_crawler_config.yaml") -> ToolResult:
    """
    Función de entrada para ejecutar la herramienta
    
    Args:
        params: Parámetros con 'query', opcionalmente 'app_name' y 'site'
        config_path: Ruta al archivo de configuración
        
    Returns:
        ToolResult con resultados de la búsqueda
    """
    query = params.get('query', '')
    app_name = params.get('app_name', 'mulesoft')  # Default a mulesoft
    site = params.get('site', None)  # Sitio específico opcional
    
    if not query:
        return ToolResult(
            success=False,
            error="Parámetro 'query' es requerido"
        )
    
    tool = WebCrawlerTool(app_name=app_name, config_path=config_path)
    return tool.search_and_extract(query, site=site)


def main():
    """Función de testing"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test
    tool = WebCrawlerTool(app_name='mulesoft')
    result = tool.search_and_extract("mulesoft runtime 4.5.0 patch security")
    
    if result.success:
        print(f"✅ Éxito: {result.data['results_count']} resultados")
        for source in result.data['sources']:
            print(f"\n{source['number']}. {source['url']}")
            print(f"   Contenido: {source['content'][:200]}...")
    else:
        print(f"❌ Error: {result.error}")


if __name__ == "__main__":
    main()
