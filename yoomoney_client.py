"""
YooMoney Payment Client
Handles payment generation and verification via YooMoney API
"""

import aiohttp
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class YooMoneyClient:
    def __init__(self, card_number: str, label: str = "Пожертвование"):
        self.card_number = card_number.replace(" ", "")
        self.label = label
        self.base_url = "https://yoomoney.ru"
        
    def generate_payment_link(self, amount: int, order_id: str) -> str:
        """Generate YooMoney payment link"""
        return f"{self.base_url}/transfer/money?patternId=card2card&moneySource=account&recipient={self.card_number}&sum={amount}&label={order_id}&message={self.label}"
    
    def generate_qr_data(self, amount: int, order_id: str) -> str:
        """Generate QR code data for payment"""
        return f"ST0001|2|Name=SkyNet MVP|PersonalAcc={self.card_number}|Sum={amount}|Purpose={self.label} {order_id}"
    
    async def check_payment(self, order_id: str, expected_amount: int, token: str) -> Dict[str, Any]:
        """Check if payment was received via YooMoney API"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                
                async with session.post(
                    f"{self.base_url}/api/transfer/history",
                    headers=headers,
                    data={"pattern_id": "history", "records": 50}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        operations = data.get("operations", [])
                        
                        for op in operations:
                            op_label = op.get("label", "")
                            op_amount = op.get("amount", 0)
                            op_status = op.get("status", "")
                            
                            if op_label == order_id and op_amount >= expected_amount and op_status == "success":
                                return {"success": True, "amount": op_amount, "datetime": op.get("datetime"), "message": "Payment confirmed"}
                        
                        return {"success": False, "message": "Payment not found"}
                    else:
                        return {"success": False, "message": f"API Error: {resp.status}"}
        except Exception as e:
            logger.error(f"YooMoney API error: {e}")
            return {"success": False, "message": str(e)}
