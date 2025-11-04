"""
Módulo común con utilidades compartidas para las herramientas de búsqueda.
"""

import yaml
import logging
import boto3
import json
import hashlib
import time
from typing import Dict, List, Any, Optional
from opensearchpy import OpenSearch
from functools import wraps
import os
import warnings

# Suprimir warnings de SSL de opensearchpy
warnings.filterwarnings('ignore', message='Connecting to .* using SSL with verify_certs=False is insecure.')

# Suprimir warnings de deprecación de Python de boto3
warnings.filterwarnings('ignore', category=DeprecationWarning, module='boto3')
warnings.filterwarnings('ignore', message='Boto3 will no longer support Python.*')

class Config:
    """Clase para manejar la configuración desde el archivo YAML"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración desde el archivo YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Archivo de configuración no encontrado: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error al parsear el archivo de configuración: {e}")
    
    def get(self, key_path: str, default=None):
        """Obtiene un valor de configuración usando notación de punto"""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value

class SearchError(Exception):
    """Excepción base para errores de búsqueda"""
    pass

class ConnectionError(SearchError):
    """Error de conexión con OpenSearch o Bedrock"""
    pass

class ValidationError(SearchError):
    """Error de validación de parámetros"""
    pass

class OpenSearchClient:
    """Cliente singleton para OpenSearch con soporte para AWS CLI"""
    
    _instance = None
    _client = None
    
    def __new__(cls, config: Config):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Config):
        if self._client is None:
            self._config = config
            self._client = self._create_client()
    
    def _create_client(self) -> OpenSearch:
        """Crea el cliente de OpenSearch con autenticación AWS"""
        try:
            # Importar AWS4Auth para autenticación con AWS CLI
            from opensearchpy import OpenSearch, RequestsHttpConnection
            from requests_aws4auth import AWS4Auth
            import boto3
            
            # Obtener configuración con soporte para variables de entorno
            host = os.getenv('OPENSEARCH_HOST', self._config.get('opensearch.host'))
            port = int(os.getenv('OPENSEARCH_PORT', self._config.get('opensearch.port', 443)))
            use_ssl = os.getenv('OPENSEARCH_USE_SSL', str(self._config.get('opensearch.use_ssl', True))).lower() == 'true'
            verify_certs = os.getenv('OPENSEARCH_VERIFY_CERTS', str(self._config.get('opensearch.verify_certs', True))).lower() == 'true'
            
            # Si el host incluye puerto, separarlo
            if ':' in host and not host.startswith('http'):
                host_parts = host.split(':')
                host = host_parts[0]
                port = int(host_parts[1])
            
            # Obtener credenciales de AWS CLI
            session = boto3.Session()
            credentials = session.get_credentials()
            region = self._config.get('opensearch.region', 'eu-west-1')
            
            # Crear autenticación AWS4Auth
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                region,
                'es',  # Servicio OpenSearch
                session_token=credentials.token
            )
            
            # Configurar cliente con autenticación AWS
            return OpenSearch(
                hosts=[{
                    'host': host,
                    'port': port
                }],
                http_auth=awsauth,
                use_ssl=use_ssl,
                verify_certs=verify_certs,
                connection_class=RequestsHttpConnection,
                timeout=self._config.get('opensearch.timeout', 30),
                max_retries=self._config.get('opensearch.max_retries', 3)
            )
            
        except ImportError:
            # Fallback sin autenticación AWS (para desarrollo local sin AWS CLI)
            host = os.getenv('OPENSEARCH_HOST', self._config.get('opensearch.host'))
            port = int(os.getenv('OPENSEARCH_PORT', self._config.get('opensearch.port', 443)))
            use_ssl = os.getenv('OPENSEARCH_USE_SSL', str(self._config.get('opensearch.use_ssl', True))).lower() == 'true'
            verify_certs = os.getenv('OPENSEARCH_VERIFY_CERTS', str(self._config.get('opensearch.verify_certs', True))).lower() == 'true'
            
            # Si el host incluye puerto, separarlo
            if ':' in host and not host.startswith('http'):
                host_parts = host.split(':')
                host = host_parts[0]
                port = int(host_parts[1])
            
            return OpenSearch([{
                'host': host,
                'port': port,
                'use_ssl': use_ssl,
                'verify_certs': verify_certs,
                'timeout': self._config.get('opensearch.timeout', 30),
                'max_retries': self._config.get('opensearch.max_retries', 3)
            }])
        except Exception as e:
            raise ConnectionError(f"Error al conectar con OpenSearch: {str(e)}")
    
    def get_client(self) -> OpenSearch:
        """Obtiene el cliente de OpenSearch"""
        return self._client

class BedrockClient:
    """Cliente singleton para AWS Bedrock"""
    
    _instance = None
    _client = None
    
    def __new__(cls, config: Config):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Config):
        if self._client is None:
            self._config = config
            self._client = self._create_client()
    
    def _create_client(self):
        """Crea el cliente de Bedrock"""
        try:
            return boto3.client(
                'bedrock-runtime',
                region_name=self._config.get('bedrock.region_name')
            )
        except Exception as e:
            raise ConnectionError(f"Error al conectar con Bedrock: {str(e)}")
    
    def get_client(self):
        """Obtiene el cliente de Bedrock"""
        return self._client
    
    def generate_embedding(self, text: str) -> List[float]:
        """Genera embedding para un texto"""
        try:
            response = self._client.invoke_model(
                modelId=self._config.get('bedrock.model_id'),
                body=json.dumps({
                    "inputText": text,
                    "embeddingConfig": {
                        "outputEmbeddingLength": self._config.get('bedrock.embedding_dimensions')
                    }
                })
            )
            
            result = json.loads(response['body'].read())
            return result['embedding']
            
        except Exception as e:
            raise ConnectionError(f"Error al generar embedding: {str(e)}")

class Logger:
    """Configurador de logging"""
    
    _configured = False
    
    @classmethod
    def setup(cls, config: Config):
        """Configura el logging"""
        if cls._configured:
            return
        
        # Crear directorio de logs si no existe
        log_file = config.get('logging.file')
        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Configurar nivel de logging para nuestros módulos
        log_level = getattr(logging, config.get('logging.level', 'INFO'))
        log_format = config.get('logging.format')
        
        # Crear handlers
        handlers = []
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(log_format))
            handlers.append(file_handler)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(console_handler)
        
        # Configurar root logger con nivel WARNING para evitar logs de librerías
        logging.basicConfig(
            level=logging.WARNING,
            format=log_format,
            handlers=handlers
        )
        
        # Configurar nuestros loggers específicamente
        for module in ['agent', 'tools', 'common']:
            logger = logging.getLogger(module)
            logger.setLevel(log_level)
        
        # Silenciar loggers de AWS y otras librerías
        logging.getLogger('boto3').setLevel(logging.WARNING)
        logging.getLogger('botocore').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('opensearchpy').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('s3transfer').setLevel(logging.WARNING)
        
        cls._configured = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Obtiene un logger"""
        return logging.getLogger(name)

