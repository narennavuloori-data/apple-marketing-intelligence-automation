import logging
import os
import zipfile

import msal
import requests
from dotenv import load_dotenv

from config.config import (
    BASE_DIR,
    INCOMING_FOLDER,
    LOG_FILE,
    RAW_FILE_NAME,
    RAW_FILE_PATH,
)


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPES = ["Mail.ReadWrite"]

EXPECTED_SUBJECT = "Apple Marketing Daily Data"
MAX_MESSAGE_PAGES = 5
MESSAGES_PER_PAGE = 50


def setup_logger():
    """Create a simple file logger for the email-download step."""
    LOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    logger = logging.getLogger(
        "apple_marketing_email_downloader"
    )

    logger.setLevel(logging.INFO)

    if not logger.handlers:
        file_handler = logging.FileHandler(
            LOG_FILE,
            encoding="utf-8",
        )

        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )

        file_handler.setFormatter(
            formatter
        )

        logger.addHandler(
            file_handler
        )

    return logger


LOGGER = setup_logger()


def get_required_env(name):
    """Read a required environment variable."""
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


def load_token_cache(cache_path):
    """Load the saved Microsoft token cache if it exists."""
    cache = msal.SerializableTokenCache()

    if cache_path.exists():
        cache.deserialize(
            cache_path.read_text(
                encoding="utf-8"
            )
        )

    return cache


def save_token_cache(cache, cache_path):
    """Save the Microsoft token cache for later silent sign-in."""
    if cache.has_state_changed:
        cache_path.write_text(
            cache.serialize(),
            encoding="utf-8",
        )


