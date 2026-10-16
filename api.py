"""Read-only results and hypothetical scenario API; does not serve individual predictions."""
from pathlib import Path
import json, csv, math
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

ROOT=Path(__file__).resolve().parent
app=FastAPI(title="Marketing Decision Lab",version="1.0.0",description="Verified benchmark results and hypothetical business scenarios. No individual-level predictions, live campaign decisions, or observed profit claims.")

def load_data():
    return json.loads((ROOT/'dashboard/dist/data.json').read_text())

class ScenarioRequest(BaseModel):
    strategy: str = Field(default="Boosted S-learner",max_length=80)
    capacity: float = Field(default=.20,ge=.05,le=1,allow_inf_nan=False)
    audience: int = Field(default=100000,ge=1000,le=10000000,strict=True)
    margin: float = Field(default=50,ge=0,le=1000000,allow_inf_nan=False)
    cost: float = Field(default=.05,ge=0,le=1000000,allow_inf_nan=False)

    @field_validator('capacity')
    @classmethod
    def observed_capacity(cls,value):
        if abs(value*20-round(value*20))>1e-8:
            raise ValueError('Capacity must be on the evaluated 5% grid (.05, .10, ..., 1.0).')
        return value

def calculate(request: ScenarioRequest):
    data=load_data()
    row=next((r for r in data['curves'] if r['strategy']==request.strategy and abs(r['fraction']-request.capacity)<1e-8),None)
    if row is None:raise HTTPException(422,'No evaluated curve for this strategy. Use Random targeting, Likely buyers, or the validation-selected model.')
    scale=request.audience/100000
    spend=request.audience*request.capacity*request.cost
    gain=row['gain_per_100k']*scale
    return {**request.model_dump(),'targeted_users':request.audience*request.capacity,'additional_purchases':gain,'purchase_ci_low':row['ci_low']*scale,'purchase_ci_high':row['ci_high']*scale,'spend':spend,'net_contribution':gain*request.margin-spend,'net_ci_low':row['ci_low']*scale*request.margin-spend,'net_ci_high':row['ci_high']*scale*request.margin-spend,'interpretation':'Released-benchmark estimate under fixed fitted models; hypothetical costs and margins; audience scaling assumes the same population mix. Not observed profit.'}

@app.get('/api/health')
def health():return {'status':'ok','data_version':'criteo-v2.1','model_training':False}

@app.get('/api/results')
def results():
    data=load_data()
    return {k:data[k] for k in ['summary','results','comparisons','provenance']}

@app.get('/api/curves')
def curves():return load_data()['curves']

@app.post('/api/scenario')
def scenario(request: ScenarioRequest):return calculate(request)

# This same container serves the complete browser app and API on one origin.
app.mount('/',StaticFiles(directory=ROOT/'dashboard/dist',html=True),name='dashboard')
