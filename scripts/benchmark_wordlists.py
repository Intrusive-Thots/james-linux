import asyncio
import time
import httpx
import multiprocessing
import uvicorn
from james.api.server import app


def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")


async def fetch_wordlists(client):
    start = time.time()
    response = await client.get(
        "http://127.0.0.1:8000/api/wordlists", timeout=10.0
    )
    return time.time() - start


async def fetch_health(client):
    start = time.time()
    response = await client.get(
        "http://127.0.0.1:8000/api/status", timeout=10.0
    )
    return time.time() - start


async def main():
    p = multiprocessing.Process(target=run_server)
    p.start()

    await asyncio.sleep(2)

    try:
        async with httpx.AsyncClient() as client:
            # Warmup
            await client.get(
                "http://127.0.0.1:8000/api/wordlists", timeout=10.0
            )

            start_time = time.time()

            # Mix slow wordlist requests with fast status requests
            tasks = [fetch_wordlists(client) for _ in range(5)]
            health_tasks = [fetch_health(client) for _ in range(20)]

            times = await asyncio.gather(*(tasks + health_tasks))
            total_time = time.time() - start_time

            wordlist_times = times[:5]
            health_times = times[5:]

            print(f"Total time for 25 concurrent requests: {total_time:.4f}s")
            print(
                f"Average time per wordlist request: {sum(wordlist_times)/len(wordlist_times):.4f}s"
            )
            print(
                f"Max time for a wordlist request: {max(wordlist_times):.4f}s"
            )
            print(
                f"Average time per health request: {sum(health_times)/len(health_times):.4f}s"
            )
            print(f"Max time for a health request: {max(health_times):.4f}s")
            print(f"Min time for a health request: {min(health_times):.4f}s")
    finally:
        p.terminate()
        p.join()


if __name__ == "__main__":
    asyncio.run(main())
