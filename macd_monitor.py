"""
MACD 多股票監控系統（含成交量 / 支撐阻力）- Streamlit Cloud App
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

DEFAULT_SYMBOLS = ["QQQ", "TSLA", "TSLL", "SPCX", "AAPL", "GOOGL", "XPEV", "NIO", "META", "MSFT", "NVDA", "AMD", "INTC", "TSM", "XOM" , "VST", "RKLB", "ARM", "SNDK"]


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


# ─── 成交量指標 ───────────────────────────────────────────
INTRADAY_INTERVALS = ["1m", "5m", "15m", "30m", "1h", "60m", "90m"]


def fmt_volume(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    v = float(v)
    if v >= 1e9:
        return f"{v / 1e9:.2f}B"
    if v >= 1e6:
        return f"{v / 1e6:.2f}M"
    if v >= 1e3:
        return f"{v / 1e3:.1f}K"
    return f"{v:.0f}"


def calc_volume_indicators(df: pd.DataFrame, ma_period: int = 20):
    """回傳 (均量, 量比 RVOL, OBV, OBV 均線)。
    量比 = 當根成交量 / 前 N 根平均成交量（不含當根）"""
    vol = df["Volume"].astype(float)
    vol_ma = vol.rolling(ma_period, min_periods=5).mean()
    base = vol.shift(1).rolling(ma_period, min_periods=5).mean()
    rvol = vol / base.replace(0, np.nan)
    direction = np.sign(df["Close"].diff().fillna(0))
    obv = (direction * vol).cumsum()
    obv_ma = obv.rolling(ma_period, min_periods=5).mean()
    return vol_ma, rvol, obv, obv_ma


def calc_vwap(df: pd.DataFrame, interval: str) -> pd.Series:
    """日內：每個交易日重置的 VWAP；日線以上：滾動 20 根 VWAP"""
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    pv = tp * df["Volume"]
    if interval in INTRADAY_INTERVALS:
        try:
            days = df.index.tz_convert("America/New_York").date if df.index.tz is not None else df.index.date
        except Exception:
            days = df.index.date
        days = pd.Series(list(days), index=df.index)
        cum_pv = pv.groupby(days).cumsum()
        cum_v = df["Volume"].groupby(days).cumsum()
    else:
        cum_pv = pv.rolling(20, min_periods=1).sum()
        cum_v = df["Volume"].rolling(20, min_periods=1).sum()
    return cum_pv / cum_v.replace(0, np.nan)


def classify_volume(rvol, price_chg_pct: float) -> tuple:
    """量價關係分類，回傳 (狀態文字, badge類型)"""
    if rvol is None or pd.isna(rvol):
        return "無量能數據", "neu"
    up = price_chg_pct >= 0
    if rvol >= 2.0:
        return ("爆量上漲" if up else "爆量下跌"), ("bull" if up else "bear")
    if rvol >= 1.3:
        return ("放量上漲" if up else "放量下跌"), ("bull" if up else "bear")
    if rvol <= 0.7:
        return ("縮量上漲(動能存疑)" if up else "縮量下跌(賣壓減輕)"), "warn"
    return "量能正常", "neu"


def obv_trend(obv: pd.Series, obv_ma: pd.Series) -> str:
    if len(obv) == 0 or pd.isna(obv_ma.iloc[-1]):
        return "OBV —"
    return "OBV 資金流入" if obv.iloc[-1] > obv_ma.iloc[-1] else "OBV 資金流出"


# ─── 支撐 / 阻力 ──────────────────────────────────────────
def find_sr_levels(df: pd.DataFrame, atr: float, window: int = 5,
                   lookback: int = 120, max_levels: int = 3):
    """擺動高低點 (swing high/low) + 價位聚類。
    回傳 (supports, resistances)，皆由近到遠排序，元素為 {price, touches}。
    觸及次數越多，該價位越有效。"""
    d = df.tail(lookback)
    if len(d) < 2 * window + 1:
        return [], []
    close = float(df["Close"].iloc[-1])
    size = 2 * window + 1
    hi, lo = d["High"], d["Low"]
    pts = list(hi[hi == hi.rolling(size, center=True).max()].values) + \
          list(lo[lo == lo.rolling(size, center=True).min()].values)
    pts = sorted(float(p) for p in pts)

    if atr is not None and not pd.isna(atr):
        tol = max(float(atr) * 0.5, close * 0.002)
    else:
        tol = close * 0.005

    clusters = []
    for p in pts:
        if clusters and p - float(np.mean(clusters[-1])) <= tol:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    levels = [{"price": float(np.mean(c)), "touches": len(c)} for c in clusters]

    resistances = sorted([l for l in levels if l["price"] > close], key=lambda l: l["price"])[:max_levels]
    supports = sorted([l for l in levels if l["price"] < close], key=lambda l: -l["price"])[:max_levels]

    # 找不到擺動點時，退而求其次用區間高低點
    if not resistances:
        top = float(d["High"].max())
        if top > close:
            resistances = [{"price": top, "touches": 1}]
    if not supports:
        bot = float(d["Low"].min())
        if bot < close:
            supports = [{"price": bot, "touches": 1}]
    return supports, resistances


def calc_pivot_points(df: pd.DataFrame):
    """經典樞軸點，以「前一根已完成 K 線」計算當根的 P / R1 / R2 / S1 / S2"""
    if len(df) < 2:
        return None
    p = df.iloc[-2]
    H, L, C = float(p["High"]), float(p["Low"]), float(p["Close"])
    P = (H + L + C) / 3
    return {"R2": P + (H - L), "R1": 2 * P - L, "P": P, "S1": 2 * P - H, "S2": P - (H - L)}


def describe_sr(close: float, supports: list, resistances: list, atr: float) -> dict:
    def _info(lv):
        if lv is None:
            return None
        dist = lv["price"] - close
        return {
            "price": lv["price"],
            "pct": dist / close * 100,
            "atr": (abs(dist) / atr) if atr and atr > 0 else None,
            "touches": lv["touches"],
        }

    s1 = _info(supports[0]) if supports else None
    r1 = _info(resistances[0]) if resistances else None
    if s1 and r1:
        rng = r1["price"] - s1["price"]
        pos = (close - s1["price"]) / rng if rng > 0 else 0.5
        position = "靠近支撐" if pos <= 0.3 else ("靠近阻力" if pos >= 0.7 else "區間中段")
    elif r1:
        position = "接近區間低點（下方無明顯支撐）"
    elif s1:
        position = "接近區間高點（上方無明顯阻力）"
    else:
        position = "—"
    return {"s1": s1, "r1": r1, "position": position}


def render_sr_html(close: float, supports: list, resistances: list, atr: float) -> str:
    def _row(kind, lv, cls):
        dist = lv["price"] - close
        d_atr = f"{abs(dist) / atr:.1f}" if atr and atr > 0 else "—"
        return (f'<tr><td class="{cls}">{kind}</td><td>{lv["price"]:.2f}</td>'
                f'<td class="{cls}">{dist / close * 100:+.2f}%</td><td>{d_atr}</td>'
                f'<td>{lv["touches"]}</td></tr>')

    rows = ""
    for i, lv in reversed(list(enumerate(resistances, 1))):
        rows += _row(f"阻力 R{i}", lv, "cell-neg")
    rows += (f'<tr style="background:#f0ece5"><td><b>現價</b></td><td><b>{close:.2f}</b></td>'
             f'<td>—</td><td>—</td><td>—</td></tr>')
    for i, lv in enumerate(supports, 1):
        rows += _row(f"支撐 S{i}", lv, "cell-pos")
    header = "<th>類型</th><th>價位</th><th>距現價</th><th>距離 (ATR)</th><th>觸及次數</th>"
    return f'<table class="macd-table"><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table>'


def lvl_card_html(title: str, lv, cls: str, empty_txt: str) -> str:
    if not lv:
        return (f'<div class="metric-card"><div class="label">{title}</div>'
                f'<div class="value neu">—</div><div class="sub neu">{empty_txt}</div></div>')
    atr_txt = f"{lv['atr']:.1f} ATR" if lv["atr"] is not None else "—"
    return (f'<div class="metric-card"><div class="label">{title}</div>'
            f'<div class="value {cls}">{lv["price"]:.2f}</div>'
            f'<div class="sub">{lv["pct"]:+.2f}% ｜ {atr_txt} ｜ 觸及 {lv["touches"]} 次</div></div>')


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


def build_macd_table(df: pd.DataFrame, n=10, vol_period: int = 20):
    """回傳最近 n 根 + 預測欄位"""
    macd, signal, hist = calc_macd(df["Close"])
    statuses = classify_status(hist, macd, signal)
    _, rvol_all, _, _ = calc_volume_indicators(df, vol_period)
    tail_rvol = rvol_all.tail(n)
    tail_prev = df["Close"].shift(1).tail(n)

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
            "成交量": fmt_volume(tail["Volume"].iloc[i]),
            "量比": (f"{tail_rvol.iloc[i]:.2f}x" if pd.notna(tail_rvol.iloc[i]) else "—"),
            "_rvol": float(tail_rvol.iloc[i]) if pd.notna(tail_rvol.iloc[i]) else float("nan"),
            "_up": bool(pd.isna(tail_prev.iloc[i]) or tail["Close"].iloc[i] >= tail_prev.iloc[i]),
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
    cols = ["日線", "收盤", "成交量", "量比", "MACD", "Histogram", "狀態", "下一交易日預測", "預測 D+1", "預測 D+2", "預測 D+3"]
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

        rv = row["_rvol"]
        rv_cls = "cell-pos" if row["_up"] else "cell-neg"
        if pd.isna(rv):
            rv_cell = "<td>—</td>"
        elif rv >= 1.5:
            rv_cell = f'<td class="{rv_cls}">{row["量比"]}</td>'
        else:
            rv_cell = f'<td>{row["量比"]}</td>'

        rows_html += f"""
        <tr>
            <td>{row['日線']}</td>
            <td>{row['收盤']}</td>
            <td>{row['成交量']}</td>
            {rv_cell}
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
                     hist: pd.Series, interval: str = "1d", vol_ma=None, vwap=None,
                     supports=None, resistances=None):
    """
    三層圖：價格(+VWAP、支撐/阻力線) / 成交量(+均量) / MACD。
    使用 categorical（字串）x 軸，徹底消除非交易時段空白。
    """
    x_labels = fmt_labels(df.index, interval)
    x_macd   = fmt_labels(macd.index, interval)
    x_hist   = fmt_labels(hist.index, interval)
    x_signal = fmt_labels(signal.index, interval)

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.45, 0.20, 0.35],
        vertical_spacing=0.05,
        subplot_titles=[f"{symbol} 收盤價", "成交量", "MACD (12,26,9)"]
    )

    # ── Row 1：收盤線 + VWAP + 支撐阻力 ──
    fig.add_trace(go.Scatter(
        x=x_labels, y=df["Close"].values,
        mode="lines", name="收盤價",
        line=dict(color="#5a7fa8", width=2),
    ), row=1, col=1)

    if vwap is not None:
        fig.add_trace(go.Scatter(
            x=fmt_labels(vwap.index, interval), y=vwap.values,
            mode="lines", name="VWAP",
            line=dict(color="#8e6bbf", width=1.3, dash="dash"),
        ), row=1, col=1)

    close_lo, close_hi = float(df["Close"].min()), float(df["Close"].max())
    pad = (close_hi - close_lo) * 0.25 or close_hi * 0.01

    def _add_level(lv, color, tag):
        p = lv["price"]
        if close_lo - pad <= p <= close_hi + pad:   # 超出可視範圍的不畫，避免壓縮 K 線
            fig.add_hline(
                y=p, row=1, col=1,
                line=dict(color=color, width=1, dash="dot"),
                annotation_text=f"{tag} {p:.2f}",
                annotation_position="top left",
                annotation_font=dict(size=10, color=color),
            )

    for i, lv in enumerate(resistances or [], 1):
        _add_level(lv, "#c0392b", f"R{i}")
    for i, lv in enumerate(supports or [], 1):
        _add_level(lv, "#4a8c6f", f"S{i}")

    # ── Row 2：成交量 + 均量 ──
    vol_colors = ["#4a8c6f" if c >= o else "#c0392b"
                  for c, o in zip(df["Close"].values, df["Open"].values)]
    fig.add_trace(go.Bar(
        x=x_labels, y=df["Volume"].values,
        name="成交量", marker_color=vol_colors, opacity=0.8,
    ), row=2, col=1)
    if vol_ma is not None:
        fig.add_trace(go.Scatter(
            x=fmt_labels(vol_ma.index, interval), y=vol_ma.values,
            mode="lines", name="均量",
            line=dict(color="#e07b39", width=1.3),
        ), row=2, col=1)

    # ── Row 3：MACD ──
    colors = ["#4a8c6f" if v >= 0 else "#c0392b" for v in hist.values]
    fig.add_trace(go.Bar(
        x=x_hist, y=hist.values,
        name="Histogram",
        marker_color=colors,
        opacity=0.85,
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=x_macd, y=macd.values,
        mode="lines", name="MACD",
        line=dict(color="#5a7fa8", width=1.5),
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=x_signal, y=signal.values,
        mode="lines", name="Signal",
        line=dict(color="#e07b39", width=1.5, dash="dot"),
    ), row=3, col=1)

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
        legend=dict(orientation="h", y=1.04, x=0),
        height=720,
        xaxis_rangeslider_visible=False,
        xaxis=xaxis_cfg,
        xaxis2=xaxis_cfg,
        xaxis3=xaxis_cfg,
    )
    fig.update_yaxes(gridcolor="#e8e3da", zeroline=False)
    fig.update_yaxes(zeroline=True, zerolinecolor="#c0bbb2", row=3, col=1)
    return fig


