"""
Simple Streaming Handler - Manejo simplificado de streaming basado en el patrón de Cline

Responsabilidad: Acumular texto del stream y parsear al final
- Acumula tokens en tiempo real
- Muestra texto inmediatamente (sin parsear)
- Parsea mensaje completo al finalizar el stream
- Ejecuta herramientas detectadas después del parsing
"""

import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from tool_executor import ToolExecutor, ToolResult, ToolType
from streaming_display import StreamingDisplay


class BlockType(Enum):
    """Tipos de bloques en la respuesta del LLM"""
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    PRESENT_ANSWER = "present_answer"
    PLAIN_TEXT = "plain_text"


@dataclass
class ParsedBlock:
    """Bloque parseado del mensaje del asistente"""
    type: BlockType
    content: str
    tool_name: Optional[str] = None
    tool_params: Optional[Dict[str, Any]] = None
    start_pos: int = 0
    end_pos: int = 0


class SimpleStreamingHandler:
    """
    Manejador simplificado de streaming siguiendo el patrón de Cline:
    1. Acumular texto del stream
    2. Mostrar en tiempo real (sin parsear)
    3. Parsear mensaje completo al final
    4. Ejecutar herramientas detectadas
    """
    
    def __init__(self, tool_executor: ToolExecutor, display: StreamingDisplay):
        """
        Inicializa el manejador
        
        Args:
            tool_executor: Ejecutor de herramientas
            display: Display para visualización
        """
        self.tool_executor = tool_executor
        self.display = display
        self.logger = logging.getLogger(__name__)
        
        # Acumulador de texto
        self.accumulated_text = ""
        
        # Resultados
        self.parsed_blocks: List[ParsedBlock] = []
        self.tool_results: List[ToolResult] = []
        
        # Estado
        self.is_finalized = False
        self._inside_tool_block = False
        self._tool_open_tags = 0
        self._tool_close_tags = 0
        
        # Estado para bloques <thinking>
        self._inside_thinking_block = False
        self._thinking_buffer = ""
        
        # Estado para bloques <present_answer>
        self._inside_answer_block = False
        self._answer_buffer = ""
        
        # Estado para bloques de metadatos (sources, confidence, suggestions, etc.)
        self._inside_metadata_block = False
        self._metadata_buffer = ""
        self._metadata_type = None
        
        self._pending_buffer = ""  # Buffer para tokens pendientes de mostrar
    
    def feed_token(self, token: str) -> None:
        """
        Alimenta un token al handler
        
        Args:
            token: Token recibido del stream
        """
        # Acumular
        self.accumulated_text += token
        
        # Actualizar estado de herramientas
        self._update_tool_state(token)
        
        # Procesar token según el estado actual
        if self._inside_thinking_block:
            # Dentro de <thinking>: mostrar contenido en streaming
            self._thinking_buffer += token
            
            # Detectar si acabamos de cerrar el tag
            if '</thinking>' in token:
                # Extraer solo el contenido antes del tag de cierre
                before_close = token.split('</thinking>')[0]
                if before_close:
                    self.display.stream_thinking(before_close)
                self._thinking_buffer = ""
                self._inside_thinking_block = False
            else:
                # Mostrar el token actual (contenido del thinking)
                self.display.stream_thinking(token)
        elif self._inside_answer_block:
            # Dentro de <present_answer>: mostrar contenido en streaming
            self._answer_buffer += token
            
            # Detectar si acabamos de cerrar el tag
            if '</present_answer>' in token:
                # Extraer solo el contenido antes del tag de cierre
                before_close = token.split('</present_answer>')[0]
                if before_close:
                    self.display.stream_answer(before_close)
                self._answer_buffer = ""
                self._inside_answer_block = False
            else:
                # Mostrar el token actual (contenido de la respuesta)
                self.display.stream_answer(token)
        elif self._inside_metadata_block:
            # Dentro de bloque de metadatos: NO mostrar nada, solo acumular
            self._metadata_buffer += token
            
            # Detectar si acabamos de cerrar algún tag de metadatos
            closing_tags = ['</answer>', '</sources>', '</confidence>', '</suggestions>']
            for closing_tag in closing_tags:
                if closing_tag in token:
                    self._metadata_buffer = ""
                    self._inside_metadata_block = False
                    break
        elif self._inside_tool_block:
            # Dentro de herramienta: no mostrar nada
            pass
        else:
            # Fuera de bloques especiales
            self._pending_buffer += token
            
            # Verificar si estamos empezando un bloque <thinking>
            if '<thinking>' in self._pending_buffer:
                # Mostrar todo lo que había antes del tag
                before_tag = self._pending_buffer.split('<thinking>')[0]
                if before_tag:
                    self.display.stream_plain_text(before_tag)
                
                # Iniciar bloque thinking
                self._inside_thinking_block = True
                self._thinking_buffer = '<thinking>'
                
                # Mostrar el contenido después del tag de apertura
                after_tag = self._pending_buffer.split('<thinking>', 1)[1]
                if after_tag:
                    self.display.stream_thinking(after_tag)
                    self._thinking_buffer += after_tag
                
                self._pending_buffer = ""
            # Verificar si estamos empezando un bloque <present_answer>
            elif '<present_answer>' in self._pending_buffer:
                # Mostrar todo lo que había antes del tag
                before_tag = self._pending_buffer.split('<present_answer>')[0]
                if before_tag:
                    self.display.stream_plain_text(before_tag)
                
                # Iniciar bloque answer
                self._inside_answer_block = True
                self._answer_buffer = '<present_answer>'
                
                # Mostrar el contenido después del tag de apertura
                after_tag = self._pending_buffer.split('<present_answer>', 1)[1]
                if after_tag:
                    self.display.stream_answer(after_tag)
                    self._answer_buffer += after_tag
                
                self._pending_buffer = ""
            # Verificar si estamos empezando un bloque de metadatos (answer, sources, confidence, suggestions)
            elif self._is_metadata_tag():
                # No mostrar nada, solo acumular en el buffer de metadatos
                self._inside_metadata_block = True
                # El tipo de metadato se detectará en _is_metadata_tag()
                self._pending_buffer = ""
            # Verificar si estamos empezando un bloque de herramienta (detección temprana y agresiva)
            elif self._is_potential_tool_block():
                # Si detectamos un tag completo de herramienta, procesarlo
                if '<tool_' in self._pending_buffer:
                    # Encontrar el inicio del tag de herramienta
                    tool_start = self._pending_buffer.find('<tool_')
                    
                    if tool_start != -1:
                        # Extraer texto antes del tag
                        before_tag = self._pending_buffer[:tool_start]
                        
                        # Eliminar "xml" o "```" del final si están presentes
                        before_tag_clean = before_tag.rstrip()
                        if before_tag_clean.endswith('xml'):
                            before_tag_clean = before_tag_clean[:-3].rstrip()
                        elif before_tag_clean.endswith('```'):
                            before_tag_clean = before_tag_clean[:-3].rstrip()
                        
                        # Mostrar solo el texto limpio antes del tag
                        if before_tag_clean:
                            self.display.stream_plain_text(before_tag_clean)
                        
                        # NO mostrar nada más, el bloque de herramienta se procesará al final
                        self._pending_buffer = ""
                # Si solo detectamos fragmentos sospechosos, esperar más tokens
                # (no hacer nada, mantener en buffer)
            elif '<' in self._pending_buffer and len(self._pending_buffer) < 100:
                # Podría ser el inicio de un tag, esperar más tokens (aumentado de 30 a 100)
                pass
            else:
                # No es un tag especial, mostrar el buffer
                self.display.stream_plain_text(self._pending_buffer)
                self._pending_buffer = ""
    
    def _is_metadata_tag(self) -> bool:
        """
        Detecta si el buffer contiene un tag de metadatos
        
        Returns:
            True si hay un tag de metadatos
        """
        buffer = self._pending_buffer
        
        # Tags de metadatos que queremos ocultar
        metadata_tags = ['<answer>', '<sources>', '<confidence>', '<suggestions>']
        
        for tag in metadata_tags:
            if tag in buffer:
                return True
        
        # Detección de fragmentos parciales (similar a herramientas)
        # El LLM puede escribir "nswer>" o "ources>" antes del tag completo
        metadata_fragments = [
            'nswer>',      # de answer
            'ources>',     # de sources
            'onfidence>',  # de confidence
            'uggestions>', # de suggestions
            'nswer',       # sin >
            'ources',      # sin >
            'onfidence',   # sin >
            'uggestions',  # sin >
        ]
        
        for fragment in metadata_fragments:
            if fragment in buffer:
                return True
        
        # Si el buffer termina con algo que podría ser el inicio de un tag de metadatos
        if '<' in buffer:
            after_bracket = buffer.split('<')[-1]
            
            # Verificar si comienza con inicios de tags de metadatos
            suspicious_starts = [
                'a',    # answer
                'an',   # answer
                'ans',  # answer
                's',    # sources o suggestions
                'so',   # sources
                'sou',  # sources
                'su',   # suggestions
                'sug',  # suggestions
                'c',    # confidence
                'co',   # confidence
                'con',  # confidence
            ]
            
            for start in suspicious_starts:
                if after_bracket.startswith(start) and len(after_bracket) <= 12:
                    return True
        
        return False
    
    def _is_potential_tool_block(self) -> bool:
        """
        Detecta si el buffer contiene indicios de un bloque de herramienta
        
        Esta función es más agresiva y detecta fragmentos parciales que podrían
        ser parte de un tag de herramienta, para evitar mostrar XML al usuario.
        
        Returns:
            True si hay indicios de un bloque de herramienta
        """
        buffer = self._pending_buffer
        
        # Detección de tags completos
        if '<tool_' in buffer:
            return True
        
        # Detección de fragmentos de nombres de herramientas (sin el prefijo <tool_)
        # Estos aparecen cuando el LLM escribe "ical_search>" antes del tag completo
        tool_fragments = [
            'emantic_search>',  # de semantic_search
            'ical_search>',     # de lexical_search
            'egex_search>',     # de regex_search
            'et_file_content>', # de get_file_content
            'emantic_search',   # sin >
            'ical_search',      # sin >
            'egex_search',      # sin >
            'et_file_content',  # sin >
        ]
        
        for fragment in tool_fragments:
            if fragment in buffer:
                return True
        
        # Si el buffer termina con algo que podría ser el inicio de un nombre de herramienta
        # y hay un '<' antes, es sospechoso
        if '<' in buffer:
            # Extraer lo que viene después del último '<'
            after_bracket = buffer.split('<')[-1]
            
            # Verificar si comienza con 'tool' o fragmentos de nombres de herramientas
            suspicious_starts = [
                'tool',
                'tool_',
                'tool_s',  # semantic
                'tool_l',  # lexical
                'tool_r',  # regex
                'tool_g',  # get_file
            ]
            
            for start in suspicious_starts:
                if after_bracket.startswith(start):
                    return True
        
        return False
    
    def _update_tool_state(self, token: str) -> None:
        """
        Actualiza el estado de si estamos dentro de un bloque de herramienta
        
        Args:
            token: Token actual
        """
        # Detectar tags de apertura de herramientas
        if '<tool_' in token:
            self._tool_open_tags += token.count('<tool_')
            self._inside_tool_block = True
        
        # Detectar tags de cierre de herramientas
        if '</tool_' in token:
            self._tool_close_tags += token.count('</tool_')
            # Si se cierran todas las herramientas abiertas, salimos del bloque
            if self._tool_close_tags >= self._tool_open_tags:
                self._inside_tool_block = False
    
    
    def finalize(self) -> Dict[str, Any]:
        """
        Finaliza el stream y parsea el mensaje completo
        
        Returns:
            Diccionario con estado final
        """
        if self.is_finalized:
            return self._get_state()
        
        self.logger.info("🔍 Finalizando stream y parseando mensaje completo...")
        
        # Parsear mensaje completo
        self.parsed_blocks = self._parse_complete_message(self.accumulated_text)
        
        # Ejecutar herramientas detectadas
        for block in self.parsed_blocks:
            if block.type == BlockType.TOOL_CALL:
                self._execute_tool(block)
        
        self.is_finalized = True
        
        return self._get_state()
    
    def _parse_complete_message(self, message: str) -> List[ParsedBlock]:
        """
        Parsea el mensaje completo para extraer bloques
        
        Args:
            message: Mensaje completo acumulado
            
        Returns:
            Lista de bloques parseados
        """
        blocks = []
        
        # Patrón para bloques <thinking>
        thinking_pattern = r'<thinking>(.*?)</thinking>'
        for match in re.finditer(thinking_pattern, message, re.DOTALL):
            blocks.append(ParsedBlock(
                type=BlockType.THINKING,
                content=match.group(1).strip(),
                start_pos=match.start(),
                end_pos=match.end()
            ))
        
        # Patrón para bloques <present_answer>
        answer_pattern = r'<present_answer>(.*?)</present_answer>'
        for match in re.finditer(answer_pattern, message, re.DOTALL):
            blocks.append(ParsedBlock(
                type=BlockType.PRESENT_ANSWER,
                content=match.group(1).strip(),
                start_pos=match.start(),
                end_pos=match.end()
            ))
        
        # Patrón para herramientas
        tool_pattern = r'<tool_(semantic_search|lexical_search|regex_search|get_file_content)>(.*?)</tool_\1>'
        for match in re.finditer(tool_pattern, message, re.DOTALL):
            tool_name = match.group(1)
            tool_content = match.group(2).strip()
            
            # Parsear parámetros de la herramienta
            params = self._parse_tool_params(tool_content)
            
            blocks.append(ParsedBlock(
                type=BlockType.TOOL_CALL,
                content=tool_content,
                tool_name=tool_name,
                tool_params=params,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        
        # Ordenar bloques por posición
        blocks.sort(key=lambda b: b.start_pos)
        
        self.logger.info(f"✅ Parseados {len(blocks)} bloques del mensaje")
        
        return blocks
    
    def _parse_tool_params(self, tool_content: str) -> Dict[str, Any]:
        """
        Parsea los parámetros de una herramienta desde su contenido XML
        
        Args:
            tool_content: Contenido XML de la herramienta
            
        Returns:
            Diccionario con parámetros parseados y convertidos a tipos apropiados
        """
        params = {}
        
        # Patrón para extraer parámetros XML
        param_pattern = r'<(\w+)>(.*?)</\1>'
        for match in re.finditer(param_pattern, tool_content, re.DOTALL):
            param_name = match.group(1)
            param_value = match.group(2).strip()
            
            # Convertir a tipo apropiado
            params[param_name] = self._convert_param_type(param_name, param_value)
        
        return params
    
    def _convert_param_type(self, param_name: str, param_value: str) -> Any:
        """
        Convierte el valor del parámetro al tipo apropiado
        
        Args:
            param_name: Nombre del parámetro
            param_value: Valor como string
            
        Returns:
            Valor convertido al tipo apropiado
        """
        # Parámetros que deben ser int
        int_params = ['top_k', 'max_results', 'max_matches_per_file', 'context_lines']
        
        # Parámetros que deben ser float
        float_params = ['min_score', 'threshold']
        
        # Parámetros que deben ser bool
        bool_params = ['case_sensitive', 'include_metadata', 'recursive']
        
        # Parámetros que deben ser list
        list_params = ['fields', 'file_types']
        
        try:
            if param_name in int_params:
                return int(param_value)
            elif param_name in float_params:
                return float(param_value)
            elif param_name in bool_params:
                return param_value.lower() in ('true', '1', 'yes')
            elif param_name in list_params:
                # Si es una lista en formato JSON
                if param_value.startswith('['):
                    import json
                    return json.loads(param_value)
                # Si es una lista separada por comas
                elif ',' in param_value:
                    return [item.strip() for item in param_value.split(',')]
                # Si es un solo valor, convertir a lista
                else:
                    return [param_value]
            else:
                # Mantener como string
                return param_value
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Error convirtiendo parámetro {param_name}={param_value}: {e}")
            # Si falla la conversión, devolver como string
            return param_value
    
    def _execute_tool(self, block: ParsedBlock) -> None:
        """
        Ejecuta una herramienta detectada
        
        Args:
            block: Bloque de herramienta a ejecutar
        """
        if not block.tool_name or not block.tool_params:
            self.logger.warning(f"⚠️  Bloque de herramienta sin nombre o parámetros")
            return
        
        # Convertir nombre de herramienta a ToolType
        tool_type_map = {
            'semantic_search': ToolType.SEMANTIC_SEARCH,
            'lexical_search': ToolType.LEXICAL_SEARCH,
            'regex_search': ToolType.REGEX_SEARCH,
            'get_file_content': ToolType.GET_FILE_CONTENT
        }
        
        tool_type = tool_type_map.get(block.tool_name)
        if not tool_type:
            self.logger.warning(f"⚠️  Tipo de herramienta desconocido: {block.tool_name}")
            return
        
        # Mostrar indicador de ejecución con parámetros
        self.display.show_tool_indicator(block.tool_name, block.tool_params)
        
        # Ejecutar herramienta
        result = self.tool_executor.execute_tool(
            tool_type=tool_type,
            params=block.tool_params
        )
        
        # Guardar resultado
        self.tool_results.append(result)
        
        # Mostrar resultado
        self.display.show_tool_result(block.tool_name, result)
    
    def get_tool_results(self) -> List[ToolResult]:
        """
        Obtiene los resultados de las herramientas ejecutadas
        
        Returns:
            Lista de resultados de herramientas
        """
        return self.tool_results
    
    def _get_state(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del handler
        
        Returns:
            Diccionario con estado
        """
        return {
            'is_finalized': self.is_finalized,
            'accumulated_length': len(self.accumulated_text),
            'blocks_parsed': len(self.parsed_blocks),
            'tools_executed': len(self.tool_results),
            'tools_successful': sum(1 for r in self.tool_results if r.success)
        }


def main():
    """Función principal para testing"""
    import logging
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear componentes
    from config_manager import ConfigManager
    config = ConfigManager()
    tool_executor = ToolExecutor(config_path="config/config.yaml")
    display = StreamingDisplay(enable_colors=True)
    
    # Crear handler
    handler = SimpleStreamingHandler(tool_executor, display)
    
    # Simular stream
    test_message = """<thinking>
Necesito buscar información sobre Darwin.
</thinking>

<tool_semantic_search>
<query>módulos principales de Darwin</query>
<top_k>5</top_k>
</tool_semantic_search>

<present_answer>
Aquí está la información sobre Darwin...
</present_answer>"""
    
    # Alimentar tokens
    for token in test_message:
        handler.feed_token(token)
    
    # Finalizar
    state = handler.finalize()
    print(f"\nEstado final: {state}")


if __name__ == "__main__":
    main()
