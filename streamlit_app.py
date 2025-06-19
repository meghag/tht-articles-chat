import streamlit as st
from datetime import datetime
import subprocess
import calendar
import time
import json
import re
import os


def run_script_with_output(command, label):
    st.markdown(f"**{label}**")
    with st.expander("Logs:", expanded=False):
        log_area = st.empty()
        log = ""
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for line in iter(process.stdout.readline, ""):
            log += "\n\n" + line
            log_area.markdown(
                f"""
                <div style="background-color:#f0f2f6; padding:10px; height:300px; overflow-y:scroll; font-family:monospace; font-size:13px; border-radius:4px;">
                    <pre>{log}</pre>
                </div>
                """,
                unsafe_allow_html=True,
            )
        process.stdout.close()
        process.wait()


st.set_page_config(page_title="EcoSearch", layout="centered")

st.title("🌱 Environment Conservation Search Tool")

# --- Search Phrase ---
# st.markdown("🔍 **Enter the Search Phrase**")
search_phrase = st.text_input(
    "🔍 **Enter the topic to search news and research articles on**"
)

# --- Date Range Selection ---
st.markdown("**Select the Time Range (within last 5 years)**")

# Get current year and month
today = datetime.now()
current_year = today.year
years = [str(y) for y in range(current_year, current_year - 5, -1)]
# month_names = list(calendar.month_name)[1:]  # Skip empty string at index 0
month_names_abbr = list(calendar.month_abbr)[1:]  # 3-letter names

# Start Date
# st.markdown("**Specify the timeframe**")
# start_col1, start_col2 = st.columns(2)
start_col1, start_col2, to_col, end_col1, end_col2 = st.columns(5)
with start_col1:
    start_month_name = st.selectbox("Start Month", month_names_abbr, key="start_month")
with start_col2:
    start_year = st.selectbox("Start Year", years, key="start_year")
start_month = f"{month_names_abbr.index(start_month_name) + 1:02d}"

# End Date
# st.markdown("**End Date**")
# end_col1, end_col2 = st.columns(2)
with end_col1:
    end_month_name = st.selectbox("End Month", month_names_abbr, key="end_month")
with end_col2:
    end_year = st.selectbox("End Year", years, key="end_year")
end_month = f"{month_names_abbr.index(end_month_name) + 1:02d}"

# Mandatory Keywords
mandatory_keywords = st.text_input(
    "🔍 **Enter the keywords that must be present in all research articles (separated by commas)**"
)

# --- Optional Data Source ---
st.markdown("**OR**")
data_source = st.text_input(
    "📁 Optional Data Source (local path, web URL, or Google Drive link)"
)

data_source_name = st.text_input(
    "Enter an understandable name for the data source with no special characters (eg., Neeraj biodiversity reports)"
)

# Placeholder for status and chatbot
status_placeholder = st.empty()
# chatbot_placeholder = st.empty()
# Always mount the chatbot interface
chatbot_placeholder = st.container()

# Initialize chat history
if "data_source_type" not in st.session_state:
    st.session_state.data_source_type = ""

if "collection_name_prefix" not in st.session_state:
    st.session_state.collection_name_prefix = ""

