"""Generate reproducible fictional scenarios; no real company or personal data."""
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from uuid import UUID
ROOT = Path(__file__).resolve().parents[1]
def uid(n): return str(UUID(int=n))
SCENARIOS = [
('Network','VPN disconnects during remote sessions','VPN tunnel drops every ten minutes; office LAN remains stable. Client logs show renegotiation timeouts.','Compared gateway and client lifetimes, corrected the approved VPN profile mismatch, then verified a stable 60-minute session.','vpn gateway'),
('Identity','SSO login loops after sign-in','Employees authenticate successfully but the expense portal redirects to the login screen. Other apps work.','Compared SAML assertion audience with the service provider configuration, corrected the audience value under change approval and verified sign-in.','saml sso'),
('Applications','ERP purchase orders stuck in queue','Purchase orders remain pending and the integration worker logs retry errors. No duplicate orders observed.','Found an expired integration credential, rotated it through the approved vault process, replayed queued messages with duplicate checks and verified delivery.','erp integration'),
('Hardware','Docking station loses external displays','Two monitors go blank when the laptop wakes; built-in display works and cables pass swap tests.','Applied the approved dock firmware update and validated three sleep/wake cycles with both monitors.','desktop firmware'),
('Cloud','Container pods repeatedly restart','Checkout staging pods report memory limit errors after the latest release; node health is normal.','Confirmed memory exhaustion in telemetry, rolled back the faulty release with owner approval and verified pod stability.','kubernetes memory'),
('Security','Endpoint reports suspicious attachment','Endpoint protection quarantined an attachment opened by a test user. No evidence yet of lateral movement.','Security team isolated the endpoint with approval, inspected the sample in a sandbox, removed persistence and restored access after a clean scan.','endpoint malware'),
('Network','Branch DNS resolution fails intermittently','Internal hostnames fail to resolve from a branch while direct IP connectivity works. Resolver timeout errors repeat.','Located an unreachable secondary DNS forwarder, corrected its routing under change approval and tested internal and external lookups.','dns routing'),
('Identity','MFA prompts repeat on managed laptop','A managed laptop requests MFA on every browser refresh; the same account works on another managed device.','Confirmed incorrect device time, restored time synchronization and renewed the managed browser session; MFA then behaved normally.','mfa identity'),
('Applications','Reporting dashboard shows stale data','Daily revenue dashboard stopped updating although source transactions continue. The ETL job has failed since midnight.','Found a schema mismatch in the ETL mapping, deployed the reviewed mapping correction and reconciled refreshed totals against the source.','etl sql'),
('Hardware','Office printer queues never complete','Jobs remain in the shared print queue and local test pages print correctly. Multiple users affected.','Found a corrupt spool job, cleared only the approved affected jobs and restarted the spooler in a maintenance window; test jobs passed.','printer desktop'),
('Cloud','Object storage uploads return forbidden','A scheduled backup can list its bucket but new uploads return access denied after a policy deployment.','Compared effective permissions with the approved baseline, restored the missing write permission at the narrow bucket scope and verified a test backup.','iam storage'),
('Security','Certificate expiry warning on internal API','Monitoring reports that the internal API TLS certificate expires within 24 hours. Clients still connect.','Renewed the certificate through the approved certificate authority, deployed the chain and verified expiry and TLS negotiation.','tls certificate'),
('Network','Video meetings suffer packet loss','Calls from the training room show packet loss during afternoon sessions; wired clients perform normally.','Measured wireless channel congestion, applied an approved channel plan and validated packet loss below the agreed threshold.','wifi network'),
('Identity','New starter cannot access shared drive','A provisioned user can sign in but gets access denied on the finance share; access request is approved.','Verified approved group membership had not synchronized, reran the provisioning job and validated least-privilege access.','directory provisioning'),
('Applications','Database connections exhausted','The internal scheduling app returns 503 during a batch run. Database connection count reaches its configured ceiling.','Identified unclosed batch connections, deployed the reviewed pooling fix and verified connection counts returned to baseline.','sql database'),
('Hardware','Laptop battery drains while sleeping','A laptop loses most battery overnight with the lid closed. Battery diagnostics show normal health.','Found an incompatible peripheral waking the system, applied an approved driver update and verified overnight sleep power usage.','desktop driver'),
('Cloud','CI deployment cannot pull image','A deployment job cannot pull a container image; the tag exists and registry health is normal.','Renewed the expired registry identity through the secret manager and reran the approved deployment with digest verification.','container registry'),
('Security','Service account has unexpected permissions','A scheduled access review flags broad permissions on a nonproduction service account. No misuse is confirmed.','Compared grants with the approved role, removed excess privileges after owner sign-off and validated required jobs still run.','iam security'),
('Applications','Email calendar invitations delayed','Meeting invitations reach mailboxes thirty minutes late while ordinary email arrives promptly. Queue metrics are elevated.','Traced delays to a stuck calendar transport worker, restarted it under change approval and verified queue recovery without duplicate invitations.','email queue'),
('Network','Load balancer marks healthy nodes down','Health checks fail after a new path is deployed; direct requests to the application succeed.','Updated the health-check path to the reviewed application endpoint and verified all nodes passed checks before restoring traffic.','loadbalancer network')]
teams=[{'id':uid(100+i),'name':name,'categories':cats,'skills':skills.split(),'capacity':cap} for i,(name,cats,skills,cap) in enumerate([
 ('Network Operations',['Network'],'vpn gateway dns routing wifi network loadbalancer',10),
 ('Identity & Access',['Identity'],'saml sso mfa identity directory provisioning iam',8),
 ('Business Applications',['Applications'],'erp integration etl sql database email queue',12),
 ('Workplace Technology',['Hardware'],'desktop firmware printer driver',10),
 ('Cloud Platform',['Cloud'],'kubernetes memory iam storage container registry',8),
 ('Security Operations',['Security'],'endpoint malware tls certificate iam security',6)])]
