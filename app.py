import re
import asyncpg
from flask_cors import CORS
import socketio
import asyncio
import aiohttp
from aiohttp import web
from dotenv import load_dotenv
import os
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
socket_io = SocketIO(app, cors_allowed_origins='*')
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/', methods=['POST', 'GET'])
async def receive_msg_from_client():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            print("Received JSON data:", data)
    #             # Extract the value of "question" directly
#             question_value = data.get('question', 'Question not found')
#             user_id = data.get('user_id', 'User id not found')
#             # print("Received user_id with post request: " + user_id)
#             print("Received question with post request: " + question_value)
#             # session_id = user_session_mapping.get(user_id)
#             session_id = data.get('session_id')
#             print("Received session_id with post request: " + str(session_id))
#             question_answered = data.get('question_answered')
#             print("Received question_answered with post request: " + question_answered)
#             user_conversation_state = data.get('user_conversation_state')
#             print("Received user_coonversation_state with post request: " + user_conversation_state)
#             if session_id:
#                 await execute_flow_async(question_value, user_id, session_id, question_answered, user_conversation_state)
#                 await handle_user_conversation_state_3(user_id, question_answered, user_conversation_state, question_value, session_id)
            
#             # Return the value of "question" directly
#             return jsonify(question_value)

    if request.method == 'GET':
        return jsonify(message="Got the main page")

sio = socketio.AsyncClient()

# load_dotenv()

# db_config = {
#     'host': os.getenv('PGHOST'),
#     'database': os.getenv('PGDATABASE'),
#     'user': os.getenv('PGUSER'),
#     'password': os.getenv('PGPASSWORD'),
# }


# token = os.getenv('token')
# website_id = os.getenv('website_id')
# username = os.getenv('crisp_identifier')
# password = os.getenv('crisp_key')

# first_messages = []
# user_session_mapping = {}
# user_thread_mapping = {}
# message_data = {}

# async def start_conversation_crisp():
#     basic_auth_credentials = (username, password)
#     api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation"
#     headers = {
#         'Content-Type': 'application/json',
#         'User-Agent': 'PostmanRuntime/7.35.0',
#         'X-Crisp-Tier': 'plugin'
#     }

#     async with aiohttp.ClientSession() as session:
#         async with session.post(
#             api_url,
#             headers=headers,
#             auth=aiohttp.BasicAuth(*basic_auth_credentials),
#         ) as response:
#             if response.status == 201:
#                 data = await response.json()
#                 current_session_id = data['data']['session_id']
#                 print(current_session_id)
#                 return current_session_id
#             else:
#                 print(f"Request failed with status code {response.status}.")
#                 print(await response.text())

# async def start_thread_openai(user_id):
#     global thread_openai_id
#     api_url = "https://api.openai.com/v1/threads"
#     headers = {
#         "OpenAI-Beta": "assistants=v1",
#         "User-Agent": "PostmanRuntime/7.34.0",
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {token}"
#     }

#     async with aiohttp.ClientSession() as session:
#         async with session.post(
#             api_url,
#             headers=headers,
#             json={},
#         ) as response:
#             if response.status == 200:
#                 data = await response.json()
#                 thread_openai_id = data.get("id")
#                 print("Thread started successfully! Thread id:", thread_openai_id)
#                 return thread_openai_id
#             elif response.status == 401:  # Unauthorized (Invalid API key)
#                 error_message = (await response.json()).get("error", {}).get("message", "")
#                 if "Incorrect API key provided" in error_message:
#                     print("Error starting OpenAI thread: Incorrect API key provided")
#                     socket_io.emit('start', {'user_id': user_id, 'message': "Технічні неполадки. Відповімо скоро"})
#                 else:
#                     print("Error starting OpenAI thread:", response.status, error_message)
#                 return None

# async def send_user_message_crisp(question, session_id):
#     api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/message"
#     basic_auth_credentials = (username, password)
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

#     async with aiohttp.ClientSession() as session:
#         async with session.post(
#             api_url,
#             headers=headers,
#             auth=aiohttp.BasicAuth(*basic_auth_credentials),
#             json=payload
#         ) as response:
#             if response.status == 202:
#                 print(await response.json())
#             else:
#                 print(f"Request failed with status code {response.status}.")
#                 print(await response.text())

