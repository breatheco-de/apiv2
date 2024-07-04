from timeit import default_timer as timer

import httpx
import requests

times = 100
url = "https://www.google.com"
timeout = 100000


def main():
    global times, url, timeout

    url_list = [url] * times
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
