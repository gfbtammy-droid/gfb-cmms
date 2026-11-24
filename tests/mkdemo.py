import os
import json,datetime as dt
T=dt.date(2026,11,17)
def d(n):return (T+dt.timedelta(days=n)).isoformat()
def ts(n,h=9):return (dt.datetime(T.year,T.month,T.day,h,0)+dt.timedelta(days=n)).isoformat()+'.000Z'
ADMIN='00000000-0000-4000-8000-000000000001';QA='00000000-0000-4000-8000-000000000002';TECH='00000000-0000-4000-8000-000000000003';VIEW='00000000-0000-4000-8000-000000000004';NEW='00000000-0000-4000-8000-000000000005'
profiles=[
 dict(id=ADMIN,email='admin@demo.my',name='Demo Admin',role='admin',active=True,incident_access=True,can_approve=True,created_at='2026-10-01T02:00:00Z'),
 dict(id=QA,email='qa@demo.my',name='QA Executive (demo)',role='editor',active=True,incident_access=True,can_approve=False,created_at='2026-10-02T02:00:00Z'),
 dict(id=TECH,email='tech@demo.my',name='Technician (demo)',role='editor',active=True,incident_access=False,can_approve=False,created_at='2026-10-03T02:00:00Z'),
 dict(id=VIEW,email='viewer@demo.my',name='Supervisor (demo)',role='viewer',active=True,incident_access=False,can_approve=False,created_at='2026-10-05T02:00:00Z'),
 dict(id=NEW,email='newstaff@demo.my',name='New Staff (demo)',role='viewer',active=False,incident_access=False,can_approve=False,created_at=ts(-1).replace('.000Z','Z'))]
def H(act,n=-30,who='Demo Admin',by=ADMIN):return [dict(at=ts(n),by=by,name=who,act=act)]
docs=[]
def add(coll,id,data,n=-30):
    data.setdefault('history',H('Created',n));data.setdefault('createdAt',ts(n));data.setdefault('createdBy','Demo Admin');data.setdefault('updatedAt',ts(n));data.setdefault('updatedBy','Demo Admin')
    docs.append(dict(coll=coll,id=id,data=data))
locs=[('Mixing room','Production'),('Packing room 1','Production'),('Packing room 2','Production'),('Raw material store','Warehouse'),('Finished goods store','Warehouse'),('QC lab','QA / QC'),('General office','Office / Admin'),('Meeting room','Office / Admin'),('Server / IT room','Office / Admin'),('Utility area','Facility / utilities')]
add('config','settings',dict(locList=[dict(name=a,dept=b) for a,b in locs],
  poDoc=dict(address='No. 1, Jalan Contoh 1/1, Taman Demo, 40000 Shah Alam, Selangor',phone='03-0000 0000',fax='',email='purchasing@example.com',regNo='000000-X (demo)',sstNo='',tin='',terms='30 days',deliverTo='Main factory (demo address)',prep='',footer='This is a computer-generated purchase order.'),
  cal=dict(lead=30,rule='error')))
# suppliers
S=[('sup-d1','Contoh Aircond Services','Contractor (service)','Approved','Aircond servicing'),
   ('sup-d2','Sample Calibration Lab Sdn Bhd','Contractor (service)','Approved','Calibration & stamping'),
   ('sup-d3','Demo Electrical Works','Contractor (service)','Under evaluation','Electrical / wiring'),
   ('sup-d4','Example Industrial Supply','Vendor (parts)','Approved','Bearings, belts, seals'),
   ('sup-d5','Mock Pest Control Services','Contractor (service)','Approved','Pest control')]
for i,(id,nm,kind,ap,sv) in enumerate(S):
    add('suppliers',id,dict(name=nm,kind=kind,approval=ap,services=sv,contact='Mr Demo '+str(i+1),phone='012-000 000'+str(i),email=f'contact{i+1}@example.com',evalDue=d(120+i*30),safetyBriefed=d(-60) if i!=2 else '',notes='',files=[]))
