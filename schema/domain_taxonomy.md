# Psychosocial Domain / Factor Taxonomy

Ten domains and 55 canonical factors used in Phase 2 extraction, matching Appendix Table 1a of the manuscript. Domains emerged from Phase 1 open-vocabulary extraction and were reviewed and refined by clinicians (see `README.md`).

## Alcohol use and relapse risk
- aud_severity_mild, aud_severity_moderate, aud_severity_severe *(mutually exclusive — see note below)*
- relapse_risk
- rehab_attempts
- abstinence_under_180_days *(mutually exclusive with abstinence_over_6_months)*
- abstinence_over_6_months
- cravings
- triggers

## Social support and caregiver readiness
- family_support
- caregiver_availability
- caregiver_understanding_and_preparedness
- living_arrangement_stability

## Polysubstance and other substance usage
- tobacco_use, cannabis_use, opioids_use, cocaine_use, benzodiazepine_use, stimulant_use, polysubstance_use_history, prescription_misuse

## Psychiatric stability and mental health
- major_depressive_disorder, anxiety_disorder, ptsd, adhd, clinically_significant_insomnia, suicidal_ideation_behavior, psychiatric_hospitalization_history, therapy_counseling_engagement

## Treatment adherence and transplant motivation
- motivation_for_transplant
- appointment_medication_adherence
- health_literacy
- engagement_in_transplant_education
- illness_awareness_treatment_insight

## Cognitive and functional status
- encephalopathy
- delirium
- cognitive_functional_capacity
- adl_independence

## Financial and socioeconomic stability
- employment_status
- income_financial_capacity
- insurance_literacy
- financial_stressors
- physical_disability_status
- housing_stability
- transportation_access

## Psychosocial environment and life stressors
- social_isolation, family_conflict, occupational_stress, psychological_trauma_history, maladaptive_coping_behaviors

## Spirituality and coping
- religious_identity
- faith_based_coping
- meaning_making_presence
- value_based_motivation

## Safety and legal context
- abuse_violence_risk
- legal_issues
- safety_planning_commitment
- firearms_access_home

## Mutually exclusive factor groups

Only one factor per group may be labeled present for a given note:
- `aud_severity_mild`, `aud_severity_moderate`, `aud_severity_severe`
- `abstinence_under_180_days`, `abstinence_over_6_months`

See `code/phase2_factor_extraction.py` for how mutual exclusivity is enforced (highest-confidence label wins).
