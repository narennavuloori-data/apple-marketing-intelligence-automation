import pandas as pd

from config.config import (
    RAW_FILE_PATH,
    RAW_FILE_NAME,
    CAMPAIGN_SHEET,
    CUSTOMER_SHEET,
    ORDER_SHEET,
    PROCESSED_FOLDER,
    CAMPAIGN_CLEAN_PATH,
    CUSTOMER_CLEAN_PATH,
    ORDER_CLEAN_PATH,
)


CAMPAIGN_NUMERIC_COLUMNS = [
    "planned_budget_usd",
    "ad_spend_usd",
    "creative_cost_usd",
    "agency_cost_usd",
    "marketing_tools_cost_usd",
    "impressions",
    "reach",
    "video_views",
    "engagements",
    "clicks",
    "landing_page_sessions",
    "leads",
    "add_to_cart",
    "conversions",
    "new_customers",
    "returning_customers",
    "units_sold",
    "attributed_revenue_usd",
    "email_sent",
    "email_delivered",
    "email_opens",
    "email_clicks",
    "unsubscribes",
]

CAMPAIGN_COUNT_COLUMNS = [
    "impressions",
    "reach",
    "video_views",
    "engagements",
    "clicks",
    "landing_page_sessions",
    "leads",
    "add_to_cart",
    "conversions",
    "new_customers",
    "returning_customers",
    "units_sold",
    "email_sent",
    "email_delivered",
    "email_opens",
    "email_clicks",
    "unsubscribes",
]

ORDER_NUMERIC_COLUMNS = [
    "units",
    "unit_price_usd",
    "gross_order_value_usd",
    "discount_amount_usd",
    "refund_amount_usd",
    "net_revenue_usd",
    "cogs_usd",
    "gross_profit_usd",
]


def print_section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def remove_duplicates(df, primary_key, sheet_name):
    """Remove exact duplicates, then keep one row for each primary key."""
    rows_before = len(df)

    df = df.drop_duplicates().copy()
    exact_removed = rows_before - len(df)

    rows_before_key_check = len(df)

    df = df.drop_duplicates(
        subset=[primary_key],
        keep="first",
    ).copy()

    duplicate_key_removed = rows_before_key_check - len(df)

    print(
        f"{sheet_name}: "
        f"{exact_removed:,} exact duplicates removed, "
        f"{duplicate_key_removed:,} remaining duplicate key rows removed."
    )

    return df


def clean_text(df):
    """Trim spaces, standardize common missing text and fix case differences."""
    missing_text = {
        "",
        "na",
        "n/a",
        "null",
        "none",
        "nan",
    }

    text_columns = df.select_dtypes(
        include=["object", "string"]
    ).columns

    for column in text_columns:
        series = df[column].astype("string").str.strip()

        missing_mask = series.str.lower().isin(missing_text)
        series = series.mask(missing_mask, pd.NA)

        # Use the most common spelling as the standard spelling.
        valid_values = series.dropna()

        if not valid_values.empty:
            value_counts = valid_values.value_counts()
            case_map = {}

            for value in value_counts.index:
                key = value.casefold()

                if key not in case_map:
                    case_map[key] = value

            series = series.map(
                lambda value: (
                    case_map.get(value.casefold(), value)
                    if pd.notna(value)
                    else pd.NA
                )
            )

        df[column] = series

    return df


def clean_country(series):
    """Standardize common United States name variations."""
    country_map = {
        "usa": "United States",
        "u.s.": "United States",
        "us": "United States",
        "united states": "United States",
    }

    return series.map(
        lambda value: (
            country_map.get(value.casefold(), value)
            if pd.notna(value)
            else pd.NA
        )
    )


def clean_channel(series):
    """Standardize known channel variations."""
    channel_map = {
        "instagram ads": "Instagram",
        "instagram": "Instagram",
    }

    return series.map(
        lambda value: (
            channel_map.get(value.casefold(), value)
            if pd.notna(value)
            else pd.NA
        )
    )


def clean_numeric_columns(df, columns):
    """Remove currency formatting and convert values to numeric."""
    for column in columns:
        series = df[column].astype("string")

        series = series.str.replace(
            "$",
            "",
            regex=False,
        )

        series = series.str.replace(
            ",",
            "",
            regex=False,
        )

        series = series.str.strip()

        df[column] = pd.to_numeric(
            series,
            errors="coerce",
        )

    return df


