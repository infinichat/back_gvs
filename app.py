import asyncio
import os
import threading
import uuid
import aiohttp
import asyncpg
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit, join_room
import time
import psycopg2
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
import re
from flask_cors import CORS
import psycopg2
from psycopg2 import OperationalError
from gevent.pywsgi import WSGIServer

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins='*')

load_dotenv()

db_config = {
    'host': os.getenv('PGHOST'),
    'database': os.getenv('PGDATABASE'),
    'user': os.getenv('PGUSER'),
    'password': os.getenv('PGPASSWORD'),
}


website_id = os.getenv('website_id')
username = os.getenv('crisp_identifier')
password = os.getenv('crisp_key')


first_messages = []
user_session_mapping = {}
user_thread_mapping = {}


async def start_thread_openai(user_id):
    global thread_openai_id
    api_url = "https://api.openai.com/v1/threads"
    headers = {
        "OpenAI-Beta": "assistants=v1",
        "User-Agent": "PostmanRuntime/7.34.0",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            api_url,
            headers=headers,
            json={},
        ) as response:
            if response.status == 200:
                data = await response.json()
                thread_openai_id = data.get("id")
                print("Thread started successfully! Thread id:", thread_openai_id)
                return thread_openai_id
            elif response.status == 401:  # Unauthorized (Invalid API key)
                error_message = (await response.json()).get("error", {}).get("message", "")
                if "Incorrect API key provided" in error_message:
                    print("Error starting OpenAI thread: Incorrect API key provided")
                    emit('start', {'user_id': user_id, 'message': "Технічні неполадки. Відповімо скоро"})
                else:
                    print("Error starting OpenAI thread:", response.status, error_message)
                return None

user_conversation_state = {}
user_first_messages = {}
retrieved_session_ids = []
user_questions_mapping = {}
user_conv_state_mapping = {}


@socketio.on('connect')
def handle_connect():
    print("Connected user")


@socketio.on('set_defaults')
def handle_init_connection(data):
    user_id_received = data.get('user_id')
    join_room(user_id_received)
    if join_room(user_id_received):
        print(f"User {user_id_received} successfully joined the room")
    else:
        print(f"Failed to join the room for user {user_id_received}")
    print("Emitting created variables")
    # if user_id_received == "null" or user_id_received is None:
    #         user_id_received = str(uuid.uuid4())
    # join_room(user_id_received)
    # socketio.emit('user_id', {'response': user_id_received})
    print('Received on set_defaults user_id: ' + user_id_received)  # Convert user_id to str
    # Check if question_answered is provided, otherwise default to False
    question_answered_received = data.get('question_answered')
    # f question_answered_received == "null" or question_answered_received is None:
    #     question_answered_received = 'False'i
    print('Received on set_defaults question_answered_received: ' + question_answered_received)

    session_id_crisp = data.get('session_crisp')
    # print('Received on set_defaults session_id_crisp: ' + session_id_crisp)
    # Check if user_conversation_state is provided, otherwise default to 0
    user_conv_state = data.get('user_conversation_state')
    # if user_conv_state == "null" or user_conv_state is None:
    #     user_conv_state = 0
    print('Received on set_defaults user_conv_state: ' + str(user_conv_state))

    user_first_msgs = data.get('user_first_messages')
    # if user_first_msgs == "undefined" or user_first_msgs == "null":
    #     user_first_msgs = []
    print('Received on set_defaults user_first_msgs: ' + str(user_first_msgs))
    


    # Run asynchronous tasks in the background
    socketio.start_background_task(start_connection_tasks, user_id_received, question_answered_received, user_conv_state, user_first_msgs, session_id_crisp)

def start_connection_tasks(user_id_received, question_answered_received, user_conv_state, user_first_msgs, session_id_crisp):
    asyncio.run(handle_connection_async(user_id_received, question_answered_received, user_conv_state, user_first_msgs, session_id_crisp))

async def handle_connection_async(user_id_received, question_answered_received, user_conv_state, user_first_msgs, session_id_crisp):
    global question_answered
    global user_conversation_state
    global user_first_messages
    if session_id_crisp == "set" or session_id_crisp is None:
        session_id_crisp = await start_conversation_crisp()
        # user_session_mapping[user_id_received] = session_id_crisp
    user_session_mapping[user_id_received] = session_id_crisp
    # session_id = await start_conversation_crisp()
    # user_session_mapping[user_id_received] = session_id
    # socketio.emit('set_session_crisp', {'response': session_id}, room = user_id_received)
    print("Assigned session_id: " +  session_id_crisp)

    retrieved_session_ids.append(session_id_crisp)
    parse_user_id(user_id_received, session_id_crisp)
    print(user_id_received, session_id_crisp)
    thread_openai_id = await start_thread_openai(user_id_received)
    user_thread_mapping[user_id_received] = thread_openai_id
    print("Thread openai" + thread_openai_id)
    user_questions_mapping[user_id_received] = question_answered_received
    print('Mapped question_answer: ' + str(user_questions_mapping[user_id_received]))


    # Reset state for the new user
    question_answered = question_answered_received
    print("Assigned question_answered: " + question_answered)
    user_conversation_state[user_id_received] = user_conv_state
    print("Assigned user_conversation_state: " + str(user_conversation_state[user_id_received]))
    user_first_messages[user_id_received] = user_first_msgs
    print("Assigned user_first_messages: " +  str(user_first_messages[user_id_received]))
    user_id = user_id_received
    print("Assigned user_id: " +  user_id)
    socketio.emit('update_variables', {
        'user_id': user_id,
        'question_answered': question_answered,
        'user_conversation_state': user_conversation_state[user_id],
        'session_crisp': session_id_crisp
    }, room=user_id)


message_data = {}


