

```markdown
# MT5RemoteBridgeAPI - High-Performance, Military-Grade Encrypted MT5 Trading Bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`MT5RemoteBridgeAPI` is a production-grade, high-performance service framework for MetaTrader 5 (MT5). It implements a client-driven communication bridge using ZeroMQ, allowing external applications (e.g., Python, C#, Node.js) to interact with the MT5 terminal securely and efficiently for programmatic trading, account management, data subscription, and other advanced functionalities.

This project is maintained by **ding9736** and is licensed under the **MIT License**.

## Core Features ✨

*   🛡️ **Military-Grade Security (ZAP & Curve25519)**: This is the core highlight of the framework. It implements the **ZeroMQ Authentication Protocol (ZAP)** to dynamically establish point-to-point encrypted sessions for each client. All communication is encrypted using the industry-leading **Curve25519** algorithm, fundamentally preventing man-in-the-middle attacks and data snooping, ensuring the absolute confidentiality and integrity of your trading commands and strategy information.

*   ⚡ **Extreme Performance**: Based on ZeroMQ's (ZMQ) asynchronous messaging model, it achieves microsecond-level low latency and high throughput. It can handle high-frequency tick data and intensive trading orders with ease.

*   🔗 **Powerful API Design**: Provides clear Request/Reply (REQ/REP) and Publish/Subscribe (PUB/SUB) patterns. The API covers dozens of interfaces for accounts, market data, trades, orders, and historical data. It is feature-complete, highly decoupled, and easy to integrate into any language.

*   📈 **Production-Grade Stability**: Includes a detailed tiered logging system, heartbeat keep-alive mechanism, connection status monitoring, and robust error handling. Designed for 24/7 uninterrupted operation in a production environment.

*   🔧 **Highly Flexible Configuration**: Core server parameters (ports, keys, trading defaults, etc.) can be configured via an external JSON file, with support for hot-reloading of some parameters without restarting the service.

*   🐍 **Comprehensive Python Client & Test Suite**: The project includes a full-featured Python client `mt5_bridge_client` as the official reference implementation. It also provides a complete test suite with unit tests, trading logic tests, concurrency stress tests, and performance benchmarks, ready to use out-of-the-box.

## Prerequisites

#### Server-Side

*   OS: Windows
*   Trading Platform: MetaTrader 5 Client (Build 1860 or newer)

#### Client-Side (Python Test Environment)

*   Python 3.7 or higher
*   Required Python libraries. You can install them with a single command:

```shell
pip install pyzmq pynacl pandas rich
```

* `pyzmq`: Python bindings for ZeroMQ, handles core communication.
* `pynacl`: Python bindings for the `libsodium` encryption library, responsible for Curve25519 encryption.
* `pandas`: Used for convenient handling and display of tabular data (like historical OHLC, positions list).
* `rich`: Used to create beautiful and readable test report outputs in the terminal.

## Deployment and Startup Guide 🚀

### Step 1: Deploy MQL5 Files

Copy the `MQL5` folder from this project's repository and overwrite the `MQL5` folder in your MT5 terminal's **data directory**.

> **Tip**: In the MT5 terminal, you can quickly locate the data directory via the menu "File" -> "Open Data Folder".

### Step 2: Generate Server Keys

Navigate to the `MQL5\Files\MT5RemoteBridgeAPI_Services_config\` path within your MT5 data directory. You will find the `generate_MT5RemoteBridgeAPI_keys.py` script.

Run it from the command line:

```shell
python generate_MT5RemoteBridgeAPI_keys.py
```

This script will generate and print your unique **ServerPublicKey** and **ServerSecretKey**. Copy them, as you will need them for the next step.

### Step 3: Configure the Server

In the same directory (`MQL5\Files\MT5RemoteBridgeAPI_Services_config\`), open the `MT5RemoteBridgeAPI_Services_config.json` configuration file with a text editor.

Complete the configuration based on the comments and your requirements:

```json
{
  "HandshakePort": 5555,          // Handshake port (plaintext, used for key exchange)
  "CmdPort": 5556,                // Command port (encrypted)
  "PubPort": 5557,                // Data publication port (encrypted)
  "AuthKey": "your_strong_and_secret_auth_key", // Custom authentication key, must match the client's key
  "ServerPublicKey": "Paste your generated ServerPublicKey from Step 2 here",
  "ServerSecretKey": "Paste your generated ServerSecretKey from Step 2 here",
  "MagicNumber": 123456,          // Default trading magic number
  "Slippage": 10,                 // Default slippage
  "TimerMs": 5,                   // Service main loop interval (milliseconds)
  "HeartbeatSec": 5               // Heartbeat sending interval (seconds)
}
```

### Step 4: Install and Start the Service in MT5

1. **Restart the MT5 terminal** to load the new program files.
2. In the MT5 "Navigator" window, right-click on "Services" and select "**Add Service**".
3. Find and select `MT5RemoteBridgeAPI` from the list.
4. **【CRITICAL STEP】** In the properties window that opens, switch to the "**Dependencies**" tab and **you must check "Allow DLL imports"**. This is essential for ZeroMQ to work correctly.
5. Click "OK". The service will appear in the "Services" list.
6. Right-click on the newly added `MT5RemoteBridgeAPI` service and select "**Start**".

After the service starts, you can check the "Experts" log in MT5 for detailed startup information and status.

## Running the Client Test Suite 🧪

The client test suite is located in the `mt5_bridge_tester` folder and is the best way to verify a successful deployment.

### Step 1: Configure the Client

Open the `MT5RemoteBridgeAPI_client_config.json` file in the `mt5_bridge_tester\config\` directory.

Ensure its configuration matches the server's:

```json
{
  "server_ip": "127.0.0.1",        // IP address of the MT5 server
  "handshake_port": 5555,          // Must match the server's HandshakePort
  "auth_key": "your_strong_and_secret_auth_key", // Must match the server's AuthKey
  "request_timeout": 5000
}
```

### Step 2: Execute the Tests

In your terminal, navigate to the `mt5_bridge_tester` folder and run the main test script:

```shell
python run_all_tests.py
```

The script will automatically execute a series of tests covering all core API functionalities. You will see formatted, real-time results. If all test items show `[PASSED]`, congratulations! Your entire system has been successfully deployed and is ready for use.

## Developer

* **ding9736**

## License

This project is released under the [MIT License](https://opensource.org/licenses/MIT).
```
