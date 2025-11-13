"""
Optimized Excel Loader - High-performance processing for large Excel files
Implements batch processing and streaming techniques to handle large Excel files efficiently
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Iterator, Optional, Tuple
from loguru import logger
import hashlib
import os
from io import StringIO
import time


class OptimizedExcelLoader:
    """
    High-performance Excel loader that processes large files in batches
    to avoid memory issues and improve indexing speed.
    """
    
    def __init__(self, 
                 batch_size: int = 1000,
                 max_rows_per_chunk: int = 50,
                 min_rows_per_chunk: int = 10,
                 include_headers_in_chunks: bool = True,
                 preserve_table_structure: bool = True):
        """
        Initialize optimized Excel loader.
        
        Args:
            batch_size: Number of rows to process in each batch
            max_rows_per_chunk: Maximum rows per semantic chunk
            min_rows_per_chunk: Minimum rows per semantic chunk
            include_headers_in_chunks: Include headers in each chunk for context
            preserve_table_structure: Maintain table formatting in chunks
        """
        self.batch_size = batch_size
        self.max_rows_per_chunk = max_rows_per_chunk
        self.min_rows_per_chunk = min_rows_per_chunk
        self.include_headers_in_chunks = include_headers_in_chunks
        self.preserve_table_structure = preserve_table_structure
        
        logger.info(f"OptimizedExcelLoader initialized with batch_size={batch_size}, "
                   f"max_rows_per_chunk={max_rows_per_chunk}")
    
    def load_excel_optimized(self, file_path: str, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load Excel file with optimized batch processing.
        
        Args:
            file_path: Path to Excel file
            document: Base document dictionary
            
        Returns:
            Document with optimized content chunks
        """
        try:
            start_time = time.time()
            
            # Get basic file info
            excel_file = pd.ExcelFile(file_path)
            total_sheets = len(excel_file.sheet_names)
            
            logger.info(f"Processing Excel file: {os.path.basename(file_path)} "
                       f"with {total_sheets} sheets")
            
            # Process each sheet with batch optimization
            all_chunks = []
            sheet_metadata = {}
            
            for sheet_idx, sheet_name in enumerate(excel_file.sheet_names):
                logger.info(f"Processing sheet {sheet_idx + 1}/{total_sheets}: {sheet_name}")
                
                sheet_chunks, sheet_meta = self._process_sheet_optimized(
                    file_path, sheet_name, sheet_idx
                )
                
                all_chunks.extend(sheet_chunks)
                sheet_metadata[sheet_name] = sheet_meta
                
                logger.info(f"Sheet '{sheet_name}' processed: {len(sheet_chunks)} chunks, "
                           f"{sheet_meta['total_rows']} rows")
            
            # Create optimized document structure
            document = self._create_optimized_document(
                document, all_chunks, sheet_metadata, excel_file.sheet_names
            )
            
            processing_time = time.time() - start_time
            logger.info(f"Excel optimization completed in {processing_time:.2f}s: "
                       f"{len(all_chunks)} total chunks from {total_sheets} sheets")
            
            return document
            
        except Exception as e:
            logger.error(f"Error in optimized Excel loading for {file_path}: {e}")
            # Fallback to standard loading
            return self._fallback_load_excel(file_path, document)
    
    def _process_sheet_optimized(self, file_path: str, sheet_name: str, sheet_idx: int) -> Tuple[List[Dict], Dict]:
        """
        Process a single Excel sheet with batch optimization.
        
        Args:
            file_path: Path to Excel file
            sheet_name: Name of the sheet to process
            sheet_idx: Index of the sheet
            
        Returns:
            Tuple of (chunks_list, sheet_metadata)
        """
        try:
            # First, get sheet dimensions by loading the full sheet
            # (We'll optimize memory usage in the chunking process)
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            total_rows = len(df)
            total_columns = len(df.columns)
            
            logger.info(f"Sheet '{sheet_name}': {total_rows} rows x {total_columns} columns")
            
            # If sheet is small, process normally
            if total_rows <= self.max_rows_per_chunk * 2:
                return self._process_small_sheet_direct(df, sheet_name, sheet_idx)
            
            # For large sheets, use batch processing on the loaded DataFrame
            return self._process_large_sheet_batched_df(
                df, sheet_name, sheet_idx, total_rows, total_columns
            )
            
        except Exception as e:
            logger.error(f"Error processing sheet '{sheet_name}': {e}")
            return [], {'error': str(e), 'total_rows': 0, 'total_columns': 0}
    
    def _process_small_sheet_direct(self, df: pd.DataFrame, sheet_name: str, sheet_idx: int) -> Tuple[List[Dict], Dict]:
        """Process small Excel sheet directly from DataFrame."""
        try:
            # Convert to optimized chunks
            chunks = self._dataframe_to_chunks(df, sheet_name, sheet_idx)
            
            metadata = {
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'processing_method': 'small_sheet_direct',
                'chunks_created': len(chunks)
            }
            
            return chunks, metadata
            
        except Exception as e:
            logger.error(f"Error processing small sheet '{sheet_name}': {e}")
            return [], {'error': str(e)}
    
    def _process_large_sheet_batched_df(self, df: pd.DataFrame, sheet_name: str, sheet_idx: int, 
                                      total_rows: int, total_columns: int) -> Tuple[List[Dict], Dict]:
        """Process large Excel sheet using batch processing on DataFrame."""
        try:
            chunks = []
            processed_rows = 0
            batch_count = 0
            
            # Get headers from DataFrame
            headers = df.columns.tolist()
            
            # Process DataFrame in batches
            for start_idx in range(0, total_rows, self.batch_size):
                end_idx = min(start_idx + self.batch_size, total_rows)
                batch_df = df.iloc[start_idx:end_idx]
                batch_count += 1
                batch_rows = len(batch_df)
                
                logger.debug(f"Processing batch {batch_count}: rows {start_idx + 1}-{end_idx}")
                
                # Convert batch to chunks
                batch_chunks = self._dataframe_to_chunks(
                    batch_df, sheet_name, sheet_idx, 
                    batch_offset=start_idx,
                    headers=headers
                )
                
                chunks.extend(batch_chunks)
                processed_rows += batch_rows
                
                # Log progress for very large files
                if processed_rows % (self.batch_size * 10) == 0:
                    progress = (processed_rows / total_rows) * 100
                    logger.info(f"Sheet '{sheet_name}' progress: {processed_rows}/{total_rows} rows ({progress:.1f}%)")
            
            metadata = {
                'total_rows': total_rows,
                'total_columns': total_columns,
                'processing_method': 'large_sheet_batched_df',
                'batches_processed': batch_count,
                'chunks_created': len(chunks),
                'batch_size': self.batch_size
            }
            
            logger.info(f"Completed DataFrame batched processing of '{sheet_name}': "
                       f"{batch_count} batches, {len(chunks)} chunks")
            
            return chunks, metadata
            
        except Exception as e:
            logger.error(f"Error in DataFrame batched processing of sheet '{sheet_name}': {e}")
            return [], {'error': str(e)}

    def _process_large_sheet_batched(self, file_path: str, sheet_name: str, sheet_idx: int, 
                                   total_rows: int, total_columns: int) -> Tuple[List[Dict], Dict]:
        """Process large Excel sheet using batch processing."""
        try:
            chunks = []
            processed_rows = 0
            batch_count = 0
            
            # Get headers first
            headers_df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=1)
            headers = headers_df.columns.tolist()
            
            # Process in batches
            chunk_reader = pd.read_excel(file_path, sheet_name=sheet_name, chunksize=self.batch_size)
            
            for batch_df in chunk_reader:
                batch_count += 1
                batch_rows = len(batch_df)
                
                logger.debug(f"Processing batch {batch_count}: rows {processed_rows + 1}-{processed_rows + batch_rows}")
                
                # Convert batch to chunks
                batch_chunks = self._dataframe_to_chunks(
                    batch_df, sheet_name, sheet_idx, 
                    batch_offset=processed_rows,
                    headers=headers
                )
                
                chunks.extend(batch_chunks)
                processed_rows += batch_rows
                
                # Log progress for very large files
                if processed_rows % (self.batch_size * 10) == 0:
                    progress = (processed_rows / total_rows) * 100
                    logger.info(f"Sheet '{sheet_name}' progress: {processed_rows}/{total_rows} rows ({progress:.1f}%)")
            
            metadata = {
                'total_rows': total_rows,
                'total_columns': total_columns,
                'processing_method': 'large_sheet_batched',
                'batches_processed': batch_count,
                'chunks_created': len(chunks),
                'batch_size': self.batch_size
            }
            
            logger.info(f"Completed batched processing of '{sheet_name}': "
                       f"{batch_count} batches, {len(chunks)} chunks")
            
            return chunks, metadata
            
        except Exception as e:
            logger.error(f"Error in batched processing of sheet '{sheet_name}': {e}")
            return [], {'error': str(e)}
    
    def _dataframe_to_chunks(self, df: pd.DataFrame, sheet_name: str, sheet_idx: int,
                           batch_offset: int = 0, headers: Optional[List[str]] = None) -> List[Dict]:
        """
        Convert DataFrame to optimized chunks.
        
        Args:
            df: DataFrame to process
            sheet_name: Name of the sheet
            sheet_idx: Index of the sheet
            batch_offset: Row offset for batch processing
            headers: Column headers (for batch processing)
            
        Returns:
            List of chunk dictionaries
        """
        if df.empty:
            return []
        
        chunks = []
        total_rows = len(df)
        
        # Use provided headers or get from DataFrame
        if headers is None:
            headers = df.columns.tolist()
        
        # Calculate optimal chunk size based on data
        optimal_chunk_size = self._calculate_optimal_chunk_size(df)
        
        # Split DataFrame into chunks
        for start_idx in range(0, total_rows, optimal_chunk_size):
            end_idx = min(start_idx + optimal_chunk_size, total_rows)
            chunk_df = df.iloc[start_idx:end_idx]
            
            # Create chunk content
            chunk_content = self._create_chunk_content(
                chunk_df, sheet_name, headers, 
                start_idx + batch_offset, end_idx + batch_offset
            )
            
            # Create chunk metadata
            chunk_metadata = self._create_chunk_metadata(
                chunk_df, sheet_name, sheet_idx,
                start_idx + batch_offset, end_idx + batch_offset,
                len(chunks)
            )
            
            chunk = {
                'content': chunk_content,
                'metadata': chunk_metadata,
                'chunk_type': 'excel_table',
                'sheet_name': sheet_name,
                'sheet_index': sheet_idx,
                'row_start': start_idx + batch_offset,
                'row_end': end_idx + batch_offset,
                'row_count': len(chunk_df)
            }
            
            chunks.append(chunk)
        
        return chunks
    
    def _calculate_optimal_chunk_size(self, df: pd.DataFrame) -> int:
        """Calculate optimal chunk size based on DataFrame characteristics."""
        total_rows = len(df)
        total_columns = len(df.columns)
        
        # Base chunk size on data density and structure
        if total_columns <= 5:
            # Few columns - can handle more rows
            base_size = self.max_rows_per_chunk
        elif total_columns <= 15:
            # Medium columns - moderate rows
            base_size = max(self.min_rows_per_chunk, self.max_rows_per_chunk // 2)
        else:
            # Many columns - fewer rows per chunk
            base_size = self.min_rows_per_chunk
        
        # Adjust based on total size
        if total_rows < base_size * 2:
            # Small dataset - keep together
            return total_rows
        
        # Ensure we don't create too many tiny chunks
        min_chunks = max(1, total_rows // self.max_rows_per_chunk)
        optimal_size = max(self.min_rows_per_chunk, total_rows // min_chunks)
        
        return min(optimal_size, self.max_rows_per_chunk)
    
    def _create_chunk_content(self, chunk_df: pd.DataFrame, sheet_name: str, 
                            headers: List[str], start_row: int, end_row: int) -> str:
        """Create formatted content for a chunk."""
        content_parts = []
        
        # Add chunk header with context
        content_parts.append(f"=== HOJA EXCEL: {sheet_name} ===")
        content_parts.append(f"Filas {start_row + 1}-{end_row} de la hoja '{sheet_name}'")
        content_parts.append(f"Columnas: {', '.join(headers)}")
        content_parts.append("")
        
        # Add headers if configured
        if self.include_headers_in_chunks:
            content_parts.append("ENCABEZADOS:")
            content_parts.append(" | ".join(headers))
            content_parts.append("-" * (len(" | ".join(headers))))
        
        # Add data rows with proper formatting
        if self.preserve_table_structure:
            # Use pandas to_string for better formatting
            table_str = chunk_df.to_string(index=False, header=False)
            content_parts.append("DATOS:")
            content_parts.append(table_str)
        else:
            # Simple row-by-row format
            content_parts.append("DATOS:")
            for _, row in chunk_df.iterrows():
                row_values = [str(val) if pd.notna(val) else "" for val in row.values]
                content_parts.append(" | ".join(row_values))
        
        # Add summary
        content_parts.append("")
        content_parts.append(f"Resumen: {len(chunk_df)} filas de datos de la hoja '{sheet_name}'")
        
        return "\n".join(content_parts)
    
    def _create_chunk_metadata(self, chunk_df: pd.DataFrame, sheet_name: str, sheet_idx: int,
                             start_row: int, end_row: int, chunk_index: int) -> Dict[str, Any]:
        """Create metadata for a chunk."""
        # Analyze data types and content
        numeric_columns = chunk_df.select_dtypes(include=[np.number]).columns.tolist()
        text_columns = chunk_df.select_dtypes(include=['object']).columns.tolist()
        date_columns = chunk_df.select_dtypes(include=['datetime']).columns.tolist()
        
        # Calculate statistics
        total_cells = len(chunk_df) * len(chunk_df.columns)
        empty_cells = chunk_df.isnull().sum().sum()
        filled_cells = total_cells - empty_cells
        
        # Extract technical codes and identifiers
        technical_codes = self._extract_codes_from_dataframe(chunk_df)
        
        metadata = {
            'content_type': 'excel_table',
            'sheet_name': sheet_name,
            'sheet_index': sheet_idx,
            'chunk_index': chunk_index,
            'row_start': start_row,
            'row_end': end_row,
            'row_count': len(chunk_df),
            'column_count': len(chunk_df.columns),
            'total_cells': total_cells,
            'filled_cells': filled_cells,
            'empty_cells': empty_cells,
            'fill_percentage': (filled_cells / total_cells) * 100 if total_cells > 0 else 0,
            'numeric_columns': numeric_columns,
            'text_columns': text_columns,
            'date_columns': date_columns,
            'technical_codes': technical_codes,
            'contains_codes': len(technical_codes) > 0,
            'has_structured_data': True,
            'chunk_type': 'excel_optimized',
            'processing_method': 'optimized_batch'
        }
        
        return metadata
    
    def _extract_codes_from_dataframe(self, df: pd.DataFrame) -> List[str]:
        """Extract technical codes from DataFrame content."""
        import re
        
        codes = set()
        
        # Patterns for technical codes
        code_patterns = [
            r'\b[A-Z]{2,3}\d{2,4}\b',  # AC01, Z001, SAP123, etc.
            r'\b[A-Z]+_[A-Z0-9_]+\b',  # SAP_MODULE_CODE, etc.
            r'\b\d{4,6}[A-Z]{1,3}\b',  # 1234AB, 567890C, etc.
            r'\b[A-Z]{1,3}-\d{3,6}\b', # A-1234, AB-567890, etc.
        ]
        
        # Search in all text columns
        for column in df.select_dtypes(include=['object']).columns:
            for value in df[column].dropna():
                value_str = str(value)
                for pattern in code_patterns:
                    matches = re.findall(pattern, value_str)
                    codes.update(matches)
        
        return list(codes)
    
    def _create_optimized_document(self, base_document: Dict[str, Any], 
                                 all_chunks: List[Dict], sheet_metadata: Dict,
                                 sheet_names: List[str]) -> Dict[str, Any]:
        """Create optimized document structure."""
        
        # Create summary content
        total_chunks = len(all_chunks)
        total_rows = sum(meta.get('total_rows', 0) for meta in sheet_metadata.values())
        
        summary_parts = [
            f"=== ARCHIVO EXCEL OPTIMIZADO: {os.path.basename(base_document['file_path'])} ===",
            f"Archivo Excel procesado con optimización de lotes",
            f"Total de hojas: {len(sheet_names)}",
            f"Total de filas: {total_rows:,}",
            f"Total de chunks generados: {total_chunks}",
            "",
            "HOJAS PROCESADAS:"
        ]
        
        for sheet_name in sheet_names:
            meta = sheet_metadata.get(sheet_name, {})
            summary_parts.append(f"  - {sheet_name}: {meta.get('total_rows', 0):,} filas, "
                                f"{meta.get('chunks_created', 0)} chunks")
        
        summary_parts.extend([
            "",
            "Este documento ha sido procesado con técnicas de optimización para archivos Excel grandes.",
            "Los datos están organizados en chunks semánticos que preservan la estructura tabular",
            "y facilitan la búsqueda y recuperación eficiente de información."
        ])
        
        # Update document
        base_document.update({
            'content': '\n'.join(summary_parts),
            'optimized_chunks': all_chunks,
            'metadata': {
                **base_document.get('metadata', {}),
                'sheets': sheet_names,
                'total_sheets': len(sheet_names),
                'total_rows': total_rows,
                'total_chunks': total_chunks,
                'sheet_metadata': sheet_metadata,
                'processing_method': 'optimized_excel_loader',
                'optimization_enabled': True,
                'has_structured_data': True
            }
        })
        
        return base_document
    
    def _fallback_load_excel(self, file_path: str, document: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback to standard Excel loading if optimization fails."""
        logger.warning(f"Using fallback Excel loading for {file_path}")
        
        try:
            excel_file = pd.ExcelFile(file_path)
            content_parts = []

            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                sheet_content = f"--- Hoja: {sheet_name} ---\n"
                sheet_content += df.to_string(index=False)
                content_parts.append(sheet_content)

            document['content'] = '\n\n'.join(content_parts)
            document['metadata']['sheets'] = excel_file.sheet_names
            document['metadata']['total_sheets'] = len(excel_file.sheet_names)
            document['metadata']['processing_method'] = 'fallback_standard'

            return document

        except Exception as e:
            logger.error(f"Error in fallback Excel loading for {file_path}: {e}")
            document['content'] = f"Error loading Excel file: {str(e)}"
            document['metadata']['error'] = str(e)
            return document


def create_optimized_excel_loader(batch_size: int = 1000, 
                                max_rows_per_chunk: int = 50) -> OptimizedExcelLoader:
    """
    Factory function to create an optimized Excel loader.
    
    Args:
        batch_size: Number of rows to process in each batch
        max_rows_per_chunk: Maximum rows per semantic chunk
        
    Returns:
        OptimizedExcelLoader instance
    """
    return OptimizedExcelLoader(
        batch_size=batch_size,
        max_rows_per_chunk=max_rows_per_chunk
    )