def parse_user_id(user_id, retrieved_session_id):
    @socketio.on('send_message')
    def crisp_messages(message, session_id, fingerprint):
        if session_id in retrieved_session_ids:

            # Reverse lookup to get user_id corresponding to session_id
            user_id_for_session = next((uid for uid, sid in user_session_mapping.items() if sid == session_id), None)

            if user_id_for_session:
                print(f"Message received for user {user_id_for_session}: {message}")
                message_data[fingerprint] = message
                socketio.emit('start', {'user_id': user_id_for_session, 'message': message}, room=user_id_for_session)
            else:
                print(f"Session ID {session_id} not mapped to any user.")
        else:
            print(f"Invalid session ID: {session_id}")
    @socketio.on('edit_message')
    def edit_message(new_message, fingerprint):
        if fingerprint in message_data:
            # Retrieve the existing message
            old_message = message_data[fingerprint]
            # emit('start', {'user_id': user_id, 'response': old_message}, room=user_id)

            # Update the message in the dictionary
            message_data[fingerprint] = new_message
            socketio.emit('delete_message', {'user_id': user_id, 'message': old_message}, room=user_id)

            print(f"Message edited. Old message: {old_message}, New message: {new_message}")

            # Emit an event to notify the client or perform any other actions
            socketio.emit('start', {'user_id': user_id, 'message': new_message}, room=user_id)
        else:
            print(f"No message found for fingerprint: {fingerprint}")
    @socketio.on('message_to_delete')
    def delete_message(fingerprint, session_id):
        # Check if the fingerprint exists in the message_data dictionary
        if session_id in retrieved_session_ids:
            # Reverse lookup to get user_id corresponding to session_id
            user_id_for_session = next((uid for uid, sid in user_session_mapping.items() if sid == session_id), None)

            if user_id_for_session:
                if fingerprint in message_data:
                    # If it exists, retrieve the corresponding message
                    del_message = message_data[fingerprint]

                    print("User id to submit delete message: " + user_id_for_session)   
                    emit('user_id', {'response': user_id_for_session})

                    emit('delete_message', {'user_id': user_id_for_session, 'message': del_message}, room=user_id)

                    # Optionally, you can remove the entry from the dictionary if you want
                    del message_data[fingerprint]

                    print(f"Message to delete: {del_message}")
                    
                    # Emit an event to notify the client or perform any other actions
                    # emit('start', {'user_id': user_id, 'response': del_message}, room=user_id)
                else:
                    print(f"No message found for fingerprint: {fingerprint}")


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')  

# @socketio.on('message_from_client')
# async def handle_send_message(data):
#     print(data)
#     user_id = data.get('user_id')
#     message = data.get('message')
#     print(user_id)
#     print(message)
#     session_id = user_session_mapping.get(user_id)

#     if session_id:
#         await execute_flow_async(message, user_id, session_id)   
    # execute_flow(message, user_id)

async def start_conversation_crisp():
    basic_auth_credentials = (username, password)
    api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation"
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'PostmanRuntime/7.35.0',
        'X-Crisp-Tier': 'plugin'
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            api_url,
            headers=headers,
            auth=aiohttp.BasicAuth(*basic_auth_credentials),
        ) as response:
            if response.status == 201:
                data = await response.json()
                current_session_id = data['data']['session_id']
                print(current_session_id)
                return current_session_id
            else:
                print(f"Request failed with status code {response.status}.")
                print(await response.text())

def send_user_message_crisp(question, session_id):
    # session_id = start_conversation_crisp()
    # website_id = os.getenv("website_id")
    api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/message"
    # username = os.getenv("crisp_identifier")
    # password = os.getenv("crisp_key")
    basic_auth_credentials=(username, password)
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'PostmanRuntime/7.35.0',
        'X-Crisp-Tier': 'plugin'
    }
    payload = {
        "type": "text",
        "from": "user",
        "origin": "chat",
        "content": question
    }
    response = requests.post(
        api_url,
        headers=headers,
        auth=HTTPBasicAuth(*basic_auth_credentials),
        json=payload
    )

    if response.status_code == 202:
        print(response.json())
    else:
        print(f"Request failed with status code {response.status_code}.")
        print(response.text)


global_fingerprint = None


def send_agent_message_crisp(response, session_id):
    global global_fingerprint
    # session_id = start_conversation_crisp()
    # website_id = os.getenv("website_id")
    api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/message"
    # username = os.getenv("crisp_identifier")
    # password = os.getenv("crisp_key")
    # alert = "http://127.0.0.1:5000/edit"
    basic_auth_credentials = (username, password)
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'PostmanRuntime/7.35.0',
        'X-Crisp-Tier': 'plugin'
    }

    payload = {
        "type": "text",
        "from": "operator",
        "origin": "chat",
        "content": response
    }
    response = requests.post(
        api_url,
        headers=headers,
        auth=HTTPBasicAuth(*basic_auth_credentials),
        json=payload
    )

    if response.status_code == 202:
        data = response.json()
        global_fingerprint = data['data']['fingerprint']
        print(global_fingerprint)
        return global_fingerprint
    else:
        print(f"Request failed with status code {response.status_code}.")
        print(response.text)


@app.route("/", methods=['POST', 'GET'])
async def receive_msg_from_client():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            print("Received JSON data:", data)
            
            # Extract the value of "question" directly
            question_value = data.get('question', 'Question not found')
            user_id = data.get('user_id')
            print("Received user_id with post request: " + user_id)
            print("Received question with post request: " + question_value)
            # session_id = user_session_mapping.get(user_id)
            session_id = data.get('session_id')
            print("Received session_id with post request: " + session_id)
            question_answered = data.get('question_answered')
            print("Received question_answered with post request: " + question_answered)
            user_conversation_state = data.get('user_conversation_state')
            print("Received user_coonversation_state with post request: " + user_conversation_state)

            if session_id:
                await execute_flow_async(question_value, user_id, session_id, question_answered, user_conversation_state)
                await handle_user_conversation_state_3(user_id, question_answered, user_conversation_state, question_value, session_id)
            
            # Return the value of "question" directly
            return jsonify(question_value)

        else:
            print("Invalid request. Expected JSON content type.")
    if request.method == 'GET':
        return jsonify("response")

