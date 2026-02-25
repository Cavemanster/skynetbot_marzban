"""
Database Module
Handles SQLite database operations for users, subscriptions, and payments
"""

import aiosqlite
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "data/users.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Initialize database connection and create tables"""
        self._connection = await aiosqlite.connect(str(self.db_path))
        self._connection.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self):
        """Close database connection"""
        if self._connection:
            await self._connection.close()

    async def _create_tables(self):
        """Create database tables if they don't exist"""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                marzban_username TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_banned INTEGER DEFAULT 0,
                referred_by INTEGER,
                FOREIGN KEY (referred_by) REFERENCES users(telegram_id)
            )
        """)

        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                tariff_id TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                traffic_limit_gb REAL,
                traffic_used_gb REAL DEFAULT 0,
                is_trial INTEGER DEFAULT 0,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        """)

        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                amount REAL,
                tariff_id TEXT,
                status TEXT DEFAULT 'pending',
                payment_comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by INTEGER,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
                FOREIGN KEY (reviewed_by) REFERENCES users(telegram_id)
            )
        """)

        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER UNIQUE,
                bonus_days INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users(telegram_id),
                FOREIGN KEY (referred_id) REFERENCES users(telegram_id)
            )
        """)

        await self._connection.commit()
        logger.info("Database initialized")

    # User Methods

    async def add_user(
        self,
        telegram_id: int,
        username: str,
        marzban_username: str,
        referred_by: Optional[int] = None
    ):
        """Add a new user to the database"""
        await self._connection.execute(
            """
            INSERT INTO users (telegram_id, username, marzban_username, referred_by)
            VALUES (?, ?, ?, ?)
            """,
            (telegram_id, username, marzban_username, referred_by)
        )
        await self._connection.commit()

    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by telegram ID"""
        cursor = await self._connection.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_user_by_marzban_username(self, marzban_username: str) -> Optional[Dict[str, Any]]:
        """Get user by Marzban username"""
        cursor = await self._connection.execute(
            "SELECT * FROM users WHERE marzban_username = ?",
            (marzban_username,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def ban_user(self, telegram_id: int):
        """Ban a user"""
        await self._connection.execute(
            "UPDATE users SET is_banned = 1 WHERE telegram_id = ?",
            (telegram_id,)
        )
        await self._connection.commit()

    async def unban_user(self, telegram_id: int):
        """Unban a user"""
        await self._connection.execute(
            "UPDATE users SET is_banned = 0 WHERE telegram_id = ?",
            (telegram_id,)
        )
        await self._connection.commit()

    async def is_user_banned(self, telegram_id: int) -> bool:
        """Check if user is banned"""
        cursor = await self._connection.execute(
            "SELECT is_banned FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        return bool(row[0]) if row else False

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        cursor = await self._connection.execute("SELECT * FROM users")
        return [dict(row) for row in await cursor.fetchall()]

    async def get_user_count(self) -> int:
        """Get total user count"""
        cursor = await self._connection.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        return row[0]

    async def get_banned_users_count(self) -> int:
        """Get banned users count"""
        cursor = await self._connection.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
        row = await cursor.fetchone()
        return row[0]

    # Subscription Methods

    async def add_subscription(
        self,
        telegram_id: int,
        tariff_id: str,
        expires_at: datetime,
        traffic_limit_gb: float,
        is_trial: bool = False
    ):
        """Add a new subscription"""
        await self._connection.execute(
            """
            INSERT INTO subscriptions 
            (telegram_id, tariff_id, expires_at, traffic_limit_gb, is_trial)
            VALUES (?, ?, ?, ?, ?)
            """,
            (telegram_id, tariff_id, expires_at, traffic_limit_gb, 1 if is_trial else 0)
        )
        await self._connection.commit()

    async def get_active_subscription(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get active subscription for a user"""
        cursor = await self._connection.execute(
            """
            SELECT * FROM subscriptions 
            WHERE telegram_id = ? AND status = 'active' AND expires_at > CURRENT_TIMESTAMP
            ORDER BY expires_at DESC
            LIMIT 1
            """,
            (telegram_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def update_subscription_status(self, subscription_id: int, status: str):
        """Update subscription status"""
        await self._connection.execute(
            "UPDATE subscriptions SET status = ? WHERE id = ?",
            (status, subscription_id)
        )
        await self._connection.commit()

    async def update_subscription_traffic(self, subscription_id: int, traffic_used_gb: float):
        """Update subscription traffic usage"""
        await self._connection.execute(
            "UPDATE subscriptions SET traffic_used_gb = ? WHERE id = ?",
            (traffic_used_gb, subscription_id)
        )
        await self._connection.commit()

    async def get_expired_subscriptions(self) -> List[Dict[str, Any]]:
        """Get all expired active subscriptions"""
        cursor = await self._connection.execute(
            """
            SELECT s.*, u.telegram_id, u.marzban_username 
            FROM subscriptions s
            JOIN users u ON s.telegram_id = u.telegram_id
            WHERE s.status = 'active' AND s.expires_at <= CURRENT_TIMESTAMP
            """
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def get_expiring_subscriptions(self, hours: int) -> List[Dict[str, Any]]:
        """Get subscriptions expiring within specified hours"""
        cursor = await self._connection.execute(
            """
            SELECT s.*, u.telegram_id, u.marzban_username 
            FROM subscriptions s
            JOIN users u ON s.telegram_id = u.telegram_id
            WHERE s.status = 'active' 
            AND s.expires_at <= datetime('now', '+' || ? || ' hours')
            AND s.expires_at > CURRENT_TIMESTAMP
            """,
            (hours,)
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def has_used_trial(self, telegram_id: int) -> bool:
        """Check if user has already used trial"""
        cursor = await self._connection.execute(
            "SELECT COUNT(*) FROM subscriptions WHERE telegram_id = ? AND is_trial = 1",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        return row[0] > 0

    # Payment Methods

    async def add_payment(
        self,
        telegram_id: int,
        amount: float,
        tariff_id: str,
        payment_comment: str
    ) -> int:
        """Add a new payment"""
        cursor = await self._connection.execute(
            """
            INSERT INTO payments (telegram_id, amount, tariff_id, payment_comment)
            VALUES (?, ?, ?, ?)
            """,
            (telegram_id, amount, tariff_id, payment_comment)
        )
        await self._connection.commit()
        return cursor.lastrowid

    async def get_payment(self, payment_id: int) -> Optional[Dict[str, Any]]:
        """Get payment by ID"""
        cursor = await self._connection.execute(
            "SELECT * FROM payments WHERE id = ?",
            (payment_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_pending_payments(self) -> List[Dict[str, Any]]:
        """Get all pending payments"""
        cursor = await self._connection.execute(
            """
            SELECT p.*, u.username as tg_username 
            FROM payments p
            JOIN users u ON p.telegram_id = u.telegram_id
            WHERE p.status = 'pending'
            ORDER BY p.created_at DESC
            """
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def approve_payment(self, payment_id: int, reviewed_by: int):
        """Approve a payment"""
        await self._connection.execute(
            """
            UPDATE payments 
            SET status = 'approved', reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ?
            WHERE id = ?
            """,
            (reviewed_by, payment_id)
        )
        await self._connection.commit()

    async def reject_payment(self, payment_id: int, reviewed_by: int):
        """Reject a payment"""
        await self._connection.execute(
            """
            UPDATE payments 
            SET status = 'rejected', reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ?
            WHERE id = ?
            """,
            (reviewed_by, payment_id)
        )
        await self._connection.commit()

    # Referral Methods

    async def add_referral(self, referrer_id: int, referred_id: int, bonus_days: int = 0):
        """Add a referral record"""
        await self._connection.execute(
            """
            INSERT OR IGNORE INTO referrals (referrer_id, referred_id, bonus_days)
            VALUES (?, ?, ?)
            """,
            (referrer_id, referred_id, bonus_days)
        )
        await self._connection.commit()

    async def get_referral_count(self, referrer_id: int) -> int:
        """Get number of referrals for a user"""
        cursor = await self._connection.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_id = ?",
            (referrer_id,)
        )
        row = await cursor.fetchone()
        return row[0]

    async def get_referrer(self, referred_id: int) -> Optional[int]:
        """Get referrer for a user"""
        cursor = await self._connection.execute(
            "SELECT referrer_id FROM referrals WHERE referred_id = ?",
            (referred_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

    # Statistics Methods

    async def get_statistics(self) -> Dict[str, Any]:
        """Get bot statistics"""
        stats = {}
        
        # User counts
        stats['total_users'] = await self.get_user_count()
        stats['banned_users'] = await self.get_banned_users_count()
        
        # Active subscriptions
        cursor = await self._connection.execute(
            "SELECT COUNT(*) FROM subscriptions WHERE status = 'active' AND expires_at > CURRENT_TIMESTAMP"
        )
        row = await cursor.fetchone()
        stats['active_subscriptions'] = row[0]
        
        # Pending payments
        cursor = await self._connection.execute(
            "SELECT COUNT(*) FROM payments WHERE status = 'pending'"
        )
        row = await cursor.fetchone()
        stats['pending_payments'] = row[0]
        
        return stats
