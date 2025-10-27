"""
Agente IA de Consulta Darwin - Módulos principales del agente
"""

__version__ = "2.0.0"
__author__ = "Darwin Team"

# Fase 1: Core Components
from .prompt_cache_manager import PromptCacheManager
from .conversation_manager import ConversationManager
from .config_manager import ConfigManager

# Fase 2: Functional Modules
from .tool_executor import ToolExecutor, ToolType, ToolResult, ConsolidatedResults
from .llm_communication import LLMCommunication, LLMRequest, LLMResponse
from .response_formatter import ResponseFormatter, ResponseFormat, FormattedResponse
from .request_handler import RequestHandler, RequestState, ProcessingMetrics, RequestResult
from .chat_interface import ChatInterface

__all__ = [
    # Fase 1
    "PromptCacheManager",
    "ConversationManager",
    "ConfigManager",
    # Fase 2
    "ToolExecutor",
    "ToolType",
    "ToolResult",
    "ConsolidatedResults",
    "LLMCommunication",
    "LLMRequest",
    "LLMResponse",
    "ResponseFormatter",
    "ResponseFormat",
    "FormattedResponse",
    "RequestHandler",
    "RequestState",
    "ProcessingMetrics",
    "RequestResult",
    "ChatInterface",
]
