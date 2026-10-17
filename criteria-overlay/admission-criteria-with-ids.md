# IHH admission criteria with rule IDs (generated)

Generated from `admission-criteria.json` by `build_overlay.py`. Rule text is IHH's wording. Tags come from the local overlay, not from IHH: **[date]** = needs a date (redacted in packets, so usually "can't tell"), **[gap]** = the written rules leave this unclear. If this page and IHH staff disagree, IHH staff are right.

**Which wins:** When the referral form screen (FORM-*) and the admission criteria outline disagree, the outline wins: it is IHH's internal rulebook. Settled conflicts: FORM-X6 (sex offender) yields to OTH-2 (case by case); FORM-M6 and FORM-X3 (walk 100 ft) yield to MOB-3 and MOB-4 (wheelchair-dependent patients who transfer independently are eligible). Where the outline is silent (tuberculosis, refusing detox), the form's exclusion applies.

## General admission criteria (any one)

- **GEN-1** Homeless/at risk of homelessness and too ill or frail to recover from illness or injury `any_of`
- **GEN-2** Lives alone with no formal supports and too ill or frail to recover from illness or injury `any_of`
- **GEN-3** At risk of hospitalization or re-hospitalization after hospitalization `any_of`

## ADLs

- **ADL-1** Able to complete all Activities of Daily Living (ADLs) independently including personal hygiene `must`
- **ADL-2** Patient must be able to complete personal hygiene independently. Benches are available for bathing so seated shower is acceptable. Patient must be able to gather all of their own bathing/showering supplies, transfer to shower area and perform shower/bath independently `must`
- **ADL-3** Able to toilet independently and/or change briefs/diapers independently `must`

## Mobility

- **MOB-1** If using DME (wheelchair, walker, etc) must be able to use independently `must`
- **MOB-2** PT/OT notes must be sent for review `document`
- **MOB-3** Patient must be able to ambulate at least 100 ft (rest breaks are acceptable) at modified independence if not wheelchair dependent `must` **[gap]**
  - Gap: Settled: wheelchair-dependent patients who transfer and use the chair independently are eligible.
- **MOB-4** Wheelchair dependent patients must be able to transfer independently `must` **[gap]**
  - Gap: Settled: see MOB-3.

## Mental Health

- **MH-1** Patient must be mentally stable on medications `must`
- **MH-2** No suicidal ideation `exclude`
- **MH-3** No commanding auditory or visual hallucinations `exclude`
- **MH-4** If a patient was admitted with acute alcohol intoxication, the patient must be held for at least 72 hours and not have signs of alcohol withdrawal (maintain a CIWA-AR score of <8, if being assessed with this tool) prior to admission to recuperative care. `must` **[date]**
- **MH-5** Cannot qualify, have history of or currently be under a conservatorship or FSP `exclude` **[gap]**
  - Gap: 'FSP' is not spelled out; likely Full Service Partnership, a county mental-health program.

## Cognition

- **COG-1** Must be capable of self-administering medications (must confirm that patient can self-administer insulin) and receiving medical education `must`
- **COG-2** AOx4 `must`

## Other Factors