# assets
def asset(id,code,name,cat,dept,loc,**k):
    a=dict(code=code,name=name,category=cat,dept=dept,location=loc,status=k.pop('status','Active'),criticality=k.pop('criticality','Medium'),foodContact=k.pop('foodContact',False),
      manufacturer=k.pop('manufacturer',''),model=k.pop('model',''),serial=k.pop('serial',''),supplierId=k.pop('supplierId',''),purchaseDate=k.pop('purchaseDate','2022-03-15'),installDate=k.pop('installDate',''),
      warrantyUntil=k.pop('warrantyUntil',''),assignedTo='',faNo=k.pop('faNo',code),pmInterval=k.pop('pmInterval',''),lastPM=k.pop('lastPM',''),pmTasks=k.pop('pmTasks',''),notes=k.pop('notes',''),files=k.pop('files',[]))
    a.update(k);add('assets',id,a)
asset('as1','AS-0001','Ribbon mixer 500 kg (demo)','Production machine','Production','Mixing room',criticality='High',foodContact=True,manufacturer='Demo Machinery',model='RM-500',serial='DM2201',supplierId='sup-d4',pmInterval='90',lastPM=d(-100),pmTasks='Check gearbox oil\nInspect shaft seals\nTighten ribbon bolts\nClean and sanitise bowl',installDate='2022-04-01',files=[dict(id='assets/as1/photo.jpg',name='mixer-photo.jpg',ct='image/jpeg',size=120000,kind='Photo',at=ts(-200),by='Demo Admin'),dict(id='assets/as1/spec.pdf',name='RM-500 spec sheet.pdf',ct='application/pdf',size=380000,kind='Product spec sheet',at=ts(-200),by='Demo Admin')])
asset('as2','AS-0002','Vertical form-fill-seal packing machine (demo)','Production machine','Production','Packing room 1',criticality='High',foodContact=True,manufacturer='Example Pack',model='VFS-300',serial='EP1180',pmInterval='30',lastPM=d(-12),pmTasks='Clean sealing jaws\nCheck film tension\nLubricate guides (food-grade)')
asset('as3','AS-0003','Air compressor 7.5 kW (demo)','Utilities & facility','Facility / utilities','Utility area',pmInterval='90',lastPM=d(-80),pmTasks='Drain condensate\nChange air filter\nCheck belt tension')
asset('as4','AS-0004','Split aircond 2.0 HP – office (demo)','Air-conditioning','Office / Admin','General office',supplierId='sup-d1',pmInterval='90',lastPM=d(-95),criticality='Low')
asset('as5','AS-0005','Forklift 2.5 t (demo)','Material handling (forklift / reach truck)','Warehouse','Finished goods store',pmInterval='180',lastPM=d(-150),serial='FL-25-001')
asset('as6','AS-0006','Laptop – admin (demo)','Computer & IT','Office / Admin','General office',criticality='Low',assignedTo='Admin clerk')
asset('as7','AS-0007','Dust collector (demo)','Production equipment','Production','Mixing room',pmInterval='30',lastPM='',status='On hold for repair')
asset('as8','AS-0008','Chiller unit (demo)','Utilities & facility','Facility / utilities','Utility area',pmInterval='180',lastPM=d(-40))
# calibration instruments
def inst(id,code,name,eq,rng,tol,loc,i,e,due,stamp='',**k):
    asset(id,code,name,'QC lab / measuring instrument',k.pop('dept','QA / QC'),loc,calId=k.pop('calId',code),calEquip=eq,calRange=rng,calTol=tol,calIntFreq=i,calExtFreq=e,calibDue=due,stampDue=stamp,calStatus=k.pop('calStatus','In use'),calLab='sup-d2',calIntLast=k.pop('calIntLast',d(-20) if i else ''),calPoints=k.pop('calPoints',''),**k)
