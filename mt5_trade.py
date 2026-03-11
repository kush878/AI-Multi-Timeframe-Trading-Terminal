## Advanced Trade Engine


# More advanced trading functions: Get price , Open trade , Close all trades

# This file is a more flexible executor.


import MetaTrader5 as mt5

def send_order(symbol, order_type, lot, sl_price=None, tp_price=None):

    if not mt5.symbol_select(symbol, True):
        return False, "Symbol not available"

    price = mt5.symbol_info_tick(symbol).ask if order_type == "BUY" else mt5.symbol_info_tick(symbol).bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl_price,
        "tp": tp_price,
        "deviation": 20,
        "magic": 123456,
        "comment": "AI Trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return False, result.comment

    return True, "Trade Executed"