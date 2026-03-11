# Filling mode finder 


# This is VERY important in real trading.
# Different brokers allow different execution types.
# this file tries: 
# FOK
# IOC
# RETURN
# And finds which works.

# This solves the famous error: Unsupported filling mode / Trade rejected

import MetaTrader5 as mt5

# ---------------- CONNECT ----------------
def connect_mt5():
    if not mt5.initialize():
        return False, mt5.last_error()
    return True, "Connected"

# ---------------- GET PRICE ----------------
def get_price(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None
    return tick.ask, tick.bid

# ---------------- OPEN TRADE ----------------
def open_trade(symbol, signal, lot=0.01):

    ask, bid = get_price(symbol)
    if ask is None:
        return "Price not available"

    price = ask if signal=="BUY" else bid

    # Detect filling mode automatically
    info = mt5.symbol_info(symbol)
    filling = info.filling_mode

    order_type = mt5.ORDER_TYPE_BUY if signal=="BUY" else mt5.ORDER_TYPE_SELL

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": 999999,
        "comment": "AI Auto Trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }

    result = mt5.order_send(request)

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        return f"Trade Opened {signal} @ {price}"
    else:
        return f"Failed: {result.comment}"

# ---------------- CLOSE TRADE ----------------
def close_all(symbol):

    positions = mt5.positions_get(symbol=symbol)
    if positions is None or len(positions)==0:
        return "No open positions"

    for pos in positions:
        price = mt5.symbol_info_tick(symbol).bid if pos.type==0 else mt5.symbol_info_tick(symbol).ask

        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": pos.volume,
            "type": mt5.ORDER_TYPE_SELL if pos.type==0 else mt5.ORDER_TYPE_BUY,
            "position": pos.ticket,
            "price": price,
            "deviation": 20,
            "magic": 999999,
            "comment": "AI Close Trade",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.symbol_info(symbol).filling_mode,
        }

        mt5.order_send(close_request)

    return "Positions Closed"
