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
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            # Получаем весь видимый текст
            text = soup.get_text(separator='\n')
            
            # Отладочный вывод: первые 4000 символов
            print("=== НАЧАЛО ТЕКСТА СТРАНИЦЫ (4000 символов) ===")
            print(text[:4000])
            print("=== КОНЕЦ ОТЛАДОЧНОГО ВЫВОДА ===")

            car_info = {
                "brand": "",
                "model": "",
                "year": None,
                "engine": "",
                "transmission": "",
                "drive": ""
            }

            # Марка из заголовка или из текста
            title = soup.title.string if soup.title else ""
            m = re.search(r'марки\s+([А-ЯA-Z]+)', title, re.IGNORECASE)
            if m:
                car_info["brand"] = m.group(1)
            else:
                m = re.search(r'марки\s+([А-ЯA-Z]+)', text, re.IGNORECASE)
                if m:
                    car_info["brand"] = m.group(1)

            # Модель: ищем фразу "Наименование модели автомобиля: значение"
            m = re.search(r'Наименование модели автомобиля:\s*([^\n]+)', text, re.IGNORECASE)
            if m:
                car_info["model"] = m.group(1).strip()

            # Год: ищем "Начали производство: ... 2019"
            m = re.search(r'Начали производство:\s*.*?(\b(19|20)\d{2}\b)', text, re.IGNORECASE)
            if m:
                car_info["year"] = int(m.group(1))

            # Двигатель: "Тип движка в ТС: ..."
            m = re.search(r'Тип движка в ТС:\s*([^\n]+)', text, re.IGNORECASE)
            if m:
                car_info["engine"] = m.group(1).strip()

            # Привод: "Привод у авто: ..."
            m = re.search(r'Привод у авто:\s*([^\n]+)', text, re.IGNORECASE)
            if m:
                car_info["drive"] = m.group(1).strip()

            # Если марка найдена, возвращаем результат
            if car_info["brand"]:
                print(f"Парсинг успешен: {car_info}")
                return car_info
            else:
                print("Марка не найдена")
                return None

        except Exception as e:
            print(f"Ошибка: {e}")
            return None