# Apple Marketing Intelligence Automation — Data Dictionary

This document explains the most important columns used in the Apple Marketing Intelligence Automation project.

---

## 1. `campaign_performance_clean.csv`

| Column | Data Type | Description | Example | Business Meaning |
|---|---|---|---|---|
| `report_date` | Date | Reporting date for the campaign performance record. | `2026-06-30` | Helps track daily marketing performance trends over time. |
| `record_id` | String | Unique row identifier for each campaign performance record. | `CPR_00024519` | Used as the primary key for campaign-level daily records. |
| `campaign_id` | String | Unique identifier for the campaign. | `CAMP_IPH_2026_014` | Helps track performance by campaign across time. |
| `campaign_name` | String | Human-readable campaign name. | `iPhone Product Launch 2026 Wave 14` | Useful for business reporting and identifying top/bottom campaigns. |
| `channel` | String | Marketing channel used for the campaign. | `Instagram` | Helps compare channel effectiveness across paid and owned media. |
| `platform` | String | Specific marketing platform or ad platform. | `Meta Ads` | Helps analyze platform-level execution within a broader channel. |
| `product_name` | String | Apple product promoted in the campaign. | `iPhone 16 Pro` | Shows which products receive spend and generate response. |
| `product_family` | String | Higher-level product grouping. | `iPhone` | Useful for product-family performance analysis. |
| `country` | String | Country targeted by the campaign. | `United States` | Supports geographic performance analysis. |
| `city` | String | City targeted or attributed to the campaign. | `New York` | Useful for city-level campaign analysis when available. |
| `audience_segment` | String | Target audience segment for the campaign. | `Young Professionals` | Helps understand which audience groups respond best. |
| `reach` | Integer | Number of unique people reached. | `185000` | Indicates audience breadth of a campaign. |
| `impressions` | Integer | Total number of ad impressions delivered. | `240000` | Used to measure campaign visibility and for CTR/CPM calculations. |
| `clicks` | Integer | Number of ad clicks. | `4230` | Used in CTR, CPC, conversion rate, and funnel analysis. |
| `landing_page_sessions` | Integer | Number of sessions generated on the landing page. | `3610` | Measures how much traffic actually reached the website/app after the click. |
| `add_to_cart` | Integer | Number of add-to-cart actions attributed to the campaign. | `690` | Indicates purchase intent in the marketing funnel. |
| `conversions` | Integer | Number of successful conversions. | `315` | Core KPI for campaign effectiveness. |
| `new_customers` | Integer | Number of new customers acquired from the campaign. | `104` | Used in acquisition analysis and CAC. |
| `leads` | Integer | Number of leads generated. | `180` | Useful for upper-funnel and lead-generation campaigns. |
| `video_views` | Integer | Number of video views. | `12850` | Useful for awareness and video engagement analysis. |
| `engagements` | Integer | Total engagements such as likes, comments, shares, etc. | `2250` | Helps measure interaction quality, especially on social channels. |
| `email_sent` | Integer | Number of marketing emails sent. | `50000` | Used for email campaign delivery analysis. |
| `email_delivered` | Integer | Number of emails successfully delivered. | `48500` | Used to evaluate email delivery quality. |
| `email_opens` | Integer | Number of opened emails. | `12140` | Used for open-rate style engagement tracking. |
| `email_clicks` | Integer | Number of clicks from email campaigns. | `1640` | Used in email performance and downstream CTR analysis. |
| `ad_spend_usd` | Decimal | Media spend for the record in USD. | `12450.75` | Primary advertising cost used in ROAS, CPC, CPM, CPA, and CAC calculations. |
| `creative_cost_usd` | Decimal | Creative production cost in USD. | `850.00` | Part of total marketing cost used in CAC and Marketing ROI. |
| `agency_cost_usd` | Decimal | Agency servicing cost in USD. | `500.00` | Included in total marketing cost. |
| `marketing_tools_cost_usd` | Decimal | Cost of marketing tools/platforms in USD. | `120.00` | Included in total marketing cost for broader acquisition efficiency measurement. |
| `attributed_revenue_usd` | Decimal | Revenue attributed to the campaign. | `48210.40` | Used in ROAS and attributed campaign performance analysis. |

---

## 2. `customers_clean.csv`

