"""GPL-3.0-or-later. Three-step desktop mission transfer UI."""
from __future__ import annotations
import json,re,shutil,sys,uuid
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QThread,Signal,QSettings,QStandardPaths,Qt,QUrl,QTimer,QSize
from PySide6.QtGui import QDesktopServices,QPixmap,QIcon
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,
 QLabel,QPushButton,QComboBox,QLineEdit,QFileDialog,QTableWidget,QTableWidgetItem,
 QHeaderView,QPlainTextEdit,QMessageBox,QCheckBox,QStackedWidget,QFrame,QDialog,QProgressBar)
from core import Adb,devices,plan,apply,atomic_json,BridgeError,inspect_kmz,digest,BASE
from preview import render_preview
import ios

class Job(QThread):
 result=Signal(object);error=Signal(str)
 def __init__(self,fn,parent=None):super().__init__(parent);self.fn=fn
 def run(self):
  try:self.result.emit(self.fn())
  except Exception as e:self.error.emit(str(e))

def android_name(description):
 model=re.search(r'\bmodel:(\S+)',description)
 if not model:return 'Android-Gerät'
 value=model.group(1)
 return {'DJI_RC_PRO_2':'DJI RC Pro 2','DJI_RC_PRO':'DJI RC Pro','DJI_RC_2':'DJI RC 2'}.get(value,value.replace('_',' '))

