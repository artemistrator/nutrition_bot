"""
meal_confirm.py — подтверждение, редактирование и сохранение приёма пищи.

Router с высоким приоритом (регистрируется ПЕРВЫМ в handlers/__init__.py).
Перехватывает callback-кнопки и текст во время редактирования.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database import add_meal, get_user
from services.nutrition import MealAnalysis
from services.nutrition_db import FOOD_DB, calculate_meal, find_food

logger = logging.getLogger(__name__)

router = Router(name="meal_confirm")


# ── FSM states ────────────────────────────────────────────────────

class MealConfirmState(StatesGroup):
    awaiting_confirmation = State()
    awaiting_edit = State()


# ── Draft storage key ─────────────────────────────────────────────

def _draft_key(user_id: int) -> str:
    return f"meal_draft:{user_id}"


# ── Inline keyboards ──────────────────────────────────────────────

def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Сохранить", callback_data="meal:save"),
                InlineKeyboardButton(text="✏️ Изменить", callback_data="meal:edit"),
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="meal:cancel"),
            ],
        ]
    )


def _saved_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Сохранить как шаблон", callback_data="meal:save_template")],
        ]
    )


# ── Formatting ────────────────────────────────────────────────────

def _format_meal_preview(structure: dict, meal_calc: dict) -> str:
    """Формирует текст карточки приёма пищи."""
    lines = ["🍽 **Я нашёл:**\n"]

    for item in structure.get("items", []):
        name = item.get("name", "?")
        grams = item.get("grams", 0)
        confidence = item.get("confidence", 1.0)
        marker = " ⚠️" if confidence < 0.7 else ""
        lines.append(f"• {name} — {grams:.0f} г{marker}")

    # Ненайденные продукты
    not_found = [d for d in meal_calc.get("items_detail", []) if not d.get("found")]
    if not_found:
        lines.append("\n⚠️ **Не удалось точно найти:**")
        for nf in not_found:
            lines.append(f"• {nf['name']} ({nf['grams']:.0f} г)")
        lines.append("\nНажми ✏️ Изменить чтобы исправить.")

    lines.append(f"\n**Итого:**")
    lines.append(f"🔥 {meal_calc['calories']:.0f} ккал")
    lines.append(f"Б: {meal_calc['protein']:.1f} г | Ж: {meal_calc['fat']:.1f} г | У: {meal_calc['carbs']:.1f} г")

    return "\n".join(lines)


# ── Edit logic ────────────────────────────────────────────────────

@dataclass
class EditCommand:
    action: str  # "upsert" | "remove" | "add"
    name: str
    grams: Optional[float] = None


_GRAMS_PATTERN = re.compile(
    r"^(?P<name>.+?)"
    r"(?:\s*(?:=|-)\s*|\s+)"
    r"(?P<grams>\d+(?:[.,]\d+)?)"
    r"\s*(?:г|гр|грамм|грамма|граммов)?\s*$",
    re.IGNORECASE,
)
_DELETE_PATTERN = re.compile(r"^(?:удали|delete)\s+(.+)$", re.IGNORECASE)
_SPACE_PATTERN = re.compile(r"\s+")


def _edit_examples() -> str:
    return (
        "Примеры:\n"
        "• `булочки 60`\n"
        "• `булочки = 60`\n"
        "• `- хлеб`\n"
        "• `+ яблоко 120`"
    )


def _edit_parse_error(reason: Optional[str] = None) -> str:
    lines = ["Не получилось разобрать правку."]
    if reason:
        lines.append(reason)
    lines.append("")
    lines.append(_edit_examples())
    return "\n".join(lines)


def _normalize_edit_input(text: str) -> str:
    text = text.strip()
    text = text.replace("\u00A0", " ")
    for old, new in {
        "—": "-",
        "–": "-",
        "−": "-",
        "«": "",
        "»": "",
        "“": "",
        "”": "",
    }.items():
        text = text.replace(old, new)
    return _SPACE_PATTERN.sub(" ", text).strip()


def _name_key(text: str) -> str:
    text = _normalize_edit_input(text).casefold().replace("-", " ")
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return _SPACE_PATTERN.sub(" ", text).strip()


def _find_exact_item_matches(items: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    query_key = _name_key(name)
    if not query_key:
        return []
    return [item for item in items if _name_key(item.get("name", "")) == query_key]


def _find_item_matches(items: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    query_key = _name_key(name)
    if not query_key:
        return []

    exact_matches = _find_exact_item_matches(items, name)
    if exact_matches:
        return exact_matches

    matches = []
    for item in items:
        item_key = _name_key(item.get("name", ""))
        if query_key and (query_key in item_key or item_key in query_key):
            matches.append(item)
    return matches


def _format_ambiguous_matches(matches: list[dict[str, Any]]) -> str:
    names = [f"«{item.get('name', '?')}»" for item in matches[:5]]
    suffix = "..." if len(matches) > 5 else ""
    return f"Нашёл несколько похожих продуктов: {', '.join(names)}{suffix}. Уточни название."


def parse_edit_command(text: str) -> tuple[Optional[EditCommand], Optional[str]]:
    """Парсит команду редактирования.

    Поддерживаемые форматы:
    - борщ=300 / борщ 300 / борщ - 300 / борщ — 300 г
    - -хлеб / - хлеб / удали хлеб / delete хлеб
    - +яблоко=120 / + яблоко 120
    - яблоко=120 / яблоко 120 → upsert
    """
    text = _normalize_edit_input(text)
    if not text:
        return None, _edit_parse_error("Сообщение пустое.")

    # Удаление: -название / удали название / delete название
    delete_match = _DELETE_PATTERN.match(text)
    if delete_match:
        name = delete_match.group(1).strip()
        if name:
            return EditCommand(action="remove", name=name), None
        return None, _edit_parse_error("Не вижу название продукта для удаления.")

    if text.startswith("-"):
        name = text[1:].strip()
        if name:
            return EditCommand(action="remove", name=name), None
        return None, _edit_parse_error("Не вижу название продукта для удаления.")

    # Добавление: +название=граммы / + название 120
    action = "upsert"
    if text.startswith("+"):
        action = "add"
        text = text[1:].strip()
        if not text:
            return None, _edit_parse_error("После `+` укажи продукт и граммы.")

    match = _GRAMS_PATTERN.match(text)
    if match:
        name = match.group("name").strip(" -")
        grams_raw = match.group("grams").replace(",", ".")
        if not name:
            return None, _edit_parse_error("Не вижу название продукта.")

        grams = float(grams_raw)
        if grams <= 0:
            return None, _edit_parse_error("Граммы должны быть больше нуля.")
        return EditCommand(action=action, name=name, grams=grams), None

    if re.search(r"\d", text) is None:
        return None, _edit_parse_error("Нужно указать граммы.")

    return None, _edit_parse_error()


def apply_meal_edit(structure: dict, edit_text: str) -> tuple[dict, Optional[str]]:
    """Применяет правку к структуре еды.

    Returns:
        (updated_structure, error_message_or_None)
    """
    cmd, parse_error = parse_edit_command(edit_text)
    if cmd is None:
        return structure, parse_error or _edit_parse_error()

    items: list[dict[str, Any]] = structure.get("items", [])

    if cmd.action == "remove":
        matches = _find_item_matches(items, cmd.name)
        if not matches:
            return structure, f"Продукт «{cmd.name}» не найден в списке."
        if len(matches) > 1:
            return structure, _format_ambiguous_matches(matches)

        target = matches[0]
        new_items = [item for item in items if item is not target]
        structure = {**structure, "items": new_items}

    elif cmd.action == "upsert":
        matches = _find_item_matches(items, cmd.name)
        if len(matches) > 1:
            return structure, _format_ambiguous_matches(matches)

        if matches:
            target = matches[0]
            target["grams"] = cmd.grams
            target["source"] = target.get("source", "llm")
        else:
            items.append({
                "name": cmd.name,
                "grams": cmd.grams,
                "confidence": 1.0,
                "source": "manual",
            })
            structure = {**structure, "items": items}

    elif cmd.action == "add":
        exact_matches = _find_exact_item_matches(items, cmd.name)
        if exact_matches:
            return structure, (
                f"Продукт «{exact_matches[0].get('name', cmd.name)}» уже есть в списке. "
                "Напиши без `+`, чтобы изменить граммы."
            )

        items.append({
            "name": cmd.name,
            "grams": cmd.grams,
            "confidence": 1.0,
            "source": "manual",
        })
        structure = {**structure, "items": items}

    return structure, None


# ── Handlers ──────────────────────────────────────────────────────

@router.callback_query(F.data == "meal:save")
async def handle_save(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None:
        return

    draft = await state.get_data()
    structure = draft.get("structure")

    if not structure:
        await callback.answer("Черновик не найден", show_alert=True)
        await state.clear()
        await callback.message.answer("Черновик не найден. Отправь еду заново.")
        return

    # Рассчитываем
    meal_calc = calculate_meal(structure.get("items", []))
    meal = MealAnalysis(
        description=meal_calc["description"],
        calories=meal_calc["calories"],
        protein=meal_calc["protein"],
        fat=meal_calc["fat"],
        carbs=meal_calc["carbs"],
    )

    source_label = draft.get("source_label", "Еда")

    # Сохраняем в БД
    if callback.message is not None:
        user_id = callback.from_user.id
        await add_meal(
            user_id=user_id,
            description=meal.description,
            calories=meal.calories,
            protein=meal.protein,
            fat=meal.fat,
            carbs=meal.carbs,
        )

        await callback.message.answer(
            f"{source_label}: запись добавлена ✅\n\n"
            f"🍽 **{meal.description}**\n"
            f"🔥 {meal.calories:.0f} ккал\n"
            f"Б: {meal.protein:.1f} г | Ж: {meal.fat:.1f} г | У: {meal.carbs:.1f} г",
            reply_markup=_saved_keyboard(),
            parse_mode="Markdown",
        )

    await state.clear()
    await callback.answer("Сохранено ✅")


@router.callback_query(F.data == "meal:cancel")
async def handle_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Ок, не сохраняю")
    if callback.message is not None:
        await callback.message.answer("❌ Не сохраняю. Отправь еду заново когда будешь готов.")


@router.callback_query(F.data == "meal:edit")
async def handle_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(MealConfirmState.awaiting_edit)
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(
            "Исправь еду одной строкой.\n\n"
            f"{_edit_examples()}\n\n"
            "Можно писать просто и по-человечески."
        )


@router.message(MealConfirmState.awaiting_edit, F.text)
async def handle_edit_text(message: Message, state: FSMContext) -> None:
    if message.from_user is None or message.text is None:
        return

    draft = await state.get_data()
    structure = draft.get("structure")
    if not structure:
        await state.clear()
        await message.answer("Черновик не найден. Отправь еду заново.")
        return

    # Применяем правку
    updated_structure, error = apply_meal_edit(structure, message.text)

    if error:
        await message.answer(error)
        return

    # Сохраняем обновлённый черновик
    await state.update_data(structure=updated_structure)

    # Пересчитываем
    meal_calc = calculate_meal(updated_structure.get("items", []))

    # Показываем обновлённую карточку
    preview = _format_meal_preview(updated_structure, meal_calc)
    await message.answer(preview, reply_markup=_confirm_keyboard(), parse_mode="Markdown")

    logger.info(f"Edit applied: {message.text} → {len(updated_structure.get('items', []))} items")


@router.message(MealConfirmState.awaiting_edit, F.photo)
@router.message(MealConfirmState.awaiting_edit, F.voice)
async def handle_edit_other(message: Message, state: FSMContext) -> None:
    await message.answer(
        "Сейчас я жду текст с правкой.\n"
        f"{_edit_examples()}"
    )