inst('ws1','WS6/01','Weighing scale 6 kg (demo)','Weighing Scale','6kg','±0.010kg','Packing room 1','30','365',d(25),d(40),serial='DS-60001',calPoints='1, 3, 6')
inst('ws2','WS60/01','Bench scale 60 kg (demo)','Weighing Scale','60kg','±0.10kg','Mixing room','30','365',d(210),d(225),serial='DS-60601',calPoints='10, 30, 60')
inst('ws3','WS60/02','Bench scale 60 kg (demo)','Weighing Scale','60kg','±0.10kg','Raw material store','30','365',d(-5),d(225),serial='DS-60602',calPoints='10, 30, 60')
inst('ws4','WS3/01','Weighing scale 3 kg (demo)','Weighing Scale','3kg','±1.0g','QC lab','30','365',d(150),serial='DS-30001',calPoints='500, 1000, 3000',calStatus='Sent for calibration',calSentDate=d(-3))
inst('ref1','REF01','Refractometer 0–85% Brix (demo)','Refractometer','0 ~ 85%','±0.20','QC lab','30','365',d(230),serial='RF-0001')
inst('pm1','PM01','pH meter (demo)','pH Meter','0 - 14 pH','±0.05','QC lab','0.5','365',d(200),serial='PH-0001')
inst('sw1','SW1/01','Standard weight 1 kg (demo)','Standard Weight','1kg','','QC lab','','365',d(60),serial='SW-0001')
inst('md1','MD01','Metal detector (demo)','Metal Detector (Fe & SUS)','Fe 2.0 mm, SUS 2.5 mm','','Packing room 1','','365',d(180),dept='Production',serial='MD-0001')
inst('sm1','SM01','Band sealer (demo)','Sealing Machine','230 °C - 250 °C','±10','Packing room 2','90','365',d(14),serial='BS-0001',dept='Production')
# work orders
def wo(id,no,assetId,title,typ,status,n,**k):
    w=dict(no=no,assetId=assetId,title=title,type=typ,status=status,priority=k.pop('priority','Normal'),reportDate=d(n),reportedBy=k.pop('reportedBy','Production supervisor (demo)'),dept=k.pop('dept',''),location=k.pop('location',''),
      performedBy=k.pop('performedBy','Internal team'),technician=k.pop('technician','Technician (demo)'),supplierId=k.pop('supplierId',''),startDate=k.pop('startDate',''),completedDate=k.pop('completedDate',''),downtimeHrs=k.pop('downtimeHrs',''),
      tasksDone=k.pop('tasksDone',''),recommendations='',lines=k.pop('lines',[]),files=[],chkHygiene=k.pop('chk',False),chkSafety=k.get('chkS',False),chkIsolated=False,chkPPE=False,chkTools=False,chkClearance=False)
    k.pop('chkS',None);w.update(k);add('workorders',id,w,n)
wo('w1','WO-2611-001','as7','Dust collector fan noisy, low suction','Breakdown / repair','Waiting parts',-6,priority='High',startDate=d(-5),dept='Production',location='Mixing room')
wo('w2','WO-2611-002','as2','Sealing jaw temperature unstable','Breakdown / repair','In progress',-3,priority='High',startDate=d(-2),dept='Production',location='Packing room 1')
wo('w3','WO-2611-003','as4','Aircond leaking water in office','Breakdown / repair','Open',-1,performedBy='External contractor / vendor',supplierId='sup-d1',technician='',dept='Office / Admin',location='General office')
wo('w4','WO-2611-004','as1','Quarterly PM – ribbon mixer','Preventive maintenance','Completed',-10,startDate=d(-9),completedDate=d(-9),downtimeHrs='2',tasksDone='Gearbox oil topped up; shaft seals OK; bowl cleaned and sanitised.',chk=True,chkS=True,chkIsolated=True,chkPPE=True,chkTools=True,chkClearance=True,dept='Production',location='Mixing room',
   lines=[dict(partId='p2',name='MCH-0002 · Food-grade grease 400 g',qty=1,unitCost=38)],partsPosted=True)
wo('w5','WO-2611-005','ws2','External calibration – WS60/01','Calibration','Completed',-14,performedBy='External contractor / vendor',supplierId='sup-d2',technician='',startDate=d(-14),completedDate=d(-14),dept='QA / QC',location='Mixing room',
   cal=dict(rule='error',kind='External',cert='CERT-DEMO-0458',std='Reference weights set (demo)',points=[dict(point='10',reading='10.02',u='0.01',err='+0.02',result='Pass',manual=False),dict(point='30',reading='30.04',u='0.02',err='+0.04',result='Pass',manual=False),dict(point='60',reading='60.06',u='0.03',err='+0.06',result='Pass',manual=False)],result='Pass',impact='',oos=False),
   chk=True,chkS=True,chkIsolated=True,chkPPE=True,chkTools=True,chkClearance=True,supplierReportNo='CERT-DEMO-0458')
