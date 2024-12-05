import streamlit as st
import requests
import openai

# Define the server URL
public_url = "https://sad-readers-move.loca.lt"  

openai.api_key = st.secrets["mykey"]

st.title("Interactive Query System")

# Parameter Configuration
st.sidebar.header("Configuration")
temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.5, 0.01)
k = st.sidebar.number_input("Top-k", min_value=1, max_value=50, value=10)
overlapping = st.sidebar.number_input("Overlapping Words", min_value=0, max_value=100, value=5)
rerank_method = st.sidebar.selectbox("Rerank Method", ["similarity", "importance"])
index_type = st.sidebar.selectbox("Index Type", ["basic", "rerank"])

# Display user inputs
st.sidebar.subheader("Selected Parameters")
st.sidebar.write({
    "Temperature": temperature,
    "Top-k": k,
    "Overlapping": overlapping,
    "Rerank Method": rerank_method,
    "Index Type": index_type
})

# Configure parameters on server
if st.sidebar.button("Set Parameters"):
    response = requests.post(f"{public_url}/set-parameters", json={
        "temperature": temperature,
        "k": k,
        "chunk_overlap": overlapping,
        "rerank_method": rerank_method,
        "index": index_type
    })

    try:
        response_data = response.json()
        st.sidebar.write("Server Response:", response_data)
    except requests.JSONDecodeError:
        st.sidebar.error("Failed to decode JSON from server response.")
        st.sidebar.write("Raw Response Text:", response.text)

# Conversational History
st.header("Query Interface")
conversation = st.session_state.get("conversation", [])

user_query = st.text_input("Enter your query:")
if st.button("Submit Query"):
    if len(conversation) >= 10:
        conversation.pop(0)
    conversation.append(user_query)

    response = requests.post(f"{public_url}/query", params={"query": user_input})

if response.status_code == 200:
    data = response.json()
    st.write("Full response:", data)
    st.write("Answer:", data.get("answer", "No answer found in the response"))
else:
    st.write("API Error:", response.status_code, response.text)
