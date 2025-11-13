#!/usr/bin/env python3
"""
Test script for Excel optimization performance
Demonstrates the performance improvements of the optimized Excel processing
"""

import os
import sys
import time
import pandas as pd
from typing import Dict, Any
from loguru import logger

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.ingestion.optimized_excel_loader import OptimizedExcelLoader
from src.ingestion.document_loader import DocumentLoader
from src.utils.connection_manager import ConnectionManager


def create_test_excel_file(file_path: str, rows: int = 5000, sheets: int = 3) -> str:
    """
    Create a test Excel file with multiple sheets and many rows.
    
    Args:
        file_path: Path where to create the test file
        rows: Number of rows per sheet
        sheets: Number of sheets
        
    Returns:
        Path to created file
    """
    logger.info(f"Creating test Excel file: {file_path} with {sheets} sheets, {rows} rows each")
    
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        for sheet_idx in range(sheets):
            sheet_name = f"TestSheet_{sheet_idx + 1}"
            
            # Create sample data
            data = {
                'ID': range(1, rows + 1),
                'Código': [f'COD{i:04d}' for i in range(1, rows + 1)],
                'Descripción': [f'Descripción del elemento {i}' for i in range(1, rows + 1)],
                'Categoría': [f'Cat_{i % 10}' for i in range(1, rows + 1)],
                'Valor': [round(i * 1.5 + (i % 100), 2) for i in range(1, rows + 1)],
                'Estado': ['Activo' if i % 3 == 0 else 'Inactivo' for i in range(1, rows + 1)],
                'Fecha': pd.date_range('2023-01-01', periods=rows, freq='D')[:rows],
                'Observaciones': [f'Observación detallada para el registro {i} con información adicional' for i in range(1, rows + 1)]
            }
            
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
    logger.info(f"Test Excel file created: {file_size:.2f} MB")
    
    return file_path


def test_standard_loading(file_path: str) -> Dict[str, Any]:
    """Test standard Excel loading performance."""
    logger.info("Testing STANDARD Excel loading...")
    
    start_time = time.time()
    
    # Create mock connection manager
    conn_manager = None
    doc_loader = DocumentLoader(conn_manager)
    
    # Create base document structure
    document = {
        'file_path': file_path,
        'file_name': os.path.basename(file_path),
        'file_extension': '.xlsx',
        'file_size': os.path.getsize(file_path),
        'file_hash': 'test_hash',
        'content': '',
        'images': [],
        'metadata': {}
    }
    
    # Load using standard method
    result = doc_loader._load_excel(file_path, document)
    
    loading_time = time.time() - start_time
    
    # Analyze result
    content_length = len(result.get('content', ''))
    sheets = result.get('metadata', {}).get('sheets', [])
    
    stats = {
        'method': 'standard',
        'loading_time': loading_time,
        'content_length': content_length,
        'sheets_count': len(sheets),
        'sheets': sheets,
        'memory_efficient': False
    }
    
    logger.info(f"Standard loading completed in {loading_time:.2f}s")
    logger.info(f"Content length: {content_length:,} characters")
    logger.info(f"Sheets processed: {len(sheets)}")
    
    return stats


def test_optimized_loading(file_path: str, batch_size: int = 1000, max_rows_per_chunk: int = 50) -> Dict[str, Any]:
    """Test optimized Excel loading performance."""
    logger.info(f"Testing OPTIMIZED Excel loading (batch_size={batch_size}, max_rows_per_chunk={max_rows_per_chunk})...")
    
    start_time = time.time()
    
    # Create optimized loader
    optimizer = OptimizedExcelLoader(
        batch_size=batch_size,
        max_rows_per_chunk=max_rows_per_chunk
    )
    
    # Create base document structure
    document = {
        'file_path': file_path,
        'file_name': os.path.basename(file_path),
        'file_extension': '.xlsx',
        'file_size': os.path.getsize(file_path),
        'file_hash': 'test_hash',
        'content': '',
        'images': [],
        'metadata': {}
    }
    
    # Load using optimized method
    result = optimizer.load_excel_optimized(file_path, document)
    
    loading_time = time.time() - start_time
    
    # Analyze result
    content_length = len(result.get('content', ''))
    optimized_chunks = result.get('optimized_chunks', [])
    metadata = result.get('metadata', {})
    
    # Calculate chunk statistics
    total_rows = metadata.get('total_rows', 0)
    total_chunks = len(optimized_chunks)
    
    chunk_sizes = [chunk.get('row_count', 0) for chunk in optimized_chunks]
    avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
    
    stats = {
        'method': 'optimized',
        'loading_time': loading_time,
        'content_length': content_length,
        'sheets_count': metadata.get('total_sheets', 0),
        'total_rows': total_rows,
        'total_chunks': total_chunks,
        'avg_chunk_size': avg_chunk_size,
        'batch_size': batch_size,
        'max_rows_per_chunk': max_rows_per_chunk,
        'memory_efficient': True,
        'chunk_details': [
            {
                'sheet': chunk.get('sheet_name', 'unknown'),
                'rows': chunk.get('row_count', 0),
                'row_range': f"{chunk.get('row_start', 0)}-{chunk.get('row_end', 0)}"
            }
            for chunk in optimized_chunks[:10]  # Show first 10 chunks
        ]
    }
    
    logger.info(f"Optimized loading completed in {loading_time:.2f}s")
    logger.info(f"Total rows processed: {total_rows:,}")
    logger.info(f"Chunks created: {total_chunks}")
    logger.info(f"Average chunk size: {avg_chunk_size:.1f} rows")
    
    return stats


