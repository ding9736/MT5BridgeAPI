//+------------------------------------------------------------------+
//|    Core/Config.mqh                                               |
//+------------------------------------------------------------------+
#property strict
#ifndef CONFIG_MQH
#define CONFIG_MQH

#include "../Lib/JsonLib/JsonLib.mqh"
#include "ServiceConstants.mqh"


//--- Input Group: Configuration File Path Settings
input group          "Configuration File Path Settings"
input string         InpConfigPath          = "MT5RemoteBridgeAPI_Services_config";     // Configuration and log file directory
input string         InpConfigFilename      = "MT5RemoteBridgeAPI_Services_config";     // Configuration filename (without .json extension)

//--- Input Group: Logging Settings
input group          "Logging Settings"
input string         InpLogFilename         = "MT5RemoteBridgeAPI_Services_config.log"; // Log filename
input ENUM_LOG_LEVEL InpLogLevel            = LOG_LEVEL_INFO;                           // Log level (this type is from ServiceConstants.mqh)
input bool           InpLogToJournal        = true;                                     // Whether to output to the "Experts" log

//--- Input Group: Service Port Settings
input group          "Service Port Settings"
input int            InpHandshakePort       = 5555;                                     // (Unencrypted) REQ/REP handshake port
input int            InpCmdPort             = 5556;                                     // (Encrypted)   REQ/REP command port
input int            InpPubPort             = 5557;                                     // (Encrypted)   PUB/SUB publish port
input string         InpAuthKey             = "secret_key_change_me";                   // "Simple credential"

//--- Input Group: Security and Encryption Settings
input group          "Security and Encryption Settings"
input string         InpServerPublicKey     = "YOUR_SERVER_PUBLIC_KEY";                 // Server public key
input string         InpServerSecretKey     = "YOUR_SERVER_SECRET_KEY";                 // Server secret key (very important!)

//--- Input Group: Performance and Heartbeat Settings
input group          "Performance and Heartbeat Settings"
input int            InpTimerMs             = 100;                                      // Main loop timer interval (milliseconds)
input int            InpHeartbeatSec        = 5;                                        // Heartbeat signal sending interval (seconds)

//--- Input Group: Default Trading Parameters
input group          "Default Trading Parameters"
input ulong          InpMagicNumber         = 123456;                                   // Default trading magic number
input uint           InpDefaultSlippage     = 10;                                       // Default slippage

//+------------------------------------------------------------------+
//| CServiceConfig Class - Encapsulates all service configurations   |
//| (pure data container)                                            |
//+------------------------------------------------------------------+
class CServiceConfig
{
public:
   // Member variables for logging configuration
   string         ConfigPath;
   string         LogFilename;
   ENUM_LOG_LEVEL LogLevel; // This type is from ServiceConstants.mqh
   bool           LogToJournal;

