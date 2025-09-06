# test_suite_5_serial_benchmark.py
import time
import logging
from mt5_bridge_client import APIClient


def get_duration(response: dict) -> str:
    """Safely extracts the end-to-end duration from the top-level fields of the response."""
    return response.get("end_to_end_duration_ms", "N/A")


def run(client: APIClient, symbols_to_test: list, iterations: int, interval_ms: int):
    """
    Executes the serial benchmark test suite.

    This suite performs an "open-close" loop for a specified number of iterations for each symbol sequentially
    in a single thread. It aims to establish a performance baseline without concurrency pressure,
    for comparative analysis with the results of concurrent tests.
    """
    if not symbols_to_test:
        logging.warning(
            "No trading symbols provided in the configuration, skipping serial benchmark test."
        )
        return []

    suite_name = "Serial Benchmark Test"
    results_list = []
    logging.info(
        f"--- {suite_name}: Each symbol will serially execute {iterations} rounds of open-close cycles, with an interval of {interval_ms} ms ---"
    )

    for symbol in symbols_to_test:
        for i in range(iterations):
            logging.info(f"[Serial {symbol}] Starting round {i+1}/{iterations}...")

            # Open position
            case_name, ticket = f"{symbol} Open Position Loop {i+1}", None
            response = client.buy(symbol=symbol, volume=0.01)
            if response.get("status") == "success" and response.get("data", {}).get(
                "ticket"
            ):
                ticket = response["data"]["ticket"]
                results_list.append(
                    {
                        "Suite": suite_name,
                        "Case": case_name,
                        "Status": "PASS",
                        "End-to-End Duration (ms)": get_duration(response),
                        "Details": f"Ticket: {ticket}",
                    }
                )
            else:
                results_list.append(
                    {
                        "Suite": suite_name,
                        "Case": case_name,
                        "Status": "FAIL",
                        "End-to-End Duration (ms)": get_duration(response),
                        "Details": f"Failed to open position: {response.get('message', 'N/A')}",
                    }
                )
                time.sleep(interval_ms / 1000.0)
                continue  # Skip the rest of this iteration if opening position failed

            # Close position
            if ticket:
                time.sleep(0.2)  # A short delay between opening and closing
                case_name = f"{symbol} Close Position Loop {i+1}"
                close_response = client.close_position_by_ticket(ticket=ticket)
                status = "PASS" if close_response.get("status") == "success" else "FAIL"
                detail = (
                    "Position closed successfully"
                    if status == "PASS"
                    else f"Failed to close position: {close_response.get('message')}"
                )
                results_list.append(
                    {
                        "Suite": suite_name,
                        "Case": case_name,
                        "Status": status,
                        "End-to-End Duration (ms)": get_duration(close_response),
                        "Details": detail,
                    }
                )

            # Wait for the specified interval after each complete open-close cycle
            time.sleep(interval_ms / 1000.0)

    logging.info(f"--- {suite_name} execution completed ---")
    return results_list
