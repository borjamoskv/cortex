"""CORTEX v4 — SAP OData Client.

Async HTTP client for SAP OData V2 services.
Handles authentication (Basic/OAuth2), CSRF tokens, and entity CRUD.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any
from xml.etree import ElementTree

import httpx

logger = logging.getLogger("cortex.sap.client")

# ─── Exceptions ──────────────────────────────────────────────────────


class SAPConnectionError(Exception):
    """Failed to connect to SAP system."""


class SAPAuthError(Exception):
    """SAP authentication failed."""


class SAPEntityError(Exception):
    """SAP entity operation failed."""


# ─── Configuration ───────────────────────────────────────────────────


@dataclass
class SAPConfig:
    """SAP OData connection configuration."""

    base_url: str
    auth_type: str = "basic"  # basic | oauth2
    username: str = ""
    password: str = ""
    client: str = ""  # SAP client number (e.g. "100")
    oauth_token_url: str = ""
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    timeout: int = 30
    max_retries: int = 3
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def base_url_normalized(self) -> str:
        """Return base URL without trailing slash."""
        return self.base_url.rstrip("/")


# ─── Client ──────────────────────────────────────────────────────────


class SAPClient:
    """Async SAP OData V2 client.

    Handles connection lifecycle, CSRF token management,
    and all entity CRUD operations.
    """

    def __init__(self, config: SAPConfig) -> None:
        self.config = config
        self._http: httpx.AsyncClient | None = None
        self._csrf_token: str | None = None
        self._oauth_token: str | None = None

    async def connect(self) -> dict[str, str]:
        """Establish connection and fetch CSRF token.

        Returns:
            dict with 'status' and 'csrf' keys.

        Raises:
            SAPConnectionError: If connection fails.
            SAPAuthError: If authentication fails.
        """
        self._http = httpx.AsyncClient(
            timeout=self.config.timeout,
            verify=True,
        )

        # Authenticate
        auth_headers = await self._build_auth_headers()

        # Fetch CSRF token via HEAD on service root
        try:
            resp = await self._http.head(
                self.config.base_url_normalized,
                headers={
                    **auth_headers,
                    "x-csrf-token": "Fetch",
                    **self.config.headers,
                },
            )
        except httpx.ConnectError as e:
            raise SAPConnectionError(f"Cannot reach SAP at {self.config.base_url}: {e}") from e

        if resp.status_code == 401:
            raise SAPAuthError("SAP authentication failed — check credentials")
        if resp.status_code == 403:
            raise SAPAuthError("SAP authorization denied — check permissions")
        if resp.status_code >= 400:
            raise SAPConnectionError(
                f"SAP connection error: HTTP {resp.status_code} — {resp.text[:200]}"
            )

        self._csrf_token = resp.headers.get("x-csrf-token", "")
        logger.info("Connected to SAP at %s", self.config.base_url_normalized)

        return {"status": "connected", "csrf": bool(self._csrf_token)}

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http:
            await self._http.aclose()
            self._http = None

    # ─── Entity Operations ───────────────────────────────────────────

    async def read_entity_set(
        self,
        entity_set: str,
        *,
        filters: str | None = None,
        select: list[str] | None = None,
        expand: list[str] | None = None,
        top: int = 100,
        skip: int = 0,
    ) -> list[dict[str, Any]]:
        """Read entities from an OData entity set.

        Args:
            entity_set: SAP entity set name (e.g. 'A_BusinessPartner').
            filters: OData $filter expression.
            select: List of properties to select.
            expand: List of navigation properties to expand.
            top: Maximum number of results.
            skip: Number of results to skip.

        Returns:
            List of entity dicts.
        """
        params: dict[str, str] = {
            "$format": "json",
            "$top": str(top),
            "$skip": str(skip),
        }
        if filters:
            params["$filter"] = filters
        if select:
            params["$select"] = ",".join(select)
        if expand:
            params["$expand"] = ",".join(expand)

        url = f"{self.config.base_url_normalized}/{entity_set}"
        data = await self._request("GET", url, params=params)

        # OData V2 wraps results in d.results
        results = data.get("d", {})
        if isinstance(results, dict):
            return results.get("results", [])
        return []

    async def read_entity(self, entity_set: str, key: str) -> dict[str, Any]:
        """Read a single entity by key.

        Args:
            entity_set: SAP entity set name.
            key: Entity key (e.g. "'1000001'" for string keys).

        Returns:
            Entity dict.
        """
        url = f"{self.config.base_url_normalized}/{entity_set}({key})"
        data = await self._request("GET", url, params={"$format": "json"})
        return data.get("d", {})

    async def create_entity(self, entity_set: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new entity in SAP.

        Args:
            entity_set: Target entity set.
            data: Entity properties.

        Returns:
            Created entity dict from SAP response.
        """
        url = f"{self.config.base_url_normalized}/{entity_set}"
        result = await self._request("POST", url, json_data=data)
        return result.get("d", result)

    async def update_entity(
        self,
        entity_set: str,
        key: str,
        data: dict[str, Any],
        *,
        merge: bool = True,
    ) -> bool:
        """Update an existing entity.

        Args:
            entity_set: Target entity set.
            key: Entity key.
            data: Updated properties.
            merge: If True, uses MERGE (partial update). Otherwise PUT (full replace).

        Returns:
            True if update succeeded.
        """
        url = f"{self.config.base_url_normalized}/{entity_set}({key})"
        method = "PATCH" if merge else "PUT"
        await self._request(method, url, json_data=data)
        return True

    async def metadata(self) -> dict[str, list[str]]:
        """Fetch service $metadata and parse entity types.

        Returns:
            Dict mapping entity set names to their property names.
        """
        url = f"{self.config.base_url_normalized}/$metadata"
        resp = await self._raw_request("GET", url)

        entity_sets: dict[str, list[str]] = {}
        try:
            root = ElementTree.fromstring(resp.text)
            # OData V2 namespace
            ns = {
                "edmx": "http://schemas.microsoft.com/ado/2007/06/edmx",
                "edm": "http://schemas.microsoft.com/ado/2008/09/edm",
            }
            for entity_type in root.iter("{http://schemas.microsoft.com/ado/2008/09/edm}EntityType"):
                name = entity_type.attrib.get("Name", "")
                props = [
                    p.attrib.get("Name", "")
                    for p in entity_type.iter(
                        "{http://schemas.microsoft.com/ado/2008/09/edm}Property"
                    )
                ]
                if name:
                    entity_sets[name] = props
        except ElementTree.ParseError:
            logger.warning("Failed to parse $metadata XML — returning raw")

        return entity_sets

    async def health_check(self) -> dict[str, Any]:
        """Check SAP connectivity and return status."""
        try:
            result = await self.connect()
            return {
                "status": "healthy",
                "base_url": self.config.base_url_normalized,
                "csrf_available": result.get("csrf", False),
                "auth_type": self.config.auth_type,
            }
        except (SAPConnectionError, SAPAuthError) as e:
            return {
                "status": "unhealthy",
                "base_url": self.config.base_url_normalized,
                "error": str(e),
            }

    # ─── Internal ────────────────────────────────────────────────────

    async def _build_auth_headers(self) -> dict[str, str]:
        """Build authentication headers based on config."""
        headers: dict[str, str] = {}

        if self.config.client:
            headers["sap-client"] = self.config.client

        if self.config.auth_type == "basic":
            import base64

            creds = base64.b64encode(
                f"{self.config.username}:{self.config.password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {creds}"

        elif self.config.auth_type == "oauth2":
            token = await self._get_oauth_token()
            headers["Authorization"] = f"Bearer {token}"

        return headers

    async def _get_oauth_token(self) -> str:
        """Obtain OAuth2 token via client credentials grant."""
        if self._oauth_token:
            return self._oauth_token

        if not self._http:
            self._http = httpx.AsyncClient(timeout=self.config.timeout)

        resp = await self._http.post(
            self.config.oauth_token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.config.oauth_client_id,
                "client_secret": self.config.oauth_client_secret,
            },
        )

        if resp.status_code != 200:
            raise SAPAuthError(f"OAuth2 token request failed: {resp.status_code}")

        self._oauth_token = resp.json().get("access_token", "")
        return self._oauth_token

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        json_data: dict | None = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request with retry and error handling."""
        resp = await self._raw_request(method, url, params=params, json_data=json_data)

        if resp.status_code == 204:
            return {}

        try:
            return resp.json()
        except (ConnectionError, OSError, RuntimeError):
            return {"raw": resp.text[:500]}

    async def _raw_request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        json_data: dict | None = None,
    ) -> httpx.Response:
        """Execute raw HTTP request with retry logic."""
        if not self._http:
            raise SAPConnectionError("Client not connected — call connect() first")

        auth_headers = await self._build_auth_headers()
        headers = {
            **auth_headers,
            **self.config.headers,
            "Accept": "application/json",
        }

        # Add CSRF for write operations
        if method in ("POST", "PUT", "PATCH", "DELETE") and self._csrf_token:
            headers["x-csrf-token"] = self._csrf_token

        if json_data is not None:
            headers["Content-Type"] = "application/json"

        last_error: Exception | None = None
        for attempt in range(self.config.max_retries):
            try:
                resp = await self._http.request(
                    method,
                    url,
                    params=params,
                    json=json_data,
                    headers=headers,
                )

                if resp.status_code == 401:
                    raise SAPAuthError("Authentication expired — reconnect required")
                if resp.status_code == 403:
                    raise SAPAuthError(f"Forbidden: {resp.text[:200]}")
                if resp.status_code >= 400:
                    raise SAPEntityError(
                        f"SAP error {resp.status_code}: {resp.text[:300]}"
                    )

                return resp

            except (SAPAuthError, SAPEntityError):
                raise
            except (ConnectionError, OSError, RuntimeError) as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    wait = 2**attempt
                    logger.warning("SAP request retry %d/%d in %ds", attempt + 1, self.config.max_retries, wait)
                    await asyncio.sleep(wait)

        raise SAPConnectionError(f"SAP request failed after {self.config.max_retries} retries: {last_error}")