def build_telegram_signal(symbol: str, df_table: pd.DataFrame, macd_val: float,
                           hist_val: float, trend: str, tf: str, d1: float, d2: float, d3: float,
                           ctx: dict = None) -> str:
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

    # ── 量能 / 支撐阻力區塊 ──
    extra_block = ""
    if ctx:
        rv = ctx.get("rvol")
        rv_ok = rv is not None and not pd.isna(rv)
        rv_txt = f"{rv:.2f}x" if rv_ok else "—"
        r1, s1 = ctx.get("r1"), ctx.get("s1")
        r_txt = f"{r1['price']:.2f}（{r1['pct']:+.1f}%）" if r1 else "—"
        s_txt = f"{s1['price']:.2f}（{s1['pct']:+.1f}%）" if s1 else "—"
        extra_block = (
            f"📦 量能：{ctx['vol_status']}（量比 {rv_txt}，{ctx['obv']}）\n"
            f"🧱 阻力：{r_txt}\n"
            f"🛡 支撐：{s_txt}\n"
            f"📍 位置：{ctx['position']}"
        )
        if trend in ["強勢多頭", "多頭趨勢"] and rv_ok and rv < 0.7:
            advice += " 但量能不足，宜等放量確認。"
        if trend in ["強勢多頭", "多頭趨勢"] and r1 and r1.get("atr") is not None and r1["atr"] < 0.5:
            advice += f" 距阻力僅 {r1['atr']:.1f} ATR，留意假突破。"
        if trend == "空頭趨勢" and s1 and s1.get("atr") is not None and s1["atr"] < 0.5:
            advice += f" 距支撐僅 {s1['atr']:.1f} ATR，留意跌破或反彈。"

    msg = f"""
📊 *{symbol}* MACD 信號 [{tf}]
━━━━━━━━━━━━━━━━━━━━━
收盤價：{close}
MACD：{fmt(macd_val, 3)}
Histogram：{fmt(hist_val, 3)}
當前狀態：{status}
整體趨勢：{trend}
{extra_block}

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



# ─── AI 總結 Prompt 生成 ─────────────────────────────────
def build_ai_prompt(summaries: list, timeframe: str, multi_tf: list,
                    vol_period: int = 20, sr_lookback: int = 120) -> str:
    """把所有股票的分析結果整理成一份可直接貼給 AI 的完整 prompt"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    def _lv(lv):
        return f"{lv['price']:.2f} ({lv['pct']:+.1f}%)" if lv else "—"

    # ── 總覽表 ──
    overview = ["| 代碼 | 收盤 | 漲跌% | MACD | Histogram | 狀態 | 趨勢 | ATR | 量比 | 量價狀態 | OBV | 最近阻力 | 最近支撐 | D+1 | D+2 | D+3 |",
                "|---|" + "---|" * 15]
    for x in summaries:
        rv = f"{x['rvol']:.2f}x" if x.get("rvol") is not None else "—"
        overview.append(
            f"| {x['symbol']} | {x['close']:.2f} | {x['pct']:+.2f}% | {x['macd']:+.3f} | "
            f"{x['hist']:+.3f} | {x['status']} | {x['trend']} | {x['atr']:.3f} | "
            f"{rv} | {x['vol_label']} | {x['obv']} | {_lv(x['sr']['r1'])} | {_lv(x['sr']['s1'])} | "
            f"{x['d1']:+.3f} | {x['d2']:+.3f} | {x['d3']:+.3f} |"
        )

    # ── 支撐阻力明細 ──
    sr_lines = ["| 代碼 | 目前位置 | 阻力（近→遠，括號為觸及次數） | 支撐（近→遠） | 樞軸點 R2 / R1 / P / S1 / S2 |",
                "|---|---|---|---|---|"]
    for x in summaries:
        res = "、".join(f"{lv['price']:.2f}({lv['touches']})" for lv in x["resistances"]) or "—"
        sup = "、".join(f"{lv['price']:.2f}({lv['touches']})" for lv in x["supports"]) or "—"
        pv = x["pivots"]
        pv_txt = " / ".join(f"{pv[k]:.2f}" for k in ["R2", "R1", "P", "S1", "S2"]) if pv else "—"
        sr_lines.append(f"| {x['symbol']} | {x['sr']['position']} | {res} | {sup} | {pv_txt} |")

    # ── 多時框共振表 ──
    mtf_lines = []
    if multi_tf:
        mtf_lines = ["| 代碼 | " + " | ".join(f"{t} 趨勢 (Hist / ATR / 量比)" for t in multi_tf) + " | 共振判斷 |",
                     "|---|" + "---|" * (len(multi_tf) + 1)]
        for x in summaries:
            cells, bull, bear = [], 0, 0
            for t in multi_tf:
                r = x["mtf"].get(t)
                if not r:
                    cells.append("N/A")
                    continue
                rv_t = f"{r['rvol']:.2f}x" if r.get("rvol") is not None else "—"
                cells.append(f"{r['trend']} ({r['hist']:+.3f} / {r['atr']:.3f} / {rv_t})")
                if r["hist"] > 0:
                    bull += 1
                elif r["hist"] < 0:
                    bear += 1
            if bull == len(multi_tf):
                reso = "全部看多（共振）"
            elif bear == len(multi_tf):
                reso = "全部看空（共振）"
            else:
                reso = f"分歧（多 {bull} / 空 {bear}）"
            mtf_lines.append(f"| {x['symbol']} | " + " | ".join(cells) + f" | {reso} |")

    # ── 各股近 5 根明細 ──
    detail = []
    for x in summaries:
        detail.append(f"### {x['symbol']}（{timeframe}）")
        detail.append("| 日期 | 收盤 | 成交量 | 量比 | MACD | Histogram | 狀態 |")
        detail.append("|---|---|---|---|---|---|---|")
        for r in x["recent"]:
            detail.append(f"| {r['date']} | {r['close']} | {r['vol']} | {r['rvol']} | {r['macd']} | {r['hist']} | {r['status']} |")
        detail.append("")

    prompt = f"""你是一位資深美股量化交易分析師。以下是我的 MACD 多股票監控系統在 {now} 產生的完整分析結果，請據此做出總結。

## 一、背景
- 主時間框架：{timeframe}
- 多時框共振：{'、'.join(multi_tf) if multi_tf else '未啟用'}
- MACD 參數 (12, 26, 9)；ATR 週期 14
- 量比 = 當根成交量 / 前 {vol_period} 根平均成交量（≥1.3 放量，≥2 爆量，≤0.7 縮量）；OBV 以 {vol_period} 根均線判斷資金流向
- 支撐阻力 = 近 {sr_lookback} 根的擺動高低點聚類（觸及次數越多越有效），另附前一根 K 線計算的經典樞軸點
- D+1 / D+2 / D+3 是系統以 Histogram 斜率外推的動能預測值（不是價格預測）
- 注意：最後一根 K 線若尚未收盤，成交量不完整，量比可能被低估

## 二、總覽
{chr(10).join(overview)}

## 三、支撐 / 阻力明細
{chr(10).join(sr_lines)}

## 四、多時框共振
{chr(10).join(mtf_lines) if mtf_lines else '（未啟用）'}

## 五、各股近 5 根 K 線明細
{chr(10).join(detail)}

## 六、請你輸出（繁體中文，結構化表格為主，結論要明確，不要模稜兩可）
1. **市場整體判斷**：一句話說明整體偏多、偏空或分歧，並列出多頭與空頭股票各有哪些。
2. **強弱排名表**：依動能強弱由強到弱排序，欄位為 排名 | 代碼 | 方向（做多/做空/觀望） | 信心度（高/中/低） | 一句話理由。信心度請同時考慮 MACD 動能與量能是否確認。
3. **量價訊號表**：標出「放量突破 / 放量跌破 / 量價背離（縮量上漲或價漲量縮）」的股票，說明該訊號可信或不可信的原因。
4. **交易計劃表**：對每檔股票給出 方向 | 參考入場價 | 止損價 | 目標價 | 風險回報比。止損優先放在最近支撐下方（約 0.5 ATR 緩衝），目標優先取最近阻力與下一個阻力；若價位不合理，再以 ATR 倍數換算，並寫出依據。
5. **多時框矛盾警示**：找出短線與長線方向相反的股票，說明該聽哪個時間框架。
6. **最值得優先操作的前 3 檔**，以及明確要避開的股票（例如緊貼阻力、風險回報比差者）。
7. **風險提示**：列出會讓上述判斷失效的具體條件（例如 Histogram 翻負、放量跌破某支撐價位）。

限制：只能根據上面的數據推論，不得編造未提供的新聞或財報；數據不足時請明確說明。"""
    return prompt


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
    st.markdown("**📦 成交量 / 支撐阻力**")
    vol_period = st.number_input("均量週期（根）", min_value=5, max_value=100, value=20, step=1)
    sr_window = st.number_input("擺動點窗口（左右各 N 根）", min_value=2, max_value=15, value=5, step=1,
                                help="數字越大，只保留越明顯的高低點")
    sr_lookback = st.number_input("支撐阻力回看（根）", min_value=40, max_value=500, value=120, step=10)
    show_sr = st.checkbox("圖表顯示支撐/阻力線", value=True)
    show_vwap = st.checkbox("圖表顯示 VWAP", value=True)

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
st.caption("⚠️ 最後一根 K 線若尚未收盤，成交量不完整，量比會被低估；VWAP 日內為每日重置，日線以上為滾動 20 根。")
tf_cfg = TIMEFRAME_MAP[timeframe]
tg_messages_all = []
ai_summaries = []   # 供 AI 總結 prompt 使用