def handle_search_error(func):
    """Decorador para manejo estándar de errores"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ConnectionError as e:
            return {"error": f"Connection error: {str(e)}", "type": "connection"}
        except ValidationError as e:
            return {"error": f"Validation error: {str(e)}", "type": "validation"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}", "type": "unexpected"}
    return wrapper

def log_search_metrics(func):
    """Decorador para logging de métricas de búsqueda"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = Logger.get_logger(func.__module__)
        start_time = time.time()
        func_name = func.__name__
        
        # Log de inicio (solo el primer argumento para evitar logs muy largos)
        first_arg = args[0] if args else "N/A"
        logger.info(f"Starting {func_name} with query: {str(first_arg)[:100]}...")
        
        result = func(*args, **kwargs)
        
        duration = time.time() - start_time
        
        if isinstance(result, dict) and "error" in result:
            logger.error(f"{func_name} failed in {duration:.2f}s: {result['error']}")
        else:
            # Contar resultados según el tipo de respuesta
            results_count = 0
            if isinstance(result, dict):
                results_count = result.get('total_found', 
                                result.get('total_results', 
                                result.get('total_matches', 
                                result.get('total_chunks', 1))))
            
            logger.info(f"{func_name} completed in {duration:.2f}s, found {results_count} results")
        
        return result
    return wrapper

