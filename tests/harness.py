import os,mimetypes
from playwright.sync_api import sync_playwright
import sys as _s
HERE=os.path.dirname(os.path.abspath(__file__));REPO=_s.argv[1] if len(_s.argv)>1 and _s.argv[1].startswith('/') else os.path.dirname(HERE)
ORIGIN='https://demo.local/gfb-cmms/'
FAKE=open(os.path.join(HERE,'demo-data.js')).read()+'\n'+open(os.path.join(HERE,'fake-supabase.js')).read()
CONFIG="window.GFB_CONFIG={supabaseUrl:'https://demo.invalid',supabaseAnonKey:'demo-key',companyName:'GFB Food Sdn Bhd'};"
blocked=[]
def handler(route):
    url=route.request.url
    if not url.startswith(ORIGIN):
        if url.startswith('data:') or url.startswith('blob:') or url.startswith('https://fonts.googleapis.com/') or url.startswith('https://fonts.gstatic.com/'):return route.continue_()
        blocked.append(url);return route.abort()
    path=url[len(ORIGIN):].split('?')[0].split('#')[0] or 'index.html'
    if path=='supabase.js':return route.fulfill(status=200,content_type='application/javascript',body=FAKE)
    if path=='config.js':return route.fulfill(status=200,content_type='application/javascript',body=CONFIG)
    if path=='demo-photo.jpg':return route.fulfill(status=200,content_type='image/jpeg',body=open(os.path.join(HERE,'demo-photo.jpg'),'rb').read())
    f=os.path.join(REPO,path)
    if os.path.isfile(f):return route.fulfill(status=200,content_type=mimetypes.guess_type(f)[0] or 'application/octet-stream',body=open(f,'rb').read())
    return route.fulfill(status=404,body='')
def new_ctx(br,**kw):
    kw.setdefault('locale','en-GB');kw.setdefault('timezone_id','Asia/Kuala_Lumpur');ctx=br.new_context(**kw);ctx.route('**/*',handler);return ctx
def login(pg,email='admin@demo.my'):
    pg.goto(ORIGIN);pg.wait_for_selector('#lf')
    try:pg.click('[data-lang=en]',timeout=1500)
    except Exception:pass
    pg.fill('#l_user',email);pg.fill('#l_pass','demo-password');pg.click('#lf button[type=submit]');pg.wait_for_function('typeof S!=="undefined"&&S.ready&&S.me',timeout=15000);pg.wait_for_timeout(600)
