import os
import json
import time
from typing import Optional

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_KEY = os.getenv("QUEUE_KEY", "stt_jobs")


def get_redis() -> redis.Redis:
	return redis.from_url(REDIS_URL)


def handle_job(job: dict) -> None:
	# Stub: in future, download audio from S3, call STT, update backend
	print(f"[worker] received job: {job}")
	# Simulate work
	time.sleep(1)
	print("[worker] done")


def pop_job(r: redis.Redis) -> Optional[dict]:
	item = r.blpop(QUEUE_KEY, timeout=5)
	if not item:
		return None
	_, raw = item
	try:
		return json.loads(raw.decode("utf-8"))
	except Exception:
		print("[worker] invalid job payload, skipping")
		return None


def main() -> None:
	r = get_redis()
	print(f"[worker] connected to {REDIS_URL}, watching {QUEUE_KEY}")
	while True:
		job = pop_job(r)
		if not job:
			continue
		try:
			handle_job(job)
		except Exception as e:
			print(f"[worker] error: {e}")


if __name__ == "__main__":
	main()
