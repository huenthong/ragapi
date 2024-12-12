import streamlit as st
import requests
import openai
import time

# Function to validate URL
def is_valid_url(url):
    try:
        response = requests.get(f"{url}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

# Initialize session state for URL if not exists
if 'public_url' not in st.session_state:
    st.session_state.public_url = ""

# Title
st.title("RAG LLM")

# URL Input Section
st.header("Server Configuration")
url_input = st.text_input(
    "Enter Server URL", 
    value=st.session_state.public_url, 
    placeholder="https://your-server-url.loca.lt"
)

# Validate URL
if url_input:
    if is_valid_url(url_input):
        st.session_state.public_url = url_input
        st.success("Server URL validated successfully!")
    else:
        st.error("Invalid or unreachable server URL. Please check and try again.")

# OpenAI API Key
openai.api_key = st.secrets["mykey"]

# Rest of your existing sidebar configuration remains the same
st.sidebar.header("Configuration")
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
    if not st.session_state.public_url:
        st.sidebar.error("Please enter a valid server URL first!")
    else:
        try:
            response = requests.post(f"{st.session_state.public_url}/set-parameters", json={
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

# Ensure public URL is set before allowing query
user_query = st.text_input("Enter your query:")
if st.button("Submit Query"):
    # Check if server URL is set
    if not st.session_state.public_url:
        st.error("Please enter a valid server URL first!")
    elif not user_query.strip():
        st.warning("Please enter a query before submitting.")
    else:
        st.session_state["conversation"].append(user_query)

        # Make the API call with retry logic
        max_retries = 3
        retry_delay = 5  # Seconds
        for attempt in range(max_retries):
            try:
                # Send both `query` and `keywords` in the JSON body
                response = requests.post(f"{st.session_state.public_url}/query", json={
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
                        st.markdown(
                            "\n".join([f"- **Reference:** {ref}" for ref in references])
                        )

                    if chunks:
                        st.write("\n### Supporting Information")
                        for chunk in chunks:
                            content = chunk.get("content", "No content available.").replace("\n", " ")
                            source = chunk.get("source", "Unknown Source")
                            st.markdown(
                                f"- **From {source}:**\n\n{content}"
                            )

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





