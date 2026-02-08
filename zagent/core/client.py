from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Any, Iterator
from urllib.parse import urljoin
from uuid import uuid4

import requests


SECRET = "key-@@@@)))()((9))-xxxx&&&%%%%%"
FE_VERSION = "prod-fe-1.0.220"


class ZAIClient:
    def __init__(self, token: str, base_url: str = "https://chat.z.ai", cookie: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "accept-language": "en-US,en;q=0.9",
                "origin": self.base_url,
                "referer": f"{self.base_url}/",
                "content-type": "application/json",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
                "authorization": f"Bearer {token}",
                "token": token,
                "x-fe-version": FE_VERSION,
            }
        )
        if cookie:
            self.session.headers["cookie"] = cookie

    def _url(self, path: str) -> str:
        return urljoin(f"{self.base_url}/", path.lstrip("/"))

    def _extract_user_id_from_token(self) -> str:
        try:
            payload = self.token.split(".")[1]
            padding = "=" * (-len(payload) % 4)
            decoded = json.loads(base64.urlsafe_b64decode(payload + padding).decode())
            return decoded.get("id", "")
        except Exception:
            return ""

    @staticmethod
    def _js_like_base64(text: str) -> str:
        utf8_bytes = text.encode("utf-8")
        latin1_str = utf8_bytes.decode("latin1")
        return base64.b64encode(latin1_str.encode("latin1")).decode()

    @staticmethod
    def _generate_signature(sorted_payload: str, action: str, timestamp_ms: int) -> str:
        w = timestamp_ms // (5 * 60 * 1000)
        d_hex = hmac.new(SECRET.encode("utf-8"), str(w).encode("utf-8"), hashlib.sha256).hexdigest()
        payload = f"{sorted_payload}|{ZAIClient._js_like_base64(action)}|{timestamp_ms}"
        return hmac.new(d_hex.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def create_chat(self, payload: dict[str, Any]) -> str:
        r = self.session.post(
            self._url("/api/v1/chats/new"),
            params={"token": self.token},
            headers={"accept": "application/json", "referer": f"{self.base_url}/", "x-fe-version": FE_VERSION},
            data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        chat_id = data.get("id")
        if not chat_id:
            raise RuntimeError("create_chat response missing id")
        return chat_id


    def latest_chat_id(self) -> str | None:
        r = self.session.get(
            self._url("/api/v1/chats/?page=1"),
            headers={"accept": "application/json", "referer": f"{self.base_url}/", "x-fe-version": FE_VERSION},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            chat_id = data[0].get("id")
            if isinstance(chat_id, str) and chat_id:
                return chat_id
        return None

    def stream_completion(self, chat_id: str, payload: dict[str, Any]) -> Iterator[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        ts = int(time.time() * 1000)
        request_id = str(uuid4())
        user_id = self._extract_user_id_from_token()
        content = str(payload.get("signature_prompt") or payload.get("messages", [{}])[0].get("content", ""))

        qs = {
            "timestamp": str(ts),
            "requestId": request_id,
            "user_id": user_id,
            "version": "0.0.1",
            "platform": "web",
            "token": self.token,
            "user_agent": self.session.headers["user-agent"],
            "language": "en-US",
            "languages": "en-US,en",
            "timezone": "UTC",
            "cookie_enabled": "true",
            "screen_width": "1536",
            "screen_height": "864",
            "screen_resolution": "1536x864",
            "viewport_height": "772",
            "viewport_width": "744",
            "viewport_size": "744x772",
            "color_depth": "24",
            "pixel_ratio": "1.125",
            "current_url": f"{self.base_url}/c/{chat_id}",
            "pathname": f"/c/{chat_id}",
            "search": "",
            "hash": "",
            "host": "chat.z.ai",
            "hostname": "chat.z.ai",
            "protocol": "https:",
            "referrer": "",
            "title": "New Chat | Z.ai Chat - Free AI powered by GLM-4.7 & GLM-4.6",
            "timezone_offset": "0",
            "local_time": now.isoformat().replace("+00:00", "Z"),
            "utc_time": now.strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "is_mobile": "false",
            "is_touch": "false",
            "max_touch_points": "0",
            "browser_name": "Chrome",
            "os_name": "Windows",
            "signature_timestamp": str(ts),
        }

        sorted_payload = f"requestId,{request_id},timestamp,{ts},user_id,{user_id}"
        signature = self._generate_signature(sorted_payload=sorted_payload, action=content, timestamp_ms=ts)

        resp = self.session.post(
            self._url("/api/v2/chat/completions"),
            params=qs,
            headers={"accept": "*/*", "referer": f"{self.base_url}/c/{chat_id}", "x-signature": signature, "x-fe-version": FE_VERSION},
            data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            timeout=(10, 300), # (connect timeout, read timeout)
            stream=True,
        )
        resp.raise_for_status()

        try:
            for raw_line in resp.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                
                # Strip 'data: ' prefix if present
                content = raw_line
                if content.startswith("data: "):
                    content = content[6:]
                
                if not content or content == "[DONE]":
                    continue
                    
                try:
                    event = json.loads(content)
                    yield event
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            # Silently end stream on network errors during iteration
            # but ensure we've yielded what we have.
            pass
