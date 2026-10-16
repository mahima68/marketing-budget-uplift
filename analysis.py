# %% [markdown]
# # Marketing Budget Optimization Using Uplift Modelling
# **Decision:** which 20% of an eligible audience should receive advertising?
# This is a noncommercial portfolio benchmark, not an estimate of Criteo's actual ROI.
# We compare purchase propensity with incremental response, select on validation data,
# and evaluate a frozen policy on an untouched test set. No deployment is required.
#
# **Learning path:** read each explanation, run its cell, inspect the output, and explain
# what would change the business decision. The project uses real, corrected v2.1 data.
# %%
from pathlib import Path
import os, sys, json, hashlib, platform, urllib.request
os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd()/".mpl-cache"))
os.environ.setdefault("OMP_NUM_THREADS", "4")
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import norm
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score, average_precision_score, log_loss
from threadpoolctl import threadpool_limits
from IPython.display import display, Markdown
threadpool_limits(limits=4)
SEED=42
ROOT=Path.cwd()
RESULTS=ROOT/"results"; RESULTS.mkdir(exist_ok=True)
DATA=ROOT/"data"; DATA.mkdir(exist_ok=True)
CAPACITY=0.20
plt.rcParams.update({"figure.figsize":(10,5),"axes.spines.top":False,"axes.spines.right":False,"font.size":11,"axes.titleweight":"bold","savefig.dpi":150})
COLORS=["#123B5D","#007F86","#F2A541","#9E4784","#667085"]
# %% [markdown]
# ## 1. Source, sampling, and the limits of causal interpretation
# Source: https://ailab.criteo.com/criteo-uplift-prediction-dataset/
# Official publisher mirror: https://huggingface.co/datasets/criteo/criteo-uplift
# Use corrected **v2.1**, not the original release with advertiser leakage.
# The publisher anonymised features and non-uniformly subsampled data; estimates describe
# this released benchmark under a constant-assignment-probability assumption, not original
# advertiser effects. Assignment is eligibility to advertising, not guaranteed exposure.
# We take a seeded Bernoulli sample across the ENTIRE file, independent of all values.
# This retains natural outcome imbalance. We never take just the first rows.
# %%
URL="https://huggingface.co/datasets/criteo/criteo-uplift/resolve/main/criteo-research-uplift-v2.1.csv.gz"
EXPECTED_SHA="2716e1bf0fd157a93b5bf86924d9088419dfbac2022c6cd90030220634f616dc"
cache=DATA/"benchmark_sample.pkl.gz"
provenance_path=DATA/"provenance.json"
if cache.exists() and provenance_path.exists():
    # Only load this locally produced, trusted cache; never unpickle unknown files.
    df=pd.read_pickle(cache)
    provenance=json.loads(provenance_path.read_text())
else:
    supplied=os.environ.get("CRITEO_RAW_PATH")
    raw=Path(supplied) if supplied else DATA/"criteo-uplift-v2.1.csv.gz"
    if not raw.exists():
        print("Downloading corrected benchmark (~311 MB)...",flush=True)
        temp=raw.with_suffix(".part")
        urllib.request.urlretrieve(URL,temp); temp.replace(raw)
    h=hashlib.sha256()
    with raw.open("rb") as f:
        for block in iter(lambda:f.read(2**20),b""):h.update(block)
    assert h.hexdigest()==EXPECTED_SHA,"Source checksum mismatch: stop and investigate."
    rng=np.random.default_rng(SEED); parts=[]; total=0
    for chunk in pd.read_csv(raw,chunksize=200_000):
        total+=len(chunk)
        parts.append(chunk.loc[rng.random(len(chunk))<0.11])
    df=pd.concat(parts,ignore_index=True)
    for col in df.columns:
        df[col]=df[col].astype("float32" if col.startswith("f") else "int8")
    df.to_pickle(cache,compression="gzip")
    provenance={"url":URL,"version":"v2.1","sha256":h.hexdigest(),"source_rows":total,"sample_rows":len(df),"sampling":"Bernoulli p=0.11 over every source row; seed 42; independent of X,T,Y","seed":SEED,"license":"CC BY-NC-SA 4.0"}
    provenance_path.write_text(json.dumps(provenance,indent=2))
