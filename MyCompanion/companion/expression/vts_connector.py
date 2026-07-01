"""
VTube Studio WebSocket Control Bridge

Enterprise-grade async WebSocket link to VTube Studio at ws://127.0.0.1:8001.
Maintains authorization handshakes automatically.
Translates emotional metrics into Live2D expressions and hotkey inputs.
"""

import asyncio
import json
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
except ImportError:
    websockets = None  # type: ignore[assignment]


class VTSConnector:
    """
    Async WebSocket bridge to VTube Studio.

    Handles:
      - Authentication token request / reuse
      - Parameter injection for Live2D expressions
      - Hotkey triggering
      - Automatic reconnection on drop
    """

    PLUGIN_NAME = "MyCompanion"
    PLUGIN_DEVELOPER = "MyCompanion Project"
    RECONNECT_DELAY = 5.0
    HEARTBEAT_INTERVAL = 10.0

    def __init__(self, host: str = "127.0.0.1", port: int = 8001) -> None:
        self._uri = f"ws://{host}:{port}"
        self._ws: Optional["WebSocketClientProtocol"] = None
        self._auth_token: str = ""
        self._authenticated = False
        self._running = False
        self._request_id = 0
        self._connected_event = asyncio.Event()

    @property
    def connected(self) -> bool:
        return self._ws is not None and self._authenticated

    async def run(self) -> None:
        if websockets is None:
            logger.error("websockets not installed; VTS connector disabled")
            return

        self._running = True
        logger.info("VTS connector starting -> %s", self._uri)

        while self._running:
            try:
                async with websockets.connect(self._uri) as ws:
                    self._ws = ws
                    logger.info("VTS WebSocket connected")
                    await self._authenticate()
                    self._connected_event.set()
                    await self._heartbeat_loop()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("VTS connection error; reconnecting in %.0fs", self.RECONNECT_DELAY)
                self._ws = None
                self._authenticated = False
                self._connected_event.clear()
                await asyncio.sleep(self.RECONNECT_DELAY)

    async def stop(self) -> None:
        self._running = False
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass

    async def _authenticate(self) -> None:
        if self._auth_token:
            resp = await self._send_request(
                "AuthenticationRequest",
                {
                    "pluginName": self.PLUGIN_NAME,
                    "pluginDeveloper": self.PLUGIN_DEVELOPER,
                    "authenticationToken": self._auth_token,
                },
            )
            if resp and resp.get("data", {}).get("authenticated", False):
                self._authenticated = True
                logger.info("VTS re-authenticated with stored token")
                return

        resp = await self._send_request(
            "AuthenticationTokenRequest",
            {
                "pluginName": self.PLUGIN_NAME,
                "pluginDeveloper": self.PLUGIN_DEVELOPER,
            },
        )
        if resp:
            self._auth_token = resp.get("data", {}).get("authenticationToken", "")

        if self._auth_token:
            resp = await self._send_request(
                "AuthenticationRequest",
                {
                    "pluginName": self.PLUGIN_NAME,
                    "pluginDeveloper": self.PLUGIN_DEVELOPER,
                    "authenticationToken": self._auth_token,
                },
            )
            if resp and resp.get("data", {}).get("authenticated", False):
                self._authenticated = True
                logger.info("VTS authenticated successfully")
            else:
                logger.warning("VTS authentication failed")
        else:
            logger.warning("VTS token request failed")

    async def set_parameter(self, param_id: str, value: float) -> None:
        if not self.connected:
            return
        await self._send_request(
            "InjectParameterDataRequest",
            {
                "parameterValues": [
                    {"id": param_id, "value": value},
                ],
            },
        )

    async def set_parameters(self, params: dict[str, float]) -> None:
        if not self.connected:
            return
        values = [{"id": k, "value": v} for k, v in params.items()]
        await self._send_request(
            "InjectParameterDataRequest",
            {"parameterValues": values},
        )

    async def trigger_hotkey(self, hotkey_id: str) -> None:
        if not self.connected:
            return
        await self._send_request(
            "HotkeyTriggerRequest",
            {"hotkeyID": hotkey_id},
        )

    async def get_hotkeys(self) -> list[dict]:
        if not self.connected:
            return []
        resp = await self._send_request("HotkeysInCurrentModelRequest", {})
        if resp:
            return resp.get("data", {}).get("availableHotkeys", [])
        return []

    async def get_parameters(self) -> list[dict]:
        if not self.connected:
            return []
        resp = await self._send_request("InputParameterListRequest", {})
        if resp:
            return resp.get("data", {}).get("defaultParameters", [])
        return []

    async def _send_request(self, msg_type: str, data: dict) -> Optional[dict]:
        if self._ws is None:
            return None
        self._request_id += 1
        payload = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": str(self._request_id),
            "messageType": msg_type,
            "data": data,
        }
        try:
            await self._ws.send(json.dumps(payload))
            raw = await asyncio.wait_for(self._ws.recv(), timeout=5.0)
            return json.loads(raw)
        except asyncio.TimeoutError:
            logger.warning("VTS request timeout: %s", msg_type)
            return None
        except Exception:
            logger.exception("VTS request error: %s", msg_type)
            return None

    async def _heartbeat_loop(self) -> None:
        while self._running and self._ws is not None:
            try:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                resp = await self._send_request("APIStateRequest", {})
                if resp is None:
                    logger.warning("VTS heartbeat failed")
                    break
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("VTS heartbeat error")
                break

    @property
    def stats(self) -> dict:
        return {
            "connected": self.connected,
            "authenticated": self._authenticated,
            "uri": self._uri,
            "request_count": self._request_id,
        }
