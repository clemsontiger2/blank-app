import datetime

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Fear & Greed Index", page_icon="📊", layout="wide")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
CNN_API_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

RATING_COLORS = {
    "Extreme Fear": "#d32f2f",
    "Fear": "#f57c00",
    "Neutral": "#fdd835",
    "Greed": "#7cb342",
    "Extreme Greed": "#2e7d32",
}

GAUGE_STEPS = [
    {"range": [0, 25], "color": "#d32f2f"},
    {"range": [25, 45], "color": "#f57c00"},
    {"range": [45, 55], "color": "#fdd835"},
    {"range": [55, 75], "color": "#7cb342"},
    {"range": [75, 100], "color": "#2e7d32"},
]


def _rating_label(score: float) -> str:
    if score <= 25:
        return "Extreme Fear"
    if score <= 45:
        return "Fear"
    if score <= 55:
        return "Neutral"
    if score <= 75:
        return "Greed"
    return "Extreme Greed"


@st.cache_data(ttl=300)
def fetch_fear_greed_data() -> dict | None:
    """Fetch Fear & Greed data from CNN's API (cached 5 min)."""
    start_date = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(f"{CNN_API_URL}/{start_date}", headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        st.error(f"Failed to fetch data from CNN: {exc}")
        return None


def build_gauge(score: float, title: str = "Current Index") -> go.Figure:
    """Return a Plotly gauge figure for the given score."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"font": {"size": 52}},
            title={"text": title, "font": {"size": 18}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1},
                "bar": {"color": "#222"},
                "steps": GAUGE_STEPS,
                "threshold": {
                    "line": {"color": "white", "width": 4},
                    "thickness": 0.8,
                    "value": score,
                },
            },
        )
    )
    fig.update_layout(height=280, margin={"t": 60, "b": 10, "l": 30, "r": 30})
    return fig


def build_history_chart(data: dict) -> go.Figure | None:
    """Return a Plotly line chart of historical F&G values."""
    hist = data.get("fear_and_greed_historical", {}).get("data")
    if not hist:
        return None

    df = pd.DataFrame(hist)
    df["date"] = pd.to_datetime(df["x"], unit="ms")
    df.rename(columns={"y": "score"}, inplace=True)
    df.sort_values("date", inplace=True)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["score"],
            mode="lines",
            line={"width": 2, "color": "#1f77b4"},
            fill="tozeroy",
            fillcolor="rgba(31,119,180,0.12)",
            hovertemplate="Date: %{x|%b %d, %Y}<br>Score: %{y:.1f}<extra></extra>",
        )
    )

    # Sentiment bands
    fig.add_hrect(y0=0, y1=25, fillcolor="#d32f2f", opacity=0.07, line_width=0)
    fig.add_hrect(y0=25, y1=45, fillcolor="#f57c00", opacity=0.07, line_width=0)
    fig.add_hrect(y0=45, y1=55, fillcolor="#fdd835", opacity=0.07, line_width=0)
    fig.add_hrect(y0=55, y1=75, fillcolor="#7cb342", opacity=0.07, line_width=0)
    fig.add_hrect(y0=75, y1=100, fillcolor="#2e7d32", opacity=0.07, line_width=0)

    fig.update_layout(
        title="Historical Fear & Greed Index (Past Year)",
        xaxis_title="Date",
        yaxis_title="Score",
        yaxis={"range": [0, 100]},
        height=400,
        margin={"t": 50, "b": 40, "l": 50, "r": 20},
        hovermode="x unified",
    )
    return fig


# ---------------------------------------------------------------------------
# Indicator descriptions
# ---------------------------------------------------------------------------
INDICATOR_INFO = {
    "Market Momentum": "S&P 500 vs its 125-day moving average.",
    "Stock Price Strength": "Net new 52-week highs vs lows on the NYSE.",
    "Stock Price Breadth": "Volume of advancing vs declining shares.",
    "Put and Call Options": "Put/call ratio — high put volume signals fear.",
    "Market Volatility": "VIX level relative to its 50-day moving average.",
    "Safe Haven Demand": "Bond returns vs stock returns over 20 days.",
    "Junk Bond Demand": "Yield spread between junk bonds and investment-grade bonds.",
}

INDICATOR_KEYS = [
    ("market_momentum_sp500", "Market Momentum"),
    ("stock_price_strength", "Stock Price Strength"),
    ("stock_price_breadth", "Stock Price Breadth"),
    ("put_call_options", "Put and Call Options"),
    ("market_volatility_vix", "Market Volatility"),
    ("safe_haven_demand", "Safe Haven Demand"),
    ("junk_bond_demand", "Junk Bond Demand"),
]


# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------
st.title("📊 CNN Fear & Greed Index Dashboard")
st.caption("Real-time market sentiment powered by CNN's Fear & Greed Index")

data = fetch_fear_greed_data()

if data is None:
    st.warning("Unable to load Fear & Greed data. Please try again later.")
    st.stop()

# --- Current score ---
fg = data.get("fear_and_greed", {})
current_score = fg.get("score", 0)
current_rating = fg.get("rating", _rating_label(current_score))
previous_close = fg.get("previous_close", current_score)
timestamp_ms = fg.get("timestamp")

# Normalise rating to title case for colour lookup
rating_display = current_rating.replace("_", " ").title()
if rating_display not in RATING_COLORS:
    rating_display = _rating_label(current_score)
color = RATING_COLORS.get(rating_display, "#666")

last_updated = ""
if timestamp_ms:
    last_updated = datetime.datetime.fromtimestamp(
        timestamp_ms / 1000, tz=datetime.timezone.utc
    ).strftime("%b %d, %Y %H:%M UTC")

# --- Layout: top row ---
col_gauge, col_info = st.columns([1, 1])

with col_gauge:
    st.plotly_chart(build_gauge(current_score), use_container_width=True)

with col_info:
    st.markdown("### Sentiment")
    st.markdown(
        f"<h1 style='color:{color}; margin:0;'>{rating_display}</h1>",
        unsafe_allow_html=True,
    )
    delta = round(current_score - previous_close, 1)
    st.metric(label="Score", value=f"{current_score:.1f}", delta=f"{delta:+.1f} vs prev close")
    if last_updated:
        st.caption(f"Last updated: {last_updated}")

    st.markdown(
        """
        | Range | Sentiment |
        |-------|-----------|
        | 0–25 | Extreme Fear |
        | 25–45 | Fear |
        | 45–55 | Neutral |
        | 55–75 | Greed |
        | 75–100 | Extreme Greed |
        """
    )

# --- Historical chart ---
st.divider()
hist_fig = build_history_chart(data)
if hist_fig:
    st.plotly_chart(hist_fig, use_container_width=True)
else:
    st.info("Historical data is not available right now.")

# --- Component indicators ---
st.divider()
st.subheader("Component Indicators")

# Build rows of indicator cards (2 per row for readability)
cols_per_row = 2
row_cols = st.columns(cols_per_row)
col_idx = 0

for key, label in INDICATOR_KEYS:
    indicator = data.get(key, {})
    if not indicator:
        continue

    score = indicator.get("score")
    rating = indicator.get("rating", "")
    if score is None:
        continue

    ind_rating = rating.replace("_", " ").title()
    if ind_rating not in RATING_COLORS:
        ind_rating = _rating_label(score)
    ind_color = RATING_COLORS.get(ind_rating, "#666")

    with row_cols[col_idx % cols_per_row]:
        st.markdown(
            f"""
            <div style="border:1px solid #ddd; border-radius:10px; padding:16px; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong>{label}</strong>
                    <span style="background:{ind_color}; color:white; padding:2px 10px;
                                 border-radius:12px; font-size:0.85em;">{ind_rating}</span>
                </div>
                <div style="font-size:2em; font-weight:700; margin:6px 0;">{score:.1f}</div>
                <div style="font-size:0.85em; color:#888;">{INDICATOR_INFO.get(label, "")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    col_idx += 1

# --- Footer ---
st.divider()
st.caption(
    "Data sourced from [CNN Fear & Greed Index](https://www.cnn.com/markets/fear-and-greed). "
    "This dashboard is for informational purposes only and does not constitute financial advice."
)