# global_fingerprint = None

# async def send_agent_message_crisp(response, session_id):
#     global global_fingerprint
#     api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/message"
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

#     async with aiohttp.ClientSession() as session:
#         async with session.post(
#             api_url,
#             headers=headers,
#             auth=aiohttp.BasicAuth(*basic_auth_credentials),
#             json=payload
#         ) as response:
#             if response.status == 202:
#                 data = await response.json()
#                 global_fingerprint = data['data']['fingerprint']
#                 print(global_fingerprint)
#                 return global_fingerprint
#             else:
#                 print(f"Request failed with status code {response.status}.")
#                 print(await response.text())

# user_conversation_state = {}
# user_first_messages = {}
# retrieved_session_ids = []
# user_questions_mapping = {}
# user_conv_state_mapping = {}

# async def send_message_user_async(thread_openai_id, question):
#     print(question)
#     print("Going into send_message_user")
#     try:
#         if thread_openai_id and question:
#             api_url = f"https://api.openai.com/v1/threads/{thread_openai_id}/messages"
#             api_headers = {
#                 "Content-Type": "application/json",
#                 "Authorization": f"Bearer {token}",
#                 "OpenAI-Beta": "assistants=v1",
#                 "User-Agent": "PostmanRuntime/7.34.0"
#             }

#             api_json_payload = {
#                 "role": "user",
#                 "content": question
#             }
#             async with aiohttp.ClientSession() as session:
#                 async with session.post(api_url, headers=api_headers, json=api_json_payload) as response:
#                     response.raise_for_status()
#                     api_data = await response.json()

#                     # Create a run after sending a message
#                     await create_run_async(session, thread_openai_id)

#                     return api_data

#     except aiohttp.ClientError as e:
#             print(f"API Request Error: {e}")
#             return None

# assistant_id = os.getenv('assistant_id')

# async def create_run_async(session, thread_openai_id):
#     try:
#         api_url = f"https://api.openai.com/v1/threads/{thread_openai_id}/runs"
#         headers = {
#             "Content-Type": "application/json",
#             "Authorization": f"Bearer {token}",
#             "OpenAI-Beta": "assistants=v1",
#             "User-Agent": "PostmanRuntime/7.34.0"
#         }
#         json_payload = {
#             "assistant_id": assistant_id
#         }

#         async with session.post(api_url, headers=headers, json=json_payload) as response:
#             response.raise_for_status()
#             data = await response.json()
#             run_id = data.get('id')
#             print("Run started successfully! " + run_id)
#             await check_run_status_async(session, thread_openai_id, run_id)

#     except aiohttp.ClientError as e:
#         print(f"API Request Error: {e}")


# async def check_run_status_async(session, thread_openai_id, run_id):
#     api_url = f"https://api.openai.com/v1/threads/{thread_openai_id}/runs/{run_id}"
#     headers = {
#         "Authorization": f"Bearer {token}",
#         "OpenAI-Beta": "assistants=v1",
#         "User-Agent": "PostmanRuntime/7.34.0"
#     }

#     while True:
#         async with session.get(api_url, headers=headers) as response:
#             response.raise_for_status()
#             data = await response.json()
#             status = data.get("status")

#             if status == "completed":
#                 print("Run status is completed. Retrieving AI response.")
#                 break  # Exit the loop if the run is completed
#             else:
#                 print(f"Run status is {status}. Waiting for completion.")
#                 await asyncio.sleep(5)  # Wait for 5 seconds before checking again


# async def retrieve_ai_response_async(thread_openai_id):
#     api_url = f"https://api.openai.com/v1/threads/{thread_openai_id}/messages"
#     print("Retrieving response")
#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.get(
#                 api_url,
#                 headers={
#                     "Authorization": f"Bearer {token}",
#                     "OpenAI-Beta": "assistants=v1",
#                     "User-Agent": "PostmanRuntime/7.34.0",
#                     "Accept": "*/*"
#                 },
#             ) as response:
#                 response.raise_for_status()

