import sys
import threading
import time

# Shared resource
shared_resource = 0

# Lock for synchronization
# lock = threading.Lock()


# Define a function that will be executed by each thread
def worker():
    global shared_resource
    accum = 0
    for n in range(10000000):  # Perform some computation
        # with lock:
        accum += n
    shared_resource += accum


def run_threads(num_threads):
    start_time = time.time()

    # Create a list to store references to the threads
    threads = []

    # Create and start the specified number of threads
    for _ in range(num_threads):
        thread = threading.Thread(target=worker)
        thread.start()
        threads.append(thread)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Ran {num_threads} threads cooperatively in {elapsed_time:.2f} seconds")


if __name__ == '__main__':
    print(f"gil_enabled={sys._is_gil_enabled()}")
    # Run the benchmark with different numbers of threads
    for num_threads in [1, 2, 4, 8, 20]:
        run_threads(num_threads)
