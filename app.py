import pandas as pd
import streamlit as st
from st_chat_message import message
import anthropic 

#PAGE SETUP
st.set_page_config(page_title="DONATIONS DASHBOARD", page_icon="📊", layout="wide")
st.title("📊 Donations Dashboard 💵")
st.caption("Upload your donation data to visualize trends + Get insights with our chat~")

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

#METRICS
total = df["amount"].sum()
num_donations = len(df)
num_donors = df["donor_name"].nunique()
avg_gift = df["amount"].mean()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Raised", f"${total:,.0f}")
col2.metric("Donations", f"{num_donations:,}")
col3.metric("Unique Donars", f"{num_donors:,}")
col4.metric("Average", f"${avg_gift:,.2f}")

#CHARTS
left,right = st.columns(2)

with left:
    st.subheader("Monthly Donation Trend")
    monthly = df.groupby("month")["amount"].sum()
    st.line_chart(monthly)

    st.subheader("Donations by Payment Method")
    by_method = df.groupby("payment_method")["amount"].sum().sort_values()
    st.bar_chart(by_method)

with right:
    st.subheader("Top Campaigns")
    by_campaign = df.groupby("campaign")["amount"].sum().sort_values(ascending=False)
    st.bar_chart(by_campaign)

    st.subheader("Top 10 Donors")
    top_donors = (
        df.groupby("donor_name")["amount"].sum().sort_values(ascending=False).head(10).reset_index()
    )
    top_donors.columns = ["Donar", "Total Given"]
    st.dataframe(top_donors, hide_index=True, use_container_width=True)

#BUILD DATA SUMMARY
def build_summary(df):
    """Summarize the dataset into a short text block Claude can reason over."""
    monthly = df.groupby("month")["amount"].sum().round(0).to_dict()
    campaigns = df.groupby("campaign")["amount"].sum().round(0).to_dict()

    #New vs Returning donors per month
    first_gift = df.groupby("donor_name")["date"].min()
    df2 = df.merge(first_gift.rename("first_gift"), on = "donor_name")
    df2["donor_type"] = (df2["date"] == df2["first_gift"]).map({True: "new", False: "returning"})
    donor_mix = df2.groupby("donor_type")["amount"].sum().round(0).to_dict()

    return (
        f"Total raised: ${df['amount'].sum():,.0f} from {len(df)} donations."
        f"by {df['donor_name'].nunique()} unique donors."
        f"Average gift: ${df['amount'].mean():,.2f}.\n"
        f"Monthly totals: {monthly}\n"
        f"Campaign totals: {campaigns}\n"
        f"New vs Returning donor revenue: {donor_mix}"
    )

#SEND PROMPT TO CAUDE 
def ask_claude(prompt):
    client = anthropic.Anthropic(api_key = st.secrets["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model = "claude-sonnet-4-5",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text

summary = build_summary(df)

#AI INSIGHTS
st.divider()
st.header("AI INSIGHTS")
briefing = ask_claude(
    "You are an advisor to a small nonprofit's executive director. "
    "Based on this donation data summary, write a short briefing (3-5 bullet points) "
    "highlighting key trends, risks, and one concrete recommendation "
    "Be specific and plain-spoken. \n\n" + str(summary)
)
st.markdown(briefing)

#CHATBOT
st.header("DATA CHAT 💬")
system_prompt = """You are a donation data analyzing chat bot. 
                    Your job is to answer questions and offer additional help.
                    Answer their inquiries with ONLY this donation 
                    entry summary. If the summary does not contain
                    enough information to answer, say so. 
                    f"Data summary:\n{summary}\n\nQuestion: {question}"""

first_message = "Welcome to the data chatbot! Ask me anything about your donations data ☺️"

with st.form("input"):
    message = st.text_input("Ask a question.")
    submitted = st.form_submit_button("Submit")
    if submitted and message != "":
        pass

