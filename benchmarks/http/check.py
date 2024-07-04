import requests

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

for url in url_list:
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        print(f"Success: {url} - Status Code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error: {url} - {e}")
