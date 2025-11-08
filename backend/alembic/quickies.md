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

 flutter run -d RZ8X3024XVD --dart-define=API_BASE_URL=http://192.168.0.105:8080

 running migrations inside docker:
 cd ..; cd infra; docker compose exec backend bash -c "cd /app/backend && python -m alembic upgrade head" 

 ```want to know the value of a certain variable in docker ```
 docker compose exec worker sh -c "printenv | grep API key"

 ```transcription voice note tests```
  Waiting for application startup.

```refreshing/clearing nlp cache```
# Option 1: By note ID (easiest)
DELETE /notes/964c65a7-ecbb-43cb-94ec-861dfd90e79d/nlp-cache

# Option 2: By text
DELETE /nlp/cache?text=Labor charges will be 20,000 Kenyan shillings

# Option 3: Force refresh on next extraction
POST /nlp/tag?force_refresh=true

Getting access token:
   # Get token first
TOKEN=$(curl -s -X POST "http://localhost:8080/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "wkellykitui@gmail.com", "password": "Password123"}' \
  | jq -r '.access_token')

# Delete all notes
curl -X DELETE "http://localhost:8080/notes/all" \
  -H "Authorization: Bearer $TOKEN"

# Delete all jobs
curl -X DELETE "http://localhost:8080/jobs/all" \
  -H "Authorization: Bearer $TOKEN"

curl -X DELETE "http://localhost:8080/jobs/all" \
  -H "Authorization: Bearer $TOKEN"

# Delete all reminders

# Delete all cache
curl -X DELETE "http://localhost:8080/nlp/cache?all=true" \
  -H "Authorization: Bearer $TOKEN"




curl -X DELETE \
  "http://localhost:8080/notes/964c65a7-ecbb-43cb-94ec-861dfd90e79d/nlp-cache" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ3a2VsbHlraXR1aUBnbWFpbC5jb20iLCJleHAiOjE3NjI1OTU4MzQsInR5cGUiOiJhY2Nlc3MifQ.STUX9ljinALZJ3AHuQLTVHMk6-AACudxn2rFIAA6KCQ"
curl -X DELETE \
  "http://localhost:8080/nlp/cache?all=true" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ3a2VsbHlraXR1aUBnbWFpbC5jb20iLCJleHAiOjE3NjI1OTU4MzQsInR5cGUiOiJhY2Nlc3MifQ.STUX9ljinALZJ3AHuQLTVHMk6-AACudxn2rFIAA6KCQ"