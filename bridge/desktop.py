"""GPL-3.0-or-later. Desktop mission transfer UI: Gerät & Missionen · Übertragen · Protokoll.

Die Gerätefunktionen (core.py, ios.py, preview.py, map_preview.py) sind unverändert; diese Datei ist nur Oberfläche.
"""
from __future__ import annotations
import json,re,shutil,sys,uuid
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QThread,Signal,QSettings,QStandardPaths,Qt,QUrl,QTimer,QSize
from PySide6.QtGui import QDesktopServices,QPixmap,QPainter,QColor,QFont
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,
 QLabel,QPushButton,QComboBox,QLineEdit,QFileDialog,QListWidget,QListWidgetItem,QPlainTextEdit,
 QMessageBox,QCheckBox,QStackedWidget,QFrame,QProgressBar,QTabWidget,QButtonGroup,QSizePolicy,QScrollArea)
from PySide6.QtSvg import QSvgRenderer
from core import Adb,devices,plan,apply,atomic_json,BridgeError,inspect_kmz,digest,BASE,prepare_source
from preview import render_preview
from archive import ArchiveClient,safe_filename
import ios

VERSION='0.4'
THUMB=QSize(176,118)
TAB_DEVICE,TAB_ARCHIVE,TAB_TRANSFER,TAB_LOG=0,1,2,3
ARCHIVE_URL='https://service.studiobaff.com/dronemissions/'
STATE_LABELS={'local':'Lokal vorhanden','cloud-or-missing':'Nur Cloud / fehlt lokal','ambiguous':'Mehrere Dateien'}

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

def placeholder(size,text):
 pixmap=QPixmap(size);pixmap.fill(QColor('#1b332b'));painter=QPainter(pixmap);painter.setPen(QColor('#a7c577'))
 painter.setFont(QFont('Helvetica Neue',11));painter.drawText(pixmap.rect(),Qt.AlignCenter|Qt.TextWordWrap,text);painter.end();return pixmap

def picture_from(data,content_type='',size=THUMB):
 pixmap=QPixmap()
 if data and 'svg' in (content_type or ''):
  renderer=QSvgRenderer(data)
  if renderer.isValid():
   pixmap=QPixmap(size);pixmap.fill(QColor('#152e2b'));painter=QPainter(pixmap);renderer.render(painter);painter.end();return pixmap
 if data and pixmap.loadFromData(data):return pixmap.scaled(size,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation)
 return None

class ArchiveRow(QWidget):
 """Eine Zeile der Webarchiv-Liste: Vorschaubild, Name, Projekt, Format, Wegpunkte, Strecke."""
 def __init__(self,m):
  super().__init__();layout=QHBoxLayout(self);layout.setContentsMargins(10,8,10,8);layout.setSpacing(16)
  self.picture=QLabel();self.picture.setFixedSize(THUMB);self.picture.setObjectName('thumb');self.picture.setAlignment(Qt.AlignCenter);self.picture.setPixmap(placeholder(THUMB,'Vorschau wird geladen …' if m['transferable'] else m['format']));layout.addWidget(self.picture)
  text=QVBoxLayout();text.setSpacing(4);title=QLabel(m['name']);title.setObjectName('rowTitle');title.setWordWrap(True);text.addWidget(title)
  folder=QLabel(m['folder']+(' · Archiv' if m['archived'] else ''));folder.setObjectName('muted');text.addWidget(folder)
  meta=f"{m['format']} · V{m.get('version') or '?'}"+(f" · {m['waypoints']} Wegpunkte · {m['distance']/1000:.2f} km" if m['waypoints'] is not None else ' · Planungsdatei, kein Flugexport')
  label=QLabel(meta);label.setObjectName('ident');text.addWidget(label);text.addStretch();layout.addLayout(text,1)
 def set_picture(self,pixmap):
  if pixmap:self.picture.setPixmap(pixmap)
  else:self.picture.setPixmap(placeholder(THUMB,'Kein Vorschaubild'))

class MissionRow(QWidget):
 """Eine Zeile der großen Missionsliste: Vorschaubild, Name, Wegpunkte, Bestand."""
 def __init__(self,label,mission,image=None):
  super().__init__();layout=QHBoxLayout(self);layout.setContentsMargins(10,8,10,8);layout.setSpacing(16)
  picture=QLabel();picture.setFixedSize(THUMB);picture.setObjectName('thumb');picture.setAlignment(Qt.AlignCenter)
  pixmap=QPixmap()
  if image and pixmap.loadFromData(image):picture.setPixmap(pixmap.scaled(THUMB,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation))
  else:picture.setPixmap(placeholder(THUMB,'Kein Vorschaubild'))
  layout.addWidget(picture)
  text=QVBoxLayout();text.setSpacing(4);title=QLabel(label);title.setObjectName('rowTitle');title.setWordWrap(True);text.addWidget(title)
  waypoints=mission.get('waypoints','—');meta=QLabel(f'{waypoints} Wegpunkte · {STATE_LABELS.get(mission.get("localState"),"—")}');meta.setObjectName('muted');text.addWidget(meta)
  ident=QLabel('Kennung '+mission['uuid']);ident.setObjectName('ident');text.addWidget(ident);text.addStretch();layout.addLayout(text,1)

