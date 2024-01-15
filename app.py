import asyncio
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO, emit, join_room
import os
import uuid
import requests
from requests.auth import HTTPBasicAuth
from flask import request
from flask_cors import CORS


app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins='*')

executor = ThreadPoolExecutor()

token = os.getenv('token')

website_id = os.getenv('website_id')
username = os.getenv('crisp_identifier')
password = os.getenv('crisp_key')

# Dictionary to store user_id -> session_id mapping
user_session_mapping = {}
retrieved_session_ids = []

async def start_conversation_crisp():
    basic_auth_credentials = (username, password)
    api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation"
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'PostmanRuntime/7.35.0',
        'X-Crisp-Tier': 'plugin'
    }

    response = requests.post(
        api_url,
        headers=headers,
        auth=HTTPBasicAuth(*basic_auth_credentials),
    )

    if response.status_code == 201:
        data = response.json()
        current_session_id = data['data']['session_id']
        print(current_session_id)
        return current_session_id
    else:
        print(f"Request failed with status code {response.status_code}.")
        print(response.text)

async def start_thread_openai(user_id):
    api_url = "https://api.openai.com/v1/threads"
    headers = {
        "OpenAI-Beta": "assistants=v1",
        "User-Agent": "PostmanRuntime/7.34.0",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    response = requests.post(api_url, headers=headers, json={})

    if response.status_code == 200:
        data = response.json()
        thread_openai_id = data.get("id")
        print("Thread started successfully! Thread id:", thread_openai_id)
        return thread_openai_id
    elif response.status_code == 401:
        error_message = response.json().get("error", {}).get("message", "")
        if "Incorrect API key provided" in error_message:
            print("Error starting OpenAI thread: Incorrect API key provided")
            socketio.emit('start', {'user_id': user_id, 'message': "Технічні неполадки. Відповімо скоро"}, room=user_id)
        else:
            print("Error starting OpenAI thread:", response.status_code, error_message)
        return None

def start_conversation_crisp_background(user_id):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    session_id = loop.run_until_complete(start_conversation_crisp())
    user_session_mapping[user_id] = session_id
    retrieved_session_ids.append(session_id)
    print(f"Session ID associated with User ID {user_id}: {session_id}")
    return session_id
  

def start_thread_openai_background(user_id):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_thread_openai(user_id))

message_data = {}

def parse_user_id(user_id, retrieved_session_id):
    @socketio.on('send_message')
    def crisp_messages(message, session_id):
        if session_id in retrieved_session_ids:
            # Reverse lookup to get user_id corresponding to session_id
            user_id_for_session = next((uid for uid, sid in user_session_mapping.items() if sid == session_id), None)

            if user_id_for_session:
                print(f"Message received for user {user_id_for_session}: {message}")
                emit('start', {'user_id': user_id_for_session, 'message': message}, room=user_id_for_session)
            else:
                print(f"Session ID {session_id} not mapped to any user.")
        else:
            print(f"Invalid session ID: {session_id}")

@socketio.on('connect')
def handle_connect():
    user_id = str(uuid.uuid4())
    join_room(user_id)
    print(f'User {user_id} connected')
    socketio.emit('user_id', {'response': user_id})

    # Start the background task to execute start_conversation_crisp
    session_id = socketio.start_background_task(target=start_conversation_crisp_background, user_id=user_id)
    
    # Start the background task to execute start_thread_openai
    socketio.start_background_task(target=start_thread_openai_background, user_id=user_id)

    parse_user_id(user_id, session_id)
    # Corrected typo in function call
  
@app.route("/", methods=['POST', 'GET'])
def receive_msg_from_client():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            print("Received JSON data:", data)
            
            # Extract the value of "question" directly
            question_value = data.get('question', 'Question not found')
            user_id = data.get('user_id')
            print(user_id)
            print(question_value)
            session_id = user_session_mapping.get(user_id)
            print(session_id)

        # if session_id:

        #     execute_flow(question_value, user_id, session_id)
            # Return the value of "question" directly
            return jsonify(question_value)

        else:
            print("Invalid request. Expected JSON content type.")
    if request.method == 'GET':
        return jsonify("response",)

if __name__ == '__main__':
    socketio.run()

