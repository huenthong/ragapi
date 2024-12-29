import streamlit as st
import requests
import openai
import time
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from requests.exceptions import RequestException

# Configure logging with both file and stream handlers
def setup_logging():
    logger = logging.getLogger('chatbot_app')
    logger.setLevel(logging.INFO)
    
    # File handler
    file_handler = logging.FileHandler('chatbot_app.log')
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Stream handler for console output
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_format = logging.Formatter('%(levelname)s: %(message)s')
    stream_handler.setFormatter(stream_format)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    
    return logger

logger = setup_logging()

# OpenAI API Key
openai.api_key = st.secrets["mykey"]

# Page configuration
st.set_page_config(
    page_title="Chatbot Interface",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables
def init_session_state():
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
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "documents" not in st.session_state:
        st.session_state.documents = []

def make_api_request(method: str, endpoint: str, max_retries: int = 3, **kwargs) -> Optional[requests.Response]:
    """
    Make API request with automatic retries and logging
    """
    url = f"{st.session_state.server_url}{endpoint}"
    attempt = 0
    
    while attempt < max_retries:
        try:
            logger.info(f"Attempting {method} request to {endpoint} (Attempt {attempt + 1}/{max_retries})")
            response = requests.request(method, url, **kwargs)
            
            if response.status_code == 502:
                attempt += 1
                logger.warning(f"502 error encountered. Retrying... (Attempt {attempt}/{max_retries})")
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
                
            response.raise_for_status()
            logger.info(f"Successful {method} request to {endpoint}")
            return response
            
        except RequestException as e:
            attempt += 1
            logger.error(f"Request failed: {str(e)}")
            if attempt == max_retries:
                logger.error("Max retries reached")
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
    return None

def show_server_setup():
    st.title("Server Configuration")
    logger.info("Displaying server setup page")
    
    with st.form("server_setup", clear_on_submit=False):
        entered_url = st.text_input(
            "Server URL",
            value=st.session_state.server_url,
            placeholder="http://localhost:8000"
        )
        
        submitted = st.form_submit_button("Connect to Server")
        
        if submitted:
            if not entered_url.strip():
                logger.warning("Empty server URL submitted")
                st.error("Please enter a server URL")
                return
                
            entered_url = entered_url.rstrip('/')
            try:
                logger.info(f"Testing connection to {entered_url}")
                response = requests.get(entered_url)
                st.session_state.server_url = entered_url
                logger.info("Server connection successful")
                st.success("✅ Connected successfully!")
                time.sleep(1)
                st.session_state.step = "user_setup"
                st.rerun()
            except Exception as e:
                logger.error(f"Server connection failed: {str(e)}")
                st.error(f"Connection error: {str(e)}")

def show_user_setup():
    st.title("User Setup")
    logger.info("Displaying user setup page")
    
    # Fetch existing users
    try:
        response = make_api_request('GET', "/users/list")
        if response and response.status_code == 200:
            existing_users = response.json()
            
            if existing_users:
                st.subheader("Select Existing User")
                user_options = ["Select a user..."] + [user["user_name"] for user in existing_users]
                selected_user = st.selectbox(
                    "Choose a user",
                    options=user_options,
                    index=0
                )
                
                if selected_user != "Select a user...":
                    selected_user_data = next(user for user in existing_users if user["user_name"] == selected_user)
                    if st.button("Use Selected User"):
                        logger.info(f"Selected existing user: {selected_user}")
                        st.session_state.user_id = selected_user_data["user_id"]
                        st.success(f"Selected user: {selected_user}")
                        time.sleep(1)
                        st.session_state.step = "chatbot_setup"
                        st.rerun()
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        st.error(f"Error fetching users: {str(e)}")
    
    # Create new user
    st.subheader("Or Create New User")
    with st.form("user_setup"):
        user_name = st.text_input("Enter your name")
        submitted = st.form_submit_button("Create User")
        
        if submitted:
            if not user_name:
                logger.warning("Empty user name submitted")
                st.error("Please enter a name")
                return
                
            try:
                logger.info(f"Creating new user: {user_name}")
                response = make_api_request(
                    'POST',
                    "/users/create",
                    json={"user_name": user_name}
                )
                
                if response and response.status_code == 200:
                    data = response.json()
                    st.session_state.user_id = data["user_id"]
                    logger.info(f"User created successfully: {user_name}")
                    st.success("User created successfully!")
                    time.sleep(1)
                    st.session_state.step = "chatbot_setup"
                    st.rerun()
                else:
                    logger.error("Failed to create user")
                    st.error("Error creating user")
            except Exception as e:
                logger.error(f"Error creating user: {str(e)}")
                st.error(f"Error: {str(e)}")

def show_chatbot_setup():
    st.title("Chatbot Setup")
    logger.info("Displaying chatbot setup page")
    
    if not st.session_state.user_id:
        logger.warning("No user_id found in session state")
        st.error("Please select or create a user first")
        return
    
    # Fetch existing chatbots
    try:
        response = make_api_request(
            'GET',
            f"/chatbots/list/{st.session_state.user_id}"
        )
        if response and response.status_code == 200:
            existing_chatbots = response.json()
            
            if existing_chatbots:
                st.subheader("Select Existing Chatbot")
                chatbot_options = ["Select a chatbot..."] + [
                    f"{chatbot['chatbot_name']} - {chatbot['chatbot_desc'][:50]}..." 
                    for chatbot in existing_chatbots
                ]
                selected_chatbot = st.selectbox(
                    "Choose a chatbot",
                    options=chatbot_options,
                    index=0
                )
                
                if selected_chatbot != "Select a chatbot...":
                    selected_chatbot_name = selected_chatbot.split(" - ")[0]
                    selected_chatbot_data = next(
                        chatbot for chatbot in existing_chatbots 
                        if chatbot["chatbot_name"] == selected_chatbot_name
                    )
                    if st.button("Use Selected Chatbot"):
                        logger.info(f"Selected existing chatbot: {selected_chatbot_name}")
                        st.session_state.chatbot_id = selected_chatbot_data["chatbot_id"]
                        st.success(f"Selected chatbot: {selected_chatbot_name}")
                        time.sleep(1)
                        st.session_state.step = "knowledge_setup"
                        st.rerun()
    except Exception as e:
        logger.error(f"Error fetching chatbots: {str(e)}")
        st.error(f"Error fetching chatbots: {str(e)}")
    
    # Create new chatbot
    st.subheader("Or Create New Chatbot")
    with st.form("chatbot_setup"):
        chatbot_name = st.text_input("Chatbot Name")
        chatbot_desc = st.text_area("Chatbot Description")
        submitted = st.form_submit_button("Create Chatbot")
        
        if submitted:
            if not chatbot_name or not chatbot_desc:
                logger.warning("Empty chatbot name or description submitted")
                st.error("Please fill in all fields")
                return
                
            try:
                logger.info(f"Creating new chatbot: {chatbot_name}")
                response = make_api_request(
                    'POST',
                    "/chatbots/create",
                    json={
                        "user_id": st.session_state.user_id,
                        "chatbot_name": chatbot_name,
                        "chatbot_desc": chatbot_desc
                    }
                )
                if response and response.status_code == 200:
                    data = response.json()
                    st.session_state.chatbot_id = data["chatbot_id"]
                    logger.info(f"Chatbot created successfully: {chatbot_name}")
                    st.success("Chatbot created successfully!")
                    time.sleep(1)
                    st.session_state.step = "knowledge_setup"
                    st.rerun()
                else:
                    logger.error("Failed to create chatbot")
                    st.error("Error creating chatbot")
            except Exception as e:
                logger.error(f"Error creating chatbot: {str(e)}")
                st.error(f"Error: {str(e)}")

def show_knowledge_setup():
    st.title("Knowledge Base Setup")
    logger.info("Displaying knowledge base setup page")
    
    if not st.session_state.chatbot_id:
        logger.warning("No chatbot_id found in session state")
        st.error("Please select or create a chatbot first")
        return
    
    # Fetch existing knowledge bases
    try:
        response = make_api_request(
            'GET',
            f"/knowledge/list/{st.session_state.chatbot_id}"
        )
        if response and response.status_code == 200:
            existing_knowledge_bases = response.json()
            
            if existing_knowledge_bases:
                st.subheader("Select Existing Knowledge Base")
                kb_options = ["Select a knowledge base..."] + [
                    f"{kb['knowledge_name']} - {kb['knowledge_desc'][:50]}..."
                    for kb in existing_knowledge_bases
                ]
                selected_kb = st.selectbox(
                    "Choose a knowledge base",
                    options=kb_options,
                    index=0
                )
                
                if selected_kb != "Select a knowledge base...":
                    selected_kb_name = selected_kb.split(" - ")[0]
                    selected_kb_data = next(
                        kb for kb in existing_knowledge_bases 
                        if kb["knowledge_name"] == selected_kb_name
                    )
                    if st.button("Use Selected Knowledge Base"):
                        logger.info(f"Selected existing knowledge base: {selected_kb_name}")
                        st.session_state.knowledge_id = selected_kb_data["knowledge_id"]
                        st.success(f"Selected knowledge base: {selected_kb_name}")
                        time.sleep(1)
                        st.session_state.step = "document_upload"
                        st.rerun()
    except Exception as e:
        logger.error(f"Error fetching knowledge bases: {str(e)}")
        st.error(f"Error fetching knowledge bases: {str(e)}")
    
    # Create new knowledge base
    st.subheader("Or Create New Knowledge Base")
    with st.form("knowledge_base"):
        knowledge_name = st.text_input("Knowledge Base Name")
        knowledge_desc = st.text_area("Knowledge Base Description")
        submitted = st.form_submit_button("Create Knowledge Base")
        
        if submitted:
            if not knowledge_name or not knowledge_desc:
                logger.warning("Empty knowledge base name or description submitted")
                st.error("Please fill in all fields")
                return
                
            try:
                logger.info(f"Creating new knowledge base: {knowledge_name}")
                response = make_api_request(
                    'POST',
                    "/knowledge/create",
                    json={
                        "chatbot_id": st.session_state.chatbot_id,
                        "knowledge_name": knowledge_name,
                        "knowledge_desc": knowledge_desc
                    }
                )
                if response and response.status_code == 200:
                    data = response.json()
                    st.session_state.knowledge_id = data["knowledge_id"]
                    logger.info(f"Knowledge base created successfully: {knowledge_name}")
                    st.success("Knowledge base created successfully!")
                    time.sleep(1)
                    st.session_state.step = "document_upload"
                    st.rerun()
                else:
                    logger.error("Failed to create knowledge base")
                    st.error("Error creating knowledge base")
            except Exception as e:
                logger.error(f"Error creating knowledge base: {str(e)}")
                st.error(f"Error: {str(e)}")

def show_document_upload():
    st.title("Document Upload")
    logger.info("Displaying document upload page")
    
    if not st.session_state.knowledge_id:
        logger.warning("No knowledge_id found in session state")
        st.error("Please select or create a knowledge base first")
        return
        
    # Show existing documents
    try:
        response = make_api_request(
            'GET',
            f"/documents/list/{st.session_state.knowledge_id}"
        )
        if response and response.status_code == 200:
            existing_docs = response.json()
            if existing_docs:
                st.subheader("Existing Documents")
                for doc in existing_docs:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"📄 {doc['filename']}")
                        st.write(f"Uploaded: {doc['upload_date']}")
                    with col2:
                        if st.button("Delete", key=f"delete_{doc['document_id']}"):
                            try:
                                logger.info(f"Attempting to delete document: {doc['filename']}")
                                delete_response = make_api_request(
                                    'DELETE',
                                    f"/documents/delete/{doc['document_id']}"
                                )
                                if delete_response and delete_response.status_code == 200:
                                    logger.info(f"Document deleted successfully: {doc['filename']}")
                                    st.success(f"Deleted {doc['filename']}")
                                    st.rerun()
                            except Exception as e:
                                logger.error(f"Error deleting document: {str(e)}")
                                st.error(f"Error deleting document: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching documents: {str(e)}")
        st.error(f"Error fetching documents: {str(e)}")

    # Upload new documents
    st.subheader("Upload New Documents")
    uploaded_files = st.file_uploader(
        "Choose files",
        type=['txt', 'pdf', 'csv'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        for file in uploaded_files:
            try:
                logger.info(f"Attempting to upload file: {file.name}")
                files = {"file": (file.name, file.getvalue(), "application/octet-stream")}
                response = make_api_request(
                    'POST',
                    f"/documents/upload/{st.session_state.knowledge_id}",
                    files=files
                )
                if response and response.status_code == 200:
                    logger.info(f"File uploaded successfully: {file.name}")
                    st.success(f"File {file.name} uploaded successfully!")
                    st.rerun()
                else:
                    logger.error(f"Error uploading file: {file.name}")
                    st.error(f"Error uploading {file.name}: {response.json().get('detail', 'Unknown error')}")
            except Exception as e:
                logger.error(f"Error uploading file {file.name}: {str(e)}")
                st.error(f"Error uploading {file.name}: {str(e)}")
    
    if st.button("Proceed to Chat"):
        logger.info("Proceeding to chat interface")
        st.session_state.step = "chat"
        st.rerun()

def show_chat_interface():
    st.title("Chat Interface")
    logger.info("Displaying chat interface")
    
    # Parameter Configuration
    with st.sidebar:
        st.header("Chat Parameters")
        temperature = st.slider("Temperature", 0.0, 1.0, 0.5)
        k = st.number_input("Top-k", 1, 50, 10)
        chunk_overlap = st.number_input("Chunk Overlap", 0, 100, 30)
        rerank_method = st.selectbox("Rerank Method", ["similarity", "keyword"])
        
        # Add keyword input
        keywords = st.text_input("Keywords (comma-separated)", "")
        keyword_list = [k.strip() for k in keywords.split(",")] if keywords else None
        
        if st.button("Update Parameters"):
            try:
                logger.info("Updating chat parameters")
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
                    logger.info("Chat parameters updated successfully")
                    st.success("Parameters updated!")
            except Exception as e:
                logger.error(f"Error updating parameters: {str(e)}")
                st.error(f"Error: {str(e)}")
    
    # Chat Interface
    st.subheader("Chat")
    user_input = st.text_input("Your message:")
    
    if st.button("Send") or (user_input and user_input.strip()):
        if user_input.strip():
            try:
                response = make_api_request(
                    'POST',
                    "/query",
                    json={
                        "query": user_input,
                        "chatbot_id": st.session_state.chatbot_id,
                        "knowledge_id": st.session_state.knowledge_id,
                        "keywords": keyword_list
                    }
                )
                
                if response and response.status_code == 200:
                    result = response.json()
                    st.write(f"Timestamp: {result['timestamp']}")
                    st.write("Answer:", result["answer"])
                    
                    with st.expander("View Supporting Documents"):
                        for chunk in result["chunks"]:
                            st.markdown(f"**Chunk ID:** {chunk['chunk_id']}")
                            st.markdown(f"**Timestamp:** {chunk['timestamp']}")
                            st.markdown(f"**Source:** {chunk['source']}")
                            st.markdown(f"**Content:** {chunk['content']}")
                            st.markdown(f"**Score:** {chunk['score']:.4f}")
                            if chunk.get('keywords'):
                                st.markdown(f"**Keywords:** {', '.join(chunk['keywords'])}")
                            st.markdown("---")

    # History Display
    if st.button("View History"):
        try:
            response = make_api_request('GET', "/history")
            if response and response.status_code == 200:
                history = response.json()
                for entry in history:
                    st.write(f"Timestamp: {entry['timestamp']}")
                    st.write(f"Query: {entry['query']}")
                    st.write(f"Answer: {entry['answer']}")
                    st.markdown("---")
        except Exception as e:
            st.error(f"Error: {str(e)}")

    # History and Download Options
    if st.button("View History"):
        try:
            logger.info("Fetching chat history")
            response = make_api_request('GET', "/history")
            if response and response.status_code == 200:
                history = response.json()
                logger.info("Chat history retrieved successfully")
                for entry in history:
                    st.write(f"Query: {entry['query']}")
                    st.write(f"Answer: {entry['answer']}")
                    st.markdown("---")
        except Exception as e:
            logger.error(f"Error retrieving history: {str(e)}")
            st.error(f"Error: {str(e)}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear History"):
            try:
                logger.info("Clearing chat history")
                response = make_api_request('POST', "/clear-history")
                if response and response.status_code == 200:
                    logger.info("Chat history cleared successfully")
                    st.success("History cleared!")
            except Exception as e:
                logger.error(f"Error clearing history: {str(e)}")
                st.error(f"Error: {str(e)}")
    
    with col2:
        if st.button("Download History"):
            try:
                logger.info("Downloading chat history")
                response = make_api_request('GET', "/history")
                if response and response.status_code == 200:
                    history = response.json()
                    filename = f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    st.download_button(
                        "Download",
                        data=json.dumps(history, indent=2),
                        file_name=filename,
                        mime="application/json"
                    )
                    logger.info(f"Chat history downloaded as {filename}")
            except Exception as e:
                logger.error(f"Error downloading history: {str(e)}")
                st.error(f"Error: {str(e)}")

def show_navigation():
    """Show navigation buttons between steps"""
    steps = ["server_setup", "user_setup", "chatbot_setup", 
             "knowledge_setup", "document_upload", "chat"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.session_state.step != "server_setup":
            if st.button("◀ Previous"):
                current_idx = steps.index(st.session_state.step)
                if current_idx > 0:
                    logger.info(f"Navigating to previous step: {steps[current_idx - 1]}")
                    st.session_state.step = steps[current_idx - 1]
                    st.rerun()
    
    with col2:
        if st.session_state.step != "chat":
            if st.button("Next ▶"):
                current_idx = steps.index(st.session_state.step)
                if current_idx < len(steps) - 1:
                    logger.info(f"Navigating to next step: {steps[current_idx + 1]}")
                    st.session_state.step = steps[current_idx + 1]
                    st.rerun()

def main():
    """Main application function"""
    try:
        # Initialize session state
        init_session_state()
        
        # Show current step in sidebar
        st.sidebar.write(f"Current Step: {st.session_state.step}")
        
        # Show navigation
        show_navigation()
        
        # Display appropriate page based on current step
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
            
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error(f"An error occurred: {str(e)}")
        logger.exception("Detailed error traceback:")

if __name__ == "__main__":
    main()
