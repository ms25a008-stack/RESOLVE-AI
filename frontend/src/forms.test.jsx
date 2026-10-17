import React from 'react';
import {describe,it,expect,vi,afterEach} from 'vitest';
import {render,screen,cleanup,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
vi.mock('react-dom/client',()=>({createRoot:()=>({render:()=>{}})}));
vi.mock('./api',()=>({api:vi.fn(),supabase:null}));
import {TicketForm} from './main';
afterEach(cleanup);
describe('Ticket submission',()=>{
 it('sends entered fields and priority to the save handler',async()=>{
 const save=vi.fn();render(<TicketForm onSave={save} onClose={()=>{}}/>); const u=userEvent.setup();
 await u.type(screen.getByLabelText('Issue title'),'VPN disconnecting');
 await u.type(screen.getByLabelText('Description & impact'),'VPN disconnects every ten minutes during remote work.');
 await u.selectOptions(screen.getByLabelText('Initial category'),'Network');
 await u.selectOptions(screen.getByLabelText('Priority'),'P2');
 await u.click(screen.getByRole('button',{name:'Create ticket'}));
 expect(save).toHaveBeenCalledWith({title:'VPN disconnecting',description:'VPN disconnects every ten minutes during remote work.',category:'Network',priority:'P2'});
 });
 it('preserves input and exposes save failures',async()=>{
 render(<TicketForm onSave={async()=>{throw new Error('Database unavailable')}} onClose={()=>{}}/>);const u=userEvent.setup();
 await u.type(screen.getByLabelText('Issue title'),'Printer unavailable');
 await u.type(screen.getByLabelText('Description & impact'),'The shared printer has been offline since this morning.');
 await u.click(screen.getByRole('button',{name:'Create ticket'}));
 expect((await screen.findByRole('alert')).textContent).toContain('Database unavailable');
 expect(screen.getByLabelText('Issue title').value).toBe('Printer unavailable');
 });
});
