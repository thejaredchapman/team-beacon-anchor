"""Create made-up sample referral files, plus built-in "demo answers" so the pre-read can be shown
without an API key. No real patient information anywhere.

samples/                 sample files in several formats + demo-answers.json
fax-inbox/               two fax-to-email messages:
  1. an incomplete fax (3 pages): form says no cognitive problems, face sheet lists dementia
  2. a complete packet (8 pages): every core document, ready for the fast lane
Use make_resend(referral_id) (or the "Demo: hospital resends pages" button) to simulate the
hospital sending the missing medication list and vitals.
"""
import hashlib
import json
import subprocess
from email.message import EmailMessage
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SAMPLES, INBOX = HERE / "samples", HERE / "fax-inbox"
BANNER = "MADE-UP SAMPLE - NOT A REAL PATIENT"


def page(title, lines):
    im = Image.new("L", (1275, 1650), 255)
    d = ImageDraw.Draw(im)
    d.text((80, 60), BANNER, fill=90)
    d.text((80, 120), title, fill=0)
    for i, ln in enumerate(lines):
        d.text((80, 200 + i * 40), ln, fill=0)
    return im


def F(key, source, status, value=None, quote=None):
    d = {"key": key, "source": source, "status": status}
    if value:
        d["value"] = value
    if quote:
        d["quote"] = quote
    return d


# ---- Packet 1: incomplete fax ----
P1 = [
    ("ihh_referral_form", "IHH Referral Form (sample)", ["Currently homeless: Yes", "Chief complaint: cellulitis of left leg", "Cognitive impairment: No",
      "Self administers all meds: Yes", "Wounds: No", "Requires O2: No"],
     [F("housing", "form", "found", "Currently homeless", "Currently homeless: Yes"), F("admitting_diagnosis", "form", "found", "Cellulitis, left leg", "Chief complaint: cellulitis of left leg"),
      F("cognitive_impairment", "form", "found", "Form says no cognitive impairment", "Cognitive impairment: No"),
      F("self_admin_meds", "form", "found", "Self-administers all medicines", "Self administers all meds: Yes"),
      F("wounds", "form", "found", "No wounds", "Wounds: No"), F("oxygen", "form", "found", "No oxygen", "Requires O2: No")], [], []),
    ("face_sheet", "Face sheet (sample)", ["Diagnoses:", "  Cellulitis of left lower limb", "  Alzheimer disease, mild", "  Hypertension", "Allergies: none known"],
     [F("cognitive_impairment", "chart", "found", "Dementia listed among diagnoses", "Alzheimer disease, mild")],
     [{"rule_id": "NEU-X5", "text": "Face sheet lists dementia, an IHH exclusion", "quote": "Alzheimer disease, mild"}],
     [{"fact_key": "cognitive_impairment", "text": "Form says no cognitive impairment; face sheet lists dementia", "quote": "Alzheimer disease, mild", "quote2": "Cognitive impairment: No", "doc_page2": 1}]),
    ("pt_ot_evaluation", "PT evaluation (sample)", ["Ambulation: 250 ft, no device", "Transfers: independent", "ADLs: independent with bathing and toileting"],
     [F("walk_100ft_transfers", "chart", "found", "Walks 250 ft; transfers independently", "Ambulation: 250 ft, no device"),
      F("dme_independent", "chart", "found", "No device used", "Ambulation: 250 ft, no device"),
      F("adl_independent", "chart", "found", "Independent with bathing and toileting", "ADLs: independent with bathing and toileting")], [], []),
]

