from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pickle
import os

# Загружаем русскоязычную модель (легковесную, работает на CPU)
# Модель кэшируется в памяти после первого вызова
MODEL_NAME = 'intfloat/multilingual-e5-small'  # компактная, быстрая
_model = None

def get_model():
    global _model
    if _model is None:
        print("Загрузка модели для интеллектуального поиска...")
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def embed_text(text: str) -> np.ndarray:
    """Превращает текст в вектор (нормализованный)"""
    model = get_model()
    return model.encode(text, normalize_embeddings=True)

def find_relevant_parts(question: str, parts: list, top_k: int = 5, threshold: float = 0.5) -> list:
    """
    Ищет запчасти, смысл которых близок к вопросу.
    parts: список словарей с ключом 'name' (название детали)
    возвращает: список частей, отсортированных по релевантности
    """
    if not parts:
        return []
    
    # Вектор вопроса
    query_vec = embed_text(question)
    
    # Векторы названий деталей
    part_names = [p.get('name', '') for p in parts]
    part_vecs = embed_text(part_names)  # матрица (len(parts) x dim)
    
    # Косинусное сходство
    similarities = cosine_similarity([query_vec], part_vecs)[0]
    
    # Сортируем по убыванию
    indices = np.argsort(similarities)[::-1]
    
    # Отбираем топ-k, где сходство выше порога
    result = []
    for i in indices[:top_k]:
        if similarities[i] >= threshold:
            part = parts[i].copy()
            part['similarity'] = float(similarities[i])
            result.append(part)
    
    return result