from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── База продуктов: калории и БЖУ на 100 г ───────────────────────

FOOD_DB: dict[str, dict[str, float]] = {
    # Первые блюда
    "борщ": {"calories_per_100g": 49, "protein": 1.5, "fat": 2.2, "carbs": 5.5},
    "щи": {"calories_per_100g": 34, "protein": 1.3, "fat": 1.5, "carbs": 3.8},
    "суп": {"calories_per_100g": 40, "protein": 1.5, "fat": 1.8, "carbs": 4.5},
    "суп куриный": {"calories_per_100g": 36, "protein": 2.0, "fat": 1.5, "carbs": 3.0},
    "бульон": {"calories_per_100g": 15, "protein": 1.0, "fat": 0.5, "carbs": 1.5},
    "окрошка": {"calories_per_100g": 42, "protein": 1.8, "fat": 1.5, "carbs": 5.5},
    "солянка": {"calories_per_100g": 55, "protein": 3.5, "fat": 3.0, "carbs": 3.0},
    "пюре суп": {"calories_per_100g": 50, "protein": 1.5, "fat": 2.5, "carbs": 5.0},
    "том ям": {"calories_per_100g": 40, "protein": 2.0, "fat": 2.0, "carbs": 3.5},
    "харчо": {"calories_per_100g": 55, "protein": 3.0, "fat": 3.0, "carbs": 3.5},
    # Гарниры
    "рис": {"calories_per_100g": 130, "protein": 2.7, "fat": 0.3, "carbs": 28.0},
    "рис варёный": {"calories_per_100g": 130, "protein": 2.7, "fat": 0.3, "carbs": 28.0},
    "гречка": {"calories_per_100g": 132, "protein": 4.5, "fat": 2.3, "carbs": 25.0},
    "гречка варёная": {"calories_per_100g": 110, "protein": 4.2, "fat": 1.6, "carbs": 21.0},
    "макароны": {"calories_per_100g": 157, "protein": 5.5, "fat": 1.8, "carbs": 30.0},
    "макароны варёные": {"calories_per_100g": 131, "protein": 4.5, "fat": 1.2, "carbs": 27.0},
    "паста": {"calories_per_100g": 157, "protein": 5.5, "fat": 1.8, "carbs": 30.0},
    "картофель": {"calories_per_100g": 82, "protein": 2.0, "fat": 0.4, "carbs": 17.0},
    "картошка": {"calories_per_100g": 82, "protein": 2.0, "fat": 0.4, "carbs": 17.0},
    "картофель варёный": {"calories_per_100g": 82, "protein": 2.0, "fat": 0.4, "carbs": 17.0},
    "картофельное пюре": {"calories_per_100g": 106, "protein": 2.5, "fat": 4.0, "carbs": 15.0},
    "овсянка": {"calories_per_100g": 88, "protein": 3.0, "fat": 1.7, "carbs": 15.0},
    "каша": {"calories_per_100g": 110, "protein": 3.5, "fat": 2.0, "carbs": 20.0},
    "киноа": {"calories_per_100g": 120, "protein": 4.4, "fat": 1.9, "carbs": 21.0},
    "булгур": {"calories_per_100g": 83, "protein": 3.1, "fat": 0.2, "carbs": 18.6},
    "кускус": {"calories_per_100g": 112, "protein": 3.8, "fat": 0.2, "carbs": 23.0},
    "плов": {"calories_per_100g": 150, "protein": 5.0, "fat": 6.0, "carbs": 20.0},
    "спагетти": {"calories_per_100g": 157, "protein": 5.5, "fat": 1.8, "carbs": 30.0},
    "лапша": {"calories_per_100g": 138, "protein": 4.5, "fat": 1.5, "carbs": 28.0},
    # Мясо и птица
    "курица": {"calories_per_100g": 165, "protein": 31.0, "fat": 3.6, "carbs": 0.0},
    "куриная грудка": {"calories_per_100g": 110, "protein": 23.6, "fat": 1.9, "carbs": 0.4},
    "куриная грудка варёная": {"calories_per_100g": 137, "protein": 29.8, "fat": 1.8, "carbs": 0.0},
    "куриная грудка жареная": {"calories_per_100g": 165, "protein": 27.0, "fat": 6.0, "carbs": 0.0},
    "куриное бедро": {"calories_per_100g": 185, "protein": 21.0, "fat": 11.0, "carbs": 0.0},
    "куриные ножки": {"calories_per_100g": 185, "protein": 20.0, "fat": 11.0, "carbs": 0.0},
    "куриное крылышко": {"calories_per_100g": 239, "protein": 20.0, "fat": 17.0, "carbs": 0.0},
    "курица гриль": {"calories_per_100g": 195, "protein": 25.0, "fat": 10.0, "carbs": 0.0},
    "говядина": {"calories_per_100g": 250, "protein": 26.0, "fat": 16.0, "carbs": 0.0},
    "говядина тушёная": {"calories_per_100g": 220, "protein": 22.0, "fat": 14.0, "carbs": 1.0},
    "свинина": {"calories_per_100g": 242, "protein": 17.0, "fat": 19.0, "carbs": 0.0},
    "котлета": {"calories_per_100g": 220, "protein": 14.0, "fat": 15.0, "carbs": 12.0},
    "котлета куриная": {"calories_per_100g": 190, "protein": 16.0, "fat": 10.0, "carbs": 10.0},
    "тефтели": {"calories_per_100g": 180, "protein": 12.0, "fat": 10.0, "carbs": 10.0},
    "гуляш": {"calories_per_100g": 180, "protein": 16.0, "fat": 10.0, "carbs": 5.0},
    "шашлык": {"calories_per_100g": 230, "protein": 20.0, "fat": 16.0, "carbs": 0.0},
    "индейка": {"calories_per_100g": 130, "protein": 23.0, "fat": 3.5, "carbs": 0.0},
    "печень": {"calories_per_100g": 130, "protein": 20.0, "fat": 4.5, "carbs": 2.0},
    "фарш": {"calories_per_100g": 254, "protein": 17.0, "fat": 20.0, "carbs": 0.0},
    "сосиска": {"calories_per_100g": 266, "protein": 11.0, "fat": 24.0, "carbs": 1.6},
    "сарделька": {"calories_per_100g": 215, "protein": 11.0, "fat": 18.0, "carbs": 1.5},
    "колбаса": {"calories_per_100g": 300, "protein": 12.0, "fat": 28.0, "carbs": 1.0},
    "бекон": {"calories_per_100g": 417, "protein": 16.0, "fat": 39.0, "carbs": 0.0},
    "ветчина": {"calories_per_100g": 270, "protein": 14.0, "fat": 24.0, "carbs": 0.5},
    # Рыба и морепродукты
    "рыба": {"calories_per_100g": 150, "protein": 20.0, "fat": 7.0, "carbs": 0.0},
    "лосось": {"calories_per_100g": 208, "protein": 20.0, "fat": 13.0, "carbs": 0.0},
    "семга": {"calories_per_100g": 208, "protein": 20.0, "fat": 13.0, "carbs": 0.0},
    "тунец": {"calories_per_100g": 132, "protein": 29.0, "fat": 1.3, "carbs": 0.0},
    "треска": {"calories_per_100g": 78, "protein": 17.0, "fat": 0.7, "carbs": 0.0},
    "минтай": {"calories_per_100g": 72, "protein": 15.9, "fat": 0.9, "carbs": 0.0},
    "тилапия": {"calories_per_100g": 96, "protein": 20.1, "fat": 1.7, "carbs": 0.0},
    "скумбрия": {"calories_per_100g": 191, "protein": 18.0, "fat": 13.0, "carbs": 0.0},
    "сельдь": {"calories_per_100g": 217, "protein": 19.0, "fat": 15.0, "carbs": 0.0},
    "креветки": {"calories_per_100g": 99, "protein": 24.0, "fat": 0.3, "carbs": 0.2},
    "кальмар": {"calories_per_100g": 100, "protein": 18.0, "fat": 2.2, "carbs": 2.0},
    # Яйца и молочные
    "яйцо": {"calories_per_100g": 155, "protein": 13.0, "fat": 11.0, "carbs": 1.1},
    "яйцо варёное": {"calories_per_100g": 155, "protein": 13.0, "fat": 11.0, "carbs": 1.1},
    "яичница": {"calories_per_100g": 196, "protein": 14.0, "fat": 15.0, "carbs": 0.7},
    "омлет": {"calories_per_100g": 154, "protein": 10.6, "fat": 12.0, "carbs": 0.7},
    "молоко": {"calories_per_100g": 52, "protein": 2.8, "fat": 2.5, "carbs": 4.7},
    "молоко 200мл": {"calories_per_100g": 52, "protein": 2.8, "fat": 2.5, "carbs": 4.7},
    "кефир": {"calories_per_100g": 40, "protein": 3.0, "fat": 1.0, "carbs": 4.0},
    "йогурт": {"calories_per_100g": 66, "protein": 5.0, "fat": 2.0, "carbs": 7.0},
    "творог": {"calories_per_100g": 120, "protein": 17.0, "fat": 5.0, "carbs": 1.8},
    "сыр": {"calories_per_100g": 350, "protein": 25.0, "fat": 27.0, "carbs": 0.0},
    "сметана": {"calories_per_100g": 206, "protein": 2.8, "fat": 20.0, "carbs": 3.2},
    "сливки": {"calories_per_100g": 206, "protein": 2.5, "fat": 20.0, "carbs": 3.5},
    "масло сливочное": {"calories_per_100g": 748, "protein": 0.5, "fat": 82.5, "carbs": 0.8},
    # Хлеб и выпечка
    "хлеб": {"calories_per_100g": 265, "protein": 9.0, "fat": 3.2, "carbs": 49.0},
    "хлеб белый": {"calories_per_100g": 265, "protein": 9.0, "fat": 3.2, "carbs": 49.0},
    "хлеб чёрный": {"calories_per_100g": 215, "protein": 7.0, "fat": 1.2, "carbs": 43.0},
    "хлеб ржаной": {"calories_per_100g": 174, "protein": 5.5, "fat": 1.2, "carbs": 36.0},
    "булка": {"calories_per_100g": 310, "protein": 8.0, "fat": 6.0, "carbs": 54.0},
    "батон": {"calories_per_100g": 265, "protein": 9.0, "fat": 3.2, "carbs": 49.0},
    "лаваш": {"calories_per_100g": 236, "protein": 7.9, "fat": 1.0, "carbs": 47.6},
    "круассан": {"calories_per_100g": 406, "protein": 8.2, "fat": 21.0, "carbs": 45.0},
    "блин": {"calories_per_100g": 233, "protein": 6.1, "fat": 12.3, "carbs": 26.0},
    "блины": {"calories_per_100g": 233, "protein": 6.1, "fat": 12.3, "carbs": 26.0},
    "пирожок": {"calories_per_100g": 260, "protein": 6.0, "fat": 12.0, "carbs": 32.0},
    # Овощи
    "салат": {"calories_per_100g": 20, "protein": 1.2, "fat": 0.3, "carbs": 3.0},
    "салат овощной": {"calories_per_100g": 50, "protein": 1.5, "fat": 3.0, "carbs": 5.0},
    "огурец": {"calories_per_100g": 15, "protein": 0.8, "fat": 0.1, "carbs": 2.8},
    "помидор": {"calories_per_100g": 20, "protein": 0.6, "fat": 0.2, "carbs": 4.2},
    "капуста": {"calories_per_100g": 27, "protein": 1.3, "fat": 0.1, "carbs": 5.4},
    "морковь": {"calories_per_100g": 41, "protein": 0.9, "fat": 0.2, "carbs": 9.6},
    "картошка фри": {"calories_per_100g": 312, "protein": 3.4, "fat": 15.0, "carbs": 41.0},
    "овощи гриль": {"calories_per_100g": 70, "protein": 2.0, "fat": 4.0, "carbs": 6.0},
    "винегрет": {"calories_per_100g": 76, "protein": 1.5, "fat": 4.5, "carbs": 7.5},
    # Фрукты
    "банан": {"calories_per_100g": 96, "protein": 1.5, "fat": 0.5, "carbs": 21.0},
    "яблоко": {"calories_per_100g": 52, "protein": 0.3, "fat": 0.2, "carbs": 14.0},
    "апельсин": {"calories_per_100g": 47, "protein": 0.9, "fat": 0.1, "carbs": 12.0},
    "груша": {"calories_per_100g": 57, "protein": 0.4, "fat": 0.1, "carbs": 15.0},
    # Напитки
    "кофе": {"calories_per_100g": 2, "protein": 0.1, "fat": 0.0, "carbs": 0.3},
    "кофе с молоком": {"calories_per_100g": 37, "protein": 1.5, "fat": 1.5, "carbs": 4.0},
    "капучино": {"calories_per_100g": 37, "protein": 1.8, "fat": 1.5, "carbs": 4.0},
    "латте": {"calories_per_100g": 44, "protein": 2.0, "fat": 1.8, "carbs": 4.8},
    "чай": {"calories_per_100g": 1, "protein": 0.0, "fat": 0.0, "carbs": 0.3},
    "сок": {"calories_per_100g": 47, "protein": 0.5, "fat": 0.2, "carbs": 11.0},
    "апельсиновый сок": {"calories_per_100g": 45, "protein": 0.7, "fat": 0.2, "carbs": 10.4},
    "яблочный сок": {"calories_per_100g": 46, "protein": 0.1, "fat": 0.1, "carbs": 11.3},
    "лимонад": {"calories_per_100g": 40, "protein": 0.0, "fat": 0.0, "carbs": 10.0},
    "кола": {"calories_per_100g": 42, "protein": 0.0, "fat": 0.0, "carbs": 10.6},
    "пиво": {"calories_per_100g": 43, "protein": 0.3, "fat": 0.0, "carbs": 3.6},
    "вино": {"calories_per_100g": 82, "protein": 0.1, "fat": 0.0, "carbs": 2.6},
    # Десерты и снеки
    "шоколад": {"calories_per_100g": 546, "protein": 7.0, "fat": 31.0, "carbs": 59.0},
    "мороженое": {"calories_per_100g": 207, "protein": 3.5, "fat": 11.0, "carbs": 24.0},
    "печенье": {"calories_per_100g": 417, "protein": 7.5, "fat": 12.0, "carbs": 70.0},
    "торт": {"calories_per_100g": 350, "protein": 5.0, "fat": 18.0, "carbs": 44.0},
    "конфета": {"calories_per_100g": 400, "protein": 3.0, "fat": 10.0, "carbs": 75.0},
    "чипсы": {"calories_per_100g": 536, "protein": 7.0, "fat": 34.0, "carbs": 49.0},
    "орехи": {"calories_per_100g": 607, "protein": 20.0, "fat": 54.0, "carbs": 16.0},
    "арахис": {"calories_per_100g": 567, "protein": 26.0, "fat": 49.0, "carbs": 16.0},
    "миндаль": {"calories_per_100g": 579, "protein": 21.0, "fat": 50.0, "carbs": 22.0},
    "сухофрукты": {"calories_per_100g": 280, "protein": 3.0, "fat": 0.5, "carbs": 68.0},
    "изюм": {"calories_per_100g": 299, "protein": 3.1, "fat": 0.5, "carbs": 79.0},
    "мёд": {"calories_per_100g": 304, "protein": 0.3, "fat": 0.0, "carbs": 82.0},
    # Фастфуд
    "бургер": {"calories_per_100g": 295, "protein": 17.0, "fat": 14.0, "carbs": 24.0},
    "пицца": {"calories_per_100g": 266, "protein": 11.0, "fat": 10.0, "carbs": 33.0},
    "суши": {"calories_per_100g": 143, "protein": 5.5, "fat": 2.5, "carbs": 24.0},
    "роллы": {"calories_per_100g": 150, "protein": 6.0, "fat": 3.0, "carbs": 24.0},
    "шаурма": {"calories_per_100g": 185, "protein": 10.0, "fat": 8.0, "carbs": 18.0},
    "хот-дог": {"calories_per_100g": 270, "protein": 11.0, "fat": 18.0, "carbs": 18.0},
    "наггетсы": {"calories_per_100g": 296, "protein": 15.0, "fat": 18.0, "carbs": 17.0},
    "чебурек": {"calories_per_100g": 276, "protein": 11.0, "fat": 16.0, "carbs": 22.0},
    # Соусы
    "майонез": {"calories_per_100g": 680, "protein": 1.0, "fat": 75.0, "carbs": 2.6},
    "кетчуп": {"calories_per_100g": 112, "protein": 1.7, "fat": 0.5, "carbs": 25.0},
    "соевый соус": {"calories_per_100g": 53, "protein": 8.1, "fat": 0.0, "carbs": 4.9},
}


