"""Make condensed mock 'original fax' PDFs for the made-up sample packets."""
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
W, H = letter
pages = json.load(open('sample-pages.json')); prof = {p['packet_id']: p for p in json.load(open('sample-profiles.json'))}
meds = json.load(open('sample-meds.json')); hist = json.load(open('sample-history.json'))
EXTRA = {
 "Sample-01": ("No known allergies", "Not in packet"), "Sample-02": ("Latex", "Not in packet"), "Sample-03": ("Sulfa drugs", "O positive (lab report)"),
 "Sample-04": ("Not in packet", "Not in packet"), "Sample-05": ("No known allergies", "Not in packet"), "Sample-06": ("Latex", "Not in packet"),
 "Sample-07": ("Codeine", "A positive (lab report)"), "Sample-08": ("No known allergies", "Not in packet"), "Sample-09": ("Not in packet", "Not in packet"),
 "Sample-10": ("Iodine contrast", "Not in packet")}
for pid, p in prof.items():
    n = pid.split('-')[1]
    p['patient_name'] = f"Sample Patient {n} (made up)"
    p['address'] = "No fixed address (made up)" if p['housing'] == "Unhoused" else "Black box (redacted)"
    p['allergies'], p['blood_type'] = EXTRA[pid]

def wm(c):
    c.saveState(); c.setFillColor(HexColor('#c62828')); c.setFillAlpha(0.13); c.setFont('Helvetica-Bold', 46)
    c.translate(W / 2, H / 2); c.rotate(35); c.drawCentredString(0, 0, "MADE-UP SAMPLE"); c.drawCentredString(0, -56, "NOT A REAL PATIENT"); c.restoreState()

def lines(c, y, items, size=10.5):
    c.setFont('Helvetica', size); c.setFillColor(HexColor('#111111'))
    for t in items:
        c.drawString(64, y, t[:95]); y -= 16
    return y

for pid, p in prof.items():
    c = canvas.Canvas(f"faxes/{pid}-original-fax.pdf", pagesize=letter); c.setTitle(f"{pid} original fax (made-up sample)")
    for pg in [x for x in pages if x['packet_id'] == pid]:
        rng = f"pp. {pg['page_from']}-{pg['page_to']}" if pg['page_from'] != pg['page_to'] else f"p. {pg['page_from']}"
        wm(c)
        c.setFont('Courier', 8); c.setFillColor(HexColor('#444444')); c.drawString(36, H - 24, f"FAX  {pid} (sample)   {rng}")
        c.setFillColor(HexColor('#111111')); c.setFont('Helvetica-Bold', 15); c.drawString(54, H - 70, pg['doc_type'])
        y = lines(c, H - 100, [f"What this page shows: {pg['key_content']}", "Condensed mock of the original pages, for demo use only."]) - 10
        dt = pg['doc_type'].lower()
        if 'face sheet' in dt or 'referral form' in dt or 'calaim' in dt:
            y = lines(c, y, [f"Patient name: {p['patient_name']}", f"Address: {p['address']}", f"Allergies: {p['allergies']}", f"Housing: {p['housing']}", f"Reason for stay: {p['reason']}", f"Expected discharge: {p['discharge']}"])
        if 'medication' in dt:
            y = lines(c, y, ["Medications:"] + [f"  {m['medicine']}  {m['dose']}  {m['route']}  {m['how_often']}  ({m['purpose']})" for m in meds if m['packet_id'] == pid])
        if 'history' in dt or 'progress' in dt or 'consult' in dt:
            y = lines(c, y, ["Conditions noted:"] + [f"  {h['condition']} - {h['status']}" for h in hist if h['packet_id'] == pid] + [f"Recent episode: {p['recent_episode']}. {p['recent_note']}"])
        if 'lab' in dt:
            y = lines(c, y, [f"Blood type: {p['blood_type']}", "Other lab values: not shown in this mock."])
        c.setFont('Helvetica-Oblique', 8); c.setFillColor(HexColor('#666666'))
        c.drawString(36, 30, "Made-up sample for the Packet Triage Board draft. Contains no real patient information.")
        c.showPage()
    c.save()
json.dump(list(prof.values()), open('sample-profiles.json', 'w'), indent=1)
print('ok')