token = os.getenv('token')

async def send_message_user_async(thread_openai_id, question):
    print(question)
    print("Going into send_message_user")
    try:
        if thread_openai_id and question:
            api_url = f"https://api.openai.com/v1/threads/{thread_openai_id}/messages"
            api_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "OpenAI-Beta": "assistants=v1",
                "User-Agent": "PostmanRuntime/7.34.0"
            }

            api_json_payload = {
                "role": "user",
                "content": question
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, headers=api_headers, json=api_json_payload) as response:
                    response.raise_for_status()
                    api_data = await response.json()

                    # Create a run after sending a message
                    await create_run_async(session, thread_openai_id)

                    return api_data

    except aiohttp.ClientError as e:
            print(f"API Request Error: {e}")
            return None

    

assistant_id = os.getenv('assistant_id')

async def create_run_async(session, thread_openai_id):
    try:
        api_url = f"https://api.openai.com/v1/threads/{thread_openai_id}/runs"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "OpenAI-Beta": "assistants=v1",
            "User-Agent": "PostmanRuntime/7.34.0"
        }
        json_payload = {
            "assistant_id": assistant_id
        }

        async with session.post(api_url, headers=headers, json=json_payload) as response:
            response.raise_for_status()
            data = await response.json()
            run_id = data.get('id')
            print("Run started successfully! " + run_id)
            await check_run_status_async(session, thread_openai_id, run_id)

    except aiohttp.ClientError as e:
        print(f"API Request Error: {e}")

async def retrieve_ai_response_async(thread_openai_id):
    api_url = f"https://api.openai.com/v1/threads/{thread_openai_id}/messages"
    print("Retrieving response")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                api_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "OpenAI-Beta": "assistants=v1",
                    "User-Agent": "PostmanRuntime/7.34.0",
                    "Accept": "*/*"
                },
            ) as response:
                response.raise_for_status()

                if response.status == 200:
                    content_type = response.headers.get('Content-Type', 'application/json')

                        # Check if 'data' key exists and is a list
                    if 'application/json' in content_type:
                        data = await response.json()
                        print("API Response:", data)

                        # Check if 'data' key exists and is a list
                        if 'data' in data:
    # Filter messages based on role
                            assistant_messages = [msg['content'][0]['text']['value'] for msg in data['data'] if msg['role'] == 'assistant']

                            if assistant_messages:
                                ai_response = assistant_messages[0]  # Retrieve the latest assistant message
                                print("AI Response:", ai_response)
                                return ai_response
                            else:
                                print("No assistant messages found in the response.")
                                return None
                        else:
                            print("Invalid response structure. 'data' key is missing or not a list.")
                            return None
                    else:
                        print("Invalid Content-Type. Expected application/json, got:", content_type)
                        return None
                else:
                    print("Error retrieving AI response:", response.status, await response.text())
                    return None

    except aiohttp.ClientError as e:
        print(f"Async API Request Error: {e}")
        return None

    
async def query_with_caching(question):
    connection = None
    try:
        connection = await asyncpg.connect(**db_config)

        # Convert question to lowercase and remove accents
        cleaned_question = re.sub(r'[^\w\s]', '', question).lower()

        # Use a simplified query without regular expressions
        query = "SELECT answer FROM chat_cache WHERE unaccent(LOWER(question)) = unaccent($1)"
        result = await connection.fetchval(query, cleaned_question)

        print("Querying db")

        return result

    except asyncpg.PostgresError as e:
        print(f"Error connecting to the database: {e}")

    finally:
        try:
            if connection:
                await connection.close()
        except asyncpg.PostgresError as e:
            print(f"Error closing the database connection: {e}")

# Modify patch_profile to accept nickname and phone_number as arguments
def patch_profile(nickname, phone_number, session_id):
    # website_id = os.getenv("website_id")
    # username = os.getenv("crisp_identifier")
    # password = os.getenv("crisp_key")
    basic_auth_credentials = (username, password)
    api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/meta"
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'PostmanRuntime/7.35.0',
        'X-Crisp-Tier': 'plugin'
    }

    payload = {
        "nickname": nickname,
        "data": {
            "phone": phone_number
        }
    }

    try:
        response = requests.patch(
            api_url,
            headers=headers,
            auth=HTTPBasicAuth(*basic_auth_credentials),
            json=payload
        )

        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
        print(response.json())
   
    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error: {errh}")
    except requests.exceptions.ConnectionError as errc:
        print(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        print(f"Request Error: {err}")


async def check_conversation(session_id):
    # website_id = os.getenv("website_id")
    # username = os.getenv("crisp_identifier")
    # password = os.getenv("crisp_key")
    basic_auth_credentials = aiohttp.BasicAuth(login=username, password=password)
    api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/messages"
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'PostmanRuntime/7.35.0',
        'X-Crisp-Tier': 'plugin'
    }
    try:
        async with aiohttp.ClientSession(auth=basic_auth_credentials) as session:
            async with session.get(api_url, headers=headers) as response:
                response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
                data = await response.json()

                user_content_after_name = None
                user_content_after_number = None
                found_name_question = False
                found_number_question = False

                for item in data.get("data", [0]):
                    print("Item:", item)
                    if item.get("from") == "operator" and "Як до вас звертатись?" in item.get("content", ""):
                        found_name_question = True
                    elif found_name_question and item.get("from") == "user":
                        user_content_after_name = item["content"]
                        # print("User's message after 'What is your name?':", user_content_after_name)
                        break

                for item in data.get("data", [1]):
                    print("Item:", item)
                    if item.get("from") == "operator" and "Вкажіть будь ласка свій номер телефону для подальшого зв'язку з Вами." in item.get("content", ""):
                        found_number_question = True
                    elif found_number_question and item.get("from") == "user":
                        user_content_after_number = item["content"]
                        # print("User's message after 'What is your phone number?':", user_content_after_number)
                        break

                patch_profile(user_content_after_name, user_content_after_number, session_id)

    except aiohttp.ClientError as err:
        print(f"HTTP Error: {err}")