| Column | Data Type | Description | Example | Business Meaning |
|---|---|---|---|---|
| `customer_id` | String | Unique customer identifier. | `CUS_00012875` | Primary key for customer-level records and customer analytics. |
| `acquisition_date` | Date | Date when the customer was first acquired. | `2026-01-14` | Helps analyze customer acquisition trends over time. |
| `acquisition_channel` | String | Channel through which the customer was acquired. | `Google Search` | Used to compare customer acquisition effectiveness by channel. |
| `acquisition_platform` | String | Specific platform associated with acquisition. | `Google Ads` | Helps drill into acquisition source in more detail. |
| `customer_segment` | String | Assigned customer segment. | `Premium` | Used for segmentation and value analysis. |
| `customer_status` | String | Current customer lifecycle status. | `Active` | Helps distinguish active, inactive, retained, or churned customers. |
| `country` | String | Customer country. | `United States` | Useful for geographic customer analysis. |
| `city` | String | Customer city. | `San Francisco` | Useful for city-level segmentation and acquisition patterns. |
| `gender` | String | Customer gender when available. | `Male` | Supports customer profile analysis. |
| `age_group` | String | Customer age band or age category. | `25-34` | Helps understand which age groups convert or retain better. |
| `primary_product_interest` | String | Main Apple product category of interest. | `Mac` | Useful for product targeting and personalization analysis. |
| `loyalty_member` | Boolean | Whether the customer is enrolled in a loyalty program. | `True` | Useful for retention and repeat purchase analysis. |
| `churn_date` | Date | Date when the customer churned, if applicable. | `2026-05-12` | Used for churn analysis and retention reporting. |

---

## 3. `orders_clean.csv`

| Column | Data Type | Description | Example | Business Meaning |
|---|---|---|---|---|
| `order_id` | String | Unique order identifier. | `ORD_00098754` | Primary key for transaction-level records. |
| `order_date` | Date | Date when the order was placed. | `2026-06-30` | Used for revenue trend analysis and time-based reporting. |
| `customer_id` | String | Customer who placed the order. | `CUS_00012875` | Links transactions to customer records. |
| `attributed_campaign_id` | String | Campaign associated with the order, if attributed. | `CAMP_IPH_2026_014` | Links revenue back to marketing activity for attribution analysis. |
| `product_name` | String | Product sold in the order. | `iPhone 16 Pro` | Used to analyze product-level sales performance. |
| `product_family` | String | High-level product grouping. | `iPhone` | Used for product-family reporting. |
| `sales_channel` | String | Channel through which the sale occurred. | `Online Store` | Helps compare online/offline or direct/indirect sales mix. |
| `device_type` | String | Device used during the purchase when available. | `Mobile` | Helps analyze purchase behavior by device. |
| `gross_order_value_usd` | Decimal | Total order value before discounts and refunds. | `1499.00` | Useful for gross sales reporting and AOV analysis. |
| `discount_amount_usd` | Decimal | Discount applied to the order. | `100.00` | Helps analyze discounting impact on revenue and profitability. |
| `refund_amount_usd` | Decimal | Refunded amount on the order. | `0.00` | Helps measure post-sale revenue leakage. |
| `net_revenue_usd` | Decimal | Final revenue after discounts and refunds. | `1399.00` | Core revenue KPI used in financial reporting. |
| `cogs_usd` | Decimal | Cost of goods sold for the order. | `940.00` | Used to calculate gross profit and gross margin. |
| `gross_profit_usd` | Decimal | Profit before operating expenses. | `459.00` | Used in profitability analysis and Marketing ROI. |
| `order_status` | String | Current order status. | `Completed` | Helps separate completed orders from cancelled or returned ones. |
| `source_file_name` | String | Original source file reference. | `Apple_Marketing_Raw_Data.xlsx` | Useful for audit trail and data lineage. |

---

## 4. Relationship Summary

### Primary Keys
- `campaign_performance_clean.record_id`
- `customers_clean.customer_id`
- `orders_clean.order_id`

### Foreign Keys
- `orders_clean.customer_id` → `customers_clean.customer_id`
- `orders_clean.attributed_campaign_id` → `campaign_performance_clean.campaign_id`

### Reporting Usage
- **Campaign table** drives marketing performance analysis.
- **Customers table** supports acquisition, retention, and churn analysis.
- **Orders table** drives revenue, margin, profitability, and product sales analysis.
