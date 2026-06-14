# app/parsers/vin_parser.py
import httpx
from bs4 import BeautifulSoup
from typing import Optional, Dict
import re

async def decode_vin(vin: str) -> Optional[Dict]:
    vin = vin.upper().strip()
    if len(vin) != 17:
        print(f"Ошибка: VIN '{vin}' имеет неверную длину.")
        return None

    url = f"https://carsvin.ru/auto/vin?vincode={vin}"
    print(f"Запрос к carsvin: {url}")

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = await client.get(url, headers=headers)
            print(f"Статус ответа: {response.status_code}")

            if response.status_code != 200:
                print(f"carsvin вернул {response.status_code}, пробуем резервный NHTSA")
                return await decode_vin_nhtsa(vin)

            soup = BeautifulSoup(response.text, 'html.parser')
            car_info = {"brand": "", "model": "", "year": None, "engine": "", "transmission": "", "drive": ""}

            # Ищем таблицу с данными по VIN
            vin_data_table = soup.find('table', id='placeholder')
            if not vin_data_table:
                print("Не удалось найти таблицу с данными VIN, пробуем резервный вариант")
                return await decode_vin_nhtsa(vin)

            # Проходим по всем строкам таблицы и ищем нужные данные
            for row in vin_data_table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)

                    if "марка" in label or "наименование идентификатора марки" in label:
                        car_info["brand"] = value
                    elif "модель" in label:
                        car_info["model"] = value
                    elif "год" in label or "начали производство" in label:
                        # Ищем год в виде 4 цифр
                        year_match = re.search(r'\b(19|20)\d{2}\b', value)
                        if year_match:
                            car_info["year"] = int(year_match.group())
                    elif "двигатель" in label or "тип движка" in label:
                        car_info["engine"] = value
                    elif "привод" in label:
                        car_info["drive"] = value

            # Если данные не найдены – fallback
            if not car_info["brand"] or not car_info["model"]:
                print(f"Не удалось извлечь марку/модель из таблицы, пробуем NHTSA")
                print(f"Извлечённые данные: {car_info}")
                return await decode_vin_nhtsa(vin)

            print(f"Успешно распарсено: {car_info}")
            return car_info

        except Exception as e:
            print(f"Ошибка при парсинге carsvin: {e}")
            return await decode_vin_nhtsa(vin)


async def decode_vin_nhtsa(vin: str) -> Optional[Dict]:
    """Резервный декодер через NHTSA (если carsvin не помог)"""
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json"
    print(f"Запрос к NHTSA: {url}")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url)
            data = response.json()
            result = {}
            for item in data.get("Results", []):
                var = item.get("Variable")
                val = item.get("Value")
                if var in ["Make", "Model", "Model Year", "Engine", "Drive Type", "Transmission Style"]:
                    result[var] = val

            year_str = result.get("Model Year", "")
            year = None
            if year_str and year_str.isdigit():
                year = int(year_str)

            return {
                "brand": result.get("Make", ""),
                "model": result.get("Model", ""),
                "year": year,
                "engine": result.get("Engine", ""),
                "transmission": result.get("Transmission Style", ""),
                "drive": result.get("Drive Type", ""),
            }
        except Exception as e:
            print(f"Ошибка NHTSA: {e}")
            return None