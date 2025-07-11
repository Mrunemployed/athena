import os
import time
import logging
import requests
from typing import Any, Dict

logger = logging.getLogger(__name__)

RELAY_BASE_URL = os.getenv("RELAY_BASE_URL", "https://api.relay.link")


def get_quote(
    data: Dict[str, Any], *, base_url: str | None = None, retries: int = 3
) -> Dict[str, Any] | None:
    """Fetch a quote from the Relay API with basic retry logic.

    The Relay API expects parameters like ``inputToken`` and ``inputAmount``.
    This function now assumes callers provide the parameters already formatted
    according to the Relay documentation.
    """
    base_url = base_url or RELAY_BASE_URL

    payload = data.copy()

    # Translate legacy field names (used in older Relay API versions) to the
    # latest field names expected by the API. This allows the rest of the code
    # base to remain backwards compatible while Relay migrates parameters.
    if "inputToken" in payload and "originCurrency" not in payload:
        payload["originCurrency"] = payload.pop("inputToken")
    if "outputToken" in payload and "destinationCurrency" not in payload:
        payload["destinationCurrency"] = payload.pop("outputToken")
    if "inputAmount" in payload and "amount" not in payload:
        payload["amount"] = payload.pop("inputAmount")
    if "userAddress" in payload and "user" not in payload:
        payload["user"] = payload.pop("userAddress")
    if "receiverAddress" in payload and "recipient" not in payload:
        payload["recipient"] = payload.pop("receiverAddress")
    if "receiver" in payload and "recipient" not in payload:
        payload["recipient"] = payload.pop("receiver")
    logger.info(f"<[PAYLOAD TO RELAY]>  {payload}")
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(
                f"{base_url}/quote",
                json=payload,
                timeout=10,
            )
            try:
                body = response.json()
            except ValueError:
                body = response.text

            if response.ok:
                return body

            logger.error(
                "Relay quote failed: %s - %s (attempt %d/%d)",
                response.status_code,
                body,
                attempt,
                retries,
            )
            if attempt == retries:
                return {"status_code": response.status_code, "body": body}
        except Exception as exc:
            logger.exception(
                "Error fetching quote on attempt %d/%d: %s", attempt, retries, exc
            )
            if attempt == retries:
                return {"status_code": 0, "body": {"error": str(exc)}}

        if attempt < retries:
            time.sleep(1 * attempt)

    return None


def execute_route(
    data: Dict[str, Any], *, base_url: str | None = None
) -> Dict[str, Any] | None:
    """Execute a prepared route through the Relay API.

    The Relay API has changed endpoint paths a few times.  Older versions used
    ``/api/v1/route/execute`` while the latest documentation references
    ``/route``.  To remain compatible we try a set of common paths until one
    succeeds.  Only 404 responses trigger a fallback; other errors are returned
    immediately.
    """

    base_url = base_url or RELAY_BASE_URL
    paths = [
        "/route",
        "/route/execute",
        "/v1/route",
        "/v1/route/execute",
        "/api/v1/route/execute",
    ]

    for path in paths:
        try:
            response = requests.post(
                f"{base_url}{path}",
                json=data,
                timeout=10,
            )
            if response.ok:
                return response.json()
            if response.status_code == 404:
                logger.warning("Relay execute path %s returned 404", path)
                continue
            logger.error(
                "Relay execute failed: %s - %s (path %s)",
                response.status_code,
                response.text,
                path,
            )
            break
        except Exception as exc:
            logger.exception("Error executing route via %s: %s", path, exc)
            break
    return None


def approve_token(
    data: Dict[str, Any], *, base_url: str | None = None
) -> Dict[str, Any] | None:
    """Request token approval transaction from Relay."""
    base_url = base_url or RELAY_BASE_URL
    try:
        response = requests.post(
            f"{base_url}/approve",
            json=data,
            timeout=10,
        )
        if response.ok:
            return response.json()
        logger.error(
            "Relay approve failed: %s - %s", response.status_code, response.text
        )
    except Exception as exc:
        logger.exception("Error approving token: %s", exc)
    return None


