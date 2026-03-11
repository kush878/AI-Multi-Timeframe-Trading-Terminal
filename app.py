import streamlit as st
from tradingview_ta import TA_Handler, Interval
import time
import requests
import pandas as pd
import plotly.graph_objects as go

from mt5_helper import connect_mt5, open_trade, close_all

st.warning("⚠️ MT5 trading only works when running locally.")

# ================= PAGE =================
st.set_page_config(page_title="AI Trading Terminal", layout="wide")

st.markdown("""
<style>
.stApp {
    background-color: #0b0f19;
}
h1 {
    color:#e6edf3;
}
h2,h3,h4 {
    color:#9aa4b2;
}
[data-testid="stMetric"] {
    background-color:#111827;
    border-radius:12px;
    padding:10px;
}
</style>
""", unsafe_allow_html=True)

st.title("🧠 AI Multi-Timeframe Trading Terminal")

# ================= SESSION =================
if "mt5_connected" not in st.session_state:
    st.session_state.mt5_connected = False
if "balance" not in st.session_state:
    st.session_state.balance = 10000.0
if "position" not in st.session_state:
    st.session_state.position = None
if "trades" not in st.session_state:
    st.session_state.trades = []
if "signals" not in st.session_state:
    st.session_state.signals = ("WAIT","WAIT","WAIT")
if "last_auto_signal" not in st.session_state:
    st.session_state.last_auto_signal = "WAIT"

# ================= MT5 CONNECTION =================
st.subheader("🔌 MetaTrader5 Connection")

colA, colB = st.columns(2)

with colA:
    if st.button("Connect MT5"):
        status, msg = connect_mt5()
        if status:
            st.session_state.mt5_connected = True
            st.success(msg)
        else:
            st.error(msg)

with colB:
    if st.session_state.mt5_connected:
        st.success("Status: Connected")
    else:
        st.warning("Status: Not Connected")

# ================= RISK =================
st.subheader("⚙ Risk Management Settings")

col_r1, col_r2 = st.columns(2)

with col_r1:
    stop_loss_percent = st.number_input("Stop Loss %", min_value=0.1, value=5.0)

with col_r2:
    take_profit_percent = st.number_input("Take Profit %", min_value=0.1, value=15.0)

# ================= ASSET =================
col1,col2,col3 = st.columns(3)

with col1:
    asset = st.selectbox("Asset",["Bitcoin","Gold"])

if asset=="Bitcoin":
    symbol="BTCUSDT"; exchange="BINANCE"; screener="crypto"; chart_symbol="BTC-USD"
else:
    symbol="GOLD"; exchange="TVC"; screener="cfd"; chart_symbol="GC=F"

timeframe_map={
"1 Minute":Interval.INTERVAL_1_MINUTE,
"5 Minutes":Interval.INTERVAL_5_MINUTES,
"15 Minutes":Interval.INTERVAL_15_MINUTES
}

with col2:
    tf1=st.selectbox("Timeframe 1",list(timeframe_map.keys()))
with col3:
    tf2=st.selectbox("Timeframe 2",list(timeframe_map.keys()))

# ================= SIGNAL BOX =================
def signal_box(label,value):

    if value=="BUY":
        color="#00ff9c"
        bg="#0f2a22"
    elif value=="SELL":
        color="#ff4d4f"
        bg="#2a0f12"
    else:
        color="#ffd166"
        bg="#2a260f"

    st.markdown(f"""
    <div style="
        padding:25px;
        border-radius:15px;
        background:{bg};
        text-align:center;
        border:1px solid rgba(255,255,255,0.08);
        box-shadow:0 0 15px rgba(0,0,0,0.4);
    ">
        <h4 style="color:#9aa4b2">{label}</h4>
        <h1 style="color:{color};font-weight:700">{value}</h1>
    </div>
    """,unsafe_allow_html=True)

# ================= ANALYZE =================
@st.cache_data(ttl=10)
def analyze(interval):
    try:
        handler = TA_Handler(
            symbol=symbol,
            exchange=exchange,
            screener=screener,
            interval=interval
        )

        r = handler.get_analysis()

        ema10 = r.indicators["EMA10"]
        ema20 = r.indicators["EMA20"]
        rsi = r.indicators["RSI"]

        if ema10 > ema20 and rsi > 50:
            return "BUY"
        elif ema10 < ema20 and rsi < 50:
            return "SELL"
        else:
            return "WAIT"

    except:
        return "WAIT"

# ================= PRICE DATA =================
def get_data():
    try:
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{chart_symbol}?range=1d&interval=5m"
        data=requests.get(url,headers={"User-Agent":"Mozilla/5.0"}).json()
        if not data["chart"]["result"]:
            return pd.DataFrame()
        r=data["chart"]["result"][0]

        df=pd.DataFrame({
            "Time":pd.to_datetime(r["timestamp"],unit="s"),
            "Close":r["indicators"]["quote"][0]["close"]
        }).dropna()

        delta=df["Close"].diff()
        gain=delta.clip(lower=0)
        loss=-delta.clip(upper=0)
        rs=gain.rolling(14).mean()/loss.rolling(14).mean()
        df["RSI"]=100-(100/(1+rs))

        ema12=df["Close"].ewm(span=12,adjust=False).mean()
        ema26=df["Close"].ewm(span=26,adjust=False).mean()
        df["MACD"]=ema12-ema26
        df["Signal"]=df["MACD"].ewm(span=9,adjust=False).mean()

        return df
    except:
        return pd.DataFrame()

