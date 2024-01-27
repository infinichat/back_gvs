from flask import Flask, render_template
from flask_socketio import SocketIO
import asyncio

app = Flask(__name__)
socketio = SocketIO(app, async_mode='asyncio')

async def connect_to_socket():
    endpoint_url = "wss://app.relay.crisp.chat/p/68/"

    sio = socketio.AsyncClient()

    @sio.on('connect')
    async def on_connect():
        await sio.emit("authentication", {
            "tier": "plugin",
            "username": "5609c6ae-2281-45fe-b66f-01f3976a8fec",
            "password": "3da36469d1da798b3b4ce23eae580637b0a308ea654c71d78cff08937604f191",
            "events": [
                "message:received",
                "message:updated",
                "message:removed"
            ],
            "rooms": [
                "84ca425b-3cf3-4a00-836c-1212d36eba0c"
            ]
        })
        print("RTM API connected")

    @sio.on('authenticated')
    async def authenticated(data):
        print(data)

    @sio.on('unauthorized')
    async def unauthorized(data):
        print(data)

    @sio.on('message:received')
    async def message_received_event(message):
        print('Got a message from agent: ' + message['content'], message['session_id'], message['fingerprint'])

    @sio.on('message:updated')
    async def message_updated_event(message):
        print('Got an updated message: ' + message['content'], message['fingerprint'])

    @sio.on('message:removed')
    async def message_removed_event(message):
        print('Got a removed message: ' + message['fingerprint'], message['session_id'])

    @sio.on('disconnect')
    async def on_disconnect():
        print("RTM API disconnected")

    @sio.on('connect_error')
    async def on_connect_error(error):
        print("RTM API connection error", error)

    @sio.on('reconnect')
    async def on_reconnect():
        print("RTM API reconnecting...")

    @sio.on('error')
    async def on_error(error):
        print("RTM API error", error)

    print(endpoint_url)

    await sio.connect(endpoint_url, transports='websocket')
    
    return sio

@app.route('/')
def index():
    return render_template('index.html')

@socketio.event
async def connect():
    global global_client
    global_client = await connect_to_socket()
    print("Connected. Performing actions...")

@socketio.event
def disconnect():
    global global_client
    print("Client disconnected")
    asyncio.create_task(global_client.disconnect())

if __name__ == '__main__':
    socketio.run(app, debug=True)

# import socketio
# import asyncio

# sio = socketio.AsyncClient()

# async def on_connect():
#     #   // Authenticate to the RTM API
#     await sio.emit("authentication", {
#         "tier": "plugin",
#         # // Configure your Crisp authentication tokens
#         "username" : "5609c6ae-2281-45fe-b66f-01f3976a8fec",
#         "password" : "3da36469d1da798b3b4ce23eae580637b0a308ea654c71d78cff08937604f191",

#         # // Subscribe to target event namespaces
#         "events" : [
#         "message:received",
#         "message:updated",
#         "message:removed"
#         ],
#         "rooms": [
#             "84ca425b-3cf3-4a00-836c-1212d36eba0c"
#         ]
#     });
#     print("RTM API connected")

# async def authenticated(data):
#     print(data)

# async def unauthorized(data):
#     print(data)

# async def message_received_event(message):
#     #   message.content, message.session_id, message.fingerprint
#     print('Got a message from agent: ' + message['content'], message['session_id'], message['fingerprint']);

# async def message_updated_event(message):
#     print('Got a updated message: ' + message['content'], message['fingerprint']);

# async def message_removed_event(message):
#     print('Got a removed message: ' + message['fingerprint'], message['session_id']);

   
# async def on_disconnect():
#     print("RTM API disconnected")

# async def on_connect_error(error):
#     print("RTM API connection error", error)

# async def on_reconnect():
#     print("RTM API reconnecting...")

# async def on_error(error):
#     print("RTM API error", error)

# async def connect_to_socket():
#     endpoint_url = "wss://app.relay.crisp.chat/p/68/"

#     sio.on('connect', on_connect)
#     sio.on('authenticated', authenticated)
#     sio.on('unauthorized', unauthorized)
#     sio.on('message:received', message_received_event)
#     sio.on('message:updated', message_updated_event)
#     sio.on('message:removed', message_removed_event)
#     sio.on('disconnect', on_disconnect)
#     sio.on('connect_error', on_connect_error)

#     # Handle IO events
#     sio.on('reconnect', on_reconnect)
#     sio.on('error', on_error)

#     print(endpoint_url)
    
#     await sio.connect(endpoint_url, transports='websocket')
    
#     return sio

# async def main():
#      while True:
#         try:
#             client = await connect_to_socket()
#             print("Connected. Performing actions...")

#             # Simulate some activity
#             await asyncio.sleep(10)

#         except Exception as e:
#             print(f"An error occurred: {e}")
#             # Handle the error (e.g., log it, sleep before retrying, etc.)
#             await asyncio.sleep(5)

#         finally:
#             await client.disconnect()

# # Run the event loop
# asyncio.get_event_loop().run_until_complete(main())






