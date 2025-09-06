# test_suite_1_basic_ops.py
import time
import logging
from mt5_bridge_client import APIClient
from test_utils import record_result, record_df_result
from datetime import datetime, timedelta


def run(client: APIClient, config: dict):
    suite_name = "Basic Operations"
    results = []
    symbols_to_test = config["trading_settings"]["symbols_to_test"]

    # Case 1: Get Account Info
    case_name = "Get Account Info"
    logging.info(f"--- {suite_name}: {case_name} ---")
    response = client.get_account_info()
    results.append(record_result(suite_name, case_name, response))

    # Case 2: Get Server Info
    case_name = "Get Server Info"
    logging.info(f"--- {suite_name}: {case_name} ---")
    response = client.get_server_info()
    results.append(record_result(suite_name, case_name, response))

    # Case 3: Subscribe to Market Data
    if not symbols_to_test:
        logging.warning(
            "No trading symbols provided in the configuration, skipping market data subscription test."
        )
    else:
        case_name = f"Subscribe to Market Data {symbols_to_test}"
        logging.info(f"--- {suite_name}: {case_name} ---")
        response = client.subscribe_symbols(symbols_to_test)
        is_success = response.get("data", {}).get("failed_count", -1) == 0
        results.append(
            record_result(
                suite_name,
                case_name,
                response,
                success_condition=is_success,
                detail_on_pass="Subscription successful",
            )
        )

        if response.get("status") == "success":
            logging.info("Waiting 5 seconds to receive quote data...")
            time.sleep(5)

    # Case 4: Get Historical Data (by count)
    history_params_count = config["history_test_params"]["by_count"]
    symbol, timeframe, count = (
        history_params_count["symbol"],
        history_params_count["timeframe"],
        history_params_count["count"],
    )
    case_name = f"Get Historical Candlesticks (by count: {count}, {symbol} {timeframe})"
    logging.info(f"--- {suite_name}: {case_name} ---")

    start_time = time.time()
    df = client.get_historical_data(symbol=symbol, timeframe=timeframe, count=count)
    duration_ms = f"{(time.time() - start_time) * 1000:.2f}"

    is_success = df is not None and not df.empty and len(df) == count
    detail_pass = f"Successfully retrieved {len(df)} candlesticks. Latest close price: {df['close'].iloc[-1]}"
    detail_fail = f"Failed to retrieve or mismatched count ({len(df) if df is not None else 'None'}/{count})"
    results.append(
        record_df_result(
            suite_name, case_name, df, duration_ms, is_success, detail_pass, detail_fail
        )
    )
    time.sleep(0.5)

    # Case 5: Get Historical Data (by time)
    history_params_time = config["history_test_params"]["by_time"]
    symbol, timeframe, days = (
        history_params_time["symbol"],
        history_params_time["timeframe"],
        history_params_time["days_ago"],
    )
    case_name = (
        f"Get Historical Candlesticks (by time: last {days} days, {symbol} {timeframe})"
    )
    logging.info(f"--- {suite_name}: {case_name} ---")

    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=days)

    start_time = time.time()
    df = client.get_historical_data(
        symbol=symbol, timeframe=timeframe, start_time=start_dt, end_time=end_dt
    )
    duration_ms = f"{(time.time() - start_time) * 1000:.2f}"

    is_success = df is not None and not df.empty
    detail_pass = f"Successfully retrieved {len(df)} candlesticks. Time range: {df.index.min()} -> {df.index.max()}"
    detail_fail = "Failed to retrieve or no data in the specified time range."
    results.append(
        record_df_result(
            suite_name, case_name, df, duration_ms, is_success, detail_pass, detail_fail
        )
    )

    return results
