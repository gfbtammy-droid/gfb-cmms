// Stand-in for supabase-js used only for user-guide screenshots. Serves made-up demo data from window.__DEMO; never contacts any server.
(function(){
const D=window.__DEMO;let _t=Date.now();const now=()=>{_t=Math.max(_t+1,Date.now());return new Date(_t).toISOString()};
let seq=100;const docs=new Map();const tomb=[];
const put=(coll,id,data)=>docs.set(coll+'/'+id,{coll,id,data,seq:++seq});
D.docs.forEach(d=>put(d.coll,d.id,d.data));
let sessEmail=null;try{sessEmail=sessionStorage.getItem('demoUser')}catch(e){}
const me=()=>D.profiles.find(p=>p.email===sessEmail)||null;
const clone=o=>JSON.parse(JSON.stringify(o));
function query(table){const st={};const b={
  select(){return b},gt(c,v){st.gt=[c,v];return b},order(c){st.order=c;return b},range(a,z){st.range=[a,z];return b},eq(c,v){st.eq=[c,v];return b},
  then(res,rej){let data=table==='docs'?[...docs.values()].map(clone):table==='tombstones'?tomb.slice():table==='profiles'?clone(D.profiles):[];
    if(st.gt)data=data.filter(r=>+r[st.gt[0]]>+st.gt[1]);if(st.eq)data=data.filter(r=>r[st.eq[0]]===st.eq[1]);
    if(st.order)data.sort((x,y)=>x[st.order]>y[st.order]?1:x[st.order]<y[st.order]?-1:0);
    if(st.range)data=data.slice(st.range[0],st.range[1]+1);
    return Promise.resolve({data,error:null}).then(res,rej)}};return b}
function saveDoc(coll,id,data,act){const k=coll+'/'+id,prev=docs.get(k);const p=me();const t=now();
  const h=((prev&&prev.data.history)||[]).concat([{at:t,by:p&&p.id,name:p&&p.name,act:act||'Saved'}]);
  const body=Object.assign({},data,{history:h,updatedAt:t,updatedBy:p&&p.name,createdAt:(prev&&prev.data.createdAt)||t,createdBy:(prev&&prev.data.createdBy)||(p&&p.name)});
  put(coll,id,body);return body}
const RPC={
  my_profile:()=>me(),
  me_can_approve:()=>!!(me()&&me().can_approve),
  save_doc:a=>{const pv=docs.get(a.p_coll+'/'+a.p_id);if(pv&&(a.p_base??null)!==pv.data.updatedAt)return{conflict:true,current:clone(pv.data)};if(!pv&&a.p_base!=null)return{conflict:true,current:null};let d=clone(a.p_data);if(a.p_coll==='purchases'&&d.approval&&!d.approval.at){const p=me();d.approval=Object.assign({},d.approval,{by:p.id,name:p.name,at:now()})}return{doc:saveDoc(a.p_coll,a.p_id,d,a.p_act)}},
  delete_doc:a=>{docs.delete(a.p_coll+'/'+a.p_id);tomb.push({coll:a.p_coll,id:a.p_id,seq:++seq});return{ok:true}},
  stock_move:a=>{const r=docs.get('parts/'+a.p_id);const d=clone(r.data);const p=me();const q=a.p_type==='Adjust'?(+a.p_count-(+d.qty||0)):+a.p_delta;d.qty=(+d.qty||0)+q;
    d.moves=(d.moves||[]).concat([{at:now(),by:p.id,name:p.name,type:a.p_type,qty:q,bal:d.qty,date:a.p_date,ref:a.p_ref,note:a.p_note}]);return{doc:saveDoc('parts',a.p_id,d,a.p_type+' '+q)}},
  po_receive:a=>{const r=docs.get('purchases/'+a.p_id);const d=clone(r.data);const p=me();d.receipts=(d.receipts||[]).concat([{at:now(),by:p.id,name:p.name,date:a.p_date,doNo:a.p_do,note:a.p_note,lines:a.p_lines}]);d.status='Received';return{doc:saveDoc('purchases',a.p_id,d,'Goods received')}},
  admin_update_user:()=>({ok:true}),import_docs:a=>({imported:a.p_docs.length})};
const listeners=[];
const auth={
  getSession:async()=>({data:{session:me()?{user:{id:me().id,email:me().email}}:null}}),
  getUser:async()=>({data:{user:me()?{id:me().id,email:me().email}:null}}),
  signInWithPassword:async({email})=>{if(!D.profiles.find(p=>p.email===email))return{error:{message:'Invalid login credentials'}};sessEmail=email;try{sessionStorage.setItem('demoUser',email)}catch(e){}return{data:{},error:null}},
  signOut:async()=>{sessEmail=null;try{sessionStorage.removeItem('demoUser')}catch(e){}return{error:null}},
  signUp:async()=>({data:{},error:null}),resetPasswordForEmail:async()=>({error:null}),updateUser:async()=>({error:null}),
  onAuthStateChange:cb=>{listeners.push(cb);return{data:{subscription:{unsubscribe(){}}}}}};
const storage={from:()=>({
  upload:async()=>({error:null}),remove:async()=>({error:null}),
  createSignedUrls:async paths=>({data:paths.map(p=>({path:p,signedUrl:(D.files&&D.files[p])||'demo-photo.jpg'})),error:null}),
  createSignedUrl:async p=>({data:{signedUrl:(D.files&&D.files[p])||'demo-photo.jpg'},error:null})})};
window.supabase={createClient:()=>({auth,storage,from:query,rpc:async(fn,args)=>{try{const f=RPC[fn];if(!f)return{data:null,error:{message:'demo: no rpc '+fn}};return{data:f(args||{}),error:null}}catch(e){return{data:null,error:{message:String(e)}}}}})};
})();
