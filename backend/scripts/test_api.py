import os
import json
import getpass
from typing import Optional

import httpx


class State:
	def __init__(self) -> None:
		self.base_url: str = os.getenv("BASE_URL", "http://localhost:8080")
		self.email: Optional[str] = os.getenv("TEST_EMAIL")
		self.password: Optional[str] = os.getenv("TEST_PASSWORD")
		self.full_name: Optional[str] = os.getenv("TEST_NAME")
		self.token: Optional[str] = None
		self.last_client_id: Optional[str] = None
		self.last_job_id: Optional[str] = None
		self.last_note_id: Optional[str] = None
		self.last_media_id: Optional[str] = None


def pp(title: str, data) -> None:
	print(f"\n=== {title} ===")
	print(json.dumps(data, indent=2))


def ih(prompt_text: str, default: Optional[str] = None, secret: bool = False) -> str:
	if secret:
		val = getpass.getpass(f"{prompt_text}{f' [{default}]' if default else ''}: ")
	else:
		val = input(f"{prompt_text}{f' [{default}]' if default else ''}: ")
	val = val.strip()
	return val if val else (default or "")


def headers(state: State) -> dict:
	return {"Authorization": f"Bearer {state.token}"} if state.token else {}


def do_signup(client: httpx.Client, state: State) -> None:
	email = ih("Email", state.email or "test@example.com")
	password = ih("Password", state.password or "pass123", secret=True)
	full_name = ih("Full name", state.full_name or "Tester")
	resp = client.post(f"{state.base_url}/auth/signup", json={"email": email, "password": password, "full_name": full_name})
	if resp.status_code == 200:
		pp("signup", resp.json())
		state.email, state.password, state.full_name = email, password, full_name
	elif resp.status_code == 400 and "already" in resp.text:
		print("Already registered")
		state.email, state.password, state.full_name = email, password, full_name
	else:
		print(f"Signup failed: {resp.status_code} {resp.text}")


def do_login(client: httpx.Client, state: State) -> None:
	email = ih("Email", state.email or "test@example.com")
	password = ih("Password", state.password or "pass123", secret=True)
	resp = client.post(f"{state.base_url}/auth/login", json={"email": email, "password": password})
	if resp.is_success:
		data = resp.json()
		state.token = data.get("access_token")
		pp("login", {"access_token": state.token[:8] + "..." if state.token else None})
		state.email, state.password = email, password
	else:
		print(f"Login failed: {resp.status_code} {resp.text}")


def do_me(client: httpx.Client, state: State) -> None:
	resp = client.get(f"{state.base_url}/auth/me", headers=headers(state))
	pp("me", resp.json() if resp.is_success else {"error": resp.text})


def create_client(client: httpx.Client, state: State) -> None:
	name = ih("Client name", "Wanjiru")
	phone = ih("Phone", "0700000000")
	location = ih("Location", "Nairobi")
	resp = client.post(f"{state.base_url}/clients", headers=headers(state), json={"name": name, "phone": phone, "location": location})
	if resp.is_success:
		data = resp.json()
		state.last_client_id = data["id"]
		pp("create_client", data)
	else:
		print(resp.text)


def list_clients(client: httpx.Client, state: State) -> None:
	resp = client.get(f"{state.base_url}/clients", headers=headers(state))
	pp("clients", resp.json() if resp.is_success else {"error": resp.text})


def create_job(client: httpx.Client, state: State) -> None:
	client_id = ih("Client ID", state.last_client_id or "")
	site = ih("Site", "Kasarani")
	resp = client.post(f"{state.base_url}/jobs", headers=headers(state), json={"client_id": client_id, "site": site, "status": "open"})
	if resp.is_success:
		data = resp.json()
		state.last_job_id = data["id"]
		pp("create_job", data)
	else:
		print(resp.text)


def list_jobs(client: httpx.Client, state: State) -> None:
	resp = client.get(f"{state.base_url}/jobs", headers=headers(state))
	pp("jobs", resp.json() if resp.is_success else {"error": resp.text})


def create_note(client: httpx.Client, state: State) -> None:
	job_id = ih("Job ID (optional)", state.last_job_id or "")
	text = ih("Text", "Test note")
	with_media = ih("Include audio media now? (y/n)", "y").lower().startswith("y")
	payload = {"text": text}
	if job_id:
		payload["job_id"] = job_id
	if with_media:
		payload.update({"media_type": "audio", "content_type": "audio/m4a"})
	resp = client.post(f"{state.base_url}/notes", headers=headers(state), json=payload)
	if resp.is_success:
		data = resp.json()
		state.last_note_id = data["id"]
		pp("create_note", data)
		media = (data.get("media") or [None])[0]
		if media:
			state.last_media_id = media["id"]
	else:
		print(resp.text)


def presign_media(client: httpx.Client, state: State) -> None:
	note_id = ih("Note ID", state.last_note_id or "")
	kind = ih("Kind (audio|photo)", "audio")
	content_type = ih("Content-Type", "audio/m4a" if kind == "audio" else "image/jpeg")
	resp = client.post(f"{state.base_url}/notes/{note_id}/presign", headers=headers(state), params={"kind": kind, "content_type": content_type})
	if resp.is_success:
		data = resp.json()
		state.last_media_id = data["media_id"]
		pp("presign", data)
		print("\nUpload hint (use another terminal):")
		print(f"curl -X PUT -H 'Content-Type: {content_type}' --upload-file YOUR_FILE '{data['upload_url']}'")
	else:
		print(resp.text)


def finalize_media(client: httpx.Client, state: State) -> None:
	note_id = ih("Note ID", state.last_note_id or "")
	media_id = ih("Media ID", state.last_media_id or "")
	resp = client.post(f"{state.base_url}/notes/{note_id}/finalize", headers=headers(state), params={"media_id": media_id})
	pp("finalize", resp.json() if resp.is_success else {"error": resp.text})


def list_notes(client: httpx.Client, state: State) -> None:
	resp = client.get(f"{state.base_url}/notes", headers=headers(state))
	pp("notes", resp.json() if resp.is_success else {"error": resp.text})


def main() -> None:
	state = State()
	print(f"API: {state.base_url}")
	with httpx.Client(timeout=30.0) as client:
		while True:
			print("\nChoose action:")
			print(" 1) Signup")
			print(" 2) Login")
			print(" 3) Me")
			print(" 4) Create client")
			print(" 5) List clients")
			print(" 6) Create job")
			print(" 7) List jobs")
			print(" 8) Create note")
			print(" 9) Presign media upload")
			print("10) Finalize media upload")
			print("11) List notes")
			print(" q) Quit")
			choice = input("> ").strip().lower()
			if choice in ("q", "quit", "exit"):
				break
			try:
				if choice == "1":
					do_signup(client, state)
				elif choice == "2":
					do_login(client, state)
				elif choice == "3":
					do_me(client, state)
				elif choice == "4":
					create_client(client, state)
				elif choice == "5":
					list_clients(client, state)
				elif choice == "6":
					create_job(client, state)
				elif choice == "7":
					list_jobs(client, state)
				elif choice == "8":
					create_note(client, state)
				elif choice == "9":
					presign_media(client, state)
				elif choice == "10":
					finalize_media(client, state)
				elif choice == "11":
					list_notes(client, state)
				else:
					print("Unknown option")
			except Exception as e:
				print(f"Error: {e}")


if __name__ == "__main__":
	main()
