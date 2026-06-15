# app/services/api_gateway.py
import httpx
import json
import numpy as np
from typing import List, Dict, Optional
from app.intelligent_search import embed_text, cosine_similarity
from app.cache import redis_client
from app.parsers.vin_parser import decode_vin

TECDOC_API_KEY = "01186691560aa5dbda9f7be1c2dcc7ec"  # ключ TecDoc
BASE_URL = "https://api.tecdoc.net/v1"  # официальный URL TecDoc API

class APIGateway:
    def __init__(self):
        self.base_url = BASE_URL

    async def _call_tecdoc(self, method: str, params: Dict) -> Dict:
        params["method"] = method
        params["key"] = TECDOC_API_KEY
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(self.base_url, params=params)
            resp.raise_for_status()
            return resp.json()

    async def _get_car_id(self, vin: str) -> Optional[str]:
        """carId из VINdecode"""
        data = await self._call_tecdoc("VINdecode", {"vin": vin, "lang": "ru"})
        if data.get("statusMsg") == "Success":
            result = data.get("result", {})
            if result:
                return next(iter(result.values())).get("carId")
        return None

    async def _get_parts_tree(self, car_id: str) -> List[Dict]:
        cache_key = f"tecdoc_tree:{car_id}"
        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        tree = await self._call_tecdoc("getSearchTree", {"carId": car_id, "carType": "PC", "lang": "ru"})
        if isinstance(tree, list):
            await redis_client.setex(cache_key, 86400, json.dumps(tree))
            return tree
        return []

    async def _find_cat(self, question: str, car_id: str) -> Optional[str]:
        """Определяет cat по смыслу вопроса через эмбеддинги"""
        tree = await self._get_parts_tree(car_id)
        names, ids = [], []
        for node in tree:
            for level in ("NODE_1_TEXT", "NODE_2_TEXT", "NODE_3_TEXT"):
                name = node.get(level)
                if name:
                    names.append(name)
                    ids.append(node.get(level.replace("TEXT", "STR_ID")))
        if not names:
            return None
        q_emb = embed_text([question])[0]
        name_embs = embed_text(names)
        sim = cosine_similarity([q_emb], name_embs)[0]
        best_idx = int(np.argmax(sim))
        if sim[best_idx] >= 0.3:
            return str(ids[best_idx])
        return None

    async def search_parts_by_vin(self, vin: str, question: str, user_id: int) -> List[Dict]:
        # Загрузка контекста (последние 3 вопроса)
        context_key = f"dialog:{user_id}"
        last = await redis_client.lrange(context_key, -3, -1)
        if last:
            question = " ".join(last) + " " + question

        car_id = await self._get_car_id(vin)
        if not car_id:
            return []
        cat = await self._find_cat(question, car_id)
        if not cat:
            return []

        data = await self._call_tecdoc("getPartsbyVIN", {"vin": vin, "type": "oem", "cat": cat, "lang": "ru"})
        if not isinstance(data, list):
            return []

        parts = []
        for item in data:
            parts_str = item.get("parts")
            if parts_str:
                tokens = parts_str.split("|")
                for i in range(0, len(tokens)-1, 2):
                    parts.append({
                        "name": item.get("shortname") or item.get("name", ""),
                        "article": tokens[i+1],
                        "manufacturer": tokens[i]
                    })
        await redis_client.rpush(context_key, question)
        await redis_client.expire(context_key, 600)
        return parts