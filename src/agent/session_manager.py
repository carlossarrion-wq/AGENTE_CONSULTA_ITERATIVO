"""
Session Manager - Gestión de sesiones de usuario

Responsabilidad: Gestionar sesiones de usuario con autenticación
- Crear y validar sesiones de usuario
- Generar IDs de sesión únicos
- Gestionar logs por usuario y sesión
- Mantener información de sesión activa
"""

import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json


class UserSession:
    """Representa una sesión de usuario"""
    
    def __init__(self, username: str, app_name: str):
        """
        Inicializa una sesión de usuario
        
        Args:
            username: Nombre de usuario
            app_name: Nombre de la aplicación (Darwin, SAP, MuleSoft)
        """
        self.username = username
        self.app_name = app_name
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.conversation_count = 0
        self.session_id = self._generate_session_id()
        
    def _generate_session_id(self) -> str:
        """
        Genera un ID de sesión único
        
        Formato: {username}_{app}_{timestamp}_{uuid}
        Ejemplo: darwin_001_darwin_20251029_152830_a1b2c3d4
        
        Returns:
            String con el ID de sesión
        """
        timestamp = self.created_at.strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"{self.username}_{self.app_name.lower()}_{timestamp}_{short_uuid}"
    
    def update_activity(self):
        """Actualiza el timestamp de última actividad"""
        self.last_activity = datetime.now()
        self.conversation_count += 1
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Obtiene información de la sesión
        
        Returns:
            Diccionario con información de la sesión
        """
        return {
            'session_id': self.session_id,
            'username': self.username,
            'app_name': self.app_name,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'conversation_count': self.conversation_count,
            'duration_minutes': (self.last_activity - self.created_at).total_seconds() / 60
        }
    
    def get_log_filename(self) -> str:
        """
        Genera el nombre del archivo de log para esta sesión
        
        Formato: conversation_{session_id}.json
        Ejemplo: conversation_darwin_001_darwin_20251029_152830_a1b2c3d4.json
        
        Returns:
            String con el nombre del archivo de log
        """
        return f"conversation_{self.session_id}.json"


class SessionManager:
    """Gestor de sesiones de usuario"""
    
    def __init__(self, logs_dir: str = "logs"):
        """
        Inicializa el gestor de sesiones
        
        Args:
            logs_dir: Directorio base para logs
        """
        self.logger = logging.getLogger(__name__)
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Directorio para logs de sesiones
        self.sessions_dir = self.logs_dir / "sessions"
        self.sessions_dir.mkdir(exist_ok=True)
        
        # Directorio para logs de conversaciones
        self.conversations_dir = self.logs_dir / "conversations"
        self.conversations_dir.mkdir(exist_ok=True)
        
        # Sesión activa
        self.current_session: Optional[UserSession] = None
        
        self.logger.info(f"SessionManager inicializado")
        self.logger.info(f"  Logs dir: {self.logs_dir}")
        self.logger.info(f"  Sessions dir: {self.sessions_dir}")
        self.logger.info(f"  Conversations dir: {self.conversations_dir}")
    
    def create_session(self, username: str, app_name: str) -> UserSession:
        """
        Crea una nueva sesión de usuario
        
        Args:
            username: Nombre de usuario
            app_name: Nombre de la aplicación
            
        Returns:
            UserSession creada
        """
        # Validar username
        if not username or not username.strip():
            raise ValueError("Username no puede estar vacío")
        
        # Sanitizar username (solo alfanuméricos, guiones y guiones bajos)
        username = ''.join(c for c in username if c.isalnum() or c in ['_', '-'])
        
        # Crear sesión
        session = UserSession(username, app_name)
        self.current_session = session
        
        # Guardar información de sesión
        self._save_session_info(session)
        
        self.logger.info(f"✅ Sesión creada para usuario: {username}")
        self.logger.info(f"   Session ID: {session.session_id}")
        self.logger.info(f"   App: {app_name}")
        self.logger.info(f"   Log file: {session.get_log_filename()}")
        
        return session
    
    def get_current_session(self) -> Optional[UserSession]:
        """
        Obtiene la sesión actual
        
        Returns:
            UserSession actual o None si no hay sesión activa
        """
        return self.current_session
    
    def update_session_activity(self):
        """Actualiza la actividad de la sesión actual"""
        if self.current_session:
            self.current_session.update_activity()
            self._save_session_info(self.current_session)
    
    def end_session(self):
        """Finaliza la sesión actual"""
        if self.current_session:
            # Guardar información final de sesión
            self._save_session_info(self.current_session, final=True)
            
            self.logger.info(f"✅ Sesión finalizada: {self.current_session.session_id}")
            self.logger.info(f"   Usuario: {self.current_session.username}")
            self.logger.info(f"   Conversaciones: {self.current_session.conversation_count}")
            self.logger.info(f"   Duración: {self.current_session.get_session_info()['duration_minutes']:.2f} minutos")
            
            self.current_session = None
    
    def get_conversation_log_path(self) -> Optional[Path]:
        """
        Obtiene la ruta del archivo de log de conversación para la sesión actual
        
        Returns:
            Path al archivo de log o None si no hay sesión activa
        """
        if not self.current_session:
            return None
        
        return self.conversations_dir / self.current_session.get_log_filename()
    
    def _save_session_info(self, session: UserSession, final: bool = False):
        """
        Guarda información de la sesión en un archivo JSON
        
        Args:
            session: Sesión a guardar
            final: Si es True, marca la sesión como finalizada
        """
        try:
            session_file = self.sessions_dir / f"session_{session.session_id}.json"
            
            session_info = session.get_session_info()
            session_info['status'] = 'completed' if final else 'active'
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_info, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Información de sesión guardada: {session_file}")
        
        except Exception as e:
            self.logger.error(f"Error guardando información de sesión: {str(e)}")
    
    def list_user_sessions(self, username: str) -> list:
        """
        Lista todas las sesiones de un usuario
        
        Args:
            username: Nombre de usuario
            
        Returns:
            Lista de diccionarios con información de sesiones
        """
        sessions = []
        
        try:
            for session_file in self.sessions_dir.glob(f"session_{username}_*.json"):
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_info = json.load(f)
                    sessions.append(session_info)
            
            # Ordenar por fecha de creación (más reciente primero)
            sessions.sort(key=lambda x: x['created_at'], reverse=True)
        
        except Exception as e:
            self.logger.error(f"Error listando sesiones de usuario: {str(e)}")
        
        return sessions
    
    def get_session_summary(self) -> str:
        """
        Genera un resumen de la sesión actual
        
        Returns:
            String con resumen formateado
        """
        if not self.current_session:
            return "No hay sesión activa"
        
        info = self.current_session.get_session_info()
        
        summary = f"""