async def execute_flow_async(message, user_id, session_id, question_answered, user_conversation_state):
    print("Question answered in execute_flow " + str(question_answered))
    print("User conversation state " + str(user_conversation_state))

    question = message
    user_first_msgs = user_first_messages.get(user_id, [])

    if not question:
        raise ValueError("Invalid payload: 'question' is required.")

    send_user_message_crisp(question, session_id)

    try:
        if question_answered == 'False' and user_conversation_state == '0':
            # print('user_conversation_state in execute_flow ' + user_conversation_state[user_id])
            user_first_msgs.append(question)
            user_first_messages[user_id] = user_first_msgs
            print("User first message: " + str(user_first_msgs))

            # Assuming user_first_messages is a dictionary, update the value for the user_id
            # user_first_messages[user_id] = user_first_msgs
            # socketio.emit('start', {'user_id': user_id, 'message': 'Як до вас звертатись?'}, room=user)
            send_agent_message_crisp('Як до вас звертатись?', session_id)
            user_conversation_state = 1
            socketio.emit('update_variables', {
                'user_id': user_id,
                'question_answered': question_answered,
                'user_conversation_state': user_conversation_state,
                'user_first_messages': user_first_msgs,
                'session_crisp': session_id,
            }, room=user_id)
            print("Emitting the updated variables")

        if question_answered == 'False' and user_conversation_state == '1':
            #  user_first_msgs.append(question)
            user_first_messages[user_id] = user_first_msgs
            print("User first message: " + str(user_first_msgs))
            # print("User first message: " + user_first_msgs[0])
            # socketio.emit('start', {'user_id': user_id, 'message': "Вкажіть будь ласка свій номер телефону для подальшого зв'язку з Вами."}, room=user_id)
            send_agent_message_crisp("Вкажіть будь ласка свій номер телефону для подальшого зв'язку з Вами.", session_id)
            user_conversation_state = 2
            print("Emitting the updated variables")
            socketio.emit('update_variables', {
                'user_id': user_id,
                'question_answered': question_answered,
                'user_conversation_state': user_conversation_state,
                'user_first_messages': user_first_msgs,
                'session_crisp': session_id,
            }, room=user_id)

        if question_answered == 'False' and user_conversation_state == '2':
            #  user_first_msgs.append(question)
            user_first_messages[user_id] = user_first_msgs
            print("User first message: " + str(user_first_msgs))
            send_agent_message_crisp("Ваш запит в обробці. Це може зайняти до 1 хвилини", session_id)
            # user_conversation_state = '3'
            print("Emitting the updated variables")
            socketio.emit('update_variables', {
                'user_id': user_id,
                'question_answered': question_answered,
                'user_conversation_state': user_conversation_state,
                'user_first_messages': user_first_msgs,
                'session_crisp': session_id,
            }, room=user_id)
            # socketio.emit('start', {'user_id': user_id, 'message': 'Ваш запит в обробці. Це може зайняти до 1 хвилини'}, room=user_id)
            cached_response = await query_with_caching(user_first_msgs[0])
            print("User first message to retrieve in this phase: " + user_first_msgs[0])
            print(cached_response)
            await check_conversation(session_id)
            if cached_response:
                # socketio.emit('start', {'user_id': user_id, 'message': cached_response}, room=user_id)
                send_agent_message_crisp(cached_response, session_id)
            else:
                print('Going into the condition')
                send_agent_message_crisp("Ваш запит в обробці. Це може зайняти до 1 хвилини", session_id)
                # socketio.emit('start', {'user_id': user_id, 'message': 'Ваш запит в обробці. Це може зайняти до 1 хвилини'}, room=user_id)
                thread_openai_id = user_thread_mapping.get(user_id)
                await send_message_user_async(thread_openai_id, user_first_msgs[0])
                ai_response = await retrieve_ai_response_async(thread_openai_id)
                if ai_response:
                    send_agent_message_crisp(ai_response, session_id)

                    # `socketio.emit('start', {'user_id': user_id, 'message': ai_response}, room=user_id)`
            user_conversation_state = '3'
            question_answered = 'True'
            socketio.emit('update_variables', {
                'user_id': user_id,
                'question_answered': question_answered,
                'user_conversation_state': user_conversation_state,
                'user_first_messages': user_first_msgs,
                'session_crisp': session_id,
            }, room=user_id)

            return
        
        # elif question_answered == 'True' and user_conversation_state == '3':
        #     await handle_user_conversation_state_3(user_id, question_answered, user_conversation_state, question, session_id)
    except Exception as e:
        print(f"Error: {str(e)}")
        socketio.emit('start', {'user_id': user_id, 'message': 'Щось пішло не так, спробуйте пізніше...'}, room=user_id)

