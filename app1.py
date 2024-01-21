import asyncio
import os
import aiohttp

import requests
assistant_id = os.getenv('assistant_id')
token = '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'

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



if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    thread_id = 'thread_Pzo2paReYvrsAbklQmzCzeig'
    loop.run_until_complete(retrieve_ai_response_async(thread_id))
    loop.close()

# import asyncio