# ================= TRADE TABLE =================
def show_trade_table(limit):
    if st.session_state.trades:
        df=pd.DataFrame(
            st.session_state.trades,
            columns=["Time","Asset","Type","Entry","SL","TP","Exit","PnL","Balance"]
        )
        st.dataframe(df.tail(limit),use_container_width=True)
    else:
        st.info("No trades yet")

# ================= MT5 AUTO TRADE =================
if st.session_state.mt5_connected:
    if asset=="Bitcoin":
        st.info("Auto trading disabled for Bitcoin (no BTC symbol in this demo account)")
    else:
        try:
            s1,s2,final_signal=st.session_state.signals
            last_signal=st.session_state.last_auto_signal

            if final_signal!=last_signal and final_signal in ["BUY","SELL"]:
                close_all("XAUUSD")
                open_trade("XAUUSD",final_signal,stop_loss_percent,take_profit_percent)
                st.session_state.last_auto_signal=final_signal
        except:
            pass

# ================= TABS =================
tab1,tab2,tab3,tab4=st.tabs(["📡 Signals","📊 Charts","📜 History","📈 Performance"])

# ================= SIGNAL TAB =================
with tab1:

    if st.button("Analyze Market"):
        s1=analyze(timeframe_map[tf1])
        time.sleep(1)
        s2=analyze(timeframe_map[tf2])
        final=s1 if s1==s2 else "WAIT"
        st.session_state.signals=(s1,s2,final)

    s1,s2,final=st.session_state.signals

    c1,c2,c3=st.columns(3)
    with c1: signal_box(tf1,s1)
    with c2: signal_box(tf2,s2)
    with c3: signal_box("Final Decision",final)

    # ================= ADDED FEATURE : ALGORITHM MONITOR =================
    st.subheader("📡 Algorithm Monitor")

    try:
        handler = TA_Handler(
            symbol=symbol,
            exchange=exchange,
            screener=screener,
            interval=timeframe_map[tf1]
        )

        analysis = handler.get_analysis()

        ema10 = analysis.indicators["EMA10"]
        ema20 = analysis.indicators["EMA20"]
        rsi = analysis.indicators["RSI"]

        m1,m2,m3 = st.columns(3)

        m1.metric("EMA10", round(ema10,2))
        m2.metric("EMA20", round(ema20,2))
        m3.metric("RSI", round(rsi,2))

        st.caption("Strategy Logic: EMA10 > EMA20 & RSI > 50 = BUY | EMA10 < EMA20 & RSI < 50 = SELL")

    except:
        st.warning("Indicator data unavailable")

    df=get_data()
    if df.empty:
        st.stop()

    price=df["Close"].iloc[-1]

    st.subheader("💼 Trade Panel")

    if st.session_state.position is None:
        if final in ["BUY","SELL"]:
            if st.button("Take Trade"):

                entry_price=price

                if final=="BUY":
                    sl_price=round(entry_price*(1-stop_loss_percent/100),2)
                    tp_price=round(entry_price*(1+take_profit_percent/100),2)
                else:
                    sl_price=round(entry_price*(1+stop_loss_percent/100),2)
                    tp_price=round(entry_price*(1-take_profit_percent/100),2)

                st.session_state.position={
                    "type":final,
                    "entry":entry_price,
                    "sl":sl_price,
                    "tp":tp_price,
                    "time":pd.Timestamp.now()
                }

                st.success("Trade Opened")

    else:
        pos=st.session_state.position
        pnl=price-pos["entry"] if pos["type"]=="BUY" else pos["entry"]-price

        risk_limit = round(st.session_state.balance*(stop_loss_percent/100),2)
        reward_target = round(st.session_state.balance*(take_profit_percent/100),2)

        st.write(f"Current PnL: {round(pnl,2)}")
        st.write(f"Stop Loss Limit ({stop_loss_percent}%): -{risk_limit}")
        st.write(f"Take Profit Target ({take_profit_percent}%): {reward_target}")

        if (pos["type"]=="BUY" and (price<=pos["sl"] or price>=pos["tp"])) or \
           (pos["type"]=="SELL" and (price>=pos["sl"] or price<=pos["tp"])):

            st.session_state.balance+=pnl
            st.session_state.trades.append([
                pos["time"],asset,pos["type"],
                round(pos["entry"],2),pos["sl"],pos["tp"],
                round(price,2),round(pnl,2),
                round(st.session_state.balance,2)
            ])
            st.session_state.position=None
            if pnl > 0:
                st.success("Take Profit Hit 🚀")
            else:
                st.error("Stop Loss Hit ❌")

        if st.button("Close Trade"):
            st.session_state.balance+=pnl
            st.session_state.trades.append([
                pos["time"],asset,pos["type"],
                round(pos["entry"],2),pos["sl"],pos["tp"],
                round(price,2),round(pnl,2),
                round(st.session_state.balance,2)
            ])
            st.session_state.position=None
            st.success("Trade Closed Manually")

    st.metric("Account Balance",round(st.session_state.balance,2))

    st.subheader("Recent Trades")
    show_trade_table(5)

