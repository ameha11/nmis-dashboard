import streamlit as st
import pandas as pd
import plotly.express as px
import os
from login import login

# ==================================================
# LOGIN CHECK
# ==================================================
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    login()

st.sidebar.success(
    f"Logged in as: {st.session_state['user']} ({st.session_state['role']})"
)

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()
# ==================================================
# SIDEBAR VIEW SELECTOR
# ==================================================
st.sidebar.markdown("### 🔎 Data View")
view_option = st.sidebar.radio(
    "Select data to display:",
    ["Calls", "Callers", "Both"],
    index=0
)

# ==================================================
# FILE LOADING 
# ==================================================

DATA_DIR = "NMIS_Data"
CALLS_FILE = os.path.join(DATA_DIR, "calls.xlsx")
CALLERS_FILE = os.path.join(DATA_DIR, "callers.xlsx")

os.makedirs(DATA_DIR, exist_ok=True)

# Admin upload
if st.session_state["role"] == "admin":
    uploaded_calls = st.file_uploader("📁 Upload Calls Excel", type=["xlsx"])
    uploaded_callers = st.file_uploader("📁 Upload Callers Excel", type=["xlsx"])

    if uploaded_calls:
        with open(CALLS_FILE, "wb") as f:
            f.write(uploaded_calls.getbuffer())
        

    if uploaded_callers:
        with open(CALLERS_FILE, "wb") as f:
            f.write(uploaded_callers.getbuffer())
        



# Load saved files
if not os.path.exists(CALLS_FILE) or not os.path.exists(CALLERS_FILE):
    st.warning("⚠️ Admin must upload Calls and Callers files once.")
    st.stop()

calls_df = pd.read_excel(CALLS_FILE)
caller_df = pd.read_excel(CALLERS_FILE)


# ==================================================
# DASHBOARD TITLE
# ==================================================
st.title("📊 NMIS Livestock Call Dashboard")

# ==================================================
# DATA PREPARATION (SHARED)
# ==================================================
def prepare_long(df):
    df.columns = df.columns.astype(str).str.strip().str.replace("\n", "", regex=False)

    region_col = next((c for c in df.columns if c.lower() == "region"), None)
    if region_col is None:
        st.error("❌ Region column not found")
        st.write("Columns:", df.columns.tolist())
        st.stop()

    months = [c for c in df.columns if c not in [region_col, "Total"]]

    for col in months:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .pipe(pd.to_numeric, errors="coerce")
        )

    long_df = df.melt(
        id_vars=region_col,
        value_vars=months,
        var_name="Month",
        value_name="Value"
    )

    return long_df, region_col, months

# ==================================================
# CARDS (SINGLE VIEW ONLY)
# ==================================================
def show_cards(df, title):
    long_df, region_col, _ = prepare_long(df)

    totals = long_df.groupby(region_col)["Value"].sum().reset_index()
    grand_total = totals["Value"].sum()

    st.subheader(f"🔢 {title} Overview")

    st.markdown(
        f"""
        <div style="background-color:#2563eb;color:white;padding:16px;
        border-radius:12px;font-size:22px;text-align:center;margin-bottom:12px;">
            <b>Total {title}: {int(grand_total):,}</b>
        </div>
        """,
        unsafe_allow_html=True
    )

    cols = st.columns(len(totals))
    for i, row in totals.iterrows():
        cols[i].markdown(
            f"""
            <div style="background-color:#10b981;color:white;padding:14px;
            border-radius:10px;text-align:center;font-size:17px;">
                <b>{row[region_col]}</b><br>
                <span style="font-size:20px;">{int(row['Value']):,}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

# ==================================================
# COMPARISON CHART (BAR / LINE)
# ==================================================
def comparison_chart(df, title):
    long_df, region_col, _ = prepare_long(df)

    regions = long_df[region_col].unique().tolist()
    selected_regions = st.multiselect(
        f"Filter Regions for {title}:",
        regions,
        default=regions,
        key=f"{title}_regions"
    )

    filtered = long_df[long_df[region_col].isin(selected_regions)]

    st.subheader(f"📊 {title} Comparison Chart")

    chart_type = st.radio(
        f"Chart Type for {title}:",
        ["Line", "Bar"],
        horizontal=True,
        key=f"{title}_chart"
    )

    if chart_type == "Bar":
        fig = px.bar(filtered, x="Month", y="Value", color=region_col, barmode="group")
    else:
        fig = px.line(filtered, x="Month", y="Value", color=region_col, markers=True)

    st.plotly_chart(fig, use_container_width=True)

# ==================================================
# PIE CHARTS
# ==================================================
def pie_charts(df, title):
    long_df, region_col, _ = prepare_long(df)

    st.subheader(f"🥧 {title} Distribution")

    col1, col2 = st.columns(2)

    region_sum = long_df.groupby(region_col)["Value"].sum().reset_index()
    month_sum = long_df.groupby("Month")["Value"].sum().reset_index()

    fig_region = px.pie(region_sum, names=region_col, values="Value", title="By Region")
    fig_month = px.pie(month_sum, names="Month", values="Value", title="By Month")

    col1.plotly_chart(fig_region, use_container_width=True)
    col2.plotly_chart(fig_month, use_container_width=True)

# ==================================================
# CALLS VS CALLERS COMPARISON
# ==================================================
def calls_vs_callers(calls_df, caller_df):
    calls_long, _, _ = prepare_long(calls_df)
    callers_long, _, _ = prepare_long(caller_df)

    calls_m = calls_long.groupby("Month")["Value"].sum().reset_index()
    calls_m["Type"] = "Calls"

    callers_m = callers_long.groupby("Month")["Value"].sum().reset_index()
    callers_m["Type"] = "Callers"

    combined = pd.concat([calls_m, callers_m])

    st.subheader("📈 Calls vs Callers (Monthly Trend)")

    fig = px.line(combined, x="Month", y="Value", color="Type", markers=True)
    st.plotly_chart(fig, use_container_width=True)


# ==================================================
# DASHBOARD LAYOUT
# ==================================================
if view_option == "Calls":
    show_cards(calls_df.copy(), "Calls")
    comparison_chart(calls_df.copy(), "Calls")
    pie_charts(calls_df.copy(), "Calls")

elif view_option == "Callers":
    show_cards(caller_df.copy(), "Callers")
    comparison_chart(caller_df.copy(), "Callers")
    pie_charts(caller_df.copy(), "Callers")

else:  # BOTH
    calls_vs_callers(calls_df.copy(), caller_df.copy())


# ==================================================
# TABLES
# ==================================================
st.write("---")
st.subheader("📄 Data Tables")

if view_option in ["Calls", "Both"]:
    st.write("**Calls**")
    st.dataframe(calls_df, use_container_width=True)

if view_option in ["Callers", "Both"]:
    st.write("**Callers**")
    st.dataframe(caller_df, use_container_width=True)
