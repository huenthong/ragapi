import streamlit as st
import requests

# Define the server URL
public_url = "https://major-moons-stare.loca.lt"  # Replace with your Colab server URL

# Streamlit App
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
        "overlapping": overlapping,
        "rerank_method": rerank_method,
        "index": index_type
    })
    st.sidebar.write("Server Response:", response.json())

# Conversational History
st.header("Query Interface")
st.text("Include up to 10 previous queries for context.")
conversation = st.session_state.get("conversation", [])

user_query = st.text_input("Enter your query:")
if st.button("Submit Query"):
    # Maintain conversational history
    if len(conversation) >= 10:
        conversation.pop(0)
    conversation.append(user_query)

    # Send the query to the server
    response = requests.post(f"{public_url}/query", params={
        "query": user_query,
        "history": conversation
    })
    data = response.json()

    # Display the response
    st.subheader("Response")
    st.write(data)

    # Chunk display with keywords
    st.subheader("Chunks with Keywords")
    chunks = data.get("chunks", [])
    for chunk in chunks:
        st.write(f"**Text:** {chunk['text']}  \n**Keywords:** {chunk['keywords']}")

    # Sorted chunks
    st.subheader("Sorted Chunks by Importance")
    sorted_chunks = sorted(chunks, key=lambda x: x.get('importance', 0), reverse=True)
    for chunk in sorted_chunks:
        st.write(f"**Text:** {chunk['text']}  \n**Importance:** {chunk['importance']}")

    # Reranked unique chunks
    st.subheader("Reranked Unique Chunks")
    unique_chunks = []
    seen_texts = set()
    for chunk in sorted_chunks:
        if chunk["text"] not in seen_texts:
            unique_chunks.append(chunk)
            seen_texts.add(chunk["text"])
    for chunk in unique_chunks:
        st.write(f"**Text:** {chunk['text']}")

    # Save conversation history to session state
    st.session_state["conversation"] = conversation
