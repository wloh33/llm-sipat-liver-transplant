"""
Phase 1: open-vocabulary domain discovery.

Lets the LLM freely identify psychosocial factors and group them into
domains it names itself, for each note. Raw domains are then consolidated
by fuzzy string matching as a first pass; the consolidated list was
subsequently reviewed and refined by clinicians into the final 10-domain,
55-factor taxonomy in schema/domain_taxonomy.md, which Phase 2 applies.

Expects an input CSV with columns: id, description, assessment_type
(patient id, note text, and note type respectively). Set DATA_DIR to the
folder containing that file.
"""
import os
import re
import json
import time
from pathlib import Path
from difflib import SequenceMatcher
from typing import Dict, List, Optional

import pandas as pd
from openai import AzureOpenAI
from dotenv import load_dotenv

# -----------------------------
# Setup & config
# -----------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
OUTDIR = Path(os.environ.get("OUTPUT_DIR", "./output"))
INPUT_FILE = DATA_DIR / "Patient_notes.csv"
OUTDIR.mkdir(parents=True, exist_ok=True)

load_dotenv()

client = AzureOpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    api_version=os.environ["API_VERSION"],
    azure_endpoint=os.environ["OPENAI_API_BASE"],
    organization=os.environ.get("OPENAI_ORGANIZATION"),
)
MODEL = os.environ["MODEL"]

NOTE_LEVEL_OUTPUT = OUTDIR / f"phase1_domains_note_level_{MODEL}.csv"
PATIENT_LEVEL_OUTPUT = OUTDIR / f"phase1_domains_patient_level_{MODEL}.csv"
VALIDATION_OUTPUT = OUTDIR / f"phase1_validation_sample_{MODEL}.csv"

VALIDATION_SAMPLE_PERCENTAGE = 0.10
VALIDATION_MIN_SAMPLE_SIZE = 100
VALIDATION_MAX_SAMPLE_SIZE = 300
RANDOM_SEED = 42

# -----------------------------
# Data loading
# -----------------------------
notes_df = pd.read_csv(INPUT_FILE)
notes_df = notes_df.rename(columns={"id": "patient_id", "description": "note_text"})
notes_df["note_id"] = notes_df.groupby("patient_id").cumcount() + 1
notes_df = notes_df[["patient_id", "note_id", "assessment_type", "note_text"]]
print(f"Loaded {len(notes_df)} notes from {notes_df['patient_id'].nunique()} patients")


