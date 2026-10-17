import React from 'react';
import {it,expect,vi,afterEach} from 'vitest';
import {render,screen,cleanup} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
vi.mock('react-dom/client',()=>({createRoot:()=>({render:()=>{}})}));
vi.mock('./api',()=>({api:vi.fn(),supabase:null}));
import {api} from './api';
import {App,TicketForm} from './main';
const ticket={id:'t1',number:1001,title:'VPN disconnects',description:'VPN disconnects during remote sessions.',category:'Network',priority:'P2',status:'open',version:1,created_at:'2026-10-17T08:00:00Z',sla_due_at:'2026-10-17T16:00:00Z',sla:{state:'at_risk',minutes_remaining:30,elapsed_percent:90,reason:'Deadline near'}};
afterEach(()=>{cleanup();vi.resetAllMocks()});
it('loads the dashboard, filters the queue and displays real analysis errors',async()=>{
 api.mockImplementation(async path=>{
  if(path==='/health')return {mode:'demo'};
  if(path==='/me')return {role:'engineer',email:'demo@example.test'};
  if(path==='/tickets')return [ticket];
  if(path==='/teams')return [];
  if(path==='/tickets/t1')return {ticket,recommendations:[],history:[],decisions:[]};
  if(path==='/tickets/t1/context')return {sources:[],resolvers:[]};
  if(path==='/tickets/t1/analyze')throw new Error('Gemini is not configured.');
  throw new Error('Unexpected endpoint '+path);
 });
 render(<App/>);const u=userEvent.setup();
 await screen.findByText('Your resolution overview');
 await u.click(screen.getByRole('button',{name:'Ticket queue',exact:true}));
 await u.type(screen.getByLabelText('Search tickets'),'printer');
 expect(screen.getByText('No tickets match this view.')).toBeTruthy();
 await u.clear(screen.getByLabelText('Search tickets'));
 await u.click(screen.getByRole('button',{name:'Open incident 1001'}));
 await u.click(await screen.findByRole('button',{name:'Analyze with Gemini'}));
 expect((await screen.findByRole('alert')).textContent).toContain('Gemini is not configured');
 expect(screen.queryByRole('button',{name:'Approve routing & plan'})).toBeNull();
});
it('supports keyboard dismissal of the intake dialog',async()=>{
 const close=vi.fn();render(<TicketForm onSave={vi.fn()} onClose={close}/>);
 await userEvent.setup().keyboard('{Escape}');
 expect(close).toHaveBeenCalledOnce();
});
