"""
Common Module - Utilidades compartidas

Este módulo contiene utilidades compartidas por todas las herramientas:
- Config: Gestión de configuración desde YAML
- OpenSearchClient: Cliente singleton para OpenSearch
- BedrockClient: Cliente singleton para AWS Bedrock
- Logger: Configuración de logging
- Decoradores: handle_search_error, log_search_metrics, validate_parameters
- Utilidades: calculate_text_similarity, find_overlap_length, remove_duplicate_chunks_by_hash
- SimpleCache: Cache en memoria con TTL
"""

from .common import (
    Config,
    SearchError,
    ConnectionError,
    ValidationError,
    OpenSearchClient,
    BedrockClient,
    Logger,
    handle_search_error,
    log_search_metrics,
    validate_parameters,
    calculate_text_similarity,
    find_overlap_length,
    remove_duplicate_chunks_by_hash,
    SimpleCache,
    get_cache
)

__all__ = [
    'Config',
    'SearchError',
    'ConnectionError',
    'ValidationError',
    'OpenSearchClient',
    'BedrockClient',
    'Logger',
    'handle_search_error',
    'log_search_metrics',
    'validate_parameters',
    'calculate_text_similarity',
    'find_overlap_length',
    'remove_duplicate_chunks_by_hash',
    'SimpleCache',
    'get_cache'
]
