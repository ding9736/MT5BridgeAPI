# test_suite_2_trading_logic.py
import time
import logging
from mt5_bridge_client import APIClient


def get_duration(response: dict) -> str:
    return response.get("end_to_end_duration_ms", "N/A")


def run(client: APIClient, symbols_to_test: list):
    suite_name = "Trading Logic"
    results = []
    if not symbols_to_test:
        logging.warning(
            "No trading symbols provided in the configuration, skipping trading logic test."
        )
        return results

    opened_tickets = {symbol: [] for symbol in symbols_to_test}

    for symbol in symbols_to_test:
        for i in range(2):
            iteration = i + 1
            logging.info(f"\n--- Symbol {symbol}, Round {iteration}/2 ---")

            # Open Position
            case_name, ticket = f"Open {symbol} Buy Order #{iteration}", None
            logging.info(f"--- {suite_name}: {case_name} ---")
            response = client.buy(symbol=symbol, volume=0.01)
            if response.get("status") == "success" and response.get("data", {}).get(
                "ticket"
            ):
                ticket = response["data"]["ticket"]
                opened_tickets[symbol].append(ticket)
                results.append(
                    {
                        "Suite": suite_name,
                        "Case": case_name,
                        "Status": "PASS",
                        "End-to-End Duration (ms)": get_duration(response),
                        "Details": f"Order successful, Ticket: {ticket}",
                    }
                )
            else:
                results.append(
                    {
                        "Suite": suite_name,
                        "Case": case_name,
                        "Status": "FAIL",
                        "End-to-End Duration (ms)": get_duration(response),
                        "Details": f"Failed to open position: {response.get('message', response)}",
                    }
                )
            time.sleep(1)

            # Modify
            if ticket:
                case_name = f"Modify {symbol} Order {ticket} #{iteration}"
                logging.info(f"--- {suite_name}: {case_name} ---")
                price_info = client._send_request(
                    {"action": "get_price", "symbol": symbol}
                )
                if price_info.get("status") == "success":
                    ask = price_info["data"]["ask"]
                    sl = ask * 0.95
                    tp = ask * 1.05
                    response = client.modify_position(ticket=ticket, sl=sl, tp=tp)
                    status = "PASS" if response.get("status") == "success" else "FAIL"
                    detail = (
                        "SL/TP modified successfully"
                        if status == "PASS"
                        else f"Modification failed: {response.get('message')}"
                    )
                    results.append(
                        {
                            "Suite": suite_name,
                            "Case": case_name,
                            "Status": status,
                            "End-to-End Duration (ms)": get_duration(response),
                            "Details": detail,
                        }
                    )
                else:
                    results.append(
                        {
                            "Suite": suite_name,
                            "Case": case_name,
                            "Status": "FAIL",
                            "End-to-End Duration (ms)": get_duration(price_info),
                            "Details": "Could not get price to set SL/TP",
                        }
                    )
                time.sleep(1)

    # Close Positions
    logging.info(
        "\n--- Starting unified cleanup of all positions opened during the test ---"
    )
    for symbol, tickets in opened_tickets.items():
        for ticket in tickets:
            case_name = f"Close {symbol} Order {ticket}"
            logging.info(f"--- {suite_name}: {case_name} ---")
            response = client.close_position_by_ticket(ticket=ticket)
            status = "PASS" if response.get("status") == "success" else "FAIL"
            detail = (
                "Position closed successfully"
                if status == "PASS"
                else f"Failed to close position: {response.get('message')}"
            )
            results.append(
                {
                    "Suite": suite_name,
                    "Case": case_name,
                    "Status": status,
                    "End-to-End Duration (ms)": get_duration(response),
                    "Details": detail,
                }
            )
            time.sleep(1)

    return results
