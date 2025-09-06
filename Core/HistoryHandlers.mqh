//+------------------------------------------------------------------+
//|    Core/HistoryHandlers.mqh                                      |
//+------------------------------------------------------------------+
#property strict
#ifndef HISTORY_HANDLERS_MQH
#define HISTORY_HANDLERS_MQH

#include "ServiceState.mqh"

namespace HistoryHandlers
{
//+------------------------------------------------------------------+
//| Convert string timeframe to ENUM_TIMEFRAMES                      |
//+------------------------------------------------------------------+
ENUM_TIMEFRAMES StringToTimeframe(const string tf_str)
{
   if(tf_str == "M1") return PERIOD_M1;
   if(tf_str == "M2") return PERIOD_M2;
   if(tf_str == "M3") return PERIOD_M3;
   if(tf_str == "M4") return PERIOD_M4;
   if(tf_str == "M5") return PERIOD_M5;
   if(tf_str == "M6") return PERIOD_M6;
   if(tf_str == "M10") return PERIOD_M10;
   if(tf_str == "M12") return PERIOD_M12;
   if(tf_str == "M15") return PERIOD_M15;
   if(tf_str == "M20") return PERIOD_M20;
   if(tf_str == "M30") return PERIOD_M30;
   if(tf_str == "H1") return PERIOD_H1;
   if(tf_str == "H2") return PERIOD_H2;
   if(tf_str == "H3") return PERIOD_H3;
   if(tf_str == "H4") return PERIOD_H4;
   if(tf_str == "H6") return PERIOD_H6;
   if(tf_str == "H8") return PERIOD_H8;
   if(tf_str == "H12") return PERIOD_H12;
   if(tf_str == "D1") return PERIOD_D1;
   if(tf_str == "W1") return PERIOD_W1;
   if(tf_str == "MN1") return PERIOD_MN1;
   return PERIOD_CURRENT; // Invalid or not provided
}

//+------------------------------------------------------------------+
//| Handle request to get historical bar data                        |
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| Handle request to get historical bar data (V2.0 - Enhanced)      |
//| [!] Intelligently handles time range and position queries,       |
//| with backward compatibility.                                     |
//+------------------------------------------------------------------+
void HandleGetBars(MQL5_Json::JsonDocument &doc, CServiceState &state)
{
   MQL5_Json::JsonNode root = doc.GetRoot();
   const string py_id = root.Get(KEY_PYTHON_ID).AsString("");
   const string symbol = root.Get(KEY_SYMBOL).AsString("");
   const string tf_str = root.Get(KEY_TIMEFRAME).AsString("");
// [New] Added parsing for time range parameters
   const long start_time = root.Get(KEY_START_TIME).AsInt(0);
   const long end_time = root.Get(KEY_END_TIME).AsInt(0);
// [Old] Retained parsing for position parameters for backward compatibility
   const uint start_pos = (uint)root.Get(KEY_START_POS).AsInt(0);
   const uint count = (uint)root.Get(KEY_COUNT).AsInt(100);
// --- 1. Parameter Validation ---
   if(symbol == "" || tf_str == "")
   {
      state.SendErrorResponse("Bad request: 'symbol' and 'timeframe' cannot be empty", SRV_ERR_BAD_REQUEST, py_id);
      return;
   }
// --- 2. Convert Timeframe ---
   ENUM_TIMEFRAMES timeframe = StringToTimeframe(tf_str);
   if(timeframe == PERIOD_CURRENT)
   {
      string error_message = "Bad request: Invalid 'timeframe' value: " + tf_str;
      state.SendErrorResponse(error_message, SRV_ERR_BAD_REQUEST, py_id, 0, symbol);
      return;
   }
// --- 3. Get Bar Data (Smart Switching Mode) ---
   MqlRates rates[];
   int rates_copied = 0;
// [New] Priority Mode: If start_time is provided, use a time-based query
   if(start_time > 0)
   {
      // If end_time is not provided, default to the current time
      datetime effective_end_time = (end_time > 0) ? (datetime)end_time : TimeCurrent();
      rates_copied = CopyRates(symbol, timeframe, (datetime)start_time, effective_end_time, rates);
   }
// [Old] Fallback Mode: If start_time is not provided, use a position-based query
   else
   {
      rates_copied = CopyRates(symbol, timeframe, start_pos, count, rates);
   }
// --- 4. Process a Get Result ---
   if(rates_copied == -1) // Explicit error
   {
      state.SendErrorResponse("Internal error: An error occurred while getting bar data (CopyRates returned -1)", SRV_ERR_INTERNAL, py_id, 0, symbol);
      return;
   }
   if(rates_copied == 0) // No error, but also no data
   {
      // Return a successful response, but with data as an empty array, which is more standard API behavior
      MQL5_Json::JsonDocument emptyDataDoc = MQL5_Json::JsonNewArray();
      state.SendSuccessResponse("Successfully retrieved 0 historical bars.", emptyDataDoc.GetRoot(), py_id);
      return;
   }
// --- 5. Build Response Data (This part of the logic is consistent with your original) ---
   MQL5_Json::JsonDocument dataDoc = MQL5_Json::JsonNewArray();
   if(!dataDoc.IsValid())
   {
      state.SendErrorResponse("Internal error: Could not create response data", SRV_ERR_INTERNAL, py_id, 0, symbol);
      return;
   }
   MQL5_Json::JsonNode barsArray = dataDoc.GetRoot();
   for(int i = 0; i < rates_copied; i++)
   {
      MQL5_Json::JsonNode barNode = barsArray.AddObject();
      barNode.Set("time", (long)rates[i].time);
      barNode.Set("open", rates[i].open);
      barNode.Set("high", rates[i].high);
      barNode.Set("low", rates[i].low);
      barNode.Set("close", rates[i].close);
      barNode.Set("tick_volume", (long)rates[i].tick_volume);
      barNode.Set("real_volume", (long)rates[i].real_volume);
      barNode.Set("spread", (long)rates[i].spread);
   }
   state.SendSuccessResponse("Historical bars retrieved successfully", barsArray, py_id);
}

//+------------------------------------------------------------------+
//| Handle request to get historical deal records                    |
//+------------------------------------------------------------------+
void HandleGetHistoryDeals(MQL5_Json::JsonDocument &doc, CServiceState &state)
{
   MQL5_Json::JsonNode root = doc.GetRoot();
   const string py_id = root.Get(KEY_PYTHON_ID).AsString("");
   const long start_time = root.Get(KEY_START_TIME).AsInt(0);
   const long end_time = root.Get(KEY_END_TIME).AsInt(TimeCurrent());
// Select history time range
   if(!HistorySelect((datetime)start_time, (datetime)end_time))
   {
      state.SendErrorResponse("Internal error: HistorySelect failed",
                              SRV_ERR_INTERNAL, py_id);
      return;
   }
// Build response data
   MQL5_Json::JsonDocument dataDoc = MQL5_Json::JsonNewArray();
   if(!dataDoc.IsValid())
   {
      state.SendErrorResponse("Internal error: Could not create response data",
                              SRV_ERR_INTERNAL, py_id);
      return;
   }
   MQL5_Json::JsonNode dealsArray = dataDoc.GetRoot();
   int total_deals = HistoryDealsTotal();
   for(int i = 0; i < total_deals; i++)
   {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket > 0)
      {
         MQL5_Json::JsonNode dealNode = dealsArray.AddObject();
         // Basic Information
         dealNode.Set(KEY_TICKET, (long)ticket);
         dealNode.Set("order", (long)HistoryDealGetInteger(ticket, DEAL_ORDER));
         dealNode.Set("time", (long)HistoryDealGetInteger(ticket, DEAL_TIME));
         dealNode.Set(KEY_TYPE, (long)HistoryDealGetInteger(ticket, DEAL_TYPE));
         // Trade Details
         dealNode.Set(KEY_SYMBOL, HistoryDealGetString(ticket, DEAL_SYMBOL));
         dealNode.Set(KEY_VOLUME, HistoryDealGetDouble(ticket, DEAL_VOLUME));
         dealNode.Set(KEY_PRICE, HistoryDealGetDouble(ticket, DEAL_PRICE));
         // Financial Information
         dealNode.Set("profit", HistoryDealGetDouble(ticket, DEAL_PROFIT));
         dealNode.Set("fee", HistoryDealGetDouble(ticket, DEAL_FEE));
         dealNode.Set("swap", HistoryDealGetDouble(ticket, DEAL_SWAP));
         // Other Information
         dealNode.Set("magic", (long)HistoryDealGetInteger(ticket, DEAL_MAGIC));
         dealNode.Set("comment", HistoryDealGetString(ticket, DEAL_COMMENT));
      }
   }
   state.SendSuccessResponse("Historical deal records retrieved successfully", dealsArray, py_id);
}

} // namespace HistoryHandlers

#endif // HISTORY_HANDLERS_MQH
//+------------------------------------------------------------------+