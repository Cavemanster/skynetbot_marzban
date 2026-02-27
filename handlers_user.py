"""
User Handlers Module
Handles all user-facing bot commands and callbacks
"""

import logging
import json
import random
import string
from datetime import datetime, timedelta
from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import Database
from marzban_client import MarzbanClient
from keyboards import (
    get_main_keyboard,
    get_tariffs_keyboard,
    get_tariff_confirm_keyboard,
    get_trial_confirm_keyboard,
    get_payment_confirm_keyboard,
    get_my_vpn_keyboard,
    get_referral_keyboard,
    get_help_keyboard,
    get_back_keyboard,
)
from states import TariffStates, PaymentStates

logger = logging.getLogger(__name__)

user_router = Router()


# Text handlers for ReplyKeyboard buttons (main menu)
@user_router.message(F.text == "🔑 Мой VPN")
async def my_vpn_text(message: types.Message, db: Database):
    """Handle VPN button text message"""
    telegram_id = message.from_user.id
    subscription = await db.get_active_subscription(telegram_id)
    from keyboards import get_my_vpn_keyboard, get_main_keyboard
    if subscription:
        text = "🔑 Ваш VPN\n\nСтатус: ✅ Активен\nТариф: " + subscription.get('tariff_name', 'N/A')
        await message.answer(text, reply_markup=get_my_vpn_keyboard(True))
    else:
        await message.answer("🔑 Мой VPN\n\nУ вас нет активной подписки.", reply_markup=get_main_keyboard())

@user_router.message(F.text == "📊 Статус")
async def status_text(message: types.Message, db: Database):
    """Handle Status button text message"""
    telegram_id = message.from_user.id
    subscription = await db.get_active_subscription(telegram_id)
    if subscription:
        text = "📊 Статус\n\n✅ Активен\nТариф: " + subscription.get('tariff_name', 'N/A')
        await message.answer(text)
    else:
        await message.answer("📊 Статус\n\nНет активной подписки")

@user_router.message(F.text == "❓ Помощь")
async def help_text(message: types.Message):
    """Handle Help button text message"""
    from keyboards import get_help_keyboard
    await message.answer("❓ Помощь\n\nКак мы можем помочь?", reply_markup=get_help_keyboard())


def generate_marzban_username(telegram_id: int) -> str:
    """Generate unique Marzban username"""
    random_suffix = ''.join(random.choices(string.ascii_lowercase, k=4))
    return f"user_{telegram_id}_{random_suffix}@vpn"


def generate_payment_comment() -> str:
    """Generate unique payment comment"""
    return f"VPN{random.randint(100000, 999999)}"


@user_router.message(Command("start"))
async def cmd_start(message: types.Message, db: Database, state: FSMContext):
    """Handle /start command"""
    telegram_id = message.from_user.id
    await state.clear()
    
    # Check if user exists
    user = await db.get_user(telegram_id)
    
    if not user:
        # Check for referral
        referred_by = None
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        if len(args) > 0 and args[0].startswith("ref_"):
            referrer_id = int(args[0].replace("ref_", ""))
            if referrer_id != telegram_id:
                referred_by = referrer_id
        
        # Create new user
        marzban_username = generate_marzban_username(telegram_id)
        await db.add_user(
            telegram_id=telegram_id,
            username=message.from_user.username or "unknown",
            marzban_username=marzban_username,
            referred_by=referred_by
        )
        
        if referred_by:
            await db.add_referral(referred_by, telegram_id)
            referrer = await db.get_user(referred_by)
            if referrer:
                try:
                    await message.bot.send_message(
                        referred_by,
                        f"🎉 Ваш реферал @{message.from_user.username or 'user'} зарегистрировался!\n"
                        f"Когда он купит подписку, вы получите бонусные дни."
                    )
                except Exception as e:
                    logger.error(f"Failed to notify referrer: {e}")
        
        welcome_text = (
            f"👋 Привет, @{message.from_user.username or 'user'}!\n\n"
            f"🤖 Добро пожаловать в VPN бот!\n\n"
            f"🔐 Быстрый и надежный VPN для ваших нужд\n"
            f"📱 Работает на всех устройствах\n"
            f"⚡ Мгновенная активация\n\n"
            f"Нажмите 🔑 Мой VPN чтобы начать!"
        )
    else:
        welcome_text = (
            f"👋 С возвращением, @{message.from_user.username or 'user'}!\n\n"
            f"Выберите действие в меню:"
        )
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())


