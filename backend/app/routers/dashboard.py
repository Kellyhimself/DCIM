from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import re
import logging

from backend.app.deps import get_db, get_current_user
from backend.app.models import User, Note
from backend.app.routers.nlp import extract_entities
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class FinancialSummary(BaseModel):
	# Actual (money already received/spent)
	total_earnings: float
	total_expenses: float
	net_profit: float
	# Projected (quotes, estimates, planned)
	total_projected_earnings: float
	total_projected_expenses: float
	projected_profit: float
	# Combined totals
	total_combined_earnings: float
	total_combined_expenses: float
	combined_profit: float
	period_start: datetime
	period_end: datetime
	by_job_type: dict[str, dict]  # {job_type: {earnings, expenses, profit, projected_earnings, projected_expenses, projected_profit}}
	by_client: dict[str, dict]  # {client_name: {earnings, expenses, profit, projected_earnings, projected_expenses, projected_profit}}


def extract_amount_value(amount_str: str) -> float:
	"""Extract numeric value from amount string like '5000 Kenyan shillings' or '2000'."""
	# Remove common currency words
	cleaned = re.sub(r'(kenyan\s+)?shillings?|kes|ksh', '', amount_str.lower(), flags=re.IGNORECASE)
	# Remove commas and extract numbers
	numbers = re.findall(r'[\d,]+\.?\d*', cleaned)
	if numbers:
		# Remove commas and convert to float
		value_str = numbers[0].replace(',', '')
		try:
			return float(value_str)
		except ValueError:
			pass
	return 0.0


