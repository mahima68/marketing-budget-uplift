# Understand the project before putting it on your CV

## 1. The business decision

Imagine 100,000 eligible customers, with capacity to advertise to 20,000. The goal is additional purchases caused by the advertising policy. A high observed conversion rate among targeted customers does not prove effectiveness: they might have purchased without advertising.

A purchase model estimates how likely a person is to buy under a particular condition. Uplift estimates the difference between their predicted purchase probabilities with and without advertising assignment. These scores are uncertain statistical estimates, not labels proving that a specific person was persuaded.

## 2. Why experiment data matter

A treatment group is eligible for advertising; a control group is withheld. Random assignment helps separate advertising effects from pre-existing purchase intent. Merely comparing people who saw an ad with people who did not can be biased: ad delivery itself depends on behaviour and eligibility.

We therefore model assigned treatment, never actual exposure. This is an intention-to-treat question. Criteo pooled experiments and changed data through privacy sampling, so the causal interpretation belongs to the released benchmark under assumptions, not original advertiser economics.

## 3. Learn these terms

| Term | Meaning in this project |
|---|---|
| Conversion | Binary purchase outcome |
| Treatment | Assignment to advertising eligibility |
| Propensity-to-buy | Predicted purchase probability; not the treatment-assignment probability |
| Assignment probability e | Fraction assigned treatment, estimated from training data |
| Uplift | Difference in expected outcomes under treatment and control |
| T-learner | Separate outcome models in each treatment arm |
| S-learner | One outcome model with treatment as an input |
| Policy | A rule that chooses who is targeted |
| Capacity | Percentage of the audience that may be targeted |
| Counterfactual | Outcome that would occur under the alternative assignment |
| Leakage | Letting unavailable future/outcome information influence a prediction |

## 4. Why three splits?

Training fits models. Validation chooses the uplift model at 20% capacity. The final test estimates how that frozen choice performs on unseen data. Selecting the model that looks best on the test table would invalidate the intended evaluation. All methods are reported for transparency, but the selected label remains tied to validation.

The split is random rather than chronological because dates are unavailable. This cannot prove performance on future campaigns or unseen advertisers.

## 5. How to evaluate when individual uplift is unobservable

Each user appears in only one treatment arm. There is no true individual uplift label to compare with a prediction. Instead, estimate policy value across held-out users.

An inverse-probability weighted score is:

`IPW = T*Y/e - (1-T)*Y/(1-e)`

Multiply this by a target indicator and average to estimate incremental conversions per eligible user. Because controls are less common, their outcomes receive larger weights and can create substantial variance.

The doubly robust score adds outcome predictions and reweights residual errors:

`DR = m1(X)-m0(X) + T*(Y-m1(X))/e - (1-T)*(Y-m0(X))/(1-e)`

With suitable identification conditions, correct assignment probabilities or correct outcome regressions can support consistency. “Doubly robust” does not remove unmeasured bias, interference, release sampling problems, or failures of the underlying assumptions. We estimate e using training data and fit outcome models only on train. Evaluation users are separate.

At 20% capacity, a result of 50 additional conversions per 100,000 eligible users means an estimated 50 more purchases from targeting 20,000 rather than nobody. It does not mean 50 more than random targeting; that needs a separate paired comparison.

## 6. How to read uncertainty

A point estimate ranks observed results. An interval describes sampling uncertainty under assumptions. If the paired interval for model minus baseline crosses zero, evidence is insufficient to claim superiority at that nominal level. This is neither proof of equality nor proof that the model has no value.

Intervals here are normal approximations, condition on fitted models, and assume independent rows. They do not include retraining variability, unknown user clustering or changes to the source population. Multiple strategies and capacities are exploratory; intervals are not simultaneous guarantees.

## 7. Business economics

`Net contribution = additional purchases * margin per purchase - targeted users * cost per target`

Costs and margins are absent, so the scenario grid uses hypothetical currency-neutral units. A different margin or delivery-cost structure can reverse the business recommendation. Budget curves are retrospective comparisons, not approval for a production campaign. The next practical step is a fresh randomized experiment comparing complete targeting policies at equal cost.

## 8. Why the project is more than fitting a classifier

Your contribution is a defensible decision framework: choosing the right estimand, preventing leakage, distinguishing purchase probability from incrementality, designing evaluation, representing uncertainty and tying outputs to spending assumptions. More complex algorithms do not automatically make the project stronger.

## 9. Interview preparation

Be ready to explain:

1. Why likely buyers might be poor advertising targets.
2. Why exposure and visits are excluded.
3. Why ROC-AUC does not establish effective targeting.
4. How the validation winner was chosen without test leakage.
5. How paired comparisons differ from comparing two overlapping confidence intervals.
6. Why positive benchmark gain is not realised profit.
7. What anonymisation and privacy sampling prevent you from concluding.
8. What you would randomize in the next business experiment.

## 10. Make the work your own

Read and explain every cell. Recreate a few calculations by hand on a tiny example. Write your interpretation of the actual plots. After documenting this fixed experiment, a future extension could compare model stability across training resamples with a fresh test set, or use a dataset with interpretable pre-treatment features. Do not invent performance gains or describe this as a campaign you ran for a real company.
