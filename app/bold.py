import os
import time
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("app.bold")

BOLD_BASE_URL = os.getenv("BOLD_BASE_URL", "https://integrations.api.bold.co")
BOLD_API_KEY = os.getenv("BOLD_API_KEY", "")
BOLD_SECRET = os.getenv("BOLD_SECRET_KEY", "")

HEADERS = {
    "Authorization": f"x-api-key {BOLD_API_KEY}",
    "Content-Type": "application/json",
}


def _expiration_nanos(minutes: int = 60) -> int:
    return int(time.time() * 1e9) + (minutes * 60 * int(1e9))


async def create_payment_link(
    amount_total: float,
    description: str,
    reference: str,
    payer_email: str | None = None,
    expiration_minutes: int = 60,
    currency: str = "COP",
) -> dict:
    url = f"{BOLD_BASE_URL}/online/link/v1"
    body = {
        "amount_type": "CLOSE",
        "amount": {
            "currency": currency,
            "tip_amount": 0,
            "total_amount": int(amount_total),
        },
        "reference": reference,
        "description": description,
        "expiration_date": _expiration_nanos(expiration_minutes),
    }
    if payer_email:
        body["payer_email"] = payer_email
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(url, json=body, headers=HEADERS)
        data = resp.json()
        if resp.status_code >= 400:
            logger.error(f"[Bold] Error creando link ({resp.status_code}): {data}")
            errors = data.get("errors", [])
            error_msg = errors[0].get("errors", str(errors[0])) if errors else "Error creando link"
            raise Exception(error_msg)
        return data["payload"]


async def get_payment_link_status(payment_link: str) -> dict:
    url = f"{BOLD_BASE_URL}/online/link/v1/{payment_link}"
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url, headers=HEADERS)
        data = resp.json()
        if resp.status_code >= 400:
            logger.error(f"[Bold] Error consultando link ({resp.status_code}): {data}")
            raise Exception(data.get("errors", [{}])[0].get("message", "Error consultando link"))
        return data


async def get_payment_methods() -> dict:
    url = f"{BOLD_BASE_URL}/online/link/v1/payment_methods"
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url, headers=HEADERS)
        data = resp.json()
        if resp.status_code >= 400:
            logger.error(f"[Bold] Error consultando metodos ({resp.status_code}): {data}")
            raise Exception(data.get("errors", [{}])[0].get("message", "Error consultando metodos"))
        return data["payload"]