def get_route_status(
    route_id: str, *, base_url: str | None = None
) -> Dict[str, Any] | None:
    """Poll the route status from Relay.

    Similar to :func:`execute_route`, the exact endpoint for fetching route
    status has changed across API versions.  Try several common paths until one
    succeeds.
    """

    base_url = base_url or RELAY_BASE_URL
    paths = [
        "/route-status",
        "/v1/route-status",
        "/route/status",
        "/api/v1/route-status",
    ]

    for path in paths:
        try:
            response = requests.get(
                f"{base_url}{path}",
                params={"routeId": route_id},
                timeout=10,
            )
            if response.ok:
                return response.json()
            if response.status_code == 404:
                logger.warning("Relay route-status path %s returned 404", path)
                continue
            logger.error(
                "Relay route-status failed: %s - %s (path %s)",
                response.status_code,
                response.text,
                path,
            )
            break
        except Exception as exc:
            logger.exception("Error getting route status via %s: %s", path, exc)
            break
    return None


def get_intent_status(
    request_id: str, *, base_url: str | None = None
) -> Dict[str, Any] | None:
    """Fetch the status of an intent/deposit step from Relay."""
    base_url = base_url or RELAY_BASE_URL
    paths = [
        "/intents/status",
        "/intent-status",
        "/v1/intents/status",
    ]
    for path in paths:
        try:
            response = requests.get(
                f"{base_url}{path}", params={"requestId": request_id}, timeout=10
            )
            if response.ok:
                return response.json()
            if response.status_code == 404:
                logger.warning("Relay intent-status path %s returned 404", path)
                continue
            logger.error(
                "Relay intent-status failed: %s - %s (path %s)",
                response.status_code,
                response.text,
                path,
            )
            break
        except Exception as exc:
            logger.exception("Error getting intent status via %s: %s", path, exc)
            break
    return None


def get_execution_status(
    request_id: str, *, base_url: str | None = None
) -> Dict[str, Any] | None:
    """Get execution status for a request from Relay API.
    
    This follows the proper Relay API flow: Get Quote -> Check Execution Status -> Execute
    """
    base_url = base_url or RELAY_BASE_URL
    paths = [
        "/execution-status",
        "/execution/status", 
        "/v1/execution-status",
        "/status",
    ]
    
    for path in paths:
        try:
            response = requests.get(
                f"{base_url}{path}",
                params={"requestId": request_id},
                timeout=10,
            )
            if response.ok:
                return response.json()
            if response.status_code == 404:
                logger.warning("Relay execution-status path %s returned 404", path)
                continue
            logger.error(
                "Relay execution-status failed: %s - %s (path %s)",
                response.status_code,
                response.text,
                path,
            )
            break
        except Exception as exc:
            logger.exception("Error getting execution status via %s: %s", path, exc)
            break
    return None


def execute_transaction(
    request_id: str, *, base_url: str | None = None
) -> Dict[str, Any] | None:
    """Execute a transaction after checking execution status.
    
    This should only be called after confirming the execution is ready.
    """
    base_url = base_url or RELAY_BASE_URL
    paths = [
        "/execute",
        "/transaction/execute",
        "/v1/execute",
    ]
    
    for path in paths:
        try:
            response = requests.post(
                f"{base_url}{path}",
                json={"requestId": request_id},
                timeout=30,
            )
            if response.ok:
                return response.json()
            if response.status_code == 404:
                logger.warning("Relay execute path %s returned 404", path)
                continue
            logger.error(
                "Relay execute failed: %s - %s (path %s)",
                response.status_code,
                response.text,
                path,
            )
            break
        except Exception as exc:
            logger.exception("Error executing transaction via %s: %s", path, exc)
            break
    return None