def clean_boolean(series):
    """Convert common boolean variations to True, False or blank."""
    true_values = {
        "yes",
        "y",
        "true",
        "1",
    }

    false_values = {
        "no",
        "n",
        "false",
        "0",
    }

    def convert(value):
        if pd.isna(value):
            return pd.NA

        value = str(value).strip().lower()

        if value in true_values:
            return True

        if value in false_values:
            return False

        return pd.NA

    return series.map(convert).astype("boolean")


def clean_date(series, include_time=False):
    """Convert mixed ISO and DD/MM/YYYY dates safely."""

    text = series.astype("string").str.strip()

    parsed = pd.Series(
        pd.NaT,
        index=series.index,
        dtype="datetime64[ns]",
    )

    # 1. Parse ISO-style dates first: YYYY-MM-DD
    iso_mask = text.str.match(
        r"^\d{4}-\d{2}-\d{2}",
        na=False,
    )

    parsed.loc[iso_mask] = pd.to_datetime(
        text.loc[iso_mask],
        errors="coerce",
        yearfirst=True,
    )

    # 2. Parse remaining dates as DD/MM/YYYY
    remaining_mask = ~iso_mask & text.notna()

    parsed.loc[remaining_mask] = pd.to_datetime(
        text.loc[remaining_mask],
        errors="coerce",
        dayfirst=True,
    )

    if include_time:
        return parsed.dt.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    return parsed.dt.strftime(
        "%Y-%m-%d"
    )


def clean_campaign_data(campaign_df):
    print_section("1. CLEANING CAMPAIGN DATA")

    campaign_df = remove_duplicates(
        campaign_df,
        "record_id",
        CAMPAIGN_SHEET,
    )

    campaign_df = clean_text(
        campaign_df
    )

    campaign_df["country"] = clean_country(
        campaign_df["country"]
    )

    campaign_df["channel"] = clean_channel(
        campaign_df["channel"]
    )

    # Use Unknown only where it is a useful reporting category.
    for column in [
        "platform",
        "city",
        "audience_segment",
        "device_type",
    ]:
        campaign_df[column] = campaign_df[
            column
        ].fillna("Unknown")

    campaign_df = clean_numeric_columns(
        campaign_df,
        CAMPAIGN_NUMERIC_COLUMNS,
    )

    # Negative campaign metrics are invalid in this project.
    for column in CAMPAIGN_NUMERIC_COLUMNS:
        campaign_df[column] = campaign_df[
            column
        ].clip(lower=0)

    # Fix impossible funnel relationships.
    campaign_df["reach"] = campaign_df[
        ["reach", "impressions"]
    ].min(axis=1)

    campaign_df["clicks"] = campaign_df[
        ["clicks", "impressions"]
    ].min(axis=1)

    campaign_df["landing_page_sessions"] = campaign_df[
        ["landing_page_sessions", "clicks"]
    ].min(axis=1)

    campaign_df["add_to_cart"] = campaign_df[
        ["add_to_cart", "landing_page_sessions"]
    ].min(axis=1)

    campaign_df["conversions"] = campaign_df[
        ["conversions", "add_to_cart", "clicks"]
    ].min(axis=1)

    campaign_df["new_customers"] = campaign_df[
        ["new_customers", "conversions"]
    ].min(axis=1)

    campaign_df["email_delivered"] = campaign_df[
        ["email_delivered", "email_sent"]
    ].min(axis=1)

    campaign_df["email_opens"] = campaign_df[
        ["email_opens", "email_delivered"]
    ].min(axis=1)

    campaign_df["email_clicks"] = campaign_df[
        ["email_clicks", "email_opens"]
    ].min(axis=1)

    for column in CAMPAIGN_COUNT_COLUMNS:
        campaign_df[column] = (
            campaign_df[column]
            .round()
            .astype("Int64")
        )

    for column in [
        "planned_budget_usd",
        "ad_spend_usd",
        "creative_cost_usd",
        "agency_cost_usd",
        "marketing_tools_cost_usd",
        "attributed_revenue_usd",
    ]:
        campaign_df[column] = campaign_df[
            column
        ].round(2)

    campaign_df["report_date"] = clean_date(
        campaign_df["report_date"]
    )

    campaign_df["ingestion_timestamp"] = clean_date(
        campaign_df["ingestion_timestamp"],
        include_time=True,
    )

    print(
        f"Campaign rows after cleaning: "
        f"{len(campaign_df):,}"
    )

    return campaign_df


