"""Twilio REST API client.

Handles phone number provisioning per tenant:
  - Search available local numbers in the requested country
  - Purchase a number
  - Configure its voice webhook to point at the tenant's container
  - Release the number on tenant deletion
"""

import httpx

TWILIO_API = "https://api.twilio.com/2010-04-01"


async def provision_number(
    account_sid: str,
    auth_token: str,
    webhook_url: str,
    country_code: str = "US",
) -> dict:
    """Search, purchase, and configure a Twilio number for a tenant.

    Returns {"phone_number": "+1...", "phone_sid": "PN..."}
    """
    auth = (account_sid, auth_token)

    async with httpx.AsyncClient() as client:
        # 1. Find an available local number
        search = await client.get(
            f"{TWILIO_API}/Accounts/{account_sid}/AvailablePhoneNumbers/{country_code}/Local.json",
            params={"VoiceEnabled": "true", "PageSize": 1},
            auth=auth,
            timeout=15,
        )
        search.raise_for_status()
        numbers = search.json().get("available_phone_numbers", [])

        # Fall back to toll-free if no local numbers available
        if not numbers:
            search = await client.get(
                f"{TWILIO_API}/Accounts/{account_sid}/AvailablePhoneNumbers/{country_code}/TollFree.json",
                params={"VoiceEnabled": "true", "PageSize": 1},
                auth=auth,
                timeout=15,
            )
            search.raise_for_status()
            numbers = search.json().get("available_phone_numbers", [])

        if not numbers:
            raise ValueError(f"No voice-enabled numbers available in {country_code}")

        phone_number = numbers[0]["phone_number"]

        # 2. Purchase it with the webhook already set
        buy = await client.post(
            f"{TWILIO_API}/Accounts/{account_sid}/IncomingPhoneNumbers.json",
            data={
                "PhoneNumber": phone_number,
                "VoiceUrl": webhook_url,
                "VoiceMethod": "POST",
            },
            auth=auth,
            timeout=15,
        )
        buy.raise_for_status()
        result = buy.json()

        return {
            "phone_number": result["phone_number"],
            "phone_sid": result["sid"],
        }


async def update_webhook(
    account_sid: str,
    auth_token: str,
    phone_sid: str,
    webhook_url: str,
) -> None:
    """Point an existing purchased number at a new webhook URL."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TWILIO_API}/Accounts/{account_sid}/IncomingPhoneNumbers/{phone_sid}.json",
            data={"VoiceUrl": webhook_url, "VoiceMethod": "POST"},
            auth=(account_sid, auth_token),
            timeout=15,
        )
        resp.raise_for_status()


async def release_number(
    account_sid: str,
    auth_token: str,
    phone_sid: str,
) -> None:
    """Release a purchased number, stopping billing."""
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{TWILIO_API}/Accounts/{account_sid}/IncomingPhoneNumbers/{phone_sid}.json",
            auth=(account_sid, auth_token),
            timeout=15,
        )
        resp.raise_for_status()
