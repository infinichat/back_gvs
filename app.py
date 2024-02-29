import asyncio
import os
import aiohttp
import asyncpg
from flask import Flask, request
from flask_socketio import SocketIO, join_room
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
import re
from flask_cors import CORS
import psycopg2
from psycopg2 import sql

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
#  message_queue='redis://'
socket_io = SocketIO(app, cors_allowed_origins='*', ping_timeout = 5, ping_interval = 10)

load_dotenv()

db_config = {
    'host': os.getenv('PGHOST'),
    'database': os.getenv('PGDATABASE'),
    'user': os.getenv('PGUSER'),
    'password': os.getenv('PGPASSWORD'),
}

db_config_2 = {
    'host': os.getenv('host'),
    'database': os.getenv('db'),
    'user': os.getenv('user'),
    'password': os.getenv('pswd')
}

website_id = os.getenv('website_id')
username = os.getenv('crisp_identifier')
password = os.getenv('crisp_key')
token = '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'

user_thread_mapping = {}
user_thread_mapping_session_id = {}
import aiohttp

async def start_thread_openai(user_id):
    global thread_openai_id  # Note: Global variables in async functions should be avoided if possible
    api_url = "https://api.openai.com/v1/threads"
    headers = {
        "OpenAI-Beta": "assistants=v1",
        "User-Agent": "PostmanRuntime/7.34.0",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, headers=headers, json={}) as response:
                if response.status == 200:
                    data = await response.json()
                    thread_openai_id = data.get("id")
                    print("Thread started successfully! Thread id:", thread_openai_id)
                    return thread_openai_id
                elif response.status == 401:  # Unauthorized (Invalid API key)
                    error_message = (await response.json()).get("error", {}).get("message", "")
                    if "Incorrect API key provided" in error_message:
                        print("Error starting OpenAI thread: Incorrect API key provided")
                        socket_io.emit('start', {'user_id': user_id, 'message': "Технічні неполадки. Відповімо скоро"})
                    else:
                        print("Error starting OpenAI thread:", response.status, error_message)
                    return None
    except aiohttp.ClientError as err:
        print(f"HTTP Error: {err}")
        return None

async def start_thread_openai_session_id(session_id):
    global thread_openai_id  # Note: Global variables in async functions should be avoided if possible
    api_url = "https://api.openai.com/v1/threads"
    headers = {
        "OpenAI-Beta": "assistants=v1",
        "User-Agent": "PostmanRuntime/7.34.0",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, headers=headers, json={}) as response:
                if response.status == 200:
                    data = await response.json()
                    thread_openai_id = data.get("id")
                    print("Thread started successfully! Thread id:", thread_openai_id)
                    return thread_openai_id
                elif response.status == 401:  # Unauthorized (Invalid API key)
                    error_message = (await response.json()).get("error", {}).get("message", "")
                    if "Incorrect API key provided" in error_message:
                         message = "Технічні неполадки. Відповімо незабаром."
                         await send_agent_message_crisp(message, session_id)
                    #     print("Error starting OpenAI thread: Incorrect API key provided")
                    #     socket_io.emit('start', {'user_id': user_id, 'message': "Технічні неполадки. Відповімо скоро"})
                    else:
                        print("Error starting OpenAI thread:", response.status, error_message)
                    return None
    except aiohttp.ClientError as err:
        print(f"HTTP Error: {err}")
        return None


user_sid_mapping = {}
del_messages_map = {}
edit_messages_map = {}

@socket_io.on('connect')
def handle_connect():
    print("Connected user")