@router.get("/financial", response_model=FinancialSummary)
def get_financial_dashboard(
	start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD), defaults to 30 days ago"),
	end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD), defaults to today"),
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""
	Get financial summary dashboard with earnings, expenses, and profits.
	Extracts financial data from notes using NLP.
	"""
	# Parse dates
	if end_date:
		try:
			period_end = datetime.strptime(end_date, "%Y-%m-%d")
			period_end = datetime.combine(period_end.date(), datetime.max.time())
		except ValueError:
			period_end = datetime.utcnow()
	else:
		period_end = datetime.utcnow()
	
	if start_date:
		try:
			period_start = datetime.strptime(start_date, "%Y-%m-%d")
			period_start = datetime.combine(period_start.date(), datetime.min.time())
		except ValueError:
			period_start = period_end - timedelta(days=30)
	else:
		period_start = period_end - timedelta(days=30)
	
	# Get notes in date range - ensure we only get notes for the current user
	notes = db.query(Note).filter(
		Note.owner_id == current_user.id,
		Note.created_at >= period_start,
		Note.created_at <= period_end,
		Note.text.isnot(None)
	).all()
	
	logger.info(
		f"Financial dashboard query for user {current_user.id} - "
		f"Found {len(notes)} notes in date range {period_start.date()} to {period_end.date()}"
	)
	
	total_earnings = 0.0
	total_expenses = 0.0
	total_projected_earnings = 0.0
	total_projected_expenses = 0.0
	by_job_type: dict[str, dict] = {}
	by_client: dict[str, dict] = {}
	
	# Process each note
	for note in notes:
		if not note.text:
			continue
		
		# Verify note belongs to current user (double-check)
		if note.owner_id != current_user.id:
			logger.warning(f"Skipping note {note.id} - owner_id {note.owner_id} != current_user.id {current_user.id}")
			continue
		
		# Extract entities using NLP (will use cache if available)
		entities = extract_entities(note.text, "KE")
		
		# Log note processing for debugging
		note_earnings = 0.0
		note_expenses = 0.0
		note_projected_earnings = 0.0
		note_projected_expenses = 0.0
		
		# Process ACTUAL earnings
		for earning_str in entities.earnings:
			amount = extract_amount_value(earning_str)
			total_earnings += amount
			note_earnings += amount
			
			# Track by job type
			if entities.job_types:
				for job_type in entities.job_types:
					if job_type not in by_job_type:
						by_job_type[job_type] = {
							"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
							"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
						}
					by_job_type[job_type]["earnings"] += amount
			
			# Track by client
			if entities.client_names:
				for client_name in entities.client_names:
					if client_name not in by_client:
						by_client[client_name] = {
							"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
							"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
						}
					by_client[client_name]["earnings"] += amount
		
		# Process ACTUAL expenses
		for expense_str in entities.expenses:
			amount = extract_amount_value(expense_str)
			total_expenses += amount
			note_expenses += amount
			
			# Track by job type
			if entities.job_types:
				for job_type in entities.job_types:
					if job_type not in by_job_type:
						by_job_type[job_type] = {
							"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
							"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
						}
					by_job_type[job_type]["expenses"] += amount
			
			# Track by client
			if entities.client_names:
				for client_name in entities.client_names:
					if client_name not in by_client:
						by_client[client_name] = {
							"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
							"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
						}
					by_client[client_name]["expenses"] += amount
		
		# Process PROJECTED expenses FIRST (planned costs, estimates)
		# Filter out labor charges that LLM incorrectly categorized as expenses
		note_projected_expenses = 0.0
		labor_charges_from_expenses = []  # Track labor charges that were misclassified
		for expense_str in entities.projected_expenses:
			expense_lower = expense_str.lower()
			# Check if this is actually a labor charge (common LLM mistake)
			if any(phrase in expense_lower for phrase in ["labor charges", "labour charges", "labor fees", "labour fees", "charges will be", "charges are"]):
				# This is a labor charge, not an expense - move it to earnings
				amount = extract_amount_value(expense_str)
				labor_charges_from_expenses.append(amount)
			else:
				# This is a legitimate projected expense
				amount = extract_amount_value(expense_str)
				total_projected_expenses += amount
				note_projected_expenses += amount
				
				# Track by job type
				if entities.job_types:
					for job_type in entities.job_types:
						if job_type not in by_job_type:
							by_job_type[job_type] = {
								"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
								"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
							}
						by_job_type[job_type]["projected_expenses"] += amount
				
				# Track by client
				if entities.client_names:
					for client_name in entities.client_names:
						if client_name not in by_client:
							by_client[client_name] = {
								"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
								"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
							}
						by_client[client_name]["projected_expenses"] += amount
		
		# Fallback: Process uncategorized amounts to capture expenses that LLM missed
		# This MUST run BEFORE calculating earnings from total quote
		processed_amounts = set()
		for earning_str in entities.earnings:
			processed_amounts.add(extract_amount_value(earning_str))
		for expense_str in entities.expenses:
			processed_amounts.add(extract_amount_value(expense_str))
		for earning_str in entities.projected_earnings:
			processed_amounts.add(extract_amount_value(earning_str))
		for expense_str in entities.projected_expenses:
			processed_amounts.add(extract_amount_value(expense_str))
		
		# Process fallback amounts to capture uncategorized expenses
		for amount_str in entities.amounts:
			amount_value = extract_amount_value(amount_str)
			# Skip if already categorized or zero
			if amount_value in processed_amounts or amount_value == 0.0:
				continue
			
			note_lower = note.text.lower()
			amount_str_lower = amount_str.lower()
			amount_pos = note_lower.find(amount_str_lower)
			
			# Get context around the amount (100 chars before and after)
			if amount_pos >= 0:
				context_start = max(0, amount_pos - 100)
				context_end = min(len(note_lower), amount_pos + len(amount_str_lower) + 100)
				context = note_lower[context_start:context_end]
			else:
				context = note_lower
			
			# EXCLUDE profit amounts - profit is calculated, not a separate earning/expense
			if any(word in context for word in ["profit", "profit of", "made a profit", "profit after", "profit is"]):
				# This is a profit amount, not an earning or expense - skip it
				processed_amounts.add(amount_value)
				continue
			
			# Check for expense indicators first
			if any(word in context for word in ["will cost", "costs", "cost roughly", "cost about", "adds to", "adds kes"]):
				# Projected expense - add to note_projected_expenses so it's included in earnings calculation
				total_projected_expenses += amount_value
				note_projected_expenses += amount_value
				processed_amounts.add(amount_value)
				if entities.job_types:
					for job_type in entities.job_types:
						if job_type not in by_job_type:
							by_job_type[job_type] = {
								"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
								"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
							}
						by_job_type[job_type]["projected_expenses"] += amount_value
				if entities.client_names:
					for client_name in entities.client_names:
						if client_name not in by_client:
							by_client[client_name] = {
								"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
								"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
							}
						by_client[client_name]["projected_expenses"] += amount_value
			elif any(word in context for word in ["spent", "paid for"]):
				# Actual expense
				total_expenses += amount_value
				note_expenses += amount_value
				processed_amounts.add(amount_value)
				if entities.job_types:
					for job_type in entities.job_types:
						if job_type not in by_job_type:
							by_job_type[job_type] = {
								"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
								"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
							}
						by_job_type[job_type]["expenses"] += amount_value
				if entities.client_names:
					for client_name in entities.client_names:
						if client_name not in by_client:
							by_client[client_name] = {
								"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
								"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
							}
						by_client[client_name]["expenses"] += amount_value
			elif any(word in context for word in ["paid", "received", "got paid", "they paid", "client paid", "gave me", "deposit"]):
				# Actual earnings - but only if not in a profit context
				# Check if this amount is mentioned in a profit calculation context
				profit_context_words = ["profit", "profit of", "made a profit", "profit after", "profit is"]
				if not any(word in context for word in profit_context_words):
					total_earnings += amount_value
					note_earnings += amount_value
					processed_amounts.add(amount_value)
					if entities.job_types:
						for job_type in entities.job_types:
							if job_type not in by_job_type:
								by_job_type[job_type] = {
									"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
									"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
								}
							by_job_type[job_type]["earnings"] += amount_value
					if entities.client_names:
						for client_name in entities.client_names:
							if client_name not in by_client:
								by_client[client_name] = {
									"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
									"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
								}
							by_client[client_name]["earnings"] += amount_value
				else:
					# Profit amount - mark as processed but don't add to earnings
					processed_amounts.add(amount_value)
			# Note: We don't add uncategorized amounts to projected_earnings here
			# because they might be part of a total quote, which we handle below
		
		# NOW calculate projected earnings AFTER fallback has captured all expenses
		# Process PROJECTED earnings (quotes, estimates)
		# If we have total quote, use quote - expenses (profit)
		# If we have labor charges but no total quote, use labor charges
		# Otherwise, use what the LLM extracted
		total_quote_amount = None
		labor_charges_amount = None
		other_projected_earnings = []
		
		# Include labor charges that were incorrectly categorized as expenses
		for amount in labor_charges_from_expenses:
			if labor_charges_amount is None:
				labor_charges_amount = amount
			else:
				# If we already have labor charges, add to other earnings
				other_projected_earnings.append(amount)
		
		for earning_str in entities.projected_earnings:
			earning_lower = earning_str.lower()
			amount = extract_amount_value(earning_str)
			
			# Check if this is a "total quote" (includes everything: materials + labor)
			# Also check for variations like "total pot", "total cut" (transcription errors)
			if any(phrase in earning_lower for phrase in ["total quote", "quote is", "quote to", "total will be", "revised quote", "updated quote", "total pot", "total cut"]):
				total_quote_amount = amount
			# Check if this is labor charges (the actual earnings/profit)
			elif any(phrase in earning_lower for phrase in ["labor charges", "labour charges", "labor fees", "labour fees", "charges will be", "charges are"]):
				labor_charges_amount = amount
			else:
				# Other projected earnings
				other_projected_earnings.append(amount)
		
		# Calculate projected earnings: if we have total quote, use quote - expenses (profit)
		# If we have labor charges but no total quote, use labor charges
		# Otherwise, use other projected earnings
		if total_quote_amount is not None:
			# We have a total quote - earnings = quote - expenses (profit after material costs)
			# note_projected_expenses now includes fallback amounts
			projected_earnings_for_note = total_quote_amount - note_projected_expenses
			if projected_earnings_for_note < 0:
				projected_earnings_for_note = 0.0
		elif labor_charges_amount is not None:
			# No total quote, but we have labor charges - use labor charges as earnings
			projected_earnings_for_note = labor_charges_amount
		else:
			# No total quote or labor charges, use other projected earnings
			projected_earnings_for_note = sum(other_projected_earnings)
		
		# Add calculated earnings to totals
		if projected_earnings_for_note > 0:
			total_projected_earnings += projected_earnings_for_note
			note_projected_earnings += projected_earnings_for_note
			
			# Track by job type
			if entities.job_types:
				for job_type in entities.job_types:
					if job_type not in by_job_type:
						by_job_type[job_type] = {
							"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
							"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
						}
					by_job_type[job_type]["projected_earnings"] += projected_earnings_for_note
			
			# Track by client
			if entities.client_names:
				for client_name in entities.client_names:
					if client_name not in by_client:
						by_client[client_name] = {
							"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
							"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
						}
					by_client[client_name]["projected_earnings"] += projected_earnings_for_note
	
	# Calculate profits
	net_profit = total_earnings - total_expenses
	projected_profit = total_projected_earnings - total_projected_expenses
	total_combined_earnings = total_earnings + total_projected_earnings
	total_combined_expenses = total_expenses + total_projected_expenses
	combined_profit = total_combined_earnings - total_combined_expenses
	
	# Calculate profits by job type and client
	for job_type, data in by_job_type.items():
		data["profit"] = data["earnings"] - data["expenses"]
		data["projected_profit"] = data["projected_earnings"] - data["projected_expenses"]
	
	for client_name, data in by_client.items():
		data["profit"] = data["earnings"] - data["expenses"]
		data["projected_profit"] = data["projected_earnings"] - data["projected_expenses"]
	
	logger.info(
		f"Financial dashboard for user {current_user.id} - "
		f"Actual: Earnings={total_earnings}, Expenses={total_expenses}, Profit={net_profit} | "
		f"Projected: Earnings={total_projected_earnings}, Expenses={total_projected_expenses}, Profit={projected_profit}"
	)
	
	return FinancialSummary(
		total_earnings=total_earnings,
		total_expenses=total_expenses,
		net_profit=net_profit,
		total_projected_earnings=total_projected_earnings,
		total_projected_expenses=total_projected_expenses,
		projected_profit=projected_profit,
		total_combined_earnings=total_combined_earnings,
		total_combined_expenses=total_combined_expenses,
		combined_profit=combined_profit,
		period_start=period_start,
		period_end=period_end,
		by_job_type=by_job_type,
		by_client=by_client
	)