print(json.dumps(provenance,indent=2))
display(df.head())
# %% [markdown]
# ## 2. Audit the data and prevent leakage
# Only f0...f11 are inputs. `visit` and `exposure` are post-assignment variables:
# using them would reveal information unavailable when choosing whom to target.
# Feature labels have no business meaning; do not invent demographic descriptions.
# Identical feature vectors can occur after anonymisation; without user IDs they are
# not evidence of duplicated people, so we do not silently drop them.
# %%
features=sorted([c for c in df if c.startswith("f")],key=lambda c:int(c[1:]))
assert len(features)==12
assert df[["treatment","conversion"]].isin([0,1]).all().all()
assert np.isfinite(df[features].to_numpy()).all(),"Unexpected missing/infinite input: investigate source."
assert set(features).isdisjoint({"visit","exposure","conversion","treatment"})
audit=pd.DataFrame({"dtype":df.dtypes.astype(str),"missing":df.isna().sum(),"unique":df.nunique()})
audit.to_csv(RESULTS/"data_audit.csv")
print(f"Sample: {len(df):,} users; {df.conversion.sum():,} conversions; treatment share {df.treatment.mean():.3%}")
print(f"Identical complete rows: {df.duplicated().sum():,}; retained because user identity is unavailable.")
display(audit)
# %% [markdown]
# ## 3. Split before modelling
# 60% train, 20% validation, 20% final test, stratified by assignment and outcome.
# The test split is not used for model choice, cost assumptions, or targeting capacity.
# No dates or advertiser IDs are available, so future-time and advertiser generalisation
# cannot be tested. Split positions are saved for reproducibility.
# %%
idx=np.arange(len(df)); strata=df.treatment.astype(str)+df.conversion.astype(str)
tr,rest=train_test_split(idx,test_size=.4,random_state=SEED,stratify=strata)
va,te=train_test_split(rest,test_size=.5,random_state=SEED,stratify=strata.iloc[rest])
assert not(set(tr)&set(va) or set(tr)&set(te) or set(va)&set(te))
np.savez_compressed(RESULTS/"split_indices.npz",train=tr,validation=va,test=te)
X=df[features].to_numpy(); t=df.treatment.to_numpy(); y=df.conversion.to_numpy()
e=float(t[tr].mean())
split_summary=pd.DataFrame([{"split":n,"users":len(ix),"treated":int(t[ix].sum()),"conversions":int(y[ix].sum()),"conversion_rate":float(y[ix].mean())} for n,ix in [("train",tr),("validation",va),("test",te)]])
split_summary.to_csv(RESULTS/"split_summary.csv",index=False); display(split_summary)
# %% [markdown]
# ## 4. Understand the experiment (training data only)
# Difference in conversion rates estimates the average assignment effect in the
# released benchmark, subject to its sampling limitations. Confidence intervals use
# independent-user normal approximations. Balance checks are descriptive diagnostics.
# %%
group=df.iloc[tr].groupby("treatment").conversion.agg(["size","sum","mean"])
ate=group.loc[1,"mean"]-group.loc[0,"mean"]
ate_se=np.sqrt(sum(group.loc[a,"mean"]*(1-group.loc[a,"mean"])/group.loc[a,"size"] for a in [0,1]))
display(group)
print(f"Training assignment effect: {ate*100:.4f} percentage points; 95% CI [{(ate-1.96*ate_se)*100:.4f}, {(ate+1.96*ate_se)*100:.4f}]")
a,b=X[tr][t[tr]==1],X[tr][t[tr]==0]
smd=(a.mean(0)-b.mean(0))/np.sqrt((a.var(0)+b.var(0))/2)
balance=pd.DataFrame({"feature":features,"standardized_mean_difference":smd})
balance.to_csv(RESULTS/"feature_balance.csv",index=False)
fig,ax=plt.subplots();ax.barh(features,smd,color=COLORS[1]);ax.axvline(0,color="black",lw=.7);ax.set(title="Assignment balance · training sample",xlabel="Standardized mean difference")
fig.tight_layout();fig.savefig(RESULTS/"01_balance.png");display(fig);plt.close(fig)
# %% [markdown]
# ## 5. Models: purchase probability versus incremental response
# A propensity baseline predicts buying under treatment. A T-learner fits separate
# purchase models for treated/control users and subtracts probabilities. An S-learner
# fits one model with assignment as an input and predicts each user twice.
# We keep natural class frequencies: class weighting can distort probabilities needed
# for uplift. Complexity and the 20% capacity are fixed before final test inspection.
# %%
def logistic():
    return make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=400,random_state=SEED))