#                 if response.status == 200:
#                     content_type = response.headers.get('Content-Type', 'application/json')

#                         # Check if 'data' key exists and is a list
#                     if 'application/json' in content_type:
#                         data = await response.json()
#                         print("API Response:", data)

#                         # Check if 'data' key exists and is a list
#                         if 'data' in data:
#     # Filter messages based on role
#                             assistant_messages = [msg['content'][0]['text']['value'] for msg in data['data'] if msg['role'] == 'assistant']

#                             if assistant_messages:
#                                 ai_response = assistant_messages[0]  # Retrieve the latest assistant message
#                                 print("AI Response:", ai_response)
#                                 return ai_response
#                             else:
#                                 print("No assistant messages found in the response.")
#                                 return None
#                         else:
#                             print("Invalid response structure. 'data' key is missing or not a list.")
#                             return None
#                     else:
#                         print("Invalid Content-Type. Expected application/json, got:", content_type)
#                         return None
#                 else:
#                     print("Error retrieving AI response:", response.status, await response.text())
#                     return None

#     except aiohttp.ClientError as e:
#         print(f"Async API Request Error: {e}")
#         return None

    
# async def query_with_caching(question):
#     connection = None
#     try:
#         connection = await asyncpg.connect(**db_config)

#         # Convert question to lowercase and remove accents
#         cleaned_question = re.sub(r'[^\w\s]', '', question).lower()

#         # Use a simplified query without regular expressions
#         query = "SELECT answer FROM chat_cache WHERE unaccent(LOWER(question)) = unaccent($1)"
#         result = await connection.fetchval(query, cleaned_question)

#         print("Querying db")

#         return result

#     except asyncpg.PostgresError as e:
#         print(f"Error connecting to the database: {e}")

#     finally:
#         try:
#             if connection:
#                 await connection.close()
#         except asyncpg.PostgresError as e:
#             print(f"Error closing the database connection: {e}")

# async def patch_profile(nickname, phone_number, session_id):
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

#     async with aiohttp.ClientSession() as session:
#         try:
#             async with session.patch(
#                 api_url,
#                 headers=headers,
#                 auth=aiohttp.BasicAuth(*basic_auth_credentials),
#                 json=payload
#             ) as response:
#                 response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
#                 print(await response.json())

#         except aiohttp.ClientError as err:
#             print(f"Aiohttp Client Error: {err}")
#         except Exception as err:
#             print(f"Error: {err}")


# async def check_conversation(session_id):
#     basic_auth_credentials = aiohttp.BasicAuth(login=username, password=password)
#     api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/messages"
#     headers = {
#         'Content-Type': 'application/json',
#         'User-Agent': 'PostmanRuntime/7.35.0',
#         'X-Crisp-Tier': 'plugin'
#     }
#     try:
#         async with aiohttp.ClientSession(auth=basic_auth_credentials) as session:
#             async with session.get(api_url, headers=headers) as response:
#                 response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
#                 data = await response.json()

#                 user_content_after_name = None
#                 user_content_after_number = None
#                 found_name_question = False
#                 found_number_question = False

#                 for item in data.get("data", [0]):
#                     print("Item:", item)
#                     if item.get("from") == "operator" and "Як до вас звертатись?" in item.get("content", ""):
#                         found_name_question = True
#                     elif found_name_question and item.get("from") == "user":
#                         user_content_after_name = item["content"]

#                         print("User's message after 'What is your name?':", user_content_after_name)
#                         break

#                 for item in data.get("data", [1]):
#                     print("Item:", item)
#                     if item.get("from") == "operator" and "Вкажіть будь ласка свій номер телефону для подальшого зв'язку з Вами." in item.get("content", ""):
#                         found_number_question = True
#                     elif found_number_question and item.get("from") == "user":
#                         user_content_after_number = item["content"]
#                         print("User's message after 'What is your phone number?':", user_content_after_number)
#                         break

#                 await patch_profile(user_content_after_name, user_content_after_number, session_id)
#                 return user_content_after_name
            
#     except aiohttp.ClientError as err:
#         print(f"HTTP Error: {err}")

