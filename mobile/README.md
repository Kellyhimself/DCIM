# mobile (Flutter)

## Setup
- Install Flutter (stable).
- Create app here or move an existing Flutter project into this folder.
- Recommended packages:
  - `sqflite` / `drift` for local DB
  - `dio` for HTTP
  - `flutter_secure_storage` for tokens
  - `workmanager` for background sync (Android)
  - `permission_handler` for mic/storage
  - `share_plus` for WhatsApp share

## Environments
- Point API base URL to `http://localhost:8000` (emulator) or machine IP for device.
- Store tokens in `flutter_secure_storage`.

## Next steps
- Add modules: auth, clients, jobs, notes (audio+photo), search, share, billing.
