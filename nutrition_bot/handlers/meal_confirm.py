"""
meal_confirm.py — подтверждение, редактирование и сохранение приёма пищи.

Router с высоким приоритом (регистрируется ПЕРВЫМ в handlers/__init__.py).
Перехватывает callback-кнопки и текст во время редактирования.
"""

from __future__ import annotations

import logging
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
    awaiting_confirmation = "awaiting_confirmation"
    awaiting_edit = "awaiting_edit"


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
    action: str  # "set" | "remove" | "add"
    name: str
    grams: Optional[float] = None


def parse_edit_command(text: str) -> Optional[EditCommand]:
    """Парсит команду редактирования.

    Поддерживаемые форматы:
    - борщ=300       → set
    - -хлеб           → remove
    - +яблоко=120     → add
    - хлеб             → set (без знака = не парсим, просим формат)
    """
    text = text.strip()

    # Удаление: -название
    if text.startswith("-"):
        name = text[1:].strip()
        if name:
            return EditCommand(action="remove", name=name)
        return None

    # Добавление: +название=граммы
    if text.startswith("+"):
        rest = text[1:].strip()
        if "=" in rest:
            parts = rest.split("=", 1)
            name = parts[0].strip()
            try:
                grams = float(parts[1].strip())
            except ValueError:
                return None
            return EditCommand(action="add", name=name, grams=grams)
        return None

    # Изменение: название=граммы
    if "=" in text:
        parts = text.split("=", 1)
        name = parts[0].strip()
        try:
            grams = float(parts[1].strip())
        except ValueError:
            return None
        return EditCommand(action="set", name=name, grams=grams)

    return None


def apply_meal_edit(structure: dict, edit_text: str) -> tuple[dict, Optional[str]]:
    """Применяет правку к структуре еды.

    Returns:
        (updated_structure, error_message_or_None)
    """
    cmd = parse_edit_command(edit_text)
    if cmd is None:
        return structure, (
            "Не понял формат. Используй:\n"
            "• `борщ=300` — изменить граммы\n"
            "• `-хлеб` — удалить продукт\n"
            "• `+яблоко=120` — добавить продукт"
        )

    items: list[dict[str, Any]] = structure.get("items", [])

    if cmd.action == "remove":
        new_items = []
        removed = False
        for item in items:
            if cmd.name.lower() in item.get("name", "").lower():
                removed = True
            else:
                new_items.append(item)
        if not removed:
            return structure, f"Продукт «{cmd.name}» не найден в списке."
        structure = {**structure, "items": new_items}

    elif cmd.action == "set":
        found = False
        for item in items:
            if cmd.name.lower() in item.get("name", "").lower():
                item["grams"] = cmd.grams
                item["source"] = item.get("source", "llm")  # сохраняем источник
                found = True
        if not found:
            return structure, f"Продукт «{cmd.name}» не найден. Используй +{cmd.name}={cmd.grams:.0f} чтобы добавить."

    elif cmd.action == "add":
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
            "✏️ Отправь исправление в формате:\n\n"
            "• `борщ=300` — изменить граммы\n"
            "• `-хлеб` — удалить продукт\n"
            "• `+яблоко=120` — добавить продукт\n\n"
            "Или нажми ❌ Отмена чтобы начать заново."
        )


@router.message(MealConfirmState.awaiting_edit)
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
        "Например: `борщ=300` или `-хлеб` или `+яблоко=120`"
    )