def boost(leaves=15):
    return HistGradientBoostingClassifier(max_iter=100,max_leaf_nodes=leaves,min_samples_leaf=150,l2_regularization=10,learning_rate=.08,early_stopping=False,random_state=SEED)
def fit_t(factory):
    models=[]
    for arm in [0,1]:
        mask=t[tr]==arm; m=factory();m.fit(X[tr][mask],y[tr][mask]);models.append(m)
    return models
print("Training linear T-learner...",flush=True)
linear=fit_t(logistic)
print("Training boosted T-learners...",flush=True)
trees15=fit_t(lambda:boost(15));trees31=fit_t(lambda:boost(31))
print("Training S-learner...",flush=True)
smodel=boost(15);smodel.fit(np.column_stack([X[tr],t[tr]]),y[tr])
def t_score(models,xx):
    return models[1].predict_proba(xx)[:,1]-models[0].predict_proba(xx)[:,1]
def s_score(xx):
    return smodel.predict_proba(np.column_stack([xx,np.ones(len(xx))]))[:,1]-smodel.predict_proba(np.column_stack([xx,np.zeros(len(xx))]))[:,1]
def scores(xx):
    return {"Likely buyers":trees15[1].predict_proba(xx)[:,1],"Linear T-learner":t_score(linear,xx),"Boosted T-learner 15":t_score(trees15,xx),"Boosted T-learner 31":t_score(trees31,xx),"Boosted S-learner":s_score(xx)}
# %% [markdown]
# ## 6. Evaluate targeting policies, not individual counterfactual labels
# We never observe both outcomes for one user. Use held-out doubly robust (DR) scores:
# phi = m1(X)-m0(X) + T/e*(Y-m1(X)) - (1-T)/(1-e)*(Y-m0(X)).
# Nuisance outcome models are trained only on train; e is the train treatment fraction.
# For a target mask pi, mean(pi*phi) estimates additional conversions per eligible user
# versus targeting nobody. IPW gives a sensitivity check without outcome regression.
# Random targeting is evaluated as its expectation q*mean(phi), not a lucky random draw.
# Normal intervals and paired comparisons condition on fitted models; they do not
# include model-training uncertainty, hidden clustering, or dataset-selection uncertainty.
# %%
def effect_scores(ix):
    m0=trees15[0].predict_proba(X[ix])[:,1];m1=trees15[1].predict_proba(X[ix])[:,1]
    ipw=t[ix]*y[ix]/e-(1-t[ix])*y[ix]/(1-e)
    dr=m1-m0+t[ix]*(y[ix]-m1)/e-(1-t[ix])*(y[ix]-m0)/(1-e)
    return dr,ipw

def policy(score,q):
    # Stable exact-size ranking, deterministic tie breaking independent of outcomes.
    k=int(np.floor(len(score)*q));mask=np.zeros(len(score));mask[np.argsort(-score,kind="stable")[:k]]=1
    return mask

