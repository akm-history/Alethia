"""
Alethia — Personal Global Intelligence Dashboard
Run with:  streamlit run alethia_app.py
Requires:  pip install streamlit pandas yfinance plotly requests
"""

import io
import json
import os
from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import yfinance as yf

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Alethia",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_FILE = "alethia_data.json"

DEFAULT_EVENTS = pd.DataFrame(
    {
        "Event": [
            "US Political Developments",
            "Russia-Ukraine Conflict",
            "Middle East Tensions",
            "US-China Relations",
            "Global Economic Risks",
        ],
        "Date": [
            "2025-Ongoing",
            "2022-Ongoing",
            "2023-Ongoing",
            "2024-Ongoing",
            "2024-2026",
        ],
        "Implications": [
            "Policy shifts, market volatility",
            "Energy, food security, NATO",
            "Oil prices, regional stability",
            "Supply chains, tech competition",
            "Debt, inflation, commodities",
        ],
        "Risk Score": [8, 7, 8, 6, 7],
        "Stock Impact": [
            "Broad markets",
            "Oil & Defense",
            "Oil up",
            "Tech & Semis",
            "Volatility",
        ],
        "Lat": [38.9, 48.0, 31.0, 35.0, 0.0],
        "Lon": [-77.0, 37.0, 35.0, 105.0, 0.0],
    }
)

# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #
def load_data():
    """Load saved state; fall back to clean defaults on any problem."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
                # Make sure expected keys exist.
                return {
                    "notes": raw.get("notes", ""),
                    "events": raw.get("events"),
                    "history": raw.get("history", ""),
                    "analysis": raw.get("analysis", {}),
                }
        except (json.JSONDecodeError, OSError):
            pass
    return {"notes": "", "events": None, "history": "", "analysis": {}}


def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except OSError as e:
        st.error(f"Could not save data: {e}")
        return False


def events_from_json(s):
    """pandas 2.x requires a buffer, not a bare JSON string."""
    try:
        return pd.read_json(io.StringIO(s))
    except ValueError:
        return DEFAULT_EVENTS.copy()


if "data" not in st.session_state:
    st.session_state.data = load_data()
data = st.session_state.data

if data.get("events"):
    events_df = events_from_json(data["events"])
else:
    events_df = DEFAULT_EVENTS.copy()

# Guarantee numeric columns are actually numeric (user edits can break this).
for col in ("Risk Score", "Lat", "Lon"):
    if col in events_df.columns:
        events_df[col] = pd.to_numeric(events_df[col], errors="coerce")

# --------------------------------------------------------------------------- #
# Header + sidebar
# --------------------------------------------------------------------------- #
st.title("🌍 Alethia — Personal Global Intelligence Dashboard")
st.caption(
    "A truth-seeking aggregator of major world events, geopolitics, markets, "
    "and balanced analysis. Sources are yours to verify."
)

st.sidebar.header("Controls")
if st.sidebar.button("🔄 Clear cached market data"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared.")

with st.sidebar.expander("📊 Risk score key"):
    st.markdown("**1–3** Low · **4–6** Moderate · **7–10** High")

st.sidebar.divider()
st.sidebar.success("🌍 Alethia")

# --------------------------------------------------------------------------- #
# Market data
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=3600, show_spinner=False)
def get_market_data(ticker, period="1mo"):
    """Return a tidy DataFrame with a Date column and a Close column."""
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
    except Exception:
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    # Recent yfinance returns a MultiIndex even for one ticker — flatten it.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()
    # The date column is "Date" for daily data, "Datetime" for intraday.
    date_col = "Date" if "Date" in df.columns else df.columns[0]
    df = df.rename(columns={date_col: "Date"})
    return df


# --------------------------------------------------------------------------- #
# Tabs
# --------------------------------------------------------------------------- #
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["📅 Events & Map", "📊 Markets", "📜 History", "⚖️ Analysis", "📰 News", "📝 Notes"]
)

# ----- Events & Map -------------------------------------------------------- #
with tab1:
    st.header("Major world events")
    st.caption("Edit any cell, add or delete rows, then save. Lat/Lon place a pin on the map.")

    edited = st.data_editor(
        events_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Risk Score": st.column_config.NumberColumn(min_value=1, max_value=10, step=1),
            "Lat": st.column_config.NumberColumn(format="%.2f"),
            "Lon": st.column_config.NumberColumn(format="%.2f"),
        },
        key="events_editor",
    )

    if st.button("💾 Save events"):
        clean = edited.copy()
        for col in ("Risk Score", "Lat", "Lon"):
            if col in clean.columns:
                clean[col] = pd.to_numeric(clean[col], errors="coerce")
        data["events"] = clean.to_json(orient="records")
        if save_data(data):
            st.success("Events saved.")
            st.rerun()

    st.subheader("🌍 Interactive world map")
    hide_unplaced = st.checkbox("Hide events without coordinates (0, 0)", value=True)

    map_df = edited.dropna(subset=["Lat", "Lon"]).copy()
    map_df["Risk Score"] = pd.to_numeric(map_df["Risk Score"], errors="coerce").fillna(1)
    if hide_unplaced:
        map_df = map_df[~((map_df["Lat"] == 0) & (map_df["Lon"] == 0))]

    if map_df.empty:
        st.info("No placed events to show. Add latitude/longitude to an event above.")
    else:
        fig = px.scatter_geo(
            map_df,
            lat="Lat",
            lon="Lon",
            hover_name="Event",
            hover_data=["Risk Score", "Implications"],
            size="Risk Score",
            color="Risk Score",
            color_continuous_scale="OrRd",
            projection="natural earth",
        )
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

# ----- Markets ------------------------------------------------------------- #
with tab2:
    st.header("Economic & market impacts")
    st.caption("Comma-separate tickers to compare. Try ^GSPC (S&P 500), CL=F (oil), GC=F (gold), ^VIX.")

    col_a, col_b = st.columns([3, 1])
    with col_a:
        ticker_input = st.text_input("Tickers", "^GSPC")
    with col_b:
        period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "5y"], index=0)

    tickers = [t.strip() for t in ticker_input.split(",") if t.strip()]
    normalize = len(tickers) > 1
    if normalize:
        st.caption("Multiple tickers shown as % change from start for fair comparison.")

    series = []
    metrics = []
    for t in tickers:
        d = get_market_data(t, period)
        if d.empty or "Close" not in d.columns:
            st.warning(f"No data for **{t}**. Check the symbol (e.g. CL=F for oil).")
            continue
        d = d.dropna(subset=["Close"])
        if d.empty:
            continue
        first, last = float(d["Close"].iloc[0]), float(d["Close"].iloc[-1])
        pct = (last / first - 1) * 100 if first else 0
        metrics.append((t, last, pct))
        plot = d[["Date", "Close"]].copy()
        plot["Ticker"] = t
        if normalize:
            plot["Value"] = d["Close"] / first * 100
        else:
            plot["Value"] = d["Close"]
        series.append(plot)

    if metrics:
        cols = st.columns(len(metrics))
        for c, (t, last, pct) in zip(cols, metrics):
            c.metric(t, f"{last:,.2f}", f"{pct:+.2f}%")

    if series:
        combined = pd.concat(series, ignore_index=True)
        ylab = "Indexed to 100" if normalize else "Close"
        fig = px.line(
            combined, x="Date", y="Value", color="Ticker",
            labels={"Value": ylab}, title="Price trend",
        )
        st.plotly_chart(fig, use_container_width=True)
    elif tickers:
        st.info("Nothing to plot yet.")

# ----- History ------------------------------------------------------------- #
with tab3:
    st.header("Historical context")
    st.caption("Keep your own background notes here. Favor primary and verified sources.")
    history = st.text_area(
        "Historical background, timelines, source links…",
        value=data.get("history", ""),
        height=350,
    )
    if st.button("💾 Save history"):
        data["history"] = history
        if save_data(data):
            st.success("History saved.")

# ----- Analysis ------------------------------------------------------------ #
with tab4:
    st.header("Balanced pros / cons")
    st.caption("Write the strongest case each side would make. Saved per event.")
    if edited.empty or "Event" not in edited.columns:
        st.info("Add an event in the first tab to analyze it.")
    else:
        options = [e for e in edited["Event"].dropna().tolist() if str(e).strip()]
        if not options:
            st.info("Add a named event to analyze it.")
        else:
            event = st.selectbox("Select event", options)
            stored = data.get("analysis", {}).get(event, "")
            analysis = st.text_area(
                f"Analysis — {event}",
                value=stored,
                height=300,
                placeholder="Supporters argue…\n\nCritics argue…\n\nKey uncertainties…",
            )
            if st.button("💾 Save analysis"):
                data.setdefault("analysis", {})[event] = analysis
                if save_data(data):
                    st.success("Analysis saved.")

# ----- News ---------------------------------------------------------------- #
with tab5:
    st.header("📰 Latest news")
    st.info("Free key at https://newsapi.org — stays in your browser session.")
    api_key = st.text_input("NewsAPI key", type="password")
    query = st.text_input("Search", "geopolitics")

    if st.button("Fetch news"):
        if not api_key:
            st.warning("Enter a NewsAPI key first.")
        elif not query.strip():
            st.warning("Enter a search term.")
        else:
            url = (
                "https://newsapi.org/v2/everything"
                f"?q={quote_plus(query)}&sortBy=publishedAt&pageSize=8&language=en"
                f"&apiKey={api_key}"
            )
            try:
                resp = requests.get(url, timeout=15)
                payload = resp.json()
                if payload.get("status") != "ok":
                    st.error(payload.get("message", "NewsAPI returned an error."))
                else:
                    articles = payload.get("articles", [])
                    if not articles:
                        st.info("No articles found for that query.")
                    for a in articles:
                        st.markdown(f"#### {a.get('title', 'Untitled')}")
                        src = a.get("source", {}).get("name", "")
                        when = (a.get("publishedAt") or "")[:10]
                        st.caption(" · ".join(x for x in (src, when) if x))
                        if a.get("description"):
                            st.write(a["description"])
                        if a.get("url"):
                            st.markdown(f"[Read full article]({a['url']})")
                        st.divider()
            except requests.RequestException as e:
                st.error(f"Could not fetch news: {e}")

# ----- Notes --------------------------------------------------------------- #
with tab6:
    st.header("📝 My research notes")
    notes = st.text_area(
        "Your thoughts, sources, analysis…",
        value=data.get("notes", ""),
        height=400,
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save notes"):
            data["notes"] = notes
            if save_data(data):
                st.success("Notes saved.")
    with col2:
        st.download_button(
            "📤 Export notes",
            data=notes,
            file_name="alethia_notes.txt",
            mime="text/plain",
        )
