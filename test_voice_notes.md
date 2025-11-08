# Test Voice Notes for Reminders and Financial Tracking

## Voice Note 1: Tailoring Job with Reminders and Actual Expenses
```
Urgent tailoring work for Beatrice Nyambura in Runda. Her phone number is 0798123456. 
She needs her wedding dress altered before the ceremony next week. 
I spent 1,800 shillings on premium thread and zippers. 
Also paid 300 shillings for a matatu ride to her house. 
The client gave me 5,000 shillings as deposit. 
I need to return on Tuesday for the final fitting. 
Also, call her on Sunday to confirm the appointment time. 
The total alteration cost will be around 4,500 shillings including materials.
```

**Expected Reminders:**
- "return on Tuesday for the final fitting" (type: return, due_date: next Tuesday)
- "call her on Sunday to confirm the appointment time" (type: call, due_date: next Sunday)

**Expected Financials:**
- Actual expenses: ["spent 1,800 shillings on premium thread and zippers", "paid 300 shillings for a matatu ride"]
- Actual earnings: ["client gave me 5,000 shillings as deposit"]
- Projected expenses: ["total alteration cost will be around 4,500 shillings"]

---

## Voice Note 2: Masonry Work with Projected Costs
```
Masonry job at Collins Otieno's compound in Ngong. 
Contact is 0789234567. 
Building a perimeter wall around his property. 
The bricks and cement will cost roughly 45,000 Kenyan shillings. 
Labour charges will be 20,000 shillings. 
So my total quote is 65,000 Kenyan shillings. 
We plan to start on the 15th of February. 
The client wants the wall completed within two weeks. 
I'll need to source quality sand and ballast. 
Follow up with Collins on Thursday to finalize the contract.
```

**Expected Reminders:**
- "Follow up with Collins on Thursday to finalize the contract" (type: follow_up, due_date: next Thursday)

**Expected Financials:**
- Projected expenses: ["bricks and cement will cost roughly 45,000 Kenyan shillings"]
- Projected earnings: ["total quote is 65,000 Kenyan shillings", "Labour charges will be 20,000 shillings"]

---

## Voice Note 3: Mixed Actual and Projected with Multiple Reminders
```
Update on the Ngong masonry project. The client wants decorative stones 
instead of plain bricks. That increases the material cost by KES 8,000. 
They also moved the start date to the 20th of February. 
I've revised the quote to KES 73,000 total. 
Call Collins at 0789234567 to confirm. 
I already purchased some foundation materials for 12,000 shillings last week, 
but I'll need to exchange them for the decorative stones. 
Check back next week to see if they've signed the contract.
```

**Expected Reminders:**
- "Call Collins at 0789234567 to confirm" (type: call, due_date: soon)
- "Check back next week to see if they've signed the contract" (type: check, due_date: next week)

**Expected Financials:**
- Actual expenses: ["purchased some foundation materials for 12,000 shillings last week"]
- Projected expenses: ["increases the material cost by KES 8,000"]
- Projected earnings: ["revised the quote to KES 73,000 total"]

---

## Voice Note 4: Completed Welding Job with Actual Earnings
```
Finished the welding work at Grace Wambui's workshop in Thika. 
Contact is 0770345678. 
Fabricated metal gates and window grills. 
The client paid me 35,000 shillings for the completed work. 
I spent 12,000 shillings on metal sheets and welding rods. 
Also paid 1,500 shillings for transport to deliver the gates. 
Made a profit of about 21,500 shillings after expenses. 
Need to return in two weeks to check on the gate hinges and apply rust protection.
```

**Expected Reminders:**
- "return in two weeks to check on the gate hinges" (type: return, due_date: two weeks from now)

**Expected Financials:**
- Actual expenses: ["spent 12,000 shillings on metal sheets and welding rods", "paid 1,500 shillings for transport"]
- Actual earnings: ["client paid me 35,000 shillings for the completed work"]

---

## Voice Note 5: Tiling Job with Shopping Items and Reminders
```
Quick update on the tiling job in Ruaka. 
The client's name is Francis Kariuki, phone 0741456789. 
I need to buy ceramic tiles, grout, and tile adhesive. 
The materials will cost approximately 18,000 shillings. 
I've already spent 2,000 shillings on transport today. 
The client said they'll pay 45,000 shillings once the tiling is complete. 
I should call them tomorrow to schedule when to start. 
Also need to bring a tile cutter and leveling tools when I go back.
```

**Expected Reminders:**
- "call them tomorrow to schedule when to start" (type: call, due_date: tomorrow)

**Expected Shopping Items:**
- ["ceramic tiles", "grout", "tile adhesive", "tile cutter", "leveling tools"]

**Expected Financials:**
- Actual expenses: ["spent 2,000 shillings on transport today"]
- Projected expenses: ["materials will cost approximately 18,000 shillings"]
- Projected earnings: ["they'll pay 45,000 shillings once the tiling is complete"]

---

## Voice Note 6: Multiple Reminders and Financial Updates
```
Update on the painting job at Lucy's place in Kasarani. 
I received 15,000 shillings from the client today as advance payment. 
Still need to paint the remaining rooms. 
The additional paint and brushes will cost about 7,500 shillings. 
I paid 800 shillings for parking today. 
Total project value is 55,000 shillings. 
I need to return on Wednesday to continue painting. 
Also, follow up with the client on Monday to confirm the color choices. 
Check the first coat on Friday to see if it needs a second layer.
```