def find_food(name: str) -> Optional[dict[str, float]]:
    """Ищет продукт в базе по имени (точное + частичное совпадение)."""
    key = name.strip().lower()

    # Точное совпадение
    if key in FOOD_DB:
        return FOOD_DB[key]

    # Частичное совпадение — ищем ключ, содержащий имя
    best_match: Optional[dict[str, float]] = None
    best_len = 0
    for db_key, db_val in FOOD_DB.items():
        if key in db_key or db_key in key:
            if len(db_key) > best_len:
                best_match = db_val
                best_len = len(db_key)

    return best_match


def calculate_meal(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Рассчитывает калории и БЖУ по списку продуктов.

    Args:
        items: [{"name": "борщ", "grams": 250}, ...]

    Returns:
        {"calories": 122.5, "protein": 3.75, "fat": 5.5, "carbs": 13.75,
         "description": "борщ 250г", "items_detail": [...]}
    """
    total = {
        "calories": 0.0,
        "protein": 0.0,
        "fat": 0.0,
        "carbs": 0.0,
    }
    items_detail: list[dict[str, Any]] = []

    for item in items:
        name = item.get("name", "").strip().lower()
        grams = float(item.get("grams", 0))
        confidence = item.get("confidence", 1.0)

        food = find_food(name)
        if food is None:
            logger.warning(f"Продукт не найден в базе: {name}")
            items_detail.append({
                "name": item.get("name", name),
                "grams": grams,
                "found": False,
                "confidence": confidence,
            })
            continue

        factor = grams / 100.0
        item_calories = food["calories_per_100g"] * factor
        item_protein = food["protein"] * factor
        item_fat = food["fat"] * factor
        item_carbs = food["carbs"] * factor

        total["calories"] += item_calories
        total["protein"] += item_protein
        total["fat"] += item_fat
        total["carbs"] += item_carbs

        items_detail.append({
            "name": item.get("name", name),
            "grams": grams,
            "calories": round(item_calories, 1),
            "protein": round(item_protein, 1),
            "fat": round(item_fat, 1),
            "carbs": round(item_carbs, 1),
            "found": True,
            "confidence": confidence,
        })

    # Округляем итог
    for key in total:
        total[key] = round(total[key], 1)

    # Формируем описание
    desc_parts = [item.get("name", "продукт") for item in items if item.get("grams", 0) > 0]
    description = ", ".join(desc_parts) if desc_parts else "Приём пищи"

    total["description"] = description
    total["items_detail"] = items_detail

    logger.info(f"Расчёт meals: {len(items)} продуктов → {total['calories']} ккал")
    for d in items_detail:
        if d.get("found"):
            logger.info(f"  ✅ {d['name']} {d['grams']}г → {d['calories']} ккал")
        else:
            logger.info(f"  ❌ {d['name']} {d['grams']}г — не найдено в базе")

    return total
