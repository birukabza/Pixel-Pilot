import json
import os
from typing import Any, Dict, Optional
from urllib import request, error

from auth_manager import get_auth_manager
from config import Config


class RateLimitError(RuntimeError):
    def __init__(self, message: str, remaining: Optional[int] = None, limit: Optional[int] = None):
        super().__init__(message)
        self.remaining = remaining
        self.limit = limit


def _parse_error_detail(body: str) -> str:
    if not body:
        return "Request failed"
    try:
        data = json.loads(body)
        return data.get("detail", "Request failed")
    except Exception:
        return body.strip() or "Request failed"


class BackendClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or Config.BACKEND_URL).rstrip("/")

    def generate_content(
        self, *, model: str, contents: list[dict], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        auth = get_auth_manager()
        if not auth.access_token:
            raise RuntimeError("Not signed in. Please log in to continue.")

        payload = {"model": model, "contents": contents, "config": config}
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth.access_token}",
        }
        url = f"{self.base_url}/v1/generate"
        req = request.Request(url, data=data, method="POST", headers=headers)

        try:
            with request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8")
            except Exception:
                pass

            detail = _parse_error_detail(body)
            if e.code == 401:
                auth.logout()
                raise RuntimeError("Session expired. Please log in again.") from e
            if e.code == 429:
                limit = None
                remaining = None
                try:
                    limit = int(e.headers.get("X-RateLimit-Limit", "0") or 0)
                    remaining = int(e.headers.get("X-RateLimit-Remaining", "0") or 0)
                except Exception:
                    pass
                raise RateLimitError(detail, remaining=remaining, limit=limit) from e
            raise RuntimeError(detail) from e
        except error.URLError as e:
            raise RuntimeError("Backend unavailable. Is it running?") from e
