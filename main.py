import streamlit as st
import requests
import openai
import time
import json
from datetime import datetime

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
rerank_method = st.sidebar.selectbox("Rerank Method", ["similarity", "keyword"])
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
                "keywords": keywords
            })
            response_data = response.json()
            st.sidebar.success("Parameters updated successfully!")
            st.sidebar.write("Server Response:", response_data)
        except requests.exceptions.RequestException as e:
            st.sidebar.error(f"Request Error: {e}")
        except requests.JSONDecodeError:
            st.sidebar.error("Failed to decode JSON from server response.")
            st.sidebar.write("Raw Response Text:", response.text)

# Query Interface
st.header("Query Interface")
if "conversation" not in st.session_state:
    st.session_state["conversation"] = []

user_query = st.text_input("Enter your query:")

def display_conversation_entry(entry):
    with st.container():
        st.write("---")
        st.write(f"**Timestamp:** {entry.get('timestamp', 'No timestamp')}")
        st.write(f"**Query:** {entry.get('query', 'No query')}")
        st.write(f"**Answer:** {entry.get('answer', 'No answer')}")
        
        if chunks := entry.get('chunks', []):
            st.write("**Supporting Chunks:**")
            for chunk in chunks:
                with st.expander(f"Chunk {chunk.get('chunk_id', 'Unknown ID')}"):
                    st.write(f"**Content:** {chunk.get('content', 'No content')}")
                    st.write(f"**Source:** {chunk.get('source', 'Unknown source')}")
                    st.write(f"**Keywords found:** {', '.join(chunk.get('keywords', [])) or 'None'}")
                    st.write(f"**Score:** {chunk.get('score', 'No score'):.4f}")

# Submit Query Button
if st.button("Submit Query"):
    if not st.session_state["public_url"]:
        st.error("Please set the server URL first.")
    elif user_query.strip():
        with st.spinner('Processing your query...'):
            try:
                response = requests.post(
                    f"{st.session_state['public_url']}/query",
                    json={"query": user_query, "keywords": keywords or []}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    st.session_state["conversation"].append(data)
                    
                    # Display the latest response
                    st.write("### Latest Response")
                    display_conversation_entry(data)
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Request Error: {e}")
    else:
        st.warning("Please enter a query before submitting.")

# Conversation History Display
if st.checkbox("Show Conversation History"):
    st.write("### Full Conversation History")
    if st.session_state["conversation"]:
        for entry in reversed(st.session_state["conversation"]):
            display_conversation_entry(entry)
    else:
        st.info("No conversation history available.")

# Clear History Button
if st.button("Clear Conversation History"):
    if not st.session_state["public_url"]:
        st.error("Please set the server URL first.")
    else:
        try:
            response = requests.post(f"{st.session_state['public_url']}/clear-history")
            if response.status_code == 200:
                st.session_state["conversation"] = []
                st.success("Conversation history cleared successfully!")
            else:
                st.error(f"Failed to clear history. Status code: {response.status_code}")
                st.error(f"Error message: {response.text}")
        except requests.exceptions.RequestException as e:
            st.error(f"Request Error: {e}")

# Download History Button
if st.button("Download History"):
    if st.session_state["conversation"]:
        # Convert the conversation history to a JSON string
        history_json = json.dumps(st.session_state["conversation"], indent=2)
        # Create a download button
        st.download_button(
            label="Download Conversation History",
            data=history_json,
            file_name=f"conversation_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    else:
        st.warning("No conversation history available to download.")

# Reload Documents Button
if st.button("Reload Documents"):
    if not st.session_state["public_url"]:
        st.error("Please set the server URL first.")
    else:
        try:
            response = requests.post(f"{st.session_state['public_url']}/reload-documents")
            if response.status_code == 200:
                st.success("Documents reloaded successfully!")
            else:
                st.error(f"Failed to reload documents. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            st.error(f"Request Error: {e}")
