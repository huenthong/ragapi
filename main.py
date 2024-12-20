import streamlit as st
import requests
import openai
import time
import json

# OpenAI API Key
openai.api_key = st.secrets["mykey"]

st.title("RAG LLM")

# Sidebar: Server URL Configuration
st.sidebar.header("Server Configuration")
if "public_url" not in st.session_state:
    st.session_state["public_url"] = ""

entered_url = st.sidebar.text_input("Enter Server URL", placeholder="https://your-server-url")
if st.sidebar.button("Submit URL"):
    if entered_url.strip():
        st.session_state["public_url"] = entered_url.strip()
        st.sidebar.success(f"Server URL set to: {st.session_state['public_url']}")
    else:
        st.sidebar.error("Please enter a valid server URL.")

# Sidebar: Parameter Configuration
st.sidebar.header("Parameter Configuration")
temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.5, 0.01)
k = st.sidebar.number_input("Top-k", min_value=1, max_value=50, value=10)
overlapping = st.sidebar.number_input("Overlapping Words", min_value=0, max_value=100, value=5)
rerank_method = st.sidebar.selectbox("Rerank Method", ["similarity", "importance"])
index_type = st.sidebar.selectbox("Index Type", ["basic", "rerank"])

# Input for custom keywords (optional)
keywords_input = st.sidebar.text_area("Custom Keywords (Optional)", "")
keywords = [keyword.strip() for keyword in keywords_input.split(",") if keyword.strip()] if keywords_input else None

# Display selected parameters
st.sidebar.subheader("Selected Parameters")
st.sidebar.write({
    "Temperature": temperature,
    "Top-k": k,
    "Overlapping": overlapping,
    "Rerank Method": rerank_method,
    "Index Type": index_type,
    "Keywords": keywords or "None"
})

# Configure parameters on the server
if st.sidebar.button("Set Parameters"):
    if not st.session_state["public_url"]:
        st.sidebar.error("Please set the server URL first.")
    else:
        try:
            response = requests.post(f"{st.session_state['public_url']}/set-parameters", json={
                "temperature": temperature,
                "k": k,
                "chunk_overlap": overlapping,
                "rerank_method": rerank_method,
                "index": index_type,
                "keywords": keywords  # Include keywords if provided
            })
            response_data = response.json()
            st.sidebar.success("Parameters updated successfully!")
            st.sidebar.write("Server Response:", response_data)
        except requests.exceptions.RequestException as e:
            st.sidebar.error(f"Request Error: {e}")
        except requests.JSONDecodeError:
            st.sidebar.error("Failed to decode JSON from server response.")
            st.sidebar.write("Raw Response Text:", response.text)

# Conversational History and Query Interface
st.header("Query Interface")
if "conversation" not in st.session_state:
    st.session_state["conversation"] = []

user_query = st.text_input("Enter your query:")
if st.button("Submit Query"):
    if not st.session_state["public_url"]:
        st.error("Please set the server URL first.")
    elif user_query.strip():  # Ensure the query is not empty
        st.session_state["conversation"].append(user_query)

        # Make the API call with retry logic
        max_retries = 3
        retry_delay = 5  # Seconds
        for attempt in range(max_retries):
            try:
                # Send both `query` and `keywords` in the JSON body
                response = requests.post(f"{st.session_state['public_url']}/query", json={
                    "query": user_query,
                    "keywords": keywords or []  # Ensure keywords is a valid list, default to empty
                })

                if response.status_code == 200:
                    data = response.json()

                    # Extract and format the answer
                    answer = data.get("answer", "No answer found.")
                    references = data.get("references", [])
                    chunks = data.get("chunks", [])

                    # Display the formatted output
                    st.write("### Answer")
                    st.write(f"{answer}")

                    if references:
                        st.write("\n### References")
                        for ref in references:
                            st.markdown(f"- {ref} pg xxx")

                    if chunks:
                        st.write("\n### Supporting Information")
                        for chunk in chunks:
                            index = chunk.get("index", "Unknown Index")
                            content = chunk.get("content", "No content available.").replace("\n", " ")
                            source = chunk.get("source", "Unknown Source")
                            keywords = ", ".join(chunk.get("keywords", [])) or "No keywords"
                            score = chunk.get("score", "No score")

                            st.markdown(f"""
                            - **Chunk {index}**: {content}
                              - Source: {source}
                              - Keywords: {keywords}
                              - Score: {score}
                            """)

                    break  # Exit retry loop on success
                else:
                    st.error(f"API Error: {response.status_code} {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Request Error: {e}")

            if attempt < max_retries - 1:
                st.warning(f"Retrying in {retry_delay} seconds... (Attempt {attempt + 2}/{max_retries})")
                time.sleep(retry_delay)
        else:
            st.error("Failed to fetch the response after multiple retries.")
    else:
        st.warning("Please enter a query before submitting.")

# Fetch and Display Query History
def fetch_history():
    try:
        response = requests.get(f"{st.session_state['public_url']}/history")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch history. Status code: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Request Error: {e}")
        return []

if st.button("Show History"):
    if not st.session_state["public_url"]:
        st.error("Please set the server URL first.")
    else:
        history = fetch_history()
        if history:
            st.write("### Query History (Last 10 Entries)")
            for i, entry in enumerate(history[:10], 1):  # Display up to 10 entries
                st.markdown(f"{i}. {entry}")
        else:
            st.info("No history available.")

# Clear conversation history
if st.button("Clear Conversation History"):
    if not st.session_state["public_url"]:
        st.error("Please set the server URL first.")
    else:
        try:
            # Call the server's clear history endpoint
            response = requests.post(f"{st.session_state['public_url']}/clear-history")
            if response.status_code == 200:
                st.session_state["conversation"] = []
                st.success("Conversation history cleared successfully!")
            else:
                st.error(f"Failed to clear server history. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            st.error(f"Request Error: {e}")

# Download history as JSON
def download_history():
    return json.dumps(st.session_state.get("conversation", []), indent=2)

if st.button("Download History as JSON"):
    history_json = download_history()
    st.download_button(
        label="Download History",
        data=history_json,
        file_name="conversation_history.json",
        mime="application/json"
    )

# Toggle conversation display
if st.checkbox("Show Conversation History"):
    if st.session_state["conversation"]:
        st.write("### Conversation History")
        for msg in st.session_state["conversation"]:
            st.markdown(f"- {msg}")
    else:
        st.info("No conversation history available.")


