import {createClient} from '@supabase/supabase-js';
export const supabase = import.meta.env.VITE_SUPABASE_URL && import.meta.env.VITE_SUPABASE_ANON_KEY ? createClient(import.meta.env.VITE_SUPABASE_URL, import.meta.env.VITE_SUPABASE_ANON_KEY) : null;
export async function api(path, options={}) {
  const session = supabase ? (await supabase.auth.getSession()).data.session : null;
  const controller=new AbortController(); const timer=setTimeout(()=>controller.abort(),90000);
  try {
    const response = await fetch(`/api${path}`,{...options,signal:controller.signal,headers:{'Content-Type':'application/json',...(session?{Authorization:`Bearer ${session.access_token}`}:{})},body:options.body?JSON.stringify(options.body):undefined});
    const data=await response.json().catch(()=>({detail:'Unexpected server response. Check deployment configuration.'}));
    if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:'Please check the form fields and try again.');
    return data;
  } catch(e) {if(e.name==='AbortError') throw new Error('The request timed out. Refresh to check whether it saved before retrying.'); throw e;} finally {clearTimeout(timer);}
}
