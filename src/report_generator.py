import os
import time

import msal
import pandas as pd
import requests
from dotenv import load_dotenv

from config.config import (
    CAMPAIGN_CLEAN_PATH,
    ORDER_CLEAN_PATH,
)


# ---------------------------------------------------------------------
# GENERAL HELPERS
# ---------------------------------------------------------------------

def safe_divide(numerator, denominator, multiplier=1):
    """Return None when a KPI cannot be calculated safely."""
    if pd.isna(denominator) or denominator == 0:
        return None

    return (numerator / denominator) * multiplier


def format_currency(value):
    """Format a currency KPI for the text report."""
    if value is None or pd.isna(value):
        return "N/A"

    return f"${value:,.2f}"


def format_percent(value):
    """Format a percentage KPI for the text report."""
    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:.2f}%"


def format_ratio(value):
    """Format a ratio KPI for the text report."""
    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:.2f}x"


def get_best_roas_group(df, group_column):
    """Return the group with the highest ROAS among positive-spend rows."""
    grouped = (
        df.groupby(group_column, dropna=True)
        .agg(
            ad_spend_usd=("ad_spend_usd", "sum"),
            attributed_revenue_usd=("attributed_revenue_usd", "sum"),
        )
        .reset_index()
    )

    grouped = grouped[grouped["ad_spend_usd"] > 0].copy()

    if grouped.empty:
        return "Not available", None

    grouped["roas"] = (
        grouped["attributed_revenue_usd"]
        / grouped["ad_spend_usd"]
    )

    best_row = grouped.sort_values(
        by="roas",
        ascending=False,
    ).iloc[0]

    return (
        str(best_row[group_column]),
        float(best_row["roas"]),
    )


# ---------------------------------------------------------------------
# JOB 1 - DAILY BUSINESS SUMMARY
# ---------------------------------------------------------------------

def generate_summary():
    """Generate the latest daily Apple marketing performance summary."""
    print("\n" + "=" * 70)
    print("APPLE MARKETING REPORT GENERATION")
    print("=" * 70)

    if not CAMPAIGN_CLEAN_PATH.exists():
        raise FileNotFoundError(
            "Clean campaign file was not found. "
            "Run data_cleaner.py first.\n"
            f"Expected file: {CAMPAIGN_CLEAN_PATH}"
        )

    if not ORDER_CLEAN_PATH.exists():
        raise FileNotFoundError(
            "Clean order file was not found. "
            "Run data_cleaner.py first.\n"
            f"Expected file: {ORDER_CLEAN_PATH}"
        )

    campaign_df = pd.read_csv(CAMPAIGN_CLEAN_PATH)
    order_df = pd.read_csv(ORDER_CLEAN_PATH)

    campaign_df["report_date"] = pd.to_datetime(
        campaign_df["report_date"],
        errors="coerce",
    )

    order_df["order_date"] = pd.to_datetime(
        order_df["order_date"],
        errors="coerce",
    )

    latest_date = campaign_df["report_date"].max()

    if pd.isna(latest_date):
        raise ValueError(
            "No valid report_date values were found "
            "in the cleaned campaign data."
        )

    campaign_day = campaign_df[
        campaign_df["report_date"] == latest_date
    ].copy()

    order_day = order_df[
        order_df["order_date"] == latest_date
    ].copy()

    ad_spend = campaign_day["ad_spend_usd"].sum()

    total_marketing_cost = (
        campaign_day["ad_spend_usd"].sum()
        + campaign_day["creative_cost_usd"].sum()
        + campaign_day["agency_cost_usd"].sum()
        + campaign_day["marketing_tools_cost_usd"].sum()
    )

    attributed_revenue = campaign_day[
        "attributed_revenue_usd"
    ].sum()

    impressions = campaign_day["impressions"].sum()
    clicks = campaign_day["clicks"].sum()
    new_customers = campaign_day["new_customers"].sum()

    total_revenue = order_day["net_revenue_usd"].sum()
    gross_profit = order_day["gross_profit_usd"].sum()

    roas = safe_divide(
        attributed_revenue,
        ad_spend,
    )

    marketing_roi = safe_divide(
        gross_profit - total_marketing_cost,
        total_marketing_cost,
        multiplier=100,
    )

    cac = safe_divide(
        total_marketing_cost,
        new_customers,
    )

    ctr = safe_divide(
        clicks,
        impressions,
        multiplier=100,
    )

    best_channel, best_channel_roas = get_best_roas_group(
        campaign_day,
        "channel",
    )

    best_campaign, best_campaign_roas = get_best_roas_group(
        campaign_day,
        "campaign_name",
    )

    report_date_text = latest_date.strftime("%d-%b-%Y")
    new_customers_text = f"{int(new_customers):,}"

    summary = f"""Apple Marketing Daily Performance

Report Date: {report_date_text}

Revenue: {format_currency(total_revenue)}
Marketing Spend: {format_currency(total_marketing_cost)}
Attributed Revenue: {format_currency(attributed_revenue)}
ROAS: {format_ratio(roas)}
Marketing ROI: {format_percent(marketing_roi)}
New Customers: {new_customers_text}
CAC: {format_currency(cac)}
CTR: {format_percent(ctr)}

Best Performing Channel by ROAS:
{best_channel} ({format_ratio(best_channel_roas)})

Best Performing Campaign by ROAS:
{best_campaign} ({format_ratio(best_campaign_roas)})"""

    print("\n" + summary)

    return summary


