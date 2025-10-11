"""Embedding generation service using OpenAI API."""
import logging
import time
from typing import Any

from openai import OpenAI, APIError, RateLimitError

from app.core.config import settings
from app.utils.chunking import TextChunker


logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using OpenAI API."""
    
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
        max_retries: int = 3,
        initial_delay: float = 1.0
    ):
        """Initialize embedding service.
        
        Args:
            model: OpenAI embedding model name
            dimensions: Embedding vector dimensions (1536 for text-embedding-3-small)
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay for exponential backoff (seconds)
        """
        self.model = model
        self.dimensions = dimensions
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
    
    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
            
        Raises:
            ValueError: If text is empty
            APIError: If OpenAI API fails after retries
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Clean and truncate text if needed
        text = text.strip()
        token_count = self.chunker.count_tokens(text)
        
        # OpenAI embedding models support up to 8191 tokens
        if token_count > 8000:
            logger.warning(
                f"Text has {token_count} tokens, truncating to 8000"
            )
            # Encode and truncate
            tokens = self.chunker.encoding.encode(text)[:8000]
            text = self.chunker.encoding.decode(tokens)
        
        # Generate embedding with retry logic
        return self._call_with_retry(lambda: self._generate_embedding(text))
    
    def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 100
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call (max 2048 for OpenAI)
            
        Returns:
            List of embedding vectors
            
        Raises:
            ValueError: If texts list is empty
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")
        
        all_embeddings: list[list[float]] = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Clean batch texts
            cleaned_batch = []
            for text in batch:
                if text and text.strip():
                    cleaned_text = text.strip()
                    token_count = self.chunker.count_tokens(cleaned_text)
                    
                    if token_count > 8000:
                        tokens = self.chunker.encoding.encode(cleaned_text)[:8000]
                        cleaned_text = self.chunker.encoding.decode(tokens)
                    
                    cleaned_batch.append(cleaned_text)
                else:
                    # Empty text - add zero vector
                    logger.warning("Empty text in batch, adding zero vector")
                    all_embeddings.append([0.0] * self.dimensions)
            
            if cleaned_batch:
                # Generate embeddings for batch
                batch_embeddings = self._call_with_retry(
                    lambda: self._generate_batch_embeddings(cleaned_batch)
                )
                all_embeddings.extend(batch_embeddings)
            
            # Rate limiting: small delay between batches
            if i + batch_size < len(texts):
                time.sleep(0.1)
        
        logger.info(
            f"Generated {len(all_embeddings)} embeddings in "
            f"{(len(texts) + batch_size - 1) // batch_size} batches"
        )
        
        return all_embeddings
    
    def _generate_embedding(self, text: str) -> list[float]:
        """Generate single embedding via OpenAI API.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
            dimensions=self.dimensions
        )
        
        return response.data[0].embedding
    
    def _generate_batch_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate multiple embeddings via OpenAI API.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
            dimensions=self.dimensions
        )
        
        # Sort by index to maintain order
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]
    
    def _call_with_retry(
        self,
        func: Any,
    ) -> Any:
        """Execute function with exponential backoff retry logic.
        
        Args:
            func: Function to execute
            
        Returns:
            Function result
            
        Raises:
            APIError: If all retries fail
        """
        delay = self.initial_delay
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return func()
            
            except RateLimitError as e:
                last_error = e
                logger.warning(
                    f"Rate limit hit (attempt {attempt + 1}/{self.max_retries}), "
                    f"waiting {delay}s"
                )
                time.sleep(delay)
                delay *= 2
            
            except APIError as e:
                last_error = e
                # Only retry on 5xx errors (check if status_code exists)
                status_code = getattr(e, 'status_code', None)
                if status_code and 500 <= status_code < 600:
                    logger.warning(
                        f"API error {status_code} (attempt {attempt + 1}/{self.max_retries}), "
                        f"waiting {delay}s"
                    )
                    time.sleep(delay)
                    delay *= 2
                else:
                    # Non-retriable error
                    raise
        
        # All retries failed
        logger.error(f"All {self.max_retries} retries failed")
        if last_error:
            raise last_error
        raise Exception("Embedding generation failed after all retries")


# Default service instance
default_embedding_service = EmbeddingService()
