"""
Conversation Logger Module - Registro de peticiones y respuestas

Responsabilidad: Registrar todas las peticiones y respuestas en archivos de log
- Crear directorio logs si no existe
- Registrar peticiones del usuario
- Registrar respuestas del LLM
- Registrar métricas de procesamiento
- Mantener logs organizados por sesión
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from session_manager import SessionManager


class ConversationLogger:
    """Logger para registrar conversaciones completas"""
    
    def __init__(self, logs_dir: str = "logs", session_manager: Optional['SessionManager'] = None):
        """
        Inicializa el logger de conversaciones
        
        Args:
            logs_dir: Directorio donde guardar los logs
            session_manager: Gestor de sesiones (opcional)
        """
        self.logs_dir = logs_dir
        self.session_manager = session_manager
        self.logger = logging.getLogger(__name__)
        
        # Crear directorio de logs si no existe
        self._ensure_logs_directory()
    
    def _ensure_logs_directory(self) -> None:
        """Crea el directorio de logs si no existe"""
        try:
            Path(self.logs_dir).mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Directorio de logs verificado: {self.logs_dir}")
            
            # Si hay session_manager, también crear sus directorios
            if self.session_manager:
                Path(self.logs_dir, "sessions").mkdir(exist_ok=True)
                Path(self.logs_dir, "conversations").mkdir(exist_ok=True)
        except Exception as e:
            self.logger.error(f"Error creando directorio de logs: {e}")
            raise
    
    def get_log_path(self) -> str:
        """
        Obtiene la ruta del archivo de log actual
        
        Returns:
            String con la ruta del archivo de log
        """
        if self.session_manager:
            log_path = self.session_manager.get_conversation_log_path()
            if log_path:
                return str(log_path)
        
        return f"{self.logs_dir}/conversation_default.json"
    
    def log_conversation_turn(
        self,
        session_id: str,
        user_input: str,
        llm_response: str,
        metrics: Optional[Dict[str, Any]] = None,
        request_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Registra un turno completo de conversación
        
        Args:
            session_id: ID de la sesión
            user_input: Input del usuario
            llm_response: Respuesta del LLM
            metrics: Métricas de procesamiento
            request_metadata: Metadatos del request
            
        Returns:
            Ruta del archivo de log creado
        """
        try:
            # Determinar ruta del archivo
            if self.session_manager:
                # Usar ruta específica de la sesión
                log_path = self.session_manager.get_conversation_log_path()
                if log_path:
                    filepath = str(log_path)
                else:
                    # Fallback si no hay sesión activa
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                    filename = f"conversation_{session_id}_{timestamp}.json"
                    filepath = os.path.join(self.logs_dir, filename)
            else:
                # Modo legacy: crear archivo con timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"conversation_{session_id}_{timestamp}.json"
                filepath = os.path.join(self.logs_dir, filename)
            
            # Preparar datos del turno
            turn_data = {
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "user_input": user_input,
                "llm_response": llm_response,
                "metrics": metrics or {},
                "request_metadata": request_metadata or {}
            }
            
            # Si el archivo ya existe, cargar turnos anteriores
            turns = []
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        if isinstance(existing_data, list):
                            turns = existing_data
                        elif isinstance(existing_data, dict) and 'turns' in existing_data:
                            turns = existing_data['turns']
                        else:
                            # Convertir formato antiguo a lista
                            turns = [existing_data]
                except Exception as e:
                    self.logger.warning(f"Error leyendo archivo existente: {e}")
            
            # Agregar nuevo turno
            turns.append(turn_data)
            
            # Escribir todos los turnos al archivo
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(turns, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Turno de conversación registrado: {filepath}")
            return filepath
        
        except Exception as e:
            self.logger.error(f"Error registrando turno de conversación: {e}")
            raise
    
    def log_session_summary(
        self,
        session_id: str,
        total_turns: int,
        total_time_ms: float,
        total_tokens: int,
        summary: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Registra un resumen de la sesión
        
        Args:
            session_id: ID de la sesión
            total_turns: Total de turnos en la sesión
            total_time_ms: Tiempo total en milisegundos
            total_tokens: Total de tokens utilizados
            summary: Resumen adicional
            
        Returns:
            Ruta del archivo de resumen
        """
        try:
            filename = f"session_summary_{session_id}.json"
            filepath = os.path.join(self.logs_dir, filename)
            
            summary_data = {
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "total_turns": total_turns,
                "total_time_ms": total_time_ms,
                "total_tokens": total_tokens,
                "summary": summary or {}
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Resumen de sesión registrado: {filepath}")
            return filepath
        
        except Exception as e:
            self.logger.error(f"Error registrando resumen de sesión: {e}")
            raise
    
    def log_error(
        self,
        session_id: str,
        error_message: str,
        error_type: str,
        user_input: Optional[str] = None,
        traceback_info: Optional[str] = None
    ) -> str:
        """
        Registra un error ocurrido durante la conversación
        
        Args:
            session_id: ID de la sesión
            error_message: Mensaje de error
            error_type: Tipo de error
            user_input: Input del usuario que causó el error
            traceback_info: Información de traceback
            
        Returns:
            Ruta del archivo de error
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"error_{session_id}_{timestamp}.json"
            filepath = os.path.join(self.logs_dir, filename)
            
            error_data = {
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "error_type": error_type,
                "error_message": error_message,
                "user_input": user_input,
                "traceback": traceback_info
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, indent=2, ensure_ascii=False)
            
            self.logger.error(f"Error registrado: {filepath}")
            return filepath
        
        except Exception as e:
            self.logger.error(f"Error registrando error: {e}")
            raise
    
    def get_session_logs(self, session_id: str) -> list:
        """
        Obtiene todos los logs de una sesión
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Lista de rutas de archivos de log
        """
        try:
            logs = []
            for filename in os.listdir(self.logs_dir):
                if session_id in filename:
                    filepath = os.path.join(self.logs_dir, filename)
                    logs.append(filepath)
            
            return sorted(logs)
        
        except Exception as e:
            self.logger.error(f"Error obteniendo logs de sesión: {e}")
            return []
    
    def cleanup_old_logs(self, days: int = 7) -> int:
        """
        Limpia logs más antiguos que el número de días especificado
        
        Args:
            days: Número de días para mantener logs
            
        Returns:
            Número de archivos eliminados
        """
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (days * 86400)  # 86400 segundos por día
            
            deleted_count = 0
            for filename in os.listdir(self.logs_dir):
                filepath = os.path.join(self.logs_dir, filename)
                if os.path.isfile(filepath):
                    file_time = os.path.getmtime(filepath)
                    if file_time < cutoff_time:
                        os.remove(filepath)
                        deleted_count += 1
                        self.logger.info(f"Archivo de log eliminado: {filepath}")
            
            return deleted_count
        
        except Exception as e:
            self.logger.error(f"Error limpiando logs antiguos: {e}")
            return 0


def main():
    """Función principal para testing"""
    import logging
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear logger
    logger = ConversationLogger()
    
    # Test: registrar un turno
    session_id = "test-session-001"
    user_input = "¿Qué es Darwin?"
    llm_response = "Darwin es un sistema de base de conocimiento..."
    metrics = {
        "total_time_ms": 1234.56,
        "llm_time_ms": 1000.00,
        "tokens_input": 150,
        "tokens_output": 200
    }
    
    filepath = logger.log_conversation_turn(
        session_id=session_id,
        user_input=user_input,
        llm_response=llm_response,
        metrics=metrics
    )
    
    print(f"✅ Turno registrado en: {filepath}")
    
    # Test: registrar resumen de sesión
    summary_filepath = logger.log_session_summary(
        session_id=session_id,
        total_turns=1,
        total_time_ms=1234.56,
        total_tokens=350
    )
    
    print(f"✅ Resumen registrado en: {summary_filepath}")


if __name__ == "__main__":
    main()
