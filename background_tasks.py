"""
Background Tasks Module
Handles periodic tasks like subscription checks, notifications, and cleanup
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from database import Database
from marzban_client import MarzbanClient

logger = logging.getLogger(__name__)


async def check_expired_subscriptions(db: Database, marzban_client: MarzbanClient, bot):
    """Check and handle expired subscriptions"""
    try:
        expired = await db.get_expired_subscriptions()
        
        for sub in expired:
            try:
                # Delete user from Marzban
                await marzban_client.delete_user(sub["marzban_username"])
                
                # Update subscription status
                await db.update_subscription_status(sub["id"], "expired")
                
                # Notify user
                try:
                    await bot.send_message(
                        sub["telegram_id"],
                        f"⏰ Ваша подписка истекла!\n\n"
                        f"📦 Тариф: {sub['tariff_id']}\n"
                        f"📅 Истекла: {sub['expires_at']}\n\n"
                        f"Нажмите 💰 Тарифы чтобы продлить."
                    )
                except Exception as e:
                    logger.error(f"Failed to notify user {sub['telegram_id']}: {e}")
                
                logger.info(f"Expired subscription processed for user {sub['telegram_id']}")
                
            except Exception as e:
                logger.error(f"Error processing expired subscription {sub['id']}: {e}")
        
        if expired:
            logger.info(f"Processed {len(expired)} expired subscriptions")
            
    except Exception as e:
        logger.error(f"Error in check_expired_subscriptions: {e}")


async def send_expiration_notifications(
    db: Database,
    marzban_client: MarzbanClient,
    bot,
    hours_before: int = 24
):
    """Send notifications for expiring subscriptions"""
    try:
        expiring = await db.get_expiring_subscriptions(hours_before)
        
        for sub in expiring:
            try:
                # Get actual usage from Marzban
                try:
                    marzban_user = await marzban_client.get_user(sub["marzban_username"])
                    traffic_used = marzban_client.format_traffic(marzban_user.get("used_traffic", 0))
                    traffic_limit = marzban_client.format_traffic(marzban_user.get("data_limit", 0))
                except Exception:
                    traffic_used = f"{sub.get('traffic_used_gb', 0):.2f} GB"
                    traffic_limit = f"{sub['traffic_limit_gb']:.2f} GB"
                
                time_left = datetime.fromisoformat(sub["expires_at"]) - datetime.utcnow()
                days_left = time_left.days
                hours_left = time_left.seconds // 3600
                
                text = (
                    f"⚠️ Подписка скоро истекает!\n\n"
                    f"⏳ Осталось: {days_left} дн. {hours_left} ч.\n"
                    f"📊 Трафик: {traffic_used} / {traffic_limit}\n\n"
                    f"Нажмите 💰 Тарифы чтобы продлить."
                )
                
                await bot.send_message(sub["telegram_id"], text)
                logger.info(f"Sent expiration notification to user {sub['telegram_id']}")
                
            except Exception as e:
                logger.error(f"Failed to notify user {sub['telegram_id']}: {e}")
        
        if expiring:
            logger.info(f"Sent {len(expiring)} expiration notifications")
            
    except Exception as e:
        logger.error(f"Error in send_expiration_notifications: {e}")


async def sync_traffic_usage(db: Database, marzban_client: MarzbanClient):
    """Sync traffic usage from Marzban to database"""
    try:
        # Get all active subscriptions
        cursor = await db._connection.execute(
            "SELECT * FROM subscriptions WHERE status = 'active'"
        )
        subscriptions = [dict(row) for row in await cursor.fetchall()]
        
        for sub in subscriptions:
            try:
                # Get user info from Marzban
                user = await db.get_user(sub["telegram_id"])
                if not user:
                    continue
                
                marzban_user = await marzban_client.get_user(user["marzban_username"])
                used_traffic = marzban_user.get("used_traffic", 0)
                used_traffic_gb = used_traffic / (1024 * 1024 * 1024)
                
                # Update database
                await db.update_subscription_traffic(sub["id"], used_traffic_gb)
                
            except Exception as e:
                logger.error(f"Failed to sync traffic for subscription {sub['id']}: {e}")
        
        logger.info(f"Synced traffic for {len(subscriptions)} subscriptions")
        
    except Exception as e:
        logger.error(f"Error in sync_traffic_usage: {e}")


async def cleanup_old_payments(db: Database, days_old: int = 30):
    """Clean up old processed payments"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        cursor = await db._connection.execute(
            """
            SELECT id FROM payments 
            WHERE status IN ('approved', 'rejected') 
            AND reviewed_at < ?
            """,
            (cutoff_date.isoformat(),)
        )
        
        old_payments = [row[0] for row in await cursor.fetchall()]
        
        for payment_id in old_payments:
            await db._connection.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
        
        await db._connection.commit()
        
        if old_payments:
            logger.info(f"Cleaned up {len(old_payments)} old payments")
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_payments: {e}")


async def periodic_tasks(db: Database, marzban_client: MarzbanClient, bot, config):
    """Run all periodic tasks"""
    while True:
        try:
            logger.info("Running periodic tasks...")

            # Check expired subscriptions
            await check_expired_subscriptions(db, marzban_client, bot)

            # Send expiration notifications
            notify_hours = config.get("NOTIFY_BEFORE_EXPIRE_HOURS", [24, 48, 72])
            for hours in notify_hours:
                await send_expiration_notifications(db, marzban_client, bot, hours)

            # Sync traffic usage
            await sync_traffic_usage(db, marzban_client)

            # Cleanup old payments (once a day)
            await cleanup_old_payments(db)

            logger.info("Periodic tasks completed")

        except Exception as e:
            logger.error(f"Error in periodic tasks: {e}")

        # Run every hour
        await asyncio.sleep(3600)


async def start_background_tasks(db: Database, marzban_client: MarzbanClient, bot, config):
    """Start all background tasks"""
    logger.info("Starting background tasks...")

    # Start periodic tasks
    asyncio.create_task(periodic_tasks(db, marzban_client, bot, config))

    logger.info("Background tasks started")
