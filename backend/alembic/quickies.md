Do this in WSL, inside the repo:
Create and activate a virtualenv
python3 -m venv .venv
source .venv/bin/activate
Install backend deps
cd backend
pip install --upgrade pip
pip install -r requirements.txt
Ensure env exists
cp env.sample .env

if a migration exists:

docker compose exec backend sh -lc "cd /app/backend && alembic -c alembic.ini upgrade head"

 flutter run -d RZ8X3024XVD --dart-define=API_BASE_URL=http://192.168.0.103:8080