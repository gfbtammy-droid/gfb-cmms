import sys,os;sys.argv=['x',os.path.dirname(os.path.dirname(os.path.abspath(__file__)))];sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from harness import *
errs=[];out=[]
def toasts(pg):return pg.evaluate("window.__t||[]")
def hook(pg):pg.evaluate("(()=>{window.__t=[];const o=toast;window.toast=t=>{window.__t.push(String(t));return o(t)}})()")
with sync_playwright() as p:
    br=p.chromium.launch()
    # --- approver (admin) ---
    ctx=new_ctx(br,viewport={'width':1300,'height':900});pg=ctx.new_page();pg.on('pageerror',lambda e:errs.append(str(e)));ctx.on('page',lambda q:q.close() if q!=pg else None);login(pg);hook(pg)
    # approve pu1 then issue PO with other charges pushing above approved -> approver re-approves
    pg.evaluate("purDecide('pu1','Approved')");pg.wait_for_timeout(300);pg.click('#fsave');pg.wait_for_timeout(800)
    ap=pg.evaluate("S.purchases.pu1.approval.total");pg.evaluate("poForm('pu1')");pg.wait_for_timeout(400);pg.fill('#f_other','25');pg.wait_for_timeout(200)
    out.append(('PO note shows total incl. other', 'other charges / tax' in pg.inner_text('#poTotNote') and 'above the approved' in pg.inner_text('#poTotNote')))
    pg.click('#fsave');pg.wait_for_timeout(900);pu=pg.evaluate("S.purchases.pu1")
    out.append(('approver: PO issued and re-approved incl. other', pu['status']=='PO issued' and 'Re-approved' in (pu['approval'].get('note') or '')))
    # CSV cell sanitising
    out.append(('CSV formula neutralised', pg.evaluate("[csvCell('=HYPERLINK(1)'),csvCell('-5'),csvCell('+60123'),csvCell('ok')].join('|')")=="'=HYPERLINK(1)|-5|'+60123|ok"))
    # D/O with an asset update that fails -> warning toast
    pg.evaluate("""(()=>{const o=sb.rpc;sb.rpc=async(fn,a)=>{if(fn==='save_doc'&&a.p_coll==='assets'&&a.p_id==='as3')return{data:null,error:{message:'simulated failure'}};return o(fn,a)}})()""")
    pg.evaluate("openDetail('asset','as3')");pg.click('#dSO');pg.wait_for_selector('#soItems');pg.select_option('#f_supplierId','sup-d4');pg.click('#fsave');pg.wait_for_timeout(2600)
    out.append(('D/O warns when an asset could not be updated', any('were not updated: AS-0003' in t for t in toasts(pg))))
    # collection note still works (with sync before numbering)
    did=pg.evaluate("Object.keys(S.sendouts)[0]");pg.evaluate(f"openDetail('sendout','{did}')");pg.click('#soC');pg.wait_for_selector('.so-col');pg.click('#fsave');pg.wait_for_timeout(1200)
    out.append(('collection note saved',pg.evaluate(f"(S.sendouts['{did}'].collections||[]).length")==1))
    # --- non-approver (tech) ---
    ctx2=new_ctx(br,viewport={'width':1300,'height':900});q=ctx2.new_page();q.on('pageerror',lambda e:errs.append(str(e)));ctx2.on('page',lambda z:z.close() if z!=q else None);login(q,'tech@demo.my');hook(q)
    # pu2 is PO issued (approved 265): raise other charges -> blocked
    q.evaluate("poForm('pu2')");q.wait_for_timeout(400);q.fill('#f_other','100');q.click('#fsave');q.wait_for_timeout(800)
    out.append(('non-approver cannot push issued PO above approval','Ask an approver' in (q.locator('.sheet').inner_text() if q.locator('.sheet').count() else '')))
    q.evaluate("closeLayer('sheet')")
    # orphan part note: PR with a new item, PR save fails
    q.evaluate("""(()=>{const o=sb.rpc;sb.rpc=async(fn,a)=>{if(fn==='save_doc'&&a.p_coll==='purchases')return{data:null,error:{message:'simulated PR failure'}};return o(fn,a)}})()""")
    q.evaluate("go('purchases');purForm()");q.wait_for_selector('#purLines .pl');q.fill('#f_purpose','Orphan test')
    r=q.locator('#purLines .pl').first;r.locator('.pl-p').select_option('__new');r.locator('.pl-c').select_option(index=2);r.locator('.pl-d').fill('Test gasket XYZ');r.locator('.pl-q').fill('1');r.locator('.pl-u').select_option('PCS');r.locator('.pl-r').fill('5')
    q.click('text=Submit for approval');q.wait_for_timeout(1500)
    note=q.evaluate("(Object.values(S.parts).find(p=>p.name==='Test gasket XYZ')||{}).notes||''")
    out.append(('orphan part gets an explanatory note','was not saved' in note))
    for n,ok in out:print(('PASS ' if ok else 'FAIL ')+n)
    print('page errors',errs[:4])
