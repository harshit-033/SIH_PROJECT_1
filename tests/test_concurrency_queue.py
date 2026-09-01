import asyncio
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.request_queue import RequestQueue, RequestStatus


async def run_simulated_inference(queue: RequestQueue, task_id: int, sleep_time: float, results: list):
    task = queue.create_task(f"sess_{task_id}", "simulated_chat")
    await queue.acquire_slot(task)
    try:
        assert task.status == RequestStatus.PROCESSING
        results.append(f"task_{task_id}_start")
        await asyncio.sleep(sleep_time)
        results.append(f"task_{task_id}_end")
        await queue.release_slot(task, success=True)
        assert task.status == RequestStatus.COMPLETED
    except Exception as exc:
        await queue.release_slot(task, success=False, error=str(exc))


async def test_queue():
    # Queue with concurrency 1 (serialized inference)
    queue = RequestQueue(max_concurrent_inference=1)
    results = []

    # Run 3 simulated requests concurrently
    tasks = [
        run_simulated_inference(queue, 1, 0.05, results),
        run_simulated_inference(queue, 2, 0.05, results),
        run_simulated_inference(queue, 3, 0.05, results),
    ]

    await asyncio.gather(*tasks)

    # Verify requests executed serially: start_1 -> end_1 -> start_2 -> end_2 -> start_3 -> end_3
    assert results == [
        "task_1_start", "task_1_end",
        "task_2_start", "task_2_end",
        "task_3_start", "task_3_end",
    ]
    assert queue.active_count == 0
    assert queue.queued_count == 0
    print("Concurrency request queue checks PASSED!")


if __name__ == "__main__":
    asyncio.run(test_queue())
