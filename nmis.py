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
st.sidebar.markdown("### Data View")
view_option = st.sidebar.radio(
    "Select data to display:",
    ["Calls", "Callers", "Both", "Markets"],
    index=0,
)

# ==================================================
# FILE LOADING
# ==================================================
DATA_DIR = "NMIS_Data"
CALLS_FILE = os.path.join(DATA_DIR, "calls.xlsx")
CALLERS_FILE = os.path.join(DATA_DIR, "callers.xlsx")
MARKETS_FILE = os.path.join(DATA_DIR, "markets.xlsx")

os.makedirs(DATA_DIR, exist_ok=True)

# Admin upload
if st.session_state["role"] == "admin":
    st.sidebar.markdown("### Upload Data")
    uploaded_calls = st.sidebar.file_uploader("Upload Calls Excel", type=["xlsx"])
    uploaded_callers = st.sidebar.file_uploader("Upload Callers Excel", type=["xlsx"])
    uploaded_markets = st.sidebar.file_uploader("Upload Markets Excel", type=["xlsx"])

    if uploaded_calls:
        with open(CALLS_FILE, "wb") as f:
            f.write(uploaded_calls.getbuffer())

    if uploaded_callers:
        with open(CALLERS_FILE, "wb") as f:
            f.write(uploaded_callers.getbuffer())

    if uploaded_markets:
        with open(MARKETS_FILE, "wb") as f:
            f.write(uploaded_markets.getbuffer())


calls_df = pd.read_excel(CALLS_FILE) if os.path.exists(CALLS_FILE) else pd.DataFrame()
caller_df = pd.read_excel(CALLERS_FILE) if os.path.exists(CALLERS_FILE) else pd.DataFrame()
markets_df = pd.read_excel(MARKETS_FILE) if os.path.exists(MARKETS_FILE) else pd.DataFrame()

if view_option in ["Calls", "Callers", "Both"] and (calls_df.empty or caller_df.empty):
    st.warning("Admin must upload Calls and Callers files once.")
    st.stop()

if view_option == "Markets" and markets_df.empty:
    st.warning("Admin must upload Markets file once.")
    st.stop()

# ==================================================
# DASHBOARD TITLE
# ==================================================
st.title("NMIS Livestock Call Dashboard")


# ==================================================
# DATA PREPARATION (SHARED)
# ==================================================
def prepare_long(df):
    df.columns = df.columns.astype(str).str.strip().str.replace("\n", "", regex=False)

    region_col = next((c for c in df.columns if c.lower() == "region"), None)
    if region_col is None:
        st.error("Region column not found")
        st.write("Columns:", df.columns.tolist())
        st.stop()

    months = [c for c in df.columns if c not in [region_col, "Total"]]

    for col in months:
        df[col] = (
            df[col].astype(str).str.replace(",", "", regex=False).pipe(pd.to_numeric, errors="coerce")
        )

    long_df = df.melt(
        id_vars=region_col,
        value_vars=months,
        var_name="Month",
        value_name="Value",
    )

    return long_df, region_col, months


