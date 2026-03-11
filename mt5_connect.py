# Connection Tester

# This file is for debugging.
#It checks: Is MT5 running? Is account logged in? Balance available?
#  Used before running bot.


import MetaTrader5 as mt5

# initialize MT5
if not mt5.initialize():
    print("❌ MT5 Initialize Failed:", mt5.last_error())
    quit()

# account info
account_info = mt5.account_info()

if account_info is None:
    print("❌ Not logged into MT5")
else:
    print("✅ Connected to MT5")
    print("Login:", account_info.login)
    print("Server:", account_info.server)
    print("Balance:", account_info.balance)

mt5.shutdown()