def validate_parameters(required_params: List[str], optional_params: Dict[str, Any] = None):
    """Decorador para validar parámetros de entrada"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Obtener nombres de parámetros de la función
            import inspect
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            
            # Crear diccionario de argumentos
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validar parámetros requeridos
            for param in required_params:
                if param not in bound_args.arguments or bound_args.arguments[param] is None:
                    raise ValidationError(f"Parámetro requerido faltante: {param}")
            
            # Aplicar valores por defecto para parámetros opcionales
            if optional_params:
                for param, default_value in optional_params.items():
                    if param in bound_args.arguments and bound_args.arguments[param] is None:
                        bound_args.arguments[param] = default_value
            
            return func(*bound_args.args, **bound_args.kwargs)
        return wrapper
    return decorator

def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calcula similitud entre dos textos normalizando espacios y saltos de línea"""
    # Normalizar textos
    norm1 = ' '.join(text1.split())
    norm2 = ' '.join(text2.split())
    
    if not norm1 or not norm2:
        return 0.0
    
    # Calcular similitud por caracteres coincidentes
    min_len = min(len(norm1), len(norm2))
    if min_len == 0:
        return 0.0
    
    matches = sum(1 for i in range(min_len) if norm1[i] == norm2[i])
    return matches / min_len

def find_overlap_length(text1: str, text2: str, min_overlap: int = 50) -> int:
    """
    Encuentra la longitud del overlap entre el final de text1 y el inicio de text2.
    """
    max_overlap = min(len(text1), len(text2), 500)  # Limitar búsqueda a 500 chars
    
    for overlap_len in range(max_overlap, min_overlap - 1, -1):
        # Comparar final de text1 con inicio de text2
        end_of_text1 = text1[-overlap_len:]
        start_of_text2 = text2[:overlap_len]
        
        # Calcular similitud (permitir pequeñas diferencias por espacios/saltos)
        similarity = calculate_text_similarity(end_of_text1, start_of_text2)
        
        if similarity > 0.85:  # 85% de similitud
            return overlap_len
    
    return 0

def remove_duplicate_chunks_by_hash(chunks: List[Dict]) -> List[Dict]:
    """Elimina chunks duplicados basándose en hash del contenido"""
    seen_hashes = set()
    unique_chunks = []
    
    for chunk in chunks:
        content = chunk.get('_source', {}).get('content', '')
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            unique_chunks.append(chunk)
    
    return unique_chunks

class SimpleCache:
    """Cache simple en memoria con TTL"""
    
    def __init__(self, max_size_mb: int = 100, ttl_seconds: int = 3600):
        self.cache = {}
        self.timestamps = {}
        self.max_size = max_size_mb * 1024 * 1024  # Convertir a bytes
        self.current_size = 0
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Obtiene un valor del cache"""
        if key not in self.cache:
            return None
        
        # Verificar TTL
        if time.time() - self.timestamps[key] > self.ttl:
            self._remove(key)
            return None
        
        return self.cache[key]
    
    def set(self, key: str, value: Any):
        """Almacena un valor en el cache"""
        value_size = len(str(value))
        
        # Limpiar cache si es necesario
        while self.current_size + value_size > self.max_size and self.cache:
            oldest_key = min(self.timestamps.keys(), key=lambda k: self.timestamps[k])
            self._remove(oldest_key)
        
        self.cache[key] = value
        self.timestamps[key] = time.time()
        self.current_size += value_size
    
    def _remove(self, key: str):
        """Elimina una entrada del cache"""
        if key in self.cache:
            self.current_size -= len(str(self.cache[key]))
            del self.cache[key]
            del self.timestamps[key]

# Cache global
_cache = None

def get_cache(config: Config) -> Optional[SimpleCache]:
    """Obtiene la instancia global del cache"""
    global _cache
    
    if not config.get('cache.enabled', False):
        return None
    
    if _cache is None:
        _cache = SimpleCache(
            max_size_mb=config.get('cache.max_size_mb', 100),
            ttl_seconds=config.get('cache.ttl_seconds', 3600)
        )
    
    return _cache
