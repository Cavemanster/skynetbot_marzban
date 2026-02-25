"""
Marzban API Client Module
Handles all interactions with the Marzban panel API
"""

import aiohttp
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MarzbanClient:
    def __init__(
        self,
        panel_url: str,
        username: str,
        password: str,
        subscription_prefix: str = "",
        verify_ssl: bool = True
    ):
        self.panel_url = panel_url.rstrip('/')
        self.username = username
        self.password = password
        self.subscription_prefix = subscription_prefix
        self.verify_ssl = verify_ssl
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _authenticate(self) -> str:
        """Get or refresh access token"""
        if self._access_token and self._token_expires_at:
            if datetime.utcnow() < self._token_expires_at - timedelta(minutes=5):
                return self._access_token

        session = await self._get_session()
        url = f"{self.panel_url}/api/admin/token"
        
        data = {
            "username": self.username,
            "password": self.password
        }

        async with session.post(url, data=data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise AuthenticationError(f"Failed to authenticate: {error_text}")
            
            result = await response.json()
            self._access_token = result["access_token"]
            # Token expires in 24 hours by default
            self._token_expires_at = datetime.utcnow() + timedelta(minutes=1430)
            return self._access_token

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Marzban API"""
        session = await self._get_session()
        url = f"{self.panel_url}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {await self._authenticate()}"
        }

        async with session.request(
            method,
            url,
            json=json_data,
            params=params,
            headers=headers
        ) as response:
            if response.status == 401:
                # Token expired, re-authenticate
                self._access_token = None
                headers["Authorization"] = f"Bearer {await self._authenticate()}"
                async with session.request(
                    method,
                    url,
                    json=json_data,
                    params=params,
                    headers=headers
                ) as retry_response:
                    return await self._parse_response(retry_response)
            return await self._parse_response(response)

    async def _parse_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        if response.status >= 400:
            error_text = await response.text()
            raise APIError(f"API Error {response.status}: {error_text}")
        return await response.json()

    # User Management Methods

    async def create_user(
        self,
        username: str,
        data_limit: int = 0,
        expire: Optional[int] = None,
        proxies: Optional[Dict[str, Dict]] = None,
        inbounds: Optional[Dict[str, list]] = None,
        data_limit_reset_strategy: str = "no_reset",
        status: str = "active"
    ) -> Dict[str, Any]:
        """Create a new user in Marzban"""
        user_data = {
            "username": username,
            "data_limit": data_limit,
            "expire": expire,
            "data_limit_reset_strategy": data_limit_reset_strategy,
            "status": status
        }

        if proxies:
            user_data["proxies"] = proxies
        
        if inbounds:
            user_data["inbounds"] = inbounds

        return await self._request("POST", "/api/user", json_data=user_data)

    async def get_user(self, username: str) -> Dict[str, Any]:
        """Get user information"""
        return await self._request("GET", f"/api/user/{username}")

    async def modify_user(
        self,
        username: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Modify an existing user"""
        return await self._request("PUT", f"/api/user/{username}", json_data=kwargs)

    async def delete_user(self, username: str) -> Dict[str, Any]:
        """Delete a user"""
        return await self._request("DELETE", f"/api/user/{username}")

    async def reset_user_data_usage(self, username: str) -> Dict[str, Any]:
        """Reset user's data usage"""
        return await self._request("POST", f"/api/user/{username}/reset")

    async def revoke_user_subscription(self, username: str) -> Dict[str, Any]:
        """Revoke user's subscription (generate new links)"""
        return await self._request("POST", f"/api/user/{username}/revoke_sub")

    # Subscription Link Methods

    def get_subscription_link(self, username: str) -> str:
        """Generate subscription link for a user"""
        prefix = self.subscription_prefix.rstrip('/') if self.subscription_prefix else self.panel_url
        return f"{prefix}/sub/{username}"

    # System Methods

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        return await self._request("GET", "/api/system")

    async def get_inbounds(self) -> Dict[str, Any]:
        """Get all inbounds"""
        return await self._request("GET", "/api/inbounds")

    async def get_admins(self) -> list:
        """Get list of admins"""
        return await self._request("GET", "/api/admins")

    # Utility Methods

    def calculate_expire_timestamp(self, days: int) -> int:
        """Calculate Unix timestamp for expiry"""
        return int((datetime.utcnow() + timedelta(days=days)).timestamp())

    def format_traffic(self, bytes_value: int) -> str:
        """Format bytes to human readable string"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(bytes_value) < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class APIError(Exception):
    """Raised when API request fails"""
    pass
