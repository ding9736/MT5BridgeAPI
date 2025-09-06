# run_all_tests.py
import json
import logging
import time
import os
import pandas as pd
from rich.console import Console
from rich.table import Table
from mt5_bridge_client import APIClient
import test_suite_1_basic_ops
import test_suite_2_trading_logic
import test_suite_3_stress_concurrency
import test_suite_4_bulk_operations
import test_suite_5_serial_benchmark  # [New] Import the new serial benchmark test suite
import os

CONFIG_FILE = os.path.join("config", "test_config.json")


def load_config():
    """Load test configuration from a JSON file"""
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Could not load or parse config file '{CONFIG_FILE}': {e}")
        return None


def setup_directories(config):
    """Ensure all directories defined in the configuration exist"""
    for directory in config["core_paths"].values():
        if not os.path.exists(directory):
            logging.info(f"Directory '{directory}' does not exist, creating it...")
            os.makedirs(directory)


def generate_report(results: list, config: dict):
    """Generate and print the test report using pandas and rich"""
    if not results:
        logging.warning("No test results were collected, cannot generate a report.")
        return

    console = Console()
    df = pd.DataFrame(results)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_filename_base = (
        f"{config['report_settings']['report_base_name']}_{timestamp}"
    )
    reports_dir = config["core_paths"]["reports_dir"]

    report_path_csv = os.path.join(reports_dir, f"{report_filename_base}.csv")
    report_path_html = os.path.join(reports_dir, f"{report_filename_base}.html")

    df.to_csv(report_path_csv, index=False, encoding="utf-8-sig")
    df.to_html(report_path_html, index=False)
    logging.info(f"Test reports have been saved to the '{reports_dir}' folder.")

    table = Table(
        title="\n\nMT5 Bridge API Test Report",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Suite", style="cyan")
    table.add_column("Case", style="yellow")
    table.add_column("Status", style="white")
    table.add_column("End-to-End Duration (ms)", style="blue")
    table.add_column("Details", style="white", no_wrap=False)

    display_columns = ["Suite", "Case", "Status", "End-to-End Duration (ms)", "Details"]
    df_display = df.reindex(columns=display_columns, fill_value="N/A")

    for _, row in df_display.iterrows():
        style = "green" if row["Status"] == "PASS" else "red"
        table.add_row(*[str(item) for item in row], style=style)

    console.print(table)

    total, passed = len(df), len(df[df["Status"] == "PASS"])
    failed = total - passed
    summary_table = Table(title="Test Summary", show_header=False)
    summary_table.add_column()
    summary_table.add_column(style="bold")
    summary_table.add_row("Total Cases", str(total))
    summary_table.add_row("[green]Passed[/green]", str(passed))
    summary_table.add_row("[red]Failed[/red]", str(failed))
    console.print(summary_table)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    config = load_config()
    if not config:
        exit(1)

    # [Optimization] Extract more parameters from config to drive tests
    trading_settings = config["trading_settings"]
    stress_settings = config["stress_test_settings"]
    symbols_to_test = trading_settings["symbols_to_test"]
    iterations = stress_settings["iterations"]
    interval_ms = stress_settings.get(
        "request_interval_ms", 100
    )  # [New] Get throttle interval, default 100ms

    logging.info("=" * 80)
    logging.info(" Initializing test environment...")
    setup_directories(config)
    logging.info(f" This test will be run on the following symbols: {symbols_to_test}")
    logging.info(
        f" Performance test iterations: {iterations}, Request interval: {interval_ms} ms"
    )
    logging.info("=" * 80)

    all_results = []
    client = None
    try:
        client = APIClient(history_cache_dir=config["core_paths"]["history_cache_dir"])
        client.connect()

        # [Optimization] Test suite registry for clarity, passing required configs
        test_suites = {
            "Basic Operations": (test_suite_1_basic_ops.run, [client, config]),
            "Trading Logic": (
                test_suite_2_trading_logic.run,
                [client, symbols_to_test],
            ),
            "Bulk Management Operations": (
                test_suite_4_bulk_operations.run,
                [client, symbols_to_test],
            ),
            "Serial Benchmark Test": (  # [New]
                test_suite_5_serial_benchmark.run,
                [client, symbols_to_test, iterations, interval_ms],
            ),
            "Concurrent Performance Test (Throttled)": (  # [Optimization]
                test_suite_3_stress_concurrency.run,
                [client, symbols_to_test, iterations, interval_ms],
            ),
        }

        for name, (suite_func, args) in test_suites.items():
            logging.info(f"\n\n{'=' * 80}\nStarting test suite: {name}")
            results = suite_func(*args)
            if results:
                all_results.extend(results)

    except Exception as e:
        logging.error(
            f"An unexpected error occurred during test execution: {e}", exc_info=True
        )
    finally:
        if client:
            client.close()
        generate_report(all_results, config)
