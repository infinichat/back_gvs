import socketio
import asyncio

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
    #   message.content, message.session_id, message.fingerprint
    print('Got a message from agent: ' + message['content'], message['session_id'], message['fingerprint']);

async def message_updated_event(message):
    print('Got a updated message: ' + message['content'], message['fingerprint']);

async def message_removed_event(message):
    print('Got a removed message: ' + message['fingerprint'], message['session_id']);

   
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

async def main():
     while True:
        try:
            client = await connect_to_socket()
            print("Connected. Performing actions...")

            # Simulate some activity
            await asyncio.sleep(10)

        except Exception as e:
            print(f"An error occurred: {e}")
            # Handle the error (e.g., log it, sleep before retrying, etc.)
            await asyncio.sleep(5)

        finally:
            await client.disconnect()

# Run the event loop
asyncio.get_event_loop().run_until_complete(main())