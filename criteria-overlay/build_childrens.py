"""Transcribe IHH's children's and family recuperative care criteria into JSON with stable IDs.

Source: claude-impact-lab-oc/challenges/1-referral-intake/criteria/childrens-admission-criteria.md
Wording is IHH's as transcribed there. IDs (KID-*) are added locally, not by IHH.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def items(prefix, texts, kind):
    return [{"id": f"{prefix}{i + 1}", "text": t, "kind": kind} for i, t in enumerate(texts)]

doc = {
    "title": "Children's and Family Recuperative Care Admission Criteria and Eligibility (under 18 years old)",
    "source": "Transcribed from childrens-admission-criteria.md. Short items keep IHH's wording; long paragraphs (ADLs, mobility, cognition, vitals) are condensed into separate rules, so check the markdown for the full text. KID-* IDs, kinds, needs_date and gap flags are local additions, not IHH's.",
    "applies_to": "Patients under 18. No children's sample packets exist in the event repo.",
    "sections": [
        {"section": "Pre-screen", "rules": [
            {"id": "KID-PRE-1", "kind": "note", "text": "A nurse will visit the hospital to pre-screen the family and child, collaborating with the social worker and discharge nurse so the discharge process and care plan stay consistent after the child leaves the hospital."}]},
        {"section": "Family", "rules": [
            {"id": "KID-FAM-1", "kind": "note", "text": "Recuperative care is voluntary. Background checks are conducted on all adults and legal guardians accompanying the child, through Megan's Law and local courts."}]},
        {"section": "Housing", "rules": [
            {"id": "KID-HOU-1", "kind": "note", "text": "Maximum of 3 people in a room."},
            {"id": "KID-HOU-2", "kind": "note", "text": "One to two adults per room with one recuperative care child."},
            {"id": "KID-HOU-3", "kind": "note", "text": "If the child is readmitted to the hospital, the family can remain in recuperative care unless the admission is more than 1 week; then the family may be placed in a short-term hotel property in the surrounding city."}]},
        {"section": "Accepted diagnoses", "rules": items("KID-DX-E", [
            "Asthma exacerbations", "Closed fractures including upper and lower extremity fractures with limited mobility",
            "Constipation requiring maintenance regimen", "Diabetes mellitus with strict guidance and education",
            "Post-allergic reaction monitoring discharged from the hospital", "Pyelonephritis treated with oral antibiotics",
            "Deep cuts requiring stitches", "Minor burns", "Attention-deficit/hyperactive disorder (ADHD)", "Anxiety disorder",
            "Autism spectrum disorder", "Depression, mild, stabilized on medication", "Oppositional defiant disorder",
            "Post-traumatic stress disorder (PTSD)", "Obsessive-compulsive disorder (OCD)"], "eligible_condition")},
        {"section": "Infection control", "rules": [
            {"id": "KID-INF-1", "kind": "document", "text": "A negative MRSA swab must be documented prior to admission for patients coming from an inpatient hospitalization."},
            {"id": "KID-INF-2", "kind": "document", "needs_date": True, "text": "A COVID-19 swab (rapid test accepted) must show a negative result within the last 24 hours."},
            {"id": "KID-INF-3", "kind": "must", "needs_date": True, "text": "All infectious diseases should be resolved for at least 24 hours without fever reducers such as acetaminophen or ibuprofen."}]},
        {"section": "Ineligible (including but not limited to)", "rules": items("KID-DX-X", [
            "Colds", "Conjunctivitis (pink eye), unless on ophthalmic drops for 24 hours", "Hand, foot and mouth disease", "Fifth disease",
            "Roseola", "Chicken pox, unless all blisters have scabbed over, about 5-7 days and rash has appeared", "Gastroenteritis (stomach flu)",
            "Impetigo", "Respiratory syncytial virus (RSV)", "Croup", "Strep throat", "Influenza", "Whooping cough", "Meningitis", "Diarrhea",
            "Fever", "Head lice", "Measles", "Viral bronchitis", "Conduct disorders", "Depression, moderate to severe", "Bipolar disorder",
            "Oppositional defiant disorder", "Explosive disorders", "Schizophrenia", "Eating disorders", "Substance abuse"], "exclude")},
        {"section": "Vital signs", "rules": [
            {"id": "KID-VS-1", "kind": "document", "text": "A minimum of five recent vital signs (blood pressure, pulse, respiration, temperature, oxygen saturation), all within normal limits."},
            {"id": "KID-VS-2", "kind": "document", "text": "For children with a stabilized history of Type 1 Diabetes, five stable blood sugar readings."},
            {"id": "KID-VS-3", "kind": "document", "text": "Weight history at hospital arrival and at discharge."}]},
        {"section": "ADLs (parent is responsible for ADLs)", "rules": [
            {"id": "KID-ADL-1", "kind": "must", "text": "The child completes all ADLs, including personal hygiene, bathing and toileting or brief changes, independently or with assistance from a legal guardian. Benches are available; a seated shower is acceptable."}]},
        {"section": "Mobility", "rules": [
            {"id": "KID-MOB-1", "kind": "document", "text": "PT and OT notes must be sent for review."},
            {"id": "KID-MOB-2", "kind": "must", "text": "If using DME (wheelchair, walker), the child uses it independently."},
            {"id": "KID-MOB-3", "kind": "must", "text": "Ambulates at least 100 feet (rest breaks acceptable) at modified independence if not wheelchair dependent."},
            {"id": "KID-MOB-4", "kind": "must", "text": "A wheelchair-dependent child transfers independently; any transfer assistance must be provided by a legal guardian."}]},
        {"section": "Mental health", "rules": [
            {"id": "KID-MH-1", "kind": "must", "text": "Mentally stable on medication, with no suicidal ideation or commanding auditory or visual hallucinations, and cleared by a psychiatrist."}]},
        {"section": "Cognition", "rules": [
            {"id": "KID-COG-1", "kind": "must", "text": "Understands information and medical education, or a legal guardian takes that responsibility."},
            {"id": "KID-COG-2", "kind": "must", "text": "Self-administers medications, or a legal guardian administers them. Staff only observe administration."}]},
        {"section": "End of life", "rules": [
            {"id": "KID-EOL-1", "kind": "conditional", "text": "Hospice arranged before admission; family informed that recuperative care staff cannot administer medications (hospice staff do)."}]},
        {"section": "Other factors", "rules": [
            {"id": "KID-OTH-1", "kind": "exclude", "text": "Ineligible if verbally or physically aggressive toward staff and parents are unable to manage outbursts."},
            {"id": "KID-OTH-2", "kind": "conditional", "text": "IV access accepted if home health is established to manage the IV and administer IV medications as needed."}]},
    ],
    "gaps": [
        {"ids": ["KID-DX-E13", "KID-DX-X23"], "note": "Oppositional defiant disorder appears on both the accepted and the ineligible list. Coordinator decides; never decide silently."},
    ],
}
# Rules whose exception depends on elapsed time (dates are redacted in packets)
for s in doc["sections"]:
    for r in s["rules"]:
        if r["id"] in ("KID-DX-X2", "KID-DX-X6"):
            r["needs_date"] = True
ids = [r["id"] for s in doc["sections"] for r in s["rules"]]
assert len(ids) == len(set(ids)), "duplicate IDs"
assert {"KID-DX-E13", "KID-DX-X23"} <= set(ids)
(HERE / "childrens-admission-criteria.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
print("children's rules:", len(ids))