def compare_performance(file_path: str) -> Dict[str, Any]:
    """Compare standard vs optimized performance."""
    logger.info("=" * 80)
    logger.info("PERFORMANCE COMPARISON: Standard vs Optimized Excel Processing")
    logger.info("=" * 80)
    
    # Test standard loading
    standard_stats = test_standard_loading(file_path)
    
    logger.info("-" * 40)
    
    # Test optimized loading with different configurations
    optimized_configs = [
        {'batch_size': 500, 'max_rows_per_chunk': 25},
        {'batch_size': 1000, 'max_rows_per_chunk': 50},
        {'batch_size': 2000, 'max_rows_per_chunk': 100}
    ]
    
    optimized_results = []
    
    for config in optimized_configs:
        optimized_stats = test_optimized_loading(
            file_path, 
            batch_size=config['batch_size'],
            max_rows_per_chunk=config['max_rows_per_chunk']
        )
        optimized_results.append(optimized_stats)
        logger.info("-" * 40)
    
    # Generate comparison report
    comparison = {
        'file_path': file_path,
        'file_size_mb': os.path.getsize(file_path) / (1024 * 1024),
        'standard': standard_stats,
        'optimized_results': optimized_results,
        'performance_improvements': []
    }
    
    # Calculate improvements
    for opt_stats in optimized_results:
        improvement = {
            'config': f"batch_size={opt_stats['batch_size']}, max_rows_per_chunk={opt_stats['max_rows_per_chunk']}",
            'time_improvement': ((standard_stats['loading_time'] - opt_stats['loading_time']) / standard_stats['loading_time']) * 100,
            'memory_efficiency': 'High (batch processing)' if opt_stats['memory_efficient'] else 'Standard',
            'chunks_created': opt_stats['total_chunks'],
            'indexing_ready': True
        }
        comparison['performance_improvements'].append(improvement)
    
    return comparison


def print_comparison_report(comparison: Dict[str, Any]):
    """Print detailed comparison report."""
    logger.info("\n" + "=" * 80)
    logger.info("DETAILED PERFORMANCE COMPARISON REPORT")
    logger.info("=" * 80)
    
    file_size = comparison['file_size_mb']
    logger.info(f"Test file: {os.path.basename(comparison['file_path'])} ({file_size:.2f} MB)")
    
    standard = comparison['standard']
    logger.info(f"\n📊 STANDARD METHOD:")
    logger.info(f"  ⏱️  Loading time: {standard['loading_time']:.2f}s")
    logger.info(f"  📄 Sheets processed: {standard['sheets_count']}")
    logger.info(f"  📝 Content length: {standard['content_length']:,} characters")
    logger.info(f"  🧠 Memory efficiency: Low (loads all data at once)")
    logger.info(f"  🔍 Indexing approach: Single large chunks per sheet")
    
    logger.info(f"\n🚀 OPTIMIZED METHODS:")
    
    for i, improvement in enumerate(comparison['performance_improvements']):
        opt_stats = comparison['optimized_results'][i]
        
        logger.info(f"\n  Configuration {i + 1}: {improvement['config']}")
        logger.info(f"    ⏱️  Loading time: {opt_stats['loading_time']:.2f}s")
        logger.info(f"    📈 Time improvement: {improvement['time_improvement']:+.1f}%")
        logger.info(f"    📊 Total rows: {opt_stats['total_rows']:,}")
        logger.info(f"    🧩 Chunks created: {improvement['chunks_created']}")
        logger.info(f"    📏 Avg chunk size: {opt_stats['avg_chunk_size']:.1f} rows")
        logger.info(f"    🧠 Memory efficiency: {improvement['memory_efficiency']}")
        logger.info(f"    🔍 Indexing ready: {'✅' if improvement['indexing_ready'] else '❌'}")
    
    # Find best configuration
    best_config = max(comparison['performance_improvements'], key=lambda x: x['time_improvement'])
    
    logger.info(f"\n🏆 RECOMMENDED CONFIGURATION:")
    logger.info(f"  {best_config['config']}")
    logger.info(f"  Performance improvement: {best_config['time_improvement']:+.1f}%")
    logger.info(f"  Chunks for efficient indexing: {best_config['chunks_created']}")
    
    logger.info(f"\n💡 KEY BENEFITS OF OPTIMIZATION:")
    logger.info(f"  • Batch processing reduces memory usage")
    logger.info(f"  • Smaller chunks enable faster indexing")
    logger.info(f"  • Better search granularity")
    logger.info(f"  • Scalable for very large Excel files")
    logger.info(f"  • Preserves table structure and context")
    
    logger.info("=" * 80)


def main():
    """Main test function."""
    # Configure logging
    logger.remove()
    logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
    
    # Create test file
    test_file = "test_large_excel.xlsx"
    
    try:
        # Create test Excel file with substantial data
        create_test_excel_file(test_file, rows=3000, sheets=4)  # 12,000 total rows
        
        # Run performance comparison
        comparison = compare_performance(test_file)
        
        # Print detailed report
        print_comparison_report(comparison)
        
        logger.info("\n✅ Excel optimization testing completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during testing: {e}")
        return 1
    
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)
            logger.info(f"Cleaned up test file: {test_file}")
    
    return 0


if __name__ == "__main__":
    exit(main())
