from pathlib import Path

# Project root folder
BASE_DIR = Path(__file__).resolve().parent.parent

# Data folders
INCOMING_FOLDER = BASE_DIR / "data" / "incoming"
PROCESSED_FOLDER = BASE_DIR / "data" / "processed"
ARCHIVE_FOLDER = BASE_DIR / "data" / "archive"

# Log file
LOG_FILE = BASE_DIR / "logs" / "pipeline.log"

# Raw input file
RAW_FILE_NAME = "Apple_Marketing_Raw_Data.xlsx"
RAW_FILE_PATH = INCOMING_FOLDER / RAW_FILE_NAME

# Excel sheet names
CAMPAIGN_SHEET = "Campaign_Performance_Raw"
CUSTOMER_SHEET = "Customers_Raw"
ORDER_SHEET = "Orders_Raw"

# Processed output file names
CAMPAIGN_CLEAN_FILE = "campaign_performance_clean.csv"
CUSTOMER_CLEAN_FILE = "customers_clean.csv"
ORDER_CLEAN_FILE = "orders_clean.csv"
KPI_SUMMARY_FILE = "marketing_kpi_summary.csv"

# Processed output paths
CAMPAIGN_CLEAN_PATH = PROCESSED_FOLDER / CAMPAIGN_CLEAN_FILE
CUSTOMER_CLEAN_PATH = PROCESSED_FOLDER / CUSTOMER_CLEAN_FILE
ORDER_CLEAN_PATH = PROCESSED_FOLDER / ORDER_CLEAN_FILE
KPI_SUMMARY_PATH = PROCESSED_FOLDER / KPI_SUMMARY_FILE
