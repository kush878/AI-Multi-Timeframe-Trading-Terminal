## Broker Symbol Inspector

# Checks broker configuration for a symbol: EURUSD filling mode
#Used to debug why trade fails.

import MetaTrader5 as mt5

mt5.initialize()

symbol = "EURUSD"
info = mt5.symbol_info(symbol)

print("Filling Mode:", info.filling_mode)

mt5.shutdown()