wo('w6','WO-2611-006','as3','Replace air filter','Preventive maintenance','Completed',-20,startDate=d(-20),completedDate=d(-20),tasksDone='Air filter replaced, condensate drained.',chk=True,chkS=True,dept='Facility / utilities',location='Utility area')
wo('w7','WO-2610-018','as5','Forklift horn not working','Breakdown / repair','Verified',-25,startDate=d(-24),completedDate=d(-24),tasksDone='Loose connector refixed; horn tested OK.',chk=True,chkS=True,verifiedBy='QA Executive (demo)',verifiedDate=d(-23),dept='Warehouse',location='Finished goods store')
wo('w8','WO-2611-007','','Emergency light at main entrance not working','Breakdown / repair','Open',-2,performedBy='External contractor / vendor',supplierId='sup-d3',technician='',dept='Facility / utilities',location='General office',priority='High')
# parts
def part(id,code,name,cat,qty,minq,unit,cost,**k):
    add('parts',id,dict(code=code,name=name,category=cat,qty=qty,minQty=minq,unit=unit,unitCost=cost,store=k.pop('store','Maintenance store, rack A'),supplierId=k.pop('supplierId','sup-d4'),compatible=k.pop('compatible',''),foodGrade=k.pop('foodGrade',False),notes='',files=[],moves=k.pop('moves',[])))
part('p1','MCH-0001','Bearing 6205-2RS (demo)','Machines & tools',6,4,'PCS',18.5,compatible='AS-0001')
part('p2','MCH-0002','Food-grade grease 400 g (demo)','Machines & tools',1,3,'TUBE',38,foodGrade=True,moves=[dict(at=ts(-9),by=TECH,name='Technician (demo)',type='Issue',qty=-1,bal=1,date=d(-9),ref='WO-2611-004',note='')])
part('p3','MCH-0003','V-belt B-42 (demo)','Machines & tools',4,2,'PCS',22,compatible='AS-0003')
part('p4','FAC-0001','LED tube 18 W (demo)','Building & facilities',12,10,'PCS',9.9)
part('p5','FLT-0001','Forklift hydraulic oil 20 L (demo)','Forklift & reach truck',0,1,'CAN',185)
part('p6','OFC-0001','Printer toner (demo)','Office equipment & IT',2,1,'PCS',120)
# incidents
add('incidents','i1',dict(no='INC-2611-001',title='Hand cut while changing mixer blade (demo)',category='Accident – injury',severity='Lost time – more than 4 days',status='Under investigation',incDate=d(-4),incTime='10:30',location='Mixing room',dept='Production',assetId='as1',
  personType='Employee',personName='Worker A (demo)',personIdNo='',occupation='Machine operator',age='',gender='',nationality='',personEmployer='',bodyPart='Left hand',injuryNature='Laceration',treatedAt='Klinik Demo',daysLost='5',
  description='Operator cut left hand on the ribbon edge while changing the blade without cut-resistant gloves.',immediateAction='First aid given, sent to clinic. Machine isolated.',reportedBy='Production supervisor (demo)',witnesses='Worker B (demo)',sceneKept=True,
  hazard='Sharp blade edge',hazardCat='Mechanical',existingControl='LOTO procedure',riskL='3',riskS='3',consPeople='Minor Injury',resL='',resS='',immediateCause='',rootCause='',capa=[],files=[],foodImpact='None',foodAction=''),-4)
add('incidents','i2',dict(no='INC-2611-002',title='Pallet fell from rack, no injury (demo)',category='Property / equipment damage only',severity='No injury',status='Closed',incDate=d(-12),incTime='15:00',location='Finished goods store',dept='Warehouse',
  description='Pallet slipped from second level during forklift handling.',immediateAction='Area cordoned off, stock re-stacked.',reportedBy='Storekeeper (demo)',closedBy='Demo Admin',closedDate=d(-8),capa=[],files=[]),-12)
# contracts
def con(id,title,typ,sup,start,end,cost,**k):
    add('contracts',id,dict(title=title,type=typ,supplierId=sup,startDate=start,endDate=end,annualCost=cost,billing=k.pop('billing','Yearly'),status='Active',autoRenew=k.pop('autoRenew',False),noticeDays=k.pop('noticeDays','30'),owner='Demo Admin',dept=k.pop('dept','Office / Admin'),ref=k.pop('ref',''),scope=k.pop('scope',''),notes='',assetId=k.pop('assetId',''),seats=k.pop('seats','')))