@user_router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    """Return to main menu"""
    await state.clear()
    await callback.message.edit_text(
        "🏠 Главное меню:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


@user_router.callback_query(F.data == "my_vpn")
async def my_vpn(callback: types.CallbackQuery, db: Database):
    """Show VPN management"""
    telegram_id = callback.from_user.id
    subscription = await db.get_active_subscription(telegram_id)
    
    if subscription:
        # Get user info from Marzban
        user = await db.get_user(telegram_id)
        text = (
            "🔑 Ваш VPN активен!\n\n"
            f"📊 Тариф: {subscription['tariff_id']}\n"
            f"⏳ Истекает: {subscription['expires_at']}\n"
            f"📈 Трафик: {subscription['traffic_used_gb']:.2f} / {subscription['traffic_limit_gb']:.2f} GB\n\n"
            f"Используйте кнопки ниже для управления."
        )
    else:
        text = (
            "🔑 У вас нет активной подписки\n\n"
            "Выберите тариф для подключения:"
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_my_vpn_keyboard(bool(subscription))
    )
    await callback.answer()


@user_router.callback_query(F.data == "tariffs")
async def show_tariffs(callback: types.CallbackQuery, db: Database):
    """Show available tariffs"""
    with open("data/tarifs.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    tariffs = data.get("tariffs", [])
    
    text = "💰 Доступные тарифы:\n\n"
    for tariff in tariffs:
        text += f"{tariff['name']}\n"
        text += f"💵 Цена: {tariff['price']}₽\n"
        text += f"⏳ Срок: {tariff['duration_days']} дн.\n"
        text += f"🔗 Устройств: {tariff['max_ips']}\n"
        if tariff.get('location'):
            text += f"🌍 Локация: {tariff['location']}\n"
        if tariff.get('is_trial'):
            text += "✅ Пробный период\n"
        text += "\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_tariffs_keyboard(tariffs)
    )
    await callback.answer()



@user_router.callback_query(F.data.startswith("tariff_"))
async def select_tariff(callback: types.CallbackQuery, db: Database):
    """Handle tariff selection"""
    tariff_id = callback.data.replace("tariff_", "")
    
    with open("data/tarifs.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    tariff = next((t for t in data["tariffs"] if t["id"] == tariff_id), None)
    if not tariff:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return
    
    # Check if trial is available
    has_used_trial = await db.has_used_trial(callback.from_user.id)
    if tariff["is_trial"] and has_used_trial:
        await callback.answer("❌ Вы уже использовали пробный период", show_alert=True)
        return
    
    text = (
        f"📦 Вы выбрали: {tariff['name']}\n\n"
        f"💵 Цена: {tariff['price']}₽\n"
        f"📊 Трафик: {tariff.get('traffic_gb', 0)} GB\n"
        f"⏳ Срок: {tariff['duration_days']} дн.\n"
        f"🔗 Устройств: {tariff['max_ips']}\n\n"
    )
    
    if tariff["price"] == 0:
        text += "🎁 Это бесплатный тариф!"
        keyboard = get_trial_confirm_keyboard(tariff_id)
    else:
        text += "💳 Оплатить для продолжения"
        keyboard = get_tariff_confirm_keyboard(tariff_id)
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard
    )
    await callback.answer()



@user_router.callback_query(F.data.startswith("trial_"))
async def activate_trial(callback: types.CallbackQuery, db: Database, marzban_client: MarzbanClient):
    """Activate trial subscription"""
    tariff_id = callback.data.replace("trial_", "")
    
    with open("data/tarifs.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    tariff = next((t for t in data["tariffs"] if t["id"] == tariff_id), None)
    if not tariff:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return
    
    has_used_trial = await db.has_used_trial(callback.from_user.id)
    if has_used_trial:
        await callback.answer("❌ Вы уже использовали пробный период", show_alert=True)
        return
    
    await activate_subscription(callback, db, tariff, callback.data["marzban_client"], is_trial=True)

@user_router.callback_query(F.data.startswith("pay_"))
async def initiate_payment(callback: types.CallbackQuery, db: Database, config: dict, state: FSMContext, marzban_client: MarzbanClient):
    """Initiate payment process"""
    tariff_id = callback.data.replace("pay_", "")
    
    with open("data/tarifs.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    tariff = next((t for t in data["tariffs"] if t["id"] == tariff_id), None)
    if not tariff:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return
    
    # Free tariff - activate immediately
    if tariff["price"] == 0:
        await activate_subscription(callback, db, tariff, callback.data["marzban_client"], is_trial=tariff["is_trial"])
        return
    
    # Generate payment comment
    payment_comment = generate_payment_comment()
    
    # Create payment record
    payment_id = await db.add_payment(
        telegram_id=callback.from_user.id,
        amount=tariff["price"],
        tariff_id=tariff_id,
        payment_comment=payment_comment
    )
    
    text = (
        f"💳 Оплата подписки\n\n"
        f"📦 Тариф: {tariff['name']}\n"
        f"💵 Сумма: {tariff['price']}₽\n\n"
        f"💳 Карта: `{config.PAYMENT_CARD_NUMBER or '0000 0000 0000 0000'}`\n"
        f"👤 Получатель: `{config.PAYMENT_CARD_HOLDER or 'CARD HOLDER'}`\n\n"
        f"⚠️ Важно: В комментарии к платежу укажите:\n"
        f"🔢 `{payment_comment}`\n\n"
        f"После оплаты нажмите ✅ Подтверждаю оплату"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_payment_confirm_keyboard(payment_id),
        parse_mode="Markdown"
    )
    await state.set_state(PaymentStates.waiting_for_confirmation)
    await callback.answer()


async def activate_subscription(
    callback: types.CallbackQuery,
    db: Database,
    tariff: dict,
    marzban_client: MarzbanClient,
    is_trial: bool = False
):
    """Activate subscription for user"""
    telegram_id = callback.from_user.id
    user = await db.get_user(telegram_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Create user in Marzban
    marzban_client: MarzbanClient = callback.data["marzban_client"]
    
    data_limit = tariff.get("traffic_gb", 0) * 1024 * 1024 * 1024  # Convert to bytes
    expire = marzban_client.calculate_expire_timestamp(tariff["duration_days"])
    
    try:
        await marzban_client.create_user(
            username=user["marzban_username"],
            data_limit=data_limit,
            expire=expire
        )
    except Exception as e:
        logger.error(f"Failed to create Marzban user: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        return
    
    # Add subscription to database
    expires_at = datetime.utcnow() + timedelta(days=tariff["duration_days"])
    await db.add_subscription(
        telegram_id=telegram_id,
        tariff_id=tariff["id"],
        expires_at=expires_at,
        traffic_limit_gb=tariff.get("traffic_gb", 0),
        is_trial=is_trial
    )
    
    # Get subscription link
    sub_link = marzban_client.get_subscription_link(user["marzban_username"])
    
    text = (
        f"✅ Подписка активирована!\n\n"
        f"📦 Тариф: {tariff['name']}\n"
        f"⏳ Срок: {tariff['duration_days']} дн.\n"
        f"📊 Трафик: {tariff.get('traffic_gb', 0)} GB\n\n"
        f"🔗 Ссылка для подключения:\n`{sub_link}`\n\n"
        f"Нажмите 🔗 Получить ссылку в любое время"
    )
    
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer("✅ Подписка активирована!")


@user_router.callback_query(F.data.startswith("confirm_payment_"))
async def confirm_payment(callback: types.CallbackQuery, db: Database, state: FSMContext):
    """User confirms payment"""
    payment_id = int(callback.data.replace("confirm_payment_", ""))
    payment = await db.get_payment(payment_id)
    
    if not payment:
        await callback.answer("❌ Платеж не найден", show_alert=True)
        return
    
    if payment["telegram_id"] != callback.from_user.id:
        await callback.answer("❌ Это не ваш платеж", show_alert=True)
        return
    
    text = (
        "✅ Вы подтвердили оплату\n\n"
        "Ожидайте проверки администратором.\n"
        "Обычно проверка занимает до 24 часов.\n\n"
        "Вы получите уведомление когда подписка будет активирована."
    )
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await state.clear()
    await callback.answer()


@user_router.callback_query(F.data == "get_link")
async def get_subscription_link(callback: types.CallbackQuery, db: Database):
    """Get subscription link"""
    telegram_id = callback.from_user.id
    user = await db.get_user(telegram_id)
    subscription = await db.get_active_subscription(telegram_id)
    
    if not user or not subscription:
        await callback.answer("❌ Нет активной подписки", show_alert=True)
        return
    
    marzban_client: MarzbanClient = callback.data["marzban_client"]
    sub_link = marzban_client.get_subscription_link(user["marzban_username"])
    
    text = (
        "🔗 Ваша ссылка для подключения:\n\n"
        f"`{sub_link}`\n\n"
        "Скопируйте и вставьте в VPN клиент"
    )
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()


@user_router.callback_query(F.data == "get_qr")
async def get_qr_code(callback: types.CallbackQuery, db: Database):
    """Get QR code for subscription"""
    telegram_id = callback.from_user.id
    user = await db.get_user(telegram_id)
    subscription = await db.get_active_subscription(telegram_id)
    
    if not user or not subscription:
        await callback.answer("❌ Нет активной подписки", show_alert=True)
        return
    
    marzban_client: MarzbanClient = callback.data["marzban_client"]
    sub_link = marzban_client.get_subscription_link(user["marzban_username"])
    
    # Send QR code
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="🔗 Ссылка", callback_data="get_link")
    
    await callback.message.answer(
        f"📱 Отсканируйте QR код для быстрого подключения:\n\n{sub_link}"
    )
    await callback.answer()


@user_router.callback_query(F.data == "status")
async def check_status(callback: types.CallbackQuery, db: Database):
    """Check subscription status"""
    telegram_id = callback.from_user.id
    subscription = await db.get_active_subscription(telegram_id)
    
    if subscription:
        # Try to get actual usage from Marzban
        user = await db.get_user(telegram_id)
        traffic_used = subscription.get("traffic_used_gb", 0)
        
        text = (
            "📊 Статус подписки\n\n"
            f"✅ Статус: Активна\n"
            f"📦 Тариф: {subscription['tariff_id']}\n"
            f"⏳ Истекает: {subscription['expires_at']}\n"
            f"📈 Трафик: {traffic_used:.2f} / {subscription['traffic_limit_gb']:.2f} GB\n"
            f"📅 Дата покупки: {subscription['created_at']}"
        )
    else:
        text = (
            "📊 Статус подписки\n\n"
            "❌ У вас нет активной подписки\n"
            "Нажмите 💰 Тарифы для выбора"
        )
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer()


@user_router.callback_query(F.data == "referrals")
async def show_referrals(callback: types.CallbackQuery, db: Database, config: dict):
    """Show referral program"""
    telegram_id = callback.from_user.id
    referral_count = await db.get_referral_count(telegram_id)

    # Generate referral link
    ref_link = f"https://t.me/{(await callback.bot.get_me()).username}?start=ref_{telegram_id}"

    text = (
        "🎁 Реферальная программа\n\n"
        f"👥 Ваши рефералы: {referral_count}\n\n"
        f"Пригласите друзей и получите бонусные дни!\n"
        f"🎁 +{config.REF_BONUS_DAYS or 7} дней за каждого друга\n\n"
        f"Ваша ссылка:\n`{ref_link}`"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_referral_keyboard(ref_link),
        parse_mode="Markdown"
    )
    await callback.answer()


@user_router.callback_query(F.data == "copy_referral")
async def copy_referral(callback: types.CallbackQuery, db: Database):
    """Copy referral link"""
    telegram_id = callback.from_user.id
    ref_link = f"https://t.me/{(await callback.bot.get_me()).username}?start=ref_{telegram_id}"
    
    await callback.answer(f"📋 {ref_link}", show_alert=True)


@user_router.callback_query(F.data == "help")
async def show_help(callback: types.CallbackQuery, config: dict):
    """Show help information"""
    text = (
        "ℹ️ Помощь\n\n"
        "🤖 Этот бот поможет вам купить и управлять VPN подпиской.\n\n"
        "📋 Команды:\n"
        "🔑 Мой VPN - управление подпиской\n"
        "💰 Тарифы - выбрать тариф\n"
        "📊 Статус - проверить статус\n"
        "🎁 Рефералы - пригласить друзей\n\n"
        "❓ Нужна помощь? Свяжитесь с поддержкой."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_help_keyboard()
    )
    await callback.answer()


@user_router.callback_query(F.data == "support")
async def contact_support(callback: types.CallbackQuery, config: dict):
    """Contact support"""
    support_url = config.SUPPORT_URL or "https://t.me/support"
    text = f"📞 Поддержка\n\nСвяжитесь с нами: {support_url}"
    await callback.message.answer(text)
    await callback.answer()


@user_router.callback_query(F.data == "channel")
async def show_channel(callback: types.CallbackQuery, config: dict):
    """Show channel link"""
    channel_url = config.TG_CHANNEL or "https://t.me/channel"
    text = f"📢 Наш канал: {channel_url}"
    await callback.message.answer(text)
    await callback.answer()


@user_router.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery, db: Database):
    """Show user profile"""
    telegram_id = callback.from_user.id
    user = await db.get_user(telegram_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    subscription = await db.get_active_subscription(telegram_id)
    referral_count = await db.get_referral_count(telegram_id)
    
    text = (
        f"👤 Профиль\n\n"
        f"ID: `{telegram_id}`\n"
        f"Username: @{user['username']}\n"
        f"📅 Регистрация: {user['created_at']}\n\n"
        f"🎁 Рефералов: {referral_count}\n"
        f"🔑 Подписка: {'✅ Активна' if subscription else '❌ Не активна'}\n"
    )
    
    if subscription:
        text += f"⏳ Истекает: {subscription['expires_at']}"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()
