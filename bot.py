"""Telegram-бот МЕТР² ПОД КЛЮЧ."""

import asyncio
import logging
import os
import re
from contextlib import suppress

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery, InlineKeyboardMarkup, KeyboardButton, Message,
    ReplyKeyboardMarkup, ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

import db
import projects

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("metr2-bot")

TOKEN = os.getenv("BOT_TOKEN", "8922144106:AAGs4zrdQrTyi1FoC7O8ID4xsx6G83Pf6F0")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "Dmitry_Dolgoter")
PRIVACY_POLICY_URL = os.getenv("PRIVACY_POLICY_URL", "https://example.com/privacy")
ADMIN_CHAT_ID: int | None = None

FINAL_PHRASE_NOT_READY = (
    "Спасибо, {name}! Заявка принята.\n\n"
    "Этот проект сейчас в финальной доработке. Вы — в числе первых, "
    "кому я пришлю полный комплект и финальную стоимость для оформления "
    "покупки. Обычно это занимает 2–4 недели.\n\n"
    "Если будут вопросы или захотите ускорить — пишите мне сюда же."
)
FINAL_PHRASE_READY = (
    "Спасибо, {name}! Заявка принята.\n\n"
    "Проект готов к покупке. Я свяжусь с вами в ближайшие несколько часов, "
    "пришлю полный комплект, реквизиты для оплаты и срок передачи материалов.\n\n"
    "Если будут вопросы — пишите мне сюда же."
)


class OrderForm(StatesGroup):
    name = State()
    phone = State()
    channel = State()
    timing = State()
    consent = State()


router = Router()


def is_admin(msg) -> bool:
    u = getattr(msg, "from_user", None)
    return bool(u and u.username and u.username == ADMIN_USERNAME)


def project_keyboard():
    b = InlineKeyboardBuilder()
    for p in projects.list_projects():
        b.button(text=f"{p['rooms']}, {p['area_m2']} м² — {p['style']}", callback_data=f"proj:{p['id']}")
    b.adjust(1)
    return b.as_markup()


def format_project(p):
    price = f"{p['price']:,}".replace(",", " ")
    return (
        f"<b>{p['title']}</b>\n\n"
        f"<b>Площадь:</b> {p['area_m2']} м²\n"
        f"<b>Тип:</b> {p['rooms']}\n"
        f"<b>Стиль:</b> {p['style']}\n"
        f"<b>Цена проекта:</b> {price} ₽\n\n"
        f"{p['description']}"
    )


def project_action_keyboard(pid):
    b = InlineKeyboardBuilder()
    b.button(text="✅ Хочу этот проект", callback_data=f"order:{pid}")
    b.button(text="← К каталогу", callback_data="catalog")
    b.adjust(1)
    return b.as_markup()


@router.message(CommandStart(deep_link=True))
async def start_deeplink(message: Message, command: CommandObject, state: FSMContext):
    global ADMIN_CHAT_ID
    if message.from_user.username == ADMIN_USERNAME:
        ADMIN_CHAT_ID = message.chat.id
    await state.clear()
    await db.upsert_user(message.from_user.id, message.from_user.username,
                         message.from_user.first_name, message.from_user.last_name)
    payload = (command.args or "").strip()
    project_id = payload[len("project_"):] if payload.startswith("project_") else payload
    p = projects.get_project(project_id)
    if not p:
        return await start_no_payload(message, state)
    await db.log_event(message.from_user.id, project_id, "project_view")
    await message.answer(format_project(p), reply_markup=project_action_keyboard(project_id))


@router.message(CommandStart())
async def start_no_payload(message: Message, state: FSMContext):
    global ADMIN_CHAT_ID
    if message.from_user.username == ADMIN_USERNAME:
        ADMIN_CHAT_ID = message.chat.id
    await state.clear()
    await db.upsert_user(message.from_user.id, message.from_user.username,
                         message.from_user.first_name, message.from_user.last_name)
    welcome = (
        "<b>МЕТР² ПОД КЛЮЧ</b>\n"
        "Готовые дизайн-проекты под планировки ЖК «Первый Нагатинский».\n\n"
        "Каждый проект — полный пакет: планировка с расстановкой, "
        "визуализации, ведомости отделки, спецификация мебели и света. "
        "Готовый документ для ремонта без долгих согласований с дизайнером.\n\n"
        "Выберите вашу планировку:"
    )
    await message.answer(welcome, reply_markup=project_keyboard())
    if is_admin(message):
        await message.answer("🔑 Вы вошли как админ. Команды: /stats /orders /projects /admin")


