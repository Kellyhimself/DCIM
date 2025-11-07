from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
from typing import Optional, List, Dict


def _wrap_text(c: canvas.Canvas, text: str, x: float, y: float, max_width: float, font_size: int = 10) -> float:
	"""Wrap text and draw it, returning the new y position."""
	words = text.split() 
	lines = []
	current_line = []
	current_width = 0
	
	for word in words:
		test_line = " ".join(current_line + [word])
		width = c.stringWidth(test_line, "Helvetica", font_size)
		if width <= max_width:
			current_line.append(word)
			current_width = width
		else:
			if current_line:
				lines.append(" ".join(current_line))
			current_line = [word]
			current_width = c.stringWidth(word, "Helvetica", font_size)
	
	if current_line:
		lines.append(" ".join(current_line))
	
	for line in lines:
		c.drawString(x, y, line)
		y -= font_size + 2 #subtracts the font size and 2 from the y position
		#this is to ensure that the text does not overlap with the next line
		#this is a good practice to avoid text overlap
		#x and y are just like what we learnt in basic maths, x is the horizontal position and y is the vertical position
		#so when we subtract the font size and 2 from the y position, we are moving the text down by the font size and 2 units
		#this is to ensure that the text does not overlap with the next line
		
	
	return y #returns the new y position


def generate_job_pdf(
	company_name: str,
	client_name: str,
	site: str | None,
	job_id: str,
	items: list[tuple[str, int, float]] | None = None,#a tuple is a list of items that are separated by a comma
	notes: List[Dict] | None = None,
	parts: List[str] | None = None,
	amounts: List[str] | None = None,
	dates: List[str] | None = None,
	phones: List[str] | None = None
) -> bytes:
	"""Generate a comprehensive job PDF with notes, parts, and amounts."""
	buf = BytesIO()
	c = canvas.Canvas(buf, pagesize=A4)
	w, h = A4
	margin = 40
	line_height = 14
	
	# Header
	c.setFont("Helvetica-Bold", 16)
	c.drawString(margin, h - margin, company_name)
	c.setFont("Helvetica", 10)
	y = h - margin - 16
	c.drawString(margin, y, f"Job ID: {job_id[:8]}...")
	y -= line_height
	c.drawString(margin, y, f"Client: {client_name}")
	y -= line_height
	c.drawString(margin, y, f"Site: {site or '-'}")
	y -= line_height
	c.drawString(margin, y, f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
	
	y -= line_height * 2
	
	# Notes section
	if notes:
		c.setFont("Helvetica-Bold", 12)
		c.drawString(margin, y, "Notes")
		y -= line_height
		c.setFont("Helvetica", 9)
		for note in notes:
			note_text = note.get("text", "")
			note_date = note.get("created_at", "")
			if note_text:
				# Format date if available
				if note_date:
					try:
						if isinstance(note_date, str):
							from datetime import datetime as dt
							dt_obj = dt.fromisoformat(note_date.replace('Z', '+00:00'))
							date_str = dt_obj.strftime('%Y-%m-%d %H:%M')
						else:
							date_str = str(note_date)
					except:
						date_str = ""
					if date_str:
						c.setFont("Helvetica-Oblique", 8)
						c.drawString(margin, y, f"[{date_str}]")
						y -= 8
				c.setFont("Helvetica", 9)
				y = _wrap_text(c, note_text, margin, y, w - 2 * margin, 9)
				y -= 4
	
	# Parts section
	if parts:
		y -= line_height
		if y < 100:
			c.showPage()
			y = h - margin
		c.setFont("Helvetica-Bold", 12)
		c.drawString(margin, y, "Parts & Materials")
		y -= line_height
		c.setFont("Helvetica", 10)
		for part in parts:
			c.drawString(margin + 10, y, f"• {part}")
			y -= line_height
			if y < 80:
				c.showPage()
				y = h - margin
	
	# Key Information section
	y -= line_height
	if y < 100:
		c.showPage()
		y = h - margin
	
	has_key_info = False
	if phones or dates or amounts:
		c.setFont("Helvetica-Bold", 12)
		c.drawString(margin, y, "Key Information")
		y -= line_height
		c.setFont("Helvetica", 10)
		has_key_info = True
		
		if phones:
			c.drawString(margin + 10, y, f"Phone: {', '.join(phones)}")
			y -= line_height
			if y < 80:
				c.showPage()
				y = h - margin
		
		if dates:
			c.drawString(margin + 10, y, f"Dates: {', '.join(dates)}")
			y -= line_height
			if y < 80:
				c.showPage()
				y = h - margin
	
	# Items/Line items section
	if items:
		y -= line_height if has_key_info else 0
		if y < 100:
			c.showPage()
			y = h - margin
		c.setFont("Helvetica-Bold", 12)
		c.drawString(margin, y, "Items")
		y -= line_height
		c.setFont("Helvetica", 10)
		total = 0.0
		for label, qty, price in items:
			c.drawString(margin, y, f"{label}")
			c.drawRightString(w - margin - 120, y, f"x{qty}")
			c.drawRightString(w - margin, y, f"KES {qty * price:,.2f}")
			total += qty * price
			y -= line_height
			if y < 80:
				c.showPage()
				y = h - margin
		
		c.setFont("Helvetica-Bold", 12)
		c.drawRightString(w - margin, y, f"Total: KES {total:,.2f}")
		y -= line_height
	
	# Summary totals from amounts
	if amounts:
		y -= line_height
		if y < 100:
			c.showPage()
			y = h - margin
		c.setFont("Helvetica-Bold", 12)
		c.drawString(margin, y, "Amounts Mentioned")
		y -= line_height
		c.setFont("Helvetica", 10)
		for amount in amounts:
			c.drawString(margin + 10, y, f"• {amount}")
			y -= line_height
			if y < 80:
				c.showPage()
				y = h - margin
	
	c.showPage()
	c.save()
	buf.seek(0)
	return buf.read()
