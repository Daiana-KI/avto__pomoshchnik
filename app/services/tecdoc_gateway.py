import httpx
from typing import List, Dict, Optional, Any
from app.intelligent_search import lemmatized_embed_text

class TecDocGateway:
    def __init__(self, api_key: str):
        self.base_url = "https://tecdoc.site/api/v2"
        self.headers = {
            "X-API-KEY": api_key,
            "Accept-Encoding": "gzip"
        }
        self._categories_cache = {}
        self._embeddings_cache = {}

    async def _request(self, path: str, params: Optional[Dict] = None) -> Dict:
        async with httpx.AsyncClient(timeout=30) as client:
            url = f"{self.base_url}{path}"
            resp = await client.get(url, params=params, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def get_manufacturer_id(self, brand: str) -> Optional[int]:
        try:
            data = await self._request("/manufacturer", params={"mfa_type": "PC"})
            brand_lower = brand.lower()
            for item in data.get("data", {}).get("list", []):
                item_brand = item.get("MFA_BRAND", "").lower()
                if brand_lower == item_brand or brand_lower in item_brand or item_brand in brand_lower:
                    return item.get("MFA_ID")
        except Exception as e:
            print(f"TecDoc manufacturer error: {e}")
        return None

    async def get_model_id(self, mfa_id: int, model_name: str, year: int = None) -> Optional[int]:
        try:
            data = await self._request("/model", params={"mfa_id": mfa_id})
            clean_model = model_name.replace("(", "").replace(")", "").replace("_", "").strip().lower()
            words = clean_model.split()
            best_match = None
            best_score = 0
            for item in data.get("data", {}).get("list", []):
                item_name = item.get("NAME", "").lower()
                score = 0
                if clean_model == item_name.replace("(", "").replace(")", "").replace("_", "").strip():
                    score += 10
                elif all(word in item_name for word in words):
                    score += 5
                elif words and words[0] in item_name:
                    score += 3
                if year:
                    date_from = item.get("DATE_FROM")
                    date_to = item.get("DATE_TO")
                    if date_from:
                        try:
                            from_year = int(date_from[:4])
                            to_year = int(date_to[:4]) if date_to else from_year + 10
                            if from_year <= year <= to_year:
                                score += 10
                        except:
                            pass
                if score > best_score:
                    best_score = score
                    best_match = item.get("MS_ID")
            return best_match
        except Exception as e:
            print(f"TecDoc model error: {e}")
        return None

    async def get_generation_id(self, ms_id: int, year: int = None) -> Optional[int]:
        try:
            data = await self._request("/generation", params={"ms_id": ms_id})
            generations = data.get("data", {}).get("list", [])
            if not generations:
                return None
            if year:
                for gen in generations:
                    date_start = gen.get("DATE_START")
                    date_end = gen.get("DATE_END")
                    if date_start:
                        try:
                            start_year = int(date_start[:4])
                            end_year = int(date_end[:4]) if date_end else start_year + 10
                            if start_year <= year <= end_year:
                                return gen.get("GEN_ID") or gen.get("genId")
                        except:
                            pass
                return generations[0].get("GEN_ID") or generations[0].get("genId")
            else:
                return generations[0].get("GEN_ID") or generations[0].get("genId")
        except Exception as e:
            print(f"TecDoc generation error: {e}")
        return None

    async def get_categories(self, gen_id: int) -> List[Dict]:
        if gen_id in self._categories_cache:
            return self._categories_cache[gen_id]
        try:
            data = await self._request("/category", params={"gen_id": gen_id})
            cats = data.get("data", {}).get("list", [])
            self._categories_cache[gen_id] = cats
            return cats
        except Exception as e:
            print(f"TecDoc categories error: {e}")
            return []

    async def get_parts(self, gen_id: int, str_id: int, page: int = 1, per_page: int = 20, with_price_only: bool = False) -> List[Dict]:
        try:
            params = {
                "gen_id": gen_id,
                "str_id": str_id,
                "page": page,
                "per_page": per_page,
            }
            if with_price_only:
                params["with_price_only"] = True
            data = await self._request("/part", params=params)
            items = data.get("data", {}).get("list", [])
            for item in items:
                price = item.get("PRICE") or item.get("price") or None
                if not price and "PRICE_LIST" in item:
                    price_list = item.get("PRICE_LIST", [])
                    if price_list:
                        price = price_list[0].get("PRICE") if isinstance(price_list[0], dict) else price_list[0]
                item["price"] = price
            return items
        except Exception as e:
            print(f"TecDoc parts error: {e}")
            return []

    async def find_categories_with_scores(self, gen_id: int, question: str) -> List[Dict[str, Any]]:
        """Возвращает категории с оценками сходства на основе эмбеддингов."""
        categories = await self.get_categories(gen_id)
        if not categories:
            return []
        cat_names = [cat.get("NAME", "").strip() for cat in categories if cat.get("NAME")]
        if not cat_names:
            return []
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        # Вычисляем эмбеддинг вопроса (с лемматизацией)
        question_embedding = lemmatized_embed_text(question)
        
        if gen_id in self._embeddings_cache:
            embeddings = self._embeddings_cache[gen_id]
        else:
            # Вычисляем эмбеддинги названий категорий (с лемматизацией)
            embeddings = lemmatized_embed_text(cat_names)
            self._embeddings_cache[gen_id] = embeddings
        
        # Косинусное сходство между вопросом и категориями
        similarities = cosine_similarity([question_embedding], embeddings)[0]
        
        results = []
        threshold = 0.25
        for idx, sim in enumerate(similarities):
            if sim >= threshold:
                results.append({
                    "str_id": categories[idx].get("STR_ID"),
                    "name": categories[idx].get("NAME"),
                    "score": float(sim)
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    async def get_vin_info(self, vin: str) -> Optional[Dict]:
        from app.parsers.vin_parser import decode_vin
        vin = vin.upper().strip()
        if len(vin) != 17:
            return None
        car_data = await decode_vin(vin)
        if not car_data:
            print("Не удалось декодировать VIN через carsvin")
            return None
        brand = car_data.get("brand")
        model = car_data.get("model")
        year = car_data.get("year")
        if not brand or not model:
            return None
        mfa_id = await self.get_manufacturer_id(brand)
        if not mfa_id:
            print(f"Марка {brand} не найдена в TecDoc")
            return None
        ms_id = await self.get_model_id(mfa_id, model, year)
        if not ms_id:
            print(f"Модель {model} не найдена в TecDoc")
            return None
        gen_id = await self.get_generation_id(ms_id, year)
        if not gen_id:
            print(f"Поколение для {model} не найдено")
            return None
        print(f"Найден gen_id={gen_id} для {brand} {model} ({year})")
        return {
            "gen_id": gen_id,
            "brand": brand,
            "model": model,
            "year": year,
            "engine": car_data.get("engine")
        }

    def filter_parts_by_side(self, parts: List[Dict], side_keyword: str) -> List[Dict]:
        if not side_keyword:
            return parts
        side_keyword_lower = side_keyword.lower()
        result = []
        for part in parts:
            criteria = part.get("ARTICLE_CRITERIA", [])
            found = False
            for crit in criteria:
                cri_name = crit.get("CRI_NAME", "").lower()
                cri_value = crit.get("CRI_DES", "").lower() or crit.get("CRI_VALUE", "").lower()
                if "сторон" in cri_name or "ось" in cri_name:
                    if side_keyword_lower in cri_value:
                        result.append(part)
                        found = True
                        break
            if not found:
                name = part.get("ART_PRODUCT_NAME", "").lower()
                if side_keyword_lower in name:
                    result.append(part)
        return result if result else parts