   // Network configuration
   int            CmdPort, PubPort, HandshakePort;
   string         AuthKey;
   string         ServerPublicKey, ServerSecretKey;
   // Performance configuration
   int            TimerMs, HeartbeatSec;
   // Trading configuration
   ulong          MagicNumber;
   uint           Slippage;

public:
   // Stores error messages that occur during loading or validation
   string LastError;

private:
   // Loads configuration items from a JSON node and populates member variables
   void LoadFromJson(MQL5_Json::JsonNode &node)
   {
      CmdPort         = (int)node.Get("CmdPort").AsInt(CmdPort);
      PubPort         = (int)node.Get("PubPort").AsInt(PubPort);
      HandshakePort   = (int)node.Get("HandshakePort").AsInt(HandshakePort);
      AuthKey         = node.Get("AuthKey").AsString(AuthKey);
      ServerPublicKey = node.Get("ServerPublicKey").AsString(ServerPublicKey);
      ServerSecretKey = node.Get("ServerSecretKey").AsString(ServerSecretKey);
      HeartbeatSec    = (int)node.Get("HeartbeatSec").AsInt(HeartbeatSec);
      MagicNumber     = (ulong)node.Get("MagicNumber").AsInt(MagicNumber);
      Slippage        = (uint)node.Get("Slippage").AsInt(Slippage);
      // --- Final, correct fix ---
      // Abandon using the .Has() method as it can cause MQL5 compiler parsing errors.
      // Adopt a more robust "get first, then validate" pattern.
      MQL5_Json::JsonNode logLevelNode = node.Get("LogLevel");
      // Assuming .IsValid() is the standard method in JsonLib to check if a node is valid.
      // If JsonLib uses .IsNull(), it should be changed to !logLevelNode.IsNull()
      if(logLevelNode.IsValid())
      {
         int logLevelInt = (int)logLevelNode.AsInt( (int)LogLevel );
         LogLevel = (ENUM_LOG_LEVEL)logLevelInt;
      }
   }

public:
   // Loads default configuration from MQL5 input parameters into member variables
   void LoadDefaults()
   {
      // Load logging related configuration
      ConfigPath   = InpConfigPath;
      LogFilename  = InpLogFilename;
      LogLevel     = InpLogLevel;
      LogToJournal = InpLogToJournal;
      // Load all other configurations
      CmdPort         = InpCmdPort;
      PubPort         = InpPubPort;
      HandshakePort   = InpHandshakePort;
      AuthKey         = InpAuthKey;
      ServerPublicKey = InpServerPublicKey;
      ServerSecretKey = InpServerSecretKey;
      TimerMs         = InpTimerMs;
      HeartbeatSec    = InpHeartbeatSec;
      MagicNumber     = InpMagicNumber;
      Slippage        = InpDefaultSlippage;
      LastError       = ""; // Reset error message before starting to load
   }

   // Main loading function, responsible for the complete loading process and returning success/failure
   bool Load()
   {
      LoadDefaults();
      string config_path = ConfigPath + "\\" + InpConfigFilename + ".json";
      string json_content = "";
      int file_handle = FileOpen(config_path, FILE_READ | FILE_BIN);
      if(file_handle != INVALID_HANDLE)
      {
         ulong file_size = FileSize(file_handle);
         if(file_size > 0)
         {
            uchar bytes[];
            ArrayResize(bytes, (int)file_size);
            FileReadArray(file_handle, bytes);
            json_content = CharArrayToString(bytes, 0, -1, CP_UTF8);
         }
         FileClose(file_handle);
         if(StringLen(json_content) > 0)
         {
            MQL5_Json::JsonError error;
            MQL5_Json::JsonParseOptions options;
            MQL5_Json::JsonDocument doc = MQL5_Json::JsonParse(json_content, error, options);
            if(doc.IsValid())
            {
               LoadFromJson(doc.GetRoot());
            }
            else
            {
               LastError = "JSON file '" + config_path + "' is invalid: " + error.ToString();
            }
         }
      }
      // Perform sanity corrections on the final parameter values
      CmdPort       = MathMax(CmdPort, 1024);
      PubPort       = MathMax(PubPort, 1024);
      HandshakePort = MathMax(HandshakePort, 1024);
      TimerMs       = MathMax(TimerMs, 20);
      HeartbeatSec  = MathMax(HeartbeatSec, 1);
      return Validate(); // Validate at the end of the loading process
   }

   // Validation function, no longer logs, only returns bool and sets error message
   bool Validate()
   {
      if(CmdPort == PubPort || CmdPort == HandshakePort || PubPort == HandshakePort)
      {
         LastError = "Fatal Configuration Error: All ports (Cmd, Pub, Handshake) must be unique.";
         return false;
      }
      if(StringLen(AuthKey) < 8)
      {
         // This is a warning-level configuration and should not cause startup to fail
      }
      if(StringFind(ServerPublicKey, "KEY") != -1 || StringLen(ServerPublicKey) < 40)
      {
         LastError = "Fatal Configuration Error: ServerPublicKey is not configured correctly.";
         return false;
      }
      if(StringFind(ServerSecretKey, "KEY") != -1 || StringLen(ServerSecretKey) < 40)
      {
         LastError = "Fatal Configuration Error: ServerSecretKey is not configured correctly.";
         return false;
      }
      return true;
   }
};

// Declare the global configuration object, which will be defined in the main program file
extern CServiceConfig g_Config;

#endif // CONFIG_MQH
//+------------------------------------------------------------------+