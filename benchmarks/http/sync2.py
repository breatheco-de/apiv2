from timeit import default_timer as timer

import httpx
import requests

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


def main():
    global url, timeout

    father_time = []
    with httpx.Client() as client:
        for url in url_list:
            t1 = timer()
            client.get(url, timeout=timeout)
            t2 = timer()
            secs = t2 - t1
            father_time.append(secs)

    print("HTTPX: ", sum(father_time))

    father_time = []
    for url in url_list:
        t1 = timer()
        requests.get(url, timeout=timeout)
        t2 = timer()
        secs = t2 - t1
        father_time.append(secs)

    print("REQUESTS: ", sum(father_time))


if __name__ == "__main__":
    main()
