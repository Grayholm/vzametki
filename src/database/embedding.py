from fastembed import TextEmbedding


class EmbeddingManager:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self.model = TextEmbedding(model_name=model_name)

    def embed_text(self, text: str) -> list[float]:
        # Создается генератор для получения вектора, так как embed может возвращать генератор для больших текстов
        embedding_generator = self.model.embed([text])

        # Получаем первый (и единственный) вектор из генератора и преобразуем его в список
        return next(embedding_generator).tolist()