class Window(QMainWindow):
 def __init__(self,autosearch=True):
  super().__init__();self.setWindowTitle(f'Drone Missions Bridge · {VERSION}');self.resize(1180,820);self.setMinimumSize(980,700)
  self.settings=QSettings('studiobaff','DroneMissionsBridge');self.root=Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation));self.root.mkdir(parents=True,exist_ok=True)
  self.transfer=None;self.rows=[];self.registry={};self.job=None;self.source_path=None;self.background_path=None;self.mode='new';self.prepared=None
  self.archive=None;self.archive_rows=[];self.archive_widgets=[];self.client_factory=ArchiveClient;self.original_source=None
  try:self.registry=json.loads((self.root/'names.json').read_text())
  except (OSError,ValueError):pass
  self.body=QWidget();outer=QVBoxLayout(self.body);outer.setContentsMargins(24,18,24,18);outer.setSpacing(14);self.setCentralWidget(self.body)
  self.build_header(outer)
  self.tabs=QTabWidget();self.tabs.setObjectName('tabs');self.tabs.setDocumentMode(True);outer.addWidget(self.tabs,1)
  self.build_device_tab();self.build_archive_tab();self.build_transfer_tab();self.build_log_tab()
  self.progress=QProgressBar();self.progress.setRange(0,0);self.progress.setFixedHeight(4);self.progress.setTextVisible(False);self.progress.hide();outer.addWidget(self.progress)
  self.status=QLabel('iPad oder Fernsteuerung per USB verbinden.');self.status.setObjectName('status');self.status.setWordWrap(True);outer.addWidget(self.status)
  self.set_mode('new');self.changed_device()
  if autosearch:QTimer.singleShot(0,self.refresh_devices)

 # ---------- Aufbau ----------
 def build_header(self,outer):
  header=QHBoxLayout();header.setSpacing(12)
  title=QLabel('Drone Missions Bridge');title.setObjectName('windowTitle');header.addWidget(title)
  header.addSpacing(18);header.addWidget(QLabel('Gerät'))
  self.device=QComboBox();self.device.setMinimumHeight(40);self.device.setMinimumWidth(260);self.device.currentIndexChanged.connect(self.changed_device);header.addWidget(self.device,1)
  self.refresh_button=QPushButton('Neu suchen');self.refresh_button.clicked.connect(self.refresh_devices);header.addWidget(self.refresh_button)
  archive=QPushButton('Webarchiv im Browser ↗');archive.setObjectName('quiet');archive.clicked.connect(lambda:QDesktopServices.openUrl(QUrl(self.archive_url.text().strip() or ARCHIVE_URL)));header.addWidget(archive)
  outer.addLayout(header)
  self.device_note=QLabel('Gerät auswählen, um fortzufahren.');self.device_note.setObjectName('muted');self.device_note.setWordWrap(True);outer.addWidget(self.device_note)

 def card(self,parent_layout,stretch=0):
  frame=QFrame();frame.setObjectName('card');layout=QVBoxLayout(frame);layout.setContentsMargins(22,20,22,20);layout.setSpacing(12);parent_layout.addWidget(frame,stretch);return layout
 def heading(self,layout,title,description=None):
  label=QLabel(title);label.setObjectName('pageTitle');layout.addWidget(label)
  if description:label=QLabel(description);label.setObjectName('muted');label.setWordWrap(True);layout.addWidget(label)

 def build_device_tab(self):
  tab=QWidget();layout=QVBoxLayout(tab);layout.setContentsMargins(0,14,0,0);layout.setSpacing(12);self.tabs.addTab(tab,'Gerät && Missionen')
  card=self.card(layout,1)
  row=QHBoxLayout();text=QVBoxLayout();text.setSpacing(2);title=QLabel('Missionen auf dem Gerät');title.setObjectName('pageTitle');text.addWidget(title)
  self.list_note=QLabel('Liste laden, um Bild, Wegpunkte und Bestand jeder Mission zu sehen.');self.list_note.setObjectName('muted');self.list_note.setWordWrap(True);text.addWidget(self.list_note);row.addLayout(text,1)
  self.list_button=QPushButton('Missionen lesen');self.list_button.clicked.connect(self.list_missions);row.addWidget(self.list_button)
  self.backup_button=QPushButton('Gerät sichern');self.backup_button.setObjectName('quiet');self.backup_button.clicked.connect(self.backup);row.addWidget(self.backup_button);card.addLayout(row)
  self.list=QListWidget();self.list.setObjectName('missions');self.list.setSelectionMode(QListWidget.SingleSelection);self.list.setSpacing(4);self.list.setUniformItemSizes(False);self.list.itemSelectionChanged.connect(self.changed_target);self.list.itemDoubleClicked.connect(lambda _:self.start_replace());card.addWidget(self.list,1)
  self.list_empty=QLabel('Noch keine Missionen gelesen.');self.list_empty.setObjectName('emptyList');self.list_empty.setAlignment(Qt.AlignCenter);card.addWidget(self.list_empty,1)
  actions=QHBoxLayout();self.selected_label=QLabel('Kein Eintrag ausgewählt.');self.selected_label.setObjectName('muted');self.selected_label.setWordWrap(True);actions.addWidget(self.selected_label,1)
  self.new_button=QPushButton('Neu anlegen');self.new_button.setObjectName('primary');self.new_button.clicked.connect(self.start_new);actions.addWidget(self.new_button)
  self.replace_button=QPushButton('Ausgewählte ersetzen …');self.replace_button.setObjectName('primary');self.replace_button.setEnabled(False);self.replace_button.clicked.connect(self.start_replace);actions.addWidget(self.replace_button);card.addLayout(actions)

 def build_archive_tab(self):
  tab=QWidget();layout=QVBoxLayout(tab);layout.setContentsMargins(0,14,0,0);layout.setSpacing(12);self.tabs.addTab(tab,'Webarchiv')
  card=self.card(layout,1)
  row=QHBoxLayout();text=QVBoxLayout();text.setSpacing(2);title=QLabel('Missionen aus dem Webarchiv');title.setObjectName('pageTitle');text.addWidget(title)
  self.archive_note=QLabel('Mit dem Zugangsschlüssel anmelden. Der Schlüssel bleibt nur für diese Sitzung im Speicher.');self.archive_note.setObjectName('muted');self.archive_note.setWordWrap(True);text.addWidget(self.archive_note);row.addLayout(text,1);card.addLayout(row)
  grid=QGridLayout();grid.setHorizontalSpacing(10);grid.setVerticalSpacing(4)
  grid.addWidget(QLabel('Archiv-Adresse'),0,0);self.archive_url=QLineEdit(self.settings.value('archiveURL','') or ARCHIVE_URL);self.archive_url.setPlaceholderText(ARCHIVE_URL);grid.addWidget(self.archive_url,1,0)
  grid.addWidget(QLabel('Zugangsschlüssel'),0,1);self.archive_key=QLineEdit();self.archive_key.setEchoMode(QLineEdit.Password);self.archive_key.setPlaceholderText('Nur für diese Sitzung');self.archive_key.returnPressed.connect(self.archive_login);grid.addWidget(self.archive_key,1,1)
  self.archive_login_button=QPushButton('Anmelden und Bibliothek laden');self.archive_login_button.clicked.connect(self.archive_login);grid.addWidget(self.archive_login_button,1,2);grid.setColumnStretch(0,3);grid.setColumnStretch(1,2);card.addLayout(grid)
  tools=QHBoxLayout();self.archive_search=QLineEdit();self.archive_search.setPlaceholderText('Name, Projekt oder Dateiname suchen …');self.archive_search.textChanged.connect(self.archive_filter);tools.addWidget(self.archive_search,1)
  self.archive_kmz_only=QCheckBox('Nur DJI-KMZ (übertragbar)');self.archive_kmz_only.setChecked(True);self.archive_kmz_only.toggled.connect(self.archive_filter);tools.addWidget(self.archive_kmz_only)
  self.archive_archived=QCheckBox('Archivierte zeigen');self.archive_archived.toggled.connect(self.archive_filter);tools.addWidget(self.archive_archived);card.addLayout(tools)
  self.archive_list=QListWidget();self.archive_list.setObjectName('missions');self.archive_list.setSelectionMode(QListWidget.SingleSelection);self.archive_list.setSpacing(4);self.archive_list.itemSelectionChanged.connect(self.archive_changed);self.archive_list.itemDoubleClicked.connect(lambda _:self.archive_use());card.addWidget(self.archive_list,1)
  self.archive_empty=QLabel('Noch nicht angemeldet.');self.archive_empty.setObjectName('emptyList');self.archive_empty.setAlignment(Qt.AlignCenter);card.addWidget(self.archive_empty,1);self.archive_list.hide()
  actions=QHBoxLayout();self.archive_selected=QLabel('Kein Eintrag ausgewählt.');self.archive_selected.setObjectName('muted');self.archive_selected.setWordWrap(True);actions.addWidget(self.archive_selected,1)
  self.archive_use_button=QPushButton('Für Übertragung verwenden');self.archive_use_button.setObjectName('primary');self.archive_use_button.setEnabled(False);self.archive_use_button.clicked.connect(self.archive_use);actions.addWidget(self.archive_use_button);card.addLayout(actions)
  label=QLabel('Die KMZ wird mit Prüfsumme aus dem Archiv geladen und als Quelle im Tab „Übertragen“ eingesetzt. Planungsdateien (MPROJ, LCHM, LCHZ) zuerst in Litchi oder Map Creator als DJI-KMZ exportieren.');label.setObjectName('muted');label.setWordWrap(True);layout.addWidget(label)

 def build_transfer_tab(self):
  tab=QWidget();layout=QVBoxLayout(tab);layout.setContentsMargins(0,14,0,0);layout.setSpacing(12);self.tabs.addTab(tab,'Übertragen')
  self.stack=QStackedWidget();layout.addWidget(self.stack,1)
  # Seite 1: Eingaben
  page=QWidget();columns=QHBoxLayout(page);columns.setContentsMargins(0,0,0,0);columns.setSpacing(14);self.stack.addWidget(page)
  left=self.card(columns,3)
  mode=QHBoxLayout();mode.setSpacing(6);self.mode_group=QButtonGroup(self);self.mode_group.setExclusive(True)
  self.mode_new=QPushButton('Neu anlegen');self.mode_replace=QPushButton('Ersetzen')
  for i,button in enumerate([self.mode_new,self.mode_replace]):button.setCheckable(True);button.setObjectName('segment');self.mode_group.addButton(button,i);mode.addWidget(button)
  mode.addStretch();left.addLayout(mode);self.mode_group.idClicked.connect(lambda i:self.set_mode('replace' if i else 'new'))
  self.mode_note=QLabel();self.mode_note.setObjectName('hintBox');self.mode_note.setWordWrap(True);left.addWidget(self.mode_note)
  # Ziel (nur Ersetzen)
  self.target_panel=QFrame();self.target_panel.setObjectName('target');target=QHBoxLayout(self.target_panel);target.setContentsMargins(12,10,12,10);target.setSpacing(14)
  self.target_image=QLabel();self.target_image.setFixedSize(THUMB);self.target_image.setObjectName('thumb');target.addWidget(self.target_image)
  text=QVBoxLayout();text.setSpacing(3);label=QLabel('Zu ersetzender Eintrag');label.setObjectName('sectionTitle');text.addWidget(label)
  self.target_name=QLabel('Noch kein Eintrag gewählt.');self.target_name.setObjectName('rowTitle');self.target_name.setWordWrap(True);text.addWidget(self.target_name)
  self.target_meta=QLabel('');self.target_meta.setObjectName('muted');text.addWidget(self.target_meta);text.addStretch();target.addLayout(text,1)
  button=QPushButton('Eintrag wählen …');button.setObjectName('quiet');button.clicked.connect(lambda:self.tabs.setCurrentIndex(TAB_DEVICE));target.addWidget(button,alignment=Qt.AlignTop);left.addWidget(self.target_panel)
  self.new_note=QLabel();self.new_note.setObjectName('muted');self.new_note.setWordWrap(True);left.addWidget(self.new_note)
  # Quelle
  label=QLabel('DJI-KMZ');label.setObjectName('sectionTitle');left.addWidget(label)
  row=QHBoxLayout();self.source_label=QLabel('Noch keine KMZ ausgewählt');self.source_label.setObjectName('fileName');self.source_label.setWordWrap(True);row.addWidget(self.source_label,1)
  button=QPushButton('KMZ auswählen …');button.clicked.connect(self.choose_kmz);row.addWidget(button);left.addLayout(row)
  self.source_meta=QLabel('Export aus Litchi, Map Creator oder dem Webarchiv.');self.source_meta.setObjectName('muted');self.source_meta.setWordWrap(True);left.addWidget(self.source_meta)
  label=QLabel('Missionsname');label.setObjectName('sectionTitle');left.addWidget(label)
  self.name=QLineEdit();self.name.setPlaceholderText('Zum Beispiel: Baustelle Nord · Panorama');self.name.setMaxLength(200);self.name.textChanged.connect(self.invalidate);left.addWidget(self.name)
  self.name_note=QLabel('Erscheint als Titel im Vorschaubild. Auf dem iPad auch als Listenname in DJI Fly; auf Android ist der Listenname für die Bridge nicht setzbar.');self.name_note.setObjectName('muted');self.name_note.setWordWrap(True);left.addWidget(self.name_note)
  left.addStretch(1)
  row=QHBoxLayout();row.addStretch();self.prepare_button=QPushButton('Vorschau prüfen');self.prepare_button.setObjectName('primary');self.prepare_button.clicked.connect(self.prepare);row.addWidget(self.prepare_button);left.addLayout(row)
  # rechts: Vorschaubild
  right=self.card(columns,2);self.heading(right,'Vorschaubild','Titelbild für DJI Fly. Ohne eigenes Bild wird die Route gezeichnet.')
  self.image=QLabel();self.image.setObjectName('preview');self.image.setMinimumSize(420,280);self.image.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding);self.image.setAlignment(Qt.AlignCenter);self.image.setPixmap(placeholder(QSize(420,280),'Vorschau erscheint nach „Vorschau prüfen“'));right.addWidget(self.image,1)
  self.preview_label=QLabel('Hintergrund: Route aus der KMZ.');self.preview_label.setObjectName('muted');self.preview_label.setWordWrap(True);right.addWidget(self.preview_label)
  row=QHBoxLayout();button=QPushButton('Eigenes Bild …');button.setObjectName('quiet');button.clicked.connect(self.choose_preview);row.addWidget(button)
  button=QPushButton('Bild entfernen');button.setObjectName('quiet');button.clicked.connect(self.clear_background);row.addWidget(button);row.addStretch();right.addLayout(row)
  # Seite 2: Prüfen und übertragen
  page=QWidget();review=QHBoxLayout(page);review.setContentsMargins(0,0,0,0);review.setSpacing(14);self.stack.addWidget(page)
  left=self.card(review,3);self.heading(left,'Passt alles?','Prüfe Titelbild, Name und Ziel. Vor jeder Übertragung wird der Bestand automatisch gesichert und jede Datei zurückgelesen.')
  self.review_image=QLabel();self.review_image.setObjectName('preview');self.review_image.setMinimumSize(540,360);self.review_image.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding);self.review_image.setAlignment(Qt.AlignCenter);left.addWidget(self.review_image,1)
  right=self.card(review,2)
  self.summary_mode=QLabel();self.summary_mode.setObjectName('eyebrow');right.addWidget(self.summary_mode)
  self.summary_name=QLabel();self.summary_name.setObjectName('pageTitle');self.summary_name.setWordWrap(True);right.addWidget(self.summary_name)
  self.summary_points=QLabel();self.summary_points.setObjectName('muted');right.addWidget(self.summary_points)
  self.summary_target=QLabel();self.summary_target.setWordWrap(True);right.addWidget(self.summary_target)
  self.review_note=QLabel();self.review_note.setWordWrap(True);self.review_note.setObjectName('hintBox');right.addWidget(self.review_note)
  right.addStretch(1)
  self.closed=QCheckBox('DJI Fly ist vollständig geschlossen. Es ist kein Flug aktiv.');self.closed.toggled.connect(lambda checked:self.apply_button.setEnabled(checked and self.transfer is not None));right.addWidget(self.closed)
  row=QHBoxLayout();self.back_button=QPushButton('Zurück');self.back_button.setObjectName('quiet');self.back_button.clicked.connect(lambda:self.stack.setCurrentIndex(0));row.addWidget(self.back_button);row.addStretch()
  self.apply_button=QPushButton('Jetzt übertragen');self.apply_button.setObjectName('primary');self.apply_button.setEnabled(False);self.apply_button.clicked.connect(self.execute);row.addWidget(self.apply_button);right.addLayout(row)

 def build_log_tab(self):
  tab=QWidget();layout=QVBoxLayout(tab);layout.setContentsMargins(0,14,0,0);layout.setSpacing(12);self.tabs.addTab(tab,'Protokoll && Einstellungen')
  card=self.card(layout,1);self.heading(card,'Protokoll','Jeder Schritt mit Zeitstempel. Sicherungen und Transferjournale liegen im Anwendungsdatenordner.')
  self.log=QPlainTextEdit();self.log.setReadOnly(True);card.addWidget(self.log,1)
  row=QHBoxLayout();button=QPushButton('Sicherungen öffnen');button.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.root))));row.addWidget(button);row.addStretch();card.addLayout(row)
  card=self.card(layout);self.heading(card,'Android-Verbindung','ADB wird nur für die Fernsteuerung benötigt. Für iPad/iPhone ist kein ADB nötig.')
  row=QHBoxLayout();self.adb=QLineEdit();self.adb.setReadOnly(True);fallback='/Applications/DJIKMZInjector.app/Contents/Frameworks/tools/adb' if sys.platform=='darwin' else '';self.adb.setText(self.settings.value('adb','') or shutil.which('adb') or fallback);self.adb.textChanged.connect(self.invalidate);row.addWidget(self.adb,1)
  button=QPushButton('ADB wählen …');button.clicked.connect(self.choose_adb);row.addWidget(button);card.addLayout(row)
  label=QLabel(f'Drone Missions Bridge {VERSION} · GPL-3.0-or-later · Lizenzen im Programmpaket. Dateiprüfung ist keine Bestätigung eines nutzbaren Flugplans.');label.setObjectName('muted');label.setWordWrap(True);layout.addWidget(label)
  # Rückwärtskompatibel: frühere Aufrufer öffneten einen Einstellungsdialog.
  self.settings_dialog=QWidget()

 # ---------- Zustand ----------
 def log_line(self,text):self.log.appendPlainText(datetime.now().strftime('%H:%M:%S')+'  '+text)
 def current_device(self):return self.device.currentData()
 def is_ios(self):r=self.current_device();return bool(r and r['kind']=='ios')
 def selected_row(self):
  i=self.list.currentRow();return self.rows[i] if 0<=i<len(self.rows) and self.list.currentItem() and self.list.currentItem().isSelected() else None
 def row_label(self,r,m,index):return m.get('name') or (self.registry.get(r['serial']+':'+m['uuid']) if r else None) or 'Eintrag '+str(index+1)
 def set_mode(self,mode):
  self.mode=mode;self.mode_new.setChecked(mode=='new');self.mode_replace.setChecked(mode=='replace')
  self.target_panel.setVisible(mode=='replace');self.new_note.setVisible(mode=='new');self.invalidate();self.update_mode_notes()
 def update_mode_notes(self):
  ios_device=self.is_ios();r=self.current_device()
  if self.mode=='new':
   self.mode_note.setText('Neue Mission mit eigener Kennung anlegen. Bestehende Missionen bleiben unverändert.'+('' if ios_device or not r else ' Auf Android ist der Neuimport experimentell: Die Dateien werden geprüft übertragen, die Sichtbarkeit in DJI Fly ist nicht bestätigt. Geprüfter Weg auf der RC Pro 2 ist „Ersetzen“.'))
   self.new_note.setText('Auf dem iPad/iPhone erscheint die Mission mit Name und Titelbild in DJI Fly.' if ios_device else 'Nach der Übertragung Gerät neu starten und in DJI Fly prüfen, ob die Mission erscheint.')
  else:
   self.mode_note.setText('Den gewählten Eintrag nach vollständiger Sicherung ersetzen. Dateien werden zuerst unter temporärem Namen geschrieben und zurückgelesen.'+(' Auf dem iPad ist das Ersetzen noch nicht am Gerät geprüft; geprüfter Weg ist „Neu anlegen“.' if ios_device else ' Auf der RC Pro 2 ist danach ein Neustart erforderlich.'))
  self.update_target_card()
 def update_target_card(self):
  m=self.selected_row();r=self.current_device()
  if not m:self.target_image.setPixmap(placeholder(THUMB,'Kein Eintrag'));self.target_name.setText('Noch kein Eintrag gewählt.');self.target_meta.setText('Im Tab „Gerät & Missionen“ die Liste lesen und einen Eintrag auswählen.');return
  pixmap=QPixmap()
  if m.get('image') and pixmap.loadFromData(m['image']):self.target_image.setPixmap(pixmap.scaled(THUMB,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation))
  else:self.target_image.setPixmap(placeholder(THUMB,'Kein Vorschaubild'))
  self.target_name.setText(self.row_label(r,m,self.list.currentRow()));self.target_meta.setText(f'{m.get("waypoints","—")} Wegpunkte · {STATE_LABELS.get(m.get("localState"),"—")} · Kennung {m["uuid"]}')
 def changed_device(self,*args):
  self.invalidate();self.rows=[];self.list.clear();self.list.hide();self.list_empty.show();self.list_empty.setText('Noch keine Missionen gelesen.')
  r=self.current_device();self.replace_button.setEnabled(False);self.selected_label.setText('Kein Eintrag ausgewählt.')
  if r:self.device_note.setText(('iPad/iPhone: Neue Mission mit Name und Titelbild anlegen (geprüft).' if r['kind']=='ios' else 'Fernsteuerung: Bestehenden Eintrag nach Sicherung ersetzen (geprüft). Danach Neustart erforderlich.')+' Vor jeder Übertragung wird der Bestand gesichert.')
  else:self.device_note.setText('Gerät auswählen, um fortzufahren.')
  self.update_mode_notes()
 def changed_target(self):
  m=self.selected_row();self.replace_button.setEnabled(m is not None and m.get('localState')=='local');r=self.current_device()
  if m:self.selected_label.setText(f'Ausgewählt: {self.row_label(r,m,self.list.currentRow())}'+('' if m.get('localState')=='local' else ' · nur lokal vorhandene Missionen lassen sich ersetzen'))
  else:self.selected_label.setText('Kein Eintrag ausgewählt.')
  self.invalidate();self.update_target_card()
 def invalidate(self,*args):
  self.transfer=None
  if hasattr(self,'apply_button'):self.apply_button.setEnabled(False)
  if hasattr(self,'stack') and self.stack.currentIndex()==1:self.stack.setCurrentIndex(0)
 def start_new(self):self.set_mode('new');self.tabs.setCurrentIndex(TAB_TRANSFER);self.status.setText('Neu anlegen: KMZ auswählen oder aus dem Webarchiv übernehmen, dann Missionsnamen eingeben.')
 def start_replace(self):
  if not self.selected_row():self.status.setText('Zuerst einen Eintrag in der Liste auswählen.');return
  self.set_mode('replace');self.tabs.setCurrentIndex(TAB_TRANSFER);self.status.setText('Ersetzen: KMZ auswählen, Namen eingeben, dann Vorschau prüfen.')
 def closeEvent(self,event):
  if self.job and self.job.isRunning():QMessageBox.information(self,'Aktion läuft','Bitte die laufende Aktion abschließen lassen.');event.ignore()
  else:event.accept()
 def selected_device(self):
  r=self.current_device()
  if not r or r.get('state')!='device':raise BridgeError('Bitte ein verbundenes, entsperrtes Gerät auswählen.')
  return dict(r)
 def adb_for(self,r):return Adb(self.adb.text().strip(),r['serial'])
 def task(self,label,fn,done):
  if self.job and self.job.isRunning():return
  self.status.setText(label);self.log_line(label);self.body.setEnabled(False);self.progress.show();j=Job(fn,self);self.job=j
  def enable():self.body.setEnabled(True);self.progress.hide()
  def ok(result):
   enable()
   try:done(result)
   except Exception as e:self.error(str(e))
  def fail(text):enable();self.error(text)
  j.result.connect(ok);j.error.connect(fail);j.start()
 def error(self,text):self.status.setText(text);self.log_line('FEHLER: '+text);QMessageBox.warning(self,'Bitte prüfen',text)

 # ---------- Dateien ----------
 def choose_adb(self):
  path,_=QFileDialog.getOpenFileName(self,'ADB auswählen')
  if path:self.adb.setText(path);self.settings.setValue('adb',path)
 def set_source(self,path):
  original=Path(path);self.original_source=original;self.source_path=original;self.source_label.setText(original.name);self.source_label.setToolTip(str(original));self.name.setText(original.stem);self.clear_background();self.invalidate()
  try:
   prepared=prepare_source(original,self.root/'cleaned');self.source_path=prepared['path'];details=inspect_kmz(self.source_path.read_bytes())
   text=f'{details["waypoints"]} Wegpunkte · {details["distance"]/1000:.2f} km · {len(details["segments"])} Flugroute(n)'
   if prepared['cleaned']:
    merged=', '.join(str(m['index']+1) for m in prepared['report']['merged']);text+=f' · Übertragungskopie: doppelter Schlusspunkt {merged} zusammengeführt (Stopp erhalten), Original unverändert';self.log_line(f'Übertragungskopie angelegt: {self.source_path} (Original {original})')
   self.source_meta.setText(text)
  except Exception as e:self.source_meta.setText('Datei kann nicht gelesen werden: '+str(e))
  for folder in [self.source_path.parent/'Preview',self.source_path.parent/'preview',self.source_path.parent]:
   thumb=folder/(self.source_path.stem+'.jpg')
   if thumb.is_file():self.background_path=thumb;self.preview_label.setText('Hintergrund: '+thumb.name);break
 def choose_kmz(self):
  path,_=QFileDialog.getOpenFileName(self,'DJI-KMZ auswählen','','DJI-KMZ (*.kmz *.KMZ)')
  if path:self.set_source(path)
 def choose_preview(self):
  path,_=QFileDialog.getOpenFileName(self,'Bildhintergrund auswählen','','Bilder (*.jpg *.jpeg *.png)')
  if path:self.background_path=Path(path);self.preview_label.setText('Hintergrund: '+Path(path).name);self.invalidate()
 def clear_background(self):self.background_path=None;self.preview_label.setText('Hintergrund: Route aus der KMZ.');self.invalidate()

 # ---------- Gerät ----------
 def refresh_devices(self):
  exe=self.adb.text().strip();previous=self.current_device()
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
   for text in errors:self.log_line(text)
  self.task('Verbundene Geräte suchen …',find,done)
 def list_missions(self):
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
  self.task('Missionen auf dem Gerät lesen …',read,lambda rows:self.show_rows(r,rows))
 def show_rows(self,r,rows):
  self.rows=rows;self.list.clear()
  for i,m in enumerate(rows):
   item=QListWidgetItem();item.setSizeHint(QSize(0,THUMB.height()+18));item.setToolTip('Kennung: '+m['uuid']);self.list.addItem(item);self.list.setItemWidget(item,MissionRow(self.row_label(r,m,i),m,m.get('image')))
  self.list.setVisible(bool(rows));self.list_empty.setVisible(not rows);self.list_empty.setText('Keine Missionen auf dem Gerät gefunden.')
  self.list_note.setText(f'{len(rows)} Missionen auf {r["name"]}. Vergleiche Bild und Punktzahl mit DJI Fly.'+(' Der Listenname auf Android ist für die Bridge nicht lesbar.' if r['kind']=='android' else ''))
  self.status.setText(f'{len(rows)} Missionen gelesen.');self.changed_target()
 def backup(self):
  try:r=self.selected_device();a=self.adb_for(r)
  except Exception as e:self.error(str(e));return
  if QMessageBox.question(self,'Bestand sichern','Ist kein Flug aktiv und DJI Fly vollständig geschlossen?\n\nDie Sicherung liest nur die vorhandenen Missionsdaten. Auf Android wird DJI Fly dabei beendet.')!=QMessageBox.Yes:return
  dest=self.root/'backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');dest.parent.mkdir(parents=True,exist_ok=True)
  self.task('Missionsbestand sichern und zurücklesen …',lambda:ios.run(ios.backup(r['serial'],dest)) if r['kind']=='ios' else a.snapshot(dest),lambda result:self.status.setText(f'{len(result["files"])} Dateien gesichert. Ablage im Tab „Protokoll“ öffnen.'))

 # ---------- Webarchiv ----------
 def archive_login(self):
  url=self.archive_url.text().strip();key=self.archive_key.text()
  def connect():
   client=self.client_factory(url);client.login(key);return client,client.library()
  def done(result):
   client,rows=result;self.archive=client;self.settings.setValue('archiveURL',url);self.archive_key.clear();self.archive_rows=rows
   self.archive_note.setText(f'Angemeldet als {"Eigentümer" if client.role=="owner" else "Freigabe"} · {len(rows)} Missionen in der Bibliothek.');self.status.setText(f'{len(rows)} Missionen aus dem Webarchiv geladen.');self.archive_filter();self.archive_previews()
  self.task('Am Webarchiv anmelden und Bibliothek laden …',connect,done)
 def archive_visible(self):
  q=self.archive_search.text().strip().lower();kmz=self.archive_kmz_only.isChecked();archived=self.archive_archived.isChecked()
  return [m for m in self.archive_rows if (not kmz or m['transferable']) and (archived or not m['archived']) and q in f"{m['name']} {m['folder']} {m['filename']}".lower()]
 def archive_filter(self,*args):
  rows=self.archive_visible();self.archive_list.clear();self.archive_widgets=[]
  for m in rows:
   item=QListWidgetItem();item.setSizeHint(QSize(0,THUMB.height()+18));item.setToolTip(m['filename']);item.setData(Qt.UserRole,m['id']);self.archive_list.addItem(item);widget=ArchiveRow(m);self.archive_list.setItemWidget(item,widget);self.archive_widgets.append((m,widget))
   if m.get('pixmap') is not None:widget.set_picture(m['pixmap'])
  self.archive_list.setVisible(bool(rows));self.archive_empty.setVisible(not rows);self.archive_empty.setText('Noch nicht angemeldet.' if not self.archive else 'Keine Mission passt zu Suche und Filter.');self.archive_changed()
 def archive_previews(self):
  client=self.archive;pending=[m for m in self.archive_rows if m['transferable'] and 'pixmap' not in m][:60]
  if not client or not pending:return
  def fetch():
   out=[]
   for m in pending:
    try:raw,content_type=client.preview(m);out.append((m['id'],raw,content_type))
    except Exception:out.append((m['id'],None,''))
   return out
  def done(results):
   for mission_id,raw,content_type in results:
    m=next((x for x in self.archive_rows if x['id']==mission_id),None)
    if m is None:continue
    m['pixmap']=picture_from(raw,content_type)
    for row,widget in self.archive_widgets:
     if row['id']==mission_id:widget.set_picture(m['pixmap'])
  self.task('Vorschaubilder laden …',fetch,done)
 def archive_current(self):
  item=self.archive_list.currentItem()
  if not item or not item.isSelected():return None
  return next((m for m in self.archive_rows if m['id']==item.data(Qt.UserRole)),None)
 def archive_changed(self):
  m=self.archive_current();self.archive_use_button.setEnabled(bool(m and m['transferable']))
  self.archive_selected.setText(f'Ausgewählt: {m["name"]} ({m["format"]})'+('' if m['transferable'] else ' · kein DJI-KMZ, nicht übertragbar') if m else 'Kein Eintrag ausgewählt.')
 def archive_use(self):
  m=self.archive_current()
  if not m or not m['transferable'] or not self.archive:return
  folder=self.root/'archive'/safe_filename(m['id']);destination=folder/(safe_filename(m['name'])+'.kmz')
  def download():return self.archive.download(m,destination)
  def done(path):
   self.set_source(path);self.name.setText(m['name']);self.source_meta.setText(self.source_meta.text()+f' · aus dem Webarchiv, V{m.get("version") or "?"}, Prüfsumme bestätigt');self.tabs.setCurrentIndex(TAB_TRANSFER);self.status.setText('KMZ aus dem Webarchiv übernommen. Jetzt Vorschau prüfen.')
  self.task('KMZ aus dem Webarchiv laden und prüfen …',download,done)

 # ---------- Übertragen ----------
 def prepare(self):
  self.invalidate()
  try:
   r=self.selected_device()
   if self.source_path is None:raise BridgeError('Bitte zuerst eine DJI-KMZ auswählen.')
   source=self.source_path;raw=source.read_bytes();details=inspect_kmz(raw);name=self.name.text().strip()
   if not name or len(name)>200:raise BridgeError('Bitte einen Missionsnamen bis 200 Zeichen eingeben.')
   preview=render_preview(self.root/'previews'/(uuid.uuid4().hex+'.jpg'),name,details,self.background_path);target=None
   if self.mode=='replace':
    m=self.selected_row()
    if not m:raise BridgeError('Bitte im Tab „Gerät & Missionen“ den Eintrag wählen, der ersetzt werden soll.')
    if m.get('localState')!='local':raise BridgeError('Nur lokal vorhandene Missionen lassen sich ersetzen. Cloud-Mission zuerst in DJI Fly herunterladen.')
    target=m['uuid'];target_name='Ersetzt: '+self.row_label(r,m,self.list.currentRow())
   else:target_name='Neue Mission auf '+r['name']
   prepared={'device':r,'source':str(source.resolve()),'originalSource':str(self.original_source.resolve()) if self.original_source else None,'sourceSha256':digest(raw),'name':name,'preview':str(preview),'previewSha256':digest(preview.read_bytes()),'kmz':details,'mode':'ios-replace' if target else 'ios-new','replace':target}
  except Exception as e:self.error(str(e));return
  mode=self.mode
  def prepare_plan():
   if r['kind']=='ios':return prepared
   result=plan(self.adb_for(r),source,name,preview,target);result['device']=r;result['originalSource']=str(self.original_source.resolve()) if self.original_source else None;return result
  def done(p):
   self.transfer=p;pixmap=QPixmap(str(preview))
   self.image.setPixmap(pixmap.scaled(self.image.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation));self.review_image.setPixmap(pixmap.scaled(self.review_image.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
   self.summary_mode.setText(('ERSETZEN' if mode=='replace' else 'NEU ANLEGEN')+' · '+r['name']);self.summary_name.setText(name);self.summary_points.setText(f'{details["waypoints"]} Wegpunkte · {details["distance"]/1000:.2f} km');self.summary_target.setText(target_name)
   if r['kind']=='ios':self.review_note.setText('Neue Mission mit Name und Titelbild. Anschließend in DJI Fly öffnen und bei Bedarf synchronisieren.' if mode=='new' else 'Der Eintrag wird nach Sicherung ersetzt (am iPad noch nicht geprüft). Anschließend in DJI Fly öffnen und Speichern prüfen.')
   else:self.review_note.setText('Der gewählte Eintrag wird nach Sicherung ersetzt. Anschließend RC Pro 2 neu starten, Mission öffnen und Speichern prüfen.' if mode=='replace' else 'Experimentell: Neue Kennung wird geprüft übertragen. Anschließend RC Pro 2 neu starten und prüfen, ob DJI Fly die Mission anzeigt.')
   self.closed.setChecked(False);self.stack.setCurrentIndex(1);self.tabs.setCurrentIndex(TAB_TRANSFER);self.status.setText('Noch nichts übertragen. Vorschau prüfen und DJI Fly schließen.')
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
  replacing=p['mode'] in ('replace','ios-replace')
  # Die Prüfseite ist die ausdrückliche Bestätigung; kein zweiter Dialog.
  def done(result):
   self.registry[r['serial']+':'+result['uuid']]=p['name'];atomic_json(self.root/'names.json',self.registry);self.transfer=None;self.apply_button.setEnabled(False);self.log_line('Sicherung und Protokoll: '+str(dest));self.status.setText('Übertragen und zurückgelesen. Jetzt in DJI Fly öffnen und Speichern prüfen.');self.stack.setCurrentIndex(0);self.rows=[];self.list.clear();self.list.hide();self.list_empty.show();self.list_empty.setText('Liste erneut lesen, um den neuen Stand zu sehen.')
   QMessageBox.information(self,'Übertragung geprüft',('KMZ und Titelvorschau wurden im gewählten Eintrag ersetzt.' if replacing else 'Die neue Mission ist mit Name und Vorschau eingetragen.')+'\n\n'+('Jetzt DJI Fly öffnen und Mission sowie Cloud-Synchronisation prüfen.' if r['kind']=='ios' else 'Jetzt RC Pro 2 neu starten und Mission in DJI Fly prüfen.')+'\n\nDie Sicherung ist im Tab „Protokoll“ erreichbar.')
  self.task('Mission sichern, übertragen und zurücklesen …',lambda:ios.run(ios.apply_new(r['serial'],Path(p['source']),p['name'],Path(p['preview']),dest,fly_closed=True,replace=p.get('replace'))) if r['kind']=='ios' else apply(self.adb_for(r),p,dest),done)

STYLE='''
QWidget{background:#f4f6f2;color:#173c31;font-family:"Helvetica Neue","Segoe UI";font-size:13px}QMainWindow,QDialog,QMessageBox{background:#f4f6f2}QToolTip{background:#173c31;color:white;border:none;padding:6px}QComboBox QAbstractItemView{background:white;color:#173c31;selection-background-color:#dcebd3;selection-color:#173c31}
QLabel#windowTitle{font-size:22px;font-weight:650;background:transparent}QLabel#pageTitle{font-size:20px;font-weight:600;background:transparent}
QLabel#eyebrow{font-size:11px;font-weight:650;letter-spacing:1px;color:#6e7c75;background:transparent}
QLabel#sectionTitle,QLabel#fileName{font-weight:600;background:transparent}QLabel#muted{color:#6e7c75;font-size:12px;background:transparent}
QLabel#rowTitle{font-size:15px;font-weight:600;background:transparent}QLabel#ident{color:#95a19a;font-size:11px;background:transparent}
QLabel#thumb{background:#1b332b;border-radius:8px}QLabel#emptyList{color:#85918b;font-size:14px;background:transparent}
QTabWidget::pane{border:none;background:#f4f6f2}QTabWidget::tab-bar{alignment:left}QTabBar{background:#f4f6f2;border-bottom:1px solid #dbe2db}QTabBar::tab{background:#f4f6f2;color:#6e7c75;padding:10px 18px;margin-right:4px;border-bottom:2px solid transparent;font-size:14px}
QTabBar::tab:selected{color:#173c31;font-weight:650;border-bottom:3px solid #54856a}QTabBar::tab:hover{color:#173c31;background:#edf2e9}
QFrame#card{background:white;border:1px solid #dce3dc;border-radius:12px}QFrame#card QWidget{background:white}QFrame#card QLabel{background:transparent}
QFrame#card QPushButton{background:#edf2e9}QFrame#card QPushButton#quiet{background:transparent}QFrame#card QPushButton#primary{background:#254e3b}QFrame#card QPushButton#primary:hover{background:#35644d}QFrame#card QPushButton#primary:disabled{background:#e7ece5}QFrame#card QPushButton#segment{background:#f1f5ed}QFrame#card QPushButton#segment:checked{background:#254e3b}
QFrame#card QListWidget#missions QWidget{background:transparent}QFrame#card QLabel#thumb,QFrame#card QLabel#preview{background:#1b332b}QFrame#card QLabel#hintBox{background:#edf3e9}QFrame#card QLineEdit,QFrame#card QPlainTextEdit{background:white}
QFrame#card QFrame#target{background:#f3f7ef;border:1px solid #d7e2d1;border-radius:10px}QFrame#card QFrame#target QPushButton#quiet{background:white}
QLabel#hintBox{background:#edf3e9;color:#395b47;border-radius:8px;padding:12px;font-size:12px}
QLabel#status{color:#67776c;font-size:12px;min-height:22px}QLabel#preview{background:#152e2b;border-radius:10px}
QPushButton{background:#edf2e9;color:#254735;border:1px solid #d3dece;border-radius:7px;padding:9px 14px;font-weight:550}
QPushButton:hover{background:#e2ebda}QPushButton#quiet{background:transparent;border:1px solid #d8e0d7;color:#5d7063;font-size:12px;padding:8px 12px}
QPushButton#primary{background:#254e3b;color:white;border:1px solid #254e3b;min-width:150px}
QPushButton#primary:hover{background:#35644d}QPushButton:disabled,QPushButton#primary:disabled{color:#9ca79e;background:#e7ece5;border-color:#dce3da}
QPushButton#segment{background:#f1f5ed;color:#5d7063;border:1px solid #d3dece;padding:9px 18px;min-width:120px}
QPushButton#segment:checked{background:#254e3b;color:white;border-color:#254e3b;font-weight:650}
QLineEdit,QComboBox{background:white;border:1px solid #ced9cd;border-radius:6px;padding:9px;min-height:20px;selection-background-color:#dbe9d3}
QListWidget#missions{background:white;border:1px solid #d9e2d7;border-radius:8px;outline:none}
QListWidget#missions::item{border-bottom:1px solid #edf0ea;border-radius:6px}
QListWidget#missions::item:selected{background:#dcebd3}QListWidget#missions::item:hover{background:#f1f5ed}
QPlainTextEdit{background:white;border:1px solid #d7e0d4;border-radius:6px;font-family:Menlo,monospace;font-size:11px;padding:8px}
QCheckBox{spacing:9px;font-size:12px}QCheckBox::indicator{width:19px;height:19px;border:1px solid #a8b9a3;border-radius:4px;background:white}
QCheckBox::indicator:checked{background:#345e43;border:3px solid #a6c794}
QProgressBar{background:#e1e9dc;border:none;border-radius:2px}QProgressBar::chunk{background:#7b9f68}
QScrollBar:vertical{background:transparent;width:10px}QScrollBar::handle:vertical{background:#cdd8c9;border-radius:5px;min-height:30px}
'''
def main():
 if '--diagnose' in sys.argv:
  target=Path(sys.argv[sys.argv.index('--diagnose')+1]);rows=ios.run(ios.discover());result={'iosDevices':len(rows),'paired':sum(r['state']=='device' for r in rows)}
  if rows and rows[0]['state']=='device':result['readableMissions']=len(ios.run(ios.list_missions(rows[0]['serial'],target.parent/'diagnostic-reads')))
  atomic_json(target,result);return
 app=QApplication(sys.argv);app.setOrganizationName('studiobaff');app.setApplicationName('Drone Missions Bridge');app.setStyle('Fusion');app.setStyleSheet(STYLE);window=Window();window.show();sys.exit(app.exec())
if __name__=='__main__':main()
