"""
Conversation Manager - Gestión del historial conversacional y contexto

Este módulo implementa:
- Historial estructurado de turnos usuario/asistente
- Gestión de tokens por conversación
- Context window management inteligente
- Integración de resultados de herramientas
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)


class ConversationTurn:
    """Representa un turno en la conversación"""

    def __init__(
        self,
        role: str,
        content: str,
        tokens: int = 0,
        tools_used: Optional[List[str]] = None,
        tool_results: Optional[Dict] = None,
    ):
        self.role = role  # "user" o "assistant"
        self.content = content
        self.tokens = tokens
        self.tools_used = tools_used or []
        self.tool_results = tool_results or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        """Convertir turno a diccionario"""
        return {
            "role": self.role,
            "content": self.content,
            "tokens": self.tokens,
            "tools_used": self.tools_used,
            "tool_results": self.tool_results,
            "timestamp": self.timestamp.isoformat(),
        }


class Conversation:
    """Representa una conversación completa"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.turns: List[ConversationTurn] = []
        self.total_tokens = 0
        self.created_at = datetime.now()
        self.last_updated = datetime.now()

    def add_turn(self, turn: ConversationTurn) -> None:
        """Agregar un turno a la conversación"""
        self.turns.append(turn)
        self.total_tokens += turn.tokens
        self.last_updated = datetime.now()

    def get_context(self, max_turns: Optional[int] = None) -> str:
        """
        Obtener contexto conversacional

        Args:
            max_turns: Máximo número de turnos a incluir (None = todos)

        Returns:
            Contexto formateado
        """
        turns_to_include = self.turns
        if max_turns:
            turns_to_include = self.turns[-max_turns:]

        context_parts = []
        for turn in turns_to_include:
            if turn.role == "user":
                context_parts.append(f"Human: {turn.content}")
            else:
                context_parts.append(f"Assistant: {turn.content}")

        return "\n\n".join(context_parts)

    def to_dict(self) -> Dict:
        """Convertir conversación a diccionario"""
        return {
            "session_id": self.session_id,
            "turns": [turn.to_dict() for turn in self.turns],
            "total_tokens": self.total_tokens,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }


