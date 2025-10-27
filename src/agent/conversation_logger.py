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
from typing import Dict, Any, Optional
from pathlib import Path


class ConversationLogger:
    """Logger para registrar conversaciones completas"""
    
    def __init__(self, logs_dir: str = "logs"):
        """
        Inicializa el logger de conversaciones
        
        Args:
            logs_dir: Directorio donde guardar los logs
        """
        self.logs_dir = logs_dir
        self.logger = logging.getLogger(__name__)
        
        # Crear directorio de logs si no existe
        self._ensure_logs_directory()
    
    def _ensure_logs_directory(self) -> None:
        """Crea el directorio de logs si no existe"""
        try:
            Path(self.logs_dir).mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Directorio de logs verificado: {self.logs_dir}")
        except Exception as e:
            self.logger.error(f"Error creando directorio de logs: {e}")
            raise
    
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
            # Crear nombre de archivo con timestamp
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
            
            # Escribir a archivo JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(turn_data, f, indent=2, ensure_ascii=False)
            
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
