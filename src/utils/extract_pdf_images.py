#!/usr/bin/env python3
"""
Script para extraer y guardar todas las imágenes de un PDF
Útil para análisis y debugging de detección de imágenes
"""

import os
import sys
import fitz  # PyMuPDF
import argparse
from pathlib import Path
from loguru import logger
import hashlib

def extract_images_from_pdf(pdf_path: str, output_dir: str, min_width: int = 0, min_height: int = 0, min_pixels: int = 0):
    """
    Extrae todas las imágenes de un PDF y las guarda en un directorio
    
    Args:
        pdf_path: Ruta al archivo PDF
        output_dir: Directorio donde guardar las imágenes
        min_width: Ancho mínimo para filtrar (0 = sin filtro)
        min_height: Alto mínimo para filtrar (0 = sin filtro)
        min_pixels: Píxeles totales mínimos para filtrar (0 = sin filtro)
    """
    
    # Crear directorio de salida si no existe
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Abrir PDF
    logger.info(f"Abriendo PDF: {pdf_path}")
    pdf_document = fitz.open(pdf_path)
    
    # Estadísticas
    total_images = 0
    extracted_images = 0
    filtered_images = 0
    duplicate_images = 0
    seen_hashes = set()
    
    # Crear archivo de reporte
    report_path = output_path / "extraction_report.txt"
    report_lines = []
    report_lines.append(f"REPORTE DE EXTRACCIÓN DE IMÁGENES")
    report_lines.append(f"PDF: {pdf_path}")
    report_lines.append(f"Filtros aplicados: min_width={min_width}, min_height={min_height}, min_pixels={min_pixels}")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    # Procesar cada página
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        image_list = page.get_images()
        
        logger.info(f"📄 Página {page_num + 1}: {len(image_list)} imágenes detectadas")
        report_lines.append(f"\n--- PÁGINA {page_num + 1} ---")
        report_lines.append(f"Imágenes detectadas: {len(image_list)}")
        report_lines.append("")
        
        total_images += len(image_list)
        
        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]
                
                # Obtener información de la imagen
                try:
                    base_image = pdf_document.extract_image(xref)
                    img_ext = base_image.get('ext', 'png')
                    img_colorspace = base_image.get('colorspace', 'unknown')
                    img_bpc = base_image.get('bpc', 'unknown')
                except Exception as e:
                    img_ext = 'png'
                    img_colorspace = 'unknown'
                    img_bpc = 'unknown'
                
                # Crear Pixmap para obtener dimensiones
                pix = fitz.Pixmap(pdf_document, xref)
                width = pix.width
                height = pix.height
                total_pixels = width * height
                colorspace_pix = pix.colorspace.name if pix.colorspace else 'unknown'
                
                # Información de la imagen
                img_info = f"Imagen {img_index + 1}: {width}x{height} ({total_pixels:,} px) - colorspace: {colorspace_pix}, ext: {img_ext}, bpc: {img_bpc}"
                
                # Aplicar filtros
                filtered = False
                filter_reasons = []
                
                if min_width > 0 and width < min_width:
                    filtered = True
                    filter_reasons.append(f"width {width} < {min_width}")
                
                if min_height > 0 and height < min_height:
                    filtered = True
                    filter_reasons.append(f"height {height} < {min_height}")
                
                if min_pixels > 0 and total_pixels < min_pixels:
                    filtered = True
                    filter_reasons.append(f"pixels {total_pixels} < {min_pixels}")
                
                if filtered:
                    logger.debug(f"🔍 {img_info} - FILTRADA: {', '.join(filter_reasons)}")
                    report_lines.append(f"  {img_info} - FILTRADA: {', '.join(filter_reasons)}")
                    filtered_images += 1
                    pix = None
                    continue
                
                # Convertir a PNG si es posible
                if pix.n - pix.alpha < 4:  # GRAY or RGB
                    img_data = pix.tobytes("png")
                    
                    # Calcular hash para detectar duplicados
                    img_hash = hashlib.md5(img_data).hexdigest()
                    
                    # Verificar si es duplicado
                    if img_hash in seen_hashes:
                        logger.debug(f"🔄 {img_info} - DUPLICADA (hash: {img_hash[:8]})")
                        report_lines.append(f"  {img_info} - DUPLICADA (hash: {img_hash[:8]})")
                        duplicate_images += 1
                        pix = None
                        continue
                    
                    seen_hashes.add(img_hash)
                    
                    # Guardar imagen
                    filename = f"page{page_num + 1:03d}_img{img_index + 1:03d}_{width}x{height}_{img_hash[:8]}.png"
                    filepath = output_path / filename
                    
                    with open(filepath, "wb") as img_file:
                        img_file.write(img_data)
                    
                    extracted_images += 1
                    logger.info(f"✅ {img_info} - GUARDADA: {filename}")
                    report_lines.append(f"  {img_info} - GUARDADA: {filename}")
                else:
                    logger.debug(f"⚠️  {img_info} - COLORSPACE NO SOPORTADO (n={pix.n}, alpha={pix.alpha})")
                    report_lines.append(f"  {img_info} - COLORSPACE NO SOPORTADO")
                
                pix = None
                
            except Exception as e:
                logger.error(f"Error extrayendo imagen {img_index + 1} de página {page_num + 1}: {e}")
                report_lines.append(f"  Imagen {img_index + 1}: ERROR - {e}")
    
    # Resumen final
    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("RESUMEN")
    report_lines.append("=" * 80)
    report_lines.append(f"Total de imágenes detectadas: {total_images}")
    report_lines.append(f"Imágenes extraídas y guardadas: {extracted_images}")
    report_lines.append(f"Imágenes filtradas (no cumplen requisitos): {filtered_images}")
    report_lines.append(f"Imágenes duplicadas (omitidas): {duplicate_images}")
    report_lines.append("")
    
    # Guardar reporte
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 RESUMEN DE EXTRACCIÓN")
    logger.info("=" * 80)
    logger.info(f"Total de imágenes detectadas: {total_images}")
    logger.info(f"Imágenes extraídas y guardadas: {extracted_images}")
    logger.info(f"Imágenes filtradas: {filtered_images}")
    logger.info(f"Imágenes duplicadas: {duplicate_images}")
    logger.info(f"Directorio de salida: {output_path.absolute()}")
    logger.info(f"Reporte guardado en: {report_path.absolute()}")
    logger.info("=" * 80)
    
    pdf_document.close()
    
    return {
        'total': total_images,
        'extracted': extracted_images,
        'filtered': filtered_images,
        'duplicates': duplicate_images,
        'output_dir': str(output_path.absolute())
    }


