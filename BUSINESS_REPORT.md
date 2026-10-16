# Marketing budget optimization: decision memo

## Decision and evidence
Allocate advertising eligibility to a fixed 20% of an audience. The validation-selected model was **Boosted S-learner**.

- Source: corrected Criteo v2.1; 13,979,592 source rows.
- Independent seeded sample: 1,537,120 users; final test: 307,424 users with 888 conversions.
- Estimated incremental conversions per 100,000 eligible users: **88.0**, nominal 95% interval **[48.1, 127.9]**.
- This estimate compares the selected 20% policy with targeting nobody, not with random targeting. See paired comparisons for baseline improvements.

The test does not establish that the selected model beats both baselines at the nominal 95% level. Treat it as a candidate for further testing, not a proven improvement.

## Strategy comparison at the same capacity

```text
            strategy  target_fraction  incremental_per_100k  ci_low  ci_high  ipw_per_100k  selected_on_validation
    Random targeting              0.2                19.255  10.934   27.575        23.973                   False
       Likely buyers              0.2                88.135  47.981  128.289       111.990                   False
    Linear T-learner              0.2                91.407  54.032  128.783       117.294                   False
Boosted T-learner 15              0.2                88.465  53.721  123.210       107.644                   False
Boosted T-learner 31              0.2                85.488  50.103  120.873       105.593                   False
   Boosted S-learner              0.2                87.988  48.115  127.860       111.104                    True
```

## Paired improvements

```text
                              comparison  difference_per_100k  ci_low  ci_high
Boosted S-learner minus Random targeting               68.733  36.747  100.719
   Boosted S-learner minus Likely buyers               -0.148  -5.762    5.467
```

## Recommendation
Use the selected policy only as a hypothesis for a fresh randomized policy-level experiment. Compare it with the existing business strategy at equal cost and measure incremental conversions and net contribution. Predefine sample size, duration, and a minimum economically meaningful improvement. Do not infer individual persuadability from noisy scores.

## Economics
`results/profit_scenarios.csv` varies margin (20/50/100 units) and targeting cost (0.01/0.05/0.10 units). These are explicit illustrative assumptions, not observed data. The project estimates assignment effects, not per-impression response. Constant cost per target is a simplifying assumption.

## What limits the conclusion
The publisher changed incrementality through privacy subsampling; results do not recover original Criteo advertiser lift or ROI. Randomization motivates a constant assignment probability, estimated on train; pooled experiments and release sampling can still limit identification. Features are anonymous; user/advertiser IDs and dates are unavailable. Repeated-user dependence, time drift and advertiser transportability cannot be assessed. Confidence intervals assume independent users and condition on fitted models and targeting rules; they exclude training variability and are not adjusted for multiple comparisons. Conversion rarity makes heterogeneous effects noisy. IPW sensitivity is reported alongside DR estimates. No post-treatment exposure or visits enter the models.

## Reproducibility
Seed 42; 60/20/20 split stratified on treatment and conversion; exact split indices saved. Model selection used validation gain at 20% only. Final test was used once for reporting all predeclared methods. Dataset SHA-256: 2716e1bf0fd157a93b5bf86924d9088419dfbac2022c6cd90030220634f616dc.

## Sources and attribution
Diemert, Betlei, Renaudin and Amini (2018), *A Large Scale Benchmark for Uplift Modeling*, AdKDD/TargetAd.
https://ailab.criteo.com/criteo-uplift-prediction-dataset/
https://huggingface.co/datasets/criteo/criteo-uplift
Data: CC BY-NC-SA 4.0, https://creativecommons.org/licenses/by-nc-sa/4.0/ . Sample is a modified subset; retain attribution and noncommercial/share-alike terms.
