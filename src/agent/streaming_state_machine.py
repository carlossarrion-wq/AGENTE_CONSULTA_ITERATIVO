"""
Streaming State Machine - Máquina de estados robusta para streaming

Responsabilidad: Gestionar el streaming de tokens con certeza absoluta
- Máquina de estados determinista
- Acumula tokens hasta tener certeza
- Libera contenido solo cuando está seguro
- No depende de heurísticas frágiles
"""

import logging
from typing import Optional, Dict, List
from enum import Enum

from streaming_display import StreamingDisplay


class StreamState(Enum):
    """Estados posibles de la máquina de streaming"""
    NEUTRAL = "neutral"
    IN_THINKING = "in_thinking"
    IN_ANSWER = "in_answer"
    IN_TOOL = "in_tool"
    IN_METADATA = "in_metadata"


class StreamingStateMachine:
    """
    Máquina de estados para streaming robusto
    
    Principio: "Acumular tokens hasta tener certeza absoluta de qué hacer con ellos"
    """
    
    def __init__(self, display: StreamingDisplay):
        """
        Inicializa la máquina de estados
        
        Args:
            display: Display para visualización
        """
        self.display = display
        self.logger = logging.getLogger(__name__)
        
        # Estado actual
        self.state = StreamState.NEUTRAL
        
        # Buffer de acumulación
        self.buffer = ""
        
        # Buffer para preprocesamiento de saltos de línea
        self._newline_buffer = ""
        
        # Configuración de tags de apertura
        self.opening_tags: Dict[str, StreamState] = {
            '<thinking>': StreamState.IN_THINKING,
            '<present_answer>': StreamState.IN_ANSWER,
            '<tool_semantic_search>': StreamState.IN_TOOL,
            '<tool_lexical_search>': StreamState.IN_TOOL,
            '<tool_regex_search>': StreamState.IN_TOOL,
            '<tool_get_file_content>': StreamState.IN_TOOL,
            '<tool_get_file_section>': StreamState.IN_TOOL,
            '<tool_web_crawler>': StreamState.IN_TOOL,
            '<answer>': StreamState.IN_METADATA,
            '<sources>': StreamState.IN_METADATA,
            '<confidence>': StreamState.IN_METADATA,
            '<suggestions>': StreamState.IN_METADATA,
        }
        
        # Configuración de tags de cierre por estado
        self.closing_tags: Dict[StreamState, List[str]] = {
            StreamState.IN_THINKING: ['</thinking>'],
            StreamState.IN_ANSWER: ['</present_answer>'],
            StreamState.IN_TOOL: [
                '</tool_semantic_search>',
                '</tool_lexical_search>',
                '</tool_regex_search>',
                '</tool_get_file_content>',
                '</tool_get_file_section>',
                '</tool_web_crawler>'
            ],
            StreamState.IN_METADATA: [
                '</answer>',
                '</sources>',
                '</confidence>',
                '</suggestions>'
            ],
        }
        
        # Tamaño mínimo del buffer antes de liberar en estado NEUTRAL
        self.min_buffer_size = 50
        
        # Acumulador completo para parsing final
        self.accumulated_text = ""
        
        # Tracking de herramientas para mostrar indicador
        self.current_tool_name: Optional[str] = None
        
        self.logger.info("StreamingStateMachine inicializada")
    
    def feed_token(self, token: str) -> None:
        """
        Alimenta un token a la máquina de estados
        
        Args:
            token: Token recibido del stream
        """
        # Preprocesar token para eliminar saltos de línea consecutivos
        token = self._preprocess_token(token)
        
        # Acumular en buffer y en texto completo
        self.buffer += token
        self.accumulated_text += token
        
        # Procesar según el estado actual
        if self.state == StreamState.NEUTRAL:
            self._process_neutral_state()
        elif self.state == StreamState.IN_THINKING:
            self._process_thinking_state()
        elif self.state == StreamState.IN_ANSWER:
            self._process_answer_state()
        elif self.state == StreamState.IN_TOOL:
            self._process_tool_state()
        elif self.state == StreamState.IN_METADATA:
            self._process_metadata_state()
    
    def _process_neutral_state(self) -> None:
        """
        Procesa tokens en estado NEUTRAL
        
        Busca tags de apertura y libera texto plano cuando está seguro
        """
        # Buscar tags de apertura (ordenados por longitud para evitar matches parciales)
        sorted_tags = sorted(self.opening_tags.items(), key=lambda x: len(x[0]), reverse=True)
        
        for tag, next_state in sorted_tags:
            if tag in self.buffer:
                # Encontrado tag completo
                before_tag = self.buffer.split(tag)[0]
                after_tag = self.buffer.split(tag, 1)[1]
                
                # Limpiar marcadores de código markdown antes del tag
                before_tag_clean = before_tag.rstrip()
                if before_tag_clean.endswith('```xml'):
                    before_tag_clean = before_tag_clean[:-6].rstrip()
                elif before_tag_clean.endswith('```'):
                    before_tag_clean = before_tag_clean[:-3].rstrip()
                elif before_tag_clean.endswith('xml'):
                    before_tag_clean = before_tag_clean[:-3].rstrip()
                
                # Liberar texto antes del tag (si hay)
                if before_tag_clean.strip():
                    self.display.stream_plain_text(before_tag_clean)
                
                # Cambiar de estado
                old_state = self.state
                self.state = next_state
                self.buffer = after_tag
                
                self.logger.debug(f"Transición: {old_state.value} → {next_state.value} (tag: {tag})")
                
                # Guardar nombre de herramienta para cuando el bloque esté completo
                if next_state == StreamState.IN_TOOL:
                    # Extraer nombre de herramienta del tag
                    self.current_tool_name = tag.replace('<tool_', '').replace('>', '')
                    # NO mostramos el indicador aquí, esperamos a tener los parámetros
                
                # Procesar inmediatamente el nuevo estado
                self.feed_token("")
                return
        
        # No se encontró ningún tag completo
        # Si el buffer contiene '<', podría ser inicio de tag
        if '<' in self.buffer:
            # Si el buffer es muy grande y aún no encontramos tag, liberar parte
            if len(self.buffer) > self.min_buffer_size:
                # Liberar todo hasta el último '<'
                last_bracket = self.buffer.rfind('<')
                to_release = self.buffer[:last_bracket]
                self.buffer = self.buffer[last_bracket:]
                
                # Limpiar marcadores de código markdown del texto a liberar
                to_release_clean = to_release.rstrip()
                if to_release_clean.endswith('```xml'):
                    to_release_clean = to_release_clean[:-6].rstrip()
                elif to_release_clean.endswith('```'):
                    to_release_clean = to_release_clean[:-3].rstrip()
                elif to_release_clean.endswith('xml'):
                    to_release_clean = to_release_clean[:-3].rstrip()
                
                if to_release_clean.strip():
                    self.display.stream_plain_text(to_release_clean)
                    self.logger.debug(f"Liberado texto plano (buffer grande): {len(to_release_clean)} chars")
        else:
            # No hay '<', liberar todo el buffer
            if self.buffer.strip():
                # Limpiar marcadores de código markdown
                buffer_clean = self.buffer.rstrip()
                if buffer_clean.endswith('```xml'):
                    buffer_clean = buffer_clean[:-6].rstrip()
                elif buffer_clean.endswith('```'):
                    buffer_clean = buffer_clean[:-3].rstrip()
                elif buffer_clean.endswith('xml'):
                    buffer_clean = buffer_clean[:-3].rstrip()
                
                if buffer_clean.strip():
                    self.display.stream_plain_text(buffer_clean)
                    self.logger.debug(f"Liberado texto plano: {len(buffer_clean)} chars")
            self.buffer = ""
    
    def _process_thinking_state(self) -> None:
        """
        Procesa tokens en estado IN_THINKING
        
        Libera tokens en amarillo hasta encontrar </thinking>
        """
        closing_tags = self.closing_tags[StreamState.IN_THINKING]
        
        for closing_tag in closing_tags:
            if closing_tag in self.buffer:
                # Encontrado tag de cierre
                before_close = self.buffer.split(closing_tag)[0]
                after_close = self.buffer.split(closing_tag, 1)[1]
                
                # Liberar contenido antes del cierre
                if before_close:
                    self.display.stream_thinking(before_close)
                    self.logger.debug(f"Liberado thinking: {len(before_close)} chars")
                
                # Volver a estado NEUTRAL
                old_state = self.state
                self.state = StreamState.NEUTRAL
                self.buffer = after_close
                
                self.logger.debug(f"Transición: {old_state.value} → NEUTRAL (tag: {closing_tag})")
                
                # Procesar inmediatamente el nuevo estado
                if self.buffer:
                    self.feed_token("")
                return
        
        # No hay tag de cierre aún
        # Liberar todo el buffer excepto los últimos caracteres (por si el tag está partido)
        if len(self.buffer) > 15:  # Longitud de "</thinking>"
            to_release = self.buffer[:-15]
            self.buffer = self.buffer[-15:]
            
            if to_release:
                self.display.stream_thinking(to_release)
                self.logger.debug(f"Liberado thinking parcial: {len(to_release)} chars")
    
    def _process_answer_state(self) -> None:
        """
        Procesa tokens en estado IN_ANSWER
        
        Libera tokens en verde hasta encontrar </present_answer>
        """
        closing_tags = self.closing_tags[StreamState.IN_ANSWER]
        
        for closing_tag in closing_tags:
            if closing_tag in self.buffer:
                # Encontrado tag de cierre
                before_close = self.buffer.split(closing_tag)[0]
                after_close = self.buffer.split(closing_tag, 1)[1]
                
                # Liberar contenido antes del cierre
                if before_close:
                    self.display.stream_answer(before_close)
                    self.logger.debug(f"Liberado answer: {len(before_close)} chars")
                
                # Volver a estado NEUTRAL
                old_state = self.state
                self.state = StreamState.NEUTRAL
                self.buffer = after_close
                
                self.logger.debug(f"Transición: {old_state.value} → NEUTRAL (tag: {closing_tag})")
                
                # Procesar inmediatamente el nuevo estado
                if self.buffer:
                    self.feed_token("")
                return
        
        # No hay tag de cierre aún
        # Liberar todo el buffer excepto los últimos caracteres (por si el tag está partido)
        if len(self.buffer) > 20:  # Longitud de "</present_answer>"
            to_release = self.buffer[:-20]
            self.buffer = self.buffer[-20:]
            
            if to_release:
                self.display.stream_answer(to_release)
                self.logger.debug(f"Liberado answer parcial: {len(to_release)} chars")
    
    def _process_tool_state(self) -> None:
        """
        Procesa tokens en estado IN_TOOL
        
        NO libera tokens, solo acumula hasta encontrar tag de cierre
        """
        closing_tags = self.closing_tags[StreamState.IN_TOOL]
        
        for closing_tag in closing_tags:
            if closing_tag in self.buffer:
                # Encontrado tag de cierre - parsear parámetros del XML
                tool_content = self.buffer.split(closing_tag)[0]
                after_close = self.buffer.split(closing_tag, 1)[1]
                
                # Parsear parámetros del XML de la herramienta
                params = self._parse_tool_params(tool_content)
                
                # Actualizar el indicador con los parámetros
                if self.current_tool_name and params:
                    self.display.show_tool_indicator(self.current_tool_name, params)
                
                self.logger.debug(f"Tool block completo: {self.current_tool_name} con {len(params)} parámetros")
                
                # Volver a estado NEUTRAL
                old_state = self.state
                self.state = StreamState.NEUTRAL
                self.buffer = after_close
                self.current_tool_name = None
                
                self.logger.debug(f"Transición: {old_state.value} → NEUTRAL (tag: {closing_tag})")
                
                # Procesar inmediatamente el nuevo estado
                if self.buffer:
                    self.feed_token("")
                return
        
        # No hacer nada, solo acumular
        # No liberamos nada en este estado
    
    def _parse_tool_params(self, xml_content: str) -> Dict[str, str]:
        """
        Parsea los parámetros del XML de una herramienta
        
        Args:
            xml_content: Contenido XML de la herramienta (sin tags de apertura/cierre)
            
        Returns:
            Diccionario con los parámetros parseados
        """
        import re
        params = {}
        
        # Buscar todos los tags de parámetros en el XML
        # Patrón: <nombre_param>valor</nombre_param>
        param_pattern = r'<(\w+)>(.*?)</\1>'
        matches = re.findall(param_pattern, xml_content, re.DOTALL)
        
        for param_name, param_value in matches:
            # Limpiar el valor (quitar espacios en blanco al inicio/final)
            params[param_name] = param_value.strip()
        
        return params
    
    def _process_metadata_state(self) -> None:
        """
        Procesa tokens en estado IN_METADATA
        
        NO libera tokens, solo acumula hasta encontrar tag de cierre
        """
        closing_tags = self.closing_tags[StreamState.IN_METADATA]
        
        for closing_tag in closing_tags:
            if closing_tag in self.buffer:
                # Encontrado tag de cierre
                after_close = self.buffer.split(closing_tag, 1)[1]
                
                self.logger.debug(f"Metadata block completo")
                
                # Volver a estado NEUTRAL
                old_state = self.state
                self.state = StreamState.NEUTRAL
                self.buffer = after_close
                
                self.logger.debug(f"Transición: {old_state.value} → NEUTRAL (tag: {closing_tag})")
                
                # Procesar inmediatamente el nuevo estado
                if self.buffer:
                    self.feed_token("")
                return
        
        # No hacer nada, solo acumular
        # No liberamos nada en este estado
    
    def finalize(self) -> str:
        """
        Finaliza el streaming y libera cualquier contenido pendiente
        
        Returns:
            Texto completo acumulado
        """
        # Si hay algo en el buffer y estamos en estado NEUTRAL, liberarlo
        if self.state == StreamState.NEUTRAL and self.buffer.strip():
            self.display.stream_plain_text(self.buffer)
            self.logger.debug(f"Liberado buffer final: {len(self.buffer)} chars")
        
        # Finalizar display
        self.display.finalize()
        
        self.logger.info(f"Streaming finalizado. Total acumulado: {len(self.accumulated_text)} chars")
        
        return self.accumulated_text
    
    def get_accumulated_text(self) -> str:
        """
        Obtiene el texto completo acumulado
        
        Returns:
            Texto completo
        """
        return self.accumulated_text
    
    def get_current_state(self) -> StreamState:
        """
        Obtiene el estado actual de la máquina
        
        Returns:
            Estado actual
        """
        return self.state
    
    def get_buffer_size(self) -> int:
        """
        Obtiene el tamaño actual del buffer
        
        Returns:
            Tamaño del buffer en caracteres
        """
        return len(self.buffer)
    
    def _preprocess_token(self, token: str) -> str:
        """
        Preprocesa un token para eliminar saltos de línea consecutivos
        
        Estrategia: Acumula caracteres en un buffer temporal y solo libera
        cuando está seguro de que no hay más saltos de línea consecutivos.
        
        Convierte secuencias de \n\n (o más) en un solo \n
        
        Args:
            token: Token recibido del stream
            
        Returns:
            Token procesado (puede ser vacío si aún está acumulando)
        """
        processed = ""
        
        for char in token:
            if char == '\n':
                # Acumular newlines
                self._newline_buffer += char
            else:
                # Carácter no-newline: procesar buffer de newlines acumulado
                if self._newline_buffer:
                    # Contar cuántos \n hay acumulados
                    newline_count = len(self._newline_buffer)
                    
                    if newline_count >= 2:
                        # Dos o más \n consecutivos -> reducir a uno solo
                        processed += '\n'
                    elif newline_count == 1:
                        # Un solo \n -> mantenerlo
                        processed += '\n'
                    
                    # Limpiar buffer
                    self._newline_buffer = ""
                
                # Agregar el carácter no-newline
                processed += char
        
        return processed


def main():
    """Función principal para testing"""
    import logging
    
    # Configurar logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear display
    display = StreamingDisplay(enable_colors=True)
    
    # Crear máquina de estados
    machine = StreamingStateMachine(display)
    
    # Simular stream con formato correcto según system prompt
    test_message = """Voy a buscar información.

<thinking>
Necesito buscar sobre Darwin.
</thinking>

<tool_semantic_search>
<query>módulos principales de Darwin</query>
<top_k>5</top_k>
</tool_semantic_search>

<present_answer>
Aquí está la información sobre Darwin...
</present_answer>

<answer>
Resumen de la información sobre Darwin
</answer>

<sources>
["doc1.txt", "doc2.txt"]
</sources>

<confidence>high</confidence>

<suggestions>["Más info sobre X", "Consulta Y"]</suggestions>"""
    
    print("=" * 64)
    print("DEMO DE STREAMING STATE MACHINE")
    print("=" * 64)
    
    # Alimentar tokens uno por uno
    for char in test_message:
        machine.feed_token(char)
    
    # Finalizar
    accumulated = machine.finalize()
    
    print("\n" + "=" * 64)
    print(f"Total acumulado: {len(accumulated)} caracteres")
    print("=" * 64)


if __name__ == "__main__":
    main()