# ---- Packet 2: complete ----
P2 = [
    ("ihh_referral_form", "IHH Referral Form (sample)", ["Currently homeless: Yes", "Chief complaint: closed wrist fracture", "Cognitive impairment: No", "Sex offender: No"],
     [F("housing", "form", "found", "Currently homeless", "Currently homeless: Yes"), F("admitting_diagnosis", "form", "found", "Closed wrist fracture", "Chief complaint: closed wrist fracture"),
      F("sex_offender", "form", "found", "No", "Sex offender: No")], [], []),
    ("face_sheet", "Face sheet (sample)", ["Diagnoses: closed fracture of right wrist", "Allergies: none known", "Conservatorship: none"],
     [F("cognitive_impairment", "chart", "found", "No cognitive diagnosis listed", "Diagnoses: closed fracture of right wrist"),
      F("conservatorship_fsp", "chart", "found", "None", "Conservatorship: none")], [], []),
    ("calaim_authorization", "CalAIM authorization (sample)", ["Pathway: recuperative care only", "Oriented to person, place, time, situation: all checked", "Specialist follow-up: orthopedics booked"],
     [F("aox4", "form", "found", "Oriented x4", "Oriented to person, place, time, situation: all checked"), F("follow_up", "form", "found", "Orthopedics follow-up booked", "Specialist follow-up: orthopedics booked")], [], []),
    ("history_physical", "History and physical (sample)", ["Alert and oriented x4", "No suicidal ideation, no hallucinations", "Mood stable; no psychiatric history",
      "No alcohol or drug use", "Calm and cooperative", "Not diabetic", "Continent; no catheter", "No IV access at discharge", "No wounds"],
     [F("aox4", "chart", "found", "Alert and oriented x4", "Alert and oriented x4"), F("si_hallucinations", "chart", "found", "None", "No suicidal ideation, no hallucinations"),
      F("mental_health_stable", "chart", "found", "Stable, no psychiatric history", "Mood stable; no psychiatric history"),
      F("substance_withdrawal", "chart", "found", "No substance use", "No alcohol or drug use"), F("aggression", "chart", "found", "Calm and cooperative", "Calm and cooperative"),
      F("diabetes", "chart", "found", "Not diabetic", "Not diabetic"), F("continence", "chart", "found", "Continent, no catheter", "Continent; no catheter"),
      F("iv_access", "chart", "found", "No IV access", "No IV access at discharge"), F("wounds", "chart", "found", "No wounds", "No wounds")], [], []),
    ("vitals", "Vital signs (sample)", ["Five sets of vital signs, all within normal limits", "Room air, oxygen saturation normal"],
     [F("vitals_last5", "chart", "found", "Five sets, normal", "Five sets of vital signs, all within normal limits"), F("oxygen", "chart", "found", "Room air", "Room air, oxygen saturation normal")], [], []),
    ("medication_list", "Discharge medication list (sample)", ["Acetaminophen 650 mg by mouth every 6 hours as needed", "30-day supply provided", "Patient self-administers"],
     [F("med_list_supply", "chart", "found", "Discharge list with 30-day supply", "30-day supply provided"), F("self_admin_meds", "chart", "found", "Self-administers", "Patient self-administers")], [], []),
    ("pt_ot_evaluation", "PT evaluation (sample)", ["Ambulation: 400 ft, no device", "Transfers: independent", "ADLs: independent"],
     [F("walk_100ft_transfers", "chart", "found", "Walks 400 ft; transfers independently", "Ambulation: 400 ft, no device"),
      F("dme_independent", "chart", "found", "No device", "Ambulation: 400 ft, no device"), F("adl_independent", "chart", "found", "Independent", "ADLs: independent")], [], []),
    ("labs", "Lab results (sample)", ["TB QuantiFERON: negative", "MRSA nasal swab: negative", "COVID rapid test: negative (date removed)", "No active infection; not on isolation", "Home health: not needed"],
     [F("tb_test", "chart", "found", "QuantiFERON negative", "TB QuantiFERON: negative"), F("mrsa_swab", "chart", "found", "Negative", "MRSA nasal swab: negative"),
      F("covid_swab", "chart", "cant_tell", "Negative, but the date is redacted", "COVID rapid test: negative (date removed)"),
      F("isolation", "chart", "found", "Not on isolation", "No active infection; not on isolation"), F("home_health", "chart", "found", "Not needed", "Home health: not needed")], [], []),
]

