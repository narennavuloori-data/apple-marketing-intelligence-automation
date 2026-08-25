
import pandas as pd

from config.config import (
    RAW_FILE_PATH,
    CAMPAIGN_SHEET,
    CUSTOMER_SHEET,
    ORDER_SHEET,
)


# Expected columns for each raw sheet
EXPECTED_COLUMNS = {
    CAMPAIGN_SHEET: [
        "record_id",
        "report_date",
        "campaign_id",
        "campaign_name",
        "campaign_objective",
        "campaign_status",
        "channel",
        "platform",
        "ad_format",
        "product_family",
        "product_name",
        "region",
        "country",
        "city",
        "device_type",
        "audience_segment",
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
        "currency_code",
        "source_system",
        "source_file_name",
        "batch_id",
        "ingestion_timestamp",
    ],
    CUSTOMER_SHEET: [
        "customer_id",
        "acquisition_date",
        "acquisition_campaign_id",
        "acquisition_channel",
        "acquisition_platform",
        "region",
        "country",
        "city",
        "age_group",
        "gender",
        "customer_segment",
        "primary_product_interest",
        "first_purchase_date",
        "last_purchase_date",
        "customer_status",
        "churn_date",
        "marketing_consent",
        "loyalty_member",
        "source_system",
        "source_file_name",
        "batch_id",
        "ingestion_timestamp",
    ],
    ORDER_SHEET: [
        "order_id",
        "order_date",
        "order_timestamp",
        "customer_id",
        "attributed_campaign_id",
        "attribution_model",
        "sales_channel",
        "product_family",
        "product_name",
        "region",
        "country",
        "device_type",
        "units",
        "unit_price_usd",
        "gross_order_value_usd",
        "discount_amount_usd",
        "refund_amount_usd",
        "net_revenue_usd",
        "cogs_usd",
        "gross_profit_usd",
        "payment_status",
        "order_status",
        "is_first_order",
        "is_repeat_order",
        "source_system",
        "source_file_name",
        "batch_id",
        "ingestion_timestamp",
    ],
}


PRIMARY_KEYS = {
    CAMPAIGN_SHEET: "record_id",
    CUSTOMER_SHEET: "customer_id",
    ORDER_SHEET: "order_id",
}


CRITICAL_COLUMNS = {
    CAMPAIGN_SHEET: [
        "record_id",
        "report_date",
        "campaign_id",
        "channel",
        "product_name",
        "ad_spend_usd",
        "impressions",
        "clicks",
        "conversions",
        "new_customers",
        "attributed_revenue_usd",
    ],
    CUSTOMER_SHEET: [
        "customer_id",
        "acquisition_date",
        "acquisition_channel",
        "customer_segment",
        "customer_status",
    ],
    ORDER_SHEET: [
        "order_id",
        "order_date",
        "customer_id",
        "product_name",
        "net_revenue_usd",
        "cogs_usd",
        "gross_profit_usd",
    ],
}


def print_section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def count_missing(series):
    missing = series.isna()

    if series.dtype == "object" or isinstance(series.dtype, pd.StringDtype):
        blank = series.astype("string").str.strip().eq("").fillna(False)
        missing = missing | blank

    return int(missing.sum())


def to_number(series):
    text = series.astype("string")
    text = text.str.replace("$", "", regex=False)
    text = text.str.replace(",", "", regex=False)
    text = text.str.strip()

    return pd.to_numeric(text, errors="coerce")