# ---------------------------------------------------------------------
# POWER BI SETTINGS AND AUTHENTICATION
# ---------------------------------------------------------------------

def power_bi_refresh_is_enabled():
    """Return True only when refresh is explicitly enabled in .env."""
    value = os.getenv(
        "POWERBI_REFRESH_ENABLED",
        "false",
    )

    return value.strip().lower() == "true"


def get_power_bi_settings():
    """Read and validate Power BI settings from environment variables."""
    settings = {
        "tenant_id": os.getenv("POWERBI_TENANT_ID"),
        "client_id": os.getenv("POWERBI_CLIENT_ID"),
        "client_secret": os.getenv("POWERBI_CLIENT_SECRET"),
        "workspace_id": os.getenv("POWERBI_WORKSPACE_ID"),
        "dataset_id": os.getenv("POWERBI_DATASET_ID"),
    }

    for key, value in settings.items():
        if value is not None:
            settings[key] = value.strip()

    missing = [
        key
        for key, value in settings.items()
        if not value
        or value.lower().startswith("your_")
    ]

    if missing:
        raise ValueError(
            "Power BI refresh is enabled, but these settings "
            "are missing or still contain placeholders: "
            + ", ".join(missing)
        )

    return settings


def get_power_bi_access_token(settings):
    """Authenticate the service principal and return a Power BI access token."""
    authority = (
        "https://login.microsoftonline.com/"
        + settings["tenant_id"]
    )

    app = msal.ConfidentialClientApplication(
        client_id=settings["client_id"],
        authority=authority,
        client_credential=settings["client_secret"],
    )

    token_result = app.acquire_token_for_client(
        scopes=[
            "https://analysis.windows.net/powerbi/api/.default"
        ]
    )

    access_token = token_result.get("access_token")

    if not access_token:
        error_message = token_result.get(
            "error_description",
            token_result.get(
                "error",
                "Unknown authentication error",
            ),
        )

        raise RuntimeError(
            "Could not authenticate with Power BI. "
            f"Details: {error_message}"
        )

    return access_token


# ---------------------------------------------------------------------
# POWER BI REFRESH STATUS HELPERS
# ---------------------------------------------------------------------

def build_refresh_collection_url(settings):
    """Return the Power BI refresh collection endpoint."""
    return (
        "https://api.powerbi.com/v1.0/myorg/groups/"
        f"{settings['workspace_id']}/datasets/"
        f"{settings['dataset_id']}/refreshes"
    )


