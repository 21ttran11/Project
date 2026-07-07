import pandas as pd
import streamlit as st
import anthropic
import plotly.express as px

#PAGE SETUP
st.set_page_config(page_title="DONATIONS DASHBOARD", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    section[data-testid="stSidebar"] {
    min-width: 400px;
    max-width: 600px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Donations Dashboard 💵")
st.caption("Upload your donation data to visualize trends + Get insights with our chat~")

#THEMES
THEMES = {
    "Vintage Plum": {
        "colors": ["#542E71", "#6A66A3", "#84A9C0", "#B3CBB9", "#DDD8B8"],
        "line": "#6A66A3",
        "fill": "rgba(106, 102, 163, 0.25)",
        "scale": ["#DDD8B8", "#B3CBB9", "#84A9C0", "#6A66A3", "#542E71"],
    },
    "Ocean Teal": {
        "colors": ["#0D5C63", "#247B7B", "#44A1A0", "#78CDD7", "#FFFFFA"],
        "line": "#247B7B",
        "fill": "rgba(68, 161, 160, 0.25)",
        "scale": ["#78CDD7", "#44A1A0", "#247B7B", "#0D5C63"],
    },
    "Sunset Pop": {
        "colors": ["#E58C8A", "#EEC0C6", "#7EE8FA", "#80FF72", "#FFF07C"],
        "line": "#E58C8A",
        "fill": "rgba(126, 232, 250, 0.30)",
        "scale": ["#FFF07C", "#7EE8FA", "#EEC0C6", "#E58C8A"],
    },
}

theme_choice = st.sidebar.selectbox("🎨 Theme", list(THEMES.keys()))
theme = THEMES[theme_choice]

#LOAD DATA
uploaded = st.sidebar.file_uploader("Upload a donations CSV", type="csv")
st.sidebar.caption("Expected columns: donor_name, date, amount, campaign, payment_method")

if uploaded:
    df = pd.read_csv(uploaded)
else:
    st.sidebar.info("No file uploaded — using sample data.")
    df = pd.read_csv("sample_donations.csv")

df["date"] = pd.to_datetime(df["date"])
df["month"] = df["date"].dt.to_period("M").astype(str)

#BUILD DATA SUMMARY
def build_summary(df):
    """Summarize the dataset into a short text block Claude can reason over."""
    monthly = df.groupby("month")["amount"].sum().round(0).to_dict()
    campaigns = df.groupby("campaign")["amount"].sum().round(0).to_dict()

    #New vs Returning donors per month
    first_gift = df.groupby("donor_name")["date"].min()
    df2 = df.merge(first_gift.rename("first_gift"), on="donor_name")
    df2["donor_type"] = (df2["date"] == df2["first_gift"]).map({True: "new", False: "returning"})
    donor_mix = df2.groupby("donor_type")["amount"].sum().round(0).to_dict()

    return (
        f"Total raised: ${df['amount'].sum():,.0f} from {len(df)} donations "
        f"by {df['donor_name'].nunique()} unique donors. "
        f"Average gift: ${df['amount'].mean():,.2f}.\n"
        f"Monthly totals: {monthly}\n"
        f"Campaign totals: {campaigns}\n"
        f"New vs Returning donor revenue: {donor_mix}"
    )

#SEND PROMPT TO CLAUDE
def ask_claude(prompt):
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text

summary = build_summary(df)

#AI INSIGHTS
@st.cache_data(show_spinner="Analyzing...")
def get_briefing(summary):
    return ask_claude(
        "You are an advisor to a small nonprofit's executive director. "
        "Based on this donation data summary, write a short briefing (3-5 bullet points) "
        "highlighting key trends, risks, and one concrete recommendation. "
        "Be specific and plain-spoken.\n\n" + summary
    )

with st.expander("AI INSIGHTS", expanded=True):
    st.info(get_briefing(summary))

#METRICS
total = df["amount"].sum()
num_donations = len(df)
num_donors = df["donor_name"].nunique()
avg_gift = df["amount"].mean()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Raised", f"${total:,.0f}")
col2.metric("Donations", f"{num_donations:,}")
col3.metric("Unique Donors", f"{num_donors:,}")
col4.metric("Average", f"${avg_gift:,.2f}")

#CHARTS
left, right = st.columns(2)

with left:
    st.subheader("Monthly Donation Trend")
    monthly = df.groupby("month")["amount"].sum().reset_index()
    fig = px.area(monthly, x="month", y="amount")
    fig.update_traces(
        line_color=theme["line"],
        fillcolor=theme["fill"],
        hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title=None, yaxis_title=None,
        yaxis_tickprefix="$",
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Donations by Payment Method")
    by_method = df.groupby("payment_method")["amount"].sum().reset_index()
    fig = px.pie(
        by_method, names="payment_method", values="amount",
        hole=0.5,
        color_discrete_sequence=theme["colors"],
    )
    fig.update_traces(hovertemplate="%{label}<br>$%{value:,.0f}<extra></extra>")
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=320)
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Top Campaigns")
    by_campaign = (
        df.groupby("campaign")["amount"].sum()
        .sort_values(ascending=True).reset_index()
    )
    fig = px.bar(
        by_campaign, x="amount", y="campaign",
        orientation="h",
        color="amount",
        color_continuous_scale=theme["scale"],
    )
    fig.update_traces(hovertemplate="%{y}<br>$%{x:,.0f}<extra></extra>")
    fig.update_layout(
        coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title=None, yaxis_title=None,
        xaxis_tickprefix="$",
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 10 Donors")
    top_donors = (
        df.groupby("donor_name")["amount"].sum()
        .sort_values(ascending=False).head(10).reset_index()
    )
    top_donors.columns = ["Donor", "Total Given"]
    st.dataframe(
        top_donors, hide_index=True, use_container_width=True,
        column_config={
            "Total Given": st.column_config.ProgressColumn(
                "Total Given",
                format="$%d",
                min_value=0,
                max_value=int(top_donors["Total Given"].max()),
            )
        },
        height=320,
    )

#CLAUDE CHATBOT CALL
system_prompt = (
    "You are a donation data analyzing chatbot for a nonprofit. "
    "Answer questions using ONLY this donation data summary. "
    "If the summary does not contain enough information, say so. "
    "Keep answers to 2-3 sentences.\n\n"
    f"Data summary:\n{summary}"
)

def chat_with_claude(messages):
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text

#CHATBOT
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Welcome to the data chatbot! Ask me anything about your donations data ☺️"}
    ]

with st.sidebar:
    st.divider()
    st.subheader("💬 Data Chat")

    with st.container(height=300):
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    user_question = st.chat_input("Ask about your data...")

if user_question:
    st.session_state.chat_history.append({"role": "user", "content": user_question})

    api_messages = [
        m for m in st.session_state.chat_history
        if m["content"] and m["role"] in ("user", "assistant")
    ][1:]

    with st.spinner("Thinking..."):
        answer = chat_with_claude(api_messages)

    st.session_state.chat_history.append({"role": "assistant", "content": answer})
    st.rerun()