def main():
    parser = argparse.ArgumentParser(
        description='Extrae y guarda todas las imágenes de un PDF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  # Extraer TODAS las imágenes (sin filtros)
  python3 src/utils/extract_pdf_images.py documento.pdf -o imagenes_extraidas

  # Extraer solo imágenes grandes (con filtros de producción)
  python3 src/utils/extract_pdf_images.py documento.pdf -o imagenes_grandes \\
    --min-width 500 --min-height 500 --min-pixels 250000

  # Extraer imágenes medianas
  python3 src/utils/extract_pdf_images.py documento.pdf -o imagenes_medianas \\
    --min-width 100 --min-height 100

  # Desde S3 (primero descargar el archivo)
  aws s3 cp s3://bucket/documento.pdf /tmp/documento.pdf
  python3 src/utils/extract_pdf_images.py /tmp/documento.pdf -o imagenes_s3
        """
    )
    
    parser.add_argument('pdf_path', help='Ruta al archivo PDF')
    parser.add_argument('-o', '--output', required=True, help='Directorio de salida para las imágenes')
    parser.add_argument('--min-width', type=int, default=0, help='Ancho mínimo en píxeles (0 = sin filtro)')
    parser.add_argument('--min-height', type=int, default=0, help='Alto mínimo en píxeles (0 = sin filtro)')
    parser.add_argument('--min-pixels', type=int, default=0, help='Píxeles totales mínimos (0 = sin filtro)')
    
    args = parser.parse_args()
    
    # Verificar que el PDF existe
    if not os.path.exists(args.pdf_path):
        logger.error(f"El archivo PDF no existe: {args.pdf_path}")
        sys.exit(1)
    
    # Extraer imágenes
    try:
        result = extract_images_from_pdf(
            pdf_path=args.pdf_path,
            output_dir=args.output,
            min_width=args.min_width,
            min_height=args.min_height,
            min_pixels=args.min_pixels
        )
        
        logger.success(f"✅ Extracción completada: {result['extracted']} imágenes guardadas en {result['output_dir']}")
        
    except Exception as e:
        logger.error(f"Error durante la extracción: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
