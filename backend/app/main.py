import asyncio
from collections import defaultdict, deque
from pathlib import Path
from time import monotonic
from uuid import UUID
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .config import Settings
from .store import DemoStore, SupabaseStore
from .models import TicketInput, Decision, Change, Note
from .domain import sla, retrieve, rank_teams
from . import ai

def create_app(settings=None, store=None):
    settings=settings or Settings()
    app=FastAPI(title='ResolveAI',version='0.1.0')
    app.state.store=store or (DemoStore() if settings.demo_mode else SupabaseStore(settings))
    app.add_middleware(CORSMiddleware,allow_origins=[settings.frontend_origin],allow_methods=['GET','POST','PATCH'],allow_headers=['Authorization','Content-Type'])
    attempts=defaultdict(deque)
    ai_slots=asyncio.Semaphore(2)
    @app.middleware('http')
    async def protection(request,call_next):
        if settings.demo_mode and request.client and request.client.host not in ('127.0.0.1','::1','testclient'):
            return __import__('starlette.responses',fromlist=['JSONResponse']).JSONResponse({'detail':'Demo mode is localhost-only. Configure Supabase for hosted use.'},403)
        result=await call_next(request)
        result.headers['X-Content-Type-Options']='nosniff'
        result.headers['Referrer-Policy']='no-referrer'
        if request.url.path.startswith('/api'): result.headers['Cache-Control']='no-store'
        return result
    async def auth(request:Request):
        token=request.headers.get('Authorization','').removeprefix('Bearer ').strip()
        if not settings.demo_mode and not token: raise HTTPException(401,'Sign in to continue.')
        return {'user':await app.state.store.user(token),'token':token}
    async def engineer(ctx=Depends(auth)):
        if ctx['user']['role'] not in ('engineer','admin'): raise HTTPException(403,'An engineer must review this action.')
        return ctx
    async def rows(table,ctx): return await app.state.store.all(table,ctx['token'])
    async def get_ticket(tid,ctx):
        t=next((t for t in await rows('tickets',ctx) if t['id']==str(tid)),None)
        if not t: raise HTTPException(404,'Ticket not found')
        return t
    async def rpc(name,data,ctx): return await app.state.store.rpc(name,data,ctx['token'],ctx['user']['id'])
    @app.get('/api/health')
    async def health(): return {'status':'ok','mode':'demo' if settings.demo_mode else 'supabase','ai_configured':bool(settings.gemini_api_key and settings.gemini_free_tier_confirmed)}
    @app.get('/api/me')
    async def me(ctx=Depends(auth)): return ctx['user']
    @app.get('/api/tickets')
    async def tickets(ctx=Depends(auth)):
        return [{**t,'sla':sla(t)} for t in sorted(await rows('tickets',ctx),key=lambda x:x['created_at'],reverse=True)]
    @app.get('/api/teams')
    async def teams(ctx=Depends(auth)):
        all_t=await rows('tickets',ctx)
        return [{**t,'active_tickets':sum(x['status']!='resolved' and x.get('assigned_team_id')==t['id'] for x in all_t)} for t in await rows('teams',ctx)]
    @app.post('/api/tickets',status_code=201)
    async def create(data:TicketInput,ctx=Depends(auth)): return await rpc('create_ticket',{'p_data':data.model_dump()},ctx)
    @app.get('/api/tickets/{tid}')
    async def detail(tid:UUID,ctx=Depends(auth)):
        t=await get_ticket(tid,ctx)
        recs=[r for r in await rows('recommendations',ctx) if r['ticket_id']==str(tid)]
        for r in recs:
            if 'multi_agent' not in r and isinstance(r.get('analysis'), dict):
                r['multi_agent'] = r['analysis'].get('multi_agent')
        ids={r['id'] for r in recs}
        return {'ticket':{**t,'sla':sla(t)},'recommendations':sorted(recs,key=lambda x:x['created_at'],reverse=True),'history':sorted([r for r in await rows('ticket_history',ctx) if r['ticket_id']==str(tid)],key=lambda x:x['created_at'],reverse=True),'decisions':[d for d in await rows('decisions',ctx) if d['recommendation_id'] in ids]}
    @app.get('/api/tickets/{tid}/context')
    async def context(tid:UUID,ctx=Depends(engineer)):
        t=await get_ticket(tid,ctx); all_t=await rows('tickets',ctx)
        return {'sources':retrieve(t,all_t),'resolvers':rank_teams(t['category'],[],await rows('teams',ctx),all_t),'method':'Deterministic keyword retrieval and resolver scoring; not AI.'}
    @app.post('/api/tickets/{tid}/analyze',status_code=201)
    async def analyze(tid:UUID,ctx=Depends(engineer)):
        # Single worker MVP rate limit; migrate to a shared limiter before horizontal scaling.
        bucket=attempts[ctx['user']['id']]; clock=monotonic()
        while bucket and clock-bucket[0]>60: bucket.popleft()
        if len(bucket)>=3: raise HTTPException(429,'Limit: 3 analysis attempts per minute. Try shortly.')
        bucket.append(clock)
        t=await get_ticket(tid,ctx)
        if t['status']=='resolved': raise HTTPException(409,'Reopen the ticket before requesting a new analysis.')
        all_t=await rows('tickets',ctx)
        all_teams=await rows('teams',ctx)
        if not all_teams: raise HTTPException(409,'Configure resolver teams before analysis.')
        async with ai_slots:
            record=await ai.analyze_ticket(t,all_t,all_teams,settings)
        # Guarantee multi_agent is attached to analysis for Supabase jsonb storage
        if 'multi_agent' in record and isinstance(record.get('analysis'), dict) and 'multi_agent' not in record['analysis']:
            record['analysis']['multi_agent'] = record['multi_agent']
        return await rpc('save_recommendation',{'p_data':record,'p_actor':ctx['user']['id']},ctx)
    @app.post('/api/recommendations/{rid}/decision')
    async def decision(rid:UUID,data:Decision,ctx=Depends(engineer)):
        return await rpc('review_recommendation',{'p_id':str(rid),'p_decision':data.decision,'p_comment':data.comment},ctx)
    @app.patch('/api/tickets/{tid}')
    async def change(tid:UUID,data:Change,ctx=Depends(engineer)):
        if data.status=='resolved' and len(data.solution.strip())<10: raise HTTPException(422,'Document a solution of at least 10 characters before resolving.')
        return await rpc('change_ticket',{'p_id':str(tid),'p_data':data.model_dump()},ctx)
    @app.post('/api/tickets/{tid}/notes',status_code=201)
    async def note(tid:UUID,data:Note,ctx=Depends(auth)):
        await get_ticket(tid,ctx)
        await rpc('add_note',{'p_id':str(tid),'p_note':data.note},ctx)
        return {'saved':True}
    dist=Path(__file__).resolve().parents[2]/'frontend/dist'
    if dist.exists():
        app.mount('/assets',StaticFiles(directory=dist/'assets'),name='assets')
        @app.get('/')
        async def index(): return FileResponse(dist/'index.html')
    return app
app=create_app()