# async def execute_flow_async(message, user_id, session_id, question_answered, user_conversation_state):
#     print("Question answered in execute_flow " + str(question_answered))
#     print("User conversation state " + str(user_conversation_state))

#     question = message
#     user_first_msgs = user_first_messages.get(user_id, [])

#     if not question:
#         raise ValueError("Invalid payload: 'question' is required.")

#     await send_user_message_crisp(question, session_id)

#     try:
#         if question_answered == 'False' and user_conversation_state == '0':
#             user_first_msgs.append(question)
#             user_first_messages[user_id] = user_first_msgs
#             print("User first message: " + str(user_first_msgs))
#             await send_agent_message_crisp('Як до вас звертатись?', session_id)
#             user_conversation_state = 1
#             socket_io.emit('update_variables', {
#                 'user_id': user_id,
#                 'question_answered': question_answered,
#                 'user_conversation_state': user_conversation_state,
#                 'user_first_messages': user_first_msgs,
#                 'session_crisp': session_id,
#             }, room=user_id)
#             print("Emitting the updated variables")

#         if question_answered == 'False' and user_conversation_state == '1':
#             user_first_messages[user_id] = user_first_msgs
#             print("User first message: " + str(user_first_msgs))
#             await send_agent_message_crisp("Вкажіть будь ласка свій номер телефону для подальшого зв'язку з Вами.", session_id)
#             user_conversation_state = 2
#             print("Emitting the updated variables")
#             socket_io.emit('update_variables', {
#                 'user_id': user_id,
#                 'question_answered': question_answered,
#                 'user_conversation_state': user_conversation_state,
#                 'user_first_messages': user_first_msgs,
#                 'session_crisp': session_id,
#             }, room=user_id)

#         if question_answered == 'False' and user_conversation_state == '2':
#             user_first_messages[user_id] = user_first_msgs
#             print("User first message: " + str(user_first_msgs))
#             await send_agent_message_crisp("Ваш запит в обробці. Це може зайняти до 1 хвилини", session_id)
#             print("Emitting the updated variables")
#             socket_io.emit('update_variables', {
#                 'user_id': user_id,
#                 'question_answered': question_answered,
#                 'user_conversation_state': user_conversation_state,
#                 'user_first_messages': user_first_msgs,
#                 'session_crisp': session_id,
#             }, room=user_id)
#             cached_response = await query_with_caching(user_first_msgs[0])
#             print("User first message to retrieve in this phase: " + user_first_msgs[0])
#             print(cached_response)
#             thread_openai_id = user_thread_mapping.get(user_id)
#             user_content_name = await check_conversation(session_id)
#             if cached_response:
#                 await send_agent_message_crisp(cached_response, session_id)
#             else:
#                 print('Going into the condition')
#                 await send_agent_message_crisp("Ваш запит в обробці. Це може зайняти до 1 хвилини", session_id)
#                 thread_openai_id = user_thread_mapping.get(user_id)
#                 question_name =  user_content_name + ". " + user_first_msgs[0]
#                 await send_message_user_async(thread_openai_id, question_name)
#                 ai_response = await retrieve_ai_response_async(thread_openai_id)
#                 if ai_response:
#                     await send_agent_message_crisp(ai_response, session_id)
#             user_conversation_state = '3'
#             question_answered = 'True'
#             socket_io.emit('update_variables', {
#                 'user_id': user_id,
#                 'question_answered': question_answered,
#                 'user_conversation_state': user_conversation_state,
#                 'user_first_messages': user_first_msgs,
#                 'session_crisp': session_id,
#             }, room=user_id)

#             return
        
#     except Exception as e:
#         print(f"Error: {str(e)}")
#         socket_io.emit('start', {'user_id': user_id, 'message': 'Щось пішло не так, спробуйте пізніше...'}, room=user_id)

# async def handle_user_conversation_state_3(user_id, question_answered, user_conversation_state, question, session_id):
#     user_session_mapping[user_id] = session_id
#     retrieved_session_ids.append(session_id)
#     print(user_id, session_id)
#     print("Mapped session_id to user_id")
#     try:
#            if question_answered == 'True' and user_conversation_state == '3':
#             cached_response = await query_with_caching(question)