@socket_io.on('user_id')
def handle_join_userid(data):
    global cursor, conn
    user_id = data.get('user_id')
    user_sid = request.sid
    if user_id in user_sid_mapping:
        # If user_id exists, append the new user_sid to the list
        user_sid_mapping[user_id].append(user_sid)
    else:
        # If user_id does not exist, create a new list with the current user_sid
        user_sid_mapping[user_id] = [user_sid]
    join_room(user_id)
    print(f"User {user_id} successfully joined the room")
    print("User id event: " + user_id)
    try: 
        select_messages_query = sql.SQL("SELECT message_content, fingerprint FROM deactivated_messages WHERE user_id = {}").format(
            sql.Literal(user_id)
        )
        try:
            cursor.execute(select_messages_query)
        except psycopg2.Error as exc:
            print(exc)
            cursor.close()
            conn.close()

            conn = psycopg2.connect(**db_config_2)
            cursor = conn.cursor()

            cursor.execute(select_messages_query)

        messages_result = cursor.fetchall()

        for message in messages_result:
            message_content = message[0] 
            print(message_content)
            # user_sid = request.sid
            # user_sid_mapping[user_id] = user_sid
                # join_room(user_id)
            socket_io.emit('start', {'user_id': user_id, 'message': message_content}, room=user_id)

        if user_id in del_messages_map:
                # del_messages_map[user_id] = []

            # Append the del_message to the list
                del_message = del_messages_map[user_id]
                if del_message:
                    socket_io.emit('delete_message', {'user_id': user_id, 'message': del_message}, room=user_id)
                    print("Message to delete: " + del_message)
            # Clear the del_messages for the user_id since they have been emitted
                del del_messages_map[user_id]
        
        if user_id in edit_messages_map:
                # del_messages_map[user_id] = []

            # Append the del_message to the list
                edit_message = edit_messages_map[user_id]
                if edit_message:
                        socket_io.emit('start', {'user_id': user_id, 'message': edit_message}, room=user_id)
            # Clear the del_messages for the user_id since they have been emitted
                del edit_messages_map[user_id]
        
        # Optionally, you can delete the retrieved messages from the database after processing
                
        delete_messages_query = sql.SQL("DELETE FROM deactivated_messages WHERE user_id = {}").format(
            sql.Literal(user_id)
        )
        try:
            cursor.execute(delete_messages_query)
            conn.commit()
        except psycopg2.Error as exc:
            print(exc)
            cursor.close()
            conn.close()

            conn = psycopg2.connect(**db_config_2)
            cursor = conn.cursor()

            cursor.execute(delete_messages_query)
            conn.commit()

    except psycopg2.Error as e:
    # Handle the exception as needed
        if "no results to fetch" in str(e):
            print("No messages to fetch.")



@socket_io.on('set_defaults')
def handle_init_connection(data):
    user_id_received = data.get('user_id')
    print("Emitting created variables")
    print('Received on set_defaults user_id: ' + user_id_received)  # Convert user_id to str
    question_answered_received = data.get('question_answered')
    print('Received on set_defaults question_answered_received: ' + question_answered_received)

    session_id_crisp = data.get('session_crisp')
    user_conv_state = data.get('user_conversation_state')
    print('Received on set_defaults user_conv_state: ' + str(user_conv_state))
    user_first_msgs = data.get('user_first_messages')
    print('Received on set_defaults user_first_msgs: ' + str(user_first_msgs))
# def start_connection_tasks(user_id_received, question_answered_received, user_conv_state, user_first_msgs, session_id_crisp):
    handle_connection_async(user_id_received, question_answered_received, user_conv_state, user_first_msgs, session_id_crisp)

conn = psycopg2.connect(**db_config_2)
cursor = conn.cursor()
def handle_connection_async(user_id_received, question_answered_received, user_conv_state, user_first_msgs, session_id_crisp):
    global cursor, conn
    if session_id_crisp == "set" or session_id_crisp is None:
        session_id_crisp = start_conversation_crisp()
    # thread_openai_id = await start_thread_openai(user_id_received)
    # user_thread_mapping[user_id_received] = thread_openai_id
    print("Assigned session_id: " +  session_id_crisp)
    print(user_id_received, session_id_crisp)
    question_answered = question_answered_received
    print("Assigned question_answered: " + question_answered)
    # try:
    #     insert_query = sql.SQL("INSERT INTO users_tab (user_id, session_id, question_answered, user_conversation_state) VALUES ({}, {}, {}, {})").format(
    #         # sql.Literal(''),  # Assuming 'question_value' is not used in your function
    #         sql.Literal(user_id_received),
    #         sql.Literal(session_id_crisp),
    #         sql.Literal(question_answered),
    #         sql.Literal(user_conv_state)
    #     )
        
    #     cursor.execute(insert_query)
    #     conn.commit()
    #     print("Data inserted into the PostgreSQL table.")
    # except psycopg2.Error as exc:
    #     print(exc)
    #     cursor.close()
    #     conn.close()

    #     conn = psycopg2.connect(**db_config_2)
    #     cursor = conn.cursor()

    #     cursor.execute(insert_query)
    #     conn.commit()
    # except Exception as e:
    #     print("Error inserting data into the PostgreSQL table:", e)
    #     pass
    print("Assigned user_id: " +  user_id_received)
    socket_io.emit('update_variables', {
        'user_id': user_id_received,
        'question_answered': question_answered,
        'user_conversation_state': user_conv_state,
        'user_first_messages': user_first_msgs,
        'session_crisp': session_id_crisp
    }, room=user_id_received)

