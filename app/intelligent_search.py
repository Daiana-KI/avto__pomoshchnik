from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from app.cache import get_embeddings_cache, set_embeddings_cache
import torch

# Загружаем русскоязычную модель (легковесную, работает на CPU)
MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'
_model = None

def lemmatize_text(text: str) -> str:
    """Приводит слова к нормальной форме (лемматизация)"""
    import pymorphy3
    morph = pymorphy3.MorphAnalyzer()
    return ' '.join([morph.parse(word)[0].normal_form for word in text.split()])

def get_model():
    global _model
    if _model is None:
        print("Загрузка модели для интеллектуального поиска...")
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def embed_text(text):
    """Превращает текст в вектор (нормализованный)"""
    model = get_model()
    return model.encode(text, normalize_embeddings=True)

def lemmatized_embed_text(text):
    """
    Применяет лемматизацию к тексту перед вычислением эмбеддинга
    """
    if isinstance(text, str):
        lemmatized = lemmatize_text(text)
        return embed_text(lemmatized)
    elif isinstance(text, list):
        lemmatized_list = [lemmatize_text(t) for t in text]
        return embed_text(lemmatized_list)
    else:
        raise TypeError("text must be str or list")

async def find_relevant_parts(question: str, parts: list, gen_id: int, str_id: int, top_k: int = 8, threshold: float = 0.3) -> list:
    """
    Ищет запчасти, смысл которых близок к вопросу.
    parts: список словарей с ключом 'name' (название детали)
    gen_id, str_id — для кэширования эмбеддингов в Redis
    возвращает: список частей, отсортированных по релевантности
    """
    if not parts:
        return []
    
    # Вектор вопроса (с лемматизацией)
    query_vec = lemmatized_embed_text(question)
    
    # Пытаемся получить эмбеддинги из Redis
    part_vecs = await get_embeddings_cache(gen_id, str_id)
    
    if part_vecs is None:
        # Кэша нет — вычисляем эмбеддинги с лемматизацией
        print(f"Вычисляем эмбеддинги для {len(parts)} деталей...")
        part_names = [p.get('name', '') for p in parts]
        part_vecs = lemmatized_embed_text(part_names)
        
        # Сохраняем в Redis
        await set_embeddings_cache(gen_id, str_id, part_vecs)
        print(f"Эмбеддинги сохранены в Redis для gen_id={gen_id}, str_id={str_id}")
    else:
        print(f"Эмбеддинги загружены из Redis для gen_id={gen_id}, str_id={str_id}")
    
    # Косинусное сходство
    similarities = cosine_similarity([query_vec], part_vecs)[0]
    indices = np.argsort(similarities)[::-1]
    
    result = []
    for i in indices[:top_k]:
        if similarities[i] >= threshold:
            part = parts[i].copy()
            part['similarity'] = float(similarities[i])
            result.append(part)
    
    return result