# --- Submit Button ---
if st.button("Build Q&A Chatbot"):
    if (not search_phrase) and (not data_source):
        st.warning("Please enter a search phrase or a data source.")
    elif data_source and (not data_source_name):
        st.warning(
            "Please enter a short and easy-to-understand name for this data source."
        )
    elif (
        data_source
        and data_source_name
        and (not re.match(r"^[a-zA-Z0-9 ]+$", data_source_name))
    ):
        # Validate the name: only allow alphanumeric and space (adjust pattern if needed)
        st.warning(
            "❌ The name should contain only letters, numbers, and spaces. No special characters allowed."
        )
    else:
        config = {
            "search_phrase": search_phrase,
            "start_date": f"{start_year}-{start_month}",
            "end_date": f"{end_year}-{end_month}",
            "data_source": data_source.strip() or None,
        }

        try:
            with status_placeholder.container():
                st.info("🔄 Initializing pipeline...")
                time.sleep(1)

            if config["data_source"]:
                st.info("📁 Running alternate script for custom data source...")
                st.session_state.data_source_type = "link"

                collection_name_prefix = "_".join(data_source_name.lower().split())
                st.session_state.collection_name_prefix = collection_name_prefix
                time.sleep(1)

                inputs = {
                    "data_source": config["data_source"],
                    # "dirname": os.path.join("results"),
                    "vectordb_collection_name": collection_name_prefix,
                }
                run_script_with_output(
                    ["python3", "src/custom_data_ingest.py", json.dumps(inputs)],
                    label="📚 Embedding the docs at the given link...",
                )
            else:
                st.session_state.data_source_type = "news_scholar"

                keywords = [word for word in search_phrase.split() if len(word) > 2]
                if mandatory_keywords:
                    keywords = [word.strip() for word in mandatory_keywords.split(",")]

                main_dirname = f"{'_'.join(keywords)}"
                collection_name_prefix = f"{main_dirname}_{start_month_name}{start_year}_{end_month_name}{end_year}"
                st.session_state.collection_name_prefix = collection_name_prefix

                # st.info("📰 Scraping news articles...")
                time.sleep(1)
                google_news_inputs = {
                    "keyphrase": search_phrase,
                    "dirname": f"{main_dirname}/news",
                    "start_month_year": f"{start_month_name} {start_year}",  # 'MMM YYYY'
                    "end_month_year": f"{end_month_name} {end_year}",  # 'MMM YYYY'
                    "vectordb_collection_name": f"{collection_name_prefix}_news",
                }

                output_news = run_script_with_output(
                    [
                        "python3",
                        "src/google_news_v1.py",
                        json.dumps(google_news_inputs),
                    ],
                    # capture_output=True,
                    # text=True,
                    label="📰 Scraping news articles...",
                )
                # print("Output:", output_news.stdout)
                # print("Error:", output_news.stderr)

                # st.info("📚 Scraping research articles...")
                time.sleep(1)

                google_scholar_inputs = {
                    "keyphrase": search_phrase,
                    "dirname": f"{main_dirname}/scholar",
                    "mandatory_keywords": keywords,  # specify the keywords that MUST be present in the title
                    "start_year": int(start_year),
                    "end_year": int(end_year),
                    "vectordb_collection_name": f"{collection_name_prefix}_scholar",
                }
                output_scholar = run_script_with_output(
                    [
                        "python3",
                        "src/google_scholar_v1.py",
                        json.dumps(google_scholar_inputs),
                    ],
                    # capture_output=True,
                    # text=True,
                    label="📚 Scraping research articles...",
                )
                # print("Output:", output_scholar.stdout)
                # print("Error:", output_scholar.stderr)

            st.success("✅ Pipeline execution completed successfully.")
            st.session_state.pipeline_success = True

        except Exception as e:
            st.error(f"An error occurred: {e}")

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# if "chat_input" not in st.session_state:
#     st.session_state.chat_input = ""

if "pipeline_success" not in st.session_state:
    st.session_state.pipeline_success = False  # Set to True after pipeline finishes


# ---- Helper function to handle submission ----
def submit_question(rag_inputs):
    try:
        result = subprocess.run(
            ["python3", "src/rag_query.py", json.dumps(rag_inputs)],
            capture_output=True,
            text=True,
            check=True,
        )
        bot_reply = result.stdout.strip()
    except subprocess.CalledProcessError as e:
        bot_reply = (
            f"Error: {e.stderr.strip() if e.stderr else 'Something went wrong.'}"
        )

    # Append to chat history
    st.session_state.chat_history.insert(0, ("EcoBot", bot_reply))
    st.session_state.chat_history.insert(0, ("You", user_input))

    # Clear input indirectly via session_state update (NOT directly overwriting it)
    # st.session_state.chat_input = ""


# Display chatbot interface
st.markdown("---")
st.markdown("### 🤖 Chat with the Documents")

if st.session_state.pipeline_success:
    # Form for new message
    with st.form("chat_form"):
        st.text_input("Type your question here:", key="chat_input")
        submitted = st.form_submit_button("Send")

        if submitted:
            user_input = st.session_state.chat_input.strip()

            if user_input:
                rag_inputs = {
                    "question": user_input,
                    "data_source": st.session_state.data_source_type,
                    "collection_name_prefix": st.session_state.collection_name_prefix,
                }
                submit_question(rag_inputs)

                # Display chat history
                for sender, message in st.session_state.chat_history:
                    st.markdown(f"**{sender}:** {message}")
else:
    st.info(
        "Please provide a topic or link to your documents to start chatting with EcoBot."
    )
