*******************************************************
* Table 1 demographics + three-reviewer merge and pairwise inter-rater
* agreement (GPT-4o and GPT-5 arms)
*
* Part 1 produces the patient-level demographic and note-count rows of
* Table 1 (age, sex, race, BMI, SIPAT, evaluation year, notes per patient).
* Part 2 merges three independent reviewers' validation labels for the
* GPT-5 arm and computes pairwise Cohen's kappa (reported in Results).
* Part 3 does the same for the GPT-4o arm.
*
* Set your own paths below before running -- these were originally
* absolute paths on the author's machine and institutional file share.
*******************************************************

*----------------------------
* Part 1: Table 1 demographics and note counts
*----------------------------
import delimited "data/Patient_notes_forstata.csv", varnames(1) clear

codebook id
tab assessment_type, m

bysort id: gen notes_per_patient = _N
collapse (first) notes_per_patient, by(id)
sum notes_per_patient
tab notes_per_patient, m

import delimited "data/Patient_notes_outcomes_forstata.csv", varnames(1) clear

drop assessment_type doctor

collapse (firstnm) female age bmi sipat year hispanic_latino african_american ///
    american_indian_alaska_native caucasian relapse ltfu, by(id)

tab year, m

tab1 female hispanic_latino african_american american_indian_alaska_native caucasian, m

sum age bmi sipat

*----------------------------
* Part 2: merge three reviewers' GPT-5 validation labels and
* compute pairwise inter-rater agreement
*----------------------------
* Reviewers 1 and 2 recorded agreement/disagreement with the LLM's call
* (1 = agree with LLM, 0 = disagree); reviewer 3 recorded a direct
* present/absent call (1 = present, 0 = absent) rather than agree/disagree,
* so the reference-label reconstruction differs for that column below.

import excel "data/validation_sample_gpt5_reviewer1.xlsx", sheet("validation_sample_gpt5") firstrow clear
rename human_label human_label_r1
tempfile reviewer1
save `reviewer1'

import excel "data/validation_sample_gpt5_reviewer2.xlsx", sheet("validation_sample_gpt5") firstrow clear
rename human_label human_label_r2
tempfile reviewer2
save `reviewer2'

import excel "data/validation_sample_gpt5_reviewer3.xlsx", sheet("validation_sample_gpt5") firstrow clear
rename human_label human_label_r3

merge 1:1 patient_id note_id assessment_type factor using `reviewer1', keepusing(human_label_r1)
drop _merge

merge 1:1 patient_id note_id assessment_type factor using `reviewer2', keepusing(human_label_r2)
drop _merge

* keep only if all three reviewers validated the pair
keep if !missing(human_label_r1) & !missing(human_label_r2) & !missing(human_label_r3)
count

* Reference label per reviewer
gen human_truth_1 = .
replace human_truth_1 = present if human_label_r1 == 1
replace human_truth_1 = 1 - present if human_label_r1 == 0

gen human_truth_2 = .
replace human_truth_2 = present if human_label_r2 == 1
replace human_truth_2 = 1 - present if human_label_r2 == 0

* Reviewer 3 recorded a direct present/absent call, not agree/disagree --
* no reconstruction through `present` needed.
gen human_truth_3 = human_label_r3

* Pairwise inter-rater agreement (Cohen's kappa), reported pairwise rather
* than as a single pooled three-rater statistic. 
kap human_truth_1 human_truth_2
kap human_truth_1 human_truth_3
kap human_truth_2 human_truth_3

*----------------------------
* Part 3: merge three reviewers' GPT-4o validation labels and
* compute pairwise inter-rater agreement
*----------------------------
* Same three reviewers, same reconstruction logic as Part 2: reviewers 1
* and 2 recorded agreement/disagreement with the LLM's call; reviewer 3
* recorded a direct present/absent call. 

import excel "data/validation_sample_gpt4o_reviewer1.xlsx", sheet("validation_sample_gpt4o") firstrow clear
rename human_label human_label_r1
tempfile reviewer1_gpt4o
save `reviewer1_gpt4o'

import excel "data/validation_sample_gpt4o_reviewer2.xlsx", sheet("validation_sample_gpt4o") firstrow clear
rename human_label human_label_r2
tempfile reviewer2_gpt4o
save `reviewer2_gpt4o'

import excel "data/validation_sample_gpt4o_reviewer3.xlsx", sheet("validation_sample_gpt4o") firstrow clear
rename human_label human_label_r3

merge 1:1 patient_id note_id assessment_type factor using `reviewer1_gpt4o', keepusing(human_label_r1)
drop _merge

merge 1:1 patient_id note_id assessment_type factor using `reviewer2_gpt4o', keepusing(human_label_r2)
drop _merge

* keep only if all three reviewers validated the pair
keep if !missing(human_label_r1) & !missing(human_label_r2) & !missing(human_label_r3)
count

* Reference label per reviewer
gen human_truth_1 = .
replace human_truth_1 = present if human_label_r1 == 1
replace human_truth_1 = 1 - present if human_label_r1 == 0

gen human_truth_2 = .
replace human_truth_2 = present if human_label_r2 == 1
replace human_truth_2 = 1 - present if human_label_r2 == 0

gen human_truth_3 = human_label_r3

* Pairwise inter-rater agreement (Cohen's kappa) 
kap human_truth_1 human_truth_2
kap human_truth_1 human_truth_3
kap human_truth_2 human_truth_3
