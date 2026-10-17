import asyncio
import copy
import json
from pathlib import Path
from uuid import uuid4
from datetime import timedelta
import httpx
from fastapi import HTTPException
from .domain import now, dt, SLA_HOURS

class SupabaseStore:
    def __init__(self, settings): self.settings=settings
    async def request(self, method, path, token, body=None, service=False):
        key=self.settings.supabase_service_role_key if service else self.settings.supabase_anon_key
        if not self.settings.supabase_url or not key: raise HTTPException(503,'Supabase is not configured in backend environment settings.')
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response=await client.request(method,self.settings.supabase_url.rstrip('/')+path,headers={'apikey':key,'Authorization':'Bearer '+(key if service else token)},json=body)
        except httpx.HTTPError:
            raise HTTPException(503,'Database is unavailable. Try again shortly.')
        if response.status_code>=400:
            code=response.json().get('code','') if 'json' in response.headers.get('content-type','') else ''
            status=409 if code=='40001' else 403 if response.status_code==403 else 401 if response.status_code==401 else 503
            message={409:'This record changed or was already reviewed. Refresh before continuing.',403:'Your account does not have permission.',401:'Session expired. Sign in again.',503:'Database request failed. Check migrations and configuration.'}[status]
            raise HTTPException(status,message)
        return response.json() if response.content else None
    async def user(self,token):
        u=await self.request('GET','/auth/v1/user',token)
        members=await self.request('GET',f"/rest/v1/members?user_id=eq.{u['id']}&select=role",token)
        if not members: raise HTTPException(403,'Ask your administrator to add you to this workspace.')
        return {'id':u['id'],'email':u.get('email'),'role':members[0]['role']}
    async def all(self, table, token):
        # Explicit paging avoids silently losing records at Supabase's default row cap.
        rows=[]
        for offset in range(0,10000,500):
            batch=await self.request('GET',f'/rest/v1/{table}?select=*&order=id&limit=500&offset={offset}',token)
            rows.extend(batch)
            if len(batch)<500: return rows
        raise HTTPException(503,'Workspace exceeds MVP query capacity. Add server-side pagination before growing beyond 10,000 records.')
    async def rpc(self,name,data,token,actor=None):
        return await self.request('POST','/rest/v1/rpc/'+name,token,data,service=name=='save_recommendation')

class DemoStore:
    """Explicit process-local demo; resets on restart, never presented as Supabase."""
    def __init__(self):
        data=json.loads(Path(__file__).with_name('seed.json').read_text())
        shift=now()-dt('2026-10-17T08:00:00+00:00')
        for t in data['tickets']:
            for field in ['created_at','sla_due_at','resolved_at']:
                if t.get(field): t[field]=(dt(t[field])+shift).isoformat()
        self.data={**data,'recommendations':[],'ticket_history':[],'decisions':[]}
        self.lock=asyncio.Lock()
    async def user(self,token): return {'id':'00000000-0000-0000-0000-000000000001','email':'engineer@demo.example','role':'engineer'}
    async def all(self,table,token): return copy.deepcopy(self.data[table])
    def event(self,tid,actor,event,details):
        self.data['ticket_history'].append(dict(id=str(uuid4()),ticket_id=tid,actor_id=actor,event=event,details=details,created_at=now().isoformat()))
    async def rpc(self,name,data,token,actor=None):
        async with self.lock:
            return copy.deepcopy(self._rpc(name,data,actor))
    def _rpc(self,name,p,actor):
        def ticket(tid):
            t=next((t for t in self.data['tickets'] if t['id']==tid),None)
            if not t: raise HTTPException(404,'Ticket not found')
            return t
        if name=='create_ticket':
            d=p['p_data']; created=now(); t={**d,'id':str(uuid4()),'number':max(t['number'] for t in self.data['tickets'])+1,'status':'open','created_at':created.isoformat(),'sla_due_at':(created+timedelta(hours=SLA_HOURS[d['priority']])).isoformat(),'resolved_at':None,'solution':'','reporter_id':actor,'assigned_team_id':None,'version':1,'is_sample':False}
            self.data['tickets'].append(t); self.event(t['id'],actor,'created',{}); return t
        if name=='save_recommendation':
            d=p['p_data']; t=ticket(d['ticket_id'])
            if t['version']!=d['ticket_version'] or t['status']=='resolved': raise HTTPException(409,'Ticket changed. Refresh.')
            for r in self.data['recommendations']:
                if r['ticket_id']==t['id'] and r['status']=='pending': r['status']='superseded'
            r={**d,'id':str(uuid4()),'status':'pending','created_at':now().isoformat(),'created_by':actor}
            self.data['recommendations'].append(r); self.event(t['id'],actor,'analysis_generated',{'recommendation_id':r['id']}); return r
        if name=='review_recommendation':
            r=next((r for r in self.data['recommendations'] if r['id']==p['p_id']),None)
            if not r: raise HTTPException(404,'Recommendation not found')
            t=ticket(r['ticket_id'])
            if r['status']!='pending' or t['version']!=r['ticket_version'] or t['status']=='resolved': raise HTTPException(409,'Stale or already reviewed recommendation')
            r['status']=p['p_decision']
            self.data['decisions'].append(dict(id=str(uuid4()),recommendation_id=r['id'],actor_id=actor,decision=p['p_decision'],comment=p['p_comment'],created_at=now().isoformat()))
            if r['status']=='approved': t.update(assigned_team_id=r['resolver']['id'],category=r['analysis']['category'],version=t['version']+1)
            self.event(t['id'],actor,'recommendation_'+r['status'],{'comment':p['p_comment']}); return r
        t=ticket(p['p_id'])
        if name=='add_note': self.event(t['id'],actor,'note',{'note':p['p_note']}); return None
        if name=='change_ticket':
            d=p['p_data']
            if d['version']!=t['version']: raise HTTPException(409,'Ticket changed. Refresh.')
            t.update(status=d['status'],solution=d['solution'] if d['status']=='resolved' else '',resolved_at=(t.get('resolved_at') or now().isoformat()) if d['status']=='resolved' else None,version=t['version']+1)
            for r in self.data['recommendations']:
                if r['ticket_id']==t['id'] and r['status']=='pending': r['status']='superseded'
            self.event(t['id'],actor,'status_changed',d); return t
        raise ValueError(name)
