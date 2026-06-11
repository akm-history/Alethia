import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import requests
import json
import os

st.set_page_config(page_title="Alethia", layout="wide", initial_sidebar_state="expanded")
st.title("🌍 Alethia — Personal Global Intelligence Dashboard")
st.markdown("**Truth-seeking aggregator of major world events, geopolitics, markets, history, and balanced analysis.**")

# Persistent storage
DATA_FILE = "alethia_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {"notes": "", "events": None}
    return {"notes": "", "events": None}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

st.sidebar.header("Controls")
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()

with st.sidebar.expander("📊 Risk Score Explanation"):
    st.markdown("**1-3**: Low impact  \n**4-6**: Moderate  \n**7-10**: High risk")

@st.cache_data(ttl=3600)
def get_market_data(ticker):
    try:
        df = yf.download(ticker, period="1mo", progress=False)
        return df
    except:
        return pd.DataFrame()

# Default events
if data.get("events") is not None:
    events_df = pd.read_json(data["events"])
else:
    events_df = pd.DataFrame({
        "Event": ["US Political Developments", "Russia-Ukraine Conflict", "Middle East Tensions", "US-China Relations", "Global Economic Risks"],
        "Date": ["2025-Ongoing", "2022-Ongoing", "2023-Ongoing", "2024-Ongoing", "2024-2026"],
        "Implications": ["Policy shifts, market volatility", "Energy, food security, NATO", "Oil prices, regional stability", "Supply chains, tech competition", "Debt, inflation, commodities"],
        "Risk Score": [8, 7, 8, 6, 7],
        "Stock Impact": ["Broad markets", "Oil & Defense", "Oil ↑", "Tech & Semis", "Volatility"],
        "Lat": [38.9, 48.0, 31.0, 35.0, 0],
        "Lon": [-77.0, 37.0, 35.0, 105.0, 0]
    })

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📅 Events & Map", "📊 Markets", "📜 History", "⚖️ Analysis", "📰 News", "📝 Notes"])

with tab1:
    st.header("Major World Events")
    st.dataframe(events_df.drop(columns=["Lat", "Lon"], errors='ignore'), use_container_width=True)
    
    st.subheader("🌍 Interactive World Map")
    fig = px.scatter_geo(events_df, lat='Lat', lon='Lon', hover_name="Event",
                         hover_data=["Risk Score", "Implications"], size="Risk Score")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("➕ Add Custom Event"):
        new_event = st.text_input("Event Name")
        new_date = st.text_input("Date/Status")
        new_imp = st.text_area("Implications")
        new_risk = st.slider("Risk Score (1-10)", 1, 10, 5)
        if st.button("Add Event"):
            new_row = pd.DataFrame([{"Event": new_event, "Date": new_date, "Implications": new_imp, 
                                     "Risk Score": new_risk, "Stock Impact": "", "Lat": 0, "Lon": 0}])
            events_df = pd.concat([events_df, new_row], ignore_index=True)
            data["events"] = events_df.to_json(orient="records")
            save_data(data)
            st.success("Event saved!")

with tab2:
    st.header("Economic & Market Impacts")
    ticker = st.text_input("Ticker (e.g. ^GSPC, CL=F, GC=F)", "^GSPC")
    data_m = get_market_data(ticker)
    if not data_m.empty and "Close" in data_m.columns:
        st.plotly_chart(px.line(data_m, y="Close", title=f"{ticker} Trend"), use_container_width=True)
    else:
        st.warning("No market data available for this ticker right now. Try another (e.g. CL=F for oil).")

with tab3:
    st.header("Historical Context")
    st.write("Use primary and verified sources for deeper background.")

with tab4:
    st.header("Unbiased Pros/Cons")
    if not events_df.empty:
        event = st.selectbox("Select Event", events_df["Event"])
        st.markdown(f"**{event}**")
        st.markdown("**Proponents:** Benefits / stability  \n**Critics:** Costs / risks")

with tab5:
    st.header("📰 Latest News")
    st.info("Get free key at https://newsapi.org")
    api_key = st.text_input("News API Key (optional)", type="password")
    query = st.text_input("Search", "geopolitics")
    if st.button("Fetch News") and api_key:
        try:
            resp = requests.get(f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&apiKey={api_key}&pageSize=6").json()
            for article in resp.get("articles", []):
                st.markdown(f"**{article['title']}**\n{article.get('description','')}\n[Read]({article['url']})")
        except:
            st.error("Could not fetch news.")

with tab6:
    st.header("📝 My Research Notes")
    notes = st.text_area("Your thoughts, sources, analysis...", value=data.get("notes", ""), height=400)
    if st.button("💾 Save Notes"):
        data["notes"] = notes
        save_data(data)
        st.success("Notes saved!")
    if st.button("📤 Export Notes"):
        st.download_button("Download", notes, "alethia_notes.txt")

st.sidebar.success("🌍 Alethia")