- **OTH-1** Ineligible if client is verbally or physically aggressive towards staff or other patients `exclude`
- **OTH-2** Patients that are registered sex offenders will be evaluated on a case-by-case basis (however, as a general guide, any offense that involves violence will likely be denied `note` **[gap]**
  - Gap: Settled: case by case; offenses involving violence likely denied. Flag for the coordinator; never auto-deny.
- **OTH-3** Patients with IV access can be accepted if they have home health established to maintain the IV and administer the medication as needed. There is no limit on time for IV `conditional` **[gap]**
  - Gap: Home health threshold wording varies across rules: established, ordered, coordinated, coordinated and scheduled.
- **OTH-4** Cannot accept patients on isolation unless isolation status is cleared prior to admission to recuperative care `exclude`

## End of life care

- **EOL-1** Hospice patients are eligible for recuperative care admission. Hospice services must be arranged prior to admission to recuperative care and patient, family and other involved parties must be made aware that recuperative care staff cannot administer medications, these medications will be administered by hospice staff `conditional`

## Infection Control

- **INF-1** MRSA swab, documented negative prior to recuperative care admission if coming from inpatient hospitalization `document`
- **INF-2** Covid swab (rapid swab acceptable) documented negative within 24 hours of recuperative care admission if coming from inpatient admission `document` **[date]** **[gap]**
  - Gap: A swab negative when the referral is sent can be more than 24 hours old by arrival.

## Diabetes

- **DM-1** If patient is being referred from inpatient hospitalization, 5 consecutive glucose readings should be sent. Readings must be show improvement and stabilization. `document`
- **DM-2** If admitted from the emergency department, it must be established and documented that the patient is not in DKA. `must` **[gap]**
  - Gap: Related to END-X3: resolved DKA not addressed.
- **DM-3** We will not accept a diabetic patient that was started on an insulin regimen less than 24 hours prior to admission. `exclude` **[date]** **[gap]**
  - Gap: Does not say whether the 24 hours start at the first dose or when doses stop changing.
- **DM-4** Poorly controlled diabetics on an oral medication or established insulin regimen may be accepted from the ED if they have follow up with a primary care provider scheduled within the next 5-7 days, have not had an episode of hypoglycemia within the last week and have a written treatment plan for glucose control (i.e. sliding scale parameters, medication hold guidelines, etc). `conditional` **[date]**
- **DM-5** Patient should understand how to use glucometer `must`
- **DM-6** Patient should understand insulin administration, if applicable `must`
- **DM-Q1** Does the patient use insulin? Is the insulin administered through a pump? `ask`
- **DM-Q2** Does the patient take oral medication? `ask`
- **DM-Q3** What was the patient's last hemoglobin A1C? This is not a limiting factor for admission but does provide important information about the patient's baseline glucose level `ask` **[gap]**
  - Gap: The A1C sentence is cut off in the source.

## Infection

- **ID-1** The last 5 sets of vital signs should be sent. Patient is ineligible for recuperative care if VS show signs of sepsis (continued fever, elevated heart rate, low blood pressure) `document`
- **ID-2** The patient should be able to administer oral antibiotics independently `must`
- **ID-3** If IV antibiotics are required, home health care should be ordered before admission to recuperative care to maintain IV and administer antibiotics `conditional` **[gap]**
  - Gap: Home health wording varies (see OTH-3).
- **ID-Q1** Location of infection? `ask`
- **ID-Q2** Were cultures performed? Results should be sent `ask`
- **ID-Q3** Is the patient on isolation? `ask`

## Respiratory Illness

- **RESP-1** Chest imaging should be sent (Chest XR, CT, MRI) when available `document`
- **RESP-2** The last 5 sets of vital signs should be sent, if available; O2 saturation may be chronically low if patient has a history of COPD, readings should be stable and consistent with patient's normal O2 saturation `document`
- **RESP-3** If O2 is required, the hospital must order it and have the tank ready to be sent to the site the day before the client arrives at the recuperative care site `conditional` **[date]**
- **RESP-4** Respiratory therapy notes should be sent `document`
- **RESP-Q1** Is the patient receiving any breathing treatments? If so, what are they? `ask`
- **RESP-Q2** Is the patient on antibiotics for this condition? `ask`

## Cardiac

- **CARD-1** The last 5 sets of vital signs should be sent. Patient's BP should be stable on oral medication for at least 24 hours `document` **[date]**
- **CARD-2** If patient had a troponin in the hospital, at least 3 consecutive results should be sent with at least 2 negative results `document` **[gap]**
  - Gap: Asks for two negative troponins, but a patient admitted for a heart attack won't have them, while history of heart attack (CIR-E7) is eligible.
- **CARD-3** EKG results should be sent `document`
- **CARD-4** If patient has a history of atrial fibrillation or has been diagnosed with atrial fibrillation, patient should be able to take anticoagulation therapy independently and understand any associated lab work (i.e. INR) necessary to track this medication `must`
- **CARD-5** Ejection Fraction of 25% or higher may be accepted as long as this has been established to be the patient's baseline. If the patient is on chemotherapy or is being immediately discharged from hospitalization for heart attack with a lowered ejection fraction, this patient is ineligible for recuperative care `exclude`
- **CARD-6** Patient will not be accepted for admission to recuperative care if IV blood pressure medications have been required within 24 hours `exclude` **[date]**

## Integumentary: eligible

- **INT-E1** Uncomplicated infections of the skin, cellulitis or abscess, requiring oral antibiotic treatments `eligible_condition`
- **INT-E2** Wound care to be coordinated with home health agency prior to arrival at recuperative care and should coincide with the frequency of dressing changes or wound monitoring. If a patient should have a dressing change or wound check within 24 hours of discharge from the hospital, wound care should be arranged to arrive to recuperative care within 24 hours. Additionally, all wounds in hard-to-reach areas (coccyx, back of thighs, back, perineum) will require at least one visit from wound care in the recuperative care setting regardless of patient's ability to change the dressing in a hospital setting. `conditional` **[date]** **[gap]**
  - Gap: Hard-to-reach list reads 'coccyx, , back of thighs, back, perineum': an item seems missing and the sacrum is not named. Home health wording here is 'coordinated' (see OTH-3).
- **INT-E3** IV antibiotics are allowed as long as home health has been coordinated to maintain the IV and either patient is able to administer their own IV antibiotics or home health will be administering the antibiotic `conditional` **[gap]**
  - Gap: Home health wording varies (see OTH-3).
- **INT-E4** Uncomplicated wounds (e.g. laceration without infection) `eligible_condition`
- **INT-E5** Post-surgical incision. If staples or external sutures are placed, appropriate follow up should be scheduled for removal prior to admission to recuperative care `conditional`
- **INT-E6** Stage 1, 2, 3 pressure ulcers. Wound care to be coordinated and scheduled prior to admission to recuperative care `conditional` **[gap]**
  - Gap: Home health wording varies: here wound care must be 'coordinated and scheduled' (see OTH-3).
- **INT-E7** Third degree burns that affect <15% of the body. Wound care to be coordinated with home health agency prior to admission to recuperative care `conditional` **[gap]**
  - Gap: Home health wording varies (see OTH-3).

## Integumentary: ineligible

- **INT-X1** Complicated wounds requiring skin grafting `exclude`
- **INT-X2** Complicated large abscess `exclude` **[gap]**
  - Gap: 'Complicated large abscess' is not defined.
- **INT-X3** Burns associated with inhalation injury `exclude`

## Ophthalmology: eligible

- **OPH-E1** Uncomplicated infections of the eye `eligible_condition`
- **OPH-E2** Post-op glaucoma surgery `eligible_condition`
- **OPH-E3** Cataract surgery requiring extraction with lens implant (uncomplicated situation) `eligible_condition`
- **OPH-E4** Diabetic retinopathy `eligible_condition`
- **OPH-E5** Diabetic macular edema `eligible_condition`
- **OPH-E6** Post operative admission for vitreous hemorrhage, if patient meets all other criteria `eligible_condition`
- **OPH-E7** Post operative admission for retinal detachment, if patient meets all other criteria `eligible_condition`

## Respiratory: eligible

- **RSP-E1** Pneumonia `eligible_condition`
- **RSP-E2** Bronchitis `eligible_condition`
- **RSP-E3** COPD not requiring continuous oxygen therapy `eligible_condition`
- **RSP-E4** Asthma `eligible_condition`
- **RSP-E5** Patients with O2 baseline of 94% or greater with physician explanation `eligible_condition` **[gap]**
  - Gap: 'O2 baseline of 94% or greater with physician explanation': meaning in practice not stated.
- **RSP-E6** Patients with mature tracheostomy who are able to independently care for their tracheostomy site and are also able to eat and use a speaking valve `eligible_condition`
- **RSP-E7** CPAP `eligible_condition`

## Respiratory: ineligible

- **RSP-X1** Pneumothorax `exclude`
- **RSP-X2** Hemothorax `exclude`
- **RSP-X3** Trach patients with ventilator `exclude`
- **RSP-X4** Pulmonary Embolism `exclude`
- **RSP-X5** Respiratory conditions requiring BiPAP `exclude`

## Musculoskeletal: eligible

- **MSK-E1** Closed fractures `eligible_condition`
- **MSK-E2** PT to be coordinated and scheduled prior to arrival at recuperative care `conditional`
- **MSK-E3** Rheumatoid arthritis `eligible_condition`
- **MSK-E4** Non-elective hip/knee replacements following SNF placement, if patient meets the other recuperative care guidelines `eligible_condition`

## Musculoskeletal: ineligible

- **MSK-X1** Open fractures `exclude`
- **MSK-X2** Osteomyelitis `exclude`
- **MSK-X3** External fixation devices `exclude`
- **MSK-X4** Immediately following hospitalization for amputation with wounds `exclude`
- **MSK-X5** Facial trauma with mandibular or maxillary fracture requiring jaw wiring `exclude`

## GI: eligible

- **GI-E1** Post abdominal surgical care `eligible_condition`
- **GI-E2** Uncomplicated inguinal or umbilical hernia `eligible_condition`
- **GI-E3** Diverticulitis `eligible_condition`
- **GI-E4** Uncomplicated inflammatory bowel disease `eligible_condition`
- **GI-E5** Ascites, if chronic `eligible_condition`
- **GI-E6** Gastroesophageal reflux disorder `eligible_condition`
- **GI-E7** Post hospitalization for uncomplicated bowel obstruction that did not require surgical intervention `eligible_condition`

## GI: ineligible

- **GI-X1** Decompensated cirrhosis (defined by the development of clinically evident complications of portal hypertension, ascites, variceal hemorrhage, hepatic encephalopathy or liver insufficiency, jaundice) `exclude`
- **GI-X2** Immediately following hospitalization for bleeding ulcer disease or esophageal varices `exclude`
- **GI-X3** C.Diff `exclude` **[gap]**
  - Gap: C. diff is ineligible; the outline does not say whether that ends when isolation lifts or when treatment finishes. The form (FORM-X4) excludes it only until cleared by a doctor or CID. Show both to the coordinator.

## Endocrine: eligible

- **END-E1** Diabetes that shows improvement and stabilization in glucose levels as seen on at least 5 consecutive glucose readings with medical treatment (see the diabetes rules) `eligible_condition`
- **END-E2** Hypothyroidism or hyperthyroidism on medical treatment `eligible_condition`
- **END-E3** s/p thyroidectomy `eligible_condition`

## Endocrine: ineligible

- **END-X1** Immediately s/p parathyroidectomy `exclude`
- **END-X2** Alcoholic ketoacidosis `exclude`
- **END-X3** DKA `exclude` **[gap]**
  - Gap: DKA is ineligible; does not say whether resolved DKA still excludes.

## GU: eligible

- **GU-E1** Urinary tract infection `eligible_condition`
- **GU-E2** Post-acute glomerulonephritis, if caused by an infection `eligible_condition`
- **GU-E3** Post-op laparoscopic gynecologic surgery for treatment of non-cancerous conditions `eligible_condition`
- **GU-E4** Urolithiasis `eligible_condition`
- **GU-E5** Patients requiring catheterization if confirmation is provided that patient is able to self-catheterize `conditional`
- **GU-E6** Indwelling catheter if patient is able to empty on their own and follow up has been scheduled for removal `conditional`
- **GU-E7** Patients requiring dialysis if dialysis schedule and frequency has been established `conditional`

## GU: ineligible

- **GU-X1** Patients requiring intermittent catheterization that has to be performed by medical staff `exclude`

## Circulatory System: eligible

- **CIR-E1** Post-op angiogram `eligible_condition`
- **CIR-E2** Cardiac catheterization/stent placement `eligible_condition`
- **CIR-E3** Pacemaker/ICD insertion `eligible_condition`
- **CIR-E4** Stable hypertension (patient with baseline elevated BP; SBP<170, DBP<100, asymptomatic and not currently taking medication but with established follow up with a primary care provider) `eligible_condition`
- **CIR-E5** Post coronary artery bypass graft or heart valve surgery with controlled, stable blood pressure, normal hemoglobin/hematocrit, normal EF and without arrhythmias. Home health must be ordered and scheduled prior to admission to recuperative care. Cardiac surgery follow up must be scheduled prior to admission to recuperative care. `conditional` **[gap]**
  - Gap: Home health wording varies (see OTH-3).
- **CIR-E6** Hypertension that responds well to oral anti-hypertensive regimen `eligible_condition`
- **CIR-E7** History of heart attack. If being admitted to recuperative care immediately following admission for heart attack, will only accept patients who have an normal ejection fraction `eligible_condition` **[gap]**
  - Gap: See CARD-2: troponin rule conflicts for patients admitted for a heart attack.

## Circulatory System: ineligible

- **CIR-X1** Unstable cardiac arrhythmias `exclude`
- **CIR-X2** Hypertension that requires IV medications to improve, is symptomatic or is not responding to oral medication `exclude`

## Neurology: eligible

- **NEU-E1** Alcohol withdrawal seizure, following detox/stabilization `eligible_condition`
- **NEU-E2** Post carpal tunnel or cubital release `eligible_condition`
- **NEU-E3** Mild traumatic brain injury with intact ADLs `eligible_condition`
- **NEU-E4** Cervical or lumbar radiculopathy following epidural injection or decompression surgery `eligible_condition`

## Neurology: ineligible

- **NEU-X1** Stroke syndrome with neurological residual/deficit (e.g. ambulatory difficulty, seizure) `exclude`
- **NEU-X2** New onset of seizure with neurological deficit/impairment `exclude`
- **NEU-X3** Moderate or severe traumatic brain injury `exclude`
- **NEU-X4** Cervical or lumbar fusion `exclude`
- **NEU-X5** Dementia `exclude`
- **NEU-X6** Immediately s/p neurosurgery. Neurosurgical patients who meet other eligibility criteria should be escalated to further clinical review `exclude`

## Referral checklist

- **DOC-1** Illumination Health + Home Referral Form `document`
- **DOC-2** Client's Demographic Page `document`
- **DOC-3** CalOptima Form/LOA/AUTH `document`
- **DOC-4** H&P (History and Physical) `document`
- **DOC-5** Current Progress Notes (if needed) `document`
- **DOC-6** Updated Vitals (last 24 hours) `document` **[date]**
- **DOC-7** Medication List `document`
- **DOC-8** PT/OT or Nursing Notes `document`
- **DOC-9** Blood or Wound Culture (if needed) `document`
- **DOC-10** 30-day supply of all medications `document`

## Referral form: must meet all

- **FORM-M1** Currently unhoused, at risk of being unhoused, or are living in an inadequate environment post hospitalization `must`
- **FORM-M2** Medically and psychiatrically stable condition upon discharge `must`
- **FORM-M3** The patient is AAOx4 (alert and oriented) `must`
- **FORM-M4** Able to manage ADL (activities of daily living) `must`
- **FORM-M5** Able to self-administer medications and manage their medication schedule with staff oversight `must`
- **FORM-M6** Capable of walking 100 ft. with or without DME and able to transfer independently `must` **[gap]**
  - Gap: Superseded by MOB-3 and MOB-4.

## Referral form: not eligible if

- **FORM-X1** Cognitively impaired (i.e., dementia, Alzheimer's) `exclude`
- **FORM-X2** Unable to perform activities of daily living `exclude`
- **FORM-X3** Unable to transfer, ambulate 100 ft., or use DME independently `exclude` **[gap]**
  - Gap: Superseded by MOB-3 and MOB-4.
- **FORM-X4** Active infection has not been cleared by a doctor or CID: MRSA, Tuberculosis, C-DIFF `exclude` **[gap]**
  - Gap: Only the tuberculosis part falls to the form (the outline is silent on TB). MRSA is covered by INF-1 and C. diff by GI-X3, so the outline governs those.
- **FORM-X5** Non-compliance with detox treatment or a refusal to abstain from substance abuse `exclude` **[gap]**
  - Gap: Refusing detox is listed only on the form; the outline is silent, so the form's exclusion applies.
- **FORM-X6** Registered sex offender `exclude` **[gap]**
  - Gap: Superseded by OTH-2 (case by case).
- **FORM-X7** Aggressive or combative behavior directed at staff or other patients `exclude`

## Notes

- Outcomes are approve or deny; there is no stated 're-refer when ready' for a patient who will qualify in a day or two.
- When the referral form (FORM-*) and the outline disagree, the outline wins. Where the outline is silent, the form's exclusion applies.
- Dates are redacted in the packets: rules with needs_date=true should return 'can't tell' unless the packet states the timing without a date.
- Ophthalmology has no ineligible conditions listed in the source. Treat that as 'none listed', not 'nothing excludes'.