def get_graph_access_token():
    """
    Get a Microsoft Graph access token for reading and updating mail.

    The first run after granting Mail.ReadWrite may ask for one-time
    Microsoft device-code consent. Later runs use the token cache.
    """
    email_address = get_required_env(
        "EMAIL_ADDRESS"
    )

    client_id = get_required_env(
        "EMAIL_CLIENT_ID"
    )

    cache_file_name = os.getenv(
        "EMAIL_TOKEN_CACHE",
        ".email_token_cache.json",
    ).strip()

    cache_path = BASE_DIR / cache_file_name

    cache = load_token_cache(
        cache_path
    )

    app = msal.PublicClientApplication(
        client_id=client_id,
        authority=(
            "https://login.microsoftonline.com/"
            "consumers"
        ),
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
        print("ONE-TIME MICROSOFT INBOX PERMISSION")
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

        result = app.acquire_token_by_device_flow(
            flow
        )

    save_token_cache(
        cache,
        cache_path,
    )

    access_token = result.get(
        "access_token"
    )

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


def build_headers(access_token):
    """Create authorization headers for Microsoft Graph."""
    return {
        "Authorization": f"Bearer {access_token}",
    }


def get_sender_address(message):
    """Return the sender email address from a Graph message object."""
    return (
        message.get("from", {})
        .get("emailAddress", {})
        .get("address", "")
        .strip()
        .lower()
    )


def find_latest_matching_email(headers, manager_email):
    """
    Search recent Inbox messages and return the newest unread message
    with the exact subject and expected manager sender address.
    """
    url = (
        f"{GRAPH_BASE_URL}/me/mailFolders/inbox/messages"
    )

    params = {
        "$select": (
            "id,subject,receivedDateTime,from,"
            "hasAttachments,isRead"
        ),
        "$orderby": "receivedDateTime desc",
        "$top": str(MESSAGES_PER_PAGE),
    }

    pages_checked = 0

    while url and pages_checked < MAX_MESSAGE_PAGES:
        response = requests.get(
            url,
            headers=headers,
            params=params if pages_checked == 0 else None,
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(
                "Could not read the Outlook Inbox. "
                f"HTTP {response.status_code}: "
                f"{response.text}"
            )

        data = response.json()

        for message in data.get("value", []):
            subject = (
                message.get("subject")
                or ""
            ).strip()

            sender = get_sender_address(
                message
            )

            is_unread = not message.get(
                "isRead",
                False,
            )

            has_attachments = message.get(
                "hasAttachments",
                False,
            )

            if (
                is_unread
                and has_attachments
                and subject == EXPECTED_SUBJECT
                and sender == manager_email.lower()
            ):
                return message

        url = data.get(
            "@odata.nextLink"
        )

        pages_checked += 1

    return None


def find_expected_attachment(
    message_id,
    headers,
):
    """Find the exact Excel attachment expected by this pipeline."""
    url = (
        f"{GRAPH_BASE_URL}/me/messages/"
        f"{message_id}/attachments"
    )

    response = requests.get(
        url,
        headers=headers,
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(
            "Could not list email attachments. "
            f"HTTP {response.status_code}: "
            f"{response.text}"
        )

    for attachment in response.json().get(
        "value",
        [],
    ):
        attachment_name = (
            attachment.get("name")
            or ""
        ).strip()

        attachment_type = attachment.get(
            "@odata.type",
            "",
        )

        is_inline = attachment.get(
            "isInline",
            False,
        )

        if (
            attachment_name == RAW_FILE_NAME
            and attachment_type
            == "#microsoft.graph.fileAttachment"
            and not is_inline
        ):
            return attachment

    return None


def download_attachment(
    message_id,
    attachment_id,
    headers,
):
    """
    Download the attachment to a temporary file, verify it looks like
    an XLSX archive, then atomically replace the official incoming file.
    """
    INCOMING_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path = RAW_FILE_PATH.with_suffix(
        ".xlsx.download"
    )

    url = (
        f"{GRAPH_BASE_URL}/me/messages/"
        f"{message_id}/attachments/"
        f"{attachment_id}/$value"
    )

    response = requests.get(
        url,
        headers=headers,
        stream=True,
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(
            "Could not download the Excel attachment. "
            f"HTTP {response.status_code}: "
            f"{response.text}"
        )

    try:
        with open(
            temp_path,
            "wb",
        ) as file:
            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):
                if chunk:
                    file.write(chunk)

        if not temp_path.exists():
            raise RuntimeError(
                "The attachment download did not create a file."
            )

        if temp_path.stat().st_size == 0:
            raise RuntimeError(
                "The downloaded attachment is empty."
            )

        if not zipfile.is_zipfile(
            temp_path
        ):
            raise RuntimeError(
                "The downloaded attachment is not a valid XLSX "
                "container."
            )

        os.replace(
            temp_path,
            RAW_FILE_PATH,
        )

    finally:
        if temp_path.exists():
            temp_path.unlink(
                missing_ok=True
            )

    return RAW_FILE_PATH


def mark_message_as_read(
    message_id,
    headers,
):
    """Mark the email as read only after the attachment was saved."""
    url = (
        f"{GRAPH_BASE_URL}/me/messages/"
        f"{message_id}"
    )

    response = requests.patch(
        url,
        headers={
            **headers,
            "Content-Type": "application/json",
        },
        json={
            "isRead": True
        },
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(
            "The attachment was downloaded, but the email "
            "could not be marked as read. "
            f"HTTP {response.status_code}: "
            f"{response.text}"
        )


def download_email_attachment():
    """
    Find the newest unread manager email with the required subject,
    download Apple_Marketing_Raw_Data.xlsx, and mark the email as read.

    Returns:
        Path to the downloaded workbook on success.
        None when no matching unread email exists.
    """
    load_dotenv(
        override=True
    )

    print("\n" + "=" * 70)
    print("APPLE MARKETING EMAIL DOWNLOADER")
    print("=" * 70)

    sender_account = get_required_env(
        "EMAIL_ADDRESS"
    )

    manager_email = get_required_env(
        "EMAIL_RECEIVER"
    )

    print(
        f"Inbox: {sender_account}"
    )

    print(
        f"Expected manager: {manager_email}"
    )

    print(
        f"Expected subject: {EXPECTED_SUBJECT}"
    )

    print(
        f"Expected attachment: {RAW_FILE_NAME}"
    )

    access_token = get_graph_access_token()

    headers = build_headers(
        access_token
    )

    print(
        "\n[INFO] Searching for the latest unread "
        "matching email..."
    )

    message = find_latest_matching_email(
        headers,
        manager_email,
    )

    if message is None:
        print(
            "[INFO] No unread matching manager email was found."
        )

        LOGGER.info(
            "No unread email found with subject '%s' "
            "from %s.",
            EXPECTED_SUBJECT,
            manager_email,
        )

        return None

    message_id = message["id"]

    print(
        "[PASS] Matching unread email found."
    )

    print(
        f"Received: {message.get('receivedDateTime', 'Unknown')}"
    )

    attachment = find_expected_attachment(
        message_id,
        headers,
    )

    if attachment is None:
        LOGGER.error(
            "Matching email found, but required attachment "
            "'%s' was missing.",
            RAW_FILE_NAME,
        )

        raise FileNotFoundError(
            "The matching email was found, but it does not "
            f"contain the required attachment: {RAW_FILE_NAME}"
        )

    print(
        "[PASS] Required Excel attachment found."
    )

    downloaded_path = download_attachment(
        message_id=message_id,
        attachment_id=attachment["id"],
        headers=headers,
    )

    print(
        "[PASS] Attachment downloaded successfully."
    )

    print(
        f"Saved to: {downloaded_path}"
    )

    mark_message_as_read(
        message_id,
        headers,
    )

    print(
        "[PASS] Processed email marked as read."
    )

    LOGGER.info(
        "Downloaded '%s' from %s with subject '%s' "
        "and saved it to '%s'.",
        RAW_FILE_NAME,
        manager_email,
        EXPECTED_SUBJECT,
        downloaded_path,
    )

    print(
        f"[PASS] Download logged to: {LOG_FILE}"
    )

    return downloaded_path


if __name__ == "__main__":
    download_email_attachment()
