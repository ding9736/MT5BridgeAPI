---

# MT5RemoteBridgeAPI - 高性能、军事级加密MT5交易桥

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`MT5RemoteBridgeAPI` 是一个为 MetaTrader 5 (MT5) 设计的、生产级的高性能服务框架。它通过 ZeroMQ 实现了一个由客户端驱动的通信桥梁，允许外部应用程序（如 Python, C#, Node.js 等）与 MT5 终端进行安全、高效的交互，实现程序化交易、账户管理、数据订阅等高级功能。

项目由 **ding9736** 维护，并遵循 **MIT 开源协议**。

## 核心特性 ✨

* 🛡️ **军事级安全 (ZAP & Curve25519)**: 本框架的核心亮点。它实现了 **ZeroMQ 认证协议 (ZAP)**，为每一个客户端动态建立点对点的加密会话。所有通信都使用行业顶尖的 **Curve25519** 算法进行加密，从根本上杜绝了中间人攻击和数据窃听，确保您的交易指令和策略信息在传输过程中的绝对机密与完整。

* ⚡ **极致性能**: 基于 ZeroMQ (ZMQ) 的异步消息模型，实现微秒级的低延迟和高吞吐量通信。无论是处理高频行情数据（Tick），还是执行密集的交易指令，都能游刃有余。

* 🔗 **强大的 API 设计**: 提供清晰的请求/响应 (REQ/REP) 和发布/订阅 (PUB/SUB) 模式。API 覆盖了账户、行情、交易、订单、历史数据等数十种接口，功能完整且高度解耦，易于在任何语言中集成。

* 📈 **生产级稳定性**: 内置了详细的分级日志系统、心跳保活机制、连接状态监控和健壮的错误处理。专为 7x24 小时不间断运行的生产环境设计。

* 🔧 **高度灵活配置**: 服务端核心参数（端口、密钥、交易默认值等）均可通过外部 JSON 文件配置，并支持部分参数的热重载，无需重启服务即可调整策略参数。

* 🐍 **完善的 Python 客户端 & 测试套件**: 项目自带一个功能完备的 Python 客户端 `mt5_bridge_client` 作为官方参考实现。同时提供了一个包含单元测试、交易逻辑测试、并发压力测试和性能基准测试的完整测试套件，开箱即用。

## 先决条件

#### 服务端

* 操作系统: Windows
* 交易平台: MetaTrader 5 客户端 (Build 1860 或更高版本)

#### 客户端 (Python 测试环境)

* Python 3.7 或更高版本
* 所需的 Python 库。可以通过以下命令一键安装：

```shell
pip install pyzmq pynacl pandas rich
`*   `pyzmq`: ZeroMQ 的 Python 绑定，负责核心通信。
*   `pynacl`: `libsodium` 加密库的 Python 绑定，负责实现 Curve25519 加密。
*   `pandas`: 用于便捷地处理和展示表格化数据（如历史K线、持仓列表）。
*   `rich`: 用于在终端中创建美观、易读的测试报告输出。

## 部署与启动指南 🚀

### 第1步: 部署 MQL5 文件

将本项目代码库中的 `MQL5` 文件夹，直接覆盖到您 MT5 终端的**数据目录**下。

> **提示**: 在MT5终端，通过菜单 “文件” -> “打开数据文件夹” 即可快速定位。

### 第2步: 生成服务端密钥

进入 MT5 数据目录下的 `MQL5\Files\MT5RemoteBridgeAPI_Services_config\` 路径。您会找到 `generate_MT5RemoteBridgeAPI_keys.py` 脚本。

在命令行中运行它：
```shell
python generate_MT5RemoteBridgeAPI_keys.py
```

该脚本将生成并打印出专属于您的 **服务器公钥 (ServerPublicKey)** 和 **服务器私钥 (ServerSecretKey)**。请复制它们，下一步需要使用。

### 第3步: 配置服务端

在同一目录下 (`MQL5\Files\MT5RemoteBridgeAPI_Services_config\`)，使用文本编辑器打开 `MT5RemoteBridgeAPI_Services_config.json` 配置文件。

根据注释和您的需求，完成配置：

```json
{
  "HandshakePort": 5555,          // 握手端口 (明文，用于交换密钥)
  "CmdPort": 5556,                // 命令端口 (加密)
  "PubPort": 5557,                // 数据发布端口 (加密)
  "AuthKey": "your_strong_and_secret_auth_key", // 自定义认证密钥，客户端需保持一致
  "ServerPublicKey": "在此粘贴第2步生成的服务器公钥",
  "ServerSecretKey": "在此粘贴第2步生成的服务器私钥",
  "MagicNumber": 123456,          // 默认交易魔术手
  "Slippage": 10,                 // 默认滑点
  "TimerMs": 5,                   // 服务主循环间隔(毫秒)
  "HeartbeatSec": 5               // 心跳发送间隔(秒)
}
```

### 第4步: 在 MT5 中安装并启动服务

1. **重启 MT5 终端** 以加载新的程序文件。
2. 在 MT5“导航”窗口中，右键点击“服务”，选择“**添加服务**”。
3. 列表中找到并选择 `MT5RemoteBridgeAPI`。
4. **【关键步骤】** 在弹出的属性窗口中，切换到“**依赖关系**”选项卡，**必须勾选“允许DLL导入”**。这是 ZeroMQ 正常工作的前提。
5. 点击“确定”。服务会出现在“服务”列表中。
6. 右键点击新添加的 `MT5RemoteBridgeAPI` 服务，选择“**开始**”来启动。

服务启动后，您可以在 MT5 的“智能交易”日志中查看到详细的启动信息和状态。

## 运行客户端测试套件 🧪

客户端测试套件位于 `mt5_bridge_tester` 文件夹内，是验证部署是否成功的最佳方式。

### 第1步: 配置客户端

打开 `mt5_bridge_tester\config\` 目录下的 `MT5RemoteBridgeAPI_client_config.json` 文件。

确保其配置与服务端匹配：

```json
{
  "server_ip": "127.0.0.1",        // MT5服务端的IP地址
  "handshake_port": 5555,          // 必须与服务端的 HandshakePort 一致
  "auth_key": "your_strong_and_secret_auth_key", // 必须与服务端的 AuthKey 一致
  "request_timeout": 5000
}
```

### 第2步: 执行测试

在终端中，导航至 `mt5_bridge_tester` 文件夹，然后运行主测试脚本：

```shell
python run_all_tests.py
```

脚本将自动执行一系列测试，覆盖 API 的所有核心功能。您将看到格式化的实时结果输出。如果所有测试项均显示 `[PASSED]`，恭喜您，整个系统已成功部署并可投入使用！

## 开发者

* **ding9736**

## 许可证

本项目基于 [MIT License](https://opensource.org/licenses/MIT) 发布。
