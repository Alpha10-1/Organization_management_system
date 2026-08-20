"""E-signature abstraction.

Two backends are supported, selected via the ESIGN_BACKEND env var:

- ``mock`` (default): no external calls at all. Envelopes are created
  in-process and sit in "sent" status until something (a real provider
  webhook, or -- since there's no real provider to callback in dev/test --
  a direct POST to /esign/webhook with the shared secret) marks them
  complete. This is the zero-config path and what the test suite runs
  against.
- ``docusign``: real DocuSign eSignature REST API integration. Requires
  DOCUSIGN_ACCESS_TOKEN, DOCUSIGN_ACCOUNT_ID, and DOCUSIGN_BASE_URL
  (e.g. https://demo.docusign.net/restapi for the developer sandbox).
  NOTE: this has not been exercised against a real DocuSign account in
  this environment -- outbound network access here is allowlisted to a
  fixed set of domains that doesn't include docusign.net, so this backend
  is implemented structurally (correct request shape per DocuSign's
  documented API) but untested end-to-end. Point it at a real sandbox and
  smoke-test send -> sign -> webhook before relying on it in prod.

Callers (routes/contracts.py, routes/change_orders.py) only interact with
the small ESignBackend interface below, so switching providers is a
config change, not a code change -- same shape as get_storage_backend().
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from typing import Optional


class ESignBackend:
    """Common interface every e-signature backend implements."""

    def create_envelope(self, *, subject: str, signer_email: str, signer_name: str, document_ref: str) -> str:
        """Send `document_ref` (a human-readable description of what's
        being signed -- e.g. "Contract #12: FY26 Audit Engagement Letter")
        to `signer_email` for signature. Returns the provider's envelope
        id, which the caller persists on SignatureEnvelope.provider_envelope_id
        and which webhook callbacks will reference to resolve back to it."""
        raise NotImplementedError

    def void_envelope(self, provider_envelope_id: str, reason: str) -> None:
        """Cancel an outstanding envelope (e.g. the contract was edited
        after being sent). Best-effort -- must not raise if the provider
        no longer has the envelope."""
        raise NotImplementedError


class MockESignBackend(ESignBackend):
    """Zero-config backend for local dev and tests. No network calls --
    "sending" just means generating an id and logging to stderr, the same
    zero-cost pattern app.core.email uses for outbound mail in dev."""

    def create_envelope(self, *, subject: str, signer_email: str, signer_name: str, document_ref: str) -> str:
        envelope_id = f"mock-{uuid.uuid4().hex}"
        print(
            f"[esign:mock] envelope={envelope_id} to={signer_name} <{signer_email}> "
            f"subject=\"{subject}\"\n{document_ref}\n",
            file=sys.stderr,
        )
        return envelope_id

    def void_envelope(self, provider_envelope_id: str, reason: str) -> None:
        print(f"[esign:mock] voided envelope={provider_envelope_id} reason=\"{reason}\"", file=sys.stderr)


class DocuSignBackend(ESignBackend):
    """Real DocuSign eSignature REST API integration. See module docstring
    for the untested-in-this-environment caveat."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        account_id: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.access_token = access_token or os.getenv("DOCUSIGN_ACCESS_TOKEN")
        self.account_id = account_id or os.getenv("DOCUSIGN_ACCOUNT_ID")
        self.base_url = (base_url or os.getenv("DOCUSIGN_BASE_URL", "")).rstrip("/")

        if not (self.access_token and self.account_id and self.base_url):
            raise RuntimeError(
                "ESIGN_BACKEND=docusign requires DOCUSIGN_ACCESS_TOKEN, DOCUSIGN_ACCOUNT_ID, "
                "and DOCUSIGN_BASE_URL to be set. See backend/.env.example."
            )

    def _request(self, method: str, path: str, payload: dict) -> dict:
        import urllib.error
        import urllib.request

        url = f"{self.base_url}/v2.1/accounts/{self.account_id}{path}"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:  # pragma: no cover - real API only
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"DocuSign API error ({exc.code}): {detail}") from exc

    def create_envelope(self, *, subject: str, signer_email: str, signer_name: str, document_ref: str) -> str:  # pragma: no cover - real API only
        # A minimal DocuSign "envelope definition" per their documented
        # request shape: one plain-text document, one signer, sent
        # immediately (status="sent" rather than "created"/draft).
        payload = {
            "emailSubject": subject,
            "status": "sent",
            "documents": [
                {
                    "documentBase64": _b64(document_ref.encode("utf-8")),
                    "name": "Document",
                    "fileExtension": "txt",
                    "documentId": "1",
                }
            ],
            "recipients": {
                "signers": [
                    {
                        "email": signer_email,
                        "name": signer_name,
                        "recipientId": "1",
                        "routingOrder": "1",
                        "tabs": {"signHereTabs": [{"anchorString": "/sign/", "anchorUnits": "pixels"}]},
                    }
                ]
            },
        }
        result = self._request("POST", "/envelopes", payload)
        return result["envelopeId"]

    def void_envelope(self, provider_envelope_id: str, reason: str) -> None:  # pragma: no cover - real API only
        self._request("PUT", f"/envelopes/{provider_envelope_id}", {"status": "voided", "voidedReason": reason})


def _b64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode("ascii")


_backend_instance: Optional[ESignBackend] = None


def get_esign_backend() -> ESignBackend:
    """Return the process-wide e-sign backend, built from env vars on
    first use. Cached like a singleton -- same pattern as
    get_storage_backend()."""
    global _backend_instance
    if _backend_instance is None:
        _backend_instance = _build_backend()
    return _backend_instance


def _build_backend() -> ESignBackend:
    backend_name = os.getenv("ESIGN_BACKEND", "mock").strip().lower()
    if backend_name == "docusign":
        return DocuSignBackend()
    if backend_name not in ("mock", ""):
        raise RuntimeError(f"Unknown ESIGN_BACKEND '{backend_name}'. Use 'mock' or 'docusign'.")
    return MockESignBackend()


def reset_esign_backend_cache() -> None:
    """Test hook: force the next get_esign_backend() call to rebuild."""
    global _backend_instance
    _backend_instance = None
