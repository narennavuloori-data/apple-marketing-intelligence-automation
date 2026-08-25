import pandas as pd

from config.config import (
    CAMPAIGN_CLEAN_PATH,
    KPI_SUMMARY_PATH,
)


REQUIRED_COLUMNS = [
    "report_date",
    "channel",
    "ad_spend_usd",
    "creative_cost_usd",
    "agency_cost_usd",
    "marketing_tools_cost_usd",
    "impressions",
    "clicks",
    "conversions",
    "new_customers",
]


def safe_divide(numerator, denominator, multiplier=1):
    """Divide safely and return None when the denominator is zero."""
    if pd.isna(denominator) or denominator == 0:
        return None

    return (numerator / denominator) * multiplier


def calculate_group_kpis(df, scope, channel):
    """Calculate aggregated marketing KPIs for one group."""
    ad_spend = df["ad_spend_usd"].sum()
    creative_cost = df["creative_cost_usd"].sum()
    agency_cost = df["agency_cost_usd"].sum()
    tools_cost = df["marketing_tools_cost_usd"].sum()

    total_marketing_cost = (
        ad_spend
        + creative_cost
        + agency_cost
        + tools_cost
    )

    impressions = df["impressions"].sum()
    clicks = df["clicks"].sum()
    conversions = df["conversions"].sum()
    new_customers = df["new_customers"].sum()

    cac = safe_divide(total_marketing_cost, new_customers)
    ctr = safe_divide(clicks, impressions, multiplier=100)
    cpc = safe_divide(ad_spend, clicks)
    cpm = safe_divide(ad_spend, impressions, multiplier=1000)
    conversion_rate = safe_divide(conversions, clicks, multiplier=100)
    cpa = safe_divide(ad_spend, conversions)

    return {
        "scope": scope,
        "channel": channel,
        "total_marketing_cost_usd": round(total_marketing_cost, 2),
        "ad_spend_usd": round(ad_spend, 2),
        "new_customers": int(new_customers),
        "impressions": int(impressions),
        "clicks": int(clicks),
        "conversions": int(conversions),
        "cac_usd": round(cac, 2) if cac is not None else None,
        "ctr_pct": round(ctr, 2) if ctr is not None else None,
        "cpc_usd": round(cpc, 2) if cpc is not None else None,
        "cpm_usd": round(cpm, 2) if cpm is not None else None,
        "conversion_rate_pct": (
            round(conversion_rate, 2)
            if conversion_rate is not None
            else None
        ),
        "cpa_usd": round(cpa, 2) if cpa is not None else None,
    }


def calculate_kpis():
    print("\n" + "=" * 70)
    print("APPLE MARKETING KPI CALCULATION")
    print("=" * 70)

    if not CAMPAIGN_CLEAN_PATH.exists():
        raise FileNotFoundError(
            "Clean campaign file was not found. "
            "Run data_cleaner.py first.\n"
            f"Expected file: {CAMPAIGN_CLEAN_PATH}"
        )

    campaign_df = pd.read_csv(CAMPAIGN_CLEAN_PATH)

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in campaign_df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Required KPI columns are missing: "
            + ", ".join(missing_columns)
        )

    numeric_columns = [
        "ad_spend_usd",
        "creative_cost_usd",
        "agency_cost_usd",
        "marketing_tools_cost_usd",
        "impressions",
        "clicks",
        "conversions",
        "new_customers",
    ]

    for column in numeric_columns:
        campaign_df[column] = pd.to_numeric(
            campaign_df[column],
            errors="coerce",
        ).fillna(0)

    campaign_df["report_date"] = pd.to_datetime(
        campaign_df["report_date"],
        errors="coerce",
    )

    report_start_date = campaign_df["report_date"].min()
    report_end_date = campaign_df["report_date"].max()

    results = []

    results.append(
        calculate_group_kpis(
            campaign_df,
            scope="Overall",
            channel="All Channels",
        )
    )

    for channel, channel_df in campaign_df.groupby(
        "channel",
        dropna=False,
    ):
        channel_name = (
            str(channel)
            if pd.notna(channel)
            else "Unknown"
        )

        results.append(
            calculate_group_kpis(
                channel_df,
                scope="Channel",
                channel=channel_name,
            )
        )

    kpi_df = pd.DataFrame(results)

    kpi_df.insert(
        0,
        "report_start_date",
        (
            report_start_date.strftime("%Y-%m-%d")
            if pd.notna(report_start_date)
            else None
        ),
    )

    kpi_df.insert(
        1,
        "report_end_date",
        (
            report_end_date.strftime("%Y-%m-%d")
            if pd.notna(report_end_date)
            else None
        ),
    )

    overall_row = kpi_df[kpi_df["scope"] == "Overall"]

    channel_rows = (
        kpi_df[kpi_df["scope"] == "Channel"]
        .sort_values(
            by="total_marketing_cost_usd",
            ascending=False,
        )
    )

    kpi_df = pd.concat(
        [overall_row, channel_rows],
        ignore_index=True,
    )

    KPI_SUMMARY_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    kpi_df.to_csv(
        KPI_SUMMARY_PATH,
        index=False,
    )

    print(f"Clean campaign rows used: {len(campaign_df):,}")

    print(
        f"Report period: "
        f"{kpi_df.loc[0, 'report_start_date']} "
        f"to "
        f"{kpi_df.loc[0, 'report_end_date']}"
    )

    print("\nOVERALL KPIs")
    print("-" * 70)

    overall = kpi_df.iloc[0]

    print(
        f"Total Marketing Cost: "
        f"${overall['total_marketing_cost_usd']:,.2f}"
    )

    print(
        f"New Customers: "
        f"{overall['new_customers']:,.0f}"
    )

    print(
        f"CAC: "
        f"${overall['cac_usd']:,.2f}"
    )

    print(
        f"CTR: "
        f"{overall['ctr_pct']:.2f}%"
    )

    print(
        f"CPC: "
        f"${overall['cpc_usd']:,.2f}"
    )

    print(
        f"CPM: "
        f"${overall['cpm_usd']:,.2f}"
    )

    print(
        f"Conversion Rate: "
        f"{overall['conversion_rate_pct']:.2f}%"
    )

    print(
        f"CPA: "
        f"${overall['cpa_usd']:,.2f}"
    )

    print("\n[PASS] KPI summary saved:")
    print(f"       {KPI_SUMMARY_PATH}")

    return kpi_df


if __name__ == "__main__":
    calculate_kpis()



