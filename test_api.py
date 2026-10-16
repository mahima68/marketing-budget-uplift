import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from api import app

client=TestClient(app)

def test_health_and_app():
    assert client.get('/api/health').json()['status']=='ok'
    assert 'Spend on the' in client.get('/').text
    assert client.get('/data.json').status_code==200

def test_scenario_matches_frozen_analysis():
    r=client.post('/api/scenario',json={}).json()
    data=client.get('/api/results').json()
    row=next(x for x in data['results'] if x['selected_on_validation'])
    assert r['additional_purchases']==pytest.approx(row['incremental_per_100k'])
    assert r['spend']==1000
    assert r['net_contribution']==pytest.approx(row['incremental_per_100k']*50-1000)
    assert r['net_ci_low']<=r['net_contribution']<=r['net_ci_high']

def test_audience_scaling_and_zero_margin():
    base=client.post('/api/scenario',json={}).json()
    scaled=client.post('/api/scenario',json={'audience':200000}).json()
    assert scaled['net_contribution']==pytest.approx(2*base['net_contribution'])
    zero=client.post('/api/scenario',json={'margin':0}).json()
    assert zero['net_contribution']==zero['net_ci_low']==zero['net_ci_high']==-zero['spend']

@pytest.mark.parametrize('payload',[{'capacity':.23},{'capacity':0},{'cost':-1},{'margin':-1},{'audience':0},{'audience':1000.5},{'strategy':'invented'},{'capacity':1.1}])
def test_invalid_scenarios(payload):
    assert client.post('/api/scenario',json=payload).status_code==422

def test_all_grid_capacities_and_strategies():
    for row in client.get('/api/curves').json():
        response=client.post('/api/scenario',json={'strategy':row['strategy'],'capacity':row['fraction']})
        assert response.status_code==200
        assert response.json()['additional_purchases']==pytest.approx(row['gain_per_100k'])
