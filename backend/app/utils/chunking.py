"""Text chunking utilities for splitting documents into embeddings."""
import logging
from typing import Any

import tiktoken


logger = logging.getLogger(__name__)


class TextChunker:
    """Utility for chunking text into smaller pieces for embedding."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        encoding_name: str = "cl100k_base"
    ):
        """Initialize text chunker.
        
        Args:
            chunk_size: Target size of each chunk in tokens
            chunk_overlap: Number of tokens to overlap between chunks
            encoding_name: Tokenizer encoding name (default: cl100k_base for GPT-4/3.5-turbo)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding = tiktoken.get_encoding(encoding_name)
    
    def chunk_text(
        self,
        text: str,
        metadata: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Split text into chunks with metadata.
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk
            
        Returns:
            List of dicts with 'text' and 'metadata' keys
        """
        if not text or not text.strip():
            return []
        
        # Tokenize text
        tokens = self.encoding.encode(text)
        total_tokens = len(tokens)
        
        # Handle very short texts
        if total_tokens <= self.chunk_size:
            return [{
                "text": text,
                "metadata": {
                    **(metadata or {}),
                    "chunk_index": 0,
                    "total_chunks": 1,
                    "token_count": total_tokens
                }
            }]
        
        chunks = []
        chunk_index = 0
        start = 0
        
        while start < total_tokens:
            # Calculate end position
            end = start + self.chunk_size
            
            # Get chunk tokens
            chunk_tokens = tokens[start:end]
            
            # Decode tokens back to text
            chunk_text = self.encoding.decode(chunk_tokens)
            
            # Try to find a good boundary (sentence end)
            if end < total_tokens:
                chunk_text = self._adjust_chunk_boundary(chunk_text)
            
            # Add chunk with metadata
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    **(metadata or {}),
                    "chunk_index": chunk_index,
                    "token_count": len(chunk_tokens),
                    "start_char": len(self.encoding.decode(tokens[:start])),
                    "end_char": len(self.encoding.decode(tokens[:end]))
                }
            })
            
            chunk_index += 1
            
            # Move start position (with overlap)
            start = end - self.chunk_overlap
        
        # Add total_chunks to all metadata
        for chunk in chunks:
            chunk["metadata"]["total_chunks"] = len(chunks)
        
        logger.debug(
            f"Chunked text into {len(chunks)} chunks "
            f"({total_tokens} tokens total)"
        )
        
        return chunks
    
    def _adjust_chunk_boundary(self, text: str) -> str:
        """Adjust chunk boundary to end at sentence if possible.
        
        Args:
            text: Chunk text
            
        Returns:
            Adjusted chunk text
        """
        # Try to find last sentence end
        sentence_ends = [". ", "! ", "? ", ".\n", "!\n", "?\n"]
        
        for end_marker in sentence_ends:
            last_pos = text.rfind(end_marker)
            if last_pos > len(text) * 0.7:  # Only adjust if sentence is near end
                return text[:last_pos + len(end_marker)].strip()
        
        # Try to find last paragraph break
        last_para = text.rfind("\n\n")
        if last_para > len(text) * 0.7:
            return text[:last_para].strip()
        
        # Try to find last newline
        last_newline = text.rfind("\n")
        if last_newline > len(text) * 0.7:
            return text[:last_newline].strip()
        
        # Return as-is if no good boundary found
        return text.strip()
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))
    
    def chunk_document(
        self,
        document: dict[str, Any],
        text_field: str = "text",
        metadata_fields: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Chunk a document dictionary.
        
        Args:
            document: Document dict with text and metadata
            text_field: Key for text field in document
            metadata_fields: List of keys to include in chunk metadata
            
        Returns:
            List of chunks with text and metadata
        """
        text = document.get(text_field, "")
        
        # Build metadata from specified fields
        metadata = {}
        if metadata_fields:
            for field in metadata_fields:
                if field in document:
                    metadata[field] = document[field]
        
        return self.chunk_text(text, metadata=metadata)


# Default chunker instance
default_chunker = TextChunker(
    chunk_size=1000,
    chunk_overlap=200
)


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> list[str]:
    """Convenience function to chunk text.
    
    Args:
        text: Text to chunk
        chunk_size: Target chunk size in tokens
        chunk_overlap: Overlap size in tokens
        
    Returns:
        List of text chunks
    """
    chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = chunker.chunk_text(text)
    return [chunk["text"] for chunk in chunks]