╔════════════════════════════════════════════════════════════════╗
║                    INFORMACIÓN DE SESIÓN                       ║
╚════════════════════════════════════════════════════════════════╝

👤 Usuario: {info['username']}
🏢 Aplicación: {info['app_name']}
🆔 Session ID: {info['session_id']}

📅 Creada: {datetime.fromisoformat(info['created_at']).strftime('%Y-%m-%d %H:%M:%S')}
⏱️  Última actividad: {datetime.fromisoformat(info['last_activity']).strftime('%Y-%m-%d %H:%M:%S')}
💬 Conversaciones: {info['conversation_count']}
⏳ Duración: {info['duration_minutes']:.2f} minutos

📝 Log de conversación: {self.current_session.get_log_filename()}
"""
        return summary


def main():
    """Función principal para testing"""
    import logging
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear gestor de sesiones
    session_mgr = SessionManager()
    
    # Crear sesión de prueba
    session = session_mgr.create_session("darwin_001", "Darwin")
    
    # Mostrar información
    print(session_mgr.get_session_summary())
    
    # Simular actividad
    session_mgr.update_session_activity()
    session_mgr.update_session_activity()
    
    # Mostrar información actualizada
    print(session_mgr.get_session_summary())
    
    # Finalizar sesión
    session_mgr.end_session()
    
    # Listar sesiones del usuario
    sessions = session_mgr.list_user_sessions("darwin_001")
    print(f"\nSesiones del usuario darwin_001: {len(sessions)}")
    for s in sessions:
        print(f"  - {s['session_id']} ({s['status']})")


if __name__ == "__main__":
    main()
