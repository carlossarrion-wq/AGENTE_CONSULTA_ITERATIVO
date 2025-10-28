#!/usr/bin/env python3
import json
import os
import stat
from datetime import datetime
from pathlib import Path

def get_file_info(file_path):
    """Obtiene información detallada de un archivo"""
    try:
        file_stat = os.stat(file_path)
        return {
            'size': file_stat.st_size,
            'last_modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        }
    except Exception as e:
        return {
            'size': 0,
            'last_modified': None,
            'error': str(e)
        }

def process_json_file(file_path):
    """Procesa un archivo JSON y extrae la información relevante"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extraer información del documento
        doc_info = data.get('document_info', {})
        summary_data = data.get('summary_data', {})
        
        # Obtener información del archivo físico
        file_info = get_file_info(file_path)
        
        return {
            'file_name': doc_info.get('file_name', 'Unknown'),
            'file_size': doc_info.get('file_size', 0),
            'file_extension': doc_info.get('file_extension', 'Unknown'),
            'summary_id': os.path.basename(file_path),
            'summary': summary_data.get('summary', 'No summary available'),
            'application_id': doc_info.get('application_id', 'Unknown')
        }
    except Exception as e:
        file_info = get_file_info(file_path)
        return {
            'file_name': 'Unknown',
            'file_size': 0,
            'file_extension': 'Unknown',
            'summary_id': os.path.basename(file_path),
            'summary': f'Error processing file: {str(e)}',
            'application_id': 'Unknown',
            'error': str(e)
        }

def main():
    # Obtener la ruta raíz del proyecto (2 niveles arriba desde este script)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    summaries_dir = project_root / 'Summaries'
    
    if not summaries_dir.exists():
        print(f"Error: Directory {summaries_dir} does not exist")
        return
    
    files_info = []
    
    # Procesar todos los archivos JSON en el directorio
    for file_path in summaries_dir.glob('*.json'):
        print(f"Processing: {file_path.name}")
        file_info = process_json_file(file_path)
        files_info.append(file_info)
    
    # Ordenar por nombre de archivo original
    files_info.sort(key=lambda x: x['file_name'])
    
    # Crear el resultado final
    result = {
        'metadata': {
            'total_files': len(files_info),
            'processed_at': datetime.now().isoformat(),
            'directory': str(summaries_dir)
        },
        'files': files_info
    }
    
    # Guardar el resultado en la raíz del proyecto
    output_file = project_root / 'summaries_catalog.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\nProcessing complete!")
    print(f"Total files processed: {len(files_info)}")
    print(f"Output saved to: {output_file}")

if __name__ == "__main__":
    main()
