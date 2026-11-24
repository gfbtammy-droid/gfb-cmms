import sys,os;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from harness import *
with sync_playwright() as p:
    br=p.chromium.launch();ctx=new_ctx(br);pg=ctx.new_page();errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
    login(pg)
    def run(user):
        pg.evaluate(f"S.me.username='{user}'")
        pg.evaluate("dspForm(null,{assetId:'as4'})");pg.wait_for_selector('#f_damageDesc');pg.fill('#f_damageDesc','Compressor dead');pg.fill('#f_picName','X');pg.click('#fsave');pg.wait_for_timeout(1000)
        did=pg.evaluate("Object.entries(S.disposals).find(([k,o])=>o.assetId==='as4'&&o.status==='Reported')[0]")
        pg.click('#dspC');pg.wait_for_timeout(500)
        if pg.locator('#f_method').count():pg.click('#fsave');pg.wait_for_timeout(900)
        r=(pg.evaluate(f"S.disposals['{did}'].status"),pg.evaluate("S.assets.as4.status"))
        if r[0]=='Reported':pg.evaluate(f"(async()=>{{await put('disposals','{did}',{{...S.disposals['{did}'],status:'Cancelled'}},'x');await put('assets','as4',{{...S.assets.as4,status:'Active'}},'x')}})()");pg.wait_for_timeout(600)
        return r
    print('other user (photo required):',run('admin@demo.my'))
    print('tammy (photo optional):',run('tammyng@gfbfood.com'))
    print('errors',errs)