message_data = {}
import socketio

sio = socketio.AsyncClient()

async def on_connect():
    #   // Authenticate to the RTM API
    await sio.emit("authentication", {
        "tier": "plugin",
        # // Configure your Crisp authentication tokens
        "username" : "5609c6ae-2281-45fe-b66f-01f3976a8fec",
        "password" : "3da36469d1da798b3b4ce23eae580637b0a308ea654c71d78cff08937604f191",

        # // Subscribe to target event namespaces
        "events" : [
        "message:received",
        "message:updated",
        "message:removed",
        "message:send",
        'session:set_segments'
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

async def message_send_event(message):
    global cursor, conn
    print('Got a message from user:', message['content'], message['session_id'], message['fingerprint'])
    
    # question_value = message['content']
    # session_id = message['session_id']
    
    # if user_id and session_id and question_answered and user_conversation_state:
    #     await execute_flow_async(question_value, user_id, session_id, question_answered, user_conversation_state)
    #     await handle_user_conversation_state_3(user_id, question_answered, user_conversation_state, question_value, session_id)
    # else: 
    #     await handle_user_conversation_result(question_value, session_id)

@socket_io.on('disconnect')
def handle_disconnect():
    sid = request.sid
    print(f'Client disconnected: sid={sid}')

    # Iterate over the items in user_sid_mapping to find and remove the disconnected user_id
    for user_id, sid_list in list(user_sid_mapping.items()):
        if sid in sid_list:
            sid_list.remove(sid)
            print(f"Removed sid {sid} from user {user_id}'s list of sids")

            # If the user_id's list of sids is empty, remove the user_id from user_sid_mapping
            if not sid_list:
                del user_sid_mapping[user_id]
                print(f"Removed user {user_id} from user_sid_mapping")

            break

async def message_received_event(message):
    global cursor, conn
    print('Got a message from agent: ' + message['content'], message['session_id'], message['fingerprint'])
    session_id = message['session_id']
    fingerprint = message['fingerprint']

        # Check if the client is in the set of disconnected clients
    select_query = sql.SQL("SELECT user_id, session_id, question_answered, user_conversation_state FROM users_tab WHERE session_id = {}").format(
            sql.Literal(session_id)
    )
    try: 
            cursor.execute(select_query)
    except psycopg2.Error as exc:
            print(str(exc))
            cursor.close()
            conn.close()

            conn = psycopg2.connect(**db_config_2)
            cursor = conn.cursor()

            cursor.execute(select_query)
    result = cursor.fetchone()
    print(result)

    if result:
                user_id, session_id, question_answered, user_conversation_state = result

                # Check if user_id is not in user_sid_mapping
                if user_id not in user_sid_mapping or not user_sid_mapping[user_id]:
                    print(f"User {user_id} is not connected. The message won't be emitted.")
                    insert_query = sql.SQL("INSERT INTO deactivated_messages(user_id, message_content, fingerprint, session_id) VALUES ({}, {}, {}, {})").format(
                        sql.Literal(user_id),
                        sql.Literal(message['content']),
                        sql.Literal(fingerprint),
                        sql.Literal(session_id)
                    )
                    cursor.execute(insert_query)
                    # Commit the transaction
                    conn.commit()
                    message_data[fingerprint] = message['content']

                    return

                message_data[fingerprint] = message['content']
                socket_io.emit('start', {'user_id': user_id, 'message': message['content']}, room=user_id)
    else:
         print("Didn't go into this condition")

async def message_updated_event(message):
    global cursor, conn
    print('Got a updated message: ' + message['content'], message['fingerprint']);
    fingerprint = message['fingerprint']
    new_message = message['content']
    session_id = message['session_id']
    if fingerprint in message_data:
        select_query = sql.SQL("SELECT user_id, session_id, question_answered, user_conversation_state FROM users_tab WHERE session_id = {}").format(
                sql.Literal(session_id)
            )

        try:
            cursor.execute(select_query)
        
        except psycopg2.Error as exc:
                print(str(exc))
                cursor.close()
                conn.close()

                conn = psycopg2.connect(**db_config_2)
                cursor = conn.cursor()

                cursor.execute(select_query)

        result = cursor.fetchone()
        print(result)

        if result:
                user_id, session_id, question_answered, user_conversation_state = result  
        if user_id not in user_sid_mapping or not user_sid_mapping[user_id]:
                    print(f"User {user_id} is not connected. The edited message won't be emited.")
                    old_message = message_data[fingerprint]
                    # Update the message content in the dictionary
                    message_data[fingerprint] = new_message

                    print(old_message)
                    print(new_message)

                    # Update the message content in the database table
                    update_query = sql.SQL("UPDATE deactivated_messages SET message_content = {} WHERE user_id = {} AND message_content = {}").format(
                        sql.Literal(new_message),
                        sql.Literal(user_id),
                        sql.Literal(old_message)
                        # sql.Literal(str(fingerprint))
                    )
                    cursor.execute(update_query)
                    if cursor.rowcount > 0:
                        print(f"{cursor.rowcount} row(s) deleted.")
                    else:
                        print("No rows deleted.")
                        del_messages_map[user_id] = old_message
                        edit_messages_map[user_id] = new_message
                    # Commit the transaction
                    conn.commit()
                    return
    
    if fingerprint in message_data:
        select_query = sql.SQL("SELECT user_id, session_id, question_answered, user_conversation_state FROM users_tab WHERE session_id = {}").format(
            sql.Literal(session_id)
        )

        cursor.execute(select_query)
        result = cursor.fetchone()
        print(result)

        if result:
            user_id, session_id, question_answered, user_conversation_state = result  
            old_message = message_data[fingerprint]
            message_data[fingerprint] = new_message
            socket_io.emit('delete_message', {'user_id': user_id, 'message': old_message}, room=user_id)
            print(f"Message edited. Old message: {old_message}, New message: {new_message}")
            socket_io.emit('start', {'user_id': user_id, 'message': new_message}, room=user_id)
        else:
                print(f"No message found for fingerprint: {fingerprint}")
    else:
         print("Didn't go into this condition")

async def message_removed_event(message):
        global cursor, conn
        session_id = message['session_id']
        fingerprint = message['fingerprint']

        select_query = sql.SQL("SELECT user_id, session_id, question_answered, user_conversation_state FROM users_tab WHERE session_id = {}").format(
            sql.Literal(session_id)
        )
        try: 
            cursor.execute(select_query)
        
        except psycopg2.Error as exc:
                print(str(exc))
                cursor.close()
                conn.close()

                conn = psycopg2.connect(**db_config_2)
                cursor = conn.cursor()

                cursor.execute(select_query)

        result = cursor.fetchone()
        print(result)

        if result:
            user_id, session_id, question_answered, user_conversation_state = result

            if fingerprint in message_data:
                        if user_id not in user_sid_mapping or not user_sid_mapping[user_id]:
                                print(f"User {user_id} is not connected. The deleted message won't be emited.")
                                del_message = message_data[fingerprint]

                                # Update the message content in the database table
                                delete_query = sql.SQL("DELETE FROM deactivated_messages WHERE user_id = {} AND fingerprint = {} AND message_content = {}").format(
                                    sql.Literal(user_id),
                                    sql.Literal(str(fingerprint)),
                                    sql.Literal(del_message)
                                )
                                cursor.execute(delete_query)

                                if cursor.rowcount > 0:
                                    print(f"{cursor.rowcount} row(s) deleted.")
                                else:
                                    print("No rows deleted.")
                                    del_messages_map[user_id] = del_message
                                # Commit the transaction
                                conn.commit()
                                return
                        
                        del_message = message_data[fingerprint]

                        print("User id to submit delete message: " + user_id)
                        socket_io.emit('user_id', {'response': user_id})
                        socket_io.emit('delete_message', {'user_id': user_id, 'message': del_message}, room=user_id)

                        del message_data[fingerprint]
                        print(f"Message to delete: {del_message}")
            else:
                        print(f"No message found for fingerprint: {fingerprint}")
        else:
             print("Didn't go into this condition")
agent_flag_mapping = {}

async def message_set_segments(session):
     try: 
        global isAgentFlag, cursor, conn
        print("Got message segment: " + str(session))
        session_id = session['session_id']
        if session['segments'][1] == 'agent':
            print('Set the flag to agent')
            isAgentFlag=True
            agent_flag_mapping[session_id] = isAgentFlag
            print(agent_flag_mapping[session_id])
     except  Exception as e:
        print("An error occured" + str({e}))
        pass

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
    sio.on('message:send', message_send_event)
    sio.on('session:set_segments', message_set_segments)
    sio.on('disconnect', on_disconnect)
    sio.on('connect_error', on_connect_error)

    # Handle IO events
    sio.on('reconnect', on_reconnect)
    sio.on('error', on_error)

    print(endpoint_url)
    
    await sio.connect(endpoint_url, transports='websocket')
    
    return sio

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

def start_main_tasks():
    asyncio.run(main())

socket_io.start_background_task(start_main_tasks)


# @socket_io.on('disconnect')
# def handle_disconnect():
#     print('Client disconnected')


def start_conversation_crisp():
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
        auth=basic_auth_credentials,
    )

    if response.status_code == 201:
        data = response.json()
        current_session_id = data['data']['session_id']
        print(current_session_id)
        return current_session_id
    else:
        print(f"Request failed with status code {response.status_code}.")
        print(response.text)


def send_user_message_crisp(question, session_id):
    api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/message"
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

import aiohttp

async def send_agent_message_crisp(response, session_id):
    global global_fingerprint
    api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/message"
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

    async with aiohttp.ClientSession() as session:
        async with session.post(
            api_url,
            headers=headers,
            auth=aiohttp.BasicAuth(*basic_auth_credentials),
            json=payload
        ) as response:
            if response.status == 202:
                data = await response.json()
                global_fingerprint = data['data']['fingerprint']
                print(global_fingerprint)
                return global_fingerprint
            else:
                print(f"Request failed with status code {response.status}.")
                print(await response.text())


async def receive_msg_from_client(data):
    question_value = data.get('question', 'Question not found')
    session_id = data.get('session_id')
    user_id = data.get('user_id')
    user_conv_state = data.get('user_conversation_state')
    question_answered = data.get('question_answered')
    print('Got message from client' + str(question_value) + str(session_id) + str(user_conv_state) + str(question_answered))

    if user_id and session_id and question_answered and user_conv_state:
        await execute_flow_async(question_value, user_id, session_id, question_answered, user_conv_state)
        await handle_user_conversation_state_3(user_id, question_answered, user_conv_state, question_value, session_id)
    else: 
        await handle_user_conversation_result(question_value, session_id)


@socket_io.on('send_msgs')
def start_main_tasks_2(data):
    asyncio.run(receive_msg_from_client(data))

# socket_io.start_background_task(start_main_tasks_2)

    # if session_id:
    #     send_user_message_crisp(question_value, session_id)


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


# # Modify patch_profile to accept nickname and phone_number as arguments
async def patch_profile_async(nickname, phone_number, session_id):
    basic_auth_credentials = aiohttp.BasicAuth(username, password)
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
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                api_url,
                headers=headers,
                auth=basic_auth_credentials,
                json=payload
            ) as response:
                response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
                print(await response.json())
   
    except aiohttp.ClientError as err:
        print(f"Aiohttp Client Error: {err}")
    except aiohttp.ClientConnectionError as errc:
        print(f"Error Connecting: {errc}")
    except aiohttp.ClientResponseError as errh:
        print(f"HTTP Error: {errh}")
    except Exception as err:
        print(f"Error: {err}")


async def check_conversation(session_id):
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
                        print("User's message after 'What is your name?':", user_content_after_name)
                        break

                for item in data.get("data", [1]):
                    print("Item:", item)
                    if item.get("from") == "operator" and "Вкажіть будь ласка свій номер телефону для подальшого зв'язку з Вами." in item.get("content", ""):
                        found_number_question = True
                    elif found_number_question and item.get("from") == "user":
                        user_content_after_number = item["content"]
                        print("User's message after 'What is your phone number?':", user_content_after_number)
                        break

                await patch_profile_async(user_content_after_name, user_content_after_number, session_id)
                return user_content_after_name
            
    except aiohttp.ClientError as err:
        print(f"HTTP Error: {err}")

user_first_messages_mapping = {}

async def execute_flow_async(message, user_id, session_id, question_answered, user_conversation_state):
    global cursor, conn
    if session_id in agent_flag_mapping and agent_flag_mapping[session_id] is True:
        print("Agent flag for the current user is: " + str(agent_flag_mapping[session_id]))
        await send_agent_message_crisp("Ваш чат передано менеджеру.", session_id)
        return 
    else: 
        print("The flag is not available to a current user")
        print("Question answered in execute_flow " + str(question_answered))
        print("User conversation state " + str(user_conversation_state))
        question = message
        try:
                # Update the question_value if the conditions are met
                if question_answered == 'False' and user_conversation_state == '0':
                    user_first_messages = question
                    user_first_messages_mapping[user_id] = user_first_messages
                    await send_agent_message_crisp('Як до вас звертатись?', session_id)
                    user_conversation_state = 1
                    socket_io.emit('update_variables', {
                        'user_id': user_id,
                        'question_answered': question_answered,
                        'user_conversation_state': user_conversation_state,
                        'user_first_messages': user_first_messages,
                        'session_crisp': session_id,
                    }, room=user_id)
                    print("Emitting the updated variables")
                    print("USER FIRST MESSAGE IS: " + user_first_messages)

                if question_answered == 'False' and user_conversation_state == '1':
                    await send_agent_message_crisp("Вкажіть будь ласка свій номер телефону для подальшого зв'язку з Вами.", session_id)
                    user_conversation_state = 2
                    if user_id in user_first_messages_mapping:
                        user_first_messages = user_first_messages_mapping[user_id]
                        print("Emitting the updated variables")
                        socket_io.emit('update_variables', {
                            'user_id': user_id,
                            'question_answered': question_answered,
                            'user_conversation_state': user_conversation_state,
                            'user_first_messages': user_first_messages,
                            'session_crisp': session_id,
                        }, room=user_id)
                    # print("USER FIRST MESSAGE IS: " + user_first_messages)

                if question_answered == 'False' and user_conversation_state == '2':
                    await send_agent_message_crisp("Ваш запит в обробці. Це може зайняти до 1 хвилини", session_id)
                    print("Emitting the updated variables")
                    if user_id in user_first_messages_mapping:
                            user_first_messages = user_first_messages_mapping[user_id]
                            socket_io.emit('update_variables', {
                                'user_id': user_id,
                                'question_answered': question_answered,
                                'user_conversation_state': user_conversation_state,
                                'user_first_messages': user_first_messages,
                                'session_crisp': session_id,
                            }, room=user_id)

                            cached_response = await query_with_caching(user_first_messages)
                            print("User first message to retrieve in this phase: " + user_first_messages)
                            print(cached_response)
                            user_content_name = await check_conversation(session_id)
                            if cached_response:
                                await send_agent_message_crisp(cached_response, session_id)
                            else:
                                print('Going into the condition')
                                await send_agent_message_crisp("Ваш запит в обробці. Це може зайняти до 1 хвилини", session_id)
                                thread_openai_id = await start_thread_openai(user_id)
                                user_thread_mapping[user_id] = thread_openai_id
                                print(thread_openai_id)
                                question_name =  user_content_name + ". " + question
                                await send_message_user_async(thread_openai_id, question_name)
                                ai_response = await retrieve_ai_response_async(thread_openai_id)
                                if ai_response:
                                    await send_agent_message_crisp(ai_response, session_id)
                            user_conversation_state = 3
                            question_answered = 'True'
                            socket_io.emit('update_variables', {
                                'user_id': user_id,
                                'question_answered': question_answered,
                                'user_conversation_state': user_conversation_state,
                                'user_first_messages': user_first_messages,
                                'session_crisp': session_id,
                            }, room=user_id)

                            return 
        except Exception as e:
            print(f"Error: {str(e)}")
            socket_io.emit('start', {'user_id': user_id, 'message': 'Щось пішло не так, спробуйте пізніше...'}, room=user_id)


async def get_conversation_metas(session_id):
    basic_auth_credentials = aiohttp.BasicAuth(login=username, password=password)
    api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/meta"
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

                data_get = data.get("data", [0])
                user_nickname = data_get["nickname"]
                if user_nickname is not None:
                        print(user_nickname)
                        return user_nickname           
        
    except aiohttp.ClientError as err:
        print(f"HTTP Error: {err}")

async def handle_user_conversation_state_3(user_id, question_answered, user_conversation_state, question, session_id):
    print(user_id, session_id)
    print(question)
    print("Mapped session_id to user_id")
    if session_id in agent_flag_mapping and agent_flag_mapping[session_id] is True:
        print("Agent flag for the current user is: " + str(agent_flag_mapping[session_id]))
        await send_agent_message_crisp("Ваш чат передано менеджеру.", session_id)
        return 
    else: 
        print("The flag is not available to a current user")
        try:
            if question_answered == 'True' and user_conversation_state == '3':
                await send_agent_message_crisp("Ваш запит в обробці. Це може зайняти до 1 хвилини", session_id)
                cached_response = await query_with_caching(question)

                if cached_response:
                    await send_agent_message_crisp(cached_response, session_id)
                else:
                    user_content_name = await get_conversation_metas(session_id)
                    question_name = user_content_name + ". " + question
                    print(question_name)
                    thread_openai_id = user_thread_mapping.get(user_id)

                    if thread_openai_id is None:
                        # Thread ID not found in the mapping, start a new thread
                        thread_openai_id = await start_thread_openai(user_id)

                        # Update the user_thread_mapping with the new thread_openai_id
                        user_thread_mapping[user_id] = thread_openai_id

                    await send_message_user_async(thread_openai_id, question_name)
                    ai_response = await retrieve_ai_response_async(thread_openai_id)
                    if ai_response:
                        await send_agent_message_crisp(ai_response, session_id)

        except Exception as e:
            print(f"Error: {str(e)}")
            socket_io.emit('start', {'user_id': user_id, 'message': 'Щось пішло не так, спробуйте пізніше...'}, room=user_id)

async def handle_user_conversation_result(question, session_id):
    print(session_id)
    print(question)
    if session_id in agent_flag_mapping and agent_flag_mapping[session_id] is True:
        print("Agent flag for the current user is: " + str(agent_flag_mapping[session_id]))
        await send_agent_message_crisp("Ваш чат передано менеджеру.", session_id)
    else: 
        print("The flag is not available to a current user")
    try:
            await send_agent_message_crisp("Ваш запит в обробці. Це може зайняти до 1 хвилини", session_id)
            cached_response = await query_with_caching(question)

            if cached_response:
                await send_agent_message_crisp(cached_response, session_id)
            else:
                user_content_name = await get_conversation_metas(session_id)
                question_name = user_content_name + ". " + question
                print(question_name)
                thread_openai_id = user_thread_mapping_session_id.get(session_id)

                if thread_openai_id is None:
                    # Thread ID not found in the mapping, start a new thread
                    thread_openai_id = await start_thread_openai_session_id(session_id)

                    # Update the user_thread_mapping with the new thread_openai_id
                    user_thread_mapping_session_id[session_id] = thread_openai_id

                await send_message_user_async(thread_openai_id, question_name)
                ai_response = await retrieve_ai_response_async(thread_openai_id)
                if ai_response:
                    await send_agent_message_crisp(ai_response, session_id)

    except Exception as e:
        print(f"Error: {str(e)}")
        await send_agent_message_crisp("Щось пішло не так. Спробуйте пізніше.", session_id)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(socket_io.run(app, port=5000))

