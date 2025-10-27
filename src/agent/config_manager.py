"""
Config Manager - Gestión centralizada de configuración del agente

Este módulo implementa:
- Carga de configuración desde archivos YAML
- Gestión de variables de entorno
- Validación de configuración
- Acceso centralizado a parámetros
"""

import os
import yaml
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Gestor centralizado de configuración del agente

    Características:
    - Carga de configuración desde YAML
    - Soporte para variables de entorno
    - Validación de parámetros
    - Acceso tipo diccionario
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializar el Config Manager

        Args:
            config_path: Ruta al archivo de configuración YAML
        """
        self.config_path = config_path or "config/config.yaml"
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Cargar configuración desde archivo YAML"""
        if not os.path.exists(self.config_path):
            logger.warning(f"Archivo de configuración no encontrado: {self.config_path}")
            self._config = self._get_default_config()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
            logger.info(f"Configuración cargada desde: {self.config_path}")
        except Exception as e:
            logger.error(f"Error al cargar configuración: {e}")
            self._config = self._get_default_config()

        # Aplicar variables de entorno
        self._apply_env_overrides()

    def _apply_env_overrides(self) -> None:
        """Aplicar overrides desde variables de entorno"""
        env_mappings = {
            "OPENSEARCH_HOST": ("opensearch", "host"),
            "OPENSEARCH_INDEX": ("opensearch", "index_name"),
            "BEDROCK_REGION": ("bedrock", "region_name"),
            "BEDROCK_MODEL": ("bedrock", "model_id"),
            "LLM_MODEL": ("llm", "model_id"),
            "LLM_MAX_TOKENS": ("llm", "max_tokens"),
            "LLM_TEMPERATURE": ("llm", "temperature"),
        }

        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                if section not in self._config:
                    self._config[section] = {}
                self._config[section][key] = value
                logger.debug(f"Override desde env: {env_var} -> {section}.{key}")

    def _get_default_config(self) -> Dict[str, Any]:
        """Obtener configuración por defecto"""
        return {
            "opensearch": {
                "host": "vpc-rag-opensearch-clean-qodnaopeuroal2f6intbz7i5xy.eu-west-1.es.amazonaws.com",
                "index_name": "rag-documents-darwin",
            },
            "bedrock": {
                "region_name": "eu-west-1",
                "model_id": "amazon.titan-embed-image-v1",
            },
            "agent": {
                "max_conversation_turns": 50,
                "max_tools_per_response": 5,
                "response_timeout_seconds": 120,
            },
            "llm": {
                "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
                "max_tokens": 4000,
                "temperature": 0.1,
            },
            "prompt_caching": {
                "enabled": True,
                "cache_ttl_minutes": 60,
                "max_cached_conversations": 100,
                "cache_compression": True,
                "incremental_updates": True,
                "cache_strategy": "sliding_window",
            },
            "conversation": {
                "max_history_turns": 20,
                "context_window_tokens": 100000,
                "system_prompt_caching": True,
                "tool_results_caching": True,
            },
            "chat": {
                "welcome_message": "¡Hola! Soy el agente Darwin. ¿En qué puedo ayudarte?",
                "max_history_length": 20,
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtener valor de configuración

        Args:
            key: Clave en formato "section.key" o "section.subsection.key"
            default: Valor por defecto si no existe

        Returns:
            Valor de configuración
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Obtener sección completa de configuración

        Args:
            section: Nombre de la sección

        Returns:
            Diccionario con la sección
        """
        return self._config.get(section, {})

    def set(self, key: str, value: Any) -> None:
        """
        Establecer valor de configuración

        Args:
            key: Clave en formato "section.key"
            value: Valor a establecer
        """
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value
        logger.debug(f"Configuración actualizada: {key} = {value}")

    def validate(self) -> bool:
        """
        Validar configuración

        Returns:
            True si la configuración es válida
        """
        required_sections = ["opensearch", "bedrock", "llm"]

        for section in required_sections:
            if section not in self._config:
                logger.error(f"Sección requerida no encontrada: {section}")
                return False

        # Validar OpenSearch
        if not self.get("opensearch.host"):
            logger.error("opensearch.host no configurado")
            return False

        # Validar Bedrock
        if not self.get("bedrock.region_name"):
            logger.error("bedrock.region_name no configurado")
            return False

        # Validar LLM
        if not self.get("llm.model_id"):
            logger.error("llm.model_id no configurado")
            return False

        logger.info("Configuración validada correctamente")
        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        Obtener configuración completa como diccionario

        Returns:
            Diccionario con toda la configuración
        """
        return self._config.copy()

    def __getitem__(self, key: str) -> Any:
        """Acceso tipo diccionario"""
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Asignación tipo diccionario"""
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        """Verificar si existe clave"""
        return self.get(key) is not None

    def __repr__(self) -> str:
        """Representación en string"""
        return f"ConfigManager(path={self.config_path}, sections={list(self._config.keys())})"