def clean_customer_data(
    customer_df,
    valid_campaign_ids,
):
    print_section("2. CLEANING CUSTOMER DATA")

    customer_df = remove_duplicates(
        customer_df,
        "customer_id",
        CUSTOMER_SHEET,
    )

    customer_df = clean_text(
        customer_df
    )

    customer_df["country"] = clean_country(
        customer_df["country"]
    )

    customer_df["acquisition_channel"] = clean_channel(
        customer_df["acquisition_channel"]
    )

    for column in [
        "acquisition_platform",
        "city",
        "gender",
        "primary_product_interest",
    ]:
        customer_df[column] = customer_df[
            column
        ].fillna("Unknown")

    customer_df["marketing_consent"] = clean_boolean(
        customer_df["marketing_consent"]
    )

    customer_df["loyalty_member"] = clean_boolean(
        customer_df["loyalty_member"]
    )

    for column in [
        "acquisition_date",
        "first_purchase_date",
        "last_purchase_date",
        "churn_date",
    ]:
        customer_df[column] = clean_date(
            customer_df[column]
        )

    customer_df["ingestion_timestamp"] = clean_date(
        customer_df["ingestion_timestamp"],
        include_time=True,
    )

    # Only churned customers should have a churn date.
    non_churned = (
        customer_df["customer_status"] != "Churned"
    )

    customer_df.loc[
        non_churned,
        "churn_date",
    ] = pd.NA

    # Invalid acquisition campaign IDs become unattributed.
    invalid_campaign = (
        customer_df["acquisition_campaign_id"].notna()
        & ~customer_df[
            "acquisition_campaign_id"
        ].isin(valid_campaign_ids)
    )

    invalid_campaign_count = int(
        invalid_campaign.sum()
    )

    customer_df.loc[
        invalid_campaign,
        "acquisition_campaign_id",
    ] = pd.NA

    print(
        "Invalid acquisition campaign IDs "
        f"changed to blank: "
        f"{invalid_campaign_count:,}"
    )

    print(
        f"Customer rows after cleaning: "
        f"{len(customer_df):,}"
    )

    return customer_df


def clean_order_data(
    order_df,
    valid_customer_ids,
    valid_campaign_ids,
):
    print_section("3. CLEANING ORDER DATA")

    order_df = remove_duplicates(
        order_df,
        "order_id",
        ORDER_SHEET,
    )

    order_df = clean_text(
        order_df
    )

    order_df["country"] = clean_country(
        order_df["country"]
    )

    for column in [
        "sales_channel",
        "device_type",
    ]:
        order_df[column] = order_df[
            column
        ].fillna("Unknown")

    order_df["source_file_name"] = order_df[
        "source_file_name"
    ].fillna(RAW_FILE_NAME)

    order_df["is_first_order"] = clean_boolean(
        order_df["is_first_order"]
    )

    order_df["is_repeat_order"] = clean_boolean(
        order_df["is_repeat_order"]
    )

    order_df = clean_numeric_columns(
        order_df,
        ORDER_NUMERIC_COLUMNS,
    )

    for column in ORDER_NUMERIC_COLUMNS:
        order_df[column] = order_df[
            column
        ].clip(lower=0)

    order_df["units"] = (
        order_df["units"]
        .round()
        .astype("Int64")
    )

    # Recalculate derived financial values.
    order_df["net_revenue_usd"] = (
        order_df["gross_order_value_usd"]
        - order_df["discount_amount_usd"]
        - order_df["refund_amount_usd"]
    ).round(2)

    order_df["gross_profit_usd"] = (
        order_df["net_revenue_usd"]
        - order_df["cogs_usd"]
    ).round(2)

    for column in [
        "unit_price_usd",
        "gross_order_value_usd",
        "discount_amount_usd",
        "refund_amount_usd",
        "net_revenue_usd",
        "cogs_usd",
        "gross_profit_usd",
    ]:
        order_df[column] = order_df[
            column
        ].round(2)

    order_df["order_date"] = clean_date(
        order_df["order_date"]
    )

    order_df["order_timestamp"] = clean_date(
        order_df["order_timestamp"],
        include_time=True,
    )

    order_df["ingestion_timestamp"] = clean_date(
        order_df["ingestion_timestamp"],
        include_time=True,
    )

    # Remove orders that cannot join to a valid customer.
    invalid_customer = (
        order_df["customer_id"].isna()
        | ~order_df["customer_id"].isin(
            valid_customer_ids
        )
    )

    invalid_customer_count = int(
        invalid_customer.sum()
    )

    order_df = order_df.loc[
        ~invalid_customer
    ].copy()

    print(
        "Orders removed because customer_id "
        f"was invalid: "
        f"{invalid_customer_count:,}"
    )

    # Keep the order, but remove invalid campaign attribution.
    invalid_campaign = (
        order_df["attributed_campaign_id"].notna()
        & ~order_df[
            "attributed_campaign_id"
        ].isin(valid_campaign_ids)
    )

    invalid_campaign_count = int(
        invalid_campaign.sum()
    )

    order_df.loc[
        invalid_campaign,
        "attributed_campaign_id",
    ] = pd.NA

    print(
        "Invalid attributed campaign IDs "
        f"changed to blank: "
        f"{invalid_campaign_count:,}"
    )

    print(
        f"Order rows after cleaning: "
        f"{len(order_df):,}"
    )

    return order_df


