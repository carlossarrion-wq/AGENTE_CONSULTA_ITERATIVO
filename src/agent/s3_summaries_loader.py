"""
S3 Summaries Loader - Carga dinámica de resúmenes desde S3

Responsabilidad: Consultar S3 para obtener los resúmenes de documentos
y generar la sección de documentos disponibles para el system prompt
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, BotoCoreError


class S3SummariesLoader:
    """Cargador de resúmenes desde S3 para popular el system prompt"""
    
    def __init__(self, s3_config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el cargador de resúmenes desde S3
        
        Args:
            s3_config: Diccionario con configuración de S3 (bucket_name, prefix, region_name)
                      Si es None, usa valores por defecto de Darwin
        """
        self.logger = logging.getLogger(__name__)
        
        # Usar configuración proporcionada o valores por defecto
        if s3_config is None:
            s3_config = {
                'bucket_name': 'rag-system-darwin-eu-west-1',
                'summaries_prefix': 'applications/darwin/summaries/',
                'region_name': 'eu-west-1'
            }
        
        self.bucket_name = s3_config.get('bucket_name', 'rag-system-darwin-eu-west-1')
        self.region_name = s3_config.get('region_name', 'eu-west-1')
        
        # Usar summaries_prefix directamente
        self.summaries_prefix = s3_config.get('summaries_prefix', 'applications/darwin/summaries/')
        
        self.logger.info(f"S3SummariesLoader inicializado:")
        self.logger.info(f"  • Bucket: {self.bucket_name}")
        self.logger.info(f"  • Prefix: {self.summaries_prefix}")
        self.logger.info(f"  • Region: {self.region_name}")
        
        # Inicializar cliente S3
        try:
            self.s3_client = boto3.client('s3', region_name=self.region_name)
            self.logger.info(f"Cliente S3 inicializado para bucket: {self.bucket_name}")
        except Exception as e:
            self.logger.error(f"Error inicializando cliente S3: {str(e)}")
            raise
    
    def load_summaries_from_s3(self) -> Dict[str, Any]:
        """
        Carga todos los resúmenes desde S3
        
        Returns:
            Diccionario con metadata y lista de archivos con sus resúmenes
        """
        try:
            self.logger.info(f"Cargando resúmenes desde s3://{self.bucket_name}/{self.summaries_prefix}")
            
            # Listar todos los objetos en el prefijo
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.summaries_prefix
            )
            
            if 'Contents' not in response:
                self.logger.warning(f"No se encontraron archivos en s3://{self.bucket_name}/{self.summaries_prefix}")
                return self._get_empty_catalog()
            
            files = []
            total_files = 0
            
            # Procesar cada archivo JSON de resumen
            for obj in response['Contents']:
                key = obj['Key']
                
                # Saltar si es un directorio o no es un archivo JSON
                if key.endswith('/') or not key.endswith('.json'):
                    continue
                
                try:
                    # Descargar y parsear el archivo JSON
                    file_obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                    summary_data = json.loads(file_obj['Body'].read().decode('utf-8'))
                    
                    # SIMPLIFICAR: Extraer solo los campos esenciales para el system prompt
                    simplified_data = {}
                    
                    # Campos de document_info
                    if 'document_info' in summary_data:
                        doc_info = summary_data['document_info']
                        simplified_data['file_name'] = doc_info.get('file_name', 'Unknown')
                        simplified_data['file_size'] = doc_info.get('file_size', 0)
                        simplified_data['file_extension'] = doc_info.get('file_extension', '')
                        simplified_data['application_id'] = doc_info.get('application_id', 'darwin')
                    
                    # Campos de summary_data (solo los esenciales)
                    if 'summary_data' in summary_data:
                        summ_data = summary_data['summary_data']
                        simplified_data['summary'] = summ_data.get('summary', '')
                        simplified_data['topics'] = summ_data.get('topics', [])
                        simplified_data['key_terms'] = summ_data.get('key_terms', [])
                    
                    # Agregar a la lista de archivos
                    files.append(simplified_data)
                    total_files += 1
                    
                except Exception as e:
                    self.logger.warning(f"Error procesando archivo {key}: {str(e)}")
                    continue
            
            # Construir catálogo
            catalog = {
                "metadata": {
                    "total_files": total_files,
                    "processed_at": datetime.now().isoformat(),
                    "source": f"s3://{self.bucket_name}/{self.summaries_prefix}"
                },
                "files": files
            }
            
            self.logger.info(f"✅ Cargados {total_files} resúmenes desde S3")
            return catalog
            
        except (ClientError, BotoCoreError) as e:
            self.logger.error(f"Error accediendo a S3: {str(e)}")
            return self._get_empty_catalog()
        except Exception as e:
            self.logger.error(f"Error inesperado cargando resúmenes: {str(e)}")
            return self._get_empty_catalog()
    
    def _get_empty_catalog(self) -> Dict[str, Any]:
        """
        Retorna un catálogo vacío en caso de error
        
        Returns:
            Diccionario con estructura de catálogo vacío
        """
        return {
            "metadata": {
                "total_files": 0,
                "processed_at": datetime.now().isoformat(),
                "source": f"s3://{self.bucket_name}/{self.summaries_prefix}",
                "error": "No se pudieron cargar los resúmenes"
            },
            "files": []
        }
    
    def format_summaries_for_prompt(self, catalog: Optional[Dict[str, Any]] = None, app_name: str = "darwin") -> str:
        """
        Formatea los resúmenes en el formato esperado por el system prompt
        INCLUYE el encabezado de contexto del sistema
        
        Args:
            catalog: Catálogo de resúmenes (si es None, lo carga desde S3)
            app_name: Nombre de la aplicación para el encabezado (default: "darwin")
            
        Returns:
            String formateado para incluir en el system prompt con encabezado
        """
        if catalog is None:
            catalog = self.load_summaries_from_s3()
        
        metadata = catalog.get('metadata', {})
        files = catalog.get('files', [])
        
        # Construir la sección formateada CON ENCABEZADO
        output = f"## TIENES A TU DISPOSICIÓN LOS SIGUIENTES DOCUMENTOS DE CONTEXTO DEL SISTEMA {app_name.upper()}\n\n"
        output += f"Este agente tiene acceso a la siguiente documentación técnica y funcional del sistema {app_name}:\n\n"
        output += "### Archivos Indexados Disponibles\n\n"
        output += "Los siguientes archivos están indexados y disponibles en OpenSearch para consulta:\n\n"
        output += "```\n"
        output += json.dumps(catalog, indent=2, ensure_ascii=False)
        output += "\n```\n\n"
        output += "**Formato de cada entrada:**\n"
        output += "- __file_name__: Nombre del documento original (ej: \"Dashboard.docx\")\n"
        output += "- __file_size__: Tamaño del documento original en bytes\n"
        output += "- __file_extension__: Extensión del documento original (.docx, .pdf, .xlsx, .txt)\n"
        output += "- __summary__: Resumen del contenido del documento original\n"
        output += "- __topics__: Temas principales del documento\n"
        output += "- __key_terms__: Términos clave del documento\n"
        output += f"- __application_id__: Identificador de la aplicación (siempre \"{app_name}\")\n"
        
        return output
    
    def get_summaries_section(self) -> str:
        """
        Obtiene la sección completa de resúmenes formateada para el system prompt
        
        Returns:
            String con la sección de archivos indexados disponibles
        """
        try:
            catalog = self.load_summaries_from_s3()
            return self.format_summaries_for_prompt(catalog)
        except Exception as e:
            self.logger.error(f"Error obteniendo sección de resúmenes: {str(e)}")
            # Retornar sección vacía en caso de error
            return self._get_fallback_section()
    
    def _get_fallback_section(self) -> str:
        """
        Retorna una sección de fallback en caso de error
        
        Returns:
            String con mensaje de error
        """
        return """### Archivos Indexados Disponibles

⚠️ **Error**: No se pudieron cargar los resúmenes de documentos desde S3.
Por favor, verifica la conectividad con AWS S3 y los permisos de acceso.

"""


def main():
    """Función principal para testing"""
    import logging
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    # Crear loader
    loader = S3SummariesLoader()
    
    # Cargar resúmenes
    logger.info("Cargando resúmenes desde S3...")
    catalog = loader.load_summaries_from_s3()
    
    # Mostrar estadísticas
    logger.info(f"Total de archivos: {catalog['metadata']['total_files']}")
    logger.info(f"Procesado en: {catalog['metadata']['processed_at']}")
    
    # Mostrar primeros 3 archivos
    if catalog['files']:
        logger.info("\nPrimeros 3 archivos:")
        for i, file_info in enumerate(catalog['files'][:3], 1):
            logger.info(f"{i}. {file_info.get('file_name', 'N/A')}")
            logger.info(f"   Tamaño: {file_info.get('file_size', 0)} bytes")
            logger.info(f"   Resumen: {file_info.get('summary', 'N/A')[:100]}...")
    
    # Generar sección formateada
    logger.info("\nGenerando sección formateada para system prompt...")
    section = loader.get_summaries_section()
    
    # Mostrar primeros 500 caracteres
    logger.info(f"\nPrimeros 500 caracteres de la sección:\n{section[:500]}...")


if __name__ == "__main__":
    main()