class Window(QMainWindow):
 def __init__(self,autosearch=True):
  super().__init__();self.setWindowTitle('Drone Missions Bridge · 0.3');self.resize(960,740);self.setMinimumSize(820,660)
  self.settings=QSettings('studiobaff','DroneMissionsBridge');self.root=Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation));self.root.mkdir(parents=True,exist_ok=True)
  self.transfer=None;self.rows=[];self.registry={};self.job=None;self.source_path=None;self.background_path=None;self.step=0;self.device_key=None
  try:self.registry=json.loads((self.root/'names.json').read_text())
  except (OSError,ValueError):pass
  self.build_settings()
  self.body=QWidget();outer=QVBoxLayout(self.body);outer.setContentsMargins(28,24,28,22);outer.setSpacing(18);self.setCentralWidget(self.body)
  header=QHBoxLayout();title=QLabel('Mission übertragen');title.setObjectName('windowTitle');header.addWidget(title);header.addStretch()
  archive=QPushButton('Webarchiv ↗');archive.setObjectName('quiet');archive.clicked.connect(lambda:QDesktopServices.openUrl(QUrl('https://service.studiobaff.com/dronemissions/')));header.addWidget(archive)
  settings=QPushButton('Einstellungen');settings.setObjectName('quiet');settings.clicked.connect(self.settings_dialog.show);header.addWidget(settings);outer.addLayout(header)
  steps=QHBoxLayout();self.step_labels=[]
  for caption in ['1  Gerät','2  Mission','3  Übertragen']:
   label=QLabel(caption);label.setObjectName('step');steps.addWidget(label);self.step_labels.append(label)
  outer.addLayout(steps)
  self.pages=QStackedWidget();outer.addWidget(self.pages,1)
  self.build_device_page();self.build_mission_page();self.build_review_page()
  self.progress=QProgressBar();self.progress.setRange(0,0);self.progress.setFixedHeight(4);self.progress.hide();outer.addWidget(self.progress)
  self.status=QLabel('iPad oder Fernsteuerung per USB verbinden.');self.status.setObjectName('status');self.status.setWordWrap(True);outer.addWidget(self.status)
  footer=QHBoxLayout();self.back_button=QPushButton('Zurück');self.back_button.clicked.connect(lambda:self.show_step(self.step-1));footer.addWidget(self.back_button);footer.addStretch()
  self.next_button=QPushButton('Weiter');self.next_button.setObjectName('primary');self.next_button.clicked.connect(self.advance);footer.addWidget(self.next_button)
  self.apply_button=QPushButton('Jetzt übertragen');self.apply_button.setObjectName('primary');self.apply_button.clicked.connect(self.execute);footer.addWidget(self.apply_button);outer.addLayout(footer)
  self.show_step(0)
  if autosearch:QTimer.singleShot(0,self.refresh_devices)
 def page(self):
  page=QFrame();page.setObjectName('card');layout=QVBoxLayout(page);layout.setContentsMargins(24,22,24,22);layout.setSpacing(14);self.pages.addWidget(page);return layout
 def heading(self,layout,title,description):
  label=QLabel(title);label.setObjectName('pageTitle');layout.addWidget(label)
  label=QLabel(description);label.setObjectName('muted');label.setWordWrap(True);layout.addWidget(label)
 def build_device_page(self):
  layout=self.page();self.heading(layout,'Wohin soll die Mission?','Verbinde dein iPad, iPhone oder deine Fernsteuerung per USB und entsperre das Gerät.')
  layout.addSpacing(16);layout.addWidget(QLabel('Verbundenes Gerät'))
  row=QHBoxLayout();self.device=QComboBox();self.device.setMinimumHeight(44);self.device.currentIndexChanged.connect(self.changed_device);row.addWidget(self.device,1)
  self.refresh_button=QPushButton('Neu suchen');self.refresh_button.clicked.connect(self.refresh_devices);row.addWidget(self.refresh_button);layout.addLayout(row)
  self.device_note=QLabel('Gerät auswählen, um fortzufahren.');self.device_note.setObjectName('hintBox');self.device_note.setWordWrap(True);layout.addWidget(self.device_note)
  self.list_button=QPushButton('Missionen auf dem Gerät ansehen');self.list_button.setObjectName('quiet');self.list_button.clicked.connect(lambda:self.list_missions(True));layout.addWidget(self.list_button,alignment=Qt.AlignLeft);layout.addStretch(1)
  label=QLabel('iPad nicht sichtbar? Entsperren und „Diesem Computer vertrauen“ bestätigen.');label.setObjectName('muted');label.setWordWrap(True);layout.addWidget(label)
 def build_mission_page(self):
  layout=self.page();self.heading(layout,'Welche Mission möchtest du übertragen?','Wähle einen DJI-KMZ-Export aus Litchi, Map Creator oder deinem Webarchiv.')
  row=QHBoxLayout();self.source_label=QLabel('Noch keine KMZ ausgewählt');self.source_label.setObjectName('fileName');self.source_label.setWordWrap(True);row.addWidget(self.source_label,1)
  button=QPushButton('KMZ auswählen …');button.clicked.connect(self.choose_kmz);row.addWidget(button);layout.addLayout(row)
  layout.addWidget(QLabel('Missionsname'));self.name=QLineEdit();self.name.setPlaceholderText('Zum Beispiel: Baustelle Nord · Panorama');self.name.textChanged.connect(self.invalidate);layout.addWidget(self.name)
  row=QHBoxLayout();self.preview_label=QLabel('Vorschaubild wird aus der Route erstellt.');self.preview_label.setObjectName('muted');self.preview_label.setWordWrap(True);row.addWidget(self.preview_label,1)
  button=QPushButton('Eigenes Bild …');button.setObjectName('quiet');button.clicked.connect(self.choose_preview);row.addWidget(button)
  button=QPushButton('Entfernen');button.setObjectName('quiet');button.clicked.connect(self.clear_background);row.addWidget(button);layout.addLayout(row)
  self.target_panel=QWidget();target=QVBoxLayout(self.target_panel);target.setContentsMargins(0,8,0,0);target.setSpacing(8)
  row=QHBoxLayout();label=QLabel('Welchen Eintrag auf der Fernsteuerung ersetzen?');label.setObjectName('sectionTitle');row.addWidget(label,1)
  button=QPushButton('Liste laden');button.setObjectName('quiet');button.clicked.connect(lambda:self.list_missions(False));row.addWidget(button);target.addLayout(row)
  self.table=QTableWidget(0,3);self.table.setHorizontalHeaderLabels(['Mission / Vorschaubild','Wegpunkte','Bestand']);self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch);self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeToContents);self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeToContents)
  self.table.verticalHeader().hide();self.table.setSelectionBehavior(QTableWidget.SelectRows);self.table.setSelectionMode(QTableWidget.SingleSelection);self.table.setEditTriggers(QTableWidget.NoEditTriggers);self.table.setMinimumHeight(150);self.table.setMaximumHeight(220);self.table.setIconSize(QSize(74,50));self.table.itemSelectionChanged.connect(self.invalidate);target.addWidget(self.table)
  label=QLabel('Vergleiche Bild und Punktzahl mit DJI Fly. Der Name auf Android ist für die Bridge nicht lesbar. Der alte Stand wird vor dem Austausch gesichert.');label.setObjectName('muted');label.setWordWrap(True);target.addWidget(label);layout.addWidget(self.target_panel)
  self.new_note=QLabel('Auf dem iPad/iPhone wird eine neue Mission angelegt. Bestehende Missionen bleiben erhalten.');self.new_note.setObjectName('hintBox');self.new_note.setWordWrap(True);layout.addWidget(self.new_note);layout.addStretch(1)
 def build_review_page(self):
  layout=self.page();self.heading(layout,'Passt alles?','Prüfe Name und Vorschau. Vor jeder Übertragung wird automatisch gesichert.')
  row=QHBoxLayout();self.image=QLabel();self.image.setFixedSize(330,220);self.image.setAlignment(Qt.AlignCenter);self.image.setObjectName('preview');row.addWidget(self.image)
  text=QVBoxLayout();self.summary_name=QLabel();self.summary_name.setObjectName('pageTitle');self.summary_name.setWordWrap(True);text.addWidget(self.summary_name)
  self.summary_points=QLabel();self.summary_points.setObjectName('muted');text.addWidget(self.summary_points);self.summary_target=QLabel();self.summary_target.setWordWrap(True);text.addWidget(self.summary_target);text.addStretch();row.addLayout(text,1);layout.addLayout(row)
  self.review_note=QLabel();self.review_note.setWordWrap(True);self.review_note.setObjectName('hintBox');layout.addWidget(self.review_note)
  self.closed=QCheckBox('DJI Fly ist vollständig geschlossen. Es ist kein Flug aktiv.');self.closed.toggled.connect(lambda checked:self.apply_button.setEnabled(checked and self.transfer is not None));layout.addWidget(self.closed);layout.addStretch(1)
 def build_settings(self):
  self.settings_dialog=QDialog(self);self.settings_dialog.setWindowTitle('Einstellungen und Protokoll');self.settings_dialog.resize(700,470);layout=QVBoxLayout(self.settings_dialog)
  label=QLabel('Android-Verbindung');label.setObjectName('pageTitle');layout.addWidget(label);label=QLabel('ADB wird nur für die Fernsteuerung benötigt. Für iPad/iPhone ist kein ADB nötig.');label.setWordWrap(True);layout.addWidget(label)
  row=QHBoxLayout();self.adb=QLineEdit();self.adb.setReadOnly(True);fallback='/Applications/DJIKMZInjector.app/Contents/Frameworks/tools/adb' if sys.platform=='darwin' else '';self.adb.setText(self.settings.value('adb','') or shutil.which('adb') or fallback);self.adb.textChanged.connect(self.invalidate);row.addWidget(self.adb,1)
  button=QPushButton('ADB wählen …');button.clicked.connect(self.choose_adb);row.addWidget(button);layout.addLayout(row)
  layout.addWidget(QLabel('Protokoll'));self.log=QPlainTextEdit();self.log.setReadOnly(True);layout.addWidget(self.log,1)
  row=QHBoxLayout();button=QPushButton('Sicherungen öffnen');button.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.root))));row.addWidget(button)
  button=QPushButton('Gerät jetzt sichern');button.clicked.connect(self.backup);row.addWidget(button);row.addStretch();button=QPushButton('Schließen');button.clicked.connect(self.settings_dialog.close);row.addWidget(button);layout.addLayout(row)
 def show_step(self,index):
  self.step=max(0,min(2,index));self.pages.setCurrentIndex(self.step);self.back_button.setVisible(self.step>0);self.next_button.setVisible(self.step<2);self.apply_button.setVisible(self.step==2);self.apply_button.setEnabled(self.transfer is not None and self.closed.isChecked());self.next_button.setText('Weiter' if self.step==0 else 'Vorschau prüfen')
  for i,label in enumerate(self.step_labels):label.setProperty('active',i==self.step);label.style().unpolish(label);label.style().polish(label)
  if self.step==0:self.status.setText('Gerät auswählen, dann Weiter.')
  elif self.step==1:self.status.setText('KMZ auswählen und den Missionsnamen eingeben.')
 def advance(self):
  if self.step==0:
   try:r=self.selected_device()
   except Exception as e:self.error(str(e));return
   self.show_step(1)
   if r['kind']=='android' and not self.rows:self.list_missions(False)
  else:self.prepare()
 def changed_device(self,*args):
  self.invalidate();self.rows=[]
  if hasattr(self,'table'):self.table.setRowCount(0)
  r=self.device.currentData();is_ios=bool(r and r['kind']=='ios')
  if hasattr(self,'target_panel'):self.target_panel.setVisible(not is_ios);self.new_note.setVisible(is_ios)
  if r:self.device_note.setText('Neue Mission mit Name und Titelvorschau anlegen.' if is_ios else 'Einen bestehenden Eintrag nach Sicherung ersetzen. Auf der RC Pro 2 ist danach ein Neustart erforderlich.')
  else:self.device_note.setText('Gerät auswählen, um fortzufahren.')
 def invalidate(self,*args):
  self.transfer=None
  if hasattr(self,'apply_button'):self.apply_button.setEnabled(False)
 def closeEvent(self,event):
  if self.job and self.job.isRunning():QMessageBox.information(self,'Aktion läuft','Bitte die laufende Aktion abschließen lassen.');event.ignore()
  else:event.accept()
 def selected_device(self):
  r=self.device.currentData()
  if not r or r.get('state')!='device':raise BridgeError('Bitte ein verbundenes, entsperrtes Gerät auswählen.')
  return dict(r)
 def adb_for(self,r):return Adb(self.adb.text().strip(),r['serial'])
 def task(self,label,fn,done):
  if self.job and self.job.isRunning():return
  self.status.setText(label);self.log.appendPlainText(label);self.body.setEnabled(False);self.settings_dialog.setEnabled(False);self.progress.show();j=Job(fn,self);self.job=j
  def enable():self.body.setEnabled(True);self.settings_dialog.setEnabled(True);self.progress.hide()
  def ok(result):
   enable()
   try:done(result)
   except Exception as e:self.error(str(e))
  def fail(text):enable();self.error(text)
  j.result.connect(ok);j.error.connect(fail);j.start()
 def error(self,text):self.status.setText(text);self.log.appendPlainText('FEHLER: '+text);QMessageBox.warning(self,'Bitte prüfen',text)
 def choose_adb(self):
  path,_=QFileDialog.getOpenFileName(self,'ADB auswählen')
  if path:self.adb.setText(path);self.settings.setValue('adb',path)
 def set_source(self,path):
  self.source_path=Path(path);self.source_label.setText(self.source_path.name);self.source_label.setToolTip(str(self.source_path));self.name.setText(self.source_path.stem);self.clear_background();self.invalidate()
  for folder in [self.source_path.parent/'Preview',self.source_path.parent/'preview',self.source_path.parent]:
   thumb=folder/(self.source_path.stem+'.jpg')
   if thumb.is_file():self.background_path=thumb;self.preview_label.setText('Bild: '+thumb.name);break
 def choose_kmz(self):
  path,_=QFileDialog.getOpenFileName(self,'DJI-KMZ auswählen','','DJI-KMZ (*.kmz *.KMZ)')
  if path:self.set_source(path)
 def choose_preview(self):
  path,_=QFileDialog.getOpenFileName(self,'Bildhintergrund auswählen','','Bilder (*.jpg *.jpeg *.png)')
  if path:self.background_path=Path(path);self.preview_label.setText('Bild: '+Path(path).name);self.invalidate()
 def clear_background(self):self.background_path=None;self.preview_label.setText('Vorschaubild wird aus der Route erstellt.');self.invalidate()
 def refresh_devices(self):
  exe=self.adb.text().strip();previous=self.device.currentData()
  def find():
   found=[];errors=[]
   if exe and Path(exe).is_file():
    try:found.extend({**r,'kind':'android','name':android_name(r['description'])} for r in devices(exe))
    except Exception as e:errors.append('Android: '+str(e))
   try:found.extend(ios.run(ios.discover()))
   except Exception as e:errors.append('iPad/iPhone: '+str(e))
   return found,errors
  def done(result):
   rows,errors=result;self.device.clear();self.device.addItem('Gerät auswählen …',None)
   for r in rows:self.device.addItem(r['name']+(' · USB' if r['state']=='device' else ' · entsperren und vertrauen'),r)
   chosen=next((i+1 for i,r in enumerate(rows) if previous and r['serial']==previous['serial']),1 if len(rows)==1 else 0);self.device.setCurrentIndex(chosen);self.status.setText(f'{len(rows)} Gerät(e) gefunden.' if rows else 'Kein Gerät gefunden. Kabelverbindung und Entsperrung prüfen.')
   if errors:self.log.appendPlainText('\n'.join(errors))
  self.task('Verbundene Geräte suchen …',find,done)
 def list_missions(self,dialog=False):
  try:r=self.selected_device();a=self.adb_for(r)
  except Exception as e:self.error(str(e));return
  def read():
   if r['kind']=='ios':return ios.run(ios.list_missions(r['serial'],self.root/'reads'))
   rows=a.list_missions()
   for m in rows:
    if m.get('path'):
     try:m['waypoints']=inspect_kmz(a.read(m['path']))['waypoints']
     except BridgeError:m['waypoints']='prüfen'
    if m['preview']:
     try:m['image']=a.read(f'{BASE}/map_preview/{m["uuid"]}/{m["uuid"]}.jpg')
     except Exception:pass
   return rows
  def done(rows):
   self.rows=rows
   table=self.table
   popup=None
   if dialog:
    popup=QDialog(self);popup.setWindowTitle('Missionen auf '+r['name']);popup.resize(730,470);layout=QVBoxLayout(popup);table=QTableWidget(0,3);table.setHorizontalHeaderLabels(['Mission','Wegpunkte','Bestand']);table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch);table.verticalHeader().hide();table.setEditTriggers(QTableWidget.NoEditTriggers);layout.addWidget(table);button=QPushButton('Schließen');button.clicked.connect(popup.accept);layout.addWidget(button)
   table.setRowCount(len(rows))
   for i,m in enumerate(rows):
    label=m.get('name') or self.registry.get(r['serial']+':'+m['uuid'],'Eintrag '+str(i+1));item=QTableWidgetItem(label);item.setToolTip('Kennung: '+m['uuid'])
    if m.get('image'):
     pixmap=QPixmap();pixmap.loadFromData(m['image']);item.setIcon(QIcon(pixmap));table.setRowHeight(i,58)
    table.setItem(i,0,item);table.setItem(i,1,QTableWidgetItem(str(m.get('waypoints','—'))));table.setItem(i,2,QTableWidgetItem({'local':'Lokal vorhanden','cloud-or-missing':'Nur Cloud / fehlt lokal','ambiguous':'Mehrere Dateien'}[m['localState']]))
   self.status.setText(f'{len(rows)} Missionen gelesen.');
   if popup:popup.exec()
  self.task('Missionen auf dem Gerät lesen …',read,done)
 def backup(self):
  try:r=self.selected_device();a=self.adb_for(r)
  except Exception as e:self.error(str(e));return
  if QMessageBox.question(self,'Bestand sichern','Ist kein Flug aktiv und DJI Fly vollständig geschlossen?\n\nDie Sicherung liest nur die vorhandenen Missionsdaten. Auf Android wird DJI Fly dabei beendet.')!=QMessageBox.Yes:return
  dest=self.root/'backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');dest.parent.mkdir(parents=True,exist_ok=True)
  self.task('Missionsbestand sichern und zurücklesen …',lambda:ios.run(ios.backup(r['serial'],dest)) if r['kind']=='ios' else a.snapshot(dest),lambda result:self.status.setText(f'{len(result["files"])} Dateien gesichert. Ablage über Einstellungen öffnen.'))
 def prepare(self):
  self.invalidate()
  try:
   r=self.selected_device()
   if self.source_path is None:raise BridgeError('Bitte zuerst eine DJI-KMZ auswählen.')
   source=self.source_path;raw=source.read_bytes();details=inspect_kmz(raw);name=self.name.text().strip()
   if not name or len(name)>200:raise BridgeError('Bitte einen Missionsnamen bis 200 Zeichen eingeben.')
   preview=render_preview(self.root/'previews'/(uuid.uuid4().hex+'.jpg'),name,details,self.background_path);target=None
   if r['kind']=='android':
    row=self.table.currentRow()
    if row<0 or row>=len(self.rows):raise BridgeError('Bitte den Eintrag wählen, der auf der Fernsteuerung ersetzt werden soll.')
    target=self.rows[row]['uuid'];target_name=self.table.item(row,0).text()
   else:target_name='Neue Mission auf '+r['name']
   prepared={'device':r,'source':str(source.resolve()),'sourceSha256':digest(raw),'name':name,'preview':str(preview),'previewSha256':digest(preview.read_bytes()),'kmz':details,'mode':'ios-new'}
  except Exception as e:self.error(str(e));return
  def prepare_plan():
   if r['kind']=='ios':return prepared
   result=plan(self.adb_for(r),source,name,preview,target);result['device']=r;return result
  def done(p):
   self.transfer=p;self.image.setPixmap(QPixmap(str(preview)).scaled(330,220,Qt.KeepAspectRatio,Qt.SmoothTransformation));self.summary_name.setText(name);self.summary_points.setText(f'{details["waypoints"]} Wegpunkte · {details["distance"]/1000:.2f} km');self.summary_target.setText(target_name)
   self.review_note.setText('Neue Mission mit Name und Titelbild. Anschließend in DJI Fly öffnen und bei Bedarf synchronisieren.' if r['kind']=='ios' else 'Der gewählte Eintrag wird nach Sicherung ersetzt. Anschließend RC Pro 2 neu starten, Mission öffnen und Speichern prüfen.');self.closed.setChecked(False);self.show_step(2);self.status.setText('Noch nichts übertragen. Vorschau prüfen und DJI Fly schließen.')
  self.task('Mission und Vorschau prüfen …',prepare_plan,done)
 def execute(self):
  p=self.transfer
  if not p or not self.closed.isChecked():return
  r=p['device']
  try:
   if self.selected_device()!=r:raise BridgeError('Gerät wurde gewechselt. Bitte erneut prüfen.')
   if digest(Path(p['source']).read_bytes())!=p['sourceSha256'] or digest(Path(p['preview']).read_bytes())!=p['previewSha256']:raise BridgeError('Datei oder Vorschau wurde verändert. Bitte erneut prüfen.')
   dest=self.root/'transfers'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');dest.parent.mkdir(parents=True,exist_ok=True)
  except Exception as e:self.error(str(e));return
  # The review page is the explicit final confirmation; no second confirmation dialog.
  def done(result):
   self.registry[r['serial']+':'+result['uuid']]=p['name'];atomic_json(self.root/'names.json',self.registry);self.transfer=None;self.apply_button.setEnabled(False);self.log.appendPlainText('Sicherung und Protokoll: '+str(dest));self.status.setText('Übertragen und zurückgelesen. Jetzt in DJI Fly öffnen und Speichern prüfen.')
   QMessageBox.information(self,'Übertragung geprüft',('Die neue Mission ist mit Name und Vorschau eingetragen.' if r['kind']=='ios' else 'KMZ und Titelvorschau wurden im gewählten Eintrag ersetzt.')+'\n\n'+('Jetzt DJI Fly öffnen und Mission sowie Cloud-Synchronisation prüfen.' if r['kind']=='ios' else 'Jetzt RC Pro 2 neu starten und Mission in DJI Fly prüfen.')+'\n\nDie Sicherung ist unter Einstellungen erreichbar.')
  self.task('Mission sichern, übertragen und zurücklesen …',lambda:ios.run(ios.apply_new(r['serial'],Path(p['source']),p['name'],Path(p['preview']),dest,fly_closed=True)) if r['kind']=='ios' else apply(self.adb_for(r),p,dest),done)

