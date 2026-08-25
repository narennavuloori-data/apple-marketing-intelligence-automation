import base64
import os
from pathlib import Path

import msal
import pandas as pd
import requests
from dotenv import load_dotenv

from config.config import (
    BASE_DIR,
    CAMPAIGN_CLEAN_PATH,
    KPI_SUMMARY_PATH,
)
from src.report_generator import generate_summary


GRAPH_SEND_MAIL_URL = "https://graph.microsoft.com/v1.0/me/sendMail"
GRAPH_SCOPES = ["Mail.Send"]


def get_required_env(name):
    value = os.getenv(name)

    if value is None or value.strip() == "":
        raise ValueError(
            f"Missing required environment variable: {name}"
        )

    value = value.strip()

    if value.lower().startswith("your_"):
        raise ValueError(
            f"{name} still contains a placeholder value."
        )

    return value


def get_report_date():
    if not CAMPAIGN_CLEAN_PATH.exists():
        raise FileNotFoundError(
            "Clean campaign file was not found. "
            "Run data_cleaner.py first.\n"
            f"Expected file: {CAMPAIGN_CLEAN_PATH}"
        )

    campaign_df = pd.read_csv(
        CAMPAIGN_CLEAN_PATH,
        usecols=["report_date"],
    )

    campaign_df["report_date"] = pd.to_datetime(
        campaign_df["report_date"],
        errors="coerce",
    )

    latest_date = campaign_df["report_date"].max()

    if pd.isna(latest_date):
        raise ValueError(
            "No valid report_date values were found."
        )

    return latest_date


def load_token_cache(cache_path):
    cache = msal.SerializableTokenCache()

    if cache_path.exists():
        cache.deserialize(
            cache_path.read_text(encoding="utf-8")
        )

    return cache


def save_token_cache(cache, cache_path):
    if cache.has_state_changed:
        cache_path.write_text(
            cache.serialize(),
            encoding="utf-8",
        )


def get_graph_access_token():
    email_address = get_required_env("EMAIL_ADDRESS")
    client_id = get_required_env("EMAIL_CLIENT_ID")

    cache_file_name = os.getenv(
        "EMAIL_TOKEN_CACHE",
        ".email_token_cache.json",
    ).strip()

    cache_path = BASE_DIR / cache_file_name
    cache = load_token_cache(cache_path)

    app = msal.PublicClientApplication(
        client_id=client_id,
        authority="https://login.microsoftonline.com/consumers",
        token_cache=cache,
    )

    result = None

    accounts = app.get_accounts(
        username=email_address
    )

    if accounts:
        result = app.acquire_token_silent(
            scopes=GRAPH_SCOPES,
            account=accounts[0],
        )

    if not result:
        print("\n" + "=" * 70)
        print("ONE-TIME MICROSOFT EMAIL SIGN-IN")
        print("=" * 70)

        flow = app.initiate_device_flow(
            scopes=GRAPH_SCOPES
        )

        if "user_code" not in flow:
            raise RuntimeError(
                "Could not start Microsoft device sign-in. "
                f"Details: {flow}"
            )

        print(flow["message"])

        result = app.acquire_token_by_device_flow(flow)

    save_token_cache(cache, cache_path)

    access_token = result.get("access_token")

    if not access_token:
        error_message = result.get(
            "error_description",
            result.get(
                "error",
                "Unknown Microsoft authentication error",
            ),
        )

        raise RuntimeError(
            "Could not authenticate the Outlook/Hotmail "
            f"account. Details: {error_message}"
        )

    return access_token


def build_attachment(file_path):
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Attachment was not found: {file_path}"
        )

    encoded_content = base64.b64encode(
        file_path.read_bytes()
    ).decode("utf-8")

    return {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": file_path.name,
        "contentType": "text/csv",
        "contentBytes": encoded_content,
    }


def build_email_body(summary, report_url):
    return f'''Hello,

The daily Apple marketing data pipeline completed successfully.

Key Metrics

{summary}

The KPI summary file is attached.

Power BI Dashboard:
{report_url}

Regards,
Automated Marketing Reporting System
'''


def send_email(summary=None):
    load_dotenv(override=True)

    print("\n" + "=" * 70)
    print("APPLE MARKETING REPORT EMAIL")
    print("=" * 70)

    sender_email = get_required_env("EMAIL_ADDRESS")
    receiver_email = get_required_env("EMAIL_RECEIVER")
    report_url = get_required_env("POWERBI_REPORT_URL")

    if not KPI_SUMMARY_PATH.exists():
        raise FileNotFoundError(
            "marketing_kpi_summary.csv was not found. "
            "Run kpi_calculator.py first.\n"
            f"Expected file: {KPI_SUMMARY_PATH}"
        )

    if summary is None:
        summary = generate_summary()

    report_date = get_report_date()

    subject = (
        "Apple Marketing Daily Performance Report - "
        + report_date.strftime("%d %b %Y")
    )

    body = build_email_body(
        summary,
        report_url,
    )

    attachment = build_attachment(
        KPI_SUMMARY_PATH
    )

    access_token = get_graph_access_token()

    message = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "Text",
                "content": body,
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": receiver_email
                    }
                }
            ],
            "attachments": [
                attachment
            ],
        },
        "saveToSentItems": True,
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    print("\n" + "=" * 70)
    print("EMAIL DELIVERY")
    print("=" * 70)

    print(f"From: {sender_email}")
    print(f"To: {receiver_email}")
    print(f"Subject: {subject}")
    print(f"Attachment: {KPI_SUMMARY_PATH.name}")

    response = requests.post(
        GRAPH_SEND_MAIL_URL,
        headers=headers,
        json=message,
        timeout=30,
    )

    if response.status_code != 202:
        raise RuntimeError(
            "Email sending failed. "
            f"HTTP {response.status_code}: "
            f"{response.text}"
        )

    print(
        "[PASS] Email request accepted by Microsoft Graph."
    )
    print(
        "[PASS] Daily marketing report email sent successfully."
    )

    return True


if __name__ == "__main__":
    send_email()
