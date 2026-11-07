"""Integration adapters for iGOT Karmayogi and NSSTA.

RESEARCH FINDING (see docs/01-RESEARCH-AND-REQUIREMENTS.md §3): no publicly documented, lawfully
accessible iGOT Karmayogi or NSSTA API was found. Therefore:

  * The adapter performs a REAL HTTP request against a configured base URL when credentials exist,
    and reports the REAL outcome.
  * With no configuration it reports NOT_CONFIGURED and says so plainly.
  * No method in this module fabricates an external record. `fetch_catalogue` returns
    `NotConfigured` rather than a fake list. Demonstration content lives in the seeded local course
    catalogue and is labelled DEMONSTRATION, never attributed to a live government API.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.assessment import IntegrationCheck
from app.models.base import IntegrationStatus

log = get_logger("integrations")

CAPABILITIES = ["catalogue.read", "completion.push", "learner_record.read"]


class IntegrationNotConfigured(RuntimeError):
    pass


@dataclass
class ProbeResult:
    status: str
    http_status: int | None
    latency_ms: int | None
    detail: str


class LearningEcosystemAdapter(Protocol):
    name: str
    notes: str

    def configured(self) -> bool: ...
    def probe(self) -> ProbeResult: ...
    def fetch_catalogue(self) -> list[dict]: ...
    def push_completion(self, payload: dict) -> dict: ...
    def fetch_learner_record(self, learner_ref: str) -> dict: ...


class HttpLearningAdapter:
    """Generic HTTP adapter. Endpoint paths are configuration-driven because the real API shape is
    unknown; when the gateway contract is published, only the path constants need to change."""

    name = "generic"
    notes = ""
    catalogue_path = "/courses"
    completion_path = "/completions"
    learner_path = "/learners/{ref}"
    health_path = "/health"

    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token

    def configured(self) -> bool:
        return bool(self._base_url and self._token)

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self._base_url,
            timeout=settings.integration_timeout_seconds,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
                "User-Agent": "PRAMANA/1.0 (competency platform adapter)",
            },
        )

    def probe(self) -> ProbeResult:
        if not self.configured():
            return ProbeResult(
                IntegrationStatus.NOT_CONFIGURED.value, None, None,
                "No base URL or token configured. Adapter is present but inactive.",
            )
        started = time.perf_counter()
        try:
            with self._client() as client:
                resp = client.get(self.health_path)
            latency = int((time.perf_counter() - started) * 1000)
            if resp.status_code in (401, 403):
                return ProbeResult(
                    IntegrationStatus.AUTH_FAILED.value, resp.status_code, latency,
                    "Endpoint reachable but rejected the configured token.",
                )
            if resp.status_code >= 500:
                return ProbeResult(
                    IntegrationStatus.DEGRADED.value, resp.status_code, latency,
                    "Endpoint reachable but returned a server error.",
                )
            if resp.status_code >= 400:
                return ProbeResult(
                    IntegrationStatus.DEGRADED.value, resp.status_code, latency,
                    f"Endpoint reachable, health path returned {resp.status_code}.",
                )
            return ProbeResult(IntegrationStatus.OK.value, resp.status_code, latency,
                               "Health endpoint responded successfully.")
        except httpx.TimeoutException:
            return ProbeResult(
                IntegrationStatus.UNREACHABLE.value, None,
                int((time.perf_counter() - started) * 1000),
                "Request timed out. Network path to the gateway is not available from this host.",
            )
        except httpx.HTTPError as exc:
            return ProbeResult(
                IntegrationStatus.UNREACHABLE.value, None,
                int((time.perf_counter() - started) * 1000),
                f"Connection failed ({type(exc).__name__}).",
            )

    def fetch_catalogue(self) -> list[dict]:
        if not self.configured():
            raise IntegrationNotConfigured(
                f"{self.name}: no credentials configured; live catalogue sync is unavailable"
            )
        with self._client() as client:
            resp = client.get(self.catalogue_path)
            resp.raise_for_status()
            data = resp.json()
        items = data.get("courses") if isinstance(data, dict) else data
        if not isinstance(items, list):
            raise ValueError("Unexpected catalogue payload shape")
        return items

    def push_completion(self, payload: dict) -> dict:
        if not self.configured():
            raise IntegrationNotConfigured(
                f"{self.name}: no credentials configured; cannot push completion records"
            )
        with self._client() as client:
            resp = client.post(self.completion_path, json=payload)
            resp.raise_for_status()
            return {"accepted": True, "http_status": resp.status_code}

    def fetch_learner_record(self, learner_ref: str) -> dict:
        if not self.configured():
            raise IntegrationNotConfigured(
                f"{self.name}: no credentials configured; cannot read learner records"
            )
        with self._client() as client:
            resp = client.get(self.learner_path.format(ref=learner_ref))
            resp.raise_for_status()
            return resp.json()


class IgotAdapter(HttpLearningAdapter):
    name = "igot_karmayogi"
    notes = (
        "Mission Karmayogi digital learning platform (DoPT / Capacity Building Commission / "
        "Karmayogi Bharat). No public API documentation or self-service credentials were located "
        "during research. The adapter performs real requests only when IGOT_BASE_URL and "
        "IGOT_API_TOKEN are supplied by an authorised operator."
    )
    catalogue_path = "/courses"
    completion_path = "/completions"
    learner_path = "/learners/{ref}"
    health_path = "/health"


class NsstaAdapter(HttpLearningAdapter):
    name = "nssta"
    notes = (
        "National Statistical Systems Training Academy (MoSPI). Training calendar is published as "
        "web pages and PDFs; no machine-readable catalogue API was located. Adapter is a boundary "
        "for a future MoSPI-provided feed and is inactive until configured."
    )
    catalogue_path = "/api/trainings"
    health_path = "/"


def build_adapters() -> dict[str, LearningEcosystemAdapter]:
    return {
        "igot_karmayogi": IgotAdapter(settings.igot_base_url, settings.igot_api_token),
        "nssta": NsstaAdapter(settings.nssta_base_url, settings.nssta_api_token),
    }


def host_of(url: str) -> str | None:
    if not url:
        return None
    try:
        return httpx.URL(url).host
    except Exception:  # noqa: BLE001
        return None


def probe_all(db: Session, *, actor_id: uuid.UUID | None = None, persist: bool = True) -> list[dict]:
    results = []
    for name, adapter in build_adapters().items():
        probe = adapter.probe()
        if persist:
            db.add(
                IntegrationCheck(
                    provider=name, status=probe.status, http_status=probe.http_status,
                    latency_ms=probe.latency_ms, detail=probe.detail[:400], checked_by_id=actor_id,
                )
            )
        results.append(
            {
                "provider": name,
                "status": probe.status,
                "configured": adapter.configured(),
                "base_url_host": host_of(getattr(adapter, "_base_url", "")),
                "http_status": probe.http_status,
                "latency_ms": probe.latency_ms,
                "detail": probe.detail,
                "capabilities": CAPABILITIES,
                "notes": adapter.notes,
            }
        )
    if persist:
        db.commit()
    return results


def latest_status(db: Session) -> list[dict]:
    """Current status without making a network call: last persisted probe per provider."""
    out = []
    adapters = build_adapters()
    for name, adapter in adapters.items():
        last = db.scalars(
            select(IntegrationCheck)
            .where(IntegrationCheck.provider == name)
            .order_by(IntegrationCheck.checked_at.desc())
            .limit(1)
        ).first()
        out.append(
            {
                "provider": name,
                "status": last.status if last else IntegrationStatus.NOT_CONFIGURED.value,
                "configured": adapter.configured(),
                "base_url_host": host_of(getattr(adapter, "_base_url", "")),
                "http_status": last.http_status if last else None,
                "latency_ms": last.latency_ms if last else None,
                "detail": last.detail if last else "Never probed. Run a connectivity check.",
                "checked_at": last.checked_at if last else None,
                "capabilities": CAPABILITIES,
                "notes": adapter.notes,
            }
        )
    return out
