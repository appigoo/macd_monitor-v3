"""
MACD 多股票監控系統 - Streamlit Cloud App
作者：量化交易工程師
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import requests
import time

# ─── 頁面設定 ────────────────────────────────────────────
st.set_page_config(
    page_title="MACD 多股票監控",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── 暖米色設計系統 CSS ──────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Noto+Sans+TC:wght@400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans TC', sans-serif;
    background-color: #f5f2ed;
    color: #2c2c2c;
}

/* 主背景 */
.stApp {
    background-color: #f5f2ed;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #ede9e2;
    border-right: 1px solid #d4cfc6;
}

/* 標題 */
h1, h2, h3 {
    font-family: 'IBM Plex Mono', monospace;
    color: #2c2c2c;
}

/* 指標卡片 */
.metric-card {
    background: #fff8f0;
    border: 1px solid #d4cfc6;
    border-radius: 12px;
    padding: 16px 20px;
    margin: 6px 0;
    font-family: 'IBM Plex Mono', monospace;
}
.metric-card .label {
    font-size: 11px;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.metric-card .value {
    font-size: 26px;
    font-weight: 600;
    margin: 4px 0 2px;
}
.metric-card .sub {
    font-size: 12px;
}
.pos { color: #4a8c6f; }
.neg { color: #c0392b; }
.neu { color: #7a7a7a; }

/* 表格樣式 */
.macd-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    background: #fff8f0;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #d4cfc6;
}
.macd-table th {
    background: #e8e3da;
    color: #555;
    padding: 10px 12px;
    text-align: center;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.5px;
}
.macd-table td {
    padding: 9px 12px;
    text-align: center;
    border-bottom: 1px solid #ede9e2;
}
.macd-table tr:last-child td { border-bottom: none; }
.macd-table tr:hover td { background: #f0ece5; }
.cell-pos { color: #4a8c6f; font-weight: 600; }
.cell-neg { color: #c0392b; font-weight: 600; }
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
}
.badge-bull { background: #d4edda; color: #276745; }
.badge-bear { background: #fde8e8; color: #9b2335; }
.badge-neu  { background: #e8e8e8; color: #555; }
.badge-warn { background: #fff3cd; color: #856404; }

/* Telegram 區塊 */
.tg-box {
    background: #fff8f0;
    border: 1px solid #d4cfc6;
    border-left: 4px solid #4a8c6f;
    border-radius: 8px;
    padding: 14px 18px;
    font-size: 13px;
    white-space: pre-wrap;
    font-family: 'IBM Plex Mono', monospace;
}

/* 趨勢標籤 */
.trend-bull {
    background: linear-gradient(135deg, #d4edda, #c3e6cb);
    color: #276745;
    padding: 6px 14px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 13px;
    display: inline-block;
}
.trend-bear {
    background: linear-gradient(135deg, #fde8e8, #f5c6c6);
    color: #9b2335;
    padding: 6px 14px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 13px;
    display: inline-block;
}
.trend-neu {
    background: linear-gradient(135deg, #e8e8e8, #ddd);
    color: #555;
    padding: 6px 14px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 13px;
    display: inline-block;
}

/* Plotly 圖表容器 */
.plot-container { border-radius: 10px; overflow: hidden; }

/* 分隔線 */
hr { border-color: #d4cfc6; }

/* Selectbox / Input */
[data-testid="stSelectbox"], [data-testid="stMultiSelect"] {
    font-family: 'IBM Plex Mono', monospace;
}

/* stMetric 覆蓋 */
[data-testid="stMetric"] {
    background: #fff8f0;
    border: 1px solid #d4cfc6;
    border-radius: 10px;
    padding: 12px;
}
</style>
""", unsafe_allow_html=True)


# ─── 常數 ────────────────────────────────────────────────
TIMEFRAME_MAP = {
    "1m":  {"period": "1d",  "interval": "1m"},
    "5m":  {"period": "5d",  "interval": "5m"},
    "15m": {"period": "10d", "interval": "15m"},
    "30m": {"period": "30d", "interval": "30m"},
    "1h":  {"period": "60d", "interval": "1h"},
    "1d":  {"period": "180d","interval": "1d"},
    "1w":  {"period": "2y",  "interval": "1wk"},
    "1mo": {"period": "5y",  "interval": "1mo"},
}