for symbol in symbols:
    st.markdown(f"## 🔷 {symbol}")

    with st.spinner(f"載入 {symbol} 數據..."):
        df = fetch_data(symbol, tf_cfg["period"], tf_cfg["interval"])

    if df.empty or len(df) < 30:
        st.warning(f"⚠️ {symbol}：數據不足，跳過")
        st.markdown("---")
        continue

    df_table, macd_s, signal_s, hist_s, statuses_all = build_macd_table(df, n=10, vol_period=int(vol_period))

    last_row = df_table.iloc[-1]
    macd_val = float(last_row["MACD"].replace("+",""))
    hist_val = last_row["_hist_val"]
    status_val = last_row["_status"]
    close_val = float(last_row["收盤"])
    trend = get_overall_trend(macd_val, hist_val, status_val)
    d1, d2, d3 = predict_next3(hist_s)

    # ── 成交量 / 支撐阻力計算 ────────────────────────────
    atr_main = float(calc_atr(df))
    vol_ma_s, rvol_s, obv_s, obv_ma_s = calc_volume_indicators(df, int(vol_period))
    vwap_s = calc_vwap(df, tf_cfg["interval"])
    rvol_val = rvol_s.iloc[-1]
    chg_pct = (close_val - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100
    vol_label, vol_type = classify_volume(rvol_val, chg_pct)
    obv_txt = obv_trend(obv_s, obv_ma_s)
    supports, resistances = find_sr_levels(df, atr_main, int(sr_window), int(sr_lookback))
    pivots = calc_pivot_points(df)
    sr_info = describe_sr(close_val, supports, resistances, atr_main)

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

    # ── 量能 / 支撐阻力 卡片行 ──────────────────────────
    _cls_map = {"bull": "pos", "bear": "neg", "warn": "neu", "neu": "neu"}
    v1, v2, v3, v4 = st.columns(4)
    with v1:
        rv_txt = f"{rvol_val:.2f}x" if pd.notna(rvol_val) else "—"
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">量比 RVOL</div>
            <div class="value {_cls_map[vol_type]}">{rv_txt}</div>
            <div class="sub">量 {fmt_volume(df['Volume'].iloc[-1])} ／ 均量 {fmt_volume(vol_ma_s.iloc[-1])}</div>
        </div>""", unsafe_allow_html=True)
    with v2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">量價狀態</div>
            <div class="value {_cls_map[vol_type]}" style="font-size:18px; margin:10px 0 6px;">{vol_label}</div>
            <div class="sub">{obv_txt}</div>
        </div>""", unsafe_allow_html=True)
    with v3:
        st.markdown(lvl_card_html("最近阻力", sr_info["r1"], "neg", "上方無明顯阻力"), unsafe_allow_html=True)
    with v4:
        st.markdown(lvl_card_html("最近支撐", sr_info["s1"], "pos", "下方無明顯支撐"), unsafe_allow_html=True)

    # ── 支撐 / 阻力 明細 ────────────────────────────────
    st.markdown(
        f"#### 🧱 支撐 / 阻力　<span style='font-size:13px; color:#888;'>目前位置：{sr_info['position']}</span>",
        unsafe_allow_html=True,
    )
    if supports or resistances:
        st.markdown(render_sr_html(close_val, supports, resistances, atr_main), unsafe_allow_html=True)
    else:
        st.caption("數據不足，無法識別支撐/阻力")
    if pivots:
        st.markdown("**樞軸點（前一根 K 線計算）：** " + " ｜ ".join(f"`{k} {v:.2f}`" for k, v in pivots.items()))

    # ── MACD 表格 ───────────────────────────────────────
    st.markdown("#### 📋 近 10 根 K 線 MACD 分析")
    table_html = render_table_html(df_table)
    st.markdown(table_html, unsafe_allow_html=True)

    # ── 收集本檔分析結果（供 AI 總結） ───────────────────
    prev_close = df["Close"].iloc[-2]
    sym_summary = {
        "symbol": symbol,
        "close": close_val,
        "pct": (close_val - prev_close) / prev_close * 100,
        "macd": macd_val,
        "hist": float(hist_val),
        "status": status_val,
        "trend": trend,
        "atr": float(calc_atr(df)),
        "d1": float(d1), "d2": float(d2), "d3": float(d3),
        "recent": [
            {"date": r["日線"], "close": r["收盤"], "vol": r["成交量"], "rvol": r["量比"], "macd": r["MACD"],
             "hist": fmt(r["_hist_val"], 3), "status": r["_status"]}
            for _, r in df_table.tail(5).iterrows()
        ],
        "rvol": float(rvol_val) if pd.notna(rvol_val) else None,
        "vol_label": vol_label,
        "obv": obv_txt,
        "supports": supports,
        "resistances": resistances,
        "sr": sr_info,
        "pivots": pivots,
        "mtf": {},
    }

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
            _, rv_tf_s, _, _ = calc_volume_indicators(df_tf, int(vol_period))
            rv_tf = rv_tf_s.iloc[-1]
            rv_tf_txt = f"{rv_tf:.2f}x" if pd.notna(rv_tf) else "—"
            sym_summary["mtf"][tf] = {"trend": tr_tf, "hist": float(hv), "atr": float(atr_val),
                                      "rvol": float(rv_tf) if pd.notna(rv_tf) else None}

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
                    <div class="sub" style="margin-bottom:10px;">{tr_tf} ｜ 量比 {rv_tf_txt}</div>
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
    with st.expander(f"📈 {symbol} 價量 / MACD 圖表", expanded=True):
        chart_df = df.tail(60)
        chart_macd = macd_s.tail(60)
        chart_signal = signal_s.tail(60)
        chart_hist = hist_s.tail(60)
        fig = build_macd_chart(
            chart_df, symbol, chart_macd, chart_signal, chart_hist,
            interval=tf_cfg["interval"],
            vol_ma=vol_ma_s.tail(60),
            vwap=vwap_s.tail(60) if show_vwap else None,
            supports=supports if show_sr else None,
            resistances=resistances if show_sr else None,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Telegram 信號預覽 ───────────────────────────────
    tg_ctx = {
        "rvol": rvol_val, "vol_status": vol_label, "obv": obv_txt,
        "r1": sr_info["r1"], "s1": sr_info["s1"], "position": sr_info["position"],
    }
    tg_msg = build_telegram_signal(symbol, df_table, macd_val, hist_val, trend, timeframe, d1, d2, d3, ctx=tg_ctx)
    tg_messages_all.append(tg_msg)
    ai_summaries.append(sym_summary)

    with st.expander(f"📡 Telegram 信號預覽 — {symbol}"):
        st.markdown(f'<div class="tg-box">{tg_msg}</div>', unsafe_allow_html=True)

    st.markdown("---")


# ─── AI 總結 Prompt ──────────────────────────────────────
if ai_summaries:
    st.markdown("## 🤖 AI 總結 Prompt")
    st.caption("已自動整合所有股票、所有時間框架的分析結果。點右上角複製，貼到 Claude / ChatGPT 即可。")
    ai_prompt_text = build_ai_prompt(ai_summaries, timeframe, multi_tf,
                                     vol_period=int(vol_period), sr_lookback=int(sr_lookback))
    st.code(ai_prompt_text, language="markdown")
    st.download_button(
        "⬇️ 下載 Prompt (.txt)",
        data=ai_prompt_text,
        file_name=f"macd_ai_prompt_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain",
    )
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