# ==================================================
# CARDS (SINGLE VIEW ONLY)
# ==================================================
def show_cards(df, title):
    long_df, region_col, _ = prepare_long(df)

    totals = long_df.groupby(region_col)["Value"].sum().reset_index()
    grand_total = totals["Value"].sum()

    st.subheader(f"{title} Overview")

    st.markdown(
        f"""
        <div style="background-color:#2563eb;color:white;padding:16px;
        border-radius:12px;font-size:22px;text-align:center;margin-bottom:12px;">
            <b>Total {title}: {int(grand_total):,}</b>
        </div>
        """,
        unsafe_allow_html=True,
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
            unsafe_allow_html=True,
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
        key=f"{title}_regions",
    )

    filtered = long_df[long_df[region_col].isin(selected_regions)]

    st.subheader(f"{title} Comparison Chart")

    chart_type = st.radio(
        f"Chart Type for {title}:",
        ["Line", "Bar"],
        horizontal=True,
        key=f"{title}_chart",
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

    st.subheader(f"{title} Distribution")

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

    combined = pd.concat([calls_m, callers_m], ignore_index=True)

    month_order = ["September", "October", "November", "December", "January", "February"]

    def normalize_month(m):
        try:
            return pd.to_datetime(m, format="%B").strftime("%B")
        except Exception:
            try:
                return pd.to_datetime(m, format="%b").strftime("%B")
            except Exception:
                return str(m)

    combined["Month_norm"] = combined["Month"].apply(normalize_month)

    combined = combined[combined["Month_norm"].isin(month_order)]
    combined["Month_norm"] = pd.Categorical(
        combined["Month_norm"], categories=month_order, ordered=True
    )
    combined = combined.sort_values("Month_norm")

    st.subheader("Calls vs Callers (Monthly Trend)")

    fig = px.line(combined, x="Month_norm", y="Value", color="Type", markers=True)
    fig.update_xaxes(categoryorder="array", categoryarray=month_order)

    st.plotly_chart(fig, use_container_width=True)


# ==================================================
# MARKETS DASHBOARD
# ==================================================
def _find_col(columns, candidates):
    normalized = {str(c).strip().lower(): c for c in columns}
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in normalized:
            return normalized[key]
    return None


def prepare_markets(df):
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip().str.replace("\n", "", regex=False)

    location_col = _find_col(df.columns, ["Market Location", "Market", "Location"])
    total_col = _find_col(df.columns, ["Total Collected", "Total"])
    region_col = _find_col(df.columns, ["Region"])
    month_col = _find_col(df.columns, ["Month"])

    required = {
        "Market Location": location_col,
        "Total Collected": total_col,
        "Region": region_col,
        "Month": month_col,
    }

    missing = [k for k, v in required.items() if v is None]
    if missing:
        st.error(f"Markets file is missing required columns: {', '.join(missing)}")
        st.write("Found columns:", df.columns.tolist())
        st.stop()

    prepared = df[[location_col, total_col, region_col, month_col]].rename(
        columns={
            location_col: "Market Location",
            total_col: "Total Collected",
            region_col: "Region",
            month_col: "Month",
        }
    )

    prepared["Total Collected"] = (
        prepared["Total Collected"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
        .fillna(0)
    )

    for col in ["Market Location", "Region", "Month"]:
        prepared[col] = prepared[col].astype(str).str.strip()

    return prepared


def month_sort_key(month_text):
    try:
        return pd.to_datetime(month_text, format="%B %Y")
    except Exception:
        return pd.NaT


def markets_dashboard(df):
    if df.empty:
        st.warning("No markets data found. Upload markets.xlsx to continue.")
        return

    market_df = prepare_markets(df)

    st.subheader("Markets Overview")
    st.markdown(
        f"""
        <div style="background-color:#0ea5e9;color:white;padding:16px;
        border-radius:12px;font-size:22px;text-align:center;margin-bottom:12px;">
            <b>Total Collected (Markets): {int(market_df['Total Collected'].sum()):,}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

    region_options = sorted(market_df["Region"].dropna().unique().tolist())

    selected_regions = st.multiselect(
        "Filter Regions for Markets:",
        region_options,
        default=region_options,
        key="markets_regions",
    )

    filtered = market_df[market_df["Region"].isin(selected_regions)].copy()

    st.subheader("Markets Graph")
    month_region_market_counts = (
        filtered.groupby(["Month", "Region"], as_index=False)["Market Location"]
        .nunique()
        .rename(columns={"Market Location": "Market Places"})
    )
    month_region_market_counts["MonthSort"] = month_region_market_counts["Month"].map(month_sort_key)
    month_region_market_counts = month_region_market_counts.sort_values(["MonthSort", "Month", "Region"])

    fig = px.bar(
        month_region_market_counts,
        x="Month",
        y="Market Places",
        color="Region",
        barmode="stack",
        title="Number of Market Places by Month and Region",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Markets Pivot Table")
    all_regions = ["Oromia", "Afar", "Somali"]
    pivot_df = month_region_market_counts.pivot(
        index="Month", columns="Region", values="Market Places"
    )
    pivot_df = pivot_df.reindex(columns=all_regions, fill_value=0)
    pivot_df = pivot_df.fillna(0).astype(int).reset_index()
    pivot_df["MonthSort"] = pivot_df["Month"].map(month_sort_key)
    pivot_df = pivot_df.sort_values(["MonthSort", "Month"]).drop(columns=["MonthSort"])
    st.dataframe(pivot_df, use_container_width=True)


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

elif view_option == "Both":
    calls_vs_callers(calls_df.copy(), caller_df.copy())

else:  # Markets
    markets_dashboard(markets_df.copy())


# ==================================================
# TABLES
# ==================================================
st.write("---")
st.subheader("Data Tables")

if view_option in ["Calls", "Both"]:
    st.write("**Calls**")
    st.dataframe(calls_df, use_container_width=True)

if view_option in ["Callers", "Both"]:
    st.write("**Callers**")
    st.dataframe(caller_df, use_container_width=True)

if view_option == "Markets":
    st.write("**Markets**")
    markets_prepared = prepare_markets(markets_df.copy())
    markets_summary = (
        markets_prepared.groupby(["Month", "Region"], as_index=False)["Market Location"]
        .nunique()
        .rename(columns={"Market Location": "Market Places"})
    )
    markets_summary["MonthSort"] = markets_summary["Month"].map(month_sort_key)
    markets_summary = markets_summary.sort_values(["MonthSort", "Month", "Region"])
    st.dataframe(
        markets_summary[["Month", "Region", "Market Places"]],
        use_container_width=True,
    )
