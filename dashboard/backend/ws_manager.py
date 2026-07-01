"""
WebSocket manager for live dashboard updates.
Bridges KiteTicker (Zerodha WebSocket) to frontend clients.
"""

import json
import asyncio
import logging
from typing import Optional

from fastapi import WebSocket

logger = logging.getLogger("ws_manager")


class WSManager:
    def __init__(self):
        self.active: list[WebSocket] = []
        self.subscriptions: dict[int, set] = {}  # instrument_token -> set of ws clients
        self.kite_ticker = None
        self._ticker_task: Optional[asyncio.Task] = None

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        logger.info(f"Client connected. Total: {len(self.active)}")

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
        # Remove from subscriptions
        for token_set in self.subscriptions.values():
            token_set.discard(ws)
        logger.info(f"Client disconnected. Total: {len(self.active)}")

    async def broadcast(self, message: str):
        """Broadcast to all connected clients."""
        disconnected = []
        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)

    async def send_to(self, ws: WebSocket, message: str):
        """Send to a specific client."""
        try:
            await ws.send_text(message)
        except Exception:
            self.disconnect(ws)

    async def handle_client_message(self, ws: WebSocket, raw: str):
        """Handle incoming messages from frontend clients."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        action = msg.get("action")

        if action == "subscribe":
            tokens = msg.get("tokens", [])
            for token in tokens:
                if token not in self.subscriptions:
                    self.subscriptions[token] = set()
                self.subscriptions[token].add(ws)
            # If KiteTicker is connected, subscribe these tokens
            await self._subscribe_kite_tokens(tokens)
            await self.send_to(ws, json.dumps({
                "type": "subscribed",
                "tokens": tokens,
            }))

        elif action == "unsubscribe":
            tokens = msg.get("tokens", [])
            for token in tokens:
                if token in self.subscriptions:
                    self.subscriptions[token].discard(ws)

    async def _subscribe_kite_tokens(self, tokens: list):
        """Subscribe tokens on the KiteTicker connection."""
        if self.kite_ticker and tokens:
            try:
                self.kite_ticker.subscribe(tokens)
                self.kite_ticker.set_mode(self.kite_ticker.MODE_QUOTE, tokens)
            except Exception as e:
                logger.error(f"Failed to subscribe KiteTicker tokens: {e}")

    async def broadcast_tick(self, ticks: list):
        """Broadcast tick data from KiteTicker to subscribed clients."""
        if not ticks:
            return

        tick_data = []
        for tick in ticks:
            token = tick.get("instrument_token")
            tick_data.append({
                "instrument_token": token,
                "last_price": tick.get("last_price"),
                "change": tick.get("change"),
                "volume": tick.get("volume_traded", tick.get("volume")),
                "ohlc": tick.get("ohlc"),
                "depth": tick.get("depth"),
                "last_trade_time": str(tick.get("last_trade_time", "")),
                "oi": tick.get("oi", 0),
            })

        message = json.dumps({"type": "tick", "data": tick_data})

        # Send to all connected clients (simplified - send all ticks to all)
        await self.broadcast(message)

    async def broadcast_order_update(self, order_data: dict):
        """Broadcast order update to all clients.

        Side effect: if this Kite order matches a row in `nq_orders` (the
        NiftyQuant-executed orders table), patch its status / fill / net.
        This is the hook that turns a PENDING-tracked order into a filled
        journal entry automatically when Kite confirms the fill.

        The DB session is short-lived (open → patch → close) so we don't
        hold a connection across WS frames. Failures are logged but never
        block the broadcast — the UI update is more important than the
        tracking row in the worst case.
        """
        # Patch the nq_orders row first, so the row is up to date by the
        # time the frontend invalidates its query cache on receiving the
        # broadcast message.
        try:
            from database import SessionLocal
            from routers.nq_orders import patch_from_kite_update
            if SessionLocal is not None:
                db = SessionLocal()
                try:
                    patched = patch_from_kite_update(db, order_data)
                    if patched is not None:
                        logger.info(
                            "nq_orders patched: kite_order_id=%s → %s",
                            order_data.get("order_id"), patched.status,
                        )
                finally:
                    db.close()
        except Exception as e:
            # Never let an nq_orders patch failure interfere with the WS push.
            logger.warning(f"nq_orders patch failed (non-fatal): {e}")

        message = json.dumps({"type": "order_update", "data": order_data})
        await self.broadcast(message)

    def init_kite_ticker(self, api_key: str, access_token: str):
        """Initialize KiteTicker connection (called after auth)."""
        try:
            from kiteconnect import KiteTicker
            self.kite_ticker = KiteTicker(api_key, access_token)

            def on_ticks(ws, ticks):
                # Schedule coroutine from sync callback
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self.broadcast_tick(ticks))

            def on_connect(ws, response):
                logger.info("KiteTicker connected")
                # Re-subscribe all active tokens
                all_tokens = list(self.subscriptions.keys())
                if all_tokens:
                    ws.subscribe(all_tokens)
                    ws.set_mode(ws.MODE_QUOTE, all_tokens)

            def on_close(ws, code, reason):
                logger.warning(f"KiteTicker closed: {code} - {reason}")

            def on_error(ws, code, reason):
                logger.error(f"KiteTicker error: {code} - {reason}")

            self.kite_ticker.on_ticks = on_ticks
            self.kite_ticker.on_connect = on_connect
            self.kite_ticker.on_close = on_close
            self.kite_ticker.on_error = on_error

            # Start in a background thread (KiteTicker uses threading internally)
            import threading
            ticker_thread = threading.Thread(target=self.kite_ticker.connect, kwargs={"threaded": True}, daemon=True)
            ticker_thread.start()
            logger.info("KiteTicker thread started")

        except ImportError:
            logger.warning("kiteconnect package not installed - KiteTicker disabled. pip install kiteconnect")
        except Exception as e:
            logger.error(f"Failed to init KiteTicker: {e}")

    def stop_kite_ticker(self):
        """Stop the KiteTicker connection."""
        if self.kite_ticker:
            try:
                self.kite_ticker.close()
            except Exception:
                pass
            self.kite_ticker = None