base=datetime(2026,10,17,8,0,tzinfo=timezone.utc)
tickets=[]
for i in range(50):
 cat,title,desc,solution,skill=SCENARIOS[i%20]
 resolved=i<20
 priority=['P2','P3','P2','P4','P1'][i%5]
 hours={'P1':4,'P2':8,'P3':24,'P4':72}[priority]
 created=base-timedelta(days=2+i%7,hours=i%5) if resolved else base-timedelta(hours=(i%9)+.5)
 tickets.append({'id':uid(1000+i),'number':1001+i,'title':title+([' — Chennai hub',' — Pune hub',' — Remote workforce'][i//20]),'description':desc+' Fictional training incident; impact and resolution must be verified independently.','category':cat,'priority':priority,'status':'resolved' if resolved else ['open','in_progress','waiting'][i%3],'reporter_id':None,'assigned_team_id':teams[next(j for j,t in enumerate(teams) if cat in t['categories'])]['id'] if i%4 else None,'created_at':created.isoformat(),'sla_due_at':(created+timedelta(hours=hours)).isoformat(),'resolved_at':(created+timedelta(hours=1+i%5)).isoformat() if resolved else None,'solution':solution if resolved else '', 'version':1,'is_sample':True})
(ROOT/'backend/app/seed.json').write_text(json.dumps({'teams':teams,'tickets':tickets},indent=2))
quote=lambda v:"'"+json.dumps(v).replace("'","''")+"'::jsonb"
sql='-- Optional FICTIONAL sample data. Run after migrations. Idempotent.\n'
for t in teams:
 sql+=f"insert into public.teams select * from jsonb_populate_record(null::public.teams,{quote(t)}) on conflict (id) do nothing;\n"
for t in tickets:
 sql+=f"insert into public.tickets select * from jsonb_populate_record(null::public.tickets,{quote(t)}) on conflict (id) do nothing;\n"
sql+="select setval(pg_get_serial_sequence('public.tickets','number'), greatest(1050, (select max(number) from public.tickets)));\n"
(ROOT/'supabase/seed.sql').write_text(sql)
if __name__=='__main__': print('Generated 50 fictional tickets, 20 resolved solutions, and 6 teams.')
