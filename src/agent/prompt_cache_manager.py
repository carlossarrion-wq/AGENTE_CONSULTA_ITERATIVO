"""
Prompt Cache Manager - Gestión inteligente del cache de prompts para optimizar rendimiento y costos

Este módulo implementa un sistema de caching para:
- Cache del system prompt (una sola vez por sesión)
- Cache conversacional incremental
- Compresión inteligente de contexto
- Sliding window de contexto relevante
"""

import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class PromptCache:
    """Estructura para almacenar información de cache de un prompt"""

    def __init__(self, session_id: str, system_prompt_hash: str):
        self.session_id = session_id
        self.system_prompt_hash = system_prompt_hash
        self.turns: List[Dict] = []
        self.total_tokens = 0
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        self.cache_ttl = datetime.now() + timedelta(hours=1)

    def to_dict(self) -> Dict:
        """Convertir cache a diccionario"""
        return {
            "session_id": self.session_id,
            "system_prompt_hash": self.system_prompt_hash,
            "turns": self.turns,
            "total_tokens": self.total_tokens,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "cache_ttl": self.cache_ttl.isoformat(),
        }


class PromptCacheManager:
    """
    Gestor de cache de prompts para optimizar comunicación con LLM

    Características:
    - Cache del system prompt (reutilizable en toda la sesión)
    - Cache conversacional incremental
    - Compresión de contexto cuando se acerca al límite
    - Sliding window para mantener contexto relevante
    - TTL configurable para expiración de cache
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializar el Prompt Cache Manager

        Args:
            config: Configuración del cache (TTL, tamaño máximo, etc.)
        """
        self.config = config or {}
        self.cache_ttl_minutes = self.config.get("cache_ttl_minutes", 60)
        self.max_cached_conversations = self.config.get("max_cached_conversations", 100)
        self.cache_compression = self.config.get("cache_compression", True)
        self.incremental_updates = self.config.get("incremental_updates", True)
        self.cache_strategy = self.config.get("cache_strategy", "sliding_window")

        # Almacenamiento de caches
        self._system_prompt_cache: Dict[str, Tuple[str, str]] = {}  # {hash: (prompt, timestamp)}
        self._conversation_caches: Dict[str, PromptCache] = {}  # {session_id: PromptCache}

        logger.info(
            f"PromptCacheManager inicializado con TTL={self.cache_ttl_minutes}min, "
            f"max_conversations={self.max_cached_conversations}"
        )

    def cache_system_prompt(self, prompt: str) -> str:
        """
        Cachear el system prompt

        Args:
            prompt: El system prompt a cachear

        Returns:
            Hash del prompt cacheado
        """
        prompt_hash = self._hash_content(prompt)

        if prompt_hash not in self._system_prompt_cache:
            self._system_prompt_cache[prompt_hash] = (prompt, datetime.now().isoformat())
            logger.info(f"System prompt cacheado: {prompt_hash[:8]}...")

        return prompt_hash

    def get_cached_conversation(self, session_id: str) -> Optional[PromptCache]:
        """
        Obtener cache conversacional de una sesión

        Args:
            session_id: ID de la sesión

        Returns:
            PromptCache si existe y no ha expirado, None en caso contrario
        """
        if session_id not in self._conversation_caches:
            return None

        cache = self._conversation_caches[session_id]

        # Verificar si el cache ha expirado
        if datetime.now() > cache.cache_ttl:
            logger.info(f"Cache expirado para sesión {session_id}")
            del self._conversation_caches[session_id]
            return None

        return cache

    def update_conversation_cache(
        self, session_id: str, system_prompt_hash: str, new_turn: Dict
    ) -> None:
        """
        Actualizar cache conversacional con un nuevo turno

        Args:
            session_id: ID de la sesión
            system_prompt_hash: Hash del system prompt
            new_turn: Nuevo turno a agregar (user o assistant)
        """
        # Crear cache si no existe
        if session_id not in self._conversation_caches:
            if len(self._conversation_caches) >= self.max_cached_conversations:
                self._evict_oldest_cache()

            self._conversation_caches[session_id] = PromptCache(session_id, system_prompt_hash)

        cache = self._conversation_caches[session_id]

        # Agregar nuevo turno
        cache.turns.append(new_turn)
        cache.total_tokens += new_turn.get("tokens", 0)
        cache.last_updated = datetime.now()
        cache.cache_ttl = datetime.now() + timedelta(minutes=self.cache_ttl_minutes)

        logger.debug(
            f"Cache actualizado para sesión {session_id}: "
            f"{len(cache.turns)} turnos, {cache.total_tokens} tokens"
        )

    def build_incremental_prompt(
        self, session_id: str, system_prompt: str, user_input: str, max_context_tokens: int = 100000
    ) -> str:
        """
        Construir prompt incremental optimizado con cache

        Args:
            session_id: ID de la sesión
            system_prompt: El system prompt completo
            user_input: Nuevo input del usuario
            max_context_tokens: Máximo de tokens en el contexto

        Returns:
            Prompt optimizado para enviar al LLM
        """
        cache = self.get_cached_conversation(session_id)

        prompt_parts = []

        # 1. System prompt (cacheado)
        prompt_parts.append(system_prompt)

        # 2. Contexto conversacional (si existe)
        if cache and cache.turns:
            context = self._build_conversation_context(cache.turns, max_context_tokens)
            if context:
                prompt_parts.append(context)

        # 3. Nuevo input del usuario
        prompt_parts.append(f"Human: {user_input}")
        prompt_parts.append("Assistant:")

        return "\n\n".join(prompt_parts)

    def compress_context_if_needed(self, context: str, max_tokens: int = 100000) -> str:
        """
        Comprimir contexto si se acerca al límite de tokens

        Args:
            context: Contexto a comprimir
            max_tokens: Máximo de tokens permitidos

        Returns:
            Contexto comprimido o original
        """
        if not self.cache_compression:
            return context

        token_count = self._estimate_tokens(context)

        if token_count > max_tokens * 0.8:  # Si usa más del 80% del límite
            logger.info(f"Comprimiendo contexto: {token_count} tokens -> ", end="")
            compressed = self._compress_text(context)
            compressed_tokens = self._estimate_tokens(compressed)
            logger.info(f"{compressed_tokens} tokens")
            return compressed

        return context

    def invalidate_cache(self, session_id: str) -> None:
        """
        Invalidar cache de una sesión

        Args:
            session_id: ID de la sesión a invalidar
        """
        if session_id in self._conversation_caches:
            del self._conversation_caches[session_id]
            logger.info(f"Cache invalidado para sesión {session_id}")

    def get_cache_stats(self) -> Dict:
        """
        Obtener estadísticas del cache

        Returns:
            Diccionario con estadísticas
        """
        total_conversations = len(self._conversation_caches)
        total_turns = sum(len(c.turns) for c in self._conversation_caches.values())
        total_tokens = sum(c.total_tokens for c in self._conversation_caches.values())

        return {
            "total_conversations": total_conversations,
            "total_turns": total_turns,
            "total_tokens": total_tokens,
            "system_prompts_cached": len(self._system_prompt_cache),
            "max_conversations": self.max_cached_conversations,
        }

    # Métodos privados

    def _hash_content(self, content: str) -> str:
        """Generar hash SHA256 del contenido"""
        return hashlib.sha256(content.encode()).hexdigest()

    def _build_conversation_context(self, turns: List[Dict], max_tokens: int) -> str:
        """Construir contexto conversacional respetando límite de tokens"""
        context_parts = []
        token_count = 0

        # Usar sliding window: últimos turnos que caben en el límite
        for turn in reversed(turns):
            turn_tokens = turn.get("tokens", 0)

            if token_count + turn_tokens > max_tokens:
                break

            context_parts.insert(0, turn["content"])
            token_count += turn_tokens

        return "\n\n".join(context_parts) if context_parts else ""

    def _estimate_tokens(self, text: str) -> int:
        """Estimar número de tokens (aproximación simple)"""
        # Aproximación: 1 token ≈ 4 caracteres
        return len(text) // 4

    def _compress_text(self, text: str) -> str:
        """Comprimir texto eliminando redundancias"""
        # Implementación simple: eliminar líneas duplicadas y espacios excesivos
        lines = text.split("\n")
        unique_lines = []
        seen = set()

        for line in lines:
            stripped = line.strip()
            if stripped and stripped not in seen:
                unique_lines.append(line)
                seen.add(stripped)

        return "\n".join(unique_lines)

    def _evict_oldest_cache(self) -> None:
        """Evictar el cache más antiguo cuando se alcanza el límite"""
        if not self._conversation_caches:
            return

        oldest_session = min(
            self._conversation_caches.items(), key=lambda x: x[1].created_at
        )[0]

        del self._conversation_caches[oldest_session]
        logger.info(f"Cache evictado para sesión {oldest_session}")
