import redis.asyncio as redis
import json
import os
from functools import wraps
import numpy as np

redis_client = None

async def init_redis():
    global redis_client
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        redis_client = await redis.from_url(redis_url, decode_responses=True)
        print(f"Redis connected: {redis_url}")
    except Exception as e:
        print(f"Redis connection failed: {e}")
        redis_client = None
    return redis_client

async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()

def cached(expire=3600):
    """Декоратор для кэширования результатов функции в Redis"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if redis_client is None:
                return await func(*args, **kwargs)
            
            import hashlib
            key_str = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            cache_key = hashlib.md5(key_str.encode()).hexdigest()
            
            cached_result = await redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            result = await func(*args, **kwargs)
            await redis_client.setex(cache_key, expire, json.dumps(result, default=str))
            return result
        return wrapper
    return decorator

async def get_cached(key: str):
    if redis_client is None:
        return None
    data = await redis_client.get(key)
    return json.loads(data) if data else None

async def set_cached(key: str, value, expire=3600):
    if redis_client is None:
        return
    await redis_client.setex(key, expire, json.dumps(value, default=str))

async def clear_user_cache(user_id: int):
    if redis_client:
        keys = await redis_client.keys(f"*:{user_id}:*")
        if keys:
            await redis_client.delete(*keys)

# ===== Новые функции для кэширования эмбеддингов =====

async def get_embeddings_cache(gen_id: int, str_id: int):
    """
    Получить кэшированные эмбеддинги деталей из Redis
    Возвращает numpy array или None
    """
    if redis_client is None:
        return None
    
    cache_key = f"embeddings:{gen_id}:{str_id}"
    data = await redis_client.get(cache_key)
    if data:
        try:
            return np.array(json.loads(data))
        except:
            return None
    return None

async def set_embeddings_cache(gen_id: int, str_id: int, embeddings: np.ndarray, expire: int = 604800):
    """
    Сохранить эмбеддинги деталей в Redis
    expire = 604800 секунд (7 дней) — данные TecDoc редко меняются
    """
    if redis_client is None:
        return
    
    cache_key = f"embeddings:{gen_id}:{str_id}"
    data = embeddings.tolist()
    await redis_client.setex(cache_key, expire, json.dumps(data))
    print(f"Эмбеддинги сохранены в Redis: {cache_key}")