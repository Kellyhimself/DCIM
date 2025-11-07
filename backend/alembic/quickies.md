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
 Example 1, Voice Note (Say this when recording):

 Test Note 1: Electrical Work (Different Trade)
"Hello, this is regarding the electrical installation at John Kamau's office in Westlands. His contact is 0721122334. We need to install new circuit breakers, electrical outlets, and wiring. The quote is KES 25,000 for materials and KES 15,000 for labor, so total KES 40,000. We should start next week Tuesday, that's the 21st of January. The client wants this completed by the end of the month. I'll need to order the MCB panel and some conduit pipes."

Test Note 2: Multiple Jobs & Clients
"Quick update: Sarah Muthoni called from Karen area, phone 0733445566. She needs carpentry work done - fixing kitchen cabinets and installing new shelves. That's about KES 8,000 for materials. Also, remember the plumbing job at David Ochieng's place in Parklands, his number is 0744556677. We still need to replace the ball valve and check the water pressure. That job is scheduled for Friday the 17th. Total for both jobs is around KES 12,000."

Test Note 3: Mixed Trade with Urgent Timeline
"Emergency call from Mary Wanjala in Kilimani, contact 0755667788. Her house has a blocked drain and leaking tap. Need to bring a plunger, drain snake, and new tap washers. This is urgent - she wants it done today if possible, or tomorrow morning at the latest. The cost will be KES 5,500 including labor. She mentioned her neighbor Peter also needs similar work done."

Test Note 4: Complex Job with Multiple Parts
"Site visit at James Otieno's construction site in Lavington. Phone 0766778899. This is a major plumbing installation - we need to install a complete bathroom suite including toilet, sink, bathtub, shower head, and all the connecting pipes. Also need to install a water heater. Materials will cost approximately KES 45,000 and installation labor is KES 20,000. Start date is next Monday, January 20th, and should be finished by Wednesday the 22nd."

Test Note 5: Follow-up Note (No New Client)
"Follow-up on the Westlands job. The client confirmed they want the premium switches instead of standard ones. That adds KES 3,000 to the materials cost. Also, they want to schedule the work for the 25th of January instead. I've updated the quote to KES 43,000 total. Call them at 0721122334 to confirm."

Test Note 6: Simple Service Call
"Service call at Grace Njeri's house in Runda. Her number is 0777889900. Just need to fix a leaking faucet and replace the washer. Quick job, should take about an hour. Charge is KES 2,000 for the service call and parts. She's available tomorrow afternoon."


"Hi, this is a note for the plumbing job at Wanjiru's house. Her phone number is 0712345678. We need to replace the P-trap and install a new U-bend. The total cost will be KES 3,500. I'll come back on Monday, that's the 15th of January 2025. The client also mentioned they need this done by next Friday. I should call them at 0723456789 to confirm the time. The materials cost about KES 2,000 and labor is KES 1,500."

What Should Be Extracted:
Phone Numbers:
+254712345678 (0712345678)
+254723456789 (0723456789)
Amounts:
KES 3,500
KES 2,000
KES 1,500
Dates:
Monday
15th of January 2025 (might extract as "15" or "January")
next Friday

Additional Entities (Future Enhancement):
Client name: "Wanjiru"
Parts: "P-trap", "U-bend"
Job type: "plumbing"

Example 2, Shorter Test Note:
"Call John at 0712345678 about the electrical work. The quote is KES 5,000. Meeting on Wednesday the 20th."
This should extract:
Phone: +254712345678
Amount: KES 5,000
Date: Wednesday and 20th

Tips for Testing:
Speak clearly and at a normal pace
Pause briefly between sentences
Pronounce numbers clearly
After recording, wait for transcription to complete
Check that the entity chips appear below the transcribed text
The NLP endpoint will extract phones, amounts, and dates. Future enhancements can add parts, client names, and job types using trade dictionaries as mentioned in your MVP spec.