async def handle_user_conversation_state_3(user_id, question_answered, user_conversation_state, question, session_id):
    try:
           if question_answered == 'True' and user_conversation_state == '3':
            cached_response = await query_with_caching(question)

            if cached_response:
                # socketio.emit('start', {'user_id': user_id, 'message': cached_response}, room=user_id)
                send_agent_message_crisp(cached_response, session_id)
            else:
                # socketio.emit('start', {'user_id': user_id, 'message': 'Ваш запит в обробці. Це може зайняти до 1 хвилини'}, room=user_id)
                thread_openai_id = user_thread_mapping.get(user_id)
                await send_message_user_async(thread_openai_id, question)
                ai_response = await retrieve_ai_response_async(thread_openai_id)
                if ai_response:
                    # socketio.emit('start', {'user_id': user_id, 'message': ai_response}, room=user_id)
                    send_agent_message_crisp(ai_response, session_id)

    except Exception as e:
        print(f"Error: {str(e)}")
        socketio.emit('start', {'user_id': user_id, 'message': 'Щось пішло не так, спробуйте пізніше...'}, room=user_id)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(socketio.run(host='0.0.0.0', port=5000))

# import asyncio
# import os
# import uuid
# from flask import Flask, jsonify, render_template, request
# from flask_socketio import SocketIO, emit, join_room, leave_room
# import time
# import psycopg2
# import requests
# from dotenv import load_dotenv
# from requests.auth import HTTPBasicAuth
# import re
# from flask_cors import CORS
# import psycopg2
# from psycopg2 import OperationalError
# from gevent.pywsgi import WSGIServer
# import threading

# app = Flask(__name__)
# CORS(app, resources={r"/*": {"origins": "*"}})
# socketio = SocketIO(app, cors_allowed_origins='*')

# load_dotenv()

# db_config = {
#     'host': os.getenv('PGHOST'),
#     'database': os.getenv('PGDATABASE'),
#     'user': os.getenv('PGUSER'),
#     'password': os.getenv('PGPASSWORD'),
# }


# website_id = os.getenv('website_id')
# username = os.getenv('crisp_identifier')
# password = os.getenv('crisp_key')


# first_messages = []
# user_session_mapping = {}
# user_thread_mapping = {}


# def start_thread_openai(user_id):
#     global thread_openai_id
#     api_url = "https://api.openai.com/v1/threads"
#     response = requests.post(
#         api_url,
#         headers={
#             "OpenAI-Beta": "assistants=v1",
#             "User-Agent": "PostmanRuntime/7.34.0",
#             "Content-Type": "application/json",
#             "Authorization": f"Bearer {token}"
#         },
#         json={},
#     )

#     if response.status_code == 200:
#         data = response.json()
#         thread_openai_id = data.get("id")
#         print("Thread started successfully! Thread id:", thread_openai_id)
#         return thread_openai_id

#     elif response.status_code == 401:  # Unauthorized (Invalid API key)
#         error_message = response.json().get("error", {}).get("message", "")
#         if "Incorrect API key provided" in error_message:
#             print("Error starting OpenAI thread: Incorrect API key provided")
#             socketio.emit('start', {'user_id': user_id, 'message': "Технічні неполадки. Відповімо скоро"})
#         else:
#             print("Error starting OpenAI thread:", response.status_code, error_message)
#         return None
#     # Handle other error cases if needed...

# # ... (rest of the code)
# user_conversation_state = {}
# user_first_messages = {}
# retrieved_session_ids = []

# @socketio.on('connect')
# def handle_connect():
#     global question_answered
#     # global conversation_checked
#     # global first_messages

#     user_id = str(uuid.uuid4())  # Generate a unique user ID
#     join_room(user_id)
#     print(f'User {user_id} connected')
#     socketio.emit('user_id', {'response': user_id}) 
#     print(f'Sent {user_id}')
#     session_id = start_conversation_crisp()
#     user_session_mapping[user_id] = session_id
#     print(session_id)
#     retrieved_session_ids.append(session_id)
#     parse_user_id(user_id, session_id)
#     print(user_id, session_id)
#     # thread_openai = threading.Thread(target=start_thread_openai, args=(user_id,))
#     # thread_openai.start()
#     # print("Started OpenAI in thread mode: " + thread_openai.name)
#     thread_openai_id = start_thread_openai(user_id)
#     user_thread_mapping[user_id] = thread_openai_id
#     print(thread_openai_id)

#     # Reset state for the new user
#     question_answered = False
#     user_conversation_state[user_id] = 0
#     user_first_messages[user_id] = []
#     # conversation_checked = 0
#     # first_messages = []


# message_data = {}

# def parse_user_id(user_id, retrieved_session_id):
#     @socketio.on('send_message')
#     def crisp_messages(message, session_id):
#         if session_id in retrieved_session_ids:
#             # Reverse lookup to get user_id corresponding to session_id
#             user_id_for_session = next((uid for uid, sid in user_session_mapping.items() if sid == session_id), None)

#             if user_id_for_session:
#                 print(f"Message received for user {user_id_for_session}: {message}")
#                 socketio.emit('start', {'user_id': user_id_for_session, 'message': message}, room=user_id_for_session)
#             else:
#                 print(f"Session ID {session_id} not mapped to any user.")
#         else:
#             print(f"Invalid session ID: {session_id}")

# @socketio.on('disconnect')
# def handle_disconnect():
#     print('Client disconnected')  


# def start_conversation_crisp():
#     # global current_session_id

#     # if current_session_id:
#     #     return current_session_id

#     basic_auth_credentials = (username, password)
#     api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation"
#     headers = {
#         'Content-Type': 'application/json',
#         'User-Agent': 'PostmanRuntime/7.35.0',
#         'X-Crisp-Tier': 'plugin'
#     }

#     response = requests.post(
#         api_url,
#         headers=headers,
#         auth=HTTPBasicAuth(*basic_auth_credentials),
#     )

