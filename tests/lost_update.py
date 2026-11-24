import sys,os;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from harness import *
errs=[]
with sync_playwright() as p:
    br=p.chromium.launch();ctx=new_ctx(br,viewport={'width':1280,'height':900});pg=ctx.new_page();pg.on('pageerror',lambda e:errs.append(str(e)));login(pg)
    # User A opens WO w3 edit form
    pg.evaluate("openDetail('wo','w3')");pg.wait_for_timeout(300);pg.evaluate("woForm('w3')");pg.wait_for_selector('#f_title')
    # User B (another browser) changes the same WO: status + technician
    pg.evaluate("""sb.rpc('save_doc',{p_coll:'workorders',p_id:'w3',p_data:{...S.workorders.w3,status:'In progress',technician:'Changed by user B'},p_act:'B: started job',p_base:S.workorders.w3.updatedAt})""")
    pg.evaluate("sync()");pg.wait_for_timeout(1500)   # A's background sync picks up B's change
    print('in memory after sync:',pg.evaluate("[S.workorders.w3.status,S.workorders.w3.technician]"))
    # User A edits only the title and saves
    pg.fill('#f_title','Aircond leaking water in office (edited by A)');pg.click('#fsave');pg.wait_for_timeout(1500)
    msg=pg.locator('.sheet .err, .ferr, .form-err').all_inner_texts() if pg.locator('.sheet').count() else []
    print('form still open:',pg.locator('.sheet').count()>0,'| message:',msg[:1])
    pg.evaluate("sync()");pg.wait_for_timeout(800)
    print('saved record:',pg.evaluate("[S.workorders.w3.title,S.workorders.w3.status,S.workorders.w3.technician]"))
    print('errors',errs)
