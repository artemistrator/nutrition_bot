"""
templates.py — управление шаблонами приёмов пищи.

Команды:
  /templates       — список шаблонов с кнопками ➕ Добавить / 🗑 Удалить

Callback:
  tmpl:add:<id>    — добавить шаблон в дневник
  tmpl:del:<id>    — удалить шаблон
  meal:save_template — сохранить последний приём как шаблон
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database import (
    add_meal,
    create_meal_template,
    delete_meal_template,
    get_meal_template,
    get_user,
    list_meal_templates,
)
from handlers.meal_confirm import _format_meal_preview
from services.nutrition import MealAnalysis
from services.nutrition_db import calculate_meal

logger = logging.getLogger(__name__)

router = Router(name="templates")

# ── FSM ────────────────────────────────────────────────────────────

class TemplateState(StatesGroup):
    awaiting_name = State()


# ── Helpers ────────────────────────────────────────────────────────

def _templates_keyboard(templates: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    rows = []
    for tmpl in templates:
        tid = tmpl["id"]
        title = tmpl["title"]
        rows.append([
            InlineKeyboardButton(
                text=f"➕ {title}",
                callback_data=f"tmpl:add:{tid}",
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"tmpl:del:{tid}",
            ),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _save_template_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Сохранить как шаблон", callback_data="meal:save_template")],
        ]
    )


async def _add_template_to_diary(message: Message, user_id: int, template: dict) -> None:
    """Добавляет шаблон в дневник без LLM."""
    structure = template.get("structure")
    if structure is None:
        await message.answer("⚠️ Шаблон повреждён. Удали и создай заново.")
        return

    meal_calc = calculate_meal(structure.get("items", []))

    await add_meal(
        user_id=user_id,
        description=template["title"],
        calories=meal_calc["calories"],
        protein=meal_calc["protein"],
        fat=meal_calc["fat"],
        carbs=meal_calc["carbs"],
    )

    await message.answer(
        f"⭐ **{template['title']}** добавлен в дневник ✅\n\n"
        f"🔥 {meal_calc['calories']:.0f} ккал\n"
        f"Б: {meal_calc['protein']:.1f} г | Ж: {meal_calc['fat']:.1f} г | У: {meal_calc['carbs']:.1f} г",
        parse_mode="Markdown",
    )
    logger.info(f"Template added to diary: {template['title']} (id={template['id']})")


def _format_template_list(templates: list[dict[str, Any]]) -> str:
    lines = ["**Твои шаблоны:**\n"]
    for i, tmpl in enumerate(templates, 1):
        try:
            structure = json.loads(tmpl["structure_json"])
        except (json.JSONDecodeError, KeyError):
            structure = {"items": []}
        meal_calc = calculate_meal(structure.get("items", []))
        lines.append(f"{i}. **{tmpl['title']}** — {meal_calc['calories']:.0f} ккал")
    return "\n".join(lines)


# ── /templates ─────────────────────────────────────────────────────

@router.message(Command("templates"))
async def cmd_templates(message: Message) -> None:
    if message.from_user is None:
        return

    user = await get_user(message.from_user.id)
    if user is None:
        await message.answer("Сначала отправьте /start, чтобы создать профиль.")
        return

    templates = await list_meal_templates(message.from_user.id)

    if not templates:
        await message.answer(
            "У тебя пока нет шаблонов. 📭\n\n"
            "После сохранения приёма пищи нажми ⭐ Сохранить как шаблон, "
            "чтобы быстро добавлять его в будущем."
        )
        return

    await message.answer(
        _format_template_list(templates),
        reply_markup=_templates_keyboard(templates),
        parse_mode="Markdown",
    )


# ── ➕ Add template to diary ───────────────────────────────────────

@router.callback_query(F.data.startswith("tmpl:add:"))
async def handle_add_template(callback: CallbackQuery) -> None:
    if callback.from_user is None or callback.data is None or callback.message is None:
        return

    try:
        template_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
        await callback.answer("Неверный ID", show_alert=True)
        return

    template = await get_meal_template(template_id, callback.from_user.id)
    if template is None:
        await callback.answer("Шаблон не найден", show_alert=True)
        return

    await callback.answer()
    await _add_template_to_diary(callback.message, callback.from_user.id, template)


# ── 🗑 Delete template ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("tmpl:del:"))
async def handle_delete_template(callback: CallbackQuery) -> None:
    if callback.from_user is None or callback.data is None:
        return

    try:
        template_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
        await callback.answer("Неверный ID", show_alert=True)
        return

    deleted = await delete_meal_template(template_id, callback.from_user.id)

    if deleted:
        await callback.answer("Шаблон удалён 🗑")
        if callback.message is not None:
            templates = await list_meal_templates(callback.from_user.id)
            if templates:
                await callback.message.edit_text(
                    _format_template_list(templates),
                    reply_markup=_templates_keyboard(templates),
                    parse_mode="Markdown",
                )
            else:
                await callback.message.edit_text("У тебя больше нет шаблонов. 📭")
    else:
        await callback.answer("Не удалось удалить (не твой?)", show_alert=True)


# ── ⭐ Save last meal as template ──────────────────────────────────

@router.callback_query(F.data == "meal:save_template")
async def handle_save_template_request(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None:
        return

    data = await state.get_data()
    structure = data.get("template_structure") or data.get("structure") or data.get("last_saved_structure")

    if not structure:
        await callback.answer("Не вижу сохранённый приём. Сначала сохрани еду и потом нажми ещё раз.", show_alert=True)
        return

    # Сохраняем структуру для FSM
    template_structure = deepcopy(structure)
    await state.update_data(
        template_structure=template_structure,
        last_saved_structure=deepcopy(template_structure),
    )
    await state.set_state(TemplateState.awaiting_name)

    await callback.message.answer(
        "Введи название для шаблона, например:\n"
        "`Мой завтрак` или `Обед дома`\n\n"
        "(макс. 50 символов)"
    )
    await callback.answer()


@router.message(TemplateState.awaiting_name, F.text)
async def handle_template_name(message: Message, state: FSMContext) -> None:
    if message.from_user is None or message.text is None:
        return

    name = message.text.strip()

    # Валидация
    if not name:
        await message.answer("Название не может быть пустым. Попробуй ещё раз.")
        return

    if len(name) > 50:
        await message.answer("Название слишком длинное (макс. 50 символов). Попробуй короче.")
        return

    data = await state.get_data()
    structure = data.get("template_structure")
    last_saved_structure = data.get("last_saved_structure")
    if last_saved_structure is None and structure is not None:
        last_saved_structure = deepcopy(structure)

    if not structure:
        await state.clear()
        await message.answer("Черновик утрачен. Сохрани приём пищи и попробуй снова.")
        return

    # Создаём шаблон
    template_id = await create_meal_template(message.from_user.id, name, structure)
    await state.clear()
    if last_saved_structure:
        await state.update_data(last_saved_structure=last_saved_structure)

    # Показываем превью
    meal_calc = calculate_meal(structure.get("items", []))
    preview = _format_meal_preview(structure, meal_calc)

    await message.answer(
        f"⭐ Шаблон **{name}** сохранен!\n\n" + preview + "\n\n"
        f"Используй /templates чтобы увидеть все шаблоны.",
        parse_mode="Markdown",
    )
    logger.info(f"Template created: {name} (id={template_id})")


@router.message(TemplateState.awaiting_name)
async def handle_template_name_unexpected(message: Message) -> None:
    await message.answer("Отправь название шаблона обычным текстом. Например: `Мой завтрак`.", parse_mode="Markdown")