#     if response.status_code == 201:
#         data = response.json()
#         current_session_id = data['data']['session_id']
#         print(current_session_id)
#         return current_session_id
#     else:
#         print(f"Request failed with status code {response.status_code}.")
#         print(response.text)


# # #start conversation in crisp and return session_id
# def send_user_message_crisp(question, session_id):
#     # session_id = start_conversation_crisp()
#     # website_id = os.getenv("website_id")
#     api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/message"
#     # username = os.getenv("crisp_identifier")
#     # password = os.getenv("crisp_key")
#     basic_auth_credentials=(username, password)
#     headers = {
#         'Content-Type': 'application/json',
#         'User-Agent': 'PostmanRuntime/7.35.0',
#         'X-Crisp-Tier': 'plugin'
#     }
#     payload = {
#         "type": "text",
#         "from": "user",
#         "origin": "chat",
#         "content": question
#     }
#     response = requests.post(
#         api_url,
#         headers=headers,
#         auth=HTTPBasicAuth(*basic_auth_credentials),
#         json=payload
#     )

#     if response.status_code == 202:
#         print(response.json())
#     else:
#         print(f"Request failed with status code {response.status_code}.")
#         print(response.text)


# # global_fingerprint = None

# # Function to send agent message and return the fingerprint
# def send_agent_message_crisp(response, session_id):
#     # global global_fingerprint
#     # session_id = start_conversation_crisp()
#     # website_id = os.getenv("website_id")
#     api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/message"
#     # username = os.getenv("crisp_identifier")
#     # password = os.getenv("crisp_key")
#     # alert = "http://127.0.0.1:5000/edit"
#     basic_auth_credentials = (username, password)
#     headers = {
#         'Content-Type': 'application/json',
#         'User-Agent': 'PostmanRuntime/7.35.0',
#         'X-Crisp-Tier': 'plugin'
#     }

#     payload = {
#         "type": "text",
#         "from": "operator",
#         "origin": "chat",
#         "content": response
#     }
#     response = requests.post(
#         api_url,
#         headers=headers,
#         auth=HTTPBasicAuth(*basic_auth_credentials),
#         json=payload
#     )

#     if response.status_code == 202:
#         data = response.json()
#         print('AGENT MESSAGE SENT HERE"S THE DATA' + str(data))
#         # global_fingerprint = data['data']['fingerprint']
#         # print(global_fingerprint)
#         # return global_fingerprint
#     else:
#         print(f"Request failed with status code {response.status_code}.")
#         print(response.text)



# # thread_openai_id = None
# token = os.getenv('token')


# #Sending a message to a thread. Step 1
# def send_message_user(thread_openai_id, question):
#     print(question + "sent to openai api")
#     # token = os.getenv("api_key")
#     try:
#         if thread_openai_id and question:
#             api_url = f"https://api.openai.com/v1/threads/{thread_openai_id}/messages"
#             api_headers = {
#                 "Content-Type": "application/json",
#                 "Authorization": f"Bearer {token}",
#                 "OpenAI-Beta": "assistants=v1",
#                 "User-Agent": "PostmanRuntime/7.34.0"
#             }
            
#             # user_question = json_payload.get("question", "")

#             api_json_payload = {
#                 "role": "user",
#                 "content": question
#             }

#             api_response = requests.post(api_url, headers=api_headers, json=api_json_payload)
#             api_response.raise_for_status()

#             if api_response.status_code == 200:
#                 api_data = api_response.json()
#                 # print("Message sent successfully!", api_data)
                
#                 # Create a run after sending a message
    
#                 create_run(thread_openai_id)
                
#                 return api_data
#             else:
#                 print("Error sending message:", api_response.status_code, api_response.text)
#                 return None

#     except requests.exceptions.RequestException as e:
#         print(f"API Request Error: {e}")
#         return None
    
