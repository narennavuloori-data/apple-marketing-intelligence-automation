import logging
import shutil
import sys
from datetime import datetime

from dotenv import load_dotenv

from config.config import (
    ARCHIVE_FOLDER,
    LOG_FILE,
    RAW_FILE_PATH,
)
from src.data_cleaner import clean_data
from src.data_validator import validate_data
from src.email_downloader import download_email_attachment
from src.email_sender import send_email
from src.kpi_calculator import calculate_kpis
from src.report_generator import generate_report


def setup_logger():
    """Create the main pipeline file logger."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("apple_marketing_main_pipeline")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        file_handler = logging.FileHandler(
            LOG_FILE,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


LOGGER = setup_logger()


def print_pipeline_step(step_number, title):
    """Print a clear pipeline step heading."""
    print("\n" + "=" * 70)
    print(f"STEP {step_number} - {title}")
    print("=" * 70)


def archive_raw_file():
    """
    Move the successfully processed raw workbook from incoming
    to archive using a timestamped filename.
    """
    if not RAW_FILE_PATH.exists():
        raise FileNotFoundError(
            "Raw file could not be archived because it "
            f"does not exist: {RAW_FILE_PATH}"
        )

    ARCHIVE_FOLDER.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    archive_name = (
        f"{RAW_FILE_PATH.stem}_{timestamp}"
        f"{RAW_FILE_PATH.suffix}"
    )

    archive_path = ARCHIVE_FOLDER / archive_name

    shutil.move(
        str(RAW_FILE_PATH),
        str(archive_path),
    )

    print("[PASS] Raw input file archived successfully.")
    print(f"Archived to: {archive_path}")

    LOGGER.info(
        "Raw input file archived to '%s'.",
        archive_path,
    )

    return archive_path


def run_pipeline():
    """
    Run the complete Apple marketing reporting pipeline in order.

    Order:
        1. Download email attachment
        2. Validate raw workbook
        3. Clean data
        4. Calculate KPIs
        5. Generate report and refresh Power BI
        6. Send report email
        7. Archive raw workbook
    """
    load_dotenv(override=True)

    pipeline_start = datetime.now()

    print("\n" + "=" * 70)
    print("APPLE MARKETING INTELLIGENCE AUTOMATION")
    print("END-TO-END PIPELINE")
    print("=" * 70)

    print(
        "Pipeline started: "
        + pipeline_start.strftime("%d-%b-%Y %H:%M:%S")
    )

    LOGGER.info("Apple marketing pipeline started.")

    try:
        # STEP 1 - DOWNLOAD
        print_pipeline_step(
            1,
            "DOWNLOAD MANAGER EMAIL ATTACHMENT",
        )

        downloaded_file = download_email_attachment()

        if downloaded_file is None:
            if RAW_FILE_PATH.exists():
                print(
                    "\n[INFO] No new unread manager email was found."
                )
                print(
                    "[INFO] A pending raw workbook already exists "
                    "in data/incoming/."
                )
                print(
                    "[INFO] Resuming the pipeline with that file."
                )

                downloaded_file = RAW_FILE_PATH

                LOGGER.warning(
                    "No new email was found, but a pending raw "
                    "workbook exists. Resuming with '%s'.",
                    RAW_FILE_PATH,
                )

            else:
                print(
                    "\n[INFO] No new unread manager email was found."
                )
                print(
                    "[INFO] No pending raw workbook exists."
                )
                print(
                    "[INFO] There is no new data to process."
                )
                print(
                    "[PASS] Pipeline finished normally."
                )

                LOGGER.info(
                    "Pipeline finished normally because no new "
                    "matching email or pending raw workbook exists."
                )

                return True

        LOGGER.info(
            "Raw input workbook ready for processing: %s",
            downloaded_file,
        )

        # STEP 2 - VALIDATE
        print_pipeline_step(
            2,
            "VALIDATE RAW DATA",
        )

        validation_passed = validate_data()

        if not validation_passed:
            raise RuntimeError(
                "Raw data validation failed. "
                "The pipeline stopped before cleaning."
            )

        LOGGER.info(
            "Raw data validation completed successfully."
        )

        # STEP 3 - CLEAN
        print_pipeline_step(
            3,
            "CLEAN RAW DATA",
        )

        clean_data()

        LOGGER.info(
            "Data cleaning completed successfully."
        )

        # STEP 4 - KPI
        print_pipeline_step(
            4,
            "CALCULATE MARKETING KPIs",
        )

        calculate_kpis()

        LOGGER.info(
            "KPI calculation completed successfully."
        )

        # STEP 5 - REPORT + POWER BI
        print_pipeline_step(
            5,
            "GENERATE REPORT AND REFRESH POWER BI",
        )

        summary = generate_report()

        LOGGER.info(
            "Report generated and Power BI refresh "
            "completed successfully."
        )

        # STEP 6 - EMAIL
        print_pipeline_step(
            6,
            "SEND DAILY REPORT EMAIL",
        )

        email_sent = send_email(summary)

        if not email_sent:
            raise RuntimeError(
                "The report email was not sent successfully."
            )

        LOGGER.info(
            "Daily report email sent successfully."
        )

        # STEP 7 - ARCHIVE
        print_pipeline_step(
            7,
            "ARCHIVE RAW INPUT FILE",
        )

        archive_path = archive_raw_file()

        pipeline_end = datetime.now()
        duration = (
            pipeline_end - pipeline_start
        ).total_seconds()

        print("\n" + "=" * 70)
        print("PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 70)

        print("[PASS] Email attachment downloaded")
        print("[PASS] Raw data validated")
        print("[PASS] Data cleaned")
        print("[PASS] KPIs calculated")
        print("[PASS] Report summary generated")
        print("[PASS] Power BI refreshed")
        print("[PASS] Report email sent")
        print("[PASS] Raw file archived")

        print("\nArchived file:")
        print(archive_path)

        print(
            "\nPipeline finished: "
            + pipeline_end.strftime(
                "%d-%b-%Y %H:%M:%S"
            )
        )

        print(
            f"Total duration: {duration:.1f} seconds"
        )

        LOGGER.info(
            "Apple marketing pipeline completed "
            "successfully in %.1f seconds.",
            duration,
        )

        return True

    except Exception as error:
        pipeline_end = datetime.now()
        duration = (
            pipeline_end - pipeline_start
        ).total_seconds()

        print("\n" + "=" * 70)
        print("PIPELINE FAILED")
        print("=" * 70)

        print(
            f"[FAIL] {type(error).__name__}: {error}"
        )

        print(
            "\n[INFO] The pipeline stopped immediately."
        )

        print(
            "[INFO] The raw incoming workbook was NOT "
            "archived because the complete pipeline "
            "did not succeed."
        )

        print(
            f"[INFO] Check log file: {LOG_FILE}"
        )

        LOGGER.exception(
            "Apple marketing pipeline failed after "
            "%.1f seconds: %s",
            duration,
            error,
        )

        return False


if __name__ == "__main__":
    success = run_pipeline()

    if not success:
        sys.exit(1)
