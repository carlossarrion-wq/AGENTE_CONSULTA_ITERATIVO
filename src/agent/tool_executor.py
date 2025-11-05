"""
Tool Execution Engine - Ejecución de herramientas de búsqueda

Responsabilidad: Ejecutar herramientas de búsqueda y consolidar resultados
- Parsing de XML de respuestas LLM
- Enrutamiento a herramientas específicas
- Consolidación de resultados múltiples
- Manejo de errores de herramientas
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

# Importar herramientas de búsqueda
import sys
from pathlib import Path

# Agregar src al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.tool_semantic_search import SemanticSearch
from tools.tool_lexical_search import LexicalSearch
from tools.tool_regex_search import RegexSearch
from tools.tool_get_file_content import GetFileContent
from tools.tool_get_file_section import GetFileSection
from tools.tool_web_crawler import execute_web_crawler
from agent.color_utils import tool_result as color_tool_result


class ToolType(Enum):
    """Tipos de herramientas disponibles"""
    SEMANTIC_SEARCH = "semantic_search"
    LEXICAL_SEARCH = "lexical_search"
    REGEX_SEARCH = "regex_search"
    GET_FILE_CONTENT = "get_file_content"
    GET_FILE_SECTION = "get_file_section"
    WEB_CRAWLER = "web_crawler"


@dataclass
class ToolResult:
    """Resultado de la ejecución de una herramienta"""
    tool_type: ToolType
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ConsolidatedResults:
    """Resultados consolidados de múltiples herramientas"""
    total_tools_executed: int
    successful_executions: int
    failed_executions: int
    results: List[ToolResult]
    consolidated_data: Dict[str, Any]
    execution_time_ms: float
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class ToolExecutor:
    """Ejecutor de herramientas de búsqueda"""
    
    def __init__(self, config_path: str = "config/config.yaml", app_name: str = "mulesoft"):
        """
        Inicializa el ejecutor de herramientas
        
        Args:
            config_path: Ruta al archivo de configuración
            app_name: Nombre de la aplicación (mulesoft, darwin, sap)
        """
        self.config_path = config_path
        self.app_name = app_name
        self.logger = logging.getLogger(__name__)
        
        # Inicializar herramientas
        try:
            self.semantic_search = SemanticSearch(config_path)
            self.lexical_search = LexicalSearch(config_path)
            self.regex_search = RegexSearch(config_path)
            self.get_file_content = GetFileContent(config_path)
            self.get_file_section = GetFileSection(config_path=config_path, app_name=app_name)
            self.logger.info("Todas las herramientas inicializadas correctamente")
        except Exception as e:
            self.logger.error(f"Error inicializando herramientas: {str(e)}")
            raise
    
    def parse_tool_calls_from_xml(self, llm_response: str) -> List[Dict[str, Any]]:
        """
        Extrae llamadas a herramientas del formato XML de respuesta LLM
        
        Args:
            llm_response: Respuesta del LLM con tags XML de herramientas
            
        Returns:
            Lista de diccionarios con información de herramientas a ejecutar
            
        Ejemplo de entrada:
            "Voy a buscar información sobre OAuth.
            <semantic_search>
            <query>configuración OAuth aplicaciones web</query>
            <top_k>10</top_k>
            </semantic_search>"
        """
        tool_calls = []
        
        # Patrones regex para cada tipo de herramienta (solo formato con prefijo tool_)
        patterns = {
            ToolType.SEMANTIC_SEARCH: r'<tool_semantic_search>(.*?)</tool_semantic_search>',
            ToolType.LEXICAL_SEARCH: r'<tool_lexical_search>(.*?)</tool_lexical_search>',
            ToolType.REGEX_SEARCH: r'<tool_regex_search>(.*?)</tool_regex_search>',
            ToolType.GET_FILE_CONTENT: r'<tool_get_file_content>(.*?)</tool_get_file_content>',
            ToolType.GET_FILE_SECTION: r'<tool_get_file_section>(.*?)</tool_get_file_section>',
            ToolType.WEB_CRAWLER: r'<tool_web_crawler>(.*?)</tool_web_crawler>',
        }
        
        for tool_type, pattern in patterns.items():
            matches = re.findall(pattern, llm_response, re.DOTALL)
            
            for match in matches:
                # Parsear parámetros XML
                params = self._parse_xml_params(match)
                
                tool_calls.append({
                    'tool_type': tool_type,
                    'params': params,
                    'raw_xml': match
                })
        
        
        self.logger.debug(f"Extraídas {len(tool_calls)} llamadas a herramientas del LLM")
        return tool_calls
    
    def _parse_xml_params(self, xml_content: str) -> Dict[str, Any]:
        """
        Parsea parámetros de contenido XML
        
        Args:
            xml_content: Contenido XML con parámetros
            
        Returns:
            Diccionario con parámetros parseados
        """
        params = {}
        
        # Extraer todos los tags XML
        tag_pattern = r'<(\w+)>(.*?)</\1>'
        matches = re.findall(tag_pattern, xml_content, re.DOTALL)
        
        for tag_name, tag_value in matches:
            tag_value = tag_value.strip()
            
            # Intentar parsear como JSON si comienza con [ o {
            if tag_value.startswith('[') or tag_value.startswith('{'):
                try:
                    params[tag_name] = json.loads(tag_value)
                except json.JSONDecodeError:
                    params[tag_name] = tag_value
            else:
                # Intentar convertir a número si es posible
                try:
                    if '.' in tag_value:
                        params[tag_name] = float(tag_value)
                    else:
                        params[tag_name] = int(tag_value)
                except ValueError:
                    params[tag_name] = tag_value
        
        return params
    
    def execute_tool(self, tool_type: ToolType, params: Dict[str, Any]) -> ToolResult:
        """
        Ejecuta una herramienta específica
        
        Args:
            tool_type: Tipo de herramienta a ejecutar
            params: Parámetros para la herramienta
            
        Returns:
            ToolResult con resultado de la ejecución
        """
        import time
        start_time = time.time()
        
        # Log de inicio de ejecución (solo al archivo, no a pantalla)
        separator = "="*80
        self.logger.info(separator)
        self.logger.info(f"🔧 EJECUTANDO HERRAMIENTA: {tool_type.value}")
        self.logger.info(separator)
        self.logger.info(f"Parámetros: {json.dumps(params, indent=2, ensure_ascii=False)}")
        self.logger.info("-"*80)
        
        try:
            if tool_type == ToolType.SEMANTIC_SEARCH:
                result = self.semantic_search.search(**params)
            
            elif tool_type == ToolType.LEXICAL_SEARCH:
                # Log detallado antes de llamar a lexical_search
                self.logger.info("🎯 LLAMANDO A LEXICAL_SEARCH.SEARCH()")
                self.logger.info(f"   Parámetros que se van a pasar:")
                for key, value in params.items():
                    self.logger.info(f"      {key} = {repr(value)} (tipo: {type(value).__name__})")
                self.logger.info("-"*80)
                
                result = self.lexical_search.search(**params)
            
            elif tool_type == ToolType.REGEX_SEARCH:
                result = self.regex_search.search(**params)
            
            elif tool_type == ToolType.GET_FILE_CONTENT:
                result = self.get_file_content.get_content(**params)
            
            elif tool_type == ToolType.GET_FILE_SECTION:
                result = self.get_file_section.get_section(**params)
            
            elif tool_type == ToolType.WEB_CRAWLER:
                # Inyectar app_name en los parámetros si no está presente
                if 'app_name' not in params:
                    params['app_name'] = self.app_name
                
                # Ejecutar web crawler
                crawler_result = execute_web_crawler(params)
                if crawler_result.success:
                    result = crawler_result.data
                else:
                    raise Exception(crawler_result.error)
            
            else:
                raise ValueError(f"Tipo de herramienta desconocido: {tool_type}")
            
            execution_time = (time.time() - start_time) * 1000  # ms
            
            # Log de resultado exitoso (solo al archivo, no a pantalla)
            self.logger.info(f"✅ RESULTADO EXITOSO")
            self.logger.info(f"Tiempo de ejecución: {execution_time:.2f}ms")
            self.logger.info("-"*80)
            self.logger.info("DATOS DEVUELTOS:")
            self.logger.info("-"*80)
            
            # Formatear resultado según el tipo de herramienta
            result_summary = self._format_tool_result(tool_type, result)
            self.logger.info(result_summary)
            
            self.logger.info(separator)
            
            return ToolResult(
                tool_type=tool_type,
                success=True,
                data=result,
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"Error ejecutando {tool_type.value}: {str(e)}"
            
            # Log de error (solo al archivo de log, no mostrar en consola)
            # Usar debug en lugar de error para evitar que se muestre en pantalla
            self.logger.debug(f"❌ ERROR EN EJECUCIÓN")
            self.logger.debug(f"Tiempo de ejecución: {execution_time:.2f}ms")
            self.logger.debug(f"Error: {error_msg}")
            self.logger.debug(separator)
            
            return ToolResult(
                tool_type=tool_type,
                success=False,
                data={},
                error=error_msg,
                execution_time_ms=execution_time
            )
    
    def _format_tool_result(self, tool_type: ToolType, result: Dict[str, Any]) -> str:
        """
        Formatea el resultado de una herramienta para logging
        
        Args:
            tool_type: Tipo de herramienta
            result: Resultado de la herramienta
            
        Returns:
            String formateado con el resultado
        """
        if tool_type == ToolType.SEMANTIC_SEARCH or tool_type == ToolType.LEXICAL_SEARCH:
            fragments = result.get('fragments', [])
            total = len(fragments)
            formatted = f"Total de fragmentos encontrados: {total}\n"
            
            if total > 0:
                formatted += "\nPrimeros 3 resultados:\n"
                for i, fragment in enumerate(fragments[:3], 1):
                    formatted += f"\n{i}. Archivo: {fragment.get('file_name', 'N/A')}\n"
                    if 'score' in fragment:
                        formatted += f"   Score: {fragment['score']:.4f}\n"
                    content = fragment.get('content', '')[:200]
                    formatted += f"   Contenido: {content}...\n"
            
            return formatted
        
        elif tool_type == ToolType.REGEX_SEARCH:
            results = result.get('results', [])
            total_matches = result.get('total_matches', 0)
            formatted = f"Total de coincidencias: {total_matches}\n"
            formatted += f"Archivos con coincidencias: {len(results)}\n"
            
            if results:
                formatted += "\nPrimeros 2 archivos:\n"
                for i, file_result in enumerate(results[:2], 1):
                    formatted += f"\n{i}. Archivo: {file_result.get('file_path', 'N/A')}\n"
                    formatted += f"   Coincidencias: {file_result.get('match_count', 0)}\n"
            
            return formatted
        
        elif tool_type == ToolType.GET_FILE_CONTENT:
            file_path = result.get('file_path', 'N/A')
            access_mode = result.get('access_mode', 'full')
            
            formatted = f"Archivo: {file_path}\n"
            formatted += f"Modo de acceso: {access_mode}\n"
            
            # Si es modo progresivo, mostrar estructura completa
            if access_mode == 'progressive':
                formatted += f"\n⚠️  ARCHIVO GRANDE - MODO PROGRESIVO ACTIVADO\n"
                formatted += f"Tamaño: {result.get('content_length', 'N/A')} caracteres\n"
                formatted += f"Mensaje: {result.get('message', 'N/A')}\n"
                
                if 'structure' in result:
                    structure = result['structure']
                    formatted += f"\n📋 ESTRUCTURA DEL DOCUMENTO:\n"
                    formatted += json.dumps(structure, indent=2, ensure_ascii=False)
                
                if 'available_sections' in result:
                    formatted += f"\n\n📑 Secciones disponibles: {result['available_sections']}\n"
                
                if 'chunk_ranges' in result:
                    formatted += f"\n📊 Rangos de chunks: {result['chunk_ranges']}\n"
                
                if 'recommendation' in result:
                    formatted += f"\n💡 Recomendación: {result['recommendation']}\n"
            else:
                # Modo completo - mostrar contenido
                content = result.get('content', '')
                content_length = len(content)
                formatted += f"Tamaño del contenido: {content_length} caracteres\n"
                formatted += f"\nPrimeros 300 caracteres:\n{content[:300]}...\n"
            
            return formatted
        
        elif tool_type == ToolType.WEB_CRAWLER:
            sources = result.get('sources', [])
            query = result.get('query', 'N/A')
            total = len(sources)
            formatted = f"Query: {query}\n"
            formatted += f"Total de fuentes web encontradas: {total}\n"
            
            if total > 0:
                formatted += "\nFuentes extraídas:\n"
                for i, source in enumerate(sources, 1):
                    formatted += f"\n{i}. URL: {source.get('url', 'N/A')}\n"
                    formatted += f"   Método: {source.get('extraction_method', 'N/A')}\n"
                    content = source.get('content', '')[:200]
                    formatted += f"   Contenido: {content}...\n"
            
            return formatted
        
        else:
            return json.dumps(result, indent=2, ensure_ascii=False)[:500] + "..."
    
    def execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> ConsolidatedResults:
        """
        Ejecuta múltiples llamadas a herramientas
        
        Args:
            tool_calls: Lista de llamadas a herramientas
            
        Returns:
            ConsolidatedResults con todos los resultados
        """
        import time
        start_time = time.time()
        
        results = []
        successful = 0
        failed = 0
        
        for tool_call in tool_calls:
            tool_type = tool_call['tool_type']
            params = tool_call['params']
            
            self.logger.debug(f"Ejecutando {tool_type.value} con parámetros: {params}")
            
            result = self.execute_tool(tool_type, params)
            results.append(result)
            
            if result.success:
                successful += 1
            else:
                failed += 1
        
        # Consolidar resultados
        consolidated_data = self._consolidate_results(results)
        
        execution_time = (time.time() - start_time) * 1000
        
        return ConsolidatedResults(
            total_tools_executed=len(tool_calls),
            successful_executions=successful,
            failed_executions=failed,
            results=results,
            consolidated_data=consolidated_data,
            execution_time_ms=execution_time
        )
    
    def _consolidate_results(self, results: List[ToolResult]) -> Dict[str, Any]:
        """
        Consolida resultados de múltiples herramientas
        
        Args:
            results: Lista de resultados de herramientas
            
        Returns:
            Diccionario con datos consolidados
        """
        consolidated = {
            'by_tool_type': {},
            'all_fragments': [],
            'all_matches': [],
            'file_contents': {},
            'web_sources': [],
            'summary': {
                'total_results': 0,
                'total_files': set(),
                'search_types': set(),
                'web_sources_count': 0
            }
        }
        
        for result in results:
            if not result.success:
                continue
            
            tool_type = result.tool_type.value
            data = result.data
            
            # Agrupar por tipo de herramienta
            if tool_type not in consolidated['by_tool_type']:
                consolidated['by_tool_type'][tool_type] = []
            
            consolidated['by_tool_type'][tool_type].append(data)
            
            # Consolidar fragmentos (de búsquedas)
            if 'fragments' in data:
                consolidated['all_fragments'].extend(data['fragments'])
                consolidated['summary']['total_results'] += len(data['fragments'])
                
                # Extraer nombres de archivos
                for fragment in data['fragments']:
                    if 'file_name' in fragment:
                        consolidated['summary']['total_files'].add(fragment['file_name'])
            
            # Consolidar matches (de regex)
            if 'results' in data and isinstance(data['results'], list):
                for result_item in data['results']:
                    if 'matches' in result_item:
                        consolidated['all_matches'].extend(result_item['matches'])
                        if 'file_path' in result_item:
                            consolidated['summary']['total_files'].add(result_item['file_path'])
            
            # Consolidar contenido de archivos
            if 'content' in data and 'file_path' in data:
                consolidated['file_contents'][data['file_path']] = data['content']
                consolidated['summary']['total_files'].add(data['file_path'])
            
            # Consolidar resultados de web_crawler
            if 'sources' in data and tool_type == 'web_crawler':
                consolidated['web_sources'].extend(data['sources'])
                consolidated['summary']['web_sources_count'] += len(data['sources'])
                consolidated['summary']['total_results'] += len(data['sources'])
                consolidated['summary']['search_types'].add('web_crawler')
            
            # Consolidar URLs recomendadas de web_crawler (nueva estrategia)
            if 'recommended_urls' in data and tool_type == 'web_crawler':
                consolidated['web_sources'].extend(data['recommended_urls'])
                consolidated['summary']['web_sources_count'] += len(data['recommended_urls'])
                consolidated['summary']['total_results'] += len(data['recommended_urls'])
                consolidated['summary']['search_types'].add('web_crawler')
            
            # Registrar tipo de búsqueda
            if 'search_type' in data:
                consolidated['summary']['search_types'].add(data['search_type'])
        
        # Convertir sets a listas para serialización
        consolidated['summary']['total_files'] = list(consolidated['summary']['total_files'])
        consolidated['summary']['search_types'] = list(consolidated['summary']['search_types'])
        
        return consolidated
    
    def execute_from_llm_response(self, llm_response: str) -> ConsolidatedResults:
        """
        Ejecuta herramientas basadas en respuesta del LLM
        
        Flujo completo:
        1. Parsea XML de respuesta LLM
        2. Extrae llamadas a herramientas
        3. Ejecuta todas las herramientas
        4. Consolida resultados
        
        Args:
            llm_response: Respuesta del LLM con tags XML
            
        Returns:
            ConsolidatedResults con todos los resultados
        """
        self.logger.info("Procesando respuesta del LLM para extraer herramientas")
        
        # Parsear llamadas a herramientas
        tool_calls = self.parse_tool_calls_from_xml(llm_response)
        
        if not tool_calls:
            self.logger.warning("No se encontraron llamadas a herramientas en la respuesta del LLM")
            return ConsolidatedResults(
                total_tools_executed=0,
                successful_executions=0,
                failed_executions=0,
                results=[],
                consolidated_data={},
                execution_time_ms=0.0
            )
        
        self.logger.info(f"Encontradas {len(tool_calls)} llamadas a herramientas")
        
        # Ejecutar herramientas
        return self.execute_tool_calls(tool_calls)
    
    def get_execution_summary(self, consolidated_results: ConsolidatedResults) -> str:
        """
        Genera un resumen de la ejecución de herramientas
        
        Args:
            consolidated_results: Resultados consolidados
            
        Returns:
            String con resumen formateado
        """
        summary = f"""
