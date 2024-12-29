import streamlit as st
import requests
import openai
import time
import json
from datetime import datetime

# OpenAI API Key
openai.api_key = st.secrets["mykey"]

st.set_page_config(layout="wide")

# Initialize session state variables
if "step" not in st.session_state:
    st.session_state.step = "user_setup"
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "chatbot_id" not in st.session_state:
    st.session_state.chatbot_id = None
if "knowledge_id" not in st.session_state:
    st.session_state.knowledge_id = None
if "server_url" not in st.session_state:
    st.session_state.server_url = ""

# Server URL Configuration
st.sidebar.header("Server Configuration")
entered_url = st.sidebar.text_input("Enter Server URL", 
                                  value=st.session_state.server_url,
                                  placeholder="http://localhost:8000")
if st.sidebar.button("Connect to Server"):
    if entered_url.strip():
        st.session_state.server_url = entered_url.strip()
        st.sidebar.success(f"Connected to: {st.session_state.server_url}")
    else:
        st.sidebar.error("Please enter a valid server URL")

def show_user_setup():
    st.title("User Setup")
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
                    st.session_state.step = "chatbot_setup"
                    st.success("User created successfully!")
                    st.experimental_rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")

def show_chatbot_setup():
    st.title("Chatbot Setup")
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
                    st.session_state.step = "chatbot_config"
                    st.success("Chatbot created successfully!")
                    st.experimental_rerun()
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
                    st.experimental_rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")

def show_knowledge_setup():
    st.title("Knowledge Base Setup")
    
    # Create Knowledge Base
    with st.form("knowledge_base"):
        st.subheader("Create Knowledge Base")
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
                    st.experimental_rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Upload Documents (if knowledge base exists)
    if st.session_state.knowledge_id:
        st.subheader("Upload Documents")
        uploaded_file = st.file_uploader("Choose a file", 
                                       type=['txt', 'pdf', 'csv'],
                                       accept_multiple_files=True)
        
        if uploaded_file:
            for file in uploaded_file:
                try:
                    files = {"file": (file.name, file.getvalue(), "application/octet-stream")}
                    response = requests.post(
                        f"{st.session_state.server_url}/documents/upload/{st.session_state.knowledge_id}",
                        files=files
                    )
                    if response.status_code == 200:
                        st.success(f"File {file.name} uploaded successfully!")
                    else:
                        st.error(f"Error uploading {file.name}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        if st.button("Proceed to Chat"):
            st.session_state.step = "chat"
            st.experimental_rerun()

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
                response = requests.post(
                    f"{st.session_state.server_url}/set-parameters",
                    json={
                        "temperature": temperature,
                        "k": k,
                        "chunk_overlap": chunk_overlap,
                        "rerank_method": rerank_method
                    }
                )
                if response.status_code == 200:
                    st.success("Parameters updated!")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Chat Interface
    st.subheader("Chat")
    user_input = st.text_input("Your message:")
    
    if st.button("Send"):
        if user_input.strip():
            try:
                response = requests.post(
                    f"{st.session_state.server_url}/query",
                    json={"query": user_input}
                )
                if response.status_code == 200:
                    data = response.json()
                    st.write("Answer:", data["answer"])
                    
                    with st.expander("View Supporting Documents"):
                        for chunk in data["chunks"]:
                            st.markdown(f"**Source:** {chunk['source']}")
                            st.markdown(f"**Content:** {chunk['content']}")
                            st.markdown(f"**Score:** {chunk['score']:.4f}")
                            st.markdown("---")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # History and Download Options
    if st.button("View History"):
        try:
            response = requests.get(f"{st.session_state.server_url}/history")
            if response.status_code == 200:
                history = response.json()
                for entry in history:
                    st.write(f"Query: {entry['query']}")
                    st.write(f"Answer: {entry['answer']}")
                    st.markdown("---")
        except Exception as e:
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
    if not st.session_state.server_url:
        st.warning("Please configure the server URL in the sidebar first.")
        return
    
    if st.session_state.step == "user_setup":
        show_user_setup()
    elif st.session_state.step == "chatbot_setup":
        show_chatbot_setup()
    elif st.session_state.step == "chatbot_config":
        show_chatbot_config()
    elif st.session_state.step == "knowledge_setup":
        show_knowledge_setup()
    elif st.session_state.step == "chat":
        show_chat_interface()

if __name__ == "__main__":
    main()
