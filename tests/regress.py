import sys,os;sys.argv=['x',os.path.dirname(os.path.dirname(os.path.abspath(__file__)))];sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from harness import *
errs=[];toasts=[];res=[]
def step(name,fn):
    n0=len(toasts)
    try:fn();ok=True;e=''
    except Exception as ex:ok=False;e=str(ex).split('\n')[0][:140]
    bad=[t for t in toasts[n0:] if 'Someone else' in t or 'conflict' in t.lower()]
    res.append((name,ok and not bad,e or (bad[0] if bad else '')))
with sync_playwright() as p:
    br=p.chromium.launch();ctx=new_ctx(br,viewport={'width':1300,'height':900});pg=ctx.new_page();pg.on('pageerror',lambda e:errs.append(str(e)))
    ctx.on('page',lambda q:q.close() if q!=pg else None)
    login(pg)
    pg.expose_function('__toast',lambda t:toasts.append(t));pg.evaluate("(()=>{const o=toast;window.toast=t=>{__toast(String(t));return o(t)}})()")
    pg.add_init_script("")
    sheet_err=lambda:pg.locator('.sheet').inner_text() if pg.locator('.sheet').count() else ''
    def save():
        pg.click('#fsave');pg.wait_for_timeout(900)
        if pg.locator('.sheet').count():
            t=sheet_err();
            if 'Someone else' in t: raise Exception('false conflict')
    # 1 asset edit + in-form upload + save
    def s1():
        open('t.pdf','wb').write(b'%PDF-1.4\n%%EOF')
        pg.evaluate("openDetail('asset','as3')");pg.evaluate("assetForm('as3')");pg.wait_for_selector('.af-files');pg.set_input_files('#af_fup','t.pdf');pg.wait_for_timeout(1200)
        pg.fill('#f_model','AC-75 edited');save()
        assert pg.evaluate("S.assets.as3.model")=='AC-75 edited' and pg.evaluate("S.assets.as3.files.length")>=1
    step('asset edit with upload inside form',s1)
    # 2 move asset
    def s2():
        pg.evaluate("closeLayer('sheet');moveAsset('as4')");pg.wait_for_timeout(400);pg.select_option('#f_location','Meeting room');save()
        assert pg.evaluate("S.assets.as4.location")=='Meeting room'
    step('move asset',s2)
    # 3 WO update twice in a row, complete, verify
    def s3():
        pg.evaluate("woForm('w2')");pg.wait_for_selector('#f_title');pg.fill('#f_tasksDone','Thermocouple replaced');save()
        pg.evaluate("woForm('w2')");pg.wait_for_selector('#f_title');pg.select_option('#f_status','Completed')
        for k in ['chkHygiene','chkSafety','chkIsolated','chkPPE','chkTools','chkClearance']:
            if pg.locator('#f_'+k).count():pg.check('#f_'+k)
        if pg.locator('#f_completedDate').count():pg.fill('#f_completedDate','2026-11-23')
        save();assert pg.evaluate("S.workorders.w2.status")=='Completed',pg.evaluate("S.workorders.w2.status")
        pg.evaluate("verifyForm('w2')");pg.wait_for_timeout(400);pg.fill('#f_verifiedBy','QA demo');save()
        assert pg.evaluate("S.workorders.w2.status")=='Verified'
    step('work order update, complete, QA verify',s3)
    # 4 purchasing: PR submit -> approve -> PO -> receive -> invoice -> invoice edit
    def s4():
        pg.evaluate("go('purchases');purForm()");pg.wait_for_selector('#purLines .pl');pg.fill('#f_purpose','Regression PR')
        r=pg.locator('#purLines .pl').first;r.locator('.pl-p').select_option('p3');r.locator('.pl-q').fill('2')
        if r.locator('.pl-r').input_value()=='':r.locator('.pl-r').fill('22')
        pg.click('text=Submit for approval');pg.wait_for_timeout(1000)
        pid=pg.evaluate("Object.keys(S.purchases).find(k=>S.purchases[k].purpose==='Regression PR')");assert pid
        pg.evaluate(f"purDecide('{pid}','Approved')");pg.wait_for_timeout(400);save()
        assert pg.evaluate(f"S.purchases['{pid}'].status")=='Approved',pg.evaluate(f"S.purchases['{pid}'].status")
        pg.evaluate(f"poForm('{pid}')");pg.wait_for_timeout(500);
        if pg.locator('#f_supplierId').count() and not pg.input_value('#f_supplierId'):pg.select_option('#f_supplierId','sup-d4')
        save();assert pg.evaluate(f"S.purchases['{pid}'].status")=='PO issued',pg.evaluate(f"S.purchases['{pid}'].status")
        pg.evaluate(f"recvForm('{pid}')");pg.wait_for_timeout(500);save()
        assert pg.evaluate(f"S.purchases['{pid}'].status") in ('Received','Partly received'),pg.evaluate(f"S.purchases['{pid}'].status")
        pg.evaluate(f"invForm('{pid}')");pg.wait_for_timeout(400);pg.fill('#f_invNo','INV-1');pg.fill('#f_sapRef','PU-1');save()
        pg.evaluate(f"invForm('{pid}')");pg.wait_for_timeout(400);pg.fill('#f_invNo','INV-2');save()
        assert pg.evaluate(f"S.purchases['{pid}'].inv.invNo")=='INV-2'
    step('purchase PR → approve → PO → receive → invoice → invoice edit',s4)
    # 5 stock issue
    def s5():
        q0=pg.evaluate("S.parts.p1.qty");pg.evaluate("openDetail('part','p1')");pg.wait_for_timeout(300)
        pg.click('text=Issue / use');pg.wait_for_timeout(400);pg.locator('.sheet input[type=number]').first.fill('1');save()
        assert pg.evaluate("S.parts.p1.qty")==q0-1
    step('stock issue',s5)
    # 6 D/O send + collect
    def s6():
        pg.evaluate("openDetail('asset','as8')");pg.click('#dSO');pg.wait_for_selector('#soItems');pg.select_option('#f_supplierId','sup-d4');save()
        did=pg.evaluate("Object.keys(S.sendouts)[0]");pg.evaluate(f"openDetail('sendout','{did}')");pg.click('#soC');pg.wait_for_selector('.so-col');save()
        assert pg.evaluate(f"S.sendouts['{did}'].status")=='Collected' and pg.evaluate("S.assets.as8.status")=='Active'
    step('D/O send and collect',s6)
    # 7 calibration external record
    def s7():
        pg.evaluate("closeLayer('drawer');calRecord('ws1','External')");pg.wait_for_timeout(600)
        rs=pg.locator('#calBox .cr-r')
        for i,v in enumerate(['1.004','3.006','6.008'][:rs.count()]):rs.nth(i).fill(v)
        save();assert pg.evaluate("Object.values(S.workorders).some(w=>w.assetId==='ws1'&&w.type==='Calibration')")
    step('calibration record',s7)
    # 8 incident update + contract renewal
    def s8():
        pg.evaluate("incForm('i1')");pg.wait_for_timeout(500);pg.fill('#f_rootCause','Blade change without gloves');save()
        assert 'gloves' in pg.evaluate("S.incidents.i1.rootCause||''")
    step('incident update',s8)
    def s9():
        pg.evaluate("conForm('c1')");pg.wait_for_timeout(400);pg.fill('#f_notes','reviewed');save()
        assert pg.evaluate("S.contracts.c1.notes")=='reviewed'
    step('contract edit',s9)
    # 10 settings: add location via saveSettings twice
    def s10():
        pg.evaluate("saveSettings({uomList:[...S.settings.uomList,'BOX9']})");pg.wait_for_timeout(600)
        pg.evaluate("saveSettings({uomList:[...S.settings.uomList,'BOX10']})");pg.wait_for_timeout(600)
        assert 'BOX10' in pg.evaluate("S.settings.uomList")
    step('settings saved twice',s10)
    # 11 part delete blocked when on open PO
    def s11():
        pg.evaluate("openDetail('part','p1');partForm('p1')");pg.wait_for_timeout(400)
        n0=len(toasts);pg.click('text=Delete part');pg.wait_for_timeout(400)
        assert any('Cannot delete' in t for t in toasts[n0:]),toasts[n0:]
    step('part delete blocked when on open PO',s11)
    # 12 idle sync does not re-render constantly
    def s12():
        pg.evaluate("closeLayer('sheet');closeLayer('drawer');go('assets')");pg.evaluate('sync()');pg.wait_for_timeout(800);pg.evaluate("window.__r=0;const o=renderList;window.renderList=function(){window.__r++;return o.apply(this,arguments)};0")
        for _ in range(3):pg.evaluate("sync()");pg.wait_for_timeout(500)
        n=pg.evaluate("window.__r");assert n==0,('re-rendered',n)
    step('idle sync quiet',s12)
    for r in res:print(('PASS ' if r[1] else 'FAIL ')+r[0]+('' if r[1] else '  -> '+r[2]))
    print('page errors:',errs[:5])
