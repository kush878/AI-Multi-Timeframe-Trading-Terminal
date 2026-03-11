# Broker Execution Layer

###This is the bridge between Python and Broker


# It handles:
#Login,Send orders , Close orders Without this file → Streamlit cannot trade.
# Only this file needs modification → whole project survives.

try:
    import MetaTrader5 as mt5
except:
    mt5 = None

from mt5_trade import send_order

# ================= CONNECT MT5 =================
def connect_mt5():

    # Check if MT5 is available (Cloud will not have it)
    if mt5 is None:
        return False, "MT5 not available in cloud environment"

    if mt5.initialize():
        account_info = mt5.account_info()

        if account_info is not None:
            return True, f"Connected to MT5 | Account: {account_info.login}"
        else:
            return False, "Connected but failed to get account info"

    else:
        return False, f"Initialization failed: {mt5.last_error()}"

# ================= OPEN TRADE WITH SL / TP =================
def open_trade(symbol, direction, sl_percent=5, tp_percent=15):

    lot = 0.01

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return False, "Symbol tick not available"

    price = tick.ask if direction == "BUY" else tick.bid

    account_info = mt5.account_info()
    if account_info is None:
        return False, "Account info not available"

    balance = account_info.balance

    # Calculate risk and reward amount
    risk_amount = balance * (sl_percent / 100)
    reward_amount = balance * (tp_percent / 100)

    # For Gold scaling (adjust if needed later)
    scale_factor = 1000

    if direction == "BUY":
        sl_price = price - (risk_amount / scale_factor)
        tp_price = price + (reward_amount / scale_factor)
    else:
        sl_price = price + (risk_amount / scale_factor)
        tp_price = price - (reward_amount / scale_factor)

    # Round properly to symbol digits
    symbol_info = mt5.symbol_info(symbol)
    digits = symbol_info.digits if symbol_info else 2

    sl_price = round(sl_price, digits)
    tp_price = round(tp_price, digits)

    success, message = send_order(symbol, direction, lot, sl_price, tp_price)

    return success, message

# ================= CLOSE ALL POSITIONS =================
def close_all(symbol):

    positions = mt5.positions_get(symbol=symbol)

    if positions is None or len(positions) == 0:
        return False, "No positions to close"

    for position in positions:

        ticket = position.ticket
        volume = position.volume
        order_type = mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if position.type == 0 else mt5.symbol_info_tick(symbol).ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 123456,
            "comment": "Auto Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return False, f"Failed to close position: {result.comment}"

    return True, "All positions closed"