def estimate(values):
    mu=float(np.mean(values));se=float(np.std(values,ddof=1)/np.sqrt(len(values)))
    return mu,mu-1.96*se,mu+1.96*se

vdr,vipw=effect_scores(va);vs=scores(X[va])
validation=pd.DataFrame([{"strategy":name,"incremental_per_100k":100000*np.mean(policy(score,CAPACITY)*vdr)} for name,score in vs.items()]).sort_values("incremental_per_100k",ascending=False)
uplift_names=[n for n in vs if n!="Likely buyers"]
winner=max(uplift_names,key=lambda n:np.mean(policy(vs[n],CAPACITY)*vdr))
validation.to_csv(RESULTS/"validation_selection.csv",index=False)
print("Frozen uplift model selected at 20% capacity:",winner)
display(validation)
# %% [markdown]
# ## 7. Final untouched test evaluation
# Report all predeclared strategies, but keep the validation winner as the selected
# model even if a different one looks better here. No test-based model reselection.
# Intervals across the exploratory curves are pointwise, not simultaneous guarantees.
# %%
tdr,tipw=effect_scores(te);ts=scores(X[te]);n=len(te)
masks={"Random targeting":np.full(n,CAPACITY),**{name:policy(score,CAPACITY) for name,score in ts.items()}}
rows=[]
for name,mask in masks.items():
    mu,lo,hi=estimate(mask*tdr)
    rows.append({"strategy":name,"target_fraction":float(mask.mean()),"incremental_per_100k":mu*1e5,"ci_low":lo*1e5,"ci_high":hi*1e5,"ipw_per_100k":float(np.mean(mask*tipw)*1e5),"selected_on_validation":name==winner})
test_results=pd.DataFrame(rows)
test_results.to_csv(RESULTS/"test_results.csv",index=False)
display(test_results.round(3))
comparisons=[]
for reference in ["Random targeting","Likely buyers"]:
    mu,lo,hi=estimate((masks[winner]-masks[reference])*tdr)
    comparisons.append({"comparison":winner+" minus "+reference,"difference_per_100k":mu*1e5,"ci_low":lo*1e5,"ci_high":hi*1e5})
comparisons=pd.DataFrame(comparisons);comparisons.to_csv(RESULTS/"paired_comparisons.csv",index=False);display(comparisons)
fig,ax=plt.subplots(figsize=(11,6));z=test_results.iloc[::-1]
ax.errorbar(z.incremental_per_100k,np.arange(len(z)),xerr=np.vstack([z.incremental_per_100k-z.ci_low,z.ci_high-z.incremental_per_100k]),fmt="o",color=COLORS[1],capsize=4)
ax.set_yticks(np.arange(len(z)),z.strategy);ax.axvline(0,color="gray",ls="--");ax.set(title="20% targeting capacity · held-out test results",xlabel="Estimated additional conversions per 100,000 eligible users (95% CI)")
fig.tight_layout();fig.savefig(RESULTS/"02_policy_comparison.png");display(fig);plt.close(fig)
# %% [markdown]
# ## 8. Budget curves and response-model diagnostics
# Capacity is a proxy for budget under a constant cost per targeted user. Curves show
# incremental conversions, not ordinary conversion rates. PR-AUC/ROC-AUC evaluate the
# purchase classifier only; neither measures targeting incrementality.
# %%
fractions=np.linspace(.05,1,20);curves=[]
for name in ["Random targeting","Likely buyers",winner]:
    for q in fractions:
        mask=np.full(n,q) if name=="Random targeting" else policy(ts[name],q)
        mu,lo,hi=estimate(mask*tdr)
        curves.append({"strategy":name,"fraction":float(q),"gain_per_100k":mu*1e5,"ci_low":lo*1e5,"ci_high":hi*1e5})
