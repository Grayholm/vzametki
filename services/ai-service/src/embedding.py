import logging

from fastembed import TextEmbedding

from src.exceptions import EmbeddingError


logger = logging.getLogger(__name__)


class EmbeddingManager:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self.model = TextEmbedding(model_name=model_name)

    def embed_text(self, text: str) -> list[float]:
        try:
            # fastembed возвращает генератор; достаём первый элемент
            embedding_generator = self.model.embed([text])
            for vector in embedding_generator:
                return vector.tolist()
            raise EmbeddingError("Embedding generator returned no vectors")
        except EmbeddingError:
            raise
        except Exception as exc:
            logger.error("Embedding failed: %s", exc)
            raise EmbeddingError(f"Embedding failed: {exc}") from exc


embedding_manager = EmbeddingManager()