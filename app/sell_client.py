from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status in (429, 500, 502, 503, 504)
    return False


class SellClient:
    def __init__(self, base_url: str, token: str, timeout_s: float = 30.0, search_base_url: Optional[str] = None):
        # Core API (v2)
        self.base_url = base_url.rstrip("/")
        # Search API (v3) suele vivir en el mismo host
        self.search_base_url = (search_base_url or base_url).rstrip("/")
        self._headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        self._timeout = timeout_s
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "SellClient":
        self._client = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @retry(
        retry=retry_if_exception_type(Exception).filter(_is_retryable),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        stop=stop_after_attempt(6),
        reraise=True,
    )
    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self._client:
            raise RuntimeError("SellClient must be used as an async context manager")

        url = f"{self.base_url}{path}"
        resp = await self._client.get(url, headers=self._headers, params=params)
        resp.raise_for_status()
        return resp.json()

    @retry(
        retry=retry_if_exception_type(Exception).filter(_is_retryable),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        stop=stop_after_attempt(6),
        reraise=True,
    )
    async def _post_search(self, path: str, json_body: Dict[str, Any]) -> Dict[str, Any]:
        if not self._client:
            raise RuntimeError("SellClient must be used as an async context manager")

        url = f"{self.search_base_url}{path}"
        resp = await self._client.post(
            url,
            headers={**self._headers, "Content-Type": "application/json"},
            json=json_body,
        )
        resp.raise_for_status()
        return resp.json()

    async def get_deal(self, deal_id: int) -> Dict[str, Any]:
        payload = await self._get(f"/v2/deals/{deal_id}")
        return payload.get("data") or {}

    async def list_deals_by_stage(self, stage_id: int, per_page: int = 100) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        page = 1
        while True:
            payload = await self._get(
                "/v2/deals",
                params={"stage_id": stage_id, "page": page, "per_page": per_page},
            )
            items = payload.get("items") or []
            out.extend([i.get("data") or {} for i in items])
            if len(items) < per_page:
                break
            page += 1
        return out

    # ---------------------------
    # Search API (v3)
    # ---------------------------

    async def get_deal_custom_fields_mapping(self) -> List[Dict[str, Any]]:
        """Mapping de custom fields para Deals (Search API).

        Devuelve items[].data con: id, name, type, search_api_id.
        """
        if not self._client:
            raise RuntimeError("SellClient must be used as an async context manager")
        url = f"{self.search_base_url}/v3/deals/custom_fields"
        resp = await self._client.get(url, headers=self._headers)
        resp.raise_for_status()
        payload = resp.json()
        items = payload.get("items") or []
        return [i.get("data") or {} for i in items]

    async def search_deals(self, *, filter_obj: Dict[str, Any], projection: List[str], per_page: int = 200) -> List[Dict[str, Any]]:
        """Busca deals usando Search API v3 con paginación por cursor."""

        out: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        while True:
            data: Dict[str, Any] = {
                "query": {
                    "projection": [{"name": p} for p in projection],
                    "filter": filter_obj,
                },
                "hits": True,
                "per_page": per_page,
            }
            if cursor:
                data["cursor"] = cursor

            body = {"items": [{"data": data}]}
            payload = await self._post_search("/v3/deals/search", body)

            single = (payload.get("items") or [{}])[0]
            if not single.get("successful", True):
                raise RuntimeError(f"Search API returned unsuccessful response: {single}")

            items = single.get("items") or []
            out.extend([i.get("data") or {} for i in items])

            meta = single.get("meta") or {}
            links = (meta.get("links") or {})
            cursor = links.get("next_page")
            if not cursor:
                break

        return out