con('c1','Aircond servicing contract (demo)','Service contract (non-IT)','sup-d1',d(-340),d(25),3600,ref='SC-DEMO-01',scope='Quarterly servicing of 12 aircond units')
con('c2','Pest control service (demo)','Service contract (non-IT)','sup-d5',d(-120),d(245),4800,billing='Monthly',ref='PC-DEMO-07')
con('c3','Antivirus licence – 20 seats (demo)','Antivirus / security','sup-d4',d(-380),d(-15),1200,seats='20',dept='Office / Admin')
con('c4','Accounting software subscription (demo)','Software subscription / licence','sup-d4',d(-200),d(165),2400,autoRenew=True)
# purchases
def L(lid,desc,qty,unit,price,partId='',kind='part',remark=''):return dict(lid=lid,desc=desc,qty=qty,unit=unit,price=price,partId=partId,kind=kind,remark=remark)
add('purchases','pu1',dict(no='PR-2611-003',status='Pending approval',requestedBy='Technician (demo)',dept='Production',reqDate=d(-1),neededBy=d(6),woId='w1',supplierId='sup-d4',purpose='Parts for WO-2611-001: dust collector fan bearing and belt',
  lines=[L('l1','MCH-0001 · Bearing 6205-2RS (demo)',2,'PCS',18.5,'p1'),L('l2','MCH-0003 · V-belt B-42 (demo)',1,'PCS',22,'p3')],files=[],submittedAt=ts(-1)),-1)
add('purchases','pu2',dict(no='PR-2611-002',poNo='PO-2611-002',status='PO issued',requestedBy='Demo Admin',dept='Facility / utilities',reqDate=d(-5),neededBy=d(2),woId='w8',supplierId='sup-d3',purpose='Replace emergency light at main entrance',
  lines=[L('l1','Emergency light twin-spot LED (demo)',1,'UNIT',145,kind='svc',remark='3-hour battery backup\nWall mounted, with test button'),L('l2','Installation and wiring',1,'SET',120,kind='svc')],
  approval=dict(decision='Approved',by=ADMIN,name='Demo Admin',at=ts(-4,10),note='',total=265),
  po=dict(date=d(-4),issuedAt=ts(-4,11),issuedBy='Demo Admin',supplierId='sup-d3',delivery=d(2),terms='30 days',quoteRef='Q-DEMO-112',deliverTo='Main factory (demo address)',remarks='',other='',otherLabel=''),files=[],submittedAt=ts(-5)),-5)
add('purchases','pu3',dict(no='PR-2611-001',poNo='PO-2611-001',status='Received',requestedBy='Technician (demo)',dept='Production',reqDate=d(-15),neededBy=d(-10),supplierId='sup-d4',purpose='Restock food-grade grease and bearings',
  lines=[L('l1','MCH-0002 · Food-grade grease 400 g (demo)',2,'TUBE',38,'p2'),L('l2','MCH-0001 · Bearing 6205-2RS (demo)',4,'PCS',18.5,'p1')],
  approval=dict(decision='Approved',by=ADMIN,name='Demo Admin',at=ts(-14,10),note='',total=150),
  po=dict(date=d(-14),issuedAt=ts(-14,11),issuedBy='Demo Admin',supplierId='sup-d4',delivery=d(-10),terms='30 days',quoteRef='',deliverTo='Main factory (demo address)',remarks='',other='',otherLabel=''),
  receipts=[dict(at=ts(-11),by=TECH,name='Technician (demo)',date=d(-11),doNo='DO-DEMO-5521',note='',lines=[dict(lid='l1',qty=2),dict(lid='l2',qty=4)])],
  inv=dict(invNo='INV-DEMO-8830',invDate=d(-11),invAmount=150,sapRef='PU-DEMO-0101',sapNote=''),files=[],submittedAt=ts(-15)),-15)
json.dump(dict(profiles=profiles,docs=docs),open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'demo.json'),'w'),ensure_ascii=False,indent=0)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'demo-data.js'),'w').write('window.__DEMO='+json.dumps(dict(profiles=profiles,docs=docs),ensure_ascii=False)+';')
print(len(docs))
