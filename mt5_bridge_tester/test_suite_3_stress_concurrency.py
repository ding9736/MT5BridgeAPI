# test_suite_3_stress_concurrency.py
import time
import logging
import threading
from mt5_bridge_client import APIClient


def get_duration(response: dict) -> str:
    return response.get("end_to_end_duration_ms", "N/A")


def trading_cycle(
    client: APIClient,
    symbol: str,
    iterations: int,
    results_list: list,
    interval_ms: int,
):
    """
    Concurrent test loop for a single trading symbol.
    [Optimization] Added interval_ms parameter to introduce a delay after each cycle, enabling request throttling.
    """
    suite_name = "Concurrent Performance Test (Throttled)"
    for i in range(iterations):
        logging.info(f"[Thread {symbol}] Starting round {i+1}/{iterations}...")

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
            # If opening position fails, no need to continue this cycle
            time.sleep(interval_ms / 1000.0)
            continue

        # Close position
        if ticket:
            time.sleep(0.2)  # Maintain a short, fixed interval between open and close
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

        # [New] Wait after each complete open-close cycle according to the configured throttle interval
        time.sleep(interval_ms / 1000.0)


def run(client: APIClient, symbols_to_test: list, iterations: int, interval_ms: int):
    """
    Runs the concurrent stress test suite.
    [Optimization] Added interval_ms parameter, passed to each worker thread to control the request rate.
    """
    if not symbols_to_test:
        logging.warning(
            "No trading symbols provided in the configuration, skipping concurrent stress test."
        )
        return []

    logging.info(
        f"--- Concurrent Stress Test: Each symbol will execute {iterations} rounds of open-close cycles, with a cycle interval of {interval_ms} ms ---"
    )
    threads, results_list = [], []
    for symbol in symbols_to_test:
        thread = threading.Thread(
            target=trading_cycle,
            args=(client, symbol, iterations, results_list, interval_ms),
        )
        threads.append(thread)
        thread.start()
        logging.info(f"Started trading thread for {symbol}...")
    for thread in threads:
        thread.join()
    logging.info("--- All concurrent stress test threads have completed ---")
    return results_list
