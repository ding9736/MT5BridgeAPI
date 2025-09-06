//+------------------------------------------------------------------+
//|    Core/OrderHandlers.mqh                                        |
//+------------------------------------------------------------------+
#property strict
#ifndef ORDER_HANDLERS_MQH
#define ORDER_HANDLERS_MQH

#include "ServiceState.mqh"

namespace OrderHandlers
{
// Local definition to avoid circular include dependency
void SendOrderErrorResponse(CServiceState &state, const MqlTradeResult &result, const string default_msg, const string py_id, ulong ticket)
{
   MQL5_Json::JsonDocument dataDoc = MQL5_Json::JsonNewObject();
   MQL5_Json::JsonNode dataNode = dataDoc.GetRoot();
   dataNode.Set(KEY_TRADE_RETCODE, (long)result.retcode);
   dataNode.Set(KEY_RETCODE_MSG, result.comment);
   if(py_id != "") dataNode.Set(KEY_PYTHON_ID, py_id);
   if(ticket > 0) dataNode.Set(KEY_TICKET, (long)ticket);
   string final_message = default_msg + " Reason: " + result.comment;
   state.SendErrorResponseWithData(final_message, SRV_ERR_TRADE_EXECUTION, dataNode);
}


//--- Handle request to get pending orders ---
void HandleGetPendingOrders(MQL5_Json::JsonDocument &doc, CServiceState &state)
{
   MQL5_Json::JsonNode root = doc.GetRoot();
   const string py_id = root.Get(KEY_PYTHON_ID).AsString("");
   const string filter_symbol = root.Get(KEY_SYMBOL).AsString("");
   MQL5_Json::JsonDocument ordersDoc = MQL5_Json::JsonNewArray();
   MQL5_Json::JsonNode ordersArray = ordersDoc.GetRoot();
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;
      string symbol = OrderGetString(ORDER_SYMBOL);
      if(filter_symbol != "" && symbol != filter_symbol) continue;
      MQL5_Json::JsonNode orderNode = ordersArray.AddObject();
      orderNode.Set(KEY_TICKET, (long)ticket);
      orderNode.Set(KEY_SYMBOL, symbol);
      orderNode.Set(KEY_VOLUME, OrderGetDouble(ORDER_VOLUME_CURRENT));
      orderNode.Set(KEY_PRICE, OrderGetDouble(ORDER_PRICE_OPEN));
      orderNode.Set(KEY_SL, OrderGetDouble(ORDER_SL));
      orderNode.Set(KEY_TP, OrderGetDouble(ORDER_TP));
      orderNode.Set("magic", (long)OrderGetInteger(ORDER_MAGIC));
      orderNode.Set(KEY_TYPE, (long)OrderGetInteger(ORDER_TYPE)); // BUY_LIMIT, etc.
   }
   state.SendSuccessResponse("Pending order list retrieved successfully.", ordersArray, py_id);
}

//--- Handle request to modify a pending order (Price, SL, TP, Expiration) ---
void HandleModifyOrder(MQL5_Json::JsonDocument &doc, CServiceState &state)
{
   MQL5_Json::JsonNode root = doc.GetRoot();
   const string py_id = root.Get(KEY_PYTHON_ID).AsString("");
   const ulong ticket = (ulong)root.Get(KEY_TICKET).AsInt(0);
   if(ticket == 0)
   {
      state.SendErrorResponse("Bad request: 'ticket' must be a valid positive integer.", SRV_ERR_BAD_REQUEST, py_id);
      return;
   }
   if(!OrderSelect(ticket))
   {
      string error_message = "Resource not found: Could not find pending order with ticket " + (string)ticket;
      state.SendErrorResponse(error_message, SRV_ERR_NOT_FOUND, py_id, ticket);
      return;
   }
   MqlTradeRequest request;
   MqlTradeResult  result;
   ZeroMemory(request);
   ZeroMemory(result);
   request.action       = TRADE_ACTION_MODIFY;
   request.order        = ticket;
// Use incoming values, if not provided, use the order's current values (implements partial update)
   request.price        = root.Get(KEY_PRICE).IsValid() ? root.Get(KEY_PRICE).AsDouble() : OrderGetDouble(ORDER_PRICE_OPEN);
   request.sl           = root.Get(KEY_SL).IsValid() ? root.Get(KEY_SL).AsDouble() : OrderGetDouble(ORDER_SL);
   request.tp           = root.Get(KEY_TP).IsValid() ? root.Get(KEY_TP).AsDouble() : OrderGetDouble(ORDER_TP);
   request.expiration = root.Get(KEY_EXPIRATION).IsValid() ? (datetime)root.Get(KEY_EXPIRATION).AsInt() : (datetime)OrderGetInteger(ORDER_TIME_EXPIRATION);
   if(!OrderSend(request, result))
   {
      SendOrderErrorResponse(state, result, "OrderSend() API call failed.", py_id, ticket);
      return;
   }
   if(result.retcode == TRADE_RETCODE_DONE)
   {
      MQL5_Json::JsonDocument dataDoc;
      // [FIX] Create string variable first before passing
      string success_message = "Request to modify pending order " + (string)ticket + " was successful.";
      state.SendSuccessResponse(success_message, dataDoc.GetRoot(), py_id);
   }
   else
   {
      SendOrderErrorResponse(state, result, "Failed to modify pending order.", py_id, ticket);
   }
}