DEFAULT_SYMBOLS = ["TSLA", "AAPL", "AMZN", "NVDA", "MSFT", "META", "GOOGL"]


# ─── 核心計算函式 ─────────────────────────────────────────
def calc_ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def calc_macd(close: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = calc_ema(close, fast)
    ema_slow = calc_ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calc_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calc_atr(df: pd.DataFrame, period: int = 14) -> float:
    """計算 ATR（平均真實波幅），回傳最新一根值"""
    high = df["High"]
    low  = df["Low"]
    close_prev = df["Close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - close_prev).abs(),
        (low  - close_prev).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()
    return atr.iloc[-1]


def classify_status(hist: pd.Series, macd: pd.Series, signal: pd.Series) -> list:
    statuses = []
    for i in range(len(hist)):
        h = hist.iloc[i]
        h_prev = hist.iloc[i-1] if i > 0 else h
        m = macd.iloc[i]
        s = signal.iloc[i]

        if abs(h) < 0.005:
            status = "接近反轉"
        elif i > 0 and h_prev < 0 and h >= 0:
            status = "Histogram翻正"
        elif i > 0 and m > s and (macd.iloc[i-1] if i > 0 else m) <= (signal.iloc[i-1] if i > 0 else s):
            status = "MACD金叉確認"
        elif h > 0 and m > 0:
            status = "強勢多頭"
        elif h > 0 and i > 0 and h > h_prev:
            status = "多頭加速"
        elif h < 0 and i > 0 and h < h_prev:
            status = "空頭動能強"
        elif h < 0 and i > 0 and abs(h) < abs(h_prev):
            if h > h_prev:
                status = "跌勢放緩"
            else:
                status = "空頭減弱"
        elif h < 0:
            status = "空頭動能強"
        else:
            status = "多頭加速"
        statuses.append(status)
    return statuses


# ─── 狀態 → 下一交易日預測 對照表 ──────────────────────────
STATUS_NEXT_DAY = {
    "空頭動能強":    ("跌勢延續",   "bear"),
    "空頭減弱":      ("跌速放慢",   "warn"),
    "跌勢放緩":      ("接近底部",   "warn"),
    "空頭衰退":      ("技術反彈",   "warn"),
    "接近反轉":      ("金叉概率提升", "neu"),
    "多頭開始回補":  ("動能轉正",   "bull"),
    "Histogram翻正": ("短線突破",   "bull"),
    "MACD金叉確認":  ("多頭加速",   "bull"),
    "多頭加速":      ("趨勢延續",   "bull"),
    "強勢多頭":      ("趨勢延續",   "bull"),
}

def next_day_prediction(status: str) -> tuple:
    """回傳 (預測文字, badge類型)"""
    return STATUS_NEXT_DAY.get(status, ("待觀察", "neu"))


def badge_html(status: str) -> str:
    bull_keywords = ["多頭", "翻正", "金叉", "放緩"]
    bear_keywords = ["空頭", "動能強"]
    warn_keywords = ["接近反轉", "減弱"]
    if any(k in status for k in bull_keywords):
        return f'<span class="badge badge-bull">▲ {status}</span>'
    elif any(k in status for k in bear_keywords):
        return f'<span class="badge badge-bear">▼ {status}</span>'
    elif any(k in status for k in warn_keywords):
        return f'<span class="badge badge-warn">◆ {status}</span>'
    else:
        return f'<span class="badge badge-neu">● {status}</span>'


def predict_next3(hist: pd.Series) -> tuple:
    """基於斜率 + 動能慣性推演 D+1, D+2, D+3"""
    if len(hist) < 3:
        return 0.0, 0.0, 0.0
    recent = hist.iloc[-3:].values
    slope = (recent[-1] - recent[0]) / 2  # 線性斜率

    d1 = recent[-1] + slope            # 延續動能
    d2_slope = slope * 0.5             # 開始鈍化
    d2 = d1 + d2_slope
    d3 = d2 - abs(slope) * 0.3         # 大概率回落
    return d1, d2, d3


def get_overall_trend(macd_val, hist_val, status) -> str:
    if macd_val > 0 and hist_val > 0:
        return "強勢多頭"
    elif hist_val > 0:
        return "多頭趨勢"
    elif hist_val < 0 and macd_val < 0:
        return "空頭趨勢"
    elif "接近反轉" in status or "翻正" in status or "金叉" in status:
        return "趨勢反轉中"
    else:
        return "震盪觀望"


@st.cache_data(ttl=60)
def fetch_data(symbol: str, period: str, interval: str) -> pd.DataFrame:
    try:
        tk = yf.Ticker(symbol)
        df = tk.history(period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        return df
    except Exception:
        return pd.DataFrame()


def fmt(val: float, decimals=3) -> str:
    s = f"{val:+.{decimals}f}"
    return s


def build_macd_table(df: pd.DataFrame, n=10) -> pd.DataFrame:
    """回傳最近 n 根 + 預測欄位"""
    macd, signal, hist = calc_macd(df["Close"])
    statuses = classify_status(hist, macd, signal)

    tail = df.tail(n).copy()
    tail_macd = macd.tail(n)
    tail_signal = signal.tail(n)
    tail_hist = hist.tail(n)
    tail_status = statuses[-n:]

    # 預測（只需對最後一行有意義，其餘顯示空）
    d1, d2, d3 = predict_next3(hist)

    rows = []
    for i in range(len(tail)):
        date_str = tail.index[i].strftime("%m/%d")
        m = tail_macd.iloc[i]
        h = tail_hist.iloc[i]
        st_label = tail_status[i]

        is_last = i == len(tail) - 1
        nd_text, nd_type = next_day_prediction(st_label)
        rows.append({
            "日線": date_str,
            "收盤": f"{tail['Close'].iloc[i]:.2f}",
            "MACD": fmt(m, 3),
            "Histogram": fmt(h, 3),
            "狀態": st_label,
            "下一交易日預測": nd_text,
            "_nd_type": nd_type,
            "預測 D+1": fmt(d1, 3) if is_last else "—",
            "預測 D+2": fmt(d2, 3) if is_last else "—",
            "預測 D+3": fmt(d3, 3) if is_last else "—",
            "_hist_val": h,
            "_status": st_label,
            "_macd_val": m,
        })
    return pd.DataFrame(rows), macd, signal, hist, statuses


def next_day_badge_html(text: str, nd_type: str) -> str:
    type_map = {
        "bull": "badge-bull",
        "bear": "badge-bear",
        "warn": "badge-warn",
        "neu":  "badge-neu",
    }
    icon_map = {
        "bull": "▲",
        "bear": "▼",
        "warn": "◆",
        "neu":  "●",
    }
    cls = type_map.get(nd_type, "badge-neu")
    icon = icon_map.get(nd_type, "●")
    return f'<span class="badge {cls}">{icon} {text}</span>'


def render_table_html(df_table: pd.DataFrame) -> str:
    cols = ["日線", "收盤", "MACD", "Histogram", "狀態", "下一交易日預測", "預測 D+1", "預測 D+2", "預測 D+3"]
    header = "".join(f"<th>{c}</th>" for c in cols)
    rows_html = ""
    for _, row in df_table.iterrows():
        h_val = row["_hist_val"]
        h_cls = "cell-pos" if h_val >= 0 else "cell-neg"
        m_val = float(row["MACD"].replace("+",""))
        m_cls = "cell-pos" if m_val >= 0 else "cell-neg"

        def pred_cell(v):
            if v == "—": return "<td>—</td>"
            fv = float(v.replace("+",""))
            cls = "cell-pos" if fv >= 0 else "cell-neg"
            return f'<td class="{cls}">{v}</td>'

        nd_text = row.get("下一交易日預測", "—")
        nd_type = row.get("_nd_type", "neu")
        nd_cell = f'<td>{next_day_badge_html(nd_text, nd_type)}</td>'

        rows_html += f"""
        <tr>
            <td>{row['日線']}</td>
            <td>{row['收盤']}</td>
            <td class="{m_cls}">{row['MACD']}</td>
            <td class="{h_cls}">{row['Histogram']}</td>
            <td>{badge_html(row['狀態'])}</td>
            {nd_cell}
            {pred_cell(row['預測 D+1'])}
            {pred_cell(row['預測 D+2'])}
            {pred_cell(row['預測 D+3'])}
        </tr>"""

    return f"""
    <table class="macd-table">
        <thead><tr>{header}</tr></thead>
        <tbody>{rows_html}</tbody>
    </table>"""


def fmt_labels(index, interval: str) -> list:
    """
    為 categorical x 軸生成【唯一】字串標籤。

    關鍵原則：每個標籤必須唯一，否則 Plotly categorical axis
    會把相同標籤（如不同日的 "13:30"）合併成同一欄，造成 K 線疊圖。

    策略：
    - 日線/週線/月線：用 "MM/DD" (唯一)
    - 日內：全部用 "MM/DD HH:MM" (唯一)，但 tick 標籤只顯示時間部分
      → 透過 ticktext/tickvals 讓 x 軸標籤更易讀
    """
    import pandas as pd
    intraday = interval in ["1m", "5m", "15m", "30m", "1h", "60m", "90m"]
    labels = []
    for ts in index:
        dt = pd.Timestamp(ts)
        try:
            dt_local = dt.tz_convert("America/New_York") if dt.tzinfo else dt
        except Exception:
            dt_local = dt
        if intraday:
            # 永遠包含日期，保證唯一性
            label = dt_local.strftime("%m/%d %H:%M")
        else:
            label = dt_local.strftime("%m/%d")
        labels.append(label)
    return labels


def make_tick_display(labels: list, interval: str) -> tuple:
    """
    從唯一標籤列表生成抽稀的 tickvals + ticktext，
    日內框架：tick 顯示時間，日期變更時顯示完整日期+時間。
    回傳 (tickvals, ticktext)
    """
    intraday = interval in ["1m", "5m", "15m", "30m", "1h", "60m", "90m"]
    n = len(labels)
    # 抽稀：最多顯示 12 個 tick
    step = max(1, n // 12)
    selected = labels[::step]

    if not intraday:
        return selected, selected

    # 日內：ticktext 同日只顯示 HH:MM，換日顯示 MM/DD HH:MM
    ticktext = []
    prev_date = None
    for lbl in selected:
        # label 格式固定為 "MM/DD HH:MM"
        parts = lbl.split(" ")
        date_part = parts[0]   # MM/DD
        time_part = parts[1] if len(parts) > 1 else lbl
        if date_part != prev_date:
            ticktext.append(lbl)   # 換日：顯示完整
            prev_date = date_part
        else:
            ticktext.append(time_part)  # 同日：只顯示時間
    return selected, ticktext


def build_macd_chart(df: pd.DataFrame, symbol: str, macd: pd.Series, signal: pd.Series,
                     hist: pd.Series, interval: str = "1d"):
    """
    使用 categorical（字串）x 軸，徹底消除非交易時段空白。
    不依賴 rangebreaks，對所有時間框架都有效。
    """
    # 轉換為字串標籤 — 只顯示實際有數據的 K 線
    x_labels = fmt_labels(df.index, interval)
    x_macd   = fmt_labels(macd.index, interval)
    x_hist   = fmt_labels(hist.index, interval)
    x_signal = fmt_labels(signal.index, interval)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.45],
        vertical_spacing=0.06,
        subplot_titles=[f"{symbol} 收盤價", "MACD (12,26,9)"]
    )

    # 收盤線
    fig.add_trace(go.Scatter(
        x=x_labels, y=df["Close"].values,
        mode="lines",
        name="收盤價",
        line=dict(color="#5a7fa8", width=2),
    ), row=1, col=1)

    # Histogram — categorical x 軸下 Bar 不會出現跨時段空隙
    colors = ["#4a8c6f" if v >= 0 else "#c0392b" for v in hist.values]
    fig.add_trace(go.Bar(
        x=x_hist, y=hist.values,
        name="Histogram",
        marker_color=colors,
        opacity=0.85,
    ), row=2, col=1)

    # MACD & Signal
    fig.add_trace(go.Scatter(
        x=x_macd, y=macd.values,
        mode="lines", name="MACD",
        line=dict(color="#5a7fa8", width=1.5),
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=x_signal, y=signal.values,
        mode="lines", name="Signal",
        line=dict(color="#e07b39", width=1.5, dash="dot"),
    ), row=2, col=1)

    # 生成抽稀 tick，日內框架智慧顯示日期/時間
    tickvals, ticktext = make_tick_display(x_labels, interval)

    xaxis_cfg = dict(
        type="category",
        tickvals=tickvals,
        ticktext=ticktext,
        tickangle=-35,
        gridcolor="#e8e3da",
        showgrid=True,
    )

    fig.update_layout(
        paper_bgcolor="#fff8f0",
        plot_bgcolor="#fff8f0",
        font=dict(family="IBM Plex Mono, Noto Sans TC", color="#2c2c2c", size=11),
        margin=dict(l=10, r=10, t=40, b=20),
        legend=dict(orientation="h", y=1.02, x=0),
        height=500,
        xaxis_rangeslider_visible=False,
        xaxis=xaxis_cfg,
        xaxis2=xaxis_cfg,
    )
    fig.update_yaxes(gridcolor="#e8e3da", zeroline=True, zerolinecolor="#c0bbb2")
    return fig


def build_telegram_signal(symbol: str, df_table: pd.DataFrame, macd_val: float,
                           hist_val: float, trend: str, tf: str, d1: float, d2: float, d3: float) -> str:
    last = df_table.iloc[-1]
    status = last["_status"]
    close = last["收盤"]

    # 買賣建議
    if trend in ["強勢多頭", "多頭趨勢"]:
        action = "📈 買入 / 持多"
        advice = "動能向上，可考慮入場或加倉，設止損於近期低點。"
    elif trend in ["空頭趨勢"]:
        action = "📉 觀望 / 做空"
        advice = "空頭動能持續，謹慎持多，可等待 Histogram 回升再入場。"
    elif trend in ["趨勢反轉中"]:
        action = "⚡ 注意反轉信號"
        advice = "市場正在轉換方向，可小倉試探多頭，嚴格控制倉位。"
    else:
        action = "⏸ 觀望"
        advice = "震盪格局，等待方向確認後再行動。"

    msg = f"""
📊 *{symbol}* MACD 信號 [{tf}]
━━━━━━━━━━━━━━━━━━━━━
收盤價：{close}
MACD：{fmt(macd_val, 3)}
Histogram：{fmt(hist_val, 3)}
當前狀態：{status}
整體趨勢：{trend}

🔮 三日推演
  D+1：{fmt(d1, 3)}
  D+2：{fmt(d2, 3)}
  D+3：{fmt(d3, 3)}

🎯 操作建議
  {action}
  {advice}

📅 {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC
""".strip()
    return msg


def send_telegram(bot_token: str, chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200, r.text
    except Exception as e:
        return False, str(e)


# ─── Sidebar ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 設定")
    st.markdown("---")

    raw_symbols = st.text_area(
        "股票代碼（逗號分隔）",
        value=",".join(DEFAULT_SYMBOLS),
        height=80,
    )
    symbols = [s.strip().upper() for s in raw_symbols.split(",") if s.strip()]

    timeframe = st.selectbox(
        "時間框架",
        list(TIMEFRAME_MAP.keys()),
        index=5,  # 預設 1d
    )

    multi_tf = st.multiselect(
        "多時框共振",
        list(TIMEFRAME_MAP.keys()),
        default=["1h", "1d", "1w"],
    )

    st.markdown("---")
    st.markdown("**⏱ 自動刷新**")
    auto_refresh = st.checkbox("啟用自動刷新", value=False)
    refresh_interval = st.selectbox(
        "刷新間隔（秒）",
        [60, 120, 180, 300],
        index=0,
    )

    st.markdown("---")
    st.markdown("**📡 Telegram 設定**")
    tg_token = st.text_input("Bot Token", type="password", placeholder="1234567890:ABC...")
    tg_chat = st.text_input("Chat ID", placeholder="-100xxxxxxxxx")
    tg_send = st.button("📤 發送所有信號")

    st.markdown("---")
    st.caption(f"最後更新：{datetime.now().strftime('%H:%M:%S')}")


# ─── 自動刷新 ─────────────────────────────────────────────
if auto_refresh:
    st.markdown(f"""
    <script>
    setTimeout(function(){{ window.location.reload(); }}, {refresh_interval * 1000});
    </script>
    """, unsafe_allow_html=True)
    st.info(f"⏱ 自動刷新已啟用，每 {refresh_interval} 秒更新一次")


# ─── 主標題 ───────────────────────────────────────────────
st.markdown("# 📊 MACD 多股票監控系統")
st.markdown(f"**時間框架：** `{timeframe}` ｜ **多時框共振：** `{'、'.join(multi_tf)}`")
st.markdown("---")

# ─── 主循環：每個股票 ─────────────────────────────────────
tf_cfg = TIMEFRAME_MAP[timeframe]
tg_messages_all = []

for symbol in symbols:
    st.markdown(f"## 🔷 {symbol}")

    with st.spinner(f"載入 {symbol} 數據..."):
        df = fetch_data(symbol, tf_cfg["period"], tf_cfg["interval"])

    if df.empty or len(df) < 30:
        st.warning(f"⚠️ {symbol}：數據不足，跳過")
        st.markdown("---")
        continue

    df_table, macd_s, signal_s, hist_s, statuses_all = build_macd_table(df, n=10)

    last_row = df_table.iloc[-1]
    macd_val = float(last_row["MACD"].replace("+",""))
    hist_val = last_row["_hist_val"]
    status_val = last_row["_status"]
    close_val = float(last_row["收盤"])
    trend = get_overall_trend(macd_val, hist_val, status_val)
    d1, d2, d3 = predict_next3(hist_s)

    # ── 指標卡片行 ──────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        delta_cls = "pos" if close_val >= df["Close"].iloc[-2] else "neg"
        delta_sym = "▲" if close_val >= df["Close"].iloc[-2] else "▼"
        chg = close_val - df["Close"].iloc[-2]
        pct = chg / df["Close"].iloc[-2] * 100
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">最新收盤</div>
            <div class="value">{close_val:.2f}</div>
            <div class="sub {delta_cls}">{delta_sym} {chg:+.2f} ({pct:+.2f}%)</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        m_cls = "pos" if macd_val >= 0 else "neg"
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">MACD</div>
            <div class="value {m_cls}">{macd_val:+.3f}</div>
            <div class="sub">{status_val}</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        h_cls = "pos" if hist_val >= 0 else "neg"
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Histogram</div>
            <div class="value {h_cls}">{hist_val:+.3f}</div>
            <div class="sub">D+1 {d1:+.3f}</div>
        </div>""", unsafe_allow_html=True)

    with c4:
        if trend in ["強勢多頭", "多頭趨勢"]:
            td_cls = "trend-bull"
        elif trend in ["空頭趨勢"]:
            td_cls = "trend-bear"
        else:
            td_cls = "trend-neu"
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">整體趨勢</div>
            <div style="margin-top:8px"><span class="{td_cls}">{trend}</span></div>
        </div>""", unsafe_allow_html=True)

    # ── MACD 表格 ───────────────────────────────────────
    st.markdown("#### 📋 近 10 根 K 線 MACD 分析")
    table_html = render_table_html(df_table)
    st.markdown(table_html, unsafe_allow_html=True)

    # ── 多時框共振 ──────────────────────────────────────
    if multi_tf:
        st.markdown("#### 🔗 多時框共振")
        mtf_cols = st.columns(len(multi_tf))
        for idx, tf in enumerate(multi_tf):
            cfg = TIMEFRAME_MAP[tf]
            df_tf = fetch_data(symbol, cfg["period"], cfg["interval"])
            if df_tf.empty or len(df_tf) < 30:
                with mtf_cols[idx]:
                    st.markdown(f"`{tf}` 數據不足")
                continue
            m_tf, sig_tf, h_tf = calc_macd(df_tf["Close"])
            st_tf = classify_status(h_tf, m_tf, sig_tf)
            mv = m_tf.iloc[-1]
            hv = h_tf.iloc[-1]
            sv = st_tf[-1]
            tr_tf = get_overall_trend(mv, hv, sv)
            h_cls = "pos" if hv >= 0 else "neg"
            atr_val = calc_atr(df_tf)
            td1, td2, td3 = predict_next3(h_tf)

            def _pred_span(v):
                cls = "pos" if v >= 0 else "neg"
                return f'<span class="{cls}" style="font-weight:600;">{v:+.3f}</span>'

            with mtf_cols[idx]:
                st.markdown(f"""
                <div class="metric-card" style="position:relative;">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div class="label">{tf}</div>
                        <div style="font-family:'IBM Plex Mono',monospace; font-size:11px;
                                    background:#e8e3da; color:#555; padding:2px 8px;
                                    border-radius:4px; font-weight:700; letter-spacing:0.3px;">
                            ATR&nbsp;{atr_val:.3f}
                        </div>
                    </div>
                    <div class="value {h_cls}" style="font-size:20px; margin:6px 0 2px; font-family:'IBM Plex Mono',monospace;">
                        {hv:+.3f}
                    </div>
                    <div class="sub" style="margin-bottom:10px;">{tr_tf}</div>
                    <div style="border-top:1px solid #e8e3da; padding-top:8px; margin-top:4px;
                                font-family:'IBM Plex Mono',monospace; font-size:11px; color:#888;">
                        <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
                            <span>D+1</span>{_pred_span(td1)}
                        </div>
                        <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
                            <span>D+2</span>{_pred_span(td2)}
                        </div>
                        <div style="display:flex; justify-content:space-between;">
                            <span>D+3</span>{_pred_span(td3)}
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)

    # ── MACD 圖表 ───────────────────────────────────────
    with st.expander(f"📈 {symbol} MACD 圖表", expanded=True):
        chart_df = df.tail(60)
        chart_macd = macd_s.tail(60)
        chart_signal = signal_s.tail(60)
        chart_hist = hist_s.tail(60)
        fig = build_macd_chart(chart_df, symbol, chart_macd, chart_signal, chart_hist, interval=tf_cfg["interval"])
        st.plotly_chart(fig, use_container_width=True)

    # ── Telegram 信號預覽 ───────────────────────────────
    tg_msg = build_telegram_signal(symbol, df_table, macd_val, hist_val, trend, timeframe, d1, d2, d3)
    tg_messages_all.append(tg_msg)

    with st.expander(f"📡 Telegram 信號預覽 — {symbol}"):
        st.markdown(f'<div class="tg-box">{tg_msg}</div>', unsafe_allow_html=True)

    st.markdown("---")


# ─── 發送 Telegram ─────────────────────────────────────
if tg_send:
    if not tg_token or not tg_chat:
        st.error("請先填寫 Telegram Bot Token 和 Chat ID")
    else:
        success_count = 0
        for msg in tg_messages_all:
            ok, resp = send_telegram(tg_token, tg_chat, msg)
            if ok:
                success_count += 1
            else:
                st.warning(f"發送失敗：{resp}")
            time.sleep(0.5)
        st.success(f"✅ 已成功發送 {success_count}/{len(tg_messages_all)} 個信號")


# ─── 頁尾 ────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center; color:#aaa; font-size:11px; margin-top:20px; font-family:IBM Plex Mono;'>
MACD 多股票監控系統 ｜ 數據來源：Yahoo Finance ｜ 僅供參考，不構成投資建議
</div>
""", unsafe_allow_html=True)
