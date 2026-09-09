*******************************************************
* LLM vs Human validation metrics (note level)
* - Computes confusion matrices per factor and overall
* - Metrics: %agreement, Cohen's kappa, precision, recall, F1
* - Part 1 produces Table 2 (GPT-5). Part 2 produces Appendix Table 3a
*   (GPT-4o). Both run the identical calc_metrics program below against
*   each model's own reviewed validation sample -- same code, same logic,
*   just pointed at different input files, mirroring how the extraction
*   pipeline itself was run once per model.
*
* Set your own working directory below before running. Each part expects
* a reviewed validation sample (the CSV produced by
* code/phase2_factor_extraction.py, after human reviewers filled in
* human_label and a model_pred column has been added) exported to Excel.
*******************************************************
clear all
* cd "<path to your working directory>"

*----------------------------
* 0) Shared metrics program (used by both Part 1 and Part 2)
*----------------------------
program define calc_metrics, rclass
    args pred actual

    * Basic counts
    count if `pred'==1 & `actual'==1
    local tp = r(N)
    count if `pred'==1 & `actual'==0
    local fp = r(N)
    count if `pred'==0 & `actual'==1
    local fn = r(N)
    count if `pred'==0 & `actual'==0
    local tn = r(N)
    local n = `tp' + `fp' + `fn' + `tn'

    * Label counts
    count if `pred'==1
    local llm_pos = r(N)
    count if `actual'==1
    local human_pos = r(N)

    * Core metrics
    local acc = (`tp' + `tn')/`n'
    local prec = cond(`tp'+`fp'>0, `tp'/(`tp'+`fp'), .)
    local rec = cond(`tp'+`fn'>0, `tp'/(`tp'+`fn'), .)
    local f1 = cond(!missing(`prec') & !missing(`rec') & `prec'+`rec'>0, 2*`prec'*`rec'/(`prec'+`rec'), .)

    * Kappa (LLM prediction vs. reconstructed human reference)
    local po = `acc'
    local pe = ((`tp'+`fp')/`n')*((`tp'+`fn')/`n') + ((`fn'+`tn')/`n')*((`fp'+`tn')/`n')
    local kap = cond(1-`pe'>0, (`po'-`pe')/(1-`pe'), .)

    * Return results
    return scalar N = `n'
    return scalar LLM_pos = `llm_pos'
    return scalar Human_pos = `human_pos'
    return scalar TP = `tp'
    return scalar FP = `fp'
    return scalar FN = `fn'
    return scalar TN = `tn'
    return scalar accuracy = `acc'
    return scalar precision = `prec'
    return scalar recall = `rec'
    return scalar f1 = `f1'
    return scalar kappa = `kap'
end

*----------------------------
* Part 1: Table 2 -- GPT-5
*----------------------------
import excel "output/validation_sample_gpt5_reviewed.xlsx", sheet("validation_sample") firstrow clear

* Create human coding variable.
* Reviewers recorded simple agreement/disagreement with each LLM call
* (human_label: 1 = agree, 0 = disagree) after independently checking the
* source note. The true reference label is reconstructed by keeping the
* model's prediction when the reviewer agreed, and flipping it when they
* disagreed.
gen byte human = .
replace human = model_pred if human_label==1 & !missing(model_pred)
replace human = 1-model_pred if human_label==0 & !missing(model_pred)

tempname results_gpt5
postfile `results_gpt5' str40 factor N LLM_pos Human_pos TP FP FN TN accuracy precision recall f1 kappa using results_gpt5, replace

* Overall metrics
preserve
calc_metrics model_pred human
post `results_gpt5' ("OVERALL") (r(N)) (r(LLM_pos)) (r(Human_pos)) (r(TP)) (r(FP)) (r(FN)) (r(TN)) (r(accuracy)) (r(precision)) (r(recall)) (r(f1)) (r(kappa))
restore

* Per-factor metrics
levelsof factor, local(factors)
foreach f of local factors {
    preserve
    keep if factor=="`f'"
    count
    if r(N) > 0 {
        calc_metrics model_pred human
        post `results_gpt5' ("`f'") (r(N)) (r(LLM_pos)) (r(Human_pos)) (r(TP)) (r(FP)) (r(FN)) (r(TN)) (r(accuracy)) (r(precision)) (r(recall)) (r(f1)) (r(kappa))
    }
    restore
}

postclose `results_gpt5'

use results_gpt5, clear

* Convert to percentages and round
replace accuracy = round(accuracy*100, 0.1)
replace precision = round(precision*100, 0.1)
replace recall = round(recall*100, 0.1)
replace f1 = round(f1, 0.001)
replace kappa = round(kappa, 0.001)

* Clean up labels
label var factor "Factor"
label var N "Total N"
label var LLM_pos "LLM Positive"
label var Human_pos "Human Positive"
label var TP "True Positive"
label var FP "False Positive"
label var FN "False Negative"
label var TN "True Negative"
label var accuracy "Accuracy (%)"
label var precision "Precision (%)"
label var recall "Recall (%)"
label var f1 "F1 Score"
label var kappa "Cohen's Kappa"

* Reorder columns for better readability
order factor N LLM_pos Human_pos TP FP FN TN accuracy precision recall f1 kappa

* Export
export excel using "output/table2_gpt5_validation_metrics.xlsx", firstrow(varlabels) replace

* Display results with key columns
list factor N LLM_pos Human_pos accuracy precision recall f1 kappa, clean noobs

*----------------------------
* Part 2: Appendix Table 3a -- GPT-4o
*----------------------------
* Identical logic to Part 1, run against the GPT-4o reviewed sample.
import excel "output/validation_sample_gpt4o_reviewed.xlsx", sheet("validation_sample") firstrow clear

gen byte human = .
replace human = model_pred if human_label==1 & !missing(model_pred)
replace human = 1-model_pred if human_label==0 & !missing(model_pred)

tempname results_gpt4o
postfile `results_gpt4o' str40 factor N LLM_pos Human_pos TP FP FN TN accuracy precision recall f1 kappa using results_gpt4o, replace

* Overall metrics
preserve
calc_metrics model_pred human
post `results_gpt4o' ("OVERALL") (r(N)) (r(LLM_pos)) (r(Human_pos)) (r(TP)) (r(FP)) (r(FN)) (r(TN)) (r(accuracy)) (r(precision)) (r(recall)) (r(f1)) (r(kappa))
restore

* Per-factor metrics
levelsof factor, local(factors)
foreach f of local factors {
    preserve
    keep if factor=="`f'"
    count
    if r(N) > 0 {
        calc_metrics model_pred human
        post `results_gpt4o' ("`f'") (r(N)) (r(LLM_pos)) (r(Human_pos)) (r(TP)) (r(FP)) (r(FN)) (r(TN)) (r(accuracy)) (r(precision)) (r(recall)) (r(f1)) (r(kappa))
    }
    restore
}

postclose `results_gpt4o'

use results_gpt4o, clear

* Convert to percentages and round
replace accuracy = round(accuracy*100, 0.1)
replace precision = round(precision*100, 0.1)
replace recall = round(recall*100, 0.1)
replace f1 = round(f1, 0.001)
replace kappa = round(kappa, 0.001)

* Clean up labels
label var factor "Factor"
label var N "Total N"
label var LLM_pos "LLM Positive"
label var Human_pos "Human Positive"
label var TP "True Positive"
label var FP "False Positive"
label var FN "False Negative"
label var TN "True Negative"
label var accuracy "Accuracy (%)"
label var precision "Precision (%)"
label var recall "Recall (%)"
label var f1 "F1 Score"
label var kappa "Cohen's Kappa"

* Reorder columns for better readability
order factor N LLM_pos Human_pos TP FP FN TN accuracy precision recall f1 kappa

* Export
export excel using "output/table3a_gpt4o_validation_metrics.xlsx", firstrow(varlabels) replace

* Display results with key columns
list factor N LLM_pos Human_pos accuracy precision recall f1 kappa, clean noobs