def get_refresh_history(settings, headers, top=10):
    """Get recent semantic-model refresh history."""
    history_url = (
        build_refresh_collection_url(settings)
        + f"?$top={top}"
    )

    response = requests.get(
        history_url,
        headers=headers,
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(
            "Could not read Power BI refresh history. "
            f"HTTP {response.status_code}: {response.text}"
        )

    return response.json().get("value", [])


def wait_for_refresh_details(
    status_url,
    headers,
    timeout_seconds=600,
    check_every_seconds=15,
):
    """
    Monitor one known refresh URL.

    Returns True when completed.
    Returns False if this direct status URL isn't usable.
    """
    start_time = time.time()

    print("[INFO] Waiting for Power BI refresh to finish...")

    while time.time() - start_time < timeout_seconds:
        response = requests.get(
            status_url,
            headers=headers,
            timeout=30,
        )

        if response.status_code in {400, 404, 405}:
            print(
                "[INFO] Direct refresh-status URL is not available."
            )
            return False

        if response.status_code not in {200, 202}:
            raise RuntimeError(
                "Could not check Power BI refresh status. "
                f"HTTP {response.status_code}: {response.text}"
            )

        result = response.json()
        status = result.get("status", "Unknown")

        if status == "Completed":
            print(
                "[PASS] Power BI refresh completed successfully."
            )
            return True

        if status in {
            "Failed",
            "Disabled",
            "Cancelled",
            "TimedOut",
        }:
            details = (
                result.get("serviceExceptionJson")
                or result.get("messages")
                or result
            )

            raise RuntimeError(
                "Power BI refresh did not complete successfully. "
                f"Status: {status}. "
                f"Details: {details}"
            )

        print(
            f"[INFO] Power BI refresh status: {status}"
        )

        time.sleep(check_every_seconds)

    raise TimeoutError(
        "Power BI refresh did not finish within "
        f"{timeout_seconds // 60} minutes."
    )


def wait_for_new_refresh_in_history(
    settings,
    headers,
    previous_request_ids,
    preferred_request_id=None,
    timeout_seconds=600,
    check_every_seconds=15,
):
    """
    Find the refresh created by this run and wait until it completes.
    """
    start_time = time.time()

    print(
        "[INFO] Monitoring the new ViaApi refresh "
        "through refresh history..."
    )

    tracked_request_id = None

    while time.time() - start_time < timeout_seconds:
        refreshes = get_refresh_history(
            settings,
            headers,
            top=10,
        )

        current_refresh = None

        if preferred_request_id:
            for refresh in refreshes:
                if (
                    refresh.get("requestId")
                    == preferred_request_id
                ):
                    current_refresh = refresh
                    break

        if current_refresh is None:
            for refresh in refreshes:
                request_id = refresh.get("requestId")
                refresh_type = refresh.get("refreshType")

                if (
                    request_id
                    and request_id not in previous_request_ids
                    and refresh_type in {
                        "ViaApi",
                        "ViaEnhancedApi",
                    }
                ):
                    current_refresh = refresh
                    break

        if current_refresh is None:
            print(
                "[INFO] New refresh has not appeared "
                "in refresh history yet..."
            )
            time.sleep(check_every_seconds)
            continue

        request_id = current_refresh.get("requestId")
        status = current_refresh.get("status", "Unknown")
        refresh_type = current_refresh.get(
            "refreshType",
            "Unknown",
        )

        if tracked_request_id != request_id:
            tracked_request_id = request_id
            print(
                f"[INFO] Tracking refresh request: "
                f"{tracked_request_id}"
            )

        print(
            f"[INFO] Refresh type: {refresh_type} | "
            f"Status: {status}"
        )

        if status == "Completed":
            print(
                "[PASS] Power BI refresh completed successfully."
            )
            return True

        if status in {
            "Failed",
            "Disabled",
            "Cancelled",
            "TimedOut",
        }:
            error_details = current_refresh.get(
                "serviceExceptionJson",
                "",
            )

            raise RuntimeError(
                "Power BI refresh failed. "
                f"Status: {status}. "
                f"Details: {error_details}"
            )

        time.sleep(check_every_seconds)

    raise TimeoutError(
        "Power BI refresh was triggered, but it did not finish "
        f"within {timeout_seconds // 60} minutes."
    )


# ---------------------------------------------------------------------
# JOB 2 - POWER BI REFRESH
# ---------------------------------------------------------------------

def refresh_power_bi():
    """Trigger and monitor the Power BI semantic-model refresh."""
    if not power_bi_refresh_is_enabled():
        print(
            "\n[SKIP] Power BI API refresh is currently disabled."
        )
        print(
            "[INFO] Set POWERBI_REFRESH_ENABLED=true "
            "in your local .env file when ready."
        )
        return False

    settings = get_power_bi_settings()

    print("\n" + "=" * 70)
    print("POWER BI REFRESH")
    print("=" * 70)

    access_token = get_power_bi_access_token(
        settings
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    refresh_url = build_refresh_collection_url(
        settings
    )

    # Capture existing refreshes BEFORE creating a new one.
    # This lets us reliably find the refresh created by this exact run.
    previous_history = get_refresh_history(
        settings,
        headers,
        top=10,
    )

    previous_request_ids = {
        refresh.get("requestId")
        for refresh in previous_history
        if refresh.get("requestId")
    }

    response = requests.post(
        refresh_url,
        headers=headers,
        timeout=30,
    )

    if response.status_code != 202:
        raise RuntimeError(
            "Power BI refresh request failed. "
            f"HTTP {response.status_code}: {response.text}"
        )

    print("[PASS] Power BI refresh request accepted.")

    status_url = response.headers.get("Location")
    request_id = response.headers.get("x-ms-request-id")

    # Option 1: use the exact Location URL returned by Power BI.
    if status_url:
        completed = wait_for_refresh_details(
            status_url,
            headers,
        )

        if completed:
            return True

    # Option 2: construct the official /refreshes/{refreshId} URL
    # using x-ms-request-id when Location isn't present.
    if request_id:
        constructed_status_url = (
            refresh_url
            + "/"
            + request_id
        )

        print(
            "[INFO] Power BI did not provide a usable Location URL."
        )
        print(
            "[INFO] Trying the refresh request ID directly..."
        )

        completed = wait_for_refresh_details(
            constructed_status_url,
            headers,
        )

        if completed:
            return True

    # Option 3: monitor refresh history and identify the new ViaApi refresh.
    print(
        "[INFO] Checking refresh history instead..."
    )

    return wait_for_new_refresh_in_history(
        settings=settings,
        headers=headers,
        previous_request_ids=previous_request_ids,
        preferred_request_id=request_id,
    )


# ---------------------------------------------------------------------
# MAIN REPORT FUNCTION
# ---------------------------------------------------------------------

def generate_report():
    """Generate the daily summary and refresh Power BI when enabled."""
    load_dotenv(override=True)

    summary = generate_summary()

    refresh_power_bi()

    return summary


if __name__ == "__main__":
    generate_report()
