import asyncio
import httpx
import time
import argparse
from uuid import uuid4

API_URL = "http://localhost:8000"

async def test_retrieval(client, exam_id, subject_id, query):
    start = time.time()
    try:
        response = await client.post(
            f"{API_URL}/api/v1/retrieval/search",
            json={
                "query": query,
                "exam_id": str(exam_id),
                "subject_id": str(subject_id),
                "top_k": 5
            }
        )
        elapsed = time.time() - start
        return response.status_code, elapsed
    except Exception as e:
        elapsed = time.time() - start
        return str(e), elapsed

async def main():
    parser = argparse.ArgumentParser(description="Learnova API Load Test")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent requests")
    parser.add_argument("--exam-id", type=str, required=True, help="Exam ID for testing")
    parser.add_argument("--subject-id", type=str, required=True, help="Subject ID for testing")
    args = parser.parse_args()

    exam_id = args.exam_id
    subject_id = args.subject_id
    concurrency = args.concurrency

    print(f"Starting load test with {concurrency} concurrent retrieval requests...")

    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(concurrency):
            tasks.append(test_retrieval(client, exam_id, subject_id, f"test query {i}"))
            
        results = await asyncio.gather(*tasks)
        
        successes = 0
        failures = 0
        total_time = 0
        
        for status, elapsed in results:
            total_time += elapsed
            if status == 200:
                successes += 1
            else:
                failures += 1
                
        print(f"\n--- Load Test Results ---")
        print(f"Total Requests: {concurrency}")
        print(f"Successes: {successes}")
        print(f"Failures: {failures}")
        print(f"Average Response Time: {total_time / concurrency:.3f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
