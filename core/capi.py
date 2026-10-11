import hashlib
import json
import logging
import time
import requests

logger = logging.getLogger(__name__)

META_GRAPH_API_VERSION = "v19.0"

def hash_data(value: str) -> str:
    """SHA-256 hash for Meta Advanced Matching compliance."""
    if not value:
        return ""
    clean = str(value).strip().lower()
    return hashlib.sha256(clean.encode('utf-8')).hexdigest()

def send_meta_capi_event(
    pixel_id: str,
    access_token: str,
    event_name: str,
    event_id: str,
    event_source_url: str = "",
    client_ip: str = "127.0.0.1",
    client_user_agent: str = "",
    fbp: str = "",
    fbc: str = "",
    email: str = "",
    phone: str = "",
    custom_data: dict = None,
    test_event_code: str = ""
) -> dict:
    """
    Dispatches a server-side event to Meta Conversions API (CAPI).
    Deduplicates with browser pixel using the shared event_id.
    """
    if not pixel_id or not access_token:
        return {
            "success": False,
            "error": "Pixel ID or CAPI Access Token is missing."
        }

    url = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}/{pixel_id}/events"

    user_data = {
        "client_ip_address": client_ip or "127.0.0.1",
        "client_user_agent": client_user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }

    if fbp:
        user_data["fbp"] = fbp
    if fbc:
        user_data["fbc"] = fbc
    if email:
        user_data["em"] = [hash_data(email)]
    if phone:
        # Standardize phone for Meta matching: e.g. Bangladesh +880
        clean_phone = "".join(filter(str.isdigit, phone))
        if clean_phone.startswith("0"):
            clean_phone = "88" + clean_phone
        elif not clean_phone.startswith("880") and len(clean_phone) == 10:
            clean_phone = "880" + clean_phone
        user_data["ph"] = [hash_data(clean_phone)]

    event_payload = {
        "event_name": event_name,
        "event_time": int(time.time()),
        "event_id": event_id,
        "event_source_url": event_source_url or "http://localhost:3001/",
        "action_source": "website",
        "user_data": user_data,
        "custom_data": custom_data or {
            "currency": "BDT",
            "value": 0
        }
    }

    body = {
        "data": [event_payload],
    }

    if test_event_code:
        body["test_event_code"] = test_event_code.strip()

    params = {
        "access_token": access_token.strip()
    }

    try:
        response = requests.post(
            url,
            params=params,
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=8
        )
        resp_json = response.json() if response.content else {}
        is_success = response.status_code == 200

        return {
            "success": is_success,
            "status_code": response.status_code,
            "meta_response": resp_json,
            "event_id": event_id
        }
    except requests.exceptions.RequestException as e:
        logger.warning(f"Meta CAPI Request Exception: {e}")
        return {
            "success": False,
            "error": str(e),
            "event_id": event_id,
            "offline_logged": True
        }
