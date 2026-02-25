"""
FSM States Module
Defines all conversation states for the bot
"""

from aiogram.fsm.state import State, StatesGroup


class MainStates(StatesGroup):
    """Main bot states"""
    menu = State()
    help = State()
    profile = State()


class TariffStates(StatesGroup):
    """Tariff selection states"""
    browsing = State()
    selecting = State()
    confirming = State()


class PaymentStates(StatesGroup):
    """Payment states"""
    waiting_for_comment = State()
    waiting_for_confirmation = State()
    admin_review = State()


class ReferralStates(StatesGroup):
    """Referral states"""
    browsing = State()


class AdminStates(StatesGroup):
    """Admin panel states"""
    menu = State()
    payments = State()
    payment_review = State()
    users = State()
    user_management = State()
    search = State()
    search_input = State()
    broadcast = State()
    broadcast_message = State()
    settings = State()


class SupportStates(StatesGroup):
    """Support states"""
    waiting_message = State()
