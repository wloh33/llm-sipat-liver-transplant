*******************************************************
* Figure 2: domain prevalence (Panel A) and Spearman correlation with
* total SIPAT score (Panel B).
*
* The values entered below are the published aggregate results (domain
* prevalence percentages and Spearman rho/p-values reported in the
* manuscript's Results section and Figure 2) -- no patient-level data is
* used or required to reproduce this figure.
*******************************************************
clear
set more off

*------------------------------------------------------------*
* Enter data
*------------------------------------------------------------*

input ///
str60 domain n percent rho p
"Alcohol use and relapse risk"                    47 100.0 .    .
"Social support and caregiver readiness"          47 100.0 .    .
"Treatment adherence and transplant motivation"   47 100.0 .    .
"Cognitive and functional status"                 47 100.0 .    .
"Financial and socioeconomic stability"           47 100.0 .    .
"Polysubstance and other substance usage"         35  74.5 .01  .950
"Psychiatric stability and mental health"          41  87.2 .06  .720
"Psychosocial environment and life stressors"     39  83.0 .19  .215
"Spirituality and coping"                          40  85.1 .37  .011
"Safety and legal context"                         20  42.6 .08  .599
end


*------------------------------------------------------------*
* PANEL A: Domain prevalence
*------------------------------------------------------------*

* Desired ordering from top to bottom
gen yA = .
replace yA = 10 if domain == "Alcohol use and relapse risk"
replace yA =  9 if domain == "Social support and caregiver readiness"
replace yA =  8 if domain == "Treatment adherence and transplant motivation"
replace yA =  7 if domain == "Cognitive and functional status"
replace yA =  6 if domain == "Financial and socioeconomic stability"
replace yA =  5 if domain == "Psychiatric stability and mental health"
replace yA =  4 if domain == "Spirituality and coping"
replace yA =  3 if domain == "Psychosocial environment and life stressors"
replace yA =  2 if domain == "Polysubstance and other substance usage"
replace yA =  1 if domain == "Safety and legal context"

* Percentage labels
gen pct_label = string(percent, "%4.1f") + "%"

twoway ///
    (bar percent yA if percent == 100, horizontal ///
        barwidth(.55) fcolor(gs8) lcolor(gs8)) ///
    (bar percent yA if percent < 100, horizontal ///
        barwidth(.55) fcolor(orange) lcolor(orange)) ///
    (scatter yA percent, ///
        msymbol(none) ///
        mlabel(pct_label) ///
        mlabposition(3) ///
        mlabsize(small) ///
        mlabcolor(black)), ///
    ylabel( ///
        10 "Alcohol use and relapse risk" ///
         9 "Social support and caregiver readiness" ///
         8 "Treatment adherence and transplant motivation" ///
         7 "Cognitive and functional status" ///
         6 "Financial and socioeconomic stability" ///
         5 "Psychiatric stability and mental health" ///
         4 "Spirituality and coping" ///
         3 "Psychosocial environment and life stressors" ///
         2 "Polysubstance and other substance usage" ///
         1 "Safety and legal context", ///
         angle(horizontal) labsize(small) noticks) ///
    xlabel(0(25)100, labsize(small) grid) ///
    xscale(range(0 115)) ///
    xtitle("Patients with domain present (%)", size(small)) ///
    ytitle("") ///
    title("{bf:A   Domain Prevalence}", ///
        size(medsmall) position(11)) ///
    legend(order(2 "Varies across patients" ///
                 1 "Present in all patients" ///
                   "(correlation not estimable)") ///
           size(vsmall) ///
           cols(1) ///
           position(5) ///
           ring(0)) ///
    graphregion(color(white)) ///
    plotregion(color(white)) ///
    name(panelA, replace)


*------------------------------------------------------------*
* PANEL B: Association with SIPAT total score
*------------------------------------------------------------*

* Order from largest rho to smallest
gen yB = .
replace yB = 5 if domain == "Spirituality and coping"
replace yB = 4 if domain == "Psychosocial environment and life stressors"
replace yB = 3 if domain == "Safety and legal context"
replace yB = 2 if domain == "Psychiatric stability and mental health"
replace yB = 1 if domain == "Polysubstance and other substance usage"

* Create formatted rho/p-value labels
gen stat_label = ""
replace stat_label = "{&rho} = " + string(rho,"%4.2f") + ///
                     ", p = " + string(p,"%5.3f") if !missing(rho)

twoway ///
    (bar rho yB if !missing(rho), horizontal ///
        barwidth(.45) ///
        fcolor(orange) ///
        lcolor(orange)) ///
    (scatter yB rho if !missing(rho), ///
        msymbol(none) ///
        mlabel(stat_label) ///
        mlabposition(3) ///
        mlabsize(small) ///
        mlabcolor(black)), ///
    ylabel( ///
        5 "Spirituality and coping" ///
        4 "Psychosocial environment and life stressors" ///
        3 "Safety and legal context" ///
        2 "Psychiatric stability and mental health" ///
        1 "Polysubstance and other substance usage", ///
        angle(horizontal) labsize(small) noticks) ///
    xlabel(0(.1).5, format(%3.1f) labsize(small) grid) ///
    xscale(range(0 .60)) ///
    xtitle("Spearman {&rho} with total SIPAT score", size(small)) ///
    ytitle("") ///
    title("{bf:B   Association with SIPAT Total Score}", ///
        size(medsmall) position(11)) ///
    legend(off) ///
    note("Domains present in all patients excluded (no variance for correlation).", ///
         size(vsmall) color(gs7)) ///
    graphregion(color(white)) ///
    plotregion(color(white)) ///
    name(panelB, replace)


*------------------------------------------------------------*
* COMBINE PANELS
*------------------------------------------------------------*

graph combine panelA panelB, ///
    cols(2) ///
    xsize(13) ///
    ysize(6) ///
    graphregion(color(white)) ///
    name(Figure2, replace)


*------------------------------------------------------------*
* EXPORT
*------------------------------------------------------------*

graph export "Figure2_final.png", ///
    name(Figure2) ///
    width(4000) replace

graph export "Figure2_final.pdf", ///
    name(Figure2) ///
    replace
