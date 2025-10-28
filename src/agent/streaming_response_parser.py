"""
Streaming Response Parser - Parser incremental para respuestas del LLM en streaming

Responsabilidad: Detectar y clasificar bloques XML en tiempo real
- Detección de inicio/fin de bloques XML
- Clasificación de bloques (thinking/tool/answer)
- Emisión de eventos por tipo de bloque
- Buffer incremental para manejar tokens fragmentados
"""

import re
import logging
from typing import List, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class BlockType(Enum):
    """Tipos de bloques que puede contener una respuesta del LLM"""
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    PRESENT_ANSWER = "present_answer"
    PLAIN_TEXT = "plain_text"


@dataclass
class StreamingBlock:
    """Representa un bloque detectado en el stream"""
    block_type: BlockType
    content: str
    tool_name: Optional[str] = None
    is_complete: bool = False
    start_position: int = 0
    end_position: int = 0
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class StreamingResponseParser:
    """
    Parser incremental que procesa el stream token por token
    y detecta bloques XML en tiempo real
    """
    
    def __init__(self):
        """Inicializa el parser de streaming"""
        self.logger = logging.getLogger(__name__)
        self.buffer = ""
        self.current_block = None
        self.block_stack = []
        self.completed_blocks = []
        self.position = 0
        
        # Patrones de detección de bloques
        self.block_patterns = {
            BlockType.THINKING: (r'<thinking>', r'</thinking>'),
            BlockType.PRESENT_ANSWER: (r'<present_answer>', r'</present_answer>'),
        }
        
        # Patrones de herramientas
        self.tool_patterns = [
            r'<tool_semantic_search>',
            r'<tool_lexical_search>',
            r'<tool_regex_search>',
            r'<tool_get_file_content>',
        ]
        
        self.logger.debug("StreamingResponseParser inicializado")
    
    def feed_token(self, token: str) -> List[StreamingBlock]:
        """
        Alimenta el parser con un nuevo token del stream
        
        Args:
            token: Token recibido del LLM
            
        Returns:
            Lista de bloques completados o parciales en este token
        """
        self.buffer += token
        self.position += len(token)
        
        completed = []
        
        # Detectar inicio de nuevo bloque
        if self.current_block is None:
            block_type = self.detect_block_start()
            if block_type:
                self.start_new_block(block_type)
        
        # Si hay un bloque activo, procesar contenido incremental
        if self.current_block is not None:
            # Para thinking y answer, emitir contenido incremental
            if self.current_block.block_type in [BlockType.THINKING, BlockType.PRESENT_ANSWER]:
                # Emitir bloque de inicio si no se ha hecho
                if not hasattr(self, 'current_block_emitted_start') or not self.current_block_emitted_start:
                    start_block = StreamingBlock(
                        block_type=self.current_block.block_type,
                        content="",
                        is_complete=False,
                        start_position=self.current_block.start_position,
                        end_position=self.position
                    )
                    start_block.is_start_marker = True
                    completed.append(start_block)
                    self.current_block_emitted_start = True
                
                # Emitir contenido incremental si hay suficiente
                if len(self.buffer) > 0 and not self.detect_block_end():
                    # Emitir el contenido actual del buffer
                    incremental_block = StreamingBlock(
                        block_type=self.current_block.block_type,
                        content=self.buffer,
                        is_complete=False,
                        start_position=self.current_block.start_position,
                        end_position=self.position
                    )
                    incremental_block.is_incremental = True
                    completed.append(incremental_block)
                    
                    # Limpiar buffer después de emitir
                    self.buffer = ""
            
            # Para herramientas (TOOL_CALL), NO emitir contenido incremental
            # Solo acumular en buffer hasta que el bloque esté completo
            elif self.current_block.block_type == BlockType.TOOL_CALL:
                # No hacer nada, solo acumular en buffer
                # El contenido se emitirá cuando el bloque esté completo
                pass
            
            # Detectar fin de bloque actual
            if self.detect_block_end():
                completed_block = self.complete_current_block()
                if completed_block:
                    completed.append(completed_block)
                    # Resetear flag
                    self.current_block_emitted_start = False
        
        # Si no hay bloque activo, acumular como texto plano
        if self.current_block is None and self.buffer.strip():
            # Verificar si hay suficiente contenido para emitir como texto plano
            if len(self.buffer) > 50 or '\n' in self.buffer:
                plain_block = self.extract_plain_text()
                if plain_block:
                    completed.append(plain_block)
        
        return completed
    
    def detect_block_start(self) -> Optional[BlockType]:
        """
        Detecta el inicio de un bloque XML en el buffer
        
        Returns:
            BlockType si se detecta inicio de bloque, None en caso contrario
        """
        # Detectar bloques estándar (thinking, present_answer)
        for block_type, (start_pattern, _) in self.block_patterns.items():
            if re.search(start_pattern, self.buffer):
                self.logger.debug(f"Detectado inicio de bloque: {block_type.value}")
                return block_type
        
        # Detectar herramientas
        for tool_pattern in self.tool_patterns:
            if re.search(tool_pattern, self.buffer):
                tool_name = self.extract_tool_name(tool_pattern)
                self.logger.debug(f"Detectado inicio de herramienta: {tool_name}")
                return BlockType.TOOL_CALL
        
        return None
    
    def detect_block_end(self) -> bool:
        """
        Detecta el fin del bloque actual en el buffer
        
        Returns:
            True si se detecta fin de bloque, False en caso contrario
        """
        if self.current_block is None:
            return False
        
        block_type = self.current_block.block_type
        
        # Para bloques estándar
        if block_type in self.block_patterns:
            _, end_pattern = self.block_patterns[block_type]
            if re.search(end_pattern, self.buffer):
                self.logger.debug(f"Detectado fin de bloque: {block_type.value}")
                return True
        
        # Para herramientas
        if block_type == BlockType.TOOL_CALL and self.current_block.tool_name:
            tool_name = self.current_block.tool_name
            end_pattern = f'</{tool_name}>'
            if end_pattern in self.buffer:
                self.logger.debug(f"Detectado fin de herramienta: {tool_name}")
                return True
        
        return False
    
    def start_new_block(self, block_type: BlockType):
        """
        Inicia un nuevo bloque
        
        Args:
            block_type: Tipo de bloque a iniciar
        """
        # Extraer contenido antes del bloque como texto plano
        if block_type in self.block_patterns:
            start_pattern, _ = self.block_patterns[block_type]
            match = re.search(start_pattern, self.buffer)
            if match:
                # Contenido antes del tag
                before_content = self.buffer[:match.start()].strip()
                if before_content:
                    plain_block = StreamingBlock(
                        block_type=BlockType.PLAIN_TEXT,
                        content=before_content,
                        is_complete=True,
                        start_position=self.position - len(self.buffer),
                        end_position=self.position - len(self.buffer) + match.start()
                    )
                    self.completed_blocks.append(plain_block)
                
                # Remover contenido procesado del buffer
                self.buffer = self.buffer[match.end():]
        
        # Para herramientas, también extraer contenido antes y remover tag de apertura
        elif block_type == BlockType.TOOL_CALL:
            # Buscar el patrón de herramienta en el buffer y extraer el nombre ANTES de removerlo
            tool_name = None
            for tool_pattern in self.tool_patterns:
                match = re.search(tool_pattern, self.buffer)
                if match:
                    # Extraer nombre de la herramienta del patrón
                    tool_name = self.extract_tool_name(tool_pattern)
                    
                    # Contenido antes del tag de herramienta
                    before_content = self.buffer[:match.start()].strip()
                    if before_content:
                        plain_block = StreamingBlock(
                            block_type=BlockType.PLAIN_TEXT,
                            content=before_content,
                            is_complete=True,
                            start_position=self.position - len(self.buffer),
                            end_position=self.position - len(self.buffer) + match.start()
                        )
                        self.completed_blocks.append(plain_block)
                    
                    # Remover contenido procesado del buffer (incluyendo tag de apertura)
                    self.buffer = self.buffer[match.end():]
                    break
        
        # Crear nuevo bloque
        if block_type != BlockType.TOOL_CALL:
            tool_name = None
        
        self.current_block = StreamingBlock(
            block_type=block_type,
            content="",
            tool_name=tool_name,
            is_complete=False,
            start_position=self.position - len(self.buffer)
        )
        
        # Emitir bloque de inicio para thinking y answer (para mostrar encabezado)
        self.current_block_emitted_start = False
        
        self.logger.debug(f"Iniciado nuevo bloque: {block_type.value}" + 
                         (f" ({tool_name})" if tool_name else ""))
    
    def complete_current_block(self) -> Optional[StreamingBlock]:
        """
        Completa el bloque actual
        
        Returns:
            StreamingBlock completado o None
        """
        if self.current_block is None:
            return None
        
        block_type = self.current_block.block_type
        
        # Extraer contenido del bloque
        if block_type in self.block_patterns:
            _, end_pattern = self.block_patterns[block_type]
            match = re.search(end_pattern, self.buffer)
            if match:
                # Contenido del bloque (sin tags)
                content = self.buffer[:match.start()].strip()
                self.current_block.content = content
                self.current_block.is_complete = True
                self.current_block.end_position = self.position - len(self.buffer) + match.end()
                
                # Remover contenido procesado del buffer
                self.buffer = self.buffer[match.end():]
                
                completed = self.current_block
                self.current_block = None
                
                self.logger.debug(f"Bloque completado: {completed.block_type.value}, "
                                f"contenido: {len(completed.content)} caracteres")
                
                return completed
        
        # Para herramientas
        elif block_type == BlockType.TOOL_CALL and self.current_block.tool_name:
            tool_name = self.current_block.tool_name
            end_pattern = f'</{tool_name}>'
            if end_pattern in self.buffer:
                end_pos = self.buffer.find(end_pattern)
                # Contenido del bloque (incluyendo tags internos)
                content = self.buffer[:end_pos].strip()
                self.current_block.content = content
                self.current_block.is_complete = True
                self.current_block.end_position = self.position - len(self.buffer) + end_pos + len(end_pattern)
                
                # Remover contenido procesado del buffer
                self.buffer = self.buffer[end_pos + len(end_pattern):]
                
                completed = self.current_block
                self.current_block = None
                
                self.logger.debug(f"Herramienta completada: {tool_name}, "
                                f"contenido: {len(completed.content)} caracteres")
                
                return completed
        
        return None
    
    def extract_plain_text(self) -> Optional[StreamingBlock]:
        """
        Extrae texto plano del buffer cuando no hay bloques activos
        
        Returns:
            StreamingBlock con texto plano o None
        """
        if not self.buffer.strip():
            return None
        
        # Buscar si hay inicio de bloque próximo
        min_pos = len(self.buffer)
        for block_type, (start_pattern, _) in self.block_patterns.items():
            match = re.search(start_pattern, self.buffer)
            if match and match.start() < min_pos:
                min_pos = match.start()
        
        for tool_pattern in self.tool_patterns:
            match = re.search(tool_pattern, self.buffer)
            if match and match.start() < min_pos:
                min_pos = match.start()
        
        # Si hay un bloque próximo, extraer solo hasta ahí
        if min_pos < len(self.buffer):
            content = self.buffer[:min_pos].strip()
            self.buffer = self.buffer[min_pos:]
        else:
            # Extraer todo el buffer
            content = self.buffer.strip()
            self.buffer = ""
        
        if content:
            plain_block = StreamingBlock(
                block_type=BlockType.PLAIN_TEXT,
                content=content,
                is_complete=True,
                start_position=self.position - len(content),
                end_position=self.position
            )
            
            self.logger.debug(f"Texto plano extraído: {len(content)} caracteres")
            return plain_block
        
        return None
    
    def extract_tool_name(self, tool_pattern: str) -> str:
        """
        Extrae el nombre de la herramienta del patrón
        
        Args:
            tool_pattern: Patrón regex de la herramienta
            
        Returns:
            Nombre de la herramienta
        """
        # Remover < y > del patrón
        tool_name = tool_pattern.replace('<', '').replace('>', '')
        return tool_name
    
    def extract_tool_name_from_buffer(self) -> Optional[str]:
        """
        Extrae el nombre de la herramienta del buffer actual
        
        Returns:
            Nombre de la herramienta o None
        """
        for tool_pattern in self.tool_patterns:
            if re.search(tool_pattern, self.buffer):
                return self.extract_tool_name(tool_pattern)
        return None
    
    def get_remaining_content(self) -> str:
        """
        Obtiene el contenido restante en el buffer
        
        Returns:
            Contenido del buffer
        """
        return self.buffer
    
    def finalize(self) -> List[StreamingBlock]:
        """
        Finaliza el parsing y retorna bloques pendientes
        
        Returns:
            Lista de bloques pendientes
        """
        remaining = []
        
        # Si hay un bloque actual sin completar, marcarlo como incompleto
        if self.current_block is not None:
            self.current_block.content = self.buffer.strip()
            self.current_block.is_complete = False
            remaining.append(self.current_block)
            self.current_block = None
        
        # Si hay contenido en el buffer, extraerlo como texto plano
        elif self.buffer.strip():
            plain_block = StreamingBlock(
                block_type=BlockType.PLAIN_TEXT,
                content=self.buffer.strip(),
                is_complete=True,
                start_position=self.position - len(self.buffer),
                end_position=self.position
            )
            remaining.append(plain_block)
        
        self.buffer = ""
        
        self.logger.debug(f"Parser finalizado, {len(remaining)} bloques pendientes")
        return remaining