╔════════════════════════════════════════════════════════════════╗
║           RESUMEN DE EJECUCIÓN DE HERRAMIENTAS                ║
╚════════════════════════════════════════════════════════════════╝

📊 Estadísticas Generales:
  • Total de herramientas ejecutadas: {consolidated_results.total_tools_executed}
  • Ejecuciones exitosas: {consolidated_results.successful_executions}
  • Ejecuciones fallidas: {consolidated_results.failed_executions}
  • Tiempo total: {consolidated_results.execution_time_ms:.2f}ms

📁 Datos Consolidados:
  • Total de resultados: {consolidated_results.consolidated_data.get('summary', {}).get('total_results', 0)}
  • Archivos únicos encontrados: {len(consolidated_results.consolidated_data.get('summary', {}).get('total_files', []))}
  • Tipos de búsqueda: {', '.join(consolidated_results.consolidated_data.get('summary', {}).get('search_types', []))}

🔧 Detalles por Herramienta:
"""
        
        for result in consolidated_results.results:
            status = "✓" if result.success else "✗"
            summary += f"\n  {status} {result.tool_type.value}"
            summary += f"\n     Tiempo: {result.execution_time_ms:.2f}ms"
            
            if result.error:
                summary += f"\n     Error: {result.error}"
            else:
                # Mostrar estadísticas del resultado
                if 'total_found' in result.data:
                    summary += f"\n     Resultados: {result.data['total_found']}"
                if 'match_count' in result.data:
                    summary += f"\n     Coincidencias: {result.data['match_count']}"
        
        summary += "\n"
        return summary


def main():
    """Función principal para testing"""
    import logging
    
    # Configurar logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear ejecutor
    executor = ToolExecutor()
    
    # Ejemplo de respuesta LLM con herramientas
    llm_response = """
    Voy a buscar información sobre autenticación en el sistema.
    
    <semantic_search>
    <query>autenticación usuarios login</query>
    <top_k>5</top_k>
    </semantic_search>
    
    También buscaré patrones de código relacionados:
    
    <regex_search>
    <pattern>function.*auth.*\\(</pattern>
    <case_sensitive>false</case_sensitive>
    </regex_search>
    """
    
    # Ejecutar herramientas
    print("Ejecutando herramientas desde respuesta LLM...")
    results = executor.execute_from_llm_response(llm_response)
    
    # Mostrar resumen
    print(executor.get_execution_summary(results))
    
    # Mostrar datos consolidados
    print("\n📦 Datos Consolidados:")
    print(json.dumps(results.consolidated_data, indent=2, default=str))


if __name__ == "__main__":
    main()