#             if cached_response:
#                 await send_agent_message_crisp(cached_response, session_id)
#             else:
#                 user_content_name = await check_conversation(session_id)
#                 question_name = user_content_name + ". " + question
#                 print(question_name)
#                 thread_openai_id = user_thread_mapping.get(user_id)
#                 await send_message_user_async(thread_openai_id, question_name)
#                 ai_response = await retrieve_ai_response_async(thread_openai_id)
#                 if ai_response:
#                     await send_agent_message_crisp(ai_response, session_id)

#     except Exception as e:
#         print(f"Error: {str(e)}")
#         socket_io.emit('start', {'user_id': user_id, 'message': 'Щось пішло не так, спробуйте пізніше...'}, room=user_id)


@socket_io.on('connect')
def handle_connect():
    print("Connected user")

# @socket_io.on('user_id')
# def handle_join_userid(data):
#     user_id = data.get('user_id')
#     print("User id event: " + user_id)

#     if user_id not in socket_io.server.rooms(request.sid):
#         join_room(user_id)
#         print(f"User {user_id} successfully joined the room")
#     else:
#         print(f"User {user_id} is already in the room")

# @socket_io.on('set_defaults')
# def handle_init_connection(data):
#     user_id_received = data.get('user_id')
#     print("Emitting created variables")
#     print('Received on set_defaults user_id: ' + user_id_received) 
#     question_answered_received = data.get('question_answered')
#     print('Received on set_defaults question_answered_received: ' + question_answered_received)

#     session_id_crisp = data.get('session_crisp')
#     user_conv_state = data.get('user_conversation_state')
#     print('Received on set_defaults user_conv_state: ' + str(user_conv_state))
#     user_first_msgs = data.get('user_first_messages')
#     print('Received on set_defaults user_first_msgs: ' + str(user_first_msgs))

#     asyncio.run(handle_connection_async(user_id_received, question_answered_received, user_conv_state, user_first_msgs, session_id_crisp))

# async def handle_connection_async(user_id_received, question_answered_received, user_conv_state, user_first_msgs, session_id_crisp):
#     global question_answered
#     global user_conversation_state
#     global user_first_messages
#     if session_id_crisp == "set" or session_id_crisp is None:
#         session_id_crisp = await start_conversation_crisp()
#     user_session_mapping[user_id_received] = session_id_crisp
#     print("Assigned session_id: " +  session_id_crisp)

#     retrieved_session_ids.append(session_id_crisp)
#     print(user_id_received, session_id_crisp)
#     thread_openai_id = await start_thread_openai(user_id_received)
#     user_thread_mapping[user_id_received] = thread_openai_id
#     print("Thread openai" + thread_openai_id)
#     user_questions_mapping[user_id_received] = question_answered_received
#     print('Mapped question_answer: ' + str(user_questions_mapping[user_id_received]))


#     # Reset state for the new user
#     question_answered = question_answered_received
#     print("Assigned question_answered: " + question_answered)
#     user_conversation_state[user_id_received] = user_conv_state
#     print("Assigned user_conversation_state: " + str(user_conversation_state[user_id_received]))
#     user_first_messages[user_id_received] = user_first_msgs
#     print("Assigned user_first_messages: " +  str(user_first_messages[user_id_received]))
#     user_id = user_id_received
#     print("Assigned user_id: " +  user_id)
#     socket_io.emit('update_variables', {
#         'user_id': user_id,
#         'question_answered': question_answered,
#         'user_conversation_state': user_conversation_state[user_id],
#         'user_first_messages': user_first_msgs,
#         'session_crisp': session_id_crisp
#     }, room=user_id)


@socket_io.on('disconnect')
def handle_disconnect():
    print('Client disconnected')  


##################### RTM part START #######################

async def on_connect():
    #   // Authenticate to the RTM API
    await sio.emit("authentication", {
        "tier": "plugin",
        "username" : os.getenv('crisp_identifier'),
        "password" : os.getenv("crisp_key"),

        "events" : [
        "message:received",
        "message:updated",
        "message:removed"
        ],
        "rooms": [
            "84ca425b-3cf3-4a00-836c-1212d36eba0c"
        ]
    });
    print("RTM API connected")

