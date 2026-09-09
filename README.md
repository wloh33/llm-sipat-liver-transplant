# LLM-SIPAT: LLM-Assisted Extraction of Psychosocial Risk Factors

Code accompanying the manuscript *"Automating psychosocial screening in alcohol-associated liver disease with large language models"* (submitted to JAMIA Open). This repository contains the extraction pipeline, prompts, and domain taxonomy used to identify psychosocial risk factors from pre-transplant evaluation notes for patients with alcohol-associated liver disease (ALD), and to correlate extracted factors with SIPAT scores.

This repository contains **code only**. It does not contain patient notes, patient identifiers, or any protected health information (PHI). Data are not publicly available due to patient privacy protections.

## Study workflow

The pipeline ran in two phases, both executed against two LLM deployments (GPT-4o and GPT-5) accessed through a HIPAA-compliant institutional Azure OpenAI API.

- **Phase 1 — domain discovery** (`code/phase1_domain_discovery.py`): the LLM freely identifies psychosocial factors in each note and groups them into open-vocabulary domains. Output domains were reviewed and consolidated by clinicians into the ten-domain framework in `schema/domain_taxonomy.md`.
- **Phase 2 — canonical extraction** (`code/phase2_factor_extraction.py`): the LLM applies the clinician-refined domain/factor framework to every note, producing a presence/absence label, documentation status, evidence excerpt, and confidence score for each of the 55 canonical factors.
- **Note descriptives** (`code/table1_note_descriptives.py`): produces the note-count/note-length summary by note type reported in Table 1.

Both phases were run twice — once with `MODEL` set to the GPT-4o deployment, once to the GPT-5 deployment — using identical code and prompts.

Downstream analysis was done in Stata (version 18):

- **Table 1 demographics** (`code/stata/table1_demographics_and_interrater_agreement.do`, Part 1): patient-level demographics and note-count summary.
- **Validation performance metrics** (`code/stata/table2_and_table3a_validation_metrics.do`, Parts 1-2): sensitivity/specificity/PPV/NPV/F1/kappa, for Table 2 (GPT-5, Part 1) and Appendix Table 3a (GPT-4o, Part 2).
- **Three-reviewer merge and pairwise inter-rater agreement** (`code/stata/table1_demographics_and_interrater_agreement.do`, Parts 2-3): merges all three independent reviewers' validation labels and computes pairwise Cohen's kappa, for the GPT-5 arm (Part 2) and the GPT-4o arm (Part 3).
- **Figure 2** (`code/stata/figure2_domain_prevalence_sipat.do`): domain prevalence and Spearman correlation with total SIPAT score, from the published aggregate values.

## Repository structure

```
prompts/      De-identified system prompts used for each phase
schema/       The 10-domain, 55-factor taxonomy (Appendix Table 1a)
code/         Extraction and aggregation scripts (Python)
code/stata/   Downstream analysis and figure scripts (Stata)
```

## Requirements

**Python**: see `requirements.txt`. Requires an Azure OpenAI endpoint and deployment (institution-specific; not included). Copy `.env.example` to `.env` and fill in your own credentials — never commit `.env`.

**Stata**: version 18 or later. No user-written packages required. File paths at the top of each `.do` file are placeholders — set them to your own working directory before running.

## Reproducibility note

API calls in this pipeline do not pass an explicit `temperature` parameter, so each call ran at the Azure OpenAI API's default value of 1.0. No random seed is set for the extraction calls. Chat completion sampling is stochastic even at a fixed temperature, so re-running this code against a live model deployment will not reproduce the exact published numbers token-for-token — expected and typical for LLM-based extraction pipelines. The validation sampling steps do use a fixed `random_state`, so the *sampling* is reproducible even though the *extraction* is not.

## Citation

This code accompanies a manuscript currently under review at JAMIA Open. A full citation will be added here once the paper is published.

## License

MIT (see `LICENSE`).