def clean_data():
    print_section("APPLE MARKETING DATA CLEANING")
    print(f"Input file: {RAW_FILE_PATH}")

    if not RAW_FILE_PATH.exists():
        raise FileNotFoundError(
            f"Raw Excel file was not found: "
            f"{RAW_FILE_PATH}"
        )

    dataframes = pd.read_excel(
        RAW_FILE_PATH,
        sheet_name=[
            CAMPAIGN_SHEET,
            CUSTOMER_SHEET,
            ORDER_SHEET,
        ],
        engine="openpyxl",
    )

    campaign_df = dataframes[
        CAMPAIGN_SHEET
    ]

    customer_df = dataframes[
        CUSTOMER_SHEET
    ]

    order_df = dataframes[
        ORDER_SHEET
    ]

    print("\nRows before cleaning:")
    print(
        f"  - Campaigns: "
        f"{len(campaign_df):,}"
    )
    print(
        f"  - Customers: "
        f"{len(customer_df):,}"
    )
    print(
        f"  - Orders: "
        f"{len(order_df):,}"
    )

    # Campaigns are cleaned first because the other tables reference them.
    campaign_df = clean_campaign_data(
        campaign_df
    )

    valid_campaign_ids = set(
        campaign_df["campaign_id"]
        .dropna()
        .astype("string")
    )

    # Customers are cleaned next because orders reference customer IDs.
    customer_df = clean_customer_data(
        customer_df,
        valid_campaign_ids,
    )

    valid_customer_ids = set(
        customer_df["customer_id"]
        .dropna()
        .astype("string")
    )

    order_df = clean_order_data(
        order_df,
        valid_customer_ids,
        valid_campaign_ids,
    )

    PROCESSED_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

    campaign_df.to_csv(
        CAMPAIGN_CLEAN_PATH,
        index=False,
    )

    customer_df.to_csv(
        CUSTOMER_CLEAN_PATH,
        index=False,
    )

    order_df.to_csv(
        ORDER_CLEAN_PATH,
        index=False,
    )

    print_section("CLEANING SUMMARY")

    print("[PASS] Cleaned campaign data saved:")
    print(f"       {CAMPAIGN_CLEAN_PATH}")

    print("[PASS] Cleaned customer data saved:")
    print(f"       {CUSTOMER_CLEAN_PATH}")

    print("[PASS] Cleaned order data saved:")
    print(f"       {ORDER_CLEAN_PATH}")

    print("\nFinal row counts:")
    print(
        f"  - Campaigns: "
        f"{len(campaign_df):,}"
    )
    print(
        f"  - Customers: "
        f"{len(customer_df):,}"
    )
    print(
        f"  - Orders: "
        f"{len(order_df):,}"
    )

    print(
        "\n[INFO] The original raw Excel "
        "workbook was not changed."
    )

    return (
        campaign_df,
        customer_df,
        order_df,
    )


if __name__ == "__main__":
    clean_data()
