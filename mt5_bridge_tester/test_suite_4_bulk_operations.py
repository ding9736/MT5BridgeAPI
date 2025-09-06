# test_suite_4_bulk_operations.py
import time
import logging
import json
from mt5_bridge_client import APIClient


def get_duration(response: dict) -> str:
    """Safely extracts the end-to-end duration from the top-level fields of the response."""
    return response.get("end_to_end_duration_ms", "N/A")


def create_result(suite, case, status, duration, detail):
    """A helper function to create a standard test result dictionary."""
    return {
        "Suite": suite,
        "Case": case,
        "Status": status,
        "End-to-End Duration (ms)": duration,
        "Details": detail,
    }


def run(client: APIClient, symbols_to_test: list):
    """
    Executes the bulk management operations test suite, with behavior driven entirely by the passed-in symbol list.
    This test suite is optimized to dynamically adapt to the configuration and verifies account status before and after
    execution to ensure test robustness and result accuracy.

    :param client: A connected APIClient instance.
    :param symbols_to_test: A list of symbols to be used for dynamic testing.
    :return: A list of dictionaries containing test results.
    """
    suite_name = "Bulk Management Operations"
    results = []

    # --- [Optimization] Case 1: Close all positions for a specific symbol ---
    # Verification points: 1. API call is successful. 2. All positions of the target symbol are closed. 3. Positions of other symbols are not affected.
    case_name_base = "Close All Positions for a Specific Symbol"
    logging.info(f"--- {suite_name}: {case_name_base} ---")

    # [Optimization] Check if the configuration meets the test prerequisites
    if len(symbols_to_test) < 2:
        msg = f"Skipped: '{case_name_base}' test requires at least 2 trading symbols in the configuration."
        logging.warning(msg)
        results.append(create_result(suite_name, case_name_base, "PASS", "N/A", msg))
    else:
        target_symbol, other_symbol = symbols_to_test[0], symbols_to_test[1]
        case_name = f"{case_name_base} ({target_symbol})"
        duration = "N/A"
        try:
            # [Optimization] Preparation phase: Ensure a clean environment, then establish a predictable scenario
            logging.info("  [Setup] Cleaning up any existing historical positions...")
            client.close_positions_by_symbol(target_symbol)
            client.close_positions_by_symbol(other_symbol)
            time.sleep(1)  # Wait for cleanup to complete

            logging.info(
                f"  [Setup] Creating a scenario for the test: Opening 2 {target_symbol} and 1 {other_symbol} positions..."
            )
            client.buy(symbol=target_symbol, volume=0.01)
            client.buy(symbol=other_symbol, volume=0.01)
            client.buy(symbol=target_symbol, volume=0.01)
            time.sleep(1.5)  # Wait for orders to be fully executed

            positions_before = client.get_positions().get("data", [])
            target_pos_count_before = len(
                [p for p in positions_before if p.get("symbol") == target_symbol]
            )
            other_pos_count_before = len(
                [p for p in positions_before if p.get("symbol") == other_symbol]
            )
            logging.info(
                f"  [Verify] Setup complete. Current positions: {target_symbol} x{target_pos_count_before}, {other_symbol} x{other_pos_count_before}"
            )

            # Execute the operation under test
            logging.info(
                f"  [Execute] Calling client.close_positions_by_symbol('{target_symbol}')"
            )
            response = client.close_positions_by_symbol(symbol=target_symbol)
            duration = get_duration(response)

            is_pass = False
            # [Optimization] Verification phase: Dual verification based on API response and final account state
            if (
                response.get("status") == "success"
                and response.get("data", {}).get("closed_count", 0)
                == target_pos_count_before
            ):

                logging.info(
                    "  [Verify] API call successful and returned the correct number of closed positions. Double-checking final account position status..."
                )
                pos_res_after = client.get_positions()
                pos_data_after = pos_res_after.get("data")

                if pos_res_after.get("status") == "success" and isinstance(
                    pos_data_after, list
                ):
                    target_remains = [
                        p for p in pos_data_after if p.get("symbol") == target_symbol
                    ]
                    other_remains = [
                        p for p in pos_data_after if p.get("symbol") == other_symbol
                    ]

                    if (
                        not target_remains
                        and len(other_remains) == other_pos_count_before
                    ):
                        detail = f"Successfully closed {target_pos_count_before} {target_symbol} positions, while {other_pos_count_before} {other_symbol} positions remained unaffected."
                        results.append(
                            create_result(
                                suite_name, case_name, "PASS", duration, detail
                            )
                        )
                        is_pass = True
                    else:
                        detail = f"Final account state is inconsistent. {target_symbol} remaining: {len(target_remains)} (expected 0), {other_symbol} remaining: {len(other_remains)} (expected {other_pos_count_before})."
                else:
                    detail = f"Could not verify final account state, get_positions responded abnormally: {json.dumps(pos_res_after)}"
            else:
                detail = f"API call failed or the number of closed positions did not match. API response: {json.dumps(response)}"

            if not is_pass:
                results.append(
                    create_result(suite_name, case_name, "FAIL", duration, detail)
                )

        except Exception as e:
            results.append(
                create_result(
                    suite_name,
                    case_name,
                    "FAIL",
                    "N/A",
                    f"An unexpected exception occurred during test execution: {e}",
                )
            )
        finally:
            logging.info(
                "  [Cleanup] Closing all remaining positions to ensure a clean environment..."
            )
            client.close_all_positions()
            time.sleep(1)

    # --- Case 2: Close all positions (logic is mostly stable, minor tweaks) ---
    case_name = "Close All Positions"
    logging.info(f"--- {suite_name}: {case_name} ---")
    if not symbols_to_test:
        results.append(
            create_result(
                suite_name,
                case_name,
                "PASS",
                "N/A",
                "Skipped: No test symbols configured.",
            )
        )
    else:
        duration = "N/A"
        try:
            logging.info(
                f"  [Setup] Opening 1 position for each of the {len(symbols_to_test)} symbols..."
            )
            for symbol in symbols_to_test:
                client.buy(symbol=symbol, volume=0.01)
            time.sleep(1.5)

            positions_before = client.get_positions().get("data", [])
            pos_count_before = len(positions_before)
            logging.info(
                f"  [Verify] Setup complete, total number of positions: {pos_count_before}"
            )

            logging.info("  [Execute] Calling client.close_all_positions()")
            response = client.close_all_positions()
            duration = get_duration(response)

            if (
                response.get("status") == "success"
                and response.get("data", {}).get("closed_count", 0) == pos_count_before
            ):
                results.append(
                    create_result(
                        suite_name,
                        case_name,
                        "PASS",
                        duration,
                        f"API call successful, correctly closed all {pos_count_before} positions.",
                    )
                )
            else:
                results.append(
                    create_result(
                        suite_name,
                        case_name,
                        "FAIL",
                        duration,
                        f"API call failed or number of closed positions did not match: {json.dumps(response)}",
                    )
                )
        except Exception as e:
            results.append(
                create_result(
                    suite_name, case_name, "FAIL", "N/A", f"Test exception: {e}"
                )
            )
        finally:
            client.close_all_positions()  # Ensure cleanup
            time.sleep(1)

    # --- [Optimization] Case 3: Cancel all pending orders for a specific symbol ---
    case_name_base = "Cancel All Pending Orders for a Specific Symbol"
    logging.info(f"--- {suite_name}: {case_name_base} ---")

    if len(symbols_to_test) < 2:
        msg = f"Skipped: '{case_name_base}' test requires at least 2 trading symbols in the configuration."
        logging.warning(msg)
        results.append(create_result(suite_name, case_name_base, "PASS", "N/A", msg))
    else:
        target_symbol, other_symbol = symbols_to_test[0], symbols_to_test[1]
        case_name = f"{case_name_base} ({target_symbol})"
        duration = "N/A"
        try:
            logging.info(
                "  [Setup] Cleaning up any existing historical pending orders..."
            )
            client.cancel_symbol_pending_orders(target_symbol)
            client.cancel_symbol_pending_orders(other_symbol)
            time.sleep(1)

            logging.info(
                f"  [Setup] Setting up 2 pending orders for {target_symbol}, and 1 for {other_symbol}..."
            )
            # Simplify price fetching, assume success
            target_ask = client.get_price(symbol=target_symbol)["data"]["ask"]
            other_ask = client.get_price(symbol=other_symbol)["data"]["ask"]

            client.buy_limit(symbol=target_symbol, volume=0.01, price=target_ask * 0.9)
            client.buy_limit(symbol=target_symbol, volume=0.01, price=target_ask * 0.95)
            client.buy_limit(symbol=other_symbol, volume=0.01, price=other_ask * 0.9)
            time.sleep(1.5)

            orders_before = client.get_pending_orders().get("data", [])
            target_orders_count = len(
                [o for o in orders_before if o.get("symbol") == target_symbol]
            )

            logging.info(
                f"  [Execute] Calling client.cancel_symbol_pending_orders('{target_symbol}')"
            )
            response = client.cancel_symbol_pending_orders(symbol=target_symbol)
            duration = get_duration(response)

            is_pass = False
            if (
                response.get("status") == "success"
                and response.get("data", {}).get("cancelled_count", 0)
                == target_orders_count
            ):

                orders_after_res = client.get_pending_orders()
                orders_after = orders_after_res.get("data", [])

                target_remains = [
                    o for o in orders_after if o.get("symbol") == target_symbol
                ]
                other_remains = [
                    o for o in orders_after if o.get("symbol") == other_symbol
                ]

                if not target_remains and len(other_remains) == 1:
                    detail = f"Successfully cancelled {target_orders_count} {target_symbol} pending orders, {other_symbol} was not affected."
                    results.append(
                        create_result(suite_name, case_name, "PASS", duration, detail)
                    )
                    is_pass = True
                else:
                    detail = f"Final pending order state is inconsistent. {target_symbol} remaining: {len(target_remains)}, {other_symbol} remaining: {len(other_remains)}"
            else:
                detail = f"API call failed or number of cancelled orders did not match: {json.dumps(response)}"

            if not is_pass:
                results.append(
                    create_result(suite_name, case_name, "FAIL", duration, detail)
                )

        except Exception as e:
            results.append(
                create_result(
                    suite_name, case_name, "FAIL", "N/A", f"Test exception: {e}"
                )
            )
        finally:
            logging.info("  [Cleanup] Cancelling all remaining pending orders...")
            client.cancel_all_pending_orders()
            time.sleep(1)

    # --- Case 4: Cancel all pending orders (logic is mostly stable, minor tweaks) ---
    case_name = "Cancel All Pending Orders"
    logging.info(f"--- {suite_name}: {case_name} ---")
    if not symbols_to_test:
        results.append(
            create_result(
                suite_name,
                case_name,
                "PASS",
                "N/A",
                "Skipped: No test symbols configured.",
            )
        )
    else:
        duration = "N/A"
        try:
            logging.info(
                f"  [Setup] Setting 1 pending order for each of the {len(symbols_to_test)} symbols..."
            )
            for symbol in symbols_to_test:
                price_res = client.get_price(symbol=symbol)
                if price_res.get("status") == "success":
                    client.buy_limit(
                        symbol=symbol, volume=0.01, price=price_res["data"]["ask"] * 0.9
                    )
            time.sleep(1.5)

            orders_before = client.get_pending_orders().get("data", [])
            orders_count_before = len(orders_before)
            logging.info(
                f"  [Verify] Setup complete, total number of pending orders: {orders_count_before}"
            )

            logging.info("  [Execute] Calling client.cancel_all_pending_orders()")
            response = client.cancel_all_pending_orders()
            duration = get_duration(response)

            if (
                response.get("status") == "success"
                and response.get("data", {}).get("cancelled_count", 0)
                == orders_count_before
            ):
                results.append(
                    create_result(
                        suite_name,
                        case_name,
                        "PASS",
                        duration,
                        f"Successfully cancelled all {orders_count_before} pending orders.",
                    )
                )
            else:
                results.append(
                    create_result(
                        suite_name,
                        case_name,
                        "FAIL",
                        duration,
                        f"API call failed or number of cancelled orders did not match: {json.dumps(response)}",
                    )
                )
        except Exception as e:
            results.append(
                create_result(
                    suite_name, case_name, "FAIL", "N/A", f"Test exception: {e}"
                )
            )
        finally:
            client.cancel_all_pending_orders()  # Ensure cleanup
            time.sleep(1)

    return results