curves=pd.DataFrame(curves);curves.to_csv(RESULTS/"budget_curves.csv",index=False)
fig,ax=plt.subplots()
for color,(name,g) in zip(COLORS,curves.groupby("strategy",sort=False)):
    ax.plot(g.fraction*100,g.gain_per_100k,label=name,color=color,lw=2)
    ax.fill_between(g.fraction*100,g.ci_low,g.ci_high,color=color,alpha=.10)
ax.axvline(20,color="gray",ls=":");ax.axhline(0,color="gray",lw=.6);ax.set(title="How targeting capacity changes incremental conversions",xlabel="Audience targeted (%)",ylabel="Additional conversions per 100,000 eligible users");ax.legend(fontsize=9)
fig.tight_layout();fig.savefig(RESULTS/"03_budget_curve.png");display(fig);plt.close(fig)
mt=t[te]==1;p=ts["Likely buyers"][mt];yt=y[te][mt]
diagnostics={"treated_test_roc_auc":float(roc_auc_score(yt,p)),"treated_test_average_precision":float(average_precision_score(yt,p)),"treated_test_prevalence":float(yt.mean()),"treated_test_log_loss":float(log_loss(yt,p))}
print(json.dumps(diagnostics,indent=2))
# %% [markdown]
# ## 9. Where does the selected model find signal?
# Deciles are based on predicted uplift only. Show observed DR averages with intervals;
# noisy or non-monotonic deciles are useful evidence about model limitations.
# Feature codes cannot be translated into named business segments.
# %%
order=np.argsort(-ts[winner],kind="stable");deciles=[]
for i,ix in enumerate(np.array_split(order,10),1):
    mu,lo,hi=estimate(tdr[ix]);deciles.append({"uplift_decile":i,"users":len(ix),"conversions":int(y[te][ix].sum()),"mean_predicted_uplift":float(ts[winner][ix].mean()),"estimated_effect":mu,"ci_low":lo,"ci_high":hi})
deciles=pd.DataFrame(deciles);deciles.to_csv(RESULTS/"uplift_deciles.csv",index=False);display(deciles)
fig,ax=plt.subplots();ax.errorbar(deciles.uplift_decile,deciles.estimated_effect*100,yerr=np.vstack([deciles.estimated_effect-deciles.ci_low,deciles.ci_high-deciles.estimated_effect])*100,fmt="o-",capsize=4,color=COLORS[0]);ax.axhline(0,color="gray",ls="--");ax.set(title="Incremental response by predicted uplift decile",xlabel="Decile (1 = highest predicted uplift)",ylabel="Assignment effect (percentage points)")
fig.tight_layout();fig.savefig(RESULTS/"04_deciles.png");display(fig);plt.close(fig)
# %% [markdown]
# ## 10. Business scenarios: assumptions, not observed profits
# No costs, revenues, or margins are provided. Use currency-neutral illustrative units.
# Net contribution = incremental conversions * margin - targeted users * cost.
# Scenarios are specified here as a fixed grid; do not select a campaign policy using
# these test-set scenarios. A new prospective experiment is needed before rollout.
# Treatment means assignment/eligibility; actual impression costs could differ.
# %%
scenario=[]
for margin in [20,50,100]:
    for cost in [.01,.05,.10]:
        for _,r in test_results.iterrows():
            spend=100000*r.target_fraction*cost
            scenario.append({"strategy":r.strategy,"margin_assumption":margin,"cost_per_target_assumption":cost,"targeting_spend_per_100k":spend,"net_contribution":r.incremental_per_100k*margin-spend,"net_ci_low":r.ci_low*margin-spend,"net_ci_high":r.ci_high*margin-spend})