# ---- Resend for packet 1: medication list + vitals ----
P3 = [
    ("medication_list", "Discharge medication list (sample, resent)", ["Cephalexin 500 mg by mouth four times a day", "30-day supply provided"],
     [F("med_list_supply", "chart", "found", "Discharge list with 30-day supply", "30-day supply provided")], [], []),
    ("vitals", "Vital signs (sample, resent)", ["Five sets of vital signs, stable", "Afebrile"],
     [F("vitals_last5", "chart", "found", "Five sets, stable", "Five sets of vital signs, stable")], [], []),
]


def write_packet(spec, path):
    imgs = [page(title, lines).convert("RGB") for _, title, lines, *_ in spec]
    if path.suffix == ".tiff":
        imgs[0].convert("L").save(path, save_all=True, append_images=[i.convert("L") for i in imgs[1:]], compression="tiff_deflate")
    else:
        imgs[0].save(path, "PDF", save_all=True, append_images=imgs[1:])
    answers = {}
    for i, (doc_type, _, _, facts, reds, conflicts) in enumerate(spec, 1):
        answers[str(i)] = {"doc_type": doc_type, "facts": facts, "red_flags": reds, "contradictions": conflicts}
    return hashlib.sha256(path.read_bytes()).hexdigest(), answers


def fax_email(domain, subject, body, attach):
    msg = EmailMessage()
    msg["From"] = f"Fax Service <incoming@{domain}>"
    msg["To"] = "referrals@ihh-prototype.example.invalid"
    msg["Subject"] = subject
    msg.set_content(body)
    sub = ("image", "tiff") if attach.suffix == ".tiff" else ("application", "pdf")
    msg.add_attachment(attach.read_bytes(), maintype=sub[0], subtype=sub[1], filename=attach.name)
    return bytes(msg)


def make_resend(referral_id, inbox=INBOX):
    """Write a fax email that mentions referral_id and carries the missing pages."""
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / f"resend-{referral_id}.eml"
    path.write_bytes(fax_email("fax.sample-hospital-a.example", f"Re: Referral {referral_id} - missing items",
                               f"Attached are the missing pages for referral {referral_id}. (Made-up sample.)", SAMPLES / "sample-resend.pdf"))
    return path


def main():
    SAMPLES.mkdir(exist_ok=True)
    INBOX.mkdir(exist_ok=True)
    answers = {}
    for spec, name in ((P1, "sample-fax.tiff"), (P2, "sample-complete.pdf"), (P3, "sample-resend.pdf")):
        sha, ans = write_packet(spec, SAMPLES / name)
        answers[sha] = ans
    (SAMPLES / "demo-answers.json").write_text(json.dumps(answers, indent=1))
    page("Photo of a referral form (sample)", ["Taken on a phone"]).convert("RGB").save(SAMPLES / "sample-photo.png")
    txt = SAMPLES / "sample-notes.txt"
    txt.write_text(BANNER + "\nProgress note: improving on oral antibiotics.\n")
    subprocess.run(["textutil", "-convert", "docx", str(txt), "-output", str(SAMPLES / "sample-notes.docx")], check=False)
    (INBOX / "sample-fax-email-1.eml").write_bytes(fax_email("fax.sample-hospital-a.example", "Fax received (3 pages) - made-up sample 1",
                                                              "You have received a fax. The pages are attached. (Made-up sample.)", SAMPLES / "sample-fax.tiff"))
    (INBOX / "sample-fax-email-2.eml").write_bytes(fax_email("fax.sample-hospital-b.example", "Fax received (8 pages) - made-up sample 2",
                                                              "You have received a fax. The pages are attached. (Made-up sample.)", SAMPLES / "sample-complete.pdf"))
    print("samples:", sorted(p.name for p in SAMPLES.iterdir()), "| inbox:", sorted(p.name for p in INBOX.glob("*.eml")))


if __name__ == "__main__":
    main()
