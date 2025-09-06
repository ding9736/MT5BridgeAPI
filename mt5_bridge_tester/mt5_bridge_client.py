# mt5_bridge_client.py
import zmq
import json
import threading
import time
import logging
import random
import os
from datetime import datetime
import pandas as pd

# ==============================================================================
# [Core Library Configuration] - Defines the config file path required by the API client itself
# ==============================================================================
CONFIG_DIR = "config"
CONFIG_FILE_NAME = "MT5RemoteBridgeAPI_client_config.json"
# ==============================================================================


class APIClient:
    """
    A core client for secure, thread-safe communication with the MT5RemoteBridgeAPI server.
    It handles the entire process of handshake, encryption, command sending, and data subscription.
    """

    def __init__(self, history_cache_dir="history_cache"):
        """
        The constructor no longer accepts a configuration dictionary directly, but loads it internally.
        """
        self.config = self._load_config()
        self.context = zmq.Context()
        self.req_socket = None
        self.sub_socket = None
        self.stop_event = threading.Event()
        self.listener_thread = None
        self.req_lock = threading.Lock()

        self.server_public_key = None
        self.cmd_endpoint = None

        # Added cache directory attribute
        self.history_cache_dir = history_cache_dir
        if not os.path.exists(self.history_cache_dir):
            os.makedirs(self.history_cache_dir)

        logging.info("Generating new temporary key pair for this session...")
        self.client_public_key, self.client_secret_key = zmq.curve_keypair()
        logging.info("Temporary key pair generated.")

    def _load_config(self) -> dict:
        """
        Internal method to load the configuration file, implementing self-managed configuration.
        """
        config_path = os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)
        logging.info(f"Loading core configuration file from '{config_path}'...")
        try:
            if not os.path.exists(CONFIG_DIR):
                os.makedirs(CONFIG_DIR)
                logging.warning(
                    f"Configuration directory '{CONFIG_DIR}' did not exist and has been created. Please ensure '{config_path}' exists and is configured correctly."
                )

            with open(config_path, "r") as f:
                config = json.load(f)
                logging.info("Core configuration file loaded successfully.")
                return config
        except FileNotFoundError:
            logging.error(f"Fatal Error: Configuration file '{config_path}' not found.")
            raise
        except json.JSONDecodeError as e:
            logging.error(
                f"Fatal Error: Configuration file '{config_path}' is malformed: {e}"
            )
            raise

    def connect(self):
        logging.info("Starting connection process...")
        handshake_socket = self.context.socket(zmq.REQ)
        handshake_socket.linger = 0
        handshake_endpoint = (
            f"tcp://{self.config['server_ip']}:{self.config['handshake_port']}"
        )
        handshake_socket.connect(handshake_endpoint)
        logging.info(f"Connected to handshake port: {handshake_endpoint}")

        handshake_request = {
            "action": "request_session_keys",
            "auth_key": self.config["auth_key"],
            "client_public_key": self.client_public_key.decode("utf-8"),
        }
        handshake_socket.send_json(handshake_request)

        poller = zmq.Poller()
        poller.register(handshake_socket, zmq.POLLIN)
        if not poller.poll(self.config["request_timeout"]):
            raise ConnectionError(
                "Handshake timed out, no response received from server."
            )

        try:
            response = handshake_socket.recv_json()
        except json.JSONDecodeError as e:
            raise ConnectionError(
                f"Handshake failed: Could not parse server response. Error: {e}"
            )
        finally:
            handshake_socket.close()

        if response.get("status") != "success":
            raise ConnectionError(f"Handshake failed: {response.get('message')}")

        logging.info(
            "Handshake successful, client is authorized and has received server session info."
        )
        server_data = response["data"]

        self.server_public_key = server_data["server_public_key"].encode("utf-8")
        cmd_port = server_data["encrypted_cmd_port"]
        pub_port = server_data["encrypted_pub_port"]
        self.cmd_endpoint = f"tcp://{self.config['server_ip']}:{cmd_port}"
        pub_endpoint = f"tcp://{self.config['server_ip']}:{pub_port}"

        self._connect_req_socket()
        self._connect_sub_socket(pub_endpoint)

        self.listener_thread = threading.Thread(target=self._listen_for_updates)
        self.listener_thread.daemon = True
        self.listener_thread.start()
        logging.info("Background data listener thread has started.")
        time.sleep(0.5)
        logging.info("Connection process complete, client is ready.")

    def _connect_req_socket(self):
        """Internal method to connect or reconnect the REQ socket"""
        if self.req_socket:
            self.req_socket.close()
        self.req_socket = self.context.socket(zmq.REQ)
        self.req_socket.linger = 0
        self.req_socket.curve_serverkey = self.server_public_key
        self.req_socket.curve_publickey = self.client_public_key
        self.req_socket.curve_secretkey = self.client_secret_key
        self.req_socket.connect(self.cmd_endpoint)
        logging.info(f"Connected to encrypted command port: {self.cmd_endpoint}")

    def _connect_sub_socket(self, pub_endpoint):
        """Internal method to connect the SUB socket"""
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.linger = 0
        self.sub_socket.curve_serverkey = self.server_public_key
        self.sub_socket.curve_publickey = self.client_public_key
        self.sub_socket.curve_secretkey = self.client_secret_key
        self.sub_socket.connect(pub_endpoint)
        logging.info(f"Connected to encrypted publishing port: {pub_endpoint}")

    def _listen_for_updates(self):
        poller = zmq.Poller()
        poller.register(self.sub_socket, zmq.POLLIN)
        logging.info("Listener thread starting its loop...")
        while not self.stop_event.is_set():
            try:
                if poller.poll(200):
                    topic, data_str = self.sub_socket.recv_multipart()
                    data = json.loads(data_str.decode("utf-8"))
                    logging.info(
                        f"[Subscribed Data] Topic: {topic.decode('utf-8')}, Content: {data}"
                    )
            except zmq.error.ContextTerminated:
                break
        logging.info("Listener thread has stopped.")

    def close(self):
        logging.info("Closing the client...")
        self.stop_event.set()
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=1)
        if self.req_socket:
            self.req_socket.close()
        if self.sub_socket:
            self.sub_socket.close()
        self.context.term()
        logging.info("Client has been fully closed.")

    def _generate_python_id(self) -> str:
        return f"{int(time.time() * 1000)}-{random.randint(1000, 9999)}"

    def _send_request(self, request: dict) -> dict:
        if not self.req_socket:
            return {
                "status": "error",
                "message": "Client not connected",
                "error_code": 503,
            }
        request["auth_key"] = self.config["auth_key"]
        request["python_id"] = self._generate_python_id()
        with self.req_lock:
            try:
                start_time = time.time()
                self.req_socket.send_json(request)
                poller = zmq.Poller()
                poller.register(self.req_socket, zmq.POLLIN)
                if poller.poll(self.config["request_timeout"]):
                    response = self.req_socket.recv_json()
                    end_to_end_duration = (time.time() - start_time) * 1000
                    response["end_to_end_duration_ms"] = f"{end_to_end_duration:.2f}"
                    return response
                else:
                    # [Robustness] Timeout self-healing logic
                    logging.warning(
                        f"Request '{request.get('action')}' timed out, attempting to reconnect REQ socket..."
                    )
                    self._connect_req_socket()
                    return {
                        "status": "error",
                        "message": f"Request '{request.get('action')}' timed out",
                        "error_code": 408,
                    }
            except zmq.error.ZMQError as e:
                logging.error(f"A ZMQ error occurred while sending the request: {e}")
                return {
                    "status": "error",
                    "message": f"ZMQ communication error: {e}",
                    "error_code": 500,
                }

    # --- Query APIs ---
    def get_account_info(self):
        return self._send_request({"action": "get_account_info"})

    def get_server_info(self):
        return self._send_request({"action": "get_server_info"})

    def get_positions(self, symbol: str = ""):
        return self._send_request({"action": "get_positions", "symbol": symbol})

    def get_pending_orders(self, symbol: str = ""):
        return self._send_request({"action": "get_pending_orders", "symbol": symbol})

    def get_price(self, symbol: str):
        return self._send_request({"action": "get_price", "symbol": symbol})

    # --- Historical Data API (with caching) ---
    def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_time=None,
        end_time=None,
        count: int = 0,
    ):
        # 1. Generate cache filename
        start_ts = (
            int(start_time.timestamp()) if isinstance(start_time, datetime) else 0
        )
        end_ts = int(end_time.timestamp()) if isinstance(end_time, datetime) else 0
        cache_filename = f"{symbol}_{timeframe}_{start_ts}_{end_ts}_{count}.parquet"
        cache_path = os.path.join(self.history_cache_dir, cache_filename)

        # 2. Check cache
        if os.path.exists(cache_path):
            try:
                logging.info(f"Loading historical data from cache: {cache_path}")
                df = pd.read_parquet(cache_path)
                return df
            except Exception as e:
                logging.warning(
                    f"Failed to read cache file {cache_path}: {e}. Will refetch from server."
                )

        # 3. Cache miss, fetch from server
        request = {"action": "get_bars", "symbol": symbol, "timeframe": timeframe}
        if start_time:
            st = start_time
            if isinstance(st, str):
                st = datetime.strptime(st, "%Y-%m-%d %H:%M:%S")
            request["start_time"] = int(st.timestamp())

            if end_time:
                et = end_time
                if isinstance(et, str):
                    et = datetime.strptime(et, "%Y-%m-%d %H:%M:%S")
                request["end_time"] = int(et.timestamp())
            else:
                request["end_time"] = 0
        else:
            request["start_pos"] = 0
            request["count"] = count if count > 0 else 100

        response = self._send_request(request)

        # 4. Process response and save to cache
        if response.get("status") == "success" and response.get("data"):
            df = pd.DataFrame.from_records(response["data"])
            if not df.empty:
                df["time"] = pd.to_datetime(df["time"], unit="s")
                df.set_index("time", inplace=True)
                df.sort_index(inplace=True)  # Ensure time is in ascending order
                try:
                    df.to_parquet(cache_path)
                    logging.info(f"Historical data cached to: {cache_path}")
                except Exception as e:
                    # **[Optimization]** Changed log level from ERROR to WARNING.
                    # A cache failure should not be treated as a critical error, as it doesn't affect the success of the core function (fetching data from the server).
                    logging.warning(f"Failed to cache historical data: {e}")
            return df
        else:
            logging.error(
                f"Failed to get historical data: {response.get('message', 'Unknown error')}"
            )
            return pd.DataFrame()

    # --- Subscription APIs ---
    def subscribe_symbols(self, symbols: list):
        for symbol in symbols:
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, f"TICK.{symbol}")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "HEARTBEAT")
        return self._send_request({"action": "subscribe_symbols", "symbols": symbols})

    def unsubscribe_symbols(self, symbols: list):
        for symbol in symbols:
            self.sub_socket.setsockopt_string(zmq.UNSUBSCRIBE, f"TICK.{symbol}")
        return self._send_request({"action": "unsubscribe_symbols", "symbols": symbols})

    # --- Trading APIs ---
    def buy(self, **kwargs):
        kwargs["action"] = "buy"
        return self._send_request(kwargs)

    def sell(self, **kwargs):
        kwargs["action"] = "sell"
        return self._send_request(kwargs)

    def buy_limit(self, **kwargs):
        kwargs["action"] = "buy_limit"
        return self._send_request(kwargs)

    def sell_limit(self, **kwargs):
        kwargs["action"] = "sell_limit"
        return self._send_request(kwargs)

    def modify_position(self, **kwargs):
        kwargs["action"] = "modify_position"
        return self._send_request(kwargs)

    def close_position_by_ticket(self, **kwargs):
        kwargs["action"] = "close_position_by_ticket"
        return self._send_request(kwargs)

    # --- Bulk Management APIs ---
    def close_all_positions(self):
        return self._send_request({"action": "close_all_positions"})

    def close_positions_by_symbol(self, symbol: str):
        return self._send_request(
            {"action": "close_positions_by_symbol", "symbol": symbol}
        )

    def cancel_all_pending_orders(self):
        return self._send_request({"action": "cancel_all_pending_orders"})

    def cancel_symbol_pending_orders(self, symbol: str):
        return self._send_request(
            {"action": "cancel_symbol_pending_orders", "symbol": symbol}
        )
