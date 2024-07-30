import asyncio
import logging
import os
import requests
import httpx
from drive import get_active_account, set_active_account, write_uuid_file
import time


logger = logging.getLogger(__name__)

async def get_llm_response(prompt: str) -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3", "prompt": prompt, "stream": False}
    )
    response_data = response.json()
    return response_data.get("response", "")

async def get_llm_response_stream(prompt: str):
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", "http://localhost:11434/api/generate", json={"model": "llama3", "prompt": prompt, "stream": True}) as response:
            async for chunk in response.aiter_text():
                yield chunk

async def write_to_file(responses):
    # Convert the list of tuples 'responses' to a single bytes array
    combined_responses = "".join([f"{user_input}: {response}\n" for user_input, response in responses])
    responses_bytes = combined_responses.encode('utf-8')

    # Write the bytes array to a file using the write_uuid_file function
    url = await write_uuid_file(responses_bytes)
    logger.info(f"Responses written to file with URL: {url}")

async def interactive_shell():
    responses = []
    lastTime = time.time()
    while True:
        try:
            # Take user input
            user_input = input(">>> ")
            if user_input.lower() in ['exit', 'quit']:
                print("Exiting interactive shell.")
                break
            # Process the input and get a streamed response
            response = await get_llm_response(user_input)
            responses.append([user_input, response])
         
        except (EOFError, KeyboardInterrupt):
            print("\nExiting interactive shell.")
            break

        if len(responses) > 10:
            await write_to_file(responses) 
            responses = []

def start_mining():
    if get_active_account() is None:
        print("No active drive account found. Requesting credentials...")
        set_active_account()
    asyncio.run(interactive_shell())

if __name__ == "__main__":
    start_mining()