def main():
    """Función principal para testing"""
    import logging
    
    # Configurar logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear parser
    parser = StreamingResponseParser()
    
    # Simular stream de tokens
    response = """
    <thinking>
    Voy a buscar información sobre autenticación.
    </thinking>
    
    <tool_semantic_search>
    <query>autenticación usuarios</query>
    <top_k>5</top_k>
    </tool_semantic_search>
    
    <present_answer>
    La autenticación se gestiona en el archivo auth.js
    </present_answer>
    """
    
    # Simular tokens
    tokens = [response[i:i+10] for i in range(0, len(response), 10)]
    
    print("Procesando tokens...")
    all_blocks = []
    
    for i, token in enumerate(tokens):
        print(f"\nToken {i+1}: {repr(token)}")
        blocks = parser.feed_token(token)
        
        for block in blocks:
            print(f"  → Bloque detectado: {block.block_type.value}")
            if block.tool_name:
                print(f"     Herramienta: {block.tool_name}")
            print(f"     Contenido: {block.content[:50]}...")
            all_blocks.append(block)
    
    # Finalizar
    remaining = parser.finalize()
    all_blocks.extend(remaining)
    
    print(f"\n\nTotal de bloques detectados: {len(all_blocks)}")
    for i, block in enumerate(all_blocks, 1):
        print(f"{i}. {block.block_type.value}" + 
              (f" ({block.tool_name})" if block.tool_name else ""))


if __name__ == "__main__":
    main()