def clean_text(text: str) -> str:
    """Clean text by removing extra spacing, weird symbols, and normalizing whitespace."""
    if not text or pd.isna(text):
        return ""
    text = str(text)
    encoding_fixes = {
        "â€™": "'", "â€œ": '"', "â€": '"',
        "â€”": "-", "â€¢": "•", "Â": "",
        "‚Äù": '"', "‚Äü": '"', "‚Äô": "'",
        "‚Ä¦": "...",
    }
    for bad, good in encoding_fixes.items():
        text = text.replace(bad, good)
    text = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]", "", text)
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("`", "'")
    text = text.replace("—", "-").replace("–", "-")
    text = text.replace("…", "...")
    text = re.sub(r"[\t\r\f\v]", " ", text)
    text = re.sub(r" +", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[^\w\s.,;:!?()\[\]{}\-'/\"@#$%&*+=<>|\\~`\n°•]", "", text, flags=re.UNICODE)
    return text.strip()


notes_df["note_text"] = notes_df["note_text"].apply(clean_text)

# -----------------------------
# Prompt
# -----------------------------
SYSTEM_PROMPT = (REPO_ROOT / "prompts" / "phase1_domain_discovery_system_prompt.txt").read_text()

USER_PROMPT_TEMPLATE = """Extract generic psychosocial factors, classify them into mid-level domains, and return JSON using the schema.

Metadata:
patient_id={patient_id}
note_date=null

Note:
\"\"\"{note_text}\"\"\""""


def clean_domain_name(text: str, max_length: int = 32) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:max_length]


def parse_json_response(response_text: str) -> Optional[Dict]:
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    try:
        start = response_text.find("{")
        end = response_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(response_text[start:end + 1])
    except json.JSONDecodeError:
        pass
    return None


def call_openai_with_retry(system_prompt: str, user_prompt: str, max_retries: int = 4) -> Dict:
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content
            parsed_data = parse_json_response(content)
            if parsed_data is None:
                raise ValueError("Model returned invalid JSON")
            return parsed_data
        except Exception as error:
            wait_time = (2 ** attempt) + (0.1 * attempt)
            print(f"Attempt {attempt + 1} failed. Waiting {wait_time:.1f}s... Error: {error}")
            time.sleep(wait_time)
    print("[WARNING] All retries failed. Returning empty result.")
    return {"patient_id": None, "note_date": None, "domains": []}


def extract_factors_from_response(patient_id: str, note_id: int, api_response: Dict) -> List[Dict]:
    rows = []
    for domain_data in api_response.get("domains", []):
        clean_domain = clean_domain_name(domain_data.get("domain", ""))
        if not clean_domain:
            continue
        for factor_data in domain_data.get("factors", []):
            valence = str(factor_data.get("valence", "")).lower().strip()
            factor = clean_text(str(factor_data.get("factor", "")).strip())
            evidence = clean_text(str(factor_data.get("evidence", "")).strip())
            try:
                severity = int(factor_data.get("severity"))
                if severity not in (1, 2, 3):
                    continue
            except (ValueError, TypeError):
                continue
            try:
                certainty = float(factor_data.get("certainty"))
                if not (0 <= certainty <= 1):
                    continue
            except (ValueError, TypeError):
                continue
            if valence in ("risk", "protective") and factor and evidence:
                rows.append({
                    "patient_id": patient_id, "note_id": note_id, "domain": clean_domain,
                    "valence": valence, "factor": factor, "severity": severity,
                    "evidence": evidence, "certainty": certainty,
                })
    return rows


def consolidate_domains(df: pd.DataFrame, similarity_threshold: float = 0.7):
    """First-pass automated consolidation of raw LLM-generated domain names.
    This is a starting point, not the final taxonomy -- clinicians reviewed
    and further refined the output into the 10 domains in schema/domain_taxonomy.md."""
    def similarity(a, b):
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    unique_domains = df["domain"].unique()
    domain_mapping = {}
    consolidated_domains = []
    for domain in unique_domains:
        matched = False
        for consolidated in consolidated_domains:
            if similarity(domain, consolidated) >= similarity_threshold:
                domain_mapping[domain] = consolidated
                matched = True
                break
        if not matched:
            consolidated_domains.append(domain)
            domain_mapping[domain] = domain

    df = df.copy()
    df["domain_original"] = df["domain"]
    df["domain"] = df["domain"].map(domain_mapping)
    return df, domain_mapping


if __name__ == "__main__":
    print("\nProcessing notes with OpenAI...")
    all_extracted_factors = []

    for index, row in notes_df.iterrows():
        note_text = str(row["note_text"] or "").strip()
        if not note_text:
            continue
        user_prompt = USER_PROMPT_TEMPLATE.format(patient_id=row["patient_id"], note_text=note_text)
        api_response = call_openai_with_retry(SYSTEM_PROMPT, user_prompt)
        if not api_response.get("patient_id"):
            api_response["patient_id"] = row["patient_id"]
        factors = extract_factors_from_response(row["patient_id"], row["note_id"], api_response)
        for factor in factors:
            factor["assessment_type"] = row["assessment_type"]
        all_extracted_factors.extend(factors)
        if (index + 1) % 25 == 0:
            print(f"  Processed {index + 1}/{len(notes_df)} notes...")

    note_level_df = pd.DataFrame(all_extracted_factors, columns=[
        "patient_id", "note_id", "assessment_type", "domain", "valence", "factor",
        "severity", "evidence", "certainty",
    ])
    note_level_df.to_csv(NOTE_LEVEL_OUTPUT, index=False)
    print(f"Saved note-level data: {NOTE_LEVEL_OUTPUT}  (total factors: {len(note_level_df)})")

    # Consolidate raw open-vocabulary domains (first automated pass)
    note_level_df, domain_mapping = consolidate_domains(note_level_df, similarity_threshold=0.7)
    print(f"Consolidated {len(set(domain_mapping.values()))} domains from "
          f"{len(domain_mapping)} raw domain names (further refined by clinicians afterward).")

    # Patient-level aggregation (counts and severity sums per valence x domain)
    if not note_level_df.empty:
        note_level_df["count"] = 1
        factor_counts = note_level_df.pivot_table(
            index="patient_id", columns=["valence", "domain"], values="count",
            aggfunc="sum", fill_value=0,
        ).sort_index(axis=1)
        severity_sums = note_level_df.pivot_table(
            index="patient_id", columns=["valence", "domain"], values="severity",
            aggfunc="sum", fill_value=0,
        ).sort_index(axis=1)

        patient_level_df = pd.DataFrame(index=factor_counts.index).reset_index()
        for (valence, domain) in factor_counts.columns:
            patient_level_df[f"{valence}_count_{domain}"] = factor_counts[(valence, domain)].values
            patient_level_df[f"{valence}_sevsum_{domain}"] = severity_sums[(valence, domain)].values
        patient_level_df.to_csv(PATIENT_LEVEL_OUTPUT, index=False)
        print(f"Saved patient-level data: {PATIENT_LEVEL_OUTPUT}  (patients: {len(patient_level_df)})")

    # Stratified validation sample (by assessment type, domain, and valence)
    sample_size = int(len(note_level_df) * VALIDATION_SAMPLE_PERCENTAGE)
    sample_size = max(VALIDATION_MIN_SAMPLE_SIZE, sample_size)
    sample_size = min(VALIDATION_MAX_SAMPLE_SIZE, sample_size, len(note_level_df))

    try:
        validation_sample = note_level_df.groupby(
            ["assessment_type", "domain", "valence"], group_keys=False
        ).apply(
            lambda x: x.sample(n=max(1, int(len(x) / len(note_level_df) * sample_size)), random_state=RANDOM_SEED)
        ).reset_index(drop=True)

        if len(validation_sample) > sample_size:
            validation_sample = validation_sample.sample(n=sample_size, random_state=RANDOM_SEED)
        elif len(validation_sample) < sample_size:
            remaining = sample_size - len(validation_sample)
            additional = note_level_df[~note_level_df.index.isin(validation_sample.index)].sample(
                n=min(remaining, len(note_level_df) - len(validation_sample)), random_state=RANDOM_SEED
            )
            validation_sample = pd.concat([validation_sample, additional])
    except Exception as e:
        print(f"Stratified sampling failed ({e}), using simple random sampling")
        validation_sample = note_level_df.sample(n=sample_size, random_state=RANDOM_SEED)

    validation_sample = validation_sample.merge(
        notes_df[["patient_id", "note_id", "note_text"]], on=["patient_id", "note_id"], how="left"
    )
    validation_sample["validation_result"] = ""
    validation_sample["validation_notes"] = ""
    validation_sample["validated_by"] = ""
    validation_sample["validation_date"] = ""
    validation_sample = validation_sample.sort_values(
        ["assessment_type", "domain", "valence", "patient_id", "note_id"]
    ).reset_index(drop=True)

    validation_sample.to_csv(VALIDATION_OUTPUT, index=False)
    print(f"Saved validation sample: {VALIDATION_OUTPUT}  ({len(validation_sample)} rows)")
