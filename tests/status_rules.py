import sys,os;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from harness import *
res=[]
def ok(n,c,info=''):res.append(('PASS' if c else 'FAIL',n,info))
with sync_playwright() as p:
    br=p.chromium.launch(args=['--lang=en-GB']);ctx=new_ctx(br);pg=ctx.new_page();errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
    login(pg)
    st=lambda a:pg.evaluate(f"S.assets['{a}'].status")
    def save():pg.click('#fsave');pg.wait_for_timeout(1000)
    # 1 new breakdown WO -> hold ; second WO ; complete first keeps hold ; complete second -> Active
    ok('status list',pg.evaluate("ASSET_STATUS.join('|')")=='Active|Inactive|Damaged|On hold for repair|Under calibration|Disposed')
    for t in ['Belt slipping','Bearing noise']:
        pg.evaluate("go('wos');woForm(null,{assetId:'as1'})");pg.wait_for_selector('#f_title');pg.select_option('#f_type','Breakdown / repair');pg.fill('#f_title',t);save()
    ok('WO sets hold',st('as1')=='On hold for repair',st('as1'))
    ids=pg.evaluate("Object.entries(S.workorders).filter(([k,w])=>w.assetId==='as1'&&w.type==='Breakdown / repair'&&!['Completed','Verified'].includes(w.status)).map(x=>x[0])")
    def complete(wid):
        pg.evaluate(f"woForm('{wid}')");pg.wait_for_selector('#f_title');pg.select_option('#f_status','Completed')
        if pg.locator('#f_completedDate').count():pg.fill('#f_completedDate','2026-11-23')
        pg.fill('#f_tasksDone','Fixed')
        for c in ['chkHygiene','chkSafety','chkIsolated','chkPPE','chkTools','chkClearance']:
            if pg.locator('#f_'+c).count():pg.check('#f_'+c)
        save()
    complete(ids[0]);ok('one of two done keeps hold',st('as1')=='On hold for repair',st('as1'))
    complete(ids[1]);ok('both done -> Active',st('as1')=='Active',st('as1'))
    # 2 incident with machine -> hold; with assetOk -> stays
    def inc(asset,okbox):
        pg.evaluate(f"go('incidents');incForm(null,{{assetId:'{asset}',category:'Property / equipment damage only'}})");pg.wait_for_selector('#f_title')
        pg.fill('#f_title','Test damage');pg.fill('#f_description','Guard bent')
        if okbox:pg.check('#f_assetOk')
        save()
    inc('as3',False);ok('incident sets hold',st('as3')=='On hold for repair',st('as3'))
    inc('as8',True);ok('incident with safe tick stays Active',st('as8')=='Active',st('as8'))
    # 3 DOSH decision
    iid=pg.evaluate("Object.entries(S.incidents).find(([k,i])=>i.title==='Test damage'&&i.assetId==='as3')[0]")
    ok('decision needed pill',"decision needed" in pg.evaluate(f"doshPill(S.incidents['{iid}'])"))
    pg.evaluate(f"incForm('{iid}')");pg.wait_for_selector('#f_title');pg.select_option('#f_status','Closed');pg.fill('#f_investigatedBy','SO');pg.click('#fsave');pg.wait_for_timeout(800)
    err=pg.evaluate("(document.querySelector('.sheet .err, .sheet .ferr, .sheet [role=alert]')||{}).textContent||''")
    ok('close blocked without decision','Safety Officer' in err,err)
    pg.select_option('#f_doshDecision','Yes – JKKP 6');pg.select_option('#f_status','Under investigation');save()
    pill=pg.evaluate(f"doshPill(S.incidents['{iid}'])");ok('Yes shows due/overdue pill','JKKP 6' in pill,pill)
    # 4 D/O calibration -> Under calibration ; collect -> Active + In use
    pg.evaluate("go('sendouts');soForm(null,{purpose:'Calibration',supplierId:'sup-d2',items:[soItemFromAsset('ws1')],expectedReturn:'2026-12-07'})");pg.wait_for_timeout(600)
    pg.evaluate("window.open=()=>({document:{write(){},close(){}},focus(){},print(){}})");save()
    ok('cal D/O -> Under calibration',st('ws1')=='Under calibration',st('ws1'))
    so=pg.evaluate("Object.entries(S.sendouts).find(([k,o])=>o.items.some(i=>i.assetId==='ws1')&&o.status==='Sent')[0]")
    pg.evaluate(f"soCollect('{so}')");pg.wait_for_timeout(600)
    if pg.locator('#f_collectedBy').count():pg.fill('#f_collectedBy','Driver')
    save()
    ok('collect -> Active',st('ws1')=='Active',st('ws1'));ok('calStatus In use',pg.evaluate("S.assets.ws1.calStatus")=='In use',pg.evaluate("S.assets.ws1.calStatus"))
    # 5 repair D/O -> hold
    pg.evaluate("go('sendouts');soForm(null,{purpose:'Repair',supplierId:'sup-d4',items:[soItemFromAsset('as5')],expectedReturn:'2026-12-07'})");pg.wait_for_timeout(600);save()
    ok('repair D/O -> hold',st('as5')=='On hold for repair',st('as5'))
    pg.evaluate("go('assets')");pg.wait_for_timeout(400)
    ok('status filter options',pg.evaluate("[...document.querySelectorAll('select option')].map(o=>o.value).includes('On hold for repair')"))
    pg.screenshot(path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'out')+'/status_assets.png')
    print('errors',errs)
for r in res:print(*r)
