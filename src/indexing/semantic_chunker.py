"""
Semantic Chunker - Intelligent chunking with table preservation
Implements semantic chunking that preserves table structures and adds enriched metadata
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from loguru import logger
import pandas as pd
from io import StringIO


class SemanticChunker:
    def __init__(self, chunk_size: int = 4000, chunk_overlap: int = 600, min_chunk_size: int = 250,
                 table_min_rows_per_chunk: int = 5, table_max_rows_per_chunk: int = 20):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.table_min_rows_per_chunk = table_min_rows_per_chunk
        self.table_max_rows_per_chunk = table_max_rows_per_chunk
        
        # Patterns for detecting different content types
        self.table_patterns = [
            # Pipe-separated tables
            r'^\s*\|.*\|.*\|\s*$',
            # Tab-separated tables (multiple tabs)
            r'^\s*[^\t\n]+\t+[^\t\n]+\t+[^\t\n]+.*$',
            # Space-separated columns (3+ columns with consistent spacing)
            r'^\s*\S+\s{2,}\S+\s{2,}\S+.*$',
            # Excel-like table headers
            r'^\s*[A-Za-z][A-Za-z0-9\s]*\s+[A-Za-z][A-Za-z0-9\s]*\s+[A-Za-z][A-Za-z0-9\s]*.*$'
        ]
        
        # Patterns for technical codes
        self.code_patterns = [
            r'\b[A-Z]{2,3}\d{2,4}\b',  # AC01, Z001, SAP123, etc.
            r'\b[A-Z]+_[A-Z0-9_]+\b',  # SAP_MODULE_CODE, etc.
            r'\b\d{4,6}[A-Z]{1,3}\b',  # 1234AB, 567890C, etc.
            r'\b[A-Z]{1,3}-\d{3,6}\b', # A-1234, AB-567890, etc.
        ]
        
        # Content type indicators
        self.content_type_indicators = {
            'table': ['tabla', 'columna', 'fila', 'datos', 'registro', 'campo'],
            'procedure': ['procedimiento', 'proceso', 'paso', 'instrucción', 'método'],
            'code': ['código', 'función', 'variable', 'parámetro', 'configuración'],
            'diagram': ['diagrama', 'esquema', 'flujo', 'gráfico', 'imagen'],
            'reference': ['referencia', 'manual', 'documentación', 'guía']
        }

    def chunk_with_table_preservation(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Main chunking method that preserves table structures
        """
        if not text or len(text.strip()) == 0:
            return []
        
        # Split text into sections
        sections = self._split_into_sections(text)
        
        chunks = []
        current_position = 0
        
        for section in sections:
            section_chunks = self._process_section(section, current_position, metadata or {})
            chunks.extend(section_chunks)
            current_position += len(section['content'])
        
        logger.debug(f"Created {len(chunks)} semantic chunks with table preservation")
        return chunks

    def _split_into_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into logical sections, identifying tables and other content types
        """
        lines = text.split('\n')
        sections = []
        current_section = {'content': '', 'type': 'text', 'lines': []}
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if this line starts a table
            if self._is_table_line(line):
                # Save current section if it has content
                if current_section['content'].strip():
                    sections.append(current_section)
                
                # Process table section
                table_section, lines_consumed = self._extract_table_section(lines, i)
                sections.append(table_section)
                
                # Reset current section
                current_section = {'content': '', 'type': 'text', 'lines': []}
                i += lines_consumed
            else:
                # Add line to current section
                current_section['content'] += line + '\n'
                current_section['lines'].append(line)
                i += 1
        
        # Add final section if it has content
        if current_section['content'].strip():
            sections.append(current_section)
        
        return sections

    def _is_table_line(self, line: str) -> bool:
        """
        Check if a line appears to be part of a table
        """
        if not line.strip():
            return False
        
        for pattern in self.table_patterns:
            if re.match(pattern, line):
                return True
        
        return False

    def _extract_table_section(self, lines: List[str], start_idx: int) -> Tuple[Dict[str, Any], int]:
        """
        Extract a complete table section starting from start_idx with expanded context
        """
        table_lines = []
        i = start_idx
        
        # Look ahead to find the end of the table
        while i < len(lines):
            line = lines[i]
            
            # Empty line might be part of table formatting
            if not line.strip():
                # Check if next non-empty line is still table
                next_table_line = False
                for j in range(i + 1, min(i + 3, len(lines))):
                    if j < len(lines) and lines[j].strip():
                        if self._is_table_line(lines[j]):
                            next_table_line = True
                        break
                
                if next_table_line:
                    table_lines.append(line)
                    i += 1
                else:
                    break
            elif self._is_table_line(line):
                table_lines.append(line)
                i += 1
            else:
                break
        
        # Include expanded context lines before and after table
        context_before = []
        context_after = []
        
        # Get 5-8 lines before table for expanded context (including explanatory paragraphs)
        context_start = max(0, start_idx - 8)
        for j in range(context_start, start_idx):
            if j >= 0 and j < len(lines):
                line = lines[j].strip()
                if line:
                    context_before.append(lines[j])
                elif context_before:  # Include empty lines between content
                    context_before.append(lines[j])
        
        # Get 5-8 lines after table for expanded context (including examples and explanations)
        context_end = min(len(lines), i + 8)
        for j in range(i, context_end):
            if j < len(lines):
                line = lines[j].strip()
                if line:
                    context_after.append(lines[j])
                elif context_after and j < context_end - 1:  # Include empty lines between content
                    context_after.append(lines[j])
        
        # Build complete table content with expanded context
        full_content = '\n'.join(context_before + table_lines + context_after)
        
        table_section = {
            'content': full_content,
            'type': 'table',
            'lines': context_before + table_lines + context_after,
            'table_lines': table_lines,
            'context_before': context_before,
            'context_after': context_after
        }
        
        return table_section, i - start_idx

    def _process_section(self, section: Dict[str, Any], position: int, base_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a section into chunks with appropriate metadata
        """
        content = section['content']
        section_type = section['type']
        
        if section_type == 'table':
            # For small tables with rich context, treat as regular text to maintain narrative flow
            # Only create separate table chunks for large tables or tables without sufficient context
            table_lines = section.get('table_lines', [])
            context_before = section.get('context_before', [])
            context_after = section.get('context_after', [])
            
            # If table is small and has good context, treat as regular text chunk
            if (len(table_lines) <= 10 and 
                len(context_before) >= 2 and 
                len(context_after) >= 2 and 
                len(content) <= self.chunk_size):
                
                logger.debug(f"Processing small table with context as regular text chunk")
                return self._create_text_chunks(content, position, base_metadata)
            else:
                # Large tables or tables without context get special treatment
                return self._create_table_chunk(section, position, base_metadata)
        else:
            # Regular text chunking with semantic boundaries
            return self._create_text_chunks(content, position, base_metadata)

    def _create_table_chunk(self, table_section: Dict[str, Any], position: int, base_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create chunks for a table, grouping multiple rows together for better context
        """
        content = table_section['content']
        table_lines = table_section.get('table_lines', [])
        context_before = table_section.get('context_before', [])
        context_after = table_section.get('context_after', [])
        
        # Analyze table structure
        table_analysis = self._analyze_table_structure(table_lines)
        
        # Detect technical codes in table
        codes_found = self._extract_technical_codes(content)
        
        # If table is small enough, keep it as one chunk
        if len(table_lines) <= self.table_max_rows_per_chunk:
            enhanced_metadata = {
                **base_metadata,
                'content_type': 'table',
                'contains_codes': len(codes_found) > 0,
                'technical_codes': codes_found,
                'table_headers': table_analysis.get('headers', []),
                'table_rows_count': table_analysis.get('row_count', 0),
                'table_columns_count': table_analysis.get('column_count', 0),
                'table_format': table_analysis.get('format', 'unknown'),
                'has_structured_data': True,
                'chunk_type': 'table_complete',
                'preservation_method': 'table_intact'
            }
            
            chunk = {
                'text': content,
                'metadata': enhanced_metadata,
                'chunk_index': 0,
                'position': position,
                'length': len(content),
                'chunk_type': 'table'
            }
            
            logger.debug(f"Created single table chunk with {table_analysis.get('row_count', 0)} rows and {len(codes_found)} technical codes")
            return [chunk]
        
        # For large tables, split into multiple chunks with row grouping
        chunks = []
        chunk_index = 0
        
        # Determine header rows (usually first 1-2 rows)
        header_rows = table_lines[:min(2, len(table_lines))]
        data_rows = table_lines[min(2, len(table_lines)):]
        
        # Split data rows into groups
        rows_per_chunk = min(self.table_max_rows_per_chunk, max(self.table_min_rows_per_chunk, len(data_rows) // 5))
        
        for i in range(0, len(data_rows), rows_per_chunk):
            chunk_data_rows = data_rows[i:i + rows_per_chunk]
            
            # Build chunk content with context
            chunk_lines = []
            
            # Add context before (only for first chunk)
            if i == 0 and context_before:
                chunk_lines.extend(context_before)
            
            # Add headers to each chunk for context
            chunk_lines.extend(header_rows)
            
            # Add data rows for this chunk
            chunk_lines.extend(chunk_data_rows)
            
            # Add context after (only for last chunk)
            if i + rows_per_chunk >= len(data_rows) and context_after:
                chunk_lines.extend(context_after)
            
            chunk_content = '\n'.join(chunk_lines)
            
            # Analyze codes in this chunk
            chunk_codes = self._extract_technical_codes(chunk_content)
            
            enhanced_metadata = {
                **base_metadata,
                'content_type': 'table',
                'contains_codes': len(chunk_codes) > 0,
                'technical_codes': chunk_codes,
                'table_headers': table_analysis.get('headers', []),
                'table_rows_count': len(chunk_data_rows),
                'table_total_rows': len(table_lines),
                'table_chunk_index': chunk_index,
                'table_chunk_start_row': i + len(header_rows),
                'table_chunk_end_row': i + len(header_rows) + len(chunk_data_rows),
                'table_columns_count': table_analysis.get('column_count', 0),
                'table_format': table_analysis.get('format', 'unknown'),
                'has_structured_data': True,
                'chunk_type': 'table_partial',
                'preservation_method': 'table_grouped'
            }
            
            chunk = {
                'text': chunk_content,
                'metadata': enhanced_metadata,
                'chunk_index': chunk_index,
                'position': position + sum(len(line) for line in chunk_lines[:i]),
                'length': len(chunk_content),
                'chunk_type': 'table'
            }
            
            chunks.append(chunk)
            chunk_index += 1
        
        logger.debug(f"Created {len(chunks)} table chunks from {len(table_lines)} rows ({rows_per_chunk} rows per chunk)")
        
        return chunks

    def _analyze_table_structure(self, table_lines: List[str]) -> Dict[str, Any]:
        """
        Analyze the structure of a table to extract metadata
        """
        if not table_lines:
            return {}
        
        analysis = {
            'row_count': len(table_lines),
            'column_count': 0,
            'headers': [],
            'format': 'unknown'
        }
        
        # Try to detect table format and extract headers
        first_line = table_lines[0] if table_lines else ""
        
        if '|' in first_line:
            # Pipe-separated table
            analysis['format'] = 'pipe_separated'
            headers = [col.strip() for col in first_line.split('|') if col.strip()]
            analysis['headers'] = headers
            analysis['column_count'] = len(headers)
        elif '\t' in first_line:
            # Tab-separated table
            analysis['format'] = 'tab_separated'
            headers = [col.strip() for col in first_line.split('\t') if col.strip()]
            analysis['headers'] = headers
            analysis['column_count'] = len(headers)
        else:
            # Space-separated or other format
            analysis['format'] = 'space_separated'
            # Try to detect columns by consistent spacing
            words = first_line.split()
            analysis['column_count'] = len(words)
            analysis['headers'] = words[:5]  # Take first 5 as potential headers
        
        return analysis

    def _create_text_chunks(self, content: str, position: int, base_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create chunks for regular text content with semantic boundaries and minimum size enforcement
        """
        # Filter out very small content that doesn't meet minimum requirements
        if len(content.strip()) < self.min_chunk_size:
            if not self._is_valid_chunk(content):
                logger.debug(f"Skipping chunk smaller than minimum size ({len(content)} < {self.min_chunk_size})")
                return []
        
        if len(content) <= self.chunk_size:
            # Content fits in single chunk, but check if it meets minimum requirements
            if len(content.strip()) >= self.min_chunk_size and self._is_valid_chunk(content):
                enhanced_metadata = self._enhance_metadata(content, base_metadata)
                return [{
                    'text': content,
                    'metadata': enhanced_metadata,
                    'chunk_index': 0,
                    'position': position,
                    'length': len(content),
                    'chunk_type': 'text'
                }]
            else:
                logger.debug(f"Skipping single chunk that doesn't meet quality requirements")
                return []
        
        # Split into multiple chunks with semantic boundaries and minimum size enforcement
        chunks = []
        paragraphs = self._split_into_paragraphs(content)
        
        current_chunk = ""
        current_position = position
        chunk_index = 0
        
        for paragraph in paragraphs:
            # Check if adding this paragraph would exceed chunk size
            if len(current_chunk) + len(paragraph) > self.chunk_size and current_chunk:
                # Only create chunk if it meets minimum size and quality requirements
                if len(current_chunk.strip()) >= self.min_chunk_size and self._is_valid_chunk(current_chunk):
                    enhanced_metadata = self._enhance_metadata(current_chunk, base_metadata)
                    enhanced_metadata['chunk_index'] = chunk_index
                    
                    chunks.append({
                        'text': current_chunk.strip(),
                        'metadata': enhanced_metadata,
                        'chunk_index': chunk_index,
                        'position': current_position,
                        'length': len(current_chunk),
                        'chunk_type': 'text'
                    })
                    chunk_index += 1
                else:
                    logger.debug(f"Skipping chunk that doesn't meet minimum requirements: {len(current_chunk)} chars")
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk, self.chunk_overlap)
                current_chunk = overlap_text + paragraph
                current_position += len(current_chunk) - len(overlap_text)
            else:
                current_chunk += paragraph
        
        # Add final chunk if there's remaining content and it meets requirements
        if current_chunk.strip() and len(current_chunk.strip()) >= self.min_chunk_size and self._is_valid_chunk(current_chunk):
            enhanced_metadata = self._enhance_metadata(current_chunk, base_metadata)
            enhanced_metadata['chunk_index'] = chunk_index
            
            chunks.append({
                'text': current_chunk.strip(),
                'metadata': enhanced_metadata,
                'chunk_index': chunk_index,
                'position': current_position,
                'length': len(current_chunk),
                'chunk_type': 'text'
            })
        elif current_chunk.strip():
            logger.debug(f"Skipping final chunk that doesn't meet requirements: {len(current_chunk)} chars")
        
        return chunks

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs, preserving semantic boundaries.
        This is less aggressive than sentence splitting and creates larger chunks.
        """
        # First try to split by double newlines (paragraph breaks)
        paragraphs = text.split('\n\n')
        
        # If no paragraph breaks found, try single newlines but group them
        if len(paragraphs) <= 1:
            lines = text.split('\n')
            paragraphs = []
            current_paragraph = ""
            
            for line in lines:
                current_paragraph += line + '\n'
                # Group lines into larger paragraphs (every 3-5 lines)
                if len(current_paragraph.split('\n')) >= 4:
                    paragraphs.append(current_paragraph)
                    current_paragraph = ""
            
            # Add remaining content
            if current_paragraph.strip():
                paragraphs.append(current_paragraph)
        
        # Filter out empty paragraphs and ensure minimum content
        result = []
        for paragraph in paragraphs:
            if paragraph.strip() and len(paragraph.strip()) > 50:  # Minimum paragraph size
                result.append(paragraph)
        
        return result

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences, preserving semantic boundaries
        """
        # Split by sentence endings, but keep the punctuation
        sentences = re.split(r'([.!?]+\s+)', text)
        
        # Recombine sentences with their punctuation
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            if sentence.strip():
                result.append(sentence)
        
        # If no sentence boundaries found, split by paragraphs
        if len(result) <= 1:
            paragraphs = text.split('\n\n')
            result = [p + '\n\n' for p in paragraphs if p.strip()]
        
        return result

    def _is_valid_chunk(self, chunk: str) -> bool:
        """
        Validate if a chunk contains meaningful content and should be indexed.
        Filters out chunks that are too small, contain only codes, or lack semantic value.
        """
        content = chunk.strip()
        
        # Too short
        if len(content) < 50:
            return False
        
        # Only version codes (V5 M1, V6 M1, etc.)
        if re.match(r'^V\d+\s*M\d+$', content):
            return False
        
        # Only "role sales agent" or similar single phrases
        if content.lower() in ['role sales agent', 'sales agent', 'agent']:
            return False
        
        # Only numbers or codes without context
        words = content.split()
        if len(words) < 5:  # Less than 5 words is probably not meaningful
            return False
        
        # Check for meaningful content (at least some words longer than 3 characters)
        meaningful_words = [w for w in words if len(w) > 3 and not w.isdigit() and not re.match(r'^[A-Z0-9_-]+$', w)]
        if len(meaningful_words) < 3:
            return False
        
        # Check for at least one verb or descriptive content
        # Simple heuristic: look for common Spanish verbs or descriptive words
        descriptive_indicators = [
            'es', 'son', 'tiene', 'contiene', 'permite', 'realiza', 'ejecuta', 'procesa',
            'sistema', 'aplicación', 'módulo', 'proceso', 'función', 'servicio',
            'información', 'datos', 'documento', 'archivo', 'registro',
            'usuario', 'cliente', 'agente', 'operador'
        ]
        
        content_lower = content.lower()
        has_descriptive_content = any(indicator in content_lower for indicator in descriptive_indicators)
        
        if not has_descriptive_content:
            return False
        
        return True

    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """
        Get the last overlap_size characters from text, trying to break at word boundaries
        """
        if len(text) <= overlap_size:
            return text
        
        overlap_text = text[-overlap_size:]
        
        # Try to break at word boundary
        space_idx = overlap_text.find(' ')
        if space_idx > 0:
            overlap_text = overlap_text[space_idx + 1:]
        
        return overlap_text

    def _enhance_metadata(self, content: str, base_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance metadata with content analysis
        """
        enhanced = {**base_metadata}
        
        # Detect technical codes
        codes_found = self._extract_technical_codes(content)
        enhanced['contains_codes'] = len(codes_found) > 0
        enhanced['technical_codes'] = codes_found
        
        # Detect content type
        content_type = self._detect_content_type(content)
        enhanced['content_type'] = content_type
        
        # Detect module/system references
        module = self._detect_module(content)
        if module:
            enhanced['module'] = module
        
        # Add semantic indicators
        enhanced['has_structured_data'] = self._has_structured_data(content)
        enhanced['chunk_method'] = 'semantic'
        
        return enhanced

    def _extract_technical_codes(self, text: str) -> List[str]:
        """
        Extract technical codes from text using predefined patterns
        """
        codes = set()
        
        for pattern in self.code_patterns:
            matches = re.findall(pattern, text)
            codes.update(matches)
        
        return list(codes)

    def _detect_content_type(self, content: str) -> str:
        """
        Detect the type of content based on keywords and patterns
        """
        content_lower = content.lower()
        
        # Count indicators for each type
        type_scores = {}
        for content_type, indicators in self.content_type_indicators.items():
            score = sum(1 for indicator in indicators if indicator in content_lower)
            if score > 0:
                type_scores[content_type] = score
        
        # Return type with highest score, default to 'text'
        if type_scores:
            return max(type_scores.items(), key=lambda x: x[1])[0]
        
        return 'text'

    def _detect_module(self, content: str) -> Optional[str]:
        """
        Detect which module/system the content refers to
        """
        content_upper = content.upper()
        
        # Module indicators
        modules = {
            'DARWIN': ['DARWIN', 'SISTEMA DARWIN'],
            'SAP': ['SAP', 'SISTEMA SAP', 'ERP']
        }
        
        for module, indicators in modules.items():
            if any(indicator in content_upper for indicator in indicators):
                return module
        
        return None

    def _has_structured_data(self, content: str) -> bool:
        """
        Check if content contains structured data patterns
        """
        # Check for list patterns, numbered items, etc.
        patterns = [
            r'^\s*\d+\.\s+',  # Numbered lists
            r'^\s*[-*]\s+',   # Bullet points
            r'^\s*[A-Za-z]\)\s+',  # Lettered lists
            r':\s*$',         # Key-value patterns
        ]
        
        lines = content.split('\n')
        structured_lines = 0
        
        for line in lines:
            for pattern in patterns:
                if re.match(pattern, line):
                    structured_lines += 1
                    break
        
        # If more than 20% of lines are structured, consider it structured data
        return structured_lines > len(lines) * 0.2
