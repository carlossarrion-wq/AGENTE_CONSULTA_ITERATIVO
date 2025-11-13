"""
Optimized Excel Indexer - High-performance indexing for large Excel files
Integrates with the optimized Excel loader to provide efficient batch indexing
"""

import json
import boto3
from typing import List, Dict, Any, Optional
from loguru import logger
import hashlib
from datetime import datetime
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ingestion.optimized_excel_loader import OptimizedExcelLoader
from src.indexing.multi_app_opensearch_indexer import MultiAppOpenSearchIndexer


class OptimizedExcelIndexer(MultiAppOpenSearchIndexer):
    """
    Optimized Excel indexer that extends the multi-app indexer
    with high-performance Excel processing capabilities.
    """
    
    def __init__(self, app_name: Optional[str] = None, 
                 config_path: str = "config/multi_app_config.yaml",
                 excel_batch_size: int = 1000,
                 excel_max_rows_per_chunk: int = 50):
        """
        Initialize optimized Excel indexer.
        
        Args:
            app_name: Name of the application to index for
            config_path: Path to multi-application configuration
            excel_batch_size: Batch size for Excel processing
            excel_max_rows_per_chunk: Maximum rows per Excel chunk
        """
        # Initialize parent class
        super().__init__(app_name, config_path)
        
        # Initialize optimized Excel loader
        self.excel_loader = OptimizedExcelLoader(
            batch_size=excel_batch_size,
            max_rows_per_chunk=excel_max_rows_per_chunk,
            min_rows_per_chunk=max(5, excel_max_rows_per_chunk // 4),
            include_headers_in_chunks=True,
            preserve_table_structure=True
        )
        
        logger.info(f"OptimizedExcelIndexer initialized for {self.application_info['name']} "
                   f"with Excel batch_size={excel_batch_size}, max_rows_per_chunk={excel_max_rows_per_chunk}")
    
    def index_excel_document_optimized(self, document: Dict[str, Any]) -> bool:
        """
        Index Excel document using optimized batch processing.
        
        Args:
            document: Document dictionary with Excel content
            
        Returns:
            True if indexing successful, False otherwise
        """
        try:
            start_time = time.time()
            
            if not document.get('content'):
                logger.warning(f"No content to index for {document.get('file_name', 'unknown')} in {self.app_name}")
                return False
            
            # Check if document has optimized chunks
            optimized_chunks = document.get('optimized_chunks', [])
            
            if not optimized_chunks:
                logger.warning(f"No optimized chunks found for {document.get('file_name', 'unknown')}, "
                              f"falling back to standard indexing")
                return self.index_document(document)
            
            logger.info(f"Starting optimized Excel indexing for {document.get('file_name', 'unknown')}: "
                       f"{len(optimized_chunks)} chunks")
            
            # Add application metadata to document
            document_metadata = {
                **document.get('metadata', {}),
                'application_id': self.app_name,
                'application_name': self.application_info['name'],
                'indexed_at': datetime.now().isoformat(),
                's3_bucket': self.s3_config['bucket'],
                's3_prefix': self.s3_config.get('documents_prefix', ''),
                'indexing_method': 'optimized_excel_batch',
                'optimization_enabled': True
            }
            
            # Index each optimized chunk
            successful_chunks = 0
            failed_chunks = 0
            
            for chunk_idx, excel_chunk in enumerate(optimized_chunks):
                try:
                    success = self._index_excel_chunk(
                        excel_chunk, document, document_metadata, chunk_idx
                    )
                    
                    if success:
                        successful_chunks += 1
                    else:
                        failed_chunks += 1
                        
                    # Log progress for large files
                    if (chunk_idx + 1) % 100 == 0:
                        progress = ((chunk_idx + 1) / len(optimized_chunks)) * 100
                        logger.info(f"Excel indexing progress: {chunk_idx + 1}/{len(optimized_chunks)} "
                                   f"chunks ({progress:.1f}%) - {successful_chunks} successful, {failed_chunks} failed")
                        
                except Exception as chunk_error:
                    logger.error(f"Error indexing Excel chunk {chunk_idx}: {chunk_error}")
                    failed_chunks += 1
                    continue
            
            processing_time = time.time() - start_time
            
            if successful_chunks > 0:
                logger.info(f"Optimized Excel indexing completed for {document.get('file_name', 'unknown')}: "
                           f"{successful_chunks}/{len(optimized_chunks)} chunks indexed successfully "
                           f"in {processing_time:.2f}s ({failed_chunks} failed)")
                return True
            else:
                logger.error(f"Failed to index any chunks for {document.get('file_name', 'unknown')}")
                return False
                
        except Exception as e:
            logger.error(f"Error in optimized Excel indexing for {document.get('file_name', 'unknown')}: {e}")
            return False
    
    def _index_excel_chunk(self, excel_chunk: Dict[str, Any], 
                          document: Dict[str, Any], 
                          document_metadata: Dict[str, Any],
                          chunk_idx: int) -> bool:
        """
        Index a single Excel chunk.
        
        Args:
            excel_chunk: Excel chunk data
            document: Original document
            document_metadata: Base document metadata
            chunk_idx: Index of the chunk
            
        Returns:
            True if successful, False otherwise
        """
        try:
            chunk_content = excel_chunk.get('content', '')
            chunk_metadata = excel_chunk.get('metadata', {})
            
            if not chunk_content.strip():
                logger.debug(f"Skipping empty Excel chunk {chunk_idx}")
                return False
            
            # Generate unique chunk ID
            chunk_id = f"{self.app_name}_{document['file_hash']}_excel_{chunk_idx}"
            
            # Generate embedding for chunk content
            embedding = self.generate_embedding(chunk_content)
            if not embedding:
                logger.error(f"Failed to generate embedding for Excel chunk {chunk_idx} in {self.app_name}")
                return False
            
            # Merge document metadata with chunk-specific metadata
            merged_metadata = {
                **document_metadata,
                **chunk_metadata,
                "file_size": document.get('file_size', 0),
                "file_extension": document.get('file_extension', ''),
                "total_chunks": len(document.get('optimized_chunks', [])),
                "chunk_processing_method": "optimized_excel_batch",
                "excel_sheet_name": excel_chunk.get('sheet_name', 'unknown'),
                "excel_sheet_index": excel_chunk.get('sheet_index', 0),
                "excel_row_start": excel_chunk.get('row_start', 0),
                "excel_row_end": excel_chunk.get('row_end', 0),
                "excel_row_count": excel_chunk.get('row_count', 0),
                "is_excel_optimized": True
            }
            
            # Prepare document for indexing
            doc_to_index = {
                "content": chunk_content,
                "title": f"{document.get('file_name', '')} - {excel_chunk.get('sheet_name', 'Sheet')}",
                "file_path": document.get('file_path', ''),
                "file_name": document.get('file_name', ''),
                "chunk_id": chunk_id,
                "chunk_index": chunk_idx,
                "embedding": embedding,
                "metadata": merged_metadata,
                "timestamp": datetime.now().isoformat(),
                "document_type": "excel_optimized",
                "has_images": False,
                "image_count": 0,
                # Application fields
                "application_id": self.app_name,
                "application_name": self.application_info['name'],
                "s3_bucket": self.s3_config['bucket'],
                "s3_prefix": self.s3_config.get('documents_prefix', '')
            }
            
            # Index the chunk
            response = self.opensearch_client.index(
                index=self.index_name,
                id=chunk_id,
                body=doc_to_index
            )
            
            # Log detailed information for Excel chunks
            sheet_name = excel_chunk.get('sheet_name', 'unknown')
            row_range = f"{excel_chunk.get('row_start', 0)}-{excel_chunk.get('row_end', 0)}"
            row_count = excel_chunk.get('row_count', 0)
            codes_count = len(merged_metadata.get('technical_codes', []))
            
            logger.debug(f"Indexed Excel chunk {chunk_idx}: sheet '{sheet_name}', "
                        f"rows {row_range} ({row_count} rows), {codes_count} codes")
            
            return True
            
        except Exception as e:
            logger.error(f"Error indexing Excel chunk {chunk_idx}: {e}")
            return False
    
    def index_document(self, document: Dict[str, Any]) -> bool:
        """
        Override parent method to handle Excel files with optimization.
        
        Args:
            document: Document to index
            
        Returns:
            True if indexing successful, False otherwise
        """
        try:
            # Check if this is an Excel file
            file_extension = document.get('file_extension', '').lower()
            
            if file_extension in ['.xlsx', '.xls']:
                # Check if document already has optimized chunks
                if document.get('optimized_chunks'):
                    return self.index_excel_document_optimized(document)
                else:
                    # Apply optimization to existing document
                    logger.info(f"Applying Excel optimization to {document.get('file_name', 'unknown')}")
                    optimized_document = self.excel_loader.load_excel_optimized(
                        document.get('file_path', ''), document
                    )
                    return self.index_excel_document_optimized(optimized_document)
            else:
                # Use parent method for non-Excel files
                return super().index_document(document)
                
        except Exception as e:
            logger.error(f"Error in optimized document indexing: {e}")
            # Fallback to parent method
            return super().index_document(document)
    
    def get_excel_optimization_stats(self) -> Dict[str, Any]:
        """
        Get statistics about Excel optimization performance.
        
        Returns:
            Dictionary with optimization statistics
        """
        try:
            # Query for Excel optimized documents
            search_body = {
                "size": 0,
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"application_id": self.app_name}},
                            {"term": {"document_type": "excel_optimized"}}
                        ]
                    }
                },
                "aggs": {
                    "total_excel_chunks": {
                        "value_count": {"field": "chunk_id"}
                    },
                    "excel_files": {
                        "terms": {"field": "file_name", "size": 100}
                    },
                    "excel_sheets": {
                        "terms": {"field": "metadata.excel_sheet_name", "size": 100}
                    },
                    "avg_rows_per_chunk": {
                        "avg": {"field": "metadata.excel_row_count"}
                    },
                    "total_rows_indexed": {
                        "sum": {"field": "metadata.excel_row_count"}
                    }
                }
            }
            
            response = self.opensearch_client.search(
                index=self.index_name,
                body=search_body
            )
            
            aggs = response.get('aggregations', {})
            
            stats = {
                'application_id': self.app_name,
                'total_excel_chunks': aggs.get('total_excel_chunks', {}).get('value', 0),
                'total_excel_files': len(aggs.get('excel_files', {}).get('buckets', [])),
                'total_excel_sheets': len(aggs.get('excel_sheets', {}).get('buckets', [])),
                'avg_rows_per_chunk': round(aggs.get('avg_rows_per_chunk', {}).get('value', 0), 2),
                'total_rows_indexed': int(aggs.get('total_rows_indexed', {}).get('value', 0)),
                'excel_files': [
                    {
                        'file_name': bucket['key'],
                        'chunks': bucket['doc_count']
                    }
                    for bucket in aggs.get('excel_files', {}).get('buckets', [])
                ],
                'excel_sheets': [
                    {
                        'sheet_name': bucket['key'],
                        'chunks': bucket['doc_count']
                    }
                    for bucket in aggs.get('excel_sheets', {}).get('buckets', [])
                ]
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting Excel optimization stats: {e}")
            return {'error': str(e)}
    
    def reindex_excel_files_optimized(self, file_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Reindex Excel files using optimization.
        
        Args:
            file_paths: Optional list of specific file paths to reindex
            
        Returns:
            Dictionary with reindexing results
        """
        try:
            start_time = time.time()
            
            # If no specific files provided, find all Excel files for this application
            if not file_paths:
                search_body = {
                    "size": 1000,
                    "_source": ["file_path", "file_name"],
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"application_id": self.app_name}},
                                {"terms": {"file_path.keyword": ["*.xlsx", "*.xls"]}}
                            ]
                        }
                    }
                }
                
                response = self.opensearch_client.search(
                    index=self.index_name,
                    body=search_body
                )
                
                file_paths = list(set([
                    hit['_source']['file_path'] 
                    for hit in response['hits']['hits']
                ]))
            
            logger.info(f"Starting optimized reindexing of {len(file_paths)} Excel files")
            
            results = {
                'total_files': len(file_paths),
                'successful_files': 0,
                'failed_files': 0,
                'total_chunks_created': 0,
                'processing_time': 0,
                'errors': []
            }
            
            for file_path in file_paths:
                try:
                    if not os.path.exists(file_path):
                        logger.warning(f"File not found: {file_path}")
                        results['failed_files'] += 1
                        results['errors'].append(f"File not found: {file_path}")
                        continue
                    
                    # Delete existing chunks for this file
                    self._delete_file_chunks(file_path)
                    
                    # Load document with optimization
                    from src.ingestion.document_loader import DocumentLoader
                    doc_loader = DocumentLoader(self.conn_manager, self.config)
                    
                    # Load base document
                    document = doc_loader.load_document(file_path)
                    if not document:
                        results['failed_files'] += 1
                        results['errors'].append(f"Failed to load document: {file_path}")
                        continue
                    
                    # Apply Excel optimization
                    optimized_document = self.excel_loader.load_excel_optimized(file_path, document)
                    
                    # Index optimized document
                    success = self.index_excel_document_optimized(optimized_document)
                    
                    if success:
                        results['successful_files'] += 1
                        chunk_count = len(optimized_document.get('optimized_chunks', []))
                        results['total_chunks_created'] += chunk_count
                        logger.info(f"Successfully reindexed {file_path}: {chunk_count} chunks")
                    else:
                        results['failed_files'] += 1
                        results['errors'].append(f"Failed to index: {file_path}")
                        
                except Exception as file_error:
                    logger.error(f"Error reindexing {file_path}: {file_error}")
                    results['failed_files'] += 1
                    results['errors'].append(f"Error with {file_path}: {str(file_error)}")
            
            results['processing_time'] = time.time() - start_time
            
            logger.info(f"Optimized reindexing completed: {results['successful_files']}/{results['total_files']} "
                       f"files successful, {results['total_chunks_created']} chunks created "
                       f"in {results['processing_time']:.2f}s")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in optimized reindexing: {e}")
            return {'error': str(e)}
    
    def _delete_file_chunks(self, file_path: str):
        """Delete all chunks for a specific file."""
        try:
            delete_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"application_id": self.app_name}},
                            {"term": {"file_path.keyword": file_path}}
                        ]
                    }
                }
            }
            
            response = self.opensearch_client.delete_by_query(
                index=self.index_name,
                body=delete_query
            )
            
            deleted_count = response.get('deleted', 0)
            if deleted_count > 0:
                logger.debug(f"Deleted {deleted_count} existing chunks for {file_path}")
                
        except Exception as e:
            logger.error(f"Error deleting chunks for {file_path}: {e}")


def create_optimized_excel_indexer(app_name: str, 
                                 config_path: str = "config/multi_app_config.yaml",
                                 excel_batch_size: int = 1000,
                                 excel_max_rows_per_chunk: int = 50) -> OptimizedExcelIndexer:
    """
    Factory function to create an optimized Excel indexer.
    
    Args:
        app_name: Name of the application
        config_path: Path to multi-application configuration
        excel_batch_size: Batch size for Excel processing
        excel_max_rows_per_chunk: Maximum rows per Excel chunk
        
    Returns:
        OptimizedExcelIndexer instance
    """
    return OptimizedExcelIndexer(
        app_name=app_name,
        config_path=config_path,
        excel_batch_size=excel_batch_size,
        excel_max_rows_per_chunk=excel_max_rows_per_chunk
    )