STYLE='''
QWidget{background:#f4f6f2;color:#173c31;font-family:"Helvetica Neue","Segoe UI";font-size:13px}
QLabel#windowTitle{font-size:24px;font-weight:650}QLabel#pageTitle{font-size:21px;font-weight:600;background:transparent}
QLabel#sectionTitle,QLabel#fileName{font-weight:600;background:transparent}QLabel#muted{color:#6e7c75;font-size:12px;background:transparent}
QLabel#step{padding:10px 14px;color:#85918b;border-bottom:2px solid #dbe2db;background:transparent}
QLabel#step[active="true"]{color:#173c31;font-weight:650;border-bottom:3px solid #54856a}
QFrame#card{background:white;border:1px solid #dce3dc;border-radius:12px}QFrame#card QWidget{background:white}
QLabel#hintBox{background:#edf3e9;color:#395b47;border-radius:8px;padding:13px;font-size:12px}
QLabel#status{color:#67776c;font-size:12px;min-height:22px}QLabel#preview{background:#152e2b;border-radius:8px}
QPushButton{background:#edf2e9;color:#254735;border:1px solid #d3dece;border-radius:7px;padding:10px 15px;font-weight:550}
QPushButton:hover{background:#e2ebda}QPushButton#quiet{background:transparent;border:1px solid #d8e0d7;color:#5d7063;font-size:12px;padding:9px 12px}
QPushButton#primary{background:#254e3b;color:white;border:1px solid #254e3b;min-width:150px}
QPushButton#primary:hover{background:#35644d}QPushButton:disabled,QPushButton#primary:disabled{color:#9ca79e;background:#e7ece5;border-color:#dce3da}
QLineEdit,QComboBox{background:white;border:1px solid #ced9cd;border-radius:6px;padding:10px;min-height:20px;selection-background-color:#dbe9d3}
QTableWidget{background:white;border:1px solid #d9e2d7;border-radius:6px;selection-background-color:#dcebd3;selection-color:#1f412e;gridline-color:#edf0ea}
QHeaderView::section{background:#f1f5ed;color:#75856f;border:none;padding:8px;font-size:11px}
QPlainTextEdit{background:white;border:1px solid #d7e0d4;border-radius:6px;font-family:Menlo,monospace;font-size:11px;padding:8px}
QCheckBox{spacing:9px;font-size:12px}QCheckBox::indicator{width:19px;height:19px;border:1px solid #a8b9a3;border-radius:4px;background:white}
QCheckBox::indicator:checked{background:#345e43;border:3px solid #a6c794}
QProgressBar{background:#e1e9dc;border:none;border-radius:2px}QProgressBar::chunk{background:#7b9f68}
'''
def main():
 if '--diagnose' in sys.argv:
  target=Path(sys.argv[sys.argv.index('--diagnose')+1]);rows=ios.run(ios.discover());result={'iosDevices':len(rows),'paired':sum(r['state']=='device' for r in rows)}
  if rows and rows[0]['state']=='device':result['readableMissions']=len(ios.run(ios.list_missions(rows[0]['serial'],target.parent/'diagnostic-reads')))
  atomic_json(target,result);return
 app=QApplication(sys.argv);app.setOrganizationName('studiobaff');app.setApplicationName('Drone Missions Bridge');app.setStyleSheet(STYLE);window=Window();window.show();sys.exit(app.exec())
if __name__=='__main__':main()
