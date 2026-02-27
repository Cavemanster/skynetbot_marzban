"""
Keyboard Layouts Module
Contains all inline and reply keyboards for the bot
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard for users"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔑 Мой VPN", callback_data="my_vpn")
    builder.button(text="💰 Тарифы", callback_data="tariffs")
    builder.button(text="📊 Статус", callback_data="status")
    builder.button(text="🎁 Рефералы", callback_data="referrals")
    builder.button(text="ℹ️ Помощь", callback_data="help")
    builder.button(text="👤 Профиль", callback_data="profile")
    builder.adjust(2, 2, 2)
    return builder.as_markup()


def get_tariffs_keyboard(tariffs: list) -> InlineKeyboardMarkup:
    """Keyboard with tariff selection"""
    builder = InlineKeyboardBuilder()
    for tariff in tariffs:
        builder.button(
            text=f"{tariff['name']} - {tariff['price']}₽",
            callback_data=f"tariff_{tariff['id']}"
        )
    builder.button(text="↩️ Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()


def get_tariff_confirm_keyboard(tariff_id: str) -> InlineKeyboardMarkup:
    """Keyboard for confirming tariff purchase"""
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Оплатить", callback_data=f"pay_{tariff_id}")
    builder.button(text="↩️ Назад", callback_data="tariffs")
    builder.adjust(2)
    return builder.as_markup()


def get_trial_confirm_keyboard(tariff_id: str) -> InlineKeyboardMarkup:
    """Keyboard for confirming trial subscription"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎁 Получить", callback_data=f"trial_{tariff_id}")
    builder.button(text="↩️ Назад", callback_data="tariffs")
    builder.adjust(2)
    return builder.as_markup()


def get_payment_confirm_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    """Keyboard for confirming payment"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтверждаю оплату", callback_data=f"confirm_payment_{payment_id}")
    builder.button(text="❌ Отмена", callback_data="cancel_payment")
    builder.adjust(2)
    return builder.as_markup()


def get_my_vpn_keyboard(subscription_active: bool) -> InlineKeyboardMarkup:
    """Keyboard for VPN management"""
    builder = InlineKeyboardBuilder()
    if subscription_active:
        builder.button(text="🔗 Получить ссылку", callback_data="get_link")
        builder.button(text="📱 QR Код", callback_data="get_qr")
        builder.button(text="🔄 Обновить подписку", callback_data="renew_sub")
    else:
        builder.button(text="🛒 Купить подписку", callback_data="tariffs")
    builder.button(text="↩️ Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()


def get_referral_keyboard(referral_link: str) -> InlineKeyboardMarkup:
    """Keyboard for referrals"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Копировать ссылку", callback_data="copy_referral")
    builder.button(text="↩️ Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()


def get_help_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for help section"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📞 Поддержка", callback_data="support")
    builder.button(text="📢 Канал", callback_data="channel")
    builder.button(text="↩️ Назад", callback_data="back_to_main")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Admin menu keyboard"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="💰 Платежи", callback_data="admin_payments")
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="🔍 Поиск", callback_data="admin_search")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.button(text="⚙️ Настройки", callback_data="admin_settings")
    builder.adjust(2, 2, 2)
    return builder.as_markup()


def get_pending_payments_keyboard(payments: list) -> InlineKeyboardMarkup:
    """Keyboard with pending payments for admin"""
    builder = InlineKeyboardBuilder()
    for payment in payments[:10]:  # Show max 10 payments
        builder.button(
            text=f"💰 {payment['amount']}₽ - @{payment.get('tg_username', 'user')}",
            callback_data=f"payment_view_{payment['id']}"
        )
    builder.button(text="↩️ Назад", callback_data="back_to_admin")
    builder.adjust(1)
    return builder.as_markup()


def get_payment_review_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    """Keyboard for reviewing a payment"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Одобрить", callback_data=f"admin_approve_{payment_id}")
    builder.button(text="❌ Отклонить", callback_data=f"admin_reject_{payment_id}")
    builder.button(text="↩️ Назад", callback_data="admin_payments")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Simple back button"""
    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ Назад", callback_data="back_to_main")
    return builder.as_markup()


def get_yes_no_keyboard(yes_callback: str, no_callback: str) -> InlineKeyboardMarkup:
    """Yes/No confirmation keyboard"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data=yes_callback)
    builder.button(text="❌ Нет", callback_data=no_callback)
    builder.adjust(2)
    return builder.as_markup()


def get_user_search_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for user search"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 По ID", callback_data="search_by_id")
    builder.button(text="🔍 По username", callback_data="search_by_username")
    builder.button(text="↩️ Назад", callback_data="back_to_admin")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_user_management_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    """Keyboard for managing a specific user"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Инфо", callback_data=f"admin_user_info_{telegram_id}")
    builder.button(text="🔑 VPN", callback_data=f"admin_user_vpn_{telegram_id}")
    builder.button(text="🚫 Забанить", callback_data=f"admin_user_ban_{telegram_id}")
    builder.button(text="↩️ Назад", callback_data="admin_users")
    builder.adjust(2, 2)
    return builder.as_markup()


def get_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for broadcast message"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📤 Отправить", callback_data="broadcast_send")
    builder.button(text="❌ Отмена", callback_data="back_to_admin")
    builder.adjust(2)
    return builder.as_markup()
