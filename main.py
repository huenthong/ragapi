import streamlit as st
import requests
import openai
import time
import json
import logging
from datetime import datetime
from typing import Optional
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(
    filename='chatbot_frontend.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# OpenAI API Key
openai.api_key = st.secrets["mykey"]

st.set_page_config(layout="wide")

# Initialize session state variables
if "step" not in st.session_state:
    st.session_state.step = "server_setup"
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "chatbot_id" not in st.session_state:
    st.session_state.chatbot_id = None
if "knowledge_id" not in st.session_state:
    st.session_state.knowledge_id = None
if "server_url" not in st.session_state:
    st.session_state.server_url = ""
if "documents" not in st.session_state:
    st.session_state.documents = []

def make_api_request(method: str, endpoint: str, max_retries: int = 3, **kwargs) -> Optional[requests.Response]:
    """
    Make API request with automatic retries
    """
    url = f"{st.session_state.server_url}{endpoint}"
    attempt = 0
    while attempt < max_retries:
        try:
            logging.info(f"Attempting {method} request to {endpoint} (Attempt {attempt + 1}/{max_retries})")
            response = requests.request(method, url, **kwargs)
            
            if response.status_code == 502:
                attempt += 1
                logging.warning(f"502 error encountered. Retrying... (Attempt {attempt}/{max_retries})")
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
                
            response.raise_for_status()
            logging.info(f"Successful {method} request to {endpoint}")
            return response
            
        except RequestException as e:
            attempt += 1
            logging.error(f"Request failed: {str(e)}")
            if attempt == max_retries:
                logging.error("Max retries reached")
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
    return None

# Server URL Configuration
#st.sidebar.header("Server Configuration")
#entered_url = st.sidebar.text_input("Enter Server URL", 
                                  #value=st.session_state.server_url,
                                  #placeholder="http://localhost:8000")
#if st.sidebar.button("Connect to Server"):
    #if entered_url.strip():
        #st.session_state.server_url = entered_url.strip()
        #logging.info(f"Connected to server: {st.session_state.server_url}")
        #st.sidebar.success(f"Connected to: {st.session_state.server_url}")
   # else:
        #logging.error("Invalid server URL provided")
        #st.sidebar.error("Please enter a valid server URL")

def show_server_setup():
    st.title("Server Configuration")
    
    with st.form("server_setup", clear_on_submit=False):
        entered_url = st.text_input(
            "Server URL",
            value=st.session_state.server_url,
            placeholder="http://localhost:8000"
        )
        
        submitted = st.form_submit_button("Connect to Server")
        
        if submitted:
            if not entered_url.strip():
                st.error("Please enter a server URL")
                return
                
            entered_url = entered_url.rstrip('/')
            try:
                # Test connection with simple GET request
                response = requests.get(entered_url)
                st.session_state.server_url = entered_url
                st.success("✅ Connected successfully!")
                time.sleep(1)
                st.session_state.step = "user_setup"
                st.rerun()
            except Exception as e:
                st.error(f"Connection error: {str(e)}")

def show_navigation():
    col1, col2, col3, col4 = st.columns(4)
    
    if st.session_state.step != "server_setup":
        with col1:
            if st.button("◀ Previous"):
                steps = ["server_setup", "user_setup", "chatbot_setup", 
                        "chatbot_config", "knowledge_setup", "document_upload", "chat"]
                current_idx = steps.index(st.session_state.step)
                if current_idx > 0:
                    st.session_state.step = steps[current_idx - 1]
                    st.rerun()
    
    if st.session_state.step != "chat":
        with col4:
            if st.button("Next ▶"):
                steps = ["server_setup", "user_setup", "chatbot_setup", 
                        "chatbot_config", "knowledge_setup", "document_upload", "chat"]
                current_idx = steps.index(st.session_state.step)
                if current_idx < len(steps) - 1:
                    st.session_state.step = steps[current_idx + 1]
                    st.rerun()
        
def show_user_setup():
    st.title("User Setup")
    
    # Fetch existing users
    try:
        response = requests.get(f"{st.session_state.server_url}/users/list")
        if response.status_code == 200:
            existing_users = response.json()
            
            # Option to select existing user
            st.subheader("Select Existing User")
            selected_user = st.selectbox(
                "Choose a user",
                options=[user["user_name"] for user in existing_users],
                format_func=lambda x: f"User: {x}"
            )
            
            if st.button("Use Selected User"):
                selected_user_data = next(user for user in existing_users if user["user_name"] == selected_user)
                st.session_state.user_id = selected_user_data["user_id"]
                st.session_state.step = "chatbot_setup"
                st.rerun()
    except Exception as e:
        st.error(f"Error fetching users: {str(e)}")
    
    # Create new user
    st.subheader("Create New User")
    with st.form("user_setup"):
        user_name = st.text_input("Enter your name")
        submitted = st.form_submit_button("Create User")
        
        if submitted and user_name:
            try:
                response = requests.post(
                    f"{st.session_state.server_url}/users/create",
                    json={"user_name": user_name}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.user_id = data["user_id"]
                    st.success("User created successfully!")
                    time.sleep(1)
                    st.session_state.step = "chatbot_setup"
                    st.rerun()
                else:
                    st.error(response.json().get("detail", "Error creating user"))
            except Exception as e:
                st.error(f"Error: {str(e)}")

def show_chatbot_setup():
    st.title("Chatbot Setup")
    
    # Fetch existing chatbots
    try:
        response = requests.get(
            f"{st.session_state.server_url}/chatbots/list/{st.session_state.user_id}"
        )
        if response.status_code == 200:
            existing_chatbots = response.json()
            
            # Option to select existing chatbot
            st.subheader("Select Existing Chatbot")
            selected_chatbot = st.selectbox(
                "Choose a chatbot",
                options=[chatbot["chatbot_name"] for chatbot in existing_chatbots],
                format_func=lambda x: f"Chatbot: {x}"
            )
            
            if st.button("Use Selected Chatbot"):
                selected_chatbot_data = next(
                    chatbot for chatbot in existing_chatbots 
                    if chatbot["chatbot_name"] == selected_chatbot
                )
                st.session_state.chatbot_id = selected_chatbot_data["chatbot_id"]
                st.session_state.step = "knowledge_setup"
                st.rerun()
    except Exception as e:
        st.error(f"Error fetching chatbots: {str(e)}")
    
    # Create new chatbot
    st.subheader("Create New Chatbot")
    with st.form("chatbot_setup"):
        chatbot_name = st.text_input("Chatbot Name")
        chatbot_desc = st.text_area("Chatbot Description")
        submitted = st.form_submit_button("Create Chatbot")
        
        if submitted and chatbot_name and chatbot_desc:
            try:
                response = requests.post(
                    f"{st.session_state.server_url}/chatbots/create",
                    json={
                        "user_id": st.session_state.user_id,
                        "chatbot_name": chatbot_name,
                        "chatbot_desc": chatbot_desc
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.chatbot_id = data["chatbot_id"]
                    st.success("Chatbot created successfully!")
                    time.sleep(1)
                    st.session_state.step = "knowledge_setup"
                    st.rerun()
                else:
                    st.error(response.json().get("detail", "Error creating chatbot"))
            except Exception as e:
                st.error(f"Error: {str(e)}")

def show_chatbot_config():
    st.title("Chatbot Configuration")
    
    with st.form("chatbot_config"):
        col1, col2 = st.columns(2)
        
        with col1:
            temperature = st.slider("Temperature", 0.0, 1.0, 0.65)
            max_response = st.number_input("Max Response Tokens", 100, 2048, 1024)
            knowledge_relevance = st.slider("Knowledge Relevance", 0.0, 1.0, 0.85)
            recall_num = st.number_input("Recall Number", 1, 50, 10)
        
        with col2:
            ai_engine = st.selectbox("AI Engine", ["gpt-3.5-turbo", "gpt-4"])
            rerank_model = st.selectbox("Rerank Model", ["Disable", "Enable"])
            search_weight = st.selectbox("Search Weight", ["BM25", "Mixed"])
            mixed_percentage = st.slider("Mixed Percentage", 0, 100, 50)
        
        sys_prompt = st.text_area("System Prompt")
        empty_response = st.text_area("Empty Response Message")
        
        submitted = st.form_submit_button("Save Configuration")
        
        if submitted:
            try:
                response = requests.post(
                    f"{st.session_state.server_url}/chatbots/config",
                    json={
                        "chatbot_id": st.session_state.chatbot_id,
                        "temperature": temperature,
                        "max_response": max_response,
                        "knowledge_relevance": knowledge_relevance,
                        "recall_num": recall_num,
                        "ai_engine": ai_engine,
                        "rerank_model": rerank_model,
                        "search_weight": search_weight,
                        "mixed_percentage": mixed_percentage,
                        "sys_prompt": sys_prompt,
                        "empty_response": empty_response
                    }
                )
                if response.status_code == 200:
                    st.session_state.step = "knowledge_setup"
                    st.success("Configuration saved successfully!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")

def show_knowledge_setup():
    st.title("Knowledge Base Setup")
    
    # Fetch existing knowledge bases
    try:
        response = requests.get(
            f"{st.session_state.server_url}/knowledge/list/{st.session_state.chatbot_id}"
        )
        if response.status_code == 200:
            existing_knowledge_bases = response.json()
            
            # Option to select existing knowledge base
            st.subheader("Select Existing Knowledge Base")
            selected_kb = st.selectbox(
                "Choose a knowledge base",
                options=[kb["knowledge_name"] for kb in existing_knowledge_bases],
                format_func=lambda x: f"Knowledge Base: {x}"
            )
            
            if st.button("Use Selected Knowledge Base"):
                selected_kb_data = next(
                    kb for kb in existing_knowledge_bases 
                    if kb["knowledge_name"] == selected_kb
                )
                st.session_state.knowledge_id = selected_kb_data["knowledge_id"]
                st.rerun()
    except Exception as e:
        st.error(f"Error fetching knowledge bases: {str(e)}")
    
    # Create new knowledge base
    st.subheader("Create New Knowledge Base")
    with st.form("knowledge_base"):
        knowledge_name = st.text_input("Knowledge Base Name")
        knowledge_desc = st.text_area("Knowledge Base Description")
        submitted = st.form_submit_button("Create Knowledge Base")
        
        if submitted and knowledge_name and knowledge_desc:
            try:
                response = requests.post(
                    f"{st.session_state.server_url}/knowledge/create",
                    json={
                        "chatbot_id": st.session_state.chatbot_id,
                        "knowledge_name": knowledge_name,
                        "knowledge_desc": knowledge_desc
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.knowledge_id = data["knowledge_id"]
                    st.success("Knowledge base created successfully!")
                    st.rerun()
                else:
                    st.error(response.json().get("detail", "Error creating knowledge base"))
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Show document upload section and existing documents
    if st.session_state.knowledge_id:
        st.subheader("Document Management")
        
        # Show existing documents
        try:
            response = requests.get(
                f"{st.session_state.server_url}/documents/list/{st.session_state.knowledge_id}"
            )
            if response.status_code == 200:
                existing_docs = response.json()
                if existing_docs:
                    st.write("Existing Documents:")
                    for doc in existing_docs:
                        st.write(f"- {doc['filename']} (Uploaded: {doc['upload_date']})")
        except Exception as e:
            st.error(f"Error fetching documents: {str(e)}")
        
        # Upload new documents
        uploaded_files = st.file_uploader(
            "Upload New Documents",
            type=['txt', 'pdf', 'csv'],
            accept_multiple_files=True
        )
        
        if uploaded_files:
            for file in uploaded_files:
                try:
                    files = {"file": (file.name, file.getvalue(), "application/octet-stream")}
                    response = requests.post(
                        f"{st.session_state.server_url}/documents/upload/{st.session_state.knowledge_id}",
                        files=files
                    )
                    if response.status_code == 200:
                        st.success(f"File {file.name} uploaded successfully!")
                    else:
                        st.error(f"Error uploading {file.name}: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error uploading {file.name}: {str(e)}")
        
        if st.button("Proceed to Chat"):
            st.session_state.step = "chat"
            st.rerun()

def show_chat_interface():
    st.title("Chat Interface")
    
    # Parameter Configuration
    with st.sidebar:
        st.header("Chat Parameters")
        temperature = st.slider("Temperature", 0.0, 1.0, 0.5)
        k = st.number_input("Top-k", 1, 50, 10)
        chunk_overlap = st.number_input("Chunk Overlap", 0, 100, 30)
        rerank_method = st.selectbox("Rerank Method", ["similarity", "keyword"])
        
        if st.button("Update Parameters"):
            try:
                response = make_api_request(
                    'POST',
                    "/set-parameters",
                    json={
                        "temperature": temperature,
                        "k": k,
                        "chunk_overlap": chunk_overlap,
                        "rerank_method": rerank_method
                    }
                )
                if response and response.status_code == 200:
                    logging.info("Chat parameters updated successfully")
                    st.success("Parameters updated!")
            except Exception as e:
                logging.error(f"Error updating parameters: {str(e)}")
                st.error(f"Error: {str(e)}")
    
    # Chat Interface
    st.subheader("Chat")
    user_input = st.text_input("Your message:")
    
def send_query(query: str) -> Optional[dict]:
    """Send query with automatic retry logic"""
    try:
        response = make_api_request(
            'POST',
            "/query",
            json={
                "query": query,
                "chatbot_id": st.session_state.chatbot_id,
                "knowledge_id": st.session_state.knowledge_id
            }
        )
        if response and response.status_code == 200:
            return response.json()
    except Exception as e:
        logging.error(f"Error sending query: {str(e)}")
        st.error(f"Error: {str(e)}")
    return None
    
    if st.button("Send") or (user_input and user_input.strip()):
        if user_input.strip():
            logging.info(f"Sending query: {user_input}")
            result = send_query(user_input)
            
            if result:
                st.write("Answer:", result["answer"])
                logging.info("Query answered successfully")
                
                with st.expander("View Supporting Documents"):
                    for chunk in result["chunks"]:
                        st.markdown(f"**Source:** {chunk['source']}")
                        st.markdown(f"**Content:** {chunk['content']}")
                        st.markdown(f"**Score:** {chunk['score']:.4f}")
                        st.markdown("---")
            else:
                st.error("Failed to get response. Please try again.")

    # History and Download Options
    if st.button("View History"):
        try:
            response = make_api_request('GET', "/history")
            if response and response.status_code == 200:
                history = response.json()
                logging.info("Chat history retrieved successfully")
                for entry in history:
                    st.write(f"Query: {entry['query']}")
                    st.write(f"Answer: {entry['answer']}")
                    st.markdown("---")
        except Exception as e:
            logging.error(f"Error retrieving history: {str(e)}")
            st.error(f"Error: {str(e)}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear History"):
            try:
                response = requests.post(f"{st.session_state.server_url}/clear-history")
                if response.status_code == 200:
                    st.success("History cleared!")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    with col2:
        if st.button("Download History"):
            try:
                response = requests.get(f"{st.session_state.server_url}/history")
                if response.status_code == 200:
                    history = response.json()
                    st.download_button(
                        "Download",
                        data=json.dumps(history, indent=2),
                        file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
            except Exception as e:
                st.error(f"Error: {str(e)}")

# Main App Flow
def main():
    # Show current step
    st.sidebar.write(f"Current Step: {st.session_state.step}")
    
    # Show navigation
    show_navigation()
    
    # Main content
    if st.session_state.step == "server_setup":
        show_server_setup()
    elif st.session_state.step == "user_setup":
        show_user_setup()
    elif st.session_state.step == "chatbot_setup":
        show_chatbot_setup()
    elif st.session_state.step == "knowledge_setup":
        show_knowledge_setup()
    elif st.session_state.step == "document_upload":
        show_document_upload()
    elif st.session_state.step == "chat":
        show_chat_interface()

if __name__ == "__main__":
    main()