def validate_data():
    critical_errors = []
    warnings = []

    print_section("APPLE MARKETING DATA VALIDATION")
    print(f"File: {RAW_FILE_PATH}")

    # 1. File validation
    print_section("1. FILE VALIDATION")

    if not RAW_FILE_PATH.exists():
        critical_errors.append("Raw Excel file does not exist.")
        print("[FAIL] Raw Excel file does not exist.")
        print(f"Expected location: {RAW_FILE_PATH}")
        return False

    print("[PASS] Raw Excel file exists.")

    if RAW_FILE_PATH.stat().st_size == 0:
        critical_errors.append("Raw Excel file is empty.")
        print("[FAIL] Raw Excel file is empty.")
        return False

    print("[PASS] Raw Excel file is not empty.")

    try:
        excel_file = pd.ExcelFile(RAW_FILE_PATH, engine="openpyxl")
        print("[PASS] Python can open the Excel file.")
    except Exception as error:
        critical_errors.append("Python could not open the Excel file.")
        print("[FAIL] Python could not open the Excel file.")
        print(f"Error: {error}")
        return False

    # 2. Sheet validation
    print_section("2. SHEET VALIDATION")

    required_sheets = [
        CAMPAIGN_SHEET,
        CUSTOMER_SHEET,
        ORDER_SHEET,
    ]

    missing_sheets = [
        sheet for sheet in required_sheets
        if sheet not in excel_file.sheet_names
    ]

    if missing_sheets:
        critical_errors.append(
            f"Missing required sheets: {', '.join(missing_sheets)}"
        )
        print(f"[FAIL] Missing required sheets: {', '.join(missing_sheets)}")
        return False

    print("[PASS] All required sheets exist.")
    print("Required sheets found:")
    for sheet in required_sheets:
        print(f"  - {sheet}")

    # Read the three business-data sheets
    try:
        dataframes = pd.read_excel(
            RAW_FILE_PATH,
            sheet_name=required_sheets,
            engine="openpyxl",
        )

        campaign_df = dataframes[CAMPAIGN_SHEET]
        customer_df = dataframes[CUSTOMER_SHEET]
        order_df = dataframes[ORDER_SHEET]
    except Exception as error:
        critical_errors.append("One or more required sheets could not be read.")
        print("[FAIL] One or more required sheets could not be read.")
        print(f"Error: {error}")
        return False

    print("\nRows loaded:")
    for sheet_name, df in dataframes.items():
        print(f"  - {sheet_name}: {len(df):,} rows")

        if df.empty:
            critical_errors.append(f"{sheet_name} contains no data rows.")
            print(f"[FAIL] {sheet_name} is empty.")

    if critical_errors:
        return False

    # 3. Column validation
    print_section("3. COLUMN VALIDATION")

    for sheet_name, expected_columns in EXPECTED_COLUMNS.items():
        df = dataframes[sheet_name]

        missing_columns = [
            column for column in expected_columns
            if column not in df.columns
        ]

        if missing_columns:
            critical_errors.append(
                f"{sheet_name} is missing columns: "
                f"{', '.join(missing_columns)}"
            )
            print(f"[FAIL] {sheet_name}")
            print(f"Missing columns: {', '.join(missing_columns)}")
        else:
            print(f"[PASS] {sheet_name}: all expected columns exist.")

    if critical_errors:
        print("\nValidation cannot continue because required columns are missing.")
        return False

    # 4. Primary key validation
    print_section("4. PRIMARY KEY VALIDATION")

    for sheet_name, primary_key in PRIMARY_KEYS.items():
        df = dataframes[sheet_name]

        missing_key_count = count_missing(df[primary_key])
        duplicate_key_count = int(df[primary_key].duplicated().sum())

        if missing_key_count == 0:
            print(f"[PASS] {sheet_name}.{primary_key}: no missing values.")
        else:
            warnings.append(
                (f"{sheet_name}.{primary_key} missing", missing_key_count)
            )
            print(
                f"[WARNING] {sheet_name}.{primary_key}: "
                f"{missing_key_count:,} missing values."
            )

        if duplicate_key_count == 0:
            print(f"[PASS] {sheet_name}.{primary_key}: no duplicate keys.")
        else:
            warnings.append(
                (f"{sheet_name}.{primary_key} duplicates", duplicate_key_count)
            )
            print(
                f"[WARNING] {sheet_name}.{primary_key}: "
                f"{duplicate_key_count:,} duplicate key rows."
            )

    # 5. Missing-value validation
    print_section("5. MISSING VALUE VALIDATION")

    for sheet_name, df in dataframes.items():
        print(f"\n{sheet_name}:")

        missing_found = False

        for column in df.columns:
            missing_count = count_missing(df[column])

            if missing_count > 0:
                missing_found = True
                warnings.append(
                    (f"{sheet_name}.{column} missing", missing_count)
                )

                label = (
                    "CRITICAL COLUMN"
                    if column in CRITICAL_COLUMNS[sheet_name]
                    else "optional/non-key column"
                )

                print(
                    f"  [WARNING] {column}: "
                    f"{missing_count:,} missing ({label})"
                )

        if not missing_found:
            print("  [PASS] No missing values found.")

    # 6. Business-rule validation
    print_section("6. BUSINESS RULE VALIDATION")

    impressions = to_number(campaign_df["impressions"])
    reach = to_number(campaign_df["reach"])
    clicks = to_number(campaign_df["clicks"])
    landing_sessions = to_number(campaign_df["landing_page_sessions"])
    add_to_cart = to_number(campaign_df["add_to_cart"])
    conversions = to_number(campaign_df["conversions"])
    new_customers = to_number(campaign_df["new_customers"])
    ad_spend = to_number(campaign_df["ad_spend_usd"])
    email_sent = to_number(campaign_df["email_sent"])
    email_delivered = to_number(campaign_df["email_delivered"])
    email_opens = to_number(campaign_df["email_opens"])
    email_clicks = to_number(campaign_df["email_clicks"])

    campaign_rules = {
        "reach > impressions": reach > impressions,
        "clicks > impressions": clicks > impressions,
        "landing_page_sessions > clicks": landing_sessions > clicks,
        "add_to_cart > landing_page_sessions": add_to_cart > landing_sessions,
        "conversions > clicks": conversions > clicks,
        "conversions > add_to_cart": conversions > add_to_cart,
        "new_customers > conversions": new_customers > conversions,
        "email_delivered > email_sent": email_delivered > email_sent,
        "email_opens > email_delivered": email_opens > email_delivered,
        "email_clicks > email_opens": email_clicks > email_opens,
        "ad_spend_usd < 0": ad_spend < 0,
    }

    for rule_name, invalid_rows in campaign_rules.items():
        invalid_count = int(invalid_rows.fillna(False).sum())

        if invalid_count == 0:
            print(f"[PASS] {rule_name}: 0 invalid rows.")
        else:
            warnings.append((rule_name, invalid_count))
            print(
                f"[WARNING] {rule_name}: "
                f"{invalid_count:,} invalid rows."
            )

    net_revenue = to_number(order_df["net_revenue_usd"])
    cogs = to_number(order_df["cogs_usd"])
    gross_profit = to_number(order_df["gross_profit_usd"])
    gross_order_value = to_number(order_df["gross_order_value_usd"])
    discount_amount = to_number(order_df["discount_amount_usd"])
    refund_amount = to_number(order_df["refund_amount_usd"])

    order_rules = {
        "net_revenue_usd < 0": net_revenue < 0,
        "cogs_usd < 0": cogs < 0,
        "gross_order_value_usd < 0": gross_order_value < 0,
        "discount_amount_usd < 0": discount_amount < 0,
        "refund_amount_usd < 0": refund_amount < 0,
    }

    for rule_name, invalid_rows in order_rules.items():
        invalid_count = int(invalid_rows.fillna(False).sum())

        if invalid_count == 0:
            print(f"[PASS] {rule_name}: 0 invalid rows.")
        else:
            warnings.append((rule_name, invalid_count))
            print(
                f"[WARNING] {rule_name}: "
                f"{invalid_count:,} invalid rows."
            )

    expected_net_revenue = (
        gross_order_value - discount_amount - refund_amount
    )
    net_revenue_difference = (net_revenue - expected_net_revenue).abs()
    net_revenue_mismatch = net_revenue_difference > 0.01
    net_revenue_mismatch_count = int(
        net_revenue_mismatch.fillna(False).sum()
    )

    if net_revenue_mismatch_count == 0:
        print("[PASS] Net revenue formula is consistent.")
    else:
        warnings.append(
            ("Net revenue formula mismatch", net_revenue_mismatch_count)
        )
        print(
            "[WARNING] Net revenue formula mismatch: "
            f"{net_revenue_mismatch_count:,} rows."
        )

    expected_gross_profit = net_revenue - cogs
    gross_profit_difference = (
        gross_profit - expected_gross_profit
    ).abs()
    gross_profit_mismatch = gross_profit_difference > 0.01
    gross_profit_mismatch_count = int(
        gross_profit_mismatch.fillna(False).sum()
    )

    if gross_profit_mismatch_count == 0:
        print("[PASS] Gross profit formula is consistent.")
    else:
        warnings.append(
            ("Gross profit formula mismatch", gross_profit_mismatch_count)
        )
        print(
            "[WARNING] Gross profit formula mismatch: "
            f"{gross_profit_mismatch_count:,} rows."
        )

    # 7. Foreign-key validation
    print_section("7. FOREIGN KEY VALIDATION")

    customer_ids = set(
        customer_df["customer_id"]
        .dropna()
        .astype("string")
    )

    order_customer_ids = (
        order_df["customer_id"]
        .dropna()
        .astype("string")
    )

    orphan_customer_mask = ~order_customer_ids.isin(customer_ids)
    orphan_customer_count = int(orphan_customer_mask.sum())

    if orphan_customer_count == 0:
        print(
            "[PASS] Orders.customer_id -> Customers.customer_id: "
            "no orphan rows."
        )
    else:
        warnings.append(
            ("Orphan order customer IDs", orphan_customer_count)
        )
        print(
            "[WARNING] Orders.customer_id -> Customers.customer_id: "
            f"{orphan_customer_count:,} orphan rows."
        )

    campaign_ids = set(
        campaign_df["campaign_id"]
        .dropna()
        .astype("string")
    )

    attributed_campaign_ids = (
        order_df["attributed_campaign_id"]
        .dropna()
        .astype("string")
    )

    orphan_campaign_mask = ~attributed_campaign_ids.isin(campaign_ids)
    orphan_campaign_count = int(orphan_campaign_mask.sum())

    if orphan_campaign_count == 0:
        print(
            "[PASS] Orders.attributed_campaign_id -> "
            "Campaign campaign_id: no orphan rows."
        )
    else:
        warnings.append(
            ("Orphan attributed campaign IDs", orphan_campaign_count)
        )
        print(
            "[WARNING] Orders.attributed_campaign_id -> "
            "Campaign campaign_id: "
            f"{orphan_campaign_count:,} orphan rows."
        )

    # Final result
    print_section("VALIDATION SUMMARY")

    if critical_errors:
        print("[FAILED] Critical validation errors were found.")
        for error in critical_errors:
            print(f"  - {error}")
        return False

    print("[PASS] File structure is valid and ready for the cleaning phase.")

    if warnings:
        print(
            f"[INFO] {len(warnings)} data-quality warning types were found."
        )
        print(
            "[INFO] These warnings are expected in the intentionally messy "
            "raw dataset and should be handled in data_cleaner.py."
        )
    else:
        print("[INFO] No data-quality warnings were found.")

    print("[INFO] No data was changed or saved by this validator.")

    return True


if __name__ == "__main__":
    validate_data()