# import socketio

# sio = socketio.AsyncClient()

# async def on_connect():
#     #   // Authenticate to the RTM API
#     await sio.emit("authentication", {
#         "tier": "plugin",
#         # // Configure your Crisp authentication tokens
#         "username" : "5609c6ae-2281-45fe-b66f-01f3976a8fec",
#         "password" : "3da36469d1da798b3b4ce23eae580637b0a308ea654c71d78cff08937604f191",

#         # // Subscribe to target event namespaces
#         "events" : [
#         "message:received",
#         "message:updated",
#         "message:removed"
#         ],
#         "rooms": [
#             "84ca425b-3cf3-4a00-836c-1212d36eba0c"
#         ]
#     });
#     print("RTM API connected")

# async def authenticated(data):
#     print(data)

# async def unauthorized(data):
#     print(data)
  
# async def on_disconnect():
#     print("RTM API disconnected")

# async def on_connect_error(error):
#     print("RTM API connection error", error)

# async def on_reconnect():
#     print("RTM API reconnecting...")

# async def on_error(error):
#     print("RTM API error", error)

# # async def connect_to_socket():
# endpoint_url = "wss://app.relay.crisp.chat/p/68/"

# sio.on('connect', on_connect)
# sio.on('authenticated', authenticated)
# sio.on('unauthorized', unauthorized)


# async def parse_user_id(user_id, retrieved_session_ids):
#     @sio.event 
#     async def message_received_event(message):
#             #   message.content, message.session_id, message.fingerprint
#             print('Got a message from agent: ' + message['content'], message['session_id'], message['fingerprint']);
#             session_id = message['session_id']
#             fingerprint = message['fingerprint']
#             if session_id in retrieved_session_ids:
#                     user_id_for_session = next((uid for uid, sid in user_session_mapping.items() if sid == session_id), None)

#                     if user_id_for_session:
#                         print(f"Message received for user {user_id_for_session}: {message['content']}")
#                         message_data[fingerprint] = message['content']
#                         socket_io.emit('start', {'user_id': user_id_for_session, 'message': message['content']}, room=user_id_for_session)
#                     else:
#                         print(f"Session ID {session_id} not mapped to any user.")
#             else:
#                 print(f"Invalid session ID: {session_id}")
#             pass
#     # sio.on('message:updated')
#     @sio.event 
#     async def edit_message(message):
#             fingerprint = message['fingerprint']
#             new_message = message['content']
#             if fingerprint in message_data:
#                 old_message = message_data[fingerprint]
#                 message_data[fingerprint] = new_message
#                 socket_io.emit('delete_message', {'user_id': user_id, 'message': old_message}, room=user_id)
#                 print(f"Message edited. Old message: {old_message}, New message: {new_message}")
#                 socket_io.emit('start', {'user_id': user_id, 'message': new_message}, room=user_id)
#             else:
#                 print(f"No message found for fingerprint: {fingerprint}")
#             pass
#     # sio.on('message:removed')
#     async def delete_message(message):
#             session_id = message['session_id']
#             fingerprint = message['fingerprint']
#             if session_id in retrieved_session_ids:
#                 user_id_for_session = next((uid for uid, sid in user_session_mapping.items() if sid == session_id), None)

#                 if user_id_for_session:
#                     if fingerprint in message_data:
#                         del_message = message_data[fingerprint]

#                         print("User id to submit delete message: " + user_id_for_session)
#                         socket_io.emit('user_id', {'response': user_id_for_session})
#                         socket_io.emit('delete_message', {'user_id': user_id_for_session, 'message': del_message}, room=user_id)

#                         del message_data[fingerprint]
#                         print(f"Message to delete: {del_message}")
#                     else:
#                         print(f"No message found for fingerprint: {fingerprint}")
#                     pass 

#     sio.on('message:received', message_received_event)
#     sio.on('message:updated', edit_message)
#     sio.on('message:removed', delete_message)
#     sio.on('disconnect', on_disconnect)
#     sio.on('message:received')

#     # sio.on('message:received', message_received_event)
#     # sio.on('message:updated', message_updated_event)
#     # sio.on('message:removed', message_removed_event)
#     sio.on('disconnect', on_disconnect)
#     sio.on('connect_error', on_connect_error)

#     # Handle IO events
#     sio.on('reconnect', on_reconnect)
#     sio.on('error', on_error)

#     print(endpoint_url)
    
#     if not sio.connected:
#         await sio.connect(endpoint_url, transports='websocket')

    
#     return sio

# async def main(user_id, session_id):
#      while True:
#         try:
#             client = await parse_user_id(user_id, session_id)
#             print("Connected. Performing actions...")

#             # Simulate some activity
#             await asyncio.sleep(40)

#         except Exception as e:
#             print(f"An error occurred: {e}")
#             # Handle the error (e.g., log it, sleep before retrying, etc.)
#             await asyncio.sleep(5)

#         finally:
#             await client.disconnect()

# @socket_io.on('disconnect')
# def handle_disconnect():
#     print('Client disconnected')  

