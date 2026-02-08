from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4


def _now_unix() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp())


DEFAULT_FEATURES: dict[str, Any] = {
    "preview_mode": True,
    "enable_thinking": False,
    "image_generation": False,
    "web_search": False,
    "auto_web_search": False,
    "flags": [],
}


@dataclass
class ChatState:
    model: str = "GLM-4-6-API-V1"
    chat_id: str | None = None
    user_name: str = "User"
    user_language: str = "en-US"
    user_timezone: str = "UTC"
    system_prompt: str | None = None
    features: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_FEATURES))
    runtime_show_thinking: bool = True
    runtime_thinking_color: str = "gray"
    current_user_message_id: str | None = None
    current_user_message_parent_id: str | None = None
    current_assistant_message_id: str | None = None
    current_assistant_content: str = ""
    _uuid_factory: Callable[[], str] = field(default=lambda: str(uuid4()), repr=False)
    _now_factory: Callable[[], int] = field(default=_now_unix, repr=False)

    def begin_turn(self, prompt: str) -> tuple[str, str]:
        user_message_id = self._uuid_factory()
        assistant_message_id = self._uuid_factory()
        self.current_user_message_id = user_message_id
        self.current_assistant_message_id = assistant_message_id
        self.current_assistant_content = ""
        return user_message_id, assistant_message_id

    def apply_assistant_delta(self, delta: str) -> None:
        self.current_assistant_content += delta

    def finish_turn(self) -> None:
        self.current_user_message_parent_id = self.current_assistant_message_id

    def _system_params(self) -> dict[str, Any]:
        if not self.system_prompt:
            return {}
        return {
            "system": self.system_prompt,
            "system_prompt": self.system_prompt,
            "assistant_system_prompt": self.system_prompt,
        }

    def _system_extra(self) -> dict[str, Any]:
        if not self.system_prompt:
            return {}
        return {
            "system": self.system_prompt,
            "system_prompt": self.system_prompt,
            "assistant_system_prompt": self.system_prompt,
            "instructions": self.system_prompt,
        }

    def _feature_value(self, key: str, default: Any) -> Any:
        return self.features.get(key, default)

    def build_new_chat_payload(self, prompt: str) -> dict[str, Any]:
        if not self.current_user_message_id:
            raise RuntimeError("begin_turn must be called before build_new_chat_payload")
        timestamp_ms = self._now_factory() * 1000
        return {
            "chat": {
                "id": "",
                "title": "New Chat",
                "models": [self.model],
                "params": self._system_params(),
                "history": {
                    "messages": {
                        self.current_user_message_id: {
                            "id": self.current_user_message_id,
                            "parentId": None,
                            "childrenIds": [],
                            "role": "user",
                            "content": prompt,
                            "timestamp": self._now_factory(),
                            "models": [self.model],
                        }
                    },
                    "currentId": self.current_user_message_id,
                },
                "tags": [],
                "flags": list(self._feature_value("flags", [])),
                "features": [
                    {"type": "mcp", "server": "vibe-coding", "status": "hidden"},
                    {"type": "mcp", "server": "ppt-maker", "status": "hidden"},
                    {"type": "mcp", "server": "image-search", "status": "hidden"},
                    {"type": "mcp", "server": "deep-research", "status": "hidden"},
                    {"type": "tool_selector", "server": "tool_selector", "status": "hidden"},
                ],
                "mcp_servers": [],
                "enable_thinking": bool(self._feature_value("enable_thinking", False)),
                "auto_web_search": bool(self._feature_value("auto_web_search", False)),
                "message_version": 1,
                "extra": self._system_extra(),
                "timestamp": timestamp_ms,
            }
        }

    def build_completion_payload(self, prompt: str) -> dict[str, Any]:
        if not self.chat_id:
            raise RuntimeError("chat_id is required before completion")
        if not self.current_user_message_id or not self.current_assistant_message_id:
            raise RuntimeError("begin_turn must be called before build_completion_payload")
        now = datetime.now().astimezone()

        features: dict[str, Any] = {
            "preview_mode": bool(self._feature_value("preview_mode", True)),
            "enable_thinking": bool(self._feature_value("enable_thinking", False)),
            "image_generation": bool(self._feature_value("image_generation", False)),
            "web_search": bool(self._feature_value("web_search", False)),
            "auto_web_search": bool(self._feature_value("auto_web_search", False)),
            "flags": list(self._feature_value("flags", [])),
        }

        variables: dict[str, Any] = {
            "{{USER_NAME}}": self.user_name,
            "{{USER_LOCATION}}": "Unknown",
            "{{CURRENT_DATETIME}}": now.strftime("%Y-%m-%d %H:%M:%S"),
            "{{CURRENT_DATE}}": now.strftime("%Y-%m-%d"),
            "{{CURRENT_TIME}}": now.strftime("%H:%M:%S"),
            "{{CURRENT_WEEKDAY}}": now.strftime("%A"),
            "{{CURRENT_TIMEZONE}}": self.user_timezone,
            "{{USER_LANGUAGE}}": self.user_language,
        }
        if self.system_prompt:
            variables["{{SYSTEM_PROMPT}}"] = self.system_prompt

        return {
            "stream": True,
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "signature_prompt": prompt,
            "params": self._system_params(),
            "extra": self._system_extra(),
            "features": features,
            "variables": variables,
            "chat_id": self.chat_id,
            "id": self.current_assistant_message_id,
            "current_user_message_id": self.current_user_message_id,
            "current_user_message_parent_id": self.current_user_message_parent_id,
            "background_tasks": {
                "title_generation": True,
                "tags_generation": True,
            },
        }