**Expected Reminders:**
- "return on Wednesday to continue painting" (type: return, due_date: next Wednesday)
- "follow up with the client on Monday to confirm the color choices" (type: follow_up, due_date: next Monday)
- "Check the first coat on Friday" (type: check, due_date: next Friday)

**Expected Financials:**
- Actual earnings: ["received 15,000 shillings from the client today as advance payment"]
- Actual expenses: ["paid 800 shillings for parking today"]
- Projected expenses: ["additional paint and brushes will cost about 7,500 shillings"]
- Projected earnings: ["Total project value is 55,000 shillings"]

---

## Voice Note 7: Roofing Job with Parts and Reminders
```
Roofing work on a house in Kiambu. 
Client is Joseph Mutua, contact 0752567890. 
Replaced damaged iron sheets and fixed the gutters. 
I bought iron sheets for 22,000 shillings and gutters for 5,500 shillings. 
The client paid me 40,000 shillings for the roofing service. 
I need to call them next week to check if there are any leaks. 
Also, remind them to come back in 6 months for roof maintenance inspection.
```

**Expected Reminders:**
- "call them next week to check if there are any leaks" (type: call, due_date: next week)
- "remind them to come back in 6 months for roof maintenance" (type: follow_up, due_date: 6 months from now)

**Expected Financials:**
- Actual expenses: ["bought iron sheets for 22,000 shillings", "gutters for 5,500 shillings"]
- Actual earnings: ["client paid me 40,000 shillings for the roofing service"]

---

## Voice Note 8: Complex Landscaping Project with Multiple Financial Transactions
```
Large landscaping project update. 
Client is Agnes Njeri in Limuru, phone 0763678901. 
This is a major garden renovation job. 
I've already received 80,000 shillings as the first payment. 
Spent 35,000 shillings on plants and soil. 
Paid 4,500 shillings for delivery of landscaping materials. 
The total project quote is 280,000 shillings. 
We'll need additional plants and irrigation pipes worth about 45,000 shillings for the next phase. 
I need to meet with the client on Thursday to discuss the garden design. 
Also, call the nursery tomorrow to order the next batch of plants. 
Check the site on Monday to ensure the soil preparation is complete.
```

**Expected Reminders:**
- "meet with the client on Thursday to discuss the garden design" (type: meeting, due_date: next Thursday)
- "call the nursery tomorrow to order the next batch of plants" (type: call, due_date: tomorrow)
- "Check the site on Monday to ensure the soil preparation is complete" (type: check, due_date: next Monday)

**Expected Financials:**
- Actual earnings: ["received 80,000 shillings as the first payment"]
- Actual expenses: ["Spent 35,000 shillings on plants and soil", "Paid 4,500 shillings for delivery"]
- Projected earnings: ["total project quote is 280,000 shillings"]
- Projected expenses: ["additional plants and irrigation pipes worth about 45,000 shillings"]

---

## Voice Note 9: Simple Follow-up with Reminder
```
Quick reminder note. 
I need to return to the Ruaka job site on Friday to check the tile alignment. 
The client mentioned some tiles look uneven. 
I should call them before I go to confirm they'll be home.
```

**Expected Reminders:**
- "return to the Ruaka job site on Friday to check the tile alignment" (type: return, due_date: next Friday)
- "call them before I go to confirm they'll be home" (type: call, due_date: before Friday)

**Expected Financials:**
- None (no financial information mentioned)

---

## Voice Note 10: Payment Received and Expense Incurred
```
Payment update. 
For the Thika welding job, the client has sent me 20,000 shillings for material purchase. 
The remaining amount after material purchase, I can use it to cover my income. 
I already spent 8,000 shillings on some initial metal sheets. 
The total job is quoted at 50,000 shillings.
```

**Expected Reminders:**
- None (no reminders mentioned)

**Expected Financials:**
- Actual earnings: ["client has sent me 20,000 shillings"]
- Actual expenses: ["spent 8,000 shillings on some initial metal sheets"]
- Projected earnings: ["total job is quoted at 50,000 shillings"]

---

## Testing Checklist

When testing these voice notes, verify:

### Reminders:
- [ ] All reminders are extracted correctly
- [ ] Due dates are parsed correctly (tomorrow, Monday, Friday, next week, etc.)
- [ ] Reminder types are assigned correctly (call, return, follow_up, check, meeting)
- [ ] Reminders appear in the reminders screen after extraction

### Financials:
- [ ] Actual expenses are extracted (past tense: "spent", "paid", "bought")
- [ ] Actual earnings are extracted (past tense: "paid", "received", "sent")
- [ ] Projected expenses are extracted (future tense: "will cost", "adds to", "estimated")
- [ ] Projected earnings are extracted (quotes: "quote is", "total is", "will pay")
- [ ] Financial data appears correctly in the dashboard
- [ ] Financial summary shows correctly in job detail screen
- [ ] Combined totals (actual + projected) are calculated correctly

### Shopping Items:
- [ ] Shopping items are extracted (e.g., "need to buy", "bring", "get")
- [ ] Items appear in the extracted entities

### General:
- [ ] All entities (phones, amounts, dates, parts, client names, job types, locations) are extracted
- [ ] Cache is working (second identical note should use cache)
- [ ] Different notes trigger fresh LLM calls