//--- Handle request to cancel a pending order ---
void HandleCancelOrder(MQL5_Json::JsonDocument &doc, CServiceState &state)
{
   MQL5_Json::JsonNode root = doc.GetRoot();
   const string py_id = root.Get(KEY_PYTHON_ID).AsString("");
   const ulong ticket = (ulong)root.Get(KEY_TICKET).AsInt(0);
   if(ticket == 0)
   {
      state.SendErrorResponse("Bad request: 'ticket' must be a valid positive integer.", SRV_ERR_BAD_REQUEST, py_id);
      return;
   }
   MqlTradeRequest request;
   MqlTradeResult  result;
   ZeroMemory(request);
   ZeroMemory(result);
   request.action = TRADE_ACTION_REMOVE;
   request.order  = ticket;
   if(!OrderSend(request, result))
   {
      SendOrderErrorResponse(state, result, "OrderSend() API call failed.", py_id, ticket);
      return;
   }
   if(result.retcode == TRADE_RETCODE_DONE)
   {
      MQL5_Json::JsonDocument dataDoc;
      string success_message = "Request to cancel pending order " + (string)ticket + " was successful.";
      state.SendSuccessResponse(success_message, dataDoc.GetRoot(), py_id);
   }
   else
   {
      SendOrderErrorResponse(state, result, "Failed to cancel pending order.", py_id, ticket);
   }
}

//+------------------------------------------------------------------+
//|  Handle request to cancel all pending orders                     |
//+------------------------------------------------------------------+
void HandleCancelAllPendingOrders(MQL5_Json::JsonDocument &doc, CServiceState &state)
{
   const string py_id = doc.GetRoot().Get(KEY_PYTHON_ID).AsString("");
   int cancelled_count = 0;
   int failed_count = 0;
   MqlTradeRequest request;
   MqlTradeResult  result;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket > 0)
      {
         ZeroMemory(request);
         ZeroMemory(result);
         request.action = TRADE_ACTION_REMOVE;
         request.order  = ticket;
         if(OrderSend(request, result) && result.retcode == TRADE_RETCODE_DONE)
         {
            cancelled_count++;
         }
         else
         {
            failed_count++;
         }
      }
   }
   MQL5_Json::JsonDocument dataDoc = MQL5_Json::JsonNewObject();
   MQL5_Json::JsonNode dataNode = dataDoc.GetRoot();
   dataNode.Set("cancelled_count", (long)cancelled_count);
   dataNode.Set("failed_count", (long)failed_count);
   state.SendSuccessResponse("Request to cancel all pending orders has been executed.", dataNode, py_id);
}

//+------------------------------------------------------------------+
//| [New Feature] Handle request to cancel all pending orders        |
//| for a specific symbol                                            |
//+------------------------------------------------------------------+
void HandleCancelSymbolPendingOrders(MQL5_Json::JsonDocument &doc, CServiceState &state)
{
   MQL5_Json::JsonNode root = doc.GetRoot();
   const string py_id = root.Get(KEY_PYTHON_ID).AsString("");
   const string symbol_to_cancel = root.Get(KEY_SYMBOL).AsString("");
   if(symbol_to_cancel == "")
   {
      state.SendErrorResponse("Bad request: 'symbol' parameter cannot be empty.", SRV_ERR_BAD_REQUEST, py_id);
      return;
   }
   int cancelled_count = 0;
   int failed_count = 0;
   MqlTradeRequest request;
   MqlTradeResult  result;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket > 0)
      {
         if(OrderGetString(ORDER_SYMBOL) == symbol_to_cancel)
         {
            ZeroMemory(request);
            ZeroMemory(result);
            request.action = TRADE_ACTION_REMOVE;
            request.order  = ticket;
            if(OrderSend(request, result) && result.retcode == TRADE_RETCODE_DONE)
            {
               cancelled_count++;
            }
            else
            {
               failed_count++;
            }
         }
      }
   }
   MQL5_Json::JsonDocument dataDoc = MQL5_Json::JsonNewObject();
   MQL5_Json::JsonNode dataNode = dataDoc.GetRoot();
   dataNode.Set("cancelled_count", (long)cancelled_count);
   dataNode.Set("failed_count", (long)failed_count);
   dataNode.Set("symbol", symbol_to_cancel);
   state.SendSuccessResponse("Request to cancel pending orders for the specified symbol has been executed.", dataNode, py_id);
}


}
#endif // ORDER_HANDLERS_MQH
//+------------------------------------------------------------------+
