"""API client for Kwatt integration."""
import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    FIREBASE_INSTALLATIONS_URL,
    FIREBASE_SIGNUP_URL,
    FIREBASE_TOKEN_URL,
    GOOGLE_ANDROID_CERT,
    GOOGLE_ANDROID_PACKAGE,
    GOOGLE_API_KEY,
    GOOGLE_APP_ID,
    GOOGLE_APP_INSTANCE_ID,
    GOOGLE_FIREBASE_CLIENT,
    QUATT_API_BASE_URL,
)

_LOGGER = logging.getLogger(__name__)

PAIRING_TIMEOUT = 60  # seconds to wait for button press
PAIRING_CHECK_INTERVAL = 2  # seconds between checks


class KwattApiClient:
    """API client for Kwatt/Quatt."""

    def __init__(
        self,
        cic: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the API client."""
        self.cic = cic
        self._session = session
        self._id_token: str | None = None
        self._refresh_token: str | None = None
        self._fid: str | None = None
        self._firebase_auth_token: str | None = None
        self._installation_id: str | None = None
        self._pairing_completed: bool = False

    async def authenticate(self) -> bool:
        """Authenticate with Firebase and Quatt API."""
        try:
            # Step 1: Get Firebase Installation ID
            if not await self._get_firebase_installation():
                return False

            # Step 2: Sign up new user (anonymous)
            if not await self._signup_new_user():
                return False

            # Step 3: Update user profile
            if not await self._update_user_profile():
                return False

            # Step 4: Request pairing with CIC
            if not await self._request_pair():
                return False

            # Step 5: Wait for user to press button on CIC and verify pairing
            if not await self._wait_for_pairing():
                return False

            # Step 6: Get installation ID
            if not await self._get_installation_id():
                return False

            return True
        except Exception as err:
            _LOGGER.error("Authentication failed: %s", err)
            return False

    async def _get_firebase_installation(self) -> bool:
        """Get Firebase Installation ID and auth token."""
        headers = {
            "X-Android-Cert": GOOGLE_ANDROID_CERT,
            "X-Android-Package": GOOGLE_ANDROID_PACKAGE,
            "x-firebase-client": GOOGLE_FIREBASE_CLIENT,
            "x-goog-api-key": GOOGLE_API_KEY,
        }

        payload = {
            "fid": GOOGLE_APP_INSTANCE_ID,
            "appId": GOOGLE_APP_ID,
            "authVersion": "FIS_v2",
            "sdkVersion": "a:19.0.1",
        }

        try:
            async with self._session.post(
                FIREBASE_INSTALLATIONS_URL,
                json=payload,
                headers=headers,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._fid = data.get("fid")
                    auth_token = data.get("authToken", {})
                    self._firebase_auth_token = auth_token.get("token")
                    _LOGGER.debug("Firebase installation successful")
                    return True
                _LOGGER.error(
                    "Firebase installation failed: %s", await response.text()
                )
                return False
        except Exception as err:
            _LOGGER.error("Firebase installation error: %s", err)
            return False

    async def _signup_new_user(self) -> bool:
        """Sign up new anonymous user with Firebase."""
        headers = {
            "X-Android-Cert": GOOGLE_ANDROID_CERT,
            "X-Android-Package": GOOGLE_ANDROID_PACKAGE,
            "X-Client-Version": "Android/Fallback/X24000001/FirebaseCore-Android",
            "X-Firebase-GMPID": GOOGLE_APP_ID,
            "X-Firebase-Client": GOOGLE_FIREBASE_CLIENT,
        }

        payload = {"clientType": "CLIENT_TYPE_ANDROID"}

        url = f"{FIREBASE_SIGNUP_URL}?key={GOOGLE_API_KEY}"

        try:
            async with self._session.post(
                url,
                json=payload,
                headers=headers,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._id_token = data.get("idToken")
                    self._refresh_token = data.get("refreshToken")
                    _LOGGER.debug("User signup successful")
                    return True
                _LOGGER.error("User signup failed: %s", await response.text())
                return False
        except Exception as err:
            _LOGGER.error("User signup error: %s", err)
            return False

    async def _update_user_profile(self) -> bool:
        """Update user profile with name."""
        if not self._id_token:
            return False

        headers = {"Authorization": f"Bearer {self._id_token}"}
        payload = {"firstName": "HomeAssistant", "lastName": "User"}
        url = f"{QUATT_API_BASE_URL}/me"

        try:
            async with self._session.put(
                url,
                json=payload,
                headers=headers,
            ) as response:
                if response.status in (200, 201):
                    _LOGGER.debug("User profile updated")
                    return True
                _LOGGER.error(
                    "User profile update failed: %s", await response.text()
                )
                return False
        except Exception as err:
            _LOGGER.error("User profile update error: %s", err)
            return False

    async def _request_pair(self) -> bool:
        """Request pairing with CIC device."""
        if not self._id_token:
            return False

        headers = {"Authorization": f"Bearer {self._id_token}"}
        payload = {}
        url = f"{QUATT_API_BASE_URL}/me/cic/{self.cic}/requestPair"

        try:
            async with self._session.post(
                url,
                json=payload,
                headers=headers,
            ) as response:
                if response.status in (200, 201, 204):
                    _LOGGER.debug("Pairing request successful")
                    return True
                _LOGGER.error("Pairing request failed: %s", await response.text())
                return False
        except Exception as err:
            _LOGGER.error("Pairing request error: %s", err)
            return False

    async def _wait_for_pairing(self) -> bool:
        """Wait for user to press button on CIC device and verify pairing."""
        if not self._id_token:
            return False

        _LOGGER.info("Waiting for user to press button on CIC device...")

        headers = {"Authorization": f"Bearer {self._id_token}"}
        url = f"{QUATT_API_BASE_URL}/me"

        # Poll for up to PAIRING_TIMEOUT seconds
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < PAIRING_TIMEOUT:
            try:
                async with self._session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Check if CIC is in the user's account
                        result = data.get("result", {})
                        cic_ids = result.get("cicIds", [])

                        if cic_ids and self.cic in cic_ids:
                            _LOGGER.info("Pairing completed successfully!")
                            _LOGGER.warning("Pairing completed successfully!")
                            self._pairing_completed = True
                            return True

                        _LOGGER.debug("Pairing not yet completed, waiting...")
                        _LOGGER.warning("Pairing not yet completed, waiting...")
                    else:
                        _LOGGER.warning("Failed to check pairing status: %s", await response.text())
            except Exception as err:
                _LOGGER.warning("Error checking pairing status: %s", err)

            # Wait before checking again
            await asyncio.sleep(PAIRING_CHECK_INTERVAL)

        _LOGGER.error("Pairing timeout - user did not press button within %s seconds", PAIRING_TIMEOUT)
        return False

    async def _get_installation_id(self) -> bool:
        """Get installation ID from installations endpoint."""
        if not self._id_token:
            return False

        installations = await self.get_installations()

        if not installations:
            _LOGGER.error("No installations found")
            return False

        # Get the first installation (or match by CIC if available)
        for installation in installations:
            external_id = installation.get("externalId")
            if external_id and external_id.startswith("INS-"):
                self._installation_id = external_id
                _LOGGER.info("Installation ID: %s", self._installation_id)
                _LOGGER.warning("Installation ID: %s", self._installation_id)
                return True

        _LOGGER.error("No valid installation ID found")
        return False

    async def refresh_token(self) -> bool:
        """Refresh the authentication token."""
        if not self._refresh_token:
            return False

        headers = {
            "X-Android-Cert": GOOGLE_ANDROID_CERT,
            "X-Android-Package": GOOGLE_ANDROID_PACKAGE,
            "X-Client-Version": "Android/Fallback/X24000001/FirebaseCore-Android",
            "X-Firebase-GMPID": GOOGLE_APP_ID,
            "X-Firebase-Client": GOOGLE_FIREBASE_CLIENT,
        }

        payload = {
            "grantType": "refresh_token",
            "refreshToken": self._refresh_token,
        }

        url = f"{FIREBASE_TOKEN_URL}?key={GOOGLE_API_KEY}"

        try:
            async with self._session.post(
                url,
                json=payload,
                headers=headers,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._id_token = data.get("id_token")
                    self._refresh_token = data.get("refresh_token")
                    _LOGGER.debug("Token refresh successful")
                    return True
                _LOGGER.error("Token refresh failed: %s", await response.text())
                return False
        except Exception as err:
            _LOGGER.error("Token refresh error: %s", err)
            return False

    async def get_installations(self) -> list[dict[str, Any]]:
        """Get list of installations."""
        if not self._id_token:
            return []

        headers = {"Authorization": f"Bearer {self._id_token}"}
        url = f"{QUATT_API_BASE_URL}/me/installations"

        try:
            async with self._session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("result", [])
                _LOGGER.error("Get installations failed: %s", await response.text())
                return []
        except Exception as err:
            _LOGGER.error("Get installations error: %s", err)
            return []

    async def get_cic_data(self) -> dict[str, Any] | None:
        """Get CIC device data."""
        if not self._id_token:
            return None

        headers = {"Authorization": f"Bearer {self._id_token}"}
        url = f"{QUATT_API_BASE_URL}/me/cic/{self.cic}"

        try:
            async with self._session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                _LOGGER.error("Get CIC data failed: %s", await response.text())
                return None
        except Exception as err:
            _LOGGER.error("Get CIC data error: %s", err)
            return None
