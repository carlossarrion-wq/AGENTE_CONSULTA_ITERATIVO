"""
Response Formatter - Formateo de respuestas para presentación

Responsabilidad: Formatear respuestas del LLM para presentación
- Formateo de respuestas estáticas
- Integración de resultados de herramientas
- Filtrado de contenido técnico (XML)
- Preparación para streaming futuro
"""

import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ResponseFormat(Enum):
    """Formatos de respuesta disponibles"""
    STATIC = "static"
    STREAMING = "streaming"
    JSON = "json"
    MARKDOWN = "markdown"


@dataclass
class FormattedResponse:
    """Respuesta formateada para presentación"""
    content: str
    format_type: ResponseFormat
    has_tool_calls: bool
    tool_calls_count: int
    filtered_content: str
    metadata: Dict[str, Any]
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class ResponseFormatter:
    """Formateador de respuestas del LLM"""
    
    def __init__(self):
        """Inicializa el formateador de respuestas"""
        self.logger = logging.getLogger(__name__)
        
        # Patrones de herramientas a filtrar
        self.tool_patterns = {
            'tool_semantic_search': r'<tool_semantic_search>.*?</tool_semantic_search>',
            'tool_lexical_search': r'<tool_lexical_search>.*?</tool_lexical_search>',
            'tool_regex_search': r'<tool_regex_search>.*?</tool_regex_search>',
            'tool_get_file_content': r'<tool_get_file_content>.*?</tool_get_file_content>',
            'tool_web_crawler': r'<tool_web_crawler>.*?</tool_web_crawler>',
        }
        
        # Traducciones de herramientas para streaming
        self.tool_translations = {
            'tool_semantic_search': 'Realizando búsqueda semántica...',
            'tool_lexical_search': 'Realizando búsqueda léxica...',
            'tool_regex_search': 'Realizando búsqueda por patrones...',
            'tool_get_file_content': 'Obteniendo contenido del archivo...',
            'tool_web_crawler': 'Buscando información en internet...',
        }
    
    def extract_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """
        Extrae llamadas a herramientas del contenido
        
        Args:
            content: Contenido con posibles tags XML de herramientas
            
        Returns:
            Lista de herramientas encontradas
        """
        tool_calls = []
        
        for tool_name, pattern in self.tool_patterns.items():
            matches = re.findall(pattern, content, re.DOTALL)
            
            for match in matches:
                tool_calls.append({
                    'tool_name': tool_name,
                    'raw_xml': match,
                    'position': content.find(match)
                })
        
        return tool_calls
    
    def filter_xml_tags(self, content: str) -> str:
        """
        Filtra tags XML de herramientas del contenido
        
        Args:
            content: Contenido con posibles tags XML
            
        Returns:
            Contenido sin tags XML
        """
        filtered = content
        
        for pattern in self.tool_patterns.values():
            filtered = re.sub(pattern, '', filtered, flags=re.DOTALL)
        
        # Limpiar espacios en blanco excesivos
        filtered = re.sub(r'\n\s*\n\s*\n', '\n\n', filtered)
        filtered = filtered.strip()
        
        return filtered
    
    def format_static_response(self, llm_content: str, 
                              tool_results: Optional[Dict[str, Any]] = None) -> FormattedResponse:
        """
        Formatea una respuesta estática (sin streaming)
        
        Args:
            llm_content: Contenido de la respuesta del LLM
            tool_results: Resultados de herramientas ejecutadas (opcional)
            
        Returns:
            FormattedResponse con contenido formateado
        """
        # Extraer llamadas a herramientas
        tool_calls = self.extract_tool_calls(llm_content)
        
        # Filtrar tags XML
        filtered_content = self.filter_xml_tags(llm_content)
        
        # Integrar resultados de herramientas si existen
        if tool_results:
            filtered_content = self._integrate_tool_results(
                filtered_content, 
                tool_results
            )
        
        # Formatear con markdown
        formatted_content = self._apply_markdown_formatting(filtered_content)
        
        metadata = {
            'tool_calls_extracted': len(tool_calls),
            'tools': [tc['tool_name'] for tc in tool_calls],
            'has_tool_results': tool_results is not None,
            'content_length': len(formatted_content),
            'original_length': len(llm_content)
        }
        
        return FormattedResponse(
            content=llm_content,
            format_type=ResponseFormat.STATIC,
            has_tool_calls=len(tool_calls) > 0,
            tool_calls_count=len(tool_calls),
            filtered_content=formatted_content,
            metadata=metadata
        )
    
    def _integrate_tool_results(self, content: str, 
                               tool_results: Dict[str, Any]) -> str:
        """
        Integra resultados de herramientas en el contenido
        
        Args:
            content: Contenido base
            tool_results: Resultados de herramientas
            
        Returns:
            Contenido con resultados integrados
        """
        integrated = content
        
        # Agregar sección de resultados de herramientas
        if tool_results.get('consolidated_data'):
            results_section = self._build_tool_results_section(
                tool_results['consolidated_data']
            )
            integrated += f"\n\n{results_section}"
        
        return integrated
    
    def _build_tool_results_section(self, consolidated_data: Dict[str, Any]) -> str:
        """
        Construye una sección con resultados de herramientas
        
        Args:
            consolidated_data: Datos consolidados de herramientas
            
        Returns:
            String con sección formateada
        """
        section = "## 📊 Resultados de Búsquedas\n\n"
        
        # Agregar fragmentos encontrados
        if consolidated_data.get('all_fragments'):
            section += "### Fragmentos Encontrados\n\n"
            
            for i, fragment in enumerate(consolidated_data['all_fragments'][:5], 1):
                section += f"**{i}. {fragment.get('file_name', 'Desconocido')}**\n"
                section += f"- Relevancia: {fragment.get('relevance', 'N/A')}\n"
                section += f"- Contenido: {fragment.get('summary', 'N/A')[:200]}...\n\n"
        
        # Agregar matches de regex
        if consolidated_data.get('all_matches'):
            section += "### Coincidencias de Patrones\n\n"
            
            for i, match in enumerate(consolidated_data['all_matches'][:5], 1):
                section += f"**{i}. Línea {match.get('line_number', 'N/A')}**\n"
                section += f"- Coincidencia: `{match.get('match', 'N/A')}`\n\n"
        
        # Agregar resumen
        summary = consolidated_data.get('summary', {})
        section += "### Resumen\n\n"
        section += f"- Total de resultados: {summary.get('total_results', 0)}\n"
        section += f"- Archivos únicos: {len(summary.get('total_files', []))}\n"
        section += f"- Tipos de búsqueda: {', '.join(summary.get('search_types', []))}\n"
        
        return section
    
    def _apply_markdown_formatting(self, content: str) -> str:
        """
        Aplica formateo markdown al contenido
        
        Args:
            content: Contenido a formatear
            
        Returns:
            Contenido con formateo markdown aplicado
        """
        formatted = content
        
        # Mejorar títulos
        formatted = re.sub(r'^### (.+)$', r'### \1', formatted, flags=re.MULTILINE)
        formatted = re.sub(r'^## (.+)$', r'## \1', formatted, flags=re.MULTILINE)
        formatted = re.sub(r'^# (.+)$', r'# \1', formatted, flags=re.MULTILINE)
        
        # Mejorar listas
        formatted = re.sub(r'^\- (.+)$', r'- \1', formatted, flags=re.MULTILINE)
        formatted = re.sub(r'^\* (.+)$', r'- \1', formatted, flags=re.MULTILINE)
        
        # Mejorar código
        formatted = re.sub(r'`([^`]+)`', r'`\1`', formatted)
        
        return formatted
    
    def prepare_for_streaming(self, llm_content: str) -> Dict[str, Any]:
        """
        Prepara contenido para streaming futuro
        
        Args:
            llm_content: Contenido del LLM
            
        Returns:
            Diccionario con contenido preparado para streaming
        """
        # Extraer herramientas
        tool_calls = self.extract_tool_calls(llm_content)
        
        # Dividir contenido en chunks
        chunks = self._split_into_chunks(llm_content, tool_calls)
        
        return {
            'chunks': chunks,
            'tool_calls': tool_calls,
            'total_chunks': len(chunks),
            'streaming_ready': True
        }
    
    def _split_into_chunks(self, content: str, 
                          tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Divide contenido en chunks para streaming
        
        Args:
            content: Contenido a dividir
            tool_calls: Llamadas a herramientas encontradas
            
        Returns:
            Lista de chunks
        """
        chunks = []
        current_pos = 0
        
        # Ordenar tool calls por posición
        sorted_tools = sorted(tool_calls, key=lambda x: x['position'])
        
        for tool_call in sorted_tools:
            # Agregar contenido antes de la herramienta
            if tool_call['position'] > current_pos:
                chunk_content = content[current_pos:tool_call['position']].strip()
                if chunk_content:
                    chunks.append({
                        'type': 'text',
                        'content': chunk_content,
                        'position': current_pos
                    })
            
            # Agregar traducción de herramienta
            tool_name = tool_call['tool_name']
            chunks.append({
                'type': 'tool_call',
                'tool_name': tool_name,
                'display_message': self.tool_translations.get(
                    tool_name, 
                    f'Ejecutando {tool_name}...'
                ),
                'position': tool_call['position']
            })
            
            current_pos = tool_call['position'] + len(tool_call['raw_xml'])
        
        # Agregar contenido restante
        if current_pos < len(content):
            remaining = content[current_pos:].strip()
            if remaining:
                chunks.append({
                    'type': 'text',
                    'content': remaining,
                    'position': current_pos
                })
        
        return chunks
    
    def get_formatting_summary(self, formatted_response: FormattedResponse) -> str:
        """
        Genera un resumen del formateo aplicado
        
        Args:
            formatted_response: Respuesta formateada
            
        Returns:
            String con resumen
        """
        summary = f"""
╔════════════════════════════════════════════════════════════════╗
║              RESUMEN DE FORMATEO DE RESPUESTA                  ║
╚════════════════════════════════════════════════════════════════╝

📋 Formato: {formatted_response.format_type.value}
🔧 Herramientas encontradas: {formatted_response.tool_calls_count}
✓ Contenido filtrado: {len(formatted_response.filtered_content)} caracteres

📊 Metadatos:
"""
        
        for key, value in formatted_response.metadata.items():
            summary += f"  • {key}: {value}\n"
        
        summary += f"\n📝 Contenido filtrado (primeros 300 caracteres):\n"
        summary += f"  {formatted_response.filtered_content[:300]}...\n"
        
        return summary


def main():
    """Función principal para testing"""
    import logging
    
    # Configurar logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear formateador
    formatter = ResponseFormatter()
    
    # Ejemplo de respuesta LLM con herramientas
    llm_response = """
    Voy a buscar información sobre autenticación en el sistema Darwin.
    
    <tool_semantic_search>
    <query>autenticación usuarios login</query>
    <top_k>5</top_k>
    </tool_semantic_search>
    
    Basándome en la búsqueda, aquí está la información:
    
    ## Autenticación en Darwin
    
    El sistema Darwin implementa autenticación mediante:
    
    1. **Validación de credenciales**: Se validan usuario y contraseña
    2. **Generación de tokens**: Se generan JWT tokens para sesiones
    3. **Protección de rutas**: Middleware valida tokens en cada request
    
    <tool_lexical_search>
    <query>validateToken authenticateUser</query>
    </tool_lexical_search>
    
    Para más detalles, consulta la documentación técnica.
    """
    
    # Formatear respuesta
    print("Formateando respuesta del LLM...")
    formatted = formatter.format_static_response(llm_response)
    
    # Mostrar resumen
    print(formatter.get_formatting_summary(formatted))
    
    # Mostrar contenido filtrado
    print("\n📄 Contenido Filtrado:")
    print(formatted.filtered_content)
    
    # Preparar para streaming
    print("\n\n🎬 Preparando para Streaming:")
    streaming_data = formatter.prepare_for_streaming(llm_response)
    print(f"Total de chunks: {streaming_data['total_chunks']}")
    
    for i, chunk in enumerate(streaming_data['chunks'], 1):
        if chunk['type'] == 'text':
            print(f"\n  Chunk {i} (texto): {chunk['content'][:50]}...")
        else:
            print(f"\n  Chunk {i} (herramienta): {chunk['display_message']}")


if __name__ == "__main__":
    main()
