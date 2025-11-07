import os
import json
import time
import tempfile
from typing import Optional
import httpx
import boto3
from botocore.client import Config
from openai import OpenAI

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_KEY = os.getenv("QUEUE_KEY", "stt_jobs")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9000")
S3_BUCKET = os.getenv("S3_BUCKET", "app")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def get_redis() -> redis.Redis:
	return redis.from_url(REDIS_URL)


def get_s3_client():
	return boto3.client(
		"s3",
		endpoint_url=S3_ENDPOINT,
		aws_access_key_id=S3_ACCESS_KEY,
		aws_secret_access_key=S3_SECRET_KEY,
		config=Config(signature_version="s3v4"),
	)


def transcribe_audio(audio_path: str) -> tuple[str, bool]:
	"""
	Transcribe audio file using OpenAI Whisper API.
	Returns (transcription_text, success).
	Falls back to placeholder if API key not configured.
	"""
	if not OPENAI_API_KEY:
		print("[worker] WARNING: OPENAI_API_KEY not set, using placeholder transcription")
		return ("[Transcription placeholder - set OPENAI_API_KEY to enable real transcription]", False)
	
	try:
		client = OpenAI(api_key=OPENAI_API_KEY)
		with open(audio_path, "rb") as audio_file:
			transcript = client.audio.transcriptions.create(
				model="whisper-1",
				file=audio_file,
				language="en",  # Optional: specify language for better accuracy
			)
		return (transcript.text, True)
	except Exception as e:
		print(f"[worker] Error transcribing with OpenAI: {e}")
		# Return error message and indicate failure
		return (f"[Transcription failed: {str(e)}]", False)


def handle_job(job: dict) -> None:
	"""Process STT job: download audio, transcribe, update note."""
	note_id = job.get("note_id")
	media_id = job.get("media_id")
	key = job.get("key")
	
	if not all([note_id, key]):
		print(f"[worker] invalid job: missing required fields")
		return
	
	print(f"[worker] processing job: note_id={note_id}, key={key}")
	
	try:
		# Update status to transcribing
		with httpx.Client() as client:
			client.post(
				f"{API_BASE_URL}/notes/{note_id}/transcription",
				json={"status": "transcribing"}
			)
		
		# Download audio from S3
		s3 = get_s3_client()
		with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp_file:
			tmp_path = tmp_file.name
			s3.download_fileobj(S3_BUCKET, key, tmp_file)
		
		# Transcribe
		transcription, success = transcribe_audio(tmp_path)
		
		# Log transcribed text
		print(f"[worker] Transcribed text for note {note_id} (length: {len(transcription)}):")
		print(f"[worker] Transcription: {transcription}")
		
		# Clean up temp file
		os.unlink(tmp_path)
		
		# Update note with transcription
		with httpx.Client() as client:
			if success:
				client.post(
					f"{API_BASE_URL}/notes/{note_id}/transcription",
					json={"text": transcription, "status": "completed"}
				)
				print(f"[worker] completed transcription for note {note_id}")
			else:
				# Transcription failed - set status to failed
				client.post(
					f"{API_BASE_URL}/notes/{note_id}/transcription",
					json={"text": transcription, "status": "failed"}
				)
				print(f"[worker] transcription failed for note {note_id}: {transcription}")
	except Exception as e:
		print(f"[worker] error processing job: {e}")
		# Update status to failed
		try:
			with httpx.Client() as client:
				client.post(
					f"{API_BASE_URL}/notes/{note_id}/transcription",
					json={"status": "failed"}
				)
		except:
			pass


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