# ================= CHART TAB =================
with tab2:
    df=get_data()
    if not df.empty:

        st.subheader("📈 Price Chart (Candlestick)")

        try:
            url=f"https://query1.finance.yahoo.com/v8/finance/chart/{chart_symbol}?range=1d&interval=5m"
            raw=requests.get(url,headers={"User-Agent":"Mozilla/5.0"}).json()
            r=raw["chart"]["result"][0]

            ohlc_df=pd.DataFrame({
                "Time":pd.to_datetime(r["timestamp"],unit="s"),
                "Open":r["indicators"]["quote"][0]["open"],
                "High":r["indicators"]["quote"][0]["high"],
                "Low":r["indicators"]["quote"][0]["low"],
                "Close":r["indicators"]["quote"][0]["close"]
            }).dropna()

            fig1=go.Figure()
            
            fig1.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0b0f19",
                plot_bgcolor="#0b0f19",
                font=dict(color="#e6edf3"),
                height=600,
                
                xaxis=dict(
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.15)",
                    griddash="dot",
                    gridwidth=1
                    ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.15)",
                    griddash="dot",
                    gridwidth=1
                    ),
                
                xaxis_rangeslider_visible=False
)

            fig1.add_trace(go.Candlestick(
                x=ohlc_df["Time"],
                open=ohlc_df["Open"],
                high=ohlc_df["High"],
                low=ohlc_df["Low"],
                close=ohlc_df["Close"],
                increasing_line_color="#00ff9c",
                increasing_fillcolor="#00ff9c",
                decreasing_line_color="#ff4d4f",
                decreasing_fillcolor="#ff4d4f",
            ))

            st.plotly_chart(fig1,use_container_width=True)

        except:
            st.warning("Unable to load candlestick data")

        st.subheader("📉 RSI Indicator")

        fig2=go.Figure()
        
        fig2.add_trace(go.Scatter(
            x=df["Time"],
            y=df["RSI"],
            line=dict(color="orange",width=3),
            name="RSI"
            )
                       )
        
        fig2.add_hline(y=70,line_dash="dash",line_color="red")
        fig2.add_hline(y=30,line_dash="dash",line_color="green")
        
        fig2.update_layout(
            template="plotly_dark",
            title="Relative Strength Index",
            height=350
            )
        st.plotly_chart(fig2,use_container_width=True)

        st.subheader("📊 MACD Indicator")

        fig3=go.Figure()
        
        fig3.add_trace(go.Scatter(
            x=df["Time"],
            y=df["MACD"],
            line=dict(color="#00d4ff",width=2),
            name="MACD"
            ))
        
        fig3.add_trace(go.Scatter(
            x=df["Time"],
            y=df["Signal"],
            line=dict(color="#ffd166",width=2),
            name="Signal"
            ))
        
        hist=df["MACD"]-df["Signal"]
        
        fig3.add_bar(
            x=df["Time"],
            y=hist,
            marker_color="purple",
            opacity=0.4,
            name="Histogram"
            )
        
        fig3.update_layout(
            template="plotly_dark",
            title="MACD Indicator",
            height=400
            )
        
        st.plotly_chart(fig3,use_container_width=True)
        
# ================= HISTORY TAB =================
with tab3:
    st.subheader("Trade History")
    show_trade_table(50)

# ================= PERFORMANCE TAB =================
with tab4:

    st.subheader("📊 Strategy Performance Overview")

    if st.session_state.trades:

        df_perf = pd.DataFrame(
            st.session_state.trades,
            columns=["Time","Asset","Type","Entry","SL","TP","Exit","PnL","Balance"]
        )

        total_trades = len(df_perf)
        winning_trades = len(df_perf[df_perf["PnL"] > 0])
        losing_trades = len(df_perf[df_perf["PnL"] <= 0])

        win_rate = round((winning_trades / total_trades) * 100, 2)

        total_profit = df_perf[df_perf["PnL"] > 0]["PnL"].sum()
        total_loss = df_perf[df_perf["PnL"] <= 0]["PnL"].sum()

        net_profit = df_perf["PnL"].sum()

        profit_factor = round(abs(total_profit / total_loss), 2) if total_loss != 0 else "∞"

        col1,col2,col3,col4 = st.columns(4)

        col1.metric("Total Trades", total_trades)
        col2.metric("Win Rate (%)", win_rate)
        col3.metric("Net Profit", round(net_profit,2))
        col4.metric("Profit Factor", profit_factor)

        st.subheader("📈 Equity Curve")

        fig_equity = go.Figure()

        fig_equity.add_trace(go.Scatter(
            x=df_perf["Time"],
            y=df_perf["Balance"],
            mode="lines+markers",
            line=dict(color="cyan", width=2)
        ))

        st.plotly_chart(fig_equity, use_container_width=True)

    else:
        st.info("No trades yet to calculate performance.")