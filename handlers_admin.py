"""
    marzban_client = _marzban_client
    marzban_client = _marzban_client
    marzban_client = _marzban_client
    marzban_client = _marzban_client
Admin Handlers Module
Handles all admin panel commands and callbacks
"""

import logging
from datetime import datetime
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import LabeledPrice

from database import Database
from marzban_client import MarzbanClient
from keyboards import (
    get_admin_keyboard,
    get_pending_payments_keyboard,
    get_payment_review_keyboard,
    get_back_keyboard,
    get_user_search_keyboard,
    get_user_management_keyboard,
    get_yes_no_keyboard,
    get_broadcast_keyboard,
)
from states import AdminStates, PaymentStates
from globals import _marzban_client


logger = logging.getLogger(__name__)

admin_router = Router()


async def is_admin(telegram_id: int, config: dict) -> bool:
    """Check if user is admin"""
    admin_ids = config.ADMIN_USER_IDS
    return str(telegram_id) in admin_ids


@admin_router.message(Command("admin"))
async def cmd_admin(message: types.Message, config: dict, db: Database):
    """Open admin panel"""
    if not await is_admin(message.from_user.id, config):
        return
    
    text = (
        "👑 Админ Панель\n\n"
        "Выберите действие:"
    )
    
    await message.answer(text, reply_markup=get_admin_keyboard())


@admin_router.callback_query(F.data == "admin_stats")
async def admin_statistics(callback: types.CallbackQuery, db: Database):
    """Show bot statistics"""
    marzban_client = _marzban_client
    try:
        # Get bot stats from database
        stats = await db.get_statistics()
        
        # Get Marzban system stats
        try:
            marzban_stats = await data.get('marzban_client').get_system_stats()
            marzban_text = (
                f"\n🖥 Marzban Статистика:\n"
                f"👥 Пользователей: {marzban_stats.get('total_user', 0)}\n"
                f"✅ Активных: {marzban_stats.get('active_users', 0)}\n"
                f"💾 Использовано: {data.get('marzban_client').format_traffic(marzban_stats.get('users_used', 0))}\n"
                f"🌐 Всего: {data.get('marzban_client').format_traffic(marzban_stats.get('users_total', 0))}\n"
            )
        except Exception as e:
            logger.error(f"Failed to get Marzban stats: {e}")
            marzban_text = "\n❌ Не удалось получить статистику Marzban"
        
        text = (
            "📊 Статистика бота\n\n"
            f"👥 Всего пользователей: {stats['total_users']}\n"
            f"🚫 Забанено: {stats['banned_users']}\n"
            f"🔑 Активных подписок: {stats['active_subscriptions']}\n"
            f"💰 Ожидают оплаты: {stats['pending_payments']}\n"
            f"{marzban_text}"
        )
        
        await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)
    
    await callback.answer()


@admin_router.callback_query(F.data == "admin_payments")
async def admin_payments(callback: types.CallbackQuery, db: Database):
    """Show pending payments"""
    payments = await db.get_pending_payments()
    
    if not payments:
        text = "💰 Платежи\n\n✅ Нет ожидающих платежей"
        await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    else:
        text = f"💰 Ожидают оплаты ({len(payments)}):\n\n"
        for payment in payments[:10]:
            text += (
                f"ID: {payment['id']}\n"
                f"👤 @{payment.get('tg_username', 'user')}\n"
                f"💵 {payment['amount']}₽\n"
                f"📦 {payment['tariff_id']}\n"
                f"🔢 {payment['payment_comment']}\n"
                f"⏰ {payment['created_at']}\n\n"
            )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_pending_payments_keyboard(payments)
        )
    
    await callback.answer()


