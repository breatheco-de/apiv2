import asyncio
import time

import aiohttp
import httpx

timeout = 100000

url_list = [
    "https://jsonplaceholder.typicode.com/posts",
    "https://api.thedogapi.com/v1/breeds",
    "https://pokeapi.co/api/v2/pokemon/1/",
    "https://jsonplaceholder.typicode.com/comments",
    "https://jsonplaceholder.typicode.com/users",
    "https://dog.ceo/api/breeds/image/random",
    "https://pokeapi.co/api/v2/pokemon/25/",
    "https://api.adviceslip.com/advice",
    "https://catfact.ninja/fact",
    "https://api.thecatapi.com/v1/breeds",
    "https://api.chucknorris.io/jokes/random",
    "https://official-joke-api.appspot.com/jokes/random",
    "https://jsonplaceholder.typicode.com/photos",
    "https://jsonplaceholder.typicode.com/todos",
    "https://jsonplaceholder.typicode.com/albums",
    "https://api.thecatapi.com/v1/images/search?limit=5",
    "https://api.adviceslip.com/advice/search/cats",
    "https://api.thedogapi.com/v1/breeds?limit=5",
    "https://pokeapi.co/api/v2/ability/1/",
    "https://api.chucknorris.io/jokes/categories",
]


async def main():
    # Create clients for both the library
    httpx_client = httpx.AsyncClient()
    aiohttp_client = aiohttp.ClientSession()

    try:
        # Send 100 asynchronous GET requests using HTTPX
        start_time = time.perf_counter()
        tasks = [httpx_client.get(url, timeout=timeout) for url in url_list]
        await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        print(f"HTTPX: {end_time - start_time:.2f} seconds")

        # Send 100 asynchronous GET requests using AIOHTTP
        start_time = time.perf_counter()
        tasks = [aiohttp_client.get(url, timeout=timeout) for url in url_list]
        await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        print(f"AIOHTTP: {end_time - start_time:.2f} seconds")
    finally:
        # Close client sessions
        await aiohttp_client.close()
        await httpx_client.aclose()


asyncio.run(main())
