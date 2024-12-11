import streamlit as st
import requests
import openai
import time

# Define the server URL
public_url = "https://ready-papers-do.loca.lt"

# OpenAI API Key
openai.api_key = st.secrets["mykey"]

st.title("RAG LLM")

# Parameter Configuration
st.sidebar.header("Configuration")
temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.5, 0.01)
k = st.sidebar.number_input("Top-k", min_value=1, max_value=50, value=10)
overlapping = st.sidebar.number_input("Overlapping Words", min_value=0, max_value=100, value=5)
rerank_method = st.sidebar.selectbox("Rerank Method", ["similarity", "importance"])
index_type = st.sidebar.selectbox("Index Type", ["basic", "rerank"])

# Input for custom keywords (optional)
keywords_input = st.sidebar.text_area("Custom Keywords (Optional)", "")
keywords = [keyword.strip() for keyword in keywords_input.split(",") if keyword.strip()] if keywords_input else None

# Display user inputs
st.sidebar.subheader("Selected Parameters")
st.sidebar.write({
    "Temperature": temperature,
    "Top-k": k,
    "Overlapping": overlapping,
    "Rerank Method": rerank_method,
    "Index Type": index_type,
    "Keywords": keywords or "None"
})

# Configure parameters on server
if st.sidebar.button("Set Parameters"):
    try:
        response = requests.post(f"{public_url}/set-parameters", json={
            "temperature": temperature,
            "k": k,
            "chunk_overlap": overlapping,
            "rerank_method": rerank_method,
            "index": index_type,
            "keywords": keywords  # Include keywords only if provided
        })
        response_data = response.json()
        st.sidebar.write("Server Response:", response_data)
    except requests.exceptions.RequestException as e:
        st.sidebar.error(f"Request Error: {e}")
    except requests.JSONDecodeError:
        st.sidebar.error("Failed to decode JSON from server response.")
        st.sidebar.write("Raw Response Text:", response.text)

# Conversational History
st.header("Query Interface")
if "conversation" not in st.session_state:
    st.session_state["conversation"] = []

user_query = st.text_input("Enter your query:")
if st.button("Submit Query"):
    if user_query.strip():  # Ensure the query is not empty
        st.session_state["conversation"].append(user_query)

        # Make the API call with retry logic
        max_retries = 3
        retry_delay = 5  # Seconds
        for attempt in range(max_retries):
            try:
                response = requests.post(f"{public_url}/query", params={"query": user_query})
                if response.status_code == 200:
                    data = response.json()
                    # Format the output
                    answer = data.get("answer", "No answer found.")
                    references = data.get("references", [])
                    chunks = data.get("chunks", [])
                    
                    # Create a readable output
                    st.write("### Answer")
                    st.write(answer)
                    
                    if references:
                        st.write("\n### References")
                        for ref in references:
                            st.write(f"- {ref}")
                    
                    if chunks:
                        st.write("\n### Supporting Chunks")
                        for chunk in chunks:
                            content = chunk.get("content", "")
                            source = chunk.get("source", "Unknown Source")
                            st.write(f"- From `{source}`: {content}")
                    
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


