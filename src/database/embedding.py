import logging

from fastembed import TextEmbedding

from src.exceptions import EmbeddingError


logger = logging.getLogger(__name__)


class EmbeddingManager:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self.model = TextEmbedding(model_name=model_name)

    def embed_text(self, text: str) -> list[float]:
        try:
            embedding_generator = self.model.embed([text])
            return next(embedding_generator).tolist()
        except StopIteration as exc:
            logger.error("Embedding model returned empty result")
            raise EmbeddingError("Embedding generator returned no vectors") from exc
        except Exception as exc:
            logger.error("Embedding failed: %s", exc)
            raise EmbeddingError(f"Embedding failed: {exc}") from exc