# # Create a run Step2
async def check_run_status_async(session, thread_openai_id, run_id):
    api_url = f"https://api.openai.com/v1/threads/{thread_openai_id}/runs/{run_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "OpenAI-Beta": "assistants=v1",
        "User-Agent": "PostmanRuntime/7.34.0"
    }

    while True:
        async with session.get(api_url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()
            status = data.get("status")

            if status == "completed":
                print("Run status is completed. Retrieving AI response.")
                break  # Exit the loop if the run is completed
            else:
                print(f"Run status is {status}. Waiting for completion.")
                await asyncio.sleep(5)  # Wait for 5 seconds before checking again


# assistant_id = os.getenv('assistant_id')

# def create_run(thread_openai_id):
#     # token = os.getenv("api_key")
#     api_url = f"https://api.openai.com/v1/threads/{thread_openai_id}/runs"
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {token}",
#         "OpenAI-Beta": "assistants=v1",
#         "User-Agent": "PostmanRuntime/7.34.0"
#     }
#     json_payload = {
#         "assistant_id": assistant_id
#     }

#     response = requests.post(api_url, headers=headers, json=json_payload)
#     response.raise_for_status()

#     if response.status_code == 200:
#         data = response.json()
#         run_id = data.get('id')
#         # print("Run created successfully!", run_id)

#         # thread = threading.Thread(target=check_run_status, args=(thread_openai_id, run_id))
#         # thread.start()
#         # print(" THREAD CHECK RUN STATUS: " + thread.name)

#         check_run_status(thread_openai_id, run_id)
    

# def retrieve_ai_response(thread_openai_id):
#     # token = os.getenv("api_key")
#     api_url = f"https://api.openai.com/v1/threads/{thread_openai_id}/messages"

#     try:
#         response = requests.get(
#             api_url,
#             headers={
#                 "Authorization": f"Bearer {token}",
#                 "OpenAI-Beta": "assistants=v1",
#                 "User-Agent": "PostmanRuntime/7.34.0",
#                 "Accept": "*/*"
#             },
#         )
#         response.raise_for_status()

#         if response.status_code == 200:
#             content_type = response.headers.get('Content-Type', 'application/json')
            
#             if 'application/json' in content_type:
#                 data = response.json()
#                 # print("API Response:", data)  # Add this line to print the entire response
#                 if 'data' in data and data['data']:
#                     ai_response = data['data'][0]['content'][0]['text']['value']
#                     print("Retrieved response successfully!", ai_response)
#                     return ai_response
#                 else:
#                     print("No messages found in the response.")
#                     return None
#             else:
#                 print("Invalid Content-Type. Expected application/json, got:", content_type)
#                 return None
#         else:
#             print("Error retrieving AI response:", response.status_code, response.text)
#             return None

#     except requests.exceptions.RequestException as e:
#         print(f"API Request Error: {e}")
#         return None

# def query_with_caching(question):
#     connection = None
#     try:
#         connection = psycopg2.connect(**db_config)
#         cursor = connection.cursor()

#         # Convert question to lowercase and remove accents
#         cleaned_question = re.sub(r'[^\w\s]', '', question).lower()
        
#         # Use a simplified query without regular expressions
#         query = "SELECT answer FROM chat_cache WHERE unaccent(LOWER(question)) = unaccent(%s)"
#         cursor.execute(query, (cleaned_question,))
#         result = cursor.fetchone()

#         print("Querying db")

#         if result:
#             return result[0]
#         else:
#             return None

#     except psycopg2.OperationalError as e:
#         print(f"Error connecting to the database: {e}")

#     finally:
#         try:
#             if connection:
#                 connection.close()
#         except psycopg2.Error as e:
#             print(f"Error closing the database connection: {e}")

# # Modify patch_profile to accept nickname and phone_number as arguments
# def patch_profile(nickname, phone_number, session_id):
#     # website_id = os.getenv("website_id")
#     # username = os.getenv("crisp_identifier")
#     # password = os.getenv("crisp_key")
#     basic_auth_credentials = (username, password)
#     api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/meta"
#     headers = {
#         'Content-Type': 'application/json',
#         'User-Agent': 'PostmanRuntime/7.35.0',
#         'X-Crisp-Tier': 'plugin'
#     }

#     payload = {
#         "nickname": nickname,
#         "data": {
#             "phone": phone_number
#         }
#     }

#     try:
#         response = requests.patch(
#             api_url,
#             headers=headers,
#             auth=HTTPBasicAuth(*basic_auth_credentials),
#             json=payload
#         )

#         response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
#         print(response.json())
   
#     except requests.exceptions.HTTPError as errh:
#         print(f"HTTP Error: {errh}")
#     except requests.exceptions.ConnectionError as errc:
#         print(f"Error Connecting: {errc}")
#     except requests.exceptions.Timeout as errt:
#         print(f"Timeout Error: {errt}")
#     except requests.exceptions.RequestException as err:
#         print(f"Request Error: {err}")


# def check_conversation(session_id):
#     # website_id = os.getenv("website_id")
#     # username = os.getenv("crisp_identifier")
#     # password = os.getenv("crisp_key")
#     basic_auth_credentials = (username, password)
#     api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/messages"
#     headers = {
#         'Content-Type': 'application/json',
#         'User-Agent': 'PostmanRuntime/7.35.0',
#         'X-Crisp-Tier': 'plugin'
#     }
#     try:
#         response = requests.get(
#             api_url,
#             headers=headers,
#             auth=HTTPBasicAuth(*basic_auth_credentials),
#         )

#         response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
#         data = response.json()

#         user_content_after_name = None
#         user_content_after_number = None
#         found_name_question = False
#         found_number_question = False

#         for item in data.get("data", [0]):
#             print("Item:", item)
#             if item.get("from") == "operator" and "Як до Вас звертатись?" in item.get("content", ""):
#                 found_name_question = True
#             elif found_name_question and item.get("from") == "user":
#                 user_content_after_name = item["content"]
#                 print("User's message after 'What is your name?':", user_content_after_name)
#                 break
        
#         for item in data.get("data", [1]):
#             print("Item:", item)
#             if item.get("from") == "operator" and "Вкажіть номер телефону для подальшого зв'язку з Вами" in item.get("content", ""):
#                 found_number_question = True
#             elif found_number_question and item.get("from") == "user":
#                 user_content_after_number = item["content"]
#                 print("User's message after 'What is your phone number?':", user_content_after_number)
#                 break

#         print("Patching profile: " + str(user_content_after_name) + ", " + str(user_content_after_number))
#         patch_profile(user_content_after_name, user_content_after_number, session_id)
            
#     except requests.exceptions.HTTPError as errh:
#         print(f"HTTP Error: {errh}")
#     except requests.exceptions.ConnectionError as errc:
#         print(f"Error Connecting: {errc}")
#     except requests.exceptions.Timeout as errt:
#         print(f"Timeout Error: {errt}")
#     except requests.exceptions.RequestException as err:
#         print(f"Request Error: {err}")

# # first_messages = [] 

# # conversation_checked = 0
# # question_answered = False

# def execute_flow(message, user_id, session_id):
#     global current_session_id
#     global question_answered
#     global conversation_checked

#     question = message
   
#     user_first_msgs = user_first_messages.get(user_id, [])

#     if not question:
#         raise ValueError("Invalid payload: 'question' is required.")

#     thread = threading.Thread(target=send_user_message_crisp, args=(question, session_id))
#     thread.start()
#     print("Started thread USER_MESSAGE_CRISP: " + thread.name)
#     # send_user_message_crisp(question, session_id)

#     try:
#         if not question_answered and user_conversation_state.get(user_id, 0) == 0:
#             # print('Appending the first question')
#             user_first_msgs.append(question)
#             # print("Executing check_conversation() for the first time")
#             # send_agent_message_crisp('Як до вас звертатись?', session_id)
#             socketio.emit('start', {'user_id': user_id, 'message': 'Як до Вас звертатись?'}, room=user_id)
#             thread = threading.Thread(target=send_agent_message_crisp, args=('Як до Вас звертатись?', session_id))
#             thread.start()
#             print("Started thread  SEND_AGENT MESSAGE CRISP : " + thread.name)
#             # send_agent_message_crisp('Як до вас звертатись?', session_id)
#             user_conversation_state[user_id] = 1

#         elif not question_answered and user_conversation_state.get(user_id, 0) == 1:
#             # print("Executing check_conversation() for the second time")
#             socketio.emit('start', {'user_id': user_id, 'message': "Вкажіть будь ласка свій номер телефону для подальшого зв'язку з Вами."}, room=user_id)
#             thread = threading.Thread(target=send_agent_message_crisp, args=("Вкажіть номер телефону для подальшого зв'язку з Вами",session_id))
#             thread.start()
#             print("Started thread  SEND_AGENT MESSAGE CRISP : " + thread.name)
#             # send_agent_message_crisp("Вкажіть будь ласка свій номер телефону для подальшого зв'язку з Вами.", session_id)
#             user_conversation_state[user_id] = 2    
        
#         elif not question_answered and user_conversation_state.get(user_id, 0) == 2:
#             socketio.emit('start', {'user_id': user_id, 'message': 'Ваш запит в обробці. Це може зайняти до 1 хвилини'}, room=user_id)
#             cached_response = query_with_caching(user_first_msgs[0])
#             print(cached_response)
#             thread = threading.Thread(target=check_conversation, args=(session_id,))
#             thread.start()
#             print("Started thread CHECK CONVERSATION : " + thread.name)
#             if cached_response:
#                 socketio.emit('start', {'user_id': user_id, 'message': cached_response}, room=user_id)
#                 thread = threading.Thread(target=send_agent_message_crisp, args=(cached_response, session_id))
#                 thread.start()
#                 print("Started thread  SEND_AGENT MESSAGE CRISP : " + thread.name)
#                 # send_agent_message_crisp(cached_response, session_id)
#             else:
#                 print('Going into the condition')
#                 socketio.emit('start', {'user_id': user_id, 'message': 'Ваш запит в обробці. Це може зайняти до 1 хвилини'}, room=user_id)
#                 thread_openai_id = user_thread_mapping.get(user_id)
#                 thread = threading.Thread(target=send_message_user, args=(thread_openai_id, user_first_msgs[0]))
#                 thread.start()
#                 print("Started thread SEND_MESSAGE_USER openai: " + thread.name)
#                 # send_message_user(thread_openai_id, user_first_msgs[0])
#                 print('Going into retrieve_ai_response')
#                 ai_response = retrieve_ai_response(thread_openai_id)
#                 if ai_response:
#                     thread = threading.Thread(target=send_agent_message_crisp, args=(ai_response, session_id))
#                     thread.start()
#                     print("Started thread  SEND_AGENT MESSAGE CRISP : " + thread.name)
#                     # send_agent_message_crisp(ai_response, session_id)
#                     socketio.emit('start', {'user_id': user_id, 'message': ai_response}, room=user_id)

#             user_conversation_state[user_id] = 3

#         else:
#             # print("Skipped check_conversation()")
#             cached_response = query_with_caching(question)

#             if cached_response:
#                 socketio.emit('start', {'user_id': user_id, 'message': cached_response}, room=user_id)
#                 thread = threading.Thread(target=send_agent_message_crisp, args=(cached_response ,session_id))
#                 thread.start()
#                 print("Started thread SEND_AGENT MESSAGE CRISP : " + thread.name)
#                 # send_agent_message_crisp(cached_response, session_id)
#             else:
#                 socketio.emit('start', {'user_id': user_id, 'message': 'Ваш запит в обробці. Це може зайняти до 1 хвилини'}, room=user_id)
#                 thread_openai_id = user_thread_mapping.get(user_id)
#                 # send_message_user(thread_openai_id, question)
#                 thread = threading.Thread(target=send_message_user, args=(thread_openai_id, user_first_msgs[0]))
#                 thread.start()
#                 print("Started thread SEND_MESSAGE_USER openai: " + thread.name)
#                 ai_response = retrieve_ai_response(thread_openai_id)
#                 if ai_response:
#                     socketio.emit('start', {'user_id': user_id, 'message': ai_response}, room=user_id)
#                     thread = threading.Thread(target=send_agent_message_crisp, args=(ai_response, session_id))
#                     thread.start()
#                     print("Started thread SEND_AGENT MESSAGE CRISP: " + thread.name)
#                     # send_agent_message_crisp(ai_response, session_id)

#     except Exception as e:
#         print(f"Error: {str(e)}")
#         socketio.emit('start', {'user_id': user_id, 'message': 'Щось пішло не так, спробуйте пізніше...'}, room=user_id)

# @app.route("/", methods=['POST', 'GET'])
# def receive_msg_from_client():
#     if request.method == 'POST':
#         if request.is_json:
#             data = request.get_json()
#             print("Received JSON data:", data)
            
#             # Extract the value of "question" directly
#             question_value = data.get('question', 'Question not found')
#             user_id = data.get('user_id')
#             print(user_id)
#             print(question_value)
#             session_id = user_session_mapping.get(user_id)
#             print(session_id)

#             execute_flow(question_value, user_id, session_id)
            
#             # Return the value of "question" directly
#             return jsonify(question_value)

#         else:
#             print("Invalid request. Expected JSON content type.")
#     if request.method == 'GET':
#         return jsonify("response",)
    
# if __name__ == "__main__":
#     socketio.run()



    