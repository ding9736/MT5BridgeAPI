//+------------------------------------------------------------------+
//|    Core/AdminHandlers.mqh                                        |
//+------------------------------------------------------------------+
#property strict
#ifndef ADMIN_HANDLERS_MQH
#define ADMIN_HANDLERS_MQH

#include "ServiceState.mqh"

namespace AdminHandlers
{

//--- Handles the request for hot-reloading the configuration ---
void HandleReloadConfig(MQL5_Json::JsonDocument &doc, CServiceState &state)
{
   const string py_id = doc.GetRoot().Get(KEY_PYTHON_ID).AsString("");
   state.ReloadConfiguration();
   MQL5_Json::JsonDocument dataDoc;
   state.SendSuccessResponse("Configuration parameters hot-reloaded successfully.", dataDoc.GetRoot(), py_id);
}

}
#endif // ADMIN_HANDLERS_MQH
//+------------------------------------------------------------------+