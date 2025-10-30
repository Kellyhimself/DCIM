from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime


def generate_job_pdf(company_name: str, client_name: str, site: str | None, job_id: str, items: list[tuple[str, int, float]] | None = None) -> bytes:
	buf = BytesIO()
	c = canvas.Canvas(buf, pagesize=A4)
	w, h = A4
	margin = 40
	c.setFont("Helvetica-Bold", 16)
	c.drawString(margin, h - margin, company_name)
	c.setFont("Helvetica", 10)
	c.drawString(margin, h - margin - 16, f"Job ID: {job_id}")
	c.drawString(margin, h - margin - 30, f"Client: {client_name}")
	c.drawString(margin, h - margin - 44, f"Site: {site or '-'}")
	c.drawString(margin, h - margin - 58, f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

	y = h - margin - 90
	c.setFont("Helvetica-Bold", 12)
	c.drawString(margin, y, "Items")
	y -= 16
	c.setFont("Helvetica", 10)
	total = 0.0
	for label, qty, price in (items or []):
		c.drawString(margin, y, f"{label}")
		c.drawRightString(w - margin - 120, y, f"x{qty}")
		c.drawRightString(w - margin, y, f"KES {qty * price:,.2f}")
		total += qty * price
		y -= 14
		if y < 80:
			c.showPage()
			y = h - margin

	c.setFont("Helvetica-Bold", 12)
	c.drawRightString(w - margin, 60, f"Total: KES {total:,.2f}")
	c.showPage()
	c.save()
	buf.seek(0)
	return buf.read()