scenario=pd.DataFrame(scenario);scenario.to_csv(RESULTS/"profit_scenarios.csv",index=False)
display(scenario[(scenario.margin_assumption==50)&(scenario.cost_per_target_assumption==.05)].round(2))
# %% [markdown]
# ## 11. Write the decision memo from actual results
# A positive estimate alone is insufficient to claim superiority. Paired uncertainty
# matters because policies are evaluated on the same users. Never describe benchmark
# estimates as realised revenue, observed savings, or proven individual causal effects.
# %%
r=test_results.set_index("strategy").loc[winner]
beats_both=bool((comparisons.ci_low>0).all())
conclusion=("The selected model outperformed both predeclared baselines at the nominal 95% level in paired comparisons on this benchmark." if beats_both else "The test does not establish that the selected model beats both baselines at the nominal 95% level. Treat it as a candidate for further testing, not a proven improvement.")
report=f"""# Marketing budget optimization: decision memo

## Decision and evidence
Allocate advertising eligibility to a fixed 20% of an audience. The validation-selected model was **{winner}**.

- Source: corrected Criteo v2.1; {provenance['source_rows']:,} source rows.
- Independent seeded sample: {len(df):,} users; final test: {len(te):,} users with {int(y[te].sum()):,} conversions.
- Estimated incremental conversions per 100,000 eligible users: **{r.incremental_per_100k:.1f}**, nominal 95% interval **[{r.ci_low:.1f}, {r.ci_high:.1f}]**.
- This estimate compares the selected 20% policy with targeting nobody, not with random targeting. See paired comparisons for baseline improvements.

{conclusion}

## Strategy comparison at the same capacity

```text
"""+test_results.round(3).to_string(index=False)+"\n```\n\n## Paired improvements\n\n```text\n"+comparisons.round(3).to_string(index=False)+f"""

```

## Recommendation
Use the selected policy only as a hypothesis for a fresh randomized policy-level experiment. Compare it with the existing business strategy at equal cost and measure incremental conversions and net contribution. Predefine sample size, duration, and a minimum economically meaningful improvement. Do not infer individual persuadability from noisy scores.

## Economics
`results/profit_scenarios.csv` varies margin (20/50/100 units) and targeting cost (0.01/0.05/0.10 units). These are explicit illustrative assumptions, not observed data. The project estimates assignment effects, not per-impression response. Constant cost per target is a simplifying assumption.

## What limits the conclusion
The publisher changed incrementality through privacy subsampling; results do not recover original Criteo advertiser lift or ROI. Randomization motivates a constant assignment probability, estimated on train; pooled experiments and release sampling can still limit identification. Features are anonymous; user/advertiser IDs and dates are unavailable. Repeated-user dependence, time drift and advertiser transportability cannot be assessed. Confidence intervals assume independent users and condition on fitted models and targeting rules; they exclude training variability and are not adjusted for multiple comparisons. Conversion rarity makes heterogeneous effects noisy. IPW sensitivity is reported alongside DR estimates. No post-treatment exposure or visits enter the models.

## Reproducibility
Seed 42; 60/20/20 split stratified on treatment and conversion; exact split indices saved. Model selection used validation gain at 20% only. Final test was used once for reporting all predeclared methods. Dataset SHA-256: {provenance['sha256']}.

## Sources and attribution
Diemert, Betlei, Renaudin and Amini (2018), *A Large Scale Benchmark for Uplift Modeling*, AdKDD/TargetAd.
https://ailab.criteo.com/criteo-uplift-prediction-dataset/
https://huggingface.co/datasets/criteo/criteo-uplift
Data: CC BY-NC-SA 4.0, https://creativecommons.org/licenses/by-nc-sa/4.0/ . Sample is a modified subset; retain attribution and noncommercial/share-alike terms.
"""
(ROOT/"BUSINESS_REPORT.md").write_text(report)
summary={"winner":winner,"conclusion":conclusion,"sample_rows":len(df),"test_rows":len(te),"diagnostics":diagnostics,"seed":SEED,"assignment_probability":e,"python":platform.python_version()}
(RESULTS/"summary.json").write_text(json.dumps(summary,indent=2))
display(Markdown(report.split("## Strategy comparison")[0]))
print("Analysis complete. All results saved in results/.")