@router.callback_query(F.data == "catalog")
async def cb_catalog(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Выберите вашу планировку:", reply_markup=project_keyboard())
    await call.answer()


@router.callback_query(F.data.startswith("proj:"))
async def cb_project(call: CallbackQuery, state: FSMContext):
    project_id = call.data.removeprefix("proj:")
    p = projects.get_project(project_id)
    if not p:
        return await call.answer("Проект не найден.", show_alert=True)
    await db.log_event(call.from_user.id, project_id, "project_view")
    await call.message.edit_text(format_project(p), reply_markup=project_action_keyboard(project_id))
    await call.answer()


@router.callback_query(F.data.startswith("order:"))
async def cb_order(call: CallbackQuery, state: FSMContext):
    project_id = call.data.removeprefix("order:")
    p = projects.get_project(project_id)
    if not p:
        return await call.answer("Проект не найден.", show_alert=True)
    await state.update_data(project_id=project_id)
    await db.log_event(call.from_user.id, project_id, "start_order")
    await call.message.answer(
        f"Отлично, оформляем заявку на «{p['title']}».\n\nКак вас зовут?",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(OrderForm.name)
    await call.answer()


@router.message(OrderForm.name, F.text)
async def order_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 60:
        return await message.answer("Имя слишком короткое или длинное. Введите ещё раз.")
    await state.update_data(name=name)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True,
    )
    await message.answer(
        f"Приятно познакомиться, {name}!\n\nПришлите ваш телефон — кнопкой ниже или текстом.",
        reply_markup=kb,
    )
    await state.set_state(OrderForm.phone)


PHONE_RE = re.compile(r"[\d+\-\s()]{10,20}")


@router.message(OrderForm.phone, F.contact)
async def order_phone_contact(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await ask_channel(message, state)


@router.message(OrderForm.phone, F.text)
async def order_phone_text(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not PHONE_RE.fullmatch(phone):
        return await message.answer("Это не похоже на телефон. Например: +7 999 123 45 67.")
    await state.update_data(phone=phone)
    await ask_channel(message, state)


async def ask_channel(message: Message, state: FSMContext):
    b = InlineKeyboardBuilder()
    for label in ("Telegram", "WhatsApp", "Звонок"):
        b.button(text=label, callback_data=f"ch:{label}")
    b.adjust(3)
    await message.answer("Удобный способ связи?", reply_markup=b.as_markup())
    await message.answer("…", reply_markup=ReplyKeyboardRemove())
    await state.set_state(OrderForm.channel)


@router.callback_query(OrderForm.channel, F.data.startswith("ch:"))
async def order_channel(call: CallbackQuery, state: FSMContext):
    channel = call.data.removeprefix("ch:")
    await state.update_data(channel=channel)
    b = InlineKeyboardBuilder()
    for label, key in (
        ("В ближайший месяц", "В ближайший месяц"),
        ("1–3 месяца", "1-3 месяца"),
        ("3–6 месяцев", "3-6 месяцев"),
        ("Позже", "Позже"),
    ):
        b.button(text=label, callback_data=f"tm:{key}")
    b.adjust(1)
    await call.message.edit_text(
        f"Способ связи: <b>{channel}</b>\n\nКогда планируете ремонт?",
        reply_markup=b.as_markup(),
    )
    await state.set_state(OrderForm.timing)
    await call.answer()


@router.callback_query(OrderForm.timing, F.data.startswith("tm:"))
async def order_timing(call: CallbackQuery, state: FSMContext):
    timing = call.data.removeprefix("tm:")
    await state.update_data(timing=timing)
    b = InlineKeyboardBuilder()
    b.button(text="✅ Согласен на обработку данных", callback_data="consent:yes")
    b.button(text="❌ Не согласен", callback_data="consent:no")
    b.adjust(1)
    await call.message.edit_text(
        f"Сроки: <b>{timing}</b>\n\n"
        f"Последний шаг — согласие на обработку персональных данных. "
        f"Храню только: имя, телефон, выбранный проект и сроки. "
        f"Использую только для связи по этой заявке.\n\n"
        f'<a href="{PRIVACY_POLICY_URL}">Политика конфиденциальности</a>',
        reply_markup=b.as_markup(), disable_web_page_preview=True,
    )
    await state.set_state(OrderForm.consent)
    await call.answer()


@router.callback_query(OrderForm.consent, F.data == "consent:no")
async def consent_no(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "Без согласия на обработку данных я не могу сохранить заявку. "
        "Если передумаете — нажмите /start и пройдите снова."
    )
    await call.answer()


@router.callback_query(OrderForm.consent, F.data == "consent:yes")
async def consent_yes(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    project_id = data["project_id"]
    name = data["name"]; phone = data["phone"]
    channel = data["channel"]; timing = data["timing"]
    p = projects.get_project(project_id)
    order_id = await db.save_order(call.from_user.id, project_id, name, phone, channel, timing)
    await db.log_event(call.from_user.id, project_id, "complete_order")
    template = FINAL_PHRASE_READY if (p and p.get("ready")) else FINAL_PHRASE_NOT_READY
    await call.message.edit_text(template.format(name=name), disable_web_page_preview=True)
    await state.clear()
    await call.answer()
    if ADMIN_CHAT_ID:
        with suppress(Exception):
            u = call.from_user
            ulink = f"@{u.username}" if u.username else f"<a href='tg://user?id={u.id}'>{u.first_name or 'клиент'}</a>"
            admin_msg = (
                f"🔔 <b>Новая заявка #{order_id}</b>\n\n"
                f"<b>Проект:</b> {p['title'] if p else project_id}\n"
                f"<b>Имя:</b> {name}\n<b>Телефон:</b> {phone}\n"
                f"<b>Связь:</b> {channel}\n<b>Сроки:</b> {timing}\n"
                f"<b>Клиент:</b> {ulink}"
            )
            await call.bot.send_message(ADMIN_CHAT_ID, admin_msg, disable_web_page_preview=True)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_admin(message): return
    s = await db.get_stats()
    top = "\n".join(f"  • {pid}: {cnt} заявок" for pid, cnt in s["top_projects"]) or "  (пусто)"
    await message.answer(
        "<b>📊 Сводка</b>\n\n"
        f"Всего заявок: <b>{s['total_orders']}</b>\n"
        f"За 7 дней: <b>{s['week_orders']}</b>\n"
        f"Уникальных клиентов: <b>{s['total_users']}</b>\n"
        f"Просмотров проектов: <b>{s['total_views']}</b>\n\n"
        f"<b>Топ-5 по заявкам:</b>\n{top}"
    )


@router.message(Command("orders"))
async def cmd_orders(message: Message):
    if not is_admin(message): return
    rows = await db.get_recent_orders(20)
    if not rows: return await message.answer("Заявок пока нет.")
    lines = ["<b>Последние 20 заявок:</b>\n"]
    for r in rows:
        lines.append(f"#{r['id']} · {r['created_at']}\n  {r['name']} · {r['phone']} · {r['channel']}\n  {r['project_id']} · {r['timing']}\n")
    await message.answer("\n".join(lines))


@router.message(Command("projects"))
async def cmd_projects(message: Message):
    if not is_admin(message): return
    counters = await db.get_project_counters()
    lines = ["<b>Каталог:</b>\n"]
    for p in projects.list_projects():
        c = counters.get(p["id"], {})
        v = c.get("views", 0); o = c.get("orders", 0)
        flag = "🟢 готов" if p.get("ready") else "🟡 в разработке"
        lines.append(f"<b>{p['title']}</b>\n  {flag} · просмотров: {v} · заявок: {o}\n  id: <code>{p['id']}</code>\n")
    await message.answer("\n".join(lines))


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message):
        return await message.answer("Только для админа.")
    await message.answer("🔑 Админ-меню:\n/stats — сводка\n/orders — последние заявки\n/projects — каталог")


async def main():
    await db.init_db()
    proxy_url = os.getenv("BOT_HTTPS_PROXY") or os.getenv("https_proxy")
    session = AiohttpSession(proxy=proxy_url) if proxy_url else None
    bot = Bot(token=TOKEN, session=session,
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    log.info("Bot started — polling")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
