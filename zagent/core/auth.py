"""Authentication configuration manager with persistent storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AuthConfig:
    """Manages authentication credentials with persistent storage."""
    
    CONFIG_FILE = ".zagent_auth.json"
    
    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize auth config manager.
        
        Args:
            config_path: Optional path to config file. Defaults to user home directory.
        """
        if config_path is None:
            config_path = Path.home() / self.CONFIG_FILE
        self.config_path = config_path
        self._data: dict[str, Any] = self._load()
    
    def _load(self) -> dict[str, Any]:
        """Load auth config from file."""
        if not self.config_path.exists():
            return {}
        try:
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    
    def _save(self) -> None:
        """Save auth config to file."""
        try:
            self.config_path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            # Make file readable only by user (on Unix-like systems)
            if hasattr(self.config_path, 'chmod'):
                self.config_path.chmod(0o600)
        except OSError as e:
            print(f"Warning: Could not save auth config: {e}")
    
    def save_auth(self, token: str, cookie: str | None = None) -> None:
        """Save authentication credentials.
        
        Args:
            token: API token
            cookie: Optional cookie string
        """
        self._data["token"] = token
        if cookie:
            self._data["cookie"] = cookie
        elif "cookie" in self._data:
            del self._data["cookie"]
        self._save()
    
    def get_token(self) -> str | None:
        """Get saved API token."""
        return self._data.get("token")
    
    def get_cookie(self) -> str | None:
        """Get saved cookie."""
        return self._data.get("cookie")
    
    def has_auth(self) -> bool:
        """Check if authentication is saved."""
        return "token" in self._data
    
    def clear(self) -> None:
        """Clear saved authentication."""
        self._data.clear()
        if self.config_path.exists():
            self.config_path.unlink()
