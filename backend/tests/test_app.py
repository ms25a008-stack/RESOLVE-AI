import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
from app.main import create_app
from app.config import Settings
from app.domain import sla,now,retrieve,rank_teams
from app.models import Analysis
from app.ai import validate_sources
@pytest.fixture
def client(): return TestClient(create_app(Settings(demo_mode=True)))
def active(c): return next(t for t in c.get('/api/tickets').json() if t['status']!='resolved')
def result(): return {'category':'Network','suggested_priority':'P2','summary':'VPN configuration may be involved; investigation is needed.','hypotheses':['Profile mismatch is unverified.'],'required_expertise':['vpn'],'steps':[{'instruction':'Inspect logs without changing settings.','basis':'hypothesis','source_ids':[]}],'uncertainties':['Gateway configuration is not verified.']}
def test_seed(client):
 ts=client.get('/api/tickets').json(); assert len(ts)==50
 assert sum(t['status']=='resolved' and bool(t['solution']) for t in ts)==20
 assert all('reason' in t['sla'] for t in ts)
def test_create(client):
 assert client.post('/api/tickets',json={'title':'bad'}).status_code==422
 r=client.post('/api/tickets',json={'title':'VPN connectivity issue','description':'VPN disconnects every ten minutes on a managed laptop','priority':'P2','category':'Network'})
 assert r.status_code==201
 assert client.get('/api/tickets/'+r.json()['id']).json()['history'][0]['event']=='created'
def test_no_fake_ai(client):
 t=active(client); p='/api/tickets/'+t['id']
 assert client.post(p+'/analyze').status_code==503
 assert not client.get(p).json()['recommendations']
def test_sla():
 n=now(); t={'status':'open','created_at':(n-timedelta(hours=3)).isoformat(),'sla_due_at':(n+timedelta(hours=1)).isoformat()}
 assert sla(t,n)['state']=='at_risk'
 assert sla(t,n+timedelta(hours=1))['state']=='breached'
 t.update(status='resolved',resolved_at=n.isoformat())
 assert sla(t,n+timedelta(days=20))['state']=='met'
def test_retrieval(client):
 ts=client.get('/api/tickets').json(); t=next(t for t in ts if 'VPN' in t['title'] and t['status']!='resolved')
 ss=retrieve(t,ts); assert ss and 'VPN' in ss[0]['title']
 assert all(s['status']=='resolved' and s['id']!=t['id'] for s in ss)
 assert rank_teams('Network',['vpn'],client.get('/api/teams').json(),ts)[0]['name']=='Network Operations'
def test_sources():
 r=result(); r['steps'][0].update(basis='historical',source_ids=['invented'])
 with pytest.raises(ValueError): validate_sources(Analysis(**r),[])
 r['steps'][0]['source_ids']=[]
 with pytest.raises(ValueError): validate_sources(Analysis(**r),[])
def test_review_and_stale(client,monkeypatch):
 async def fake(*args): return result()
 monkeypatch.setattr('app.ai.analyze',fake)
 t=active(client); p='/api/tickets/'+t['id']; r=client.post(p+'/analyze').json()
 assert r['status']=='pending' and client.get(p).json()['ticket']['version']==t['version']
 d='/api/recommendations/'+r['id']+'/decision'; body={'decision':'approved','comment':'Reviewed the source and routing.'}
 assert client.post(d,json=body).status_code==200
 updated=client.get(p).json(); assert updated['ticket']['status']==t['status'] and updated['ticket']['priority']==t['priority']
 assert updated['ticket']['assigned_team_id']==r['resolver']['id'] and len(updated['decisions'])==1
 assert client.post(d,json=body).status_code==409
 assert client.patch(p,json={'version':t['version'],'status':'resolved','solution':'Verified approved repair','note':'Resolution checked'}).status_code==409
def test_resolve(client):
 t=active(client); p='/api/tickets/'+t['id']
 assert client.patch(p,json={'version':t['version'],'status':'resolved','note':'Verified repair'}).status_code==422
 assert client.post(p+'/notes',json={'note':'Waiting for owner validation.'}).status_code==201
 assert client.patch(p,json={'version':t['version'],'status':'resolved','solution':'Updated approved profile and verified connection.','note':'Owner verified restoration.'}).status_code==200
 assert client.get(p).json()['ticket']['resolved_at']
def test_auth_default(): assert TestClient(create_app(Settings(demo_mode=False))).get('/api/tickets').status_code==401
def test_requester(client,monkeypatch):
 async def requester(token): return {'id':'test','role':'requester'}
 monkeypatch.setattr(client.app.state.store,'user',requester)
 assert client.post('/api/tickets/00000000-0000-0000-0000-000000001001/analyze').status_code==403

def test_reject_does_not_apply(client,monkeypatch):
 async def fake(*args): return result()
 monkeypatch.setattr('app.ai.analyze',fake)
 t=active(client); p='/api/tickets/'+t['id']; r=client.post(p+'/analyze').json()
 assert client.post('/api/recommendations/'+r['id']+'/decision',json={'decision':'rejected','comment':'Not enough evidence to accept.'}).status_code==200
 after=client.get(p).json()['ticket']
 assert after['version']==t['version'] and after['assigned_team_id']==t['assigned_team_id']

def test_new_analysis_supersedes_old(client,monkeypatch):
 async def fake(*args): return result()
 monkeypatch.setattr('app.ai.analyze',fake)
 t=active(client); p='/api/tickets/'+t['id']; r=client.post(p+'/analyze').json()
 assert client.post(p+'/analyze').status_code==201
 assert client.post('/api/recommendations/'+r['id']+'/decision',json={'decision':'approved','comment':'Reviewed recommendation.'}).status_code==409
 assert client.post(p+'/analyze').status_code==201
 assert client.post(p+'/analyze').status_code==429

def test_production_assets(client):
 from pathlib import Path
 if not Path('frontend/dist/index.html').exists(): pytest.skip('Build frontend to check combined serving')
 assert client.get('/').status_code==200
 assert '/assets/' in client.get('/').text
 assert client.get('/api/tickets').headers['cache-control']=='no-store'

def test_demo_remote_rejected():
 c=TestClient(create_app(Settings(demo_mode=True)),client=('203.0.113.1',4321))
 assert c.get('/api/tickets').status_code==403