class ConversationManager:
    """
    Gestor de conversaciones y contexto

    Características:
    - Historial estructurado de turnos
    - Gestión de tokens por conversación
    - Context window management
    - Integración de resultados de herramientas
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializar el Conversation Manager

        Args:
            config: Configuración (max_history_turns, context_window_tokens, etc.)
        """
        self.config = config or {}
        self.max_history_turns = self.config.get("max_history_turns", 20)
        self.context_window_tokens = self.config.get("context_window_tokens", 100000)
        self.system_prompt_caching = self.config.get("system_prompt_caching", True)
        self.tool_results_caching = self.config.get("tool_results_caching", True)

        # Almacenamiento de conversaciones
        self._conversations: Dict[str, Conversation] = {}

        logger.info(
            f"ConversationManager inicializado con max_turns={self.max_history_turns}, "
            f"context_window={self.context_window_tokens} tokens"
        )

    def create_conversation(self, session_id: Optional[str] = None) -> str:
        """
        Crear una nueva conversación

        Args:
            session_id: ID de sesión (se genera si no se proporciona)

        Returns:
            ID de la sesión creada
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        if session_id not in self._conversations:
            self._conversations[session_id] = Conversation(session_id)
            logger.info(f"Conversación creada: {session_id}")

        return session_id

    def add_user_turn(self, session_id: str, message: str, tokens: int = 0) -> None:
        """
        Agregar turno del usuario

        Args:
            session_id: ID de la sesión
            message: Mensaje del usuario
            tokens: Número de tokens (estimado si no se proporciona)
        """
        if session_id not in self._conversations:
            self.create_conversation(session_id)

        if tokens == 0:
            tokens = self._estimate_tokens(message)

        turn = ConversationTurn(role="user", content=message, tokens=tokens)
        self._conversations[session_id].add_turn(turn)

        logger.debug(f"Turno usuario agregado a {session_id}: {len(message)} chars, {tokens} tokens")

    def add_assistant_turn(
        self,
        session_id: str,
        response: str,
        tools_used: Optional[List[str]] = None,
        tool_results: Optional[Dict] = None,
        tokens: int = 0,
    ) -> None:
        """
        Agregar turno del asistente

        Args:
            session_id: ID de la sesión
            response: Respuesta del asistente
            tools_used: Lista de herramientas utilizadas
            tool_results: Resultados de las herramientas
            tokens: Número de tokens (estimado si no se proporciona)
        """
        if session_id not in self._conversations:
            self.create_conversation(session_id)

        if tokens == 0:
            tokens = self._estimate_tokens(response)

        turn = ConversationTurn(
            role="assistant",
            content=response,
            tokens=tokens,
            tools_used=tools_used,
            tool_results=tool_results,
        )
        self._conversations[session_id].add_turn(turn)

        logger.debug(
            f"Turno asistente agregado a {session_id}: {len(response)} chars, "
            f"{tokens} tokens, herramientas: {tools_used}"
        )

    def get_conversation_context(
        self, session_id: str, max_turns: Optional[int] = None
    ) -> str:
        """
        Obtener contexto conversacional

        Args:
            session_id: ID de la sesión
            max_turns: Máximo número de turnos (None = usar configuración)

        Returns:
            Contexto formateado
        """
        if session_id not in self._conversations:
            return ""

        if max_turns is None:
            max_turns = self.max_history_turns

        return self._conversations[session_id].get_context(max_turns)

    def trim_context_to_window(
        self, session_id: str, max_tokens: Optional[int] = None
    ) -> str:
        """
        Obtener contexto trimmed a la ventana de contexto máxima

        Args:
            session_id: ID de la sesión
            max_tokens: Máximo de tokens (None = usar configuración)

        Returns:
            Contexto trimmed
        """
        if session_id not in self._conversations:
            return ""

        if max_tokens is None:
            max_tokens = self.context_window_tokens

        conversation = self._conversations[session_id]
        context_parts = []
        token_count = 0

        # Usar sliding window: últimos turnos que caben en el límite
        for turn in reversed(conversation.turns):
            if token_count + turn.tokens > max_tokens:
                break

            context_parts.insert(0, self._format_turn(turn))
            token_count += turn.tokens

        return "\n\n".join(context_parts)

    def get_token_count(self, session_id: str) -> int:
        """
        Obtener total de tokens en una conversación

        Args:
            session_id: ID de la sesión

        Returns:
            Total de tokens
        """
        if session_id not in self._conversations:
            return 0

        return self._conversations[session_id].total_tokens

    def get_conversation_stats(self, session_id: str) -> Dict:
        """
        Obtener estadísticas de una conversación

        Args:
            session_id: ID de la sesión

        Returns:
            Diccionario con estadísticas
        """
        if session_id not in self._conversations:
            return {}

        conv = self._conversations[session_id]
        user_turns = sum(1 for t in conv.turns if t.role == "user")
        assistant_turns = sum(1 for t in conv.turns if t.role == "assistant")
        tools_used = set()
        for turn in conv.turns:
            tools_used.update(turn.tools_used)

        return {
            "session_id": session_id,
            "total_turns": len(conv.turns),
            "user_turns": user_turns,
            "assistant_turns": assistant_turns,
            "total_tokens": conv.total_tokens,
            "tools_used": list(tools_used),
            "created_at": conv.created_at.isoformat(),
            "last_updated": conv.last_updated.isoformat(),
        }

    def delete_conversation(self, session_id: str) -> None:
        """
        Eliminar una conversación

        Args:
            session_id: ID de la sesión
        """
        if session_id in self._conversations:
            del self._conversations[session_id]
            logger.info(f"Conversación eliminada: {session_id}")

    def get_all_sessions(self) -> List[str]:
        """
        Obtener lista de todas las sesiones activas

        Returns:
            Lista de IDs de sesión
        """
        return list(self._conversations.keys())

    # Métodos privados

    def _estimate_tokens(self, text: str) -> int:
        """Estimar número de tokens (aproximación simple)"""
        # Aproximación: 1 token ≈ 4 caracteres
        return len(text) // 4

    def _format_turn(self, turn: ConversationTurn) -> str:
        """Formatear un turno para display"""
        if turn.role == "user":
            return f"Human: {turn.content}"
        else:
            formatted = f"Assistant: {turn.content}"
            if turn.tools_used:
                formatted += f"\n[Herramientas utilizadas: {', '.join(turn.tools_used)}]"
            return formatted