@admin_router.callback_query(F.data.startswith("payment_view_"))
async def admin_view_payment(callback: types.CallbackQuery, db: Database):
    """View payment details"""
    payment_id = int(callback.data.replace("payment_view_", ""))
    payment = await db.get_payment(payment_id)
    
    if not payment:
        await callback.answer("❌ Платеж не найден", show_alert=True)
        return
    
    user = await db.get_user(payment["telegram_id"])
    
    text = (
        f"💰 Детали платежа\n\n"
        f"ID: {payment['id']}\n"
        f"👤 Пользователь: @{user['username'] if user else 'unknown'}\n"
        f"🆔 Telegram ID: `{payment['telegram_id']}`\n"
        f"💵 Сумма: {payment['amount']}₽\n"
        f"📦 Тариф: {payment['tariff_id']}\n"
        f"🔢 Комментарий: `{payment['payment_comment']}`\n"
        f"📅 Создан: {payment['created_at']}\n"
        f"⏳ Статус: {payment['status']}\n"
    )
    
    if payment["status"] == "pending":
        await callback.message.edit_text(
            text,
            reply_markup=get_payment_review_keyboard(payment_id),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_approve_"))
async def admin_approve_payment(callback: types.CallbackQuery, db: Database):
    """Approve payment"""
    marzban_client = _marzban_client
    payment_id = int(callback.data.replace("admin_approve_", ""))
    payment = await db.get_payment(payment_id)
    
    if not payment:
        await callback.answer("❌ Платеж не найден", show_alert=True)
        return
    
    # Approve payment
    await db.approve_payment(payment_id, callback.from_user.id)
    
    # Get tariff info
    with open("data/tarifs.json", "r", encoding="utf-8") as f:
        import json
        data = json.load(f)
    tariff = next((t for t in data["tariffs"] if t["id"] == payment["tariff_id"]), None)
    
    if not tariff:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return
    
    # Get or create user in Marzban
    user = await db.get_user(payment["telegram_id"])
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Check if user already has subscription
    existing_sub = await db.get_active_subscription(payment["telegram_id"])
    
    try:
        if existing_sub:
            # Extend existing subscription
            marzban_user = await data.get('marzban_client').get_user(user["marzban_username"])
            new_expire = data.get('marzban_client').calculate_expire_timestamp(
                tariff["duration_days"]
            )
            new_traffic = marzban_user.get("data_limit", 0) + (tariff.get('traffic_gb', 0) * 1024 * 1024 * 1024)
            
            await data.get('marzban_client').modify_user(
                user["marzban_username"],
                data_limit=new_traffic,
                expire=new_expire
            )
        else:
            # Create new user
            await data.get('marzban_client').create_user(
                username=user["marzban_username"],
                data_limit=tariff.get('traffic_gb', 0) * 1024 * 1024 * 1024,
                expire=data.get('marzban_client').calculate_expire_timestamp(tariff["duration_days"])
            )
        
        # Add subscription to database
        expires_at = datetime.utcnow() + timedelta(days=tariff["duration_days"])
        await db.add_subscription(
            telegram_id=payment["telegram_id"],
            tariff_id=tariff["id"],
            expires_at=expires_at,
            traffic_limit_gb=tariff.get('traffic_gb', 0)
        )
        
        # Notify user
        sub_link = data.get('marzban_client').get_subscription_link(user["marzban_username"])
        try:
            await callback.bot.send_message(
                payment["telegram_id"],
                f"✅ Ваша оплата одобрена!\n\n"
                f"📦 Тариф: {tariff['name']}\n"
                f"⏳ Срок: {tariff['duration_days']} дн.\n"
                f"📊 Трафик: {tariff.get('traffic_gb', 0)} GB\n\n"
                f"🔗 Ссылка: `{sub_link}`",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")
        
        await callback.message.edit_text(
            f"✅ Платеж #{payment_id} одобрен!\n"
            f"Пользователь уведомлен.",
            reply_markup=get_back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error approving payment: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        return
    
    await callback.answer("✅ Платеж одобрен!")


@admin_router.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject_payment(callback: types.CallbackQuery, db: Database):
    """Reject payment"""
    payment_id = int(callback.data.replace("admin_reject_", ""))
    payment = await db.get_payment(payment_id)
    
    if not payment:
        await callback.answer("❌ Платеж не найден", show_alert=True)
        return
    
    # Reject payment
    await db.reject_payment(payment_id, callback.from_user.id)
    
    # Notify user
    try:
        await callback.bot.send_message(
            payment["telegram_id"],
            f"❌ Ваша оплата #{payment_id} была отклонена.\n\n"
            f"Если вы считаете это ошибкой, свяжитесь с поддержкой."
        )
    except Exception as e:
        logger.error(f"Failed to notify user: {e}")
    
    await callback.message.edit_text(
        f"❌ Платеж #{payment_id} отклонен!\n"
        f"Пользователь уведомлен.",
        reply_markup=get_back_keyboard()
    )
    
    await callback.answer("❌ Платеж отклонен!")


@admin_router.callback_query(F.data == "admin_users")
async def admin_users(callback: types.CallbackQuery, db: Database):
    """Show users management"""
    text = (
        "👥 Управление пользователями\n\n"
        "Выберите действие:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_user_search_keyboard()
    )
    await callback.answer()


@admin_router.callback_query(F.data == "search_by_id")
async def search_by_id(callback: types.CallbackQuery, state: FSMContext):
    """Search user by ID"""
    await callback.message.edit_text(
        "🔍 Введите Telegram ID пользователя:",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(AdminStates.search_input)
    await state.update_data(search_type="id")
    await callback.answer()


@admin_router.callback_query(F.data == "search_by_username")
async def search_by_username(callback: types.CallbackQuery, state: FSMContext):
    """Search user by username"""
    await callback.message.edit_text(
        "🔍 Введите username пользователя (без @):",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(AdminStates.search_input)
    await state.update_data(search_type="username")
    await callback.answer()


@admin_router.message(AdminStates.search_input)
async def process_search(message: types.Message, state: FSMContext, db: Database):
    """Process user search"""
    data = await state.get_data()
    search_type = data.get("search_type")
    search_value = message.text.strip()
    
    if search_type == "id":
        try:
            telegram_id = int(search_value)
            user = await db.get_user(telegram_id)
        except ValueError:
            await message.answer("❌ Неверный формат ID")
            return
    else:
        # Search by username - need to iterate all users
        all_users = await db.get_all_users()
        user = next((u for u in all_users if u["username"] == search_value.lstrip("@")), None)
    
    if not user:
        await message.answer("❌ Пользователь не найден", reply_markup=get_back_keyboard())
        return
    
    # Show user management
    subscription = await db.get_active_subscription(user["telegram_id"])
    
    text = (
        f"👤 Пользователь\n\n"
        f"ID: `{user['telegram_id']}`\n"
        f"Username: @{user['username']}\n"
        f"Marzban: `{user['marzban_username']}`\n"
        f"📅 Регистрация: {user['created_at']}\n"
        f"🔑 Подписка: {'✅ Активна' if subscription else '❌ Не активна'}\n"
    )
    
    if subscription:
        text += f"⏳ Истекает: {subscription['expires_at']}"
    
    await message.answer(
        text,
        reply_markup=get_user_management_keyboard(user["telegram_id"]),
        parse_mode="Markdown"
    )
    
    await state.clear()


@admin_router.callback_query(F.data.startswith("admin_user_info_"))
async def admin_user_info(callback: types.CallbackQuery, db: Database):
    """Show detailed user info"""
    telegram_id = int(callback.data.replace("admin_user_info_", ""))
    user = await db.get_user(telegram_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Get info from Marzban
    try:
        marzban_user = await data.get('marzban_client').get_user(user["marzban_username"])
        traffic_used = data.get('marzban_client').format_traffic(marzban_user.get("used_traffic", 0))
        traffic_limit = data.get('marzban_client').format_traffic(marzban_user.get("data_limit", 0))
        status = marzban_user.get("status", "unknown")
        expire_date = datetime.fromtimestamp(marzban_user.get("expire", 0)) if marzban_user.get("expire") else "Never"
    except Exception as e:
        logger.error(f"Failed to get Marzban user info: {e}")
        marzban_user = None
    
    text = (
        f"📊 Информация о пользователе\n\n"
        f"Telegram: @{user['username']}\n"
        f"ID: `{user['telegram_id']}`\n"
        f"Marzban: `{user['marzban_username']}`\n"
    )
    
    if marzban_user:
        text += (
            f"\n🖥 Marzban:\n"
            f"Статус: {status}\n"
            f"Трафик: {traffic_used} / {traffic_limit}\n"
            f"Истекает: {expire_date}\n"
        )
    
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=get_back_keyboard())
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_user_ban_"))
async def admin_user_ban(callback: types.CallbackQuery, db: Database):
    """Ban user"""
    marzban_client = _marzban_client
    telegram_id = int(callback.data.replace("admin_user_ban_", ""))
    user = await db.get_user(telegram_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Check current ban status
    is_banned = await db.is_user_banned(telegram_id)
    
    if is_banned:
        # Unban
        await db.unban_user(telegram_id)
        text = f"✅ Пользователь @{user['username']} разбанен"
    else:
        # Ban
        await db.ban_user(telegram_id)
        # Disable user in Marzban
        try:
            await data.get('marzban_client').modify_user(user["marzban_username"], status="disabled")
        except Exception as e:
            logger.error(f"Failed to disable Marzban user: {e}")
        text = f"🚫 Пользователь @{user['username']} забанен"
    
    await callback.message.answer(text, reply_markup=get_back_keyboard())
    await callback.answer()


@admin_router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: types.CallbackQuery, state: FSMContext):
    """Start broadcast message"""
    await callback.message.edit_text(
        "📢 Рассылка\n\n"
        "Отправьте сообщение, которое хотите разослать всем пользователям.\n\n"
        "Поддерживается текст, фото, видео и другие медиа.",
        reply_markup=get_broadcast_keyboard()
    )
    await state.set_state(AdminStates.broadcast_message)
    await callback.answer()


@admin_router.message(AdminStates.broadcast_message)
async def process_broadcast(message: types.Message, state: FSMContext, db: Database):
    """Process broadcast message"""
    users = await db.get_all_users()
    
    success_count = 0
    fail_count = 0
    
    # Forward message to all users
    for user in users:
        try:
            if message.text:
                await message.copy_to(user["telegram_id"])
            elif message.photo:
                await message.copy_to(user["telegram_id"])
            elif message.video:
                await message.copy_to(user["telegram_id"])
            else:
                await message.copy_to(user["telegram_id"])
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send to {user['telegram_id']}: {e}")
            fail_count += 1
    
    await message.answer(
        f"📢 Рассылка завершена\n\n"
        f"✅ Успешно: {success_count}\n"
        f"❌ Ошибок: {fail_count}\n"
        f"👥 Всего: {len(users)}",
        reply_markup=get_back_keyboard()
    )
    
    await state.clear()


@admin_router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: types.CallbackQuery, config: dict):
    """Return to admin menu"""
    if not await is_admin(callback.from_user.id, config):
        return
    
    text = (
        "👑 Админ Панель\n\n"
        "Выберите действие:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()