async def authenticated(data):
    print(data)

async def unauthorized(data):
    print(data)


async def message_received_event(message):
        print("Got removed msg event" + str(message))
        # session_id = message['session_id']
        # fingerprint = message['fingerprint']
        # if session_id in retrieved_session_ids:
        #             user_id_for_session = next((uid for uid, sid in user_session_mapping.items() if sid == session_id), None)

        #             if user_id_for_session:
        #                 print(f"Message received for user {user_id_for_session}: {message['content']}")
        #                 message_data[fingerprint] = message['content']
        #                 socket_io.emit('start', {'user_id': user_id_for_session, 'message': message['content']}, room=user_id_for_session)
        #             else:
        #                 print(f"Session ID {session_id} not mapped to any user.")
        # else:
        #         print(f"Invalid session ID: {session_id}")
        # pass
          
async def message_updated_event(message):
        print("Got removed msg event" + str(message))
        # fingerprint = message['fingerprint']
        # new_message = message['content']
        # session_id = message['session_id']
        # if fingerprint in message_data:
        #         if session_id in retrieved_session_ids:
        #             user_id_for_session = next((uid for uid, sid in user_session_mapping.items() if sid == session_id), None)

        #             if user_id_for_session:
        #                 old_message = message_data[fingerprint]
        #                 message_data[fingerprint] = new_message
        #                 socket_io.emit('delete_message', {'user_id': user_id_for_session, 'message': old_message}, room=user_id_for_session)
        #                 print(f"Message edited. Old message: {old_message}, New message: {new_message}")
        #                 socket_io.emit('start', {'user_id': user_id_for_session, 'message': new_message}, room=user_id_for_session)
        # else:
        #         print(f"No message found for fingerprint: {fingerprint}")
        # pass
 
async def message_removed_event(message):
    print("Got removed msg event" + str(message))
            # session_id = message['session_id']
            # fingerprint = message['fingerprint']
            # if session_id in retrieved_session_ids:
            #     user_id_for_session = next((uid for uid, sid in user_session_mapping.items() if sid == session_id), None)

            #     if user_id_for_session:
            #         if fingerprint in message_data:
            #             del_message = message_data[fingerprint]

            #             print("User id to submit delete message: " + user_id_for_session)
            #             socket_io.emit('user_id', {'response': user_id_for_session})
            #             socket_io.emit('delete_message', {'user_id': user_id_for_session, 'message': del_message}, room=user_id_for_session)

            #             del message_data[fingerprint]
            #             print(f"Message to delete: {del_message}")
            #         else:
            #             print(f"No message found for fingerprint: {fingerprint}")
            #         pass 

   
async def on_disconnect():
    print("RTM API disconnected")

async def on_connect_error(error):
    print("RTM API connection error", error)

async def on_reconnect():
    print("RTM API reconnecting...")

async def on_error(error):
    print("RTM API error", error)

async def connect_to_socket():
    endpoint_url = "wss://app.relay.crisp.chat/p/68/"

    sio.on('connect', on_connect)
    sio.on('authenticated', authenticated)
    sio.on('unauthorized', unauthorized)
    sio.on('message:received', message_received_event)
    sio.on('message:updated', message_updated_event)
    sio.on('message:removed', message_removed_event)
    sio.on('disconnect', on_disconnect)
    sio.on('connect_error', on_connect_error)

    # Handle IO events
    sio.on('reconnect', on_reconnect)
    sio.on('error', on_error)

    print(endpoint_url)
    
    await sio.connect(endpoint_url, transports='websocket')
    
    return sio

##################### RTM part END #######################

async def main():
     while True:
        try:
            client = await connect_to_socket()
            print("Connected. Performing actions...")

            # Simulate some activity
            await asyncio.sleep(120)

        except Exception as e:
            print(f"An error occurred: {e}")
            # Handle the error (e.g., log it, sleep before retrying, etc.)
            await asyncio.sleep(5)

        finally:
            await client.disconnect()

# Use asyncio.run to run the main coroutine
def start_main_tasks():
    asyncio.run(main())

socket_io.start_background_task(start_main_tasks)

if __name__ == '__main__':
    socket_io.run(app, debug=True)