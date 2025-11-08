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
	
	# Get notes in date range
	notes = db.query(Note).filter(
		Note.owner_id == current_user.id,
		Note.created_at >= period_start,
		Note.created_at <= period_end,
		Note.text.isnot(None)
	).all()
	
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
		
		# Extract entities using NLP (will use cache if available)
		entities = extract_entities(note.text, "KE")
		
		# Process ACTUAL earnings
		for earning_str in entities.earnings:
			amount = extract_amount_value(earning_str)
			total_earnings += amount
			
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
		
		# Process PROJECTED earnings (quotes, estimates)
		for earning_str in entities.projected_earnings:
			amount = extract_amount_value(earning_str)
			total_projected_earnings += amount
			
			# Track by job type
			if entities.job_types:
				for job_type in entities.job_types:
					if job_type not in by_job_type:
						by_job_type[job_type] = {
							"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
							"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
						}
					by_job_type[job_type]["projected_earnings"] += amount
			
			# Track by client
			if entities.client_names:
				for client_name in entities.client_names:
					if client_name not in by_client:
						by_client[client_name] = {
							"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
							"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
						}
					by_client[client_name]["projected_earnings"] += amount
		
		# Process PROJECTED expenses (planned costs, estimates)
		for expense_str in entities.projected_expenses:
			amount = extract_amount_value(expense_str)
			total_projected_expenses += amount
			
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
		
		# Also check amounts field for earnings (if not already in earnings/expenses/projected)
		# This is a fallback - amounts might be earnings or expenses
		for amount_str in entities.amounts:
			# Skip if already categorized
			if (amount_str in entities.earnings or amount_str in entities.expenses or 
				amount_str in entities.projected_earnings or amount_str in entities.projected_expenses):
				continue
			
			amount = extract_amount_value(amount_str)
			note_lower = note.text.lower()
			
			# Heuristic: check if it's actual or projected
			if any(word in note_lower for word in ["quote", "estimated", "will charge", "will cost", "adds to", "total will be"]):
				# Projected
				if any(word in note_lower for word in ["quote", "will charge", "estimated", "total will be"]):
					total_projected_earnings += amount
					if entities.job_types:
						for job_type in entities.job_types:
							if job_type not in by_job_type:
								by_job_type[job_type] = {
									"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
									"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
								}
							by_job_type[job_type]["projected_earnings"] += amount
					if entities.client_names:
						for client_name in entities.client_names:
							if client_name not in by_client:
								by_client[client_name] = {
									"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
									"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
								}
							by_client[client_name]["projected_earnings"] += amount
				elif any(word in note_lower for word in ["will cost", "adds to", "adds KES"]):
					total_projected_expenses += amount
					if entities.job_types:
						for job_type in entities.job_types:
							if job_type not in by_job_type:
								by_job_type[job_type] = {
									"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
									"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
								}
							by_job_type[job_type]["projected_expenses"] += amount
					if entities.client_names:
						for client_name in entities.client_names:
							if client_name not in by_client:
								by_client[client_name] = {
									"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
									"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
								}
							by_client[client_name]["projected_expenses"] += amount
			elif any(word in note_lower for word in ["paid", "received", "got paid", "they paid", "client paid"]):
				# Actual earnings
				total_earnings += amount
				if entities.job_types:
					for job_type in entities.job_types:
						if job_type not in by_job_type:
							by_job_type[job_type] = {
								"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
								"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
							}
						by_job_type[job_type]["earnings"] += amount
				if entities.client_names:
					for client_name in entities.client_names:
						if client_name not in by_client:
							by_client[client_name] = {
								"earnings": 0.0, "expenses": 0.0, "profit": 0.0,
								"projected_earnings": 0.0, "projected_expenses": 0.0, "projected_profit": 0.0
							}
						by_client[client_name]["earnings"] += amount
	
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

