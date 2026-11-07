"""GPL-3.0-or-later. Desktop mission transfer UI: Gerät & Missionen · Übertragen · Protokoll.

Die Gerätefunktionen (core.py, ios.py, preview.py, map_preview.py) sind unverändert; diese Datei ist nur Oberfläche.
"""
from __future__ import annotations
import json,os,re,shutil,sys,uuid
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QThread,Signal,QSettings,QStandardPaths,Qt,QUrl,QTimer,QSize
from PySide6.QtGui import QDesktopServices,QPixmap,QPainter,QColor,QFont,QIcon,QAction,QKeySequence
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,
 QLabel,QPushButton,QComboBox,QLineEdit,QFileDialog,QListWidget,QListWidgetItem,QPlainTextEdit,
 QMessageBox,QCheckBox,QStackedWidget,QFrame,QProgressBar,QTabWidget,QButtonGroup,QSizePolicy,QScrollArea,QInputDialog)
from PySide6.QtSvg import QSvgRenderer
from core import Adb,devices,plan,apply,atomic_json,BridgeError,inspect_kmz,digest,BASE,prepare_source,bundled_adb
from preview import render_preview
from map_preview import map_background
from archive import ArchiveClient,safe_filename
import credentials
import ios

VERSION='0.4.2'
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

def app_icon():
 base=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
 for candidate in [base/'assets'/'icon.png',Path(__file__).resolve().parent/'assets'/'icon.png']:
  if candidate.is_file():return QIcon(str(candidate))
 return QIcon()

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
 def __init__(self,label,mission,image=None,checked=False,on_toggle=None):
  super().__init__();layout=QHBoxLayout(self);layout.setContentsMargins(10,8,10,8);layout.setSpacing(16)
  self.check=QCheckBox();self.check.setChecked(checked);self.check.setToolTip('Für „Im Webarchiv sichern“ auswählen')
  if on_toggle:self.check.toggled.connect(lambda state:on_toggle(mission['uuid'],state))
  layout.addWidget(self.check,alignment=Qt.AlignVCenter)
  picture=QLabel();picture.setFixedSize(THUMB);picture.setObjectName('thumb');picture.setAlignment(Qt.AlignCenter)
  pixmap=QPixmap()
  if image and pixmap.loadFromData(image):picture.setPixmap(pixmap.scaled(THUMB,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation))
  else:picture.setPixmap(placeholder(THUMB,'Kein Vorschaubild'))
  layout.addWidget(picture)
  text=QVBoxLayout();text.setSpacing(4);title=QLabel(label);title.setObjectName('rowTitle');title.setWordWrap(True);text.addWidget(title)
  waypoints=mission.get('waypoints','—');meta=QLabel(f'{waypoints} Wegpunkte · {STATE_LABELS.get(mission.get("localState"),"—")}');meta.setObjectName('muted');text.addWidget(meta)
  ident=QLabel('Kennung '+mission['uuid']);ident.setObjectName('ident');text.addWidget(ident);text.addStretch();layout.addLayout(text,1)

class Window(QMainWindow):
 def __init__(self,autosearch=True,credential_store=None,client_factory=None):
  super().__init__();self.setWindowTitle(f'Drone Missions Bridge · {VERSION}');self.setWindowIcon(app_icon());self.resize(1180,820);self.setMinimumSize(980,700)
  self.settings=QSettings('studiobaff','DroneMissionsBridge');self.root=Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation));self.root.mkdir(parents=True,exist_ok=True)
  self.transfer=None;self.rows=[];self.registry={};self.job=None;self.source_path=None;self.background_path=None;self.mode='new';self.prepared=None
  self.archive=None;self.archive_rows=[];self.archive_widgets=[];self.client_factory=client_factory or ArchiveClient;self.credential_store=credential_store or credentials;self.original_source=None;self.archive_auto=False;self.checked=set();self.device_rows_widgets=[];self.preview_mode=self.settings.value('previewMode','3d') or '3d'
  try:self.registry=json.loads((self.root/'names.json').read_text())
  except (OSError,ValueError):pass
  self.body=QWidget();outer=QVBoxLayout(self.body);outer.setContentsMargins(24,18,24,18);outer.setSpacing(14);self.setCentralWidget(self.body)
  self.build_header(outer)
  self.tabs=QTabWidget();self.tabs.setObjectName('tabs');self.tabs.setDocumentMode(True);outer.addWidget(self.tabs,1)
  self.build_device_tab();self.build_archive_tab();self.build_transfer_tab();self.build_log_tab()
  self.progress=QProgressBar();self.progress.setRange(0,0);self.progress.setFixedHeight(4);self.progress.setTextVisible(False);self.progress.hide();outer.addWidget(self.progress)
  self.status=QLabel('iPad oder Fernsteuerung per USB verbinden.');self.status.setObjectName('status');self.status.setWordWrap(True);outer.addWidget(self.status)
  self.set_mode('new');self.changed_device();self.build_menu()
  self.tabs.currentChanged.connect(lambda i:self.archive_login() if i==TAB_ARCHIVE and self.archive_auto and self.archive is None and not (self.job and self.job.isRunning()) else None)
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
  tools=QHBoxLayout();self.device_search=QLineEdit();self.device_search.setPlaceholderText('Name oder Kennung suchen …');self.device_search.textChanged.connect(self.render_device_list);tools.addWidget(self.device_search,1)
  self.device_local_only=QCheckBox('Nur lokal vorhanden');self.device_local_only.setToolTip('Nur Missionen mit heruntergeladener KMZ anzeigen; reine Cloud-Einträge ausblenden.');self.device_local_only.setChecked(self.settings.value('deviceLocalOnly',False,type=bool));self.device_local_only.toggled.connect(lambda value:(self.settings.setValue('deviceLocalOnly',value),self.render_device_list()));tools.addWidget(self.device_local_only)
  self.select_all=QCheckBox('Alle sichtbaren');self.select_all.setTristate(True);self.select_all.toggled.connect(self.toggle_all_visible);tools.addWidget(self.select_all)
  self.checked_label=QLabel('0 ausgewählt');self.checked_label.setObjectName('muted');tools.addWidget(self.checked_label)
  self.save_web_button=QPushButton('Im Webarchiv sichern …');self.save_web_button.setEnabled(False);self.save_web_button.clicked.connect(self.save_to_archive);tools.addWidget(self.save_web_button);card.addLayout(tools)
  self.list=QListWidget();self.list.setObjectName('missions');self.list.setSelectionMode(QListWidget.SingleSelection);self.list.setSpacing(4);self.list.setUniformItemSizes(False);self.list.itemSelectionChanged.connect(self.changed_target);self.list.itemDoubleClicked.connect(lambda _:self.start_replace());card.addWidget(self.list,1)
  self.list_empty=QLabel('Noch keine Missionen gelesen.');self.list_empty.setObjectName('emptyList');self.list_empty.setAlignment(Qt.AlignCenter);card.addWidget(self.list_empty,1)
  actions=QHBoxLayout();self.selected_label=QLabel('Kein Eintrag ausgewählt.');self.selected_label.setObjectName('muted');self.selected_label.setWordWrap(True);actions.addWidget(self.selected_label,1)
  self.rename_button=QPushButton('Umbenennen …');self.rename_button.setObjectName('quiet');self.rename_button.setEnabled(False);self.rename_button.clicked.connect(self.rename_selected);actions.addWidget(self.rename_button)
  self.new_button=QPushButton('Neu anlegen');self.new_button.setObjectName('primary');self.new_button.clicked.connect(self.start_new);actions.addWidget(self.new_button)
  self.replace_button=QPushButton('Ausgewählte ersetzen …');self.replace_button.setObjectName('primary');self.replace_button.setEnabled(False);self.replace_button.clicked.connect(self.start_replace);actions.addWidget(self.replace_button);card.addLayout(actions)

 def build_archive_tab(self):
  tab=QWidget();layout=QVBoxLayout(tab);layout.setContentsMargins(0,14,0,0);layout.setSpacing(12);self.tabs.addTab(tab,'Webarchiv')
  card=self.card(layout,1)
  row=QHBoxLayout();text=QVBoxLayout();text.setSpacing(2);title=QLabel('Missionen aus dem Webarchiv');title.setObjectName('pageTitle');text.addWidget(title)
  self.archive_note=QLabel('Mit dem Zugangsschlüssel anmelden. Der Schlüssel bleibt nur für diese Sitzung im Speicher.');self.archive_note.setObjectName('muted');self.archive_note.setWordWrap(True);text.addWidget(self.archive_note);row.addLayout(text,1);card.addLayout(row)
  grid=QGridLayout();grid.setHorizontalSpacing(10);grid.setVerticalSpacing(4)
  saved_url=self.settings.value('archiveURL','') or '';
  if re.match(r'^https?://(?:127\.0\.0\.1|localhost|\[::1\]|example\.(?:com|net|org))(?=[:/]|$)',saved_url,re.I) and not os.environ.get('DRONEMISSIONS_DEV'):saved_url='';self.settings.setValue('archiveURL',ARCHIVE_URL)
  grid.addWidget(QLabel('Archiv-Adresse'),0,0);self.archive_url=QLineEdit(saved_url or ARCHIVE_URL);self.archive_url.setPlaceholderText(ARCHIVE_URL);grid.addWidget(self.archive_url,1,0)
  grid.addWidget(QLabel('Zugangsschlüssel'),0,1);self.archive_key=QLineEdit();self.archive_key.setEchoMode(QLineEdit.Password);self.archive_key.setPlaceholderText('Nur für diese Sitzung');self.archive_key.returnPressed.connect(self.archive_login);grid.addWidget(self.archive_key,1,1)
  self.archive_login_button=QPushButton('Anmelden und Bibliothek laden');self.archive_login_button.clicked.connect(self.archive_login);grid.addWidget(self.archive_login_button,1,2)
  config=QPushButton('Konfiguration laden …');config.setObjectName('quiet');config.setToolTip('Konfigurationsdatei aus dem Webarchiv (Bereich „Bridge“) einlesen: setzt die Archiv-Adresse.');config.clicked.connect(lambda checked=False:self.archive_import_config());grid.addWidget(config,1,3);grid.setColumnStretch(0,3);grid.setColumnStretch(1,2);card.addLayout(grid)
  remember=QHBoxLayout();self.store_pref=self.settings.value('credentialStore','auto') or 'auto';stores=self.credential_store.available()
  self.archive_remember=QCheckBox('Schlüssel merken');self.archive_remember.setEnabled(bool(stores));remember.addWidget(self.archive_remember)
  remember.addWidget(QLabel('in'));self.archive_store=QComboBox();labels={'keychain':'macOS-Schlüsselbund','1password':'1Password','dpapi':'Windows (DPAPI)'}
  for key in stores:self.archive_store.addItem(labels[key],key)
  if not stores:self.archive_store.addItem('kein Schlüsselspeicher verfügbar',None)
  index=self.archive_store.findData(self.store_pref);self.archive_store.setCurrentIndex(index if index>=0 else 0);self.archive_store.currentIndexChanged.connect(lambda _:self.settings.setValue('credentialStore',self.archive_store.currentData() or 'auto'));remember.addWidget(self.archive_store)
  self.archive_forget=QPushButton('Schlüssel vergessen');self.archive_forget.setObjectName('quiet');self.archive_forget.setEnabled(False);self.archive_forget.clicked.connect(self.archive_forget_key);remember.addWidget(self.archive_forget);remember.addStretch();card.addLayout(remember)
  self.archive_restore_key()
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
  right=self.card(columns,2);self.heading(right,'Vorschaubild','Titelbild für DJI Fly. Festes Bild, in DJI Fly nicht drehbar.')
  modes=QHBoxLayout();modes.setSpacing(6);self.preview_group=QButtonGroup(self);self.preview_group.setExclusive(True)
  self.preview_3d=QPushButton('3D-Ansicht');self.preview_map=QPushButton('Luftbild');self.preview_image_button=QPushButton('Eigenes Bild …')
  for i,button in enumerate([self.preview_3d,self.preview_map,self.preview_image_button]):button.setCheckable(True);button.setObjectName('segment');self.preview_group.addButton(button,i);modes.addWidget(button)
  modes.addStretch();right.addLayout(modes);self.preview_group.idClicked.connect(lambda i:self.set_preview_mode(['3d','map','image'][i]))
  self.image=QLabel();self.image.setObjectName('preview');self.image.setMinimumSize(420,280);self.image.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding);self.image.setAlignment(Qt.AlignCenter);self.image.setPixmap(placeholder(QSize(420,280),'Vorschau erscheint nach „Vorschau prüfen“'));right.addWidget(self.image,1)
  self.preview_label=QLabel();self.preview_label.setObjectName('muted');self.preview_label.setWordWrap(True);right.addWidget(self.preview_label)
  self.set_preview_mode(self.preview_mode,choose=False)
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
  row=QHBoxLayout();self.adb=QLineEdit();self.adb.setReadOnly(True);bundled=bundled_adb();saved=self.settings.value('adb','')
  self.adb.setText(saved or (str(bundled) if bundled else '') or shutil.which('adb') or '');self.adb.textChanged.connect(self.invalidate);row.addWidget(self.adb,1)
  button=QPushButton('ADB wählen …');button.clicked.connect(self.choose_adb);row.addWidget(button)
  reset=QPushButton('Eingebautes ADB');reset.setObjectName('quiet');reset.setEnabled(bundled is not None);reset.clicked.connect(lambda:(self.settings.remove('adb'),self.adb.setText(str(bundled))));row.addWidget(reset);card.addLayout(row)
  self.adb_note=QLabel('Eingebautes ADB aus den Android Platform-Tools 37.0.1, Prüfsumme bestätigt.' if bundled and not saved else ('Eigener ADB-Pfad aus den Einstellungen.' if saved else 'Kein ADB gefunden. Für die Fernsteuerung ADB wählen; iPad/iPhone funktioniert ohne.'));self.adb_note.setObjectName('muted');self.adb_note.setWordWrap(True);card.addWidget(self.adb_note)
  label=QLabel(f'Drone Missions Bridge {VERSION} · GPL-3.0-or-later · Lizenzen im Programmpaket. Dateiprüfung ist keine Bestätigung eines nutzbaren Flugplans.');label.setObjectName('muted');label.setWordWrap(True);layout.addWidget(label)
  # Rückwärtskompatibel: frühere Aufrufer öffneten einen Einstellungsdialog.
  self.settings_dialog=QWidget()

 def build_menu(self):
  """Native Menüleiste (macOS oben, Windows im Fenster) mit den Hauptfunktionen und Tastenkürzeln."""
  bar=self.menuBar();bar.setNativeMenuBar(True);self.menu_actions={}
  def add(menu,text,slot,shortcut=None,role=None):
   action=QAction(text,self);action.triggered.connect(lambda *_:slot())
   if shortcut:action.setShortcut(QKeySequence(shortcut))
   if role is not None:action.setMenuRole(role)
   menu.addAction(action);self.menu_actions[text]=action;return action
  datei=bar.addMenu('Datei');add(datei,'KMZ auswählen …',self.choose_kmz,'Ctrl+O');add(datei,'Eigenes Vorschaubild …',self.choose_preview,'Ctrl+Shift+O');add(datei,'Bridge-Konfiguration laden …',self.archive_import_config);datei.addSeparator()
  add(datei,'Sicherungen öffnen',lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.root))));datei.addSeparator();add(datei,'Beenden',self.close,'Ctrl+Q',QAction.QuitRole)
  geraet=bar.addMenu('Gerät');add(geraet,'Geräte neu suchen',self.refresh_devices,'Ctrl+R');add(geraet,'Missionen lesen',self.list_missions,'Ctrl+L');add(geraet,'Gerät sichern …',self.backup,'Ctrl+B');geraet.addSeparator()
  add(geraet,'Umbenennen …',self.rename_selected,'Ctrl+E');add(geraet,'Neu anlegen',self.start_new,'Ctrl+N');add(geraet,'Ausgewählte ersetzen …',self.start_replace,'Ctrl+Shift+R');geraet.addSeparator();add(geraet,'Im Webarchiv sichern …',self.save_to_archive,'Ctrl+S')
  archiv=bar.addMenu('Webarchiv');add(archiv,'Anmelden und Bibliothek laden',lambda:(self.tabs.setCurrentIndex(TAB_ARCHIVE),self.archive_login()),'Ctrl+Shift+L');add(archiv,'Ausgewählte für Übertragung verwenden',self.archive_use,'Ctrl+U');archiv.addSeparator();add(archiv,'Webarchiv im Browser öffnen',lambda:QDesktopServices.openUrl(QUrl(self.archive_url.text().strip() or ARCHIVE_URL)))
  transfer=bar.addMenu('Übertragen');add(transfer,'Vorschau prüfen',self.prepare,'Ctrl+Return');add(transfer,'Jetzt übertragen',self.execute,'Ctrl+Shift+Return');transfer.addSeparator();add(transfer,'Modus: Neu anlegen',lambda:self.set_mode('new'));add(transfer,'Modus: Ersetzen',lambda:self.set_mode('replace'))
  ansicht=bar.addMenu('Ansicht')
  for i,title in enumerate(['Gerät & Missionen','Webarchiv','Übertragen','Protokoll & Einstellungen']):add(ansicht,title,lambda i=i:self.tabs.setCurrentIndex(i),f'Ctrl+{i+1}')
  hilfe=bar.addMenu('Hilfe');add(hilfe,'Anleitung (README)',lambda:QDesktopServices.openUrl(QUrl('https://github.com/studiobaff/dronemissions/blob/main/dronemissions/docs/BRIDGE.md')));add(hilfe,'Über Drone Missions Bridge',self.about,None,QAction.AboutRole)
 def about(self):
  QMessageBox.about(self,'Über Drone Missions Bridge',f'<b>Drone Missions Bridge {VERSION}</b><br>Überträgt DJI-KMZ-Missionen aus dem Webarchiv per USB auf iPad, iPhone oder DJI-Fernsteuerung.<br><br>GPL-3.0-or-later · Lizenzen im Programmpaket.<br>Dateiprüfung ist keine Bestätigung eines nutzbaren Flugplans.')

 # ---------- Zustand ----------
 def log_line(self,text):self.log.appendPlainText(datetime.now().strftime('%H:%M:%S')+'  '+text)
 def current_device(self):return self.device.currentData()
 def is_ios(self):r=self.current_device();return bool(r and r['kind']=='ios')
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
  self.target_name.setText(self.row_label(r,m,self.rows.index(m)));self.target_meta.setText(f'{m.get("waypoints","—")} Wegpunkte · {STATE_LABELS.get(m.get("localState"),"—")} · Kennung {m["uuid"]}')
 def changed_device(self,*args):
  self.invalidate();self.rows=[];self.checked=set();self.list.clear();self.list.hide();self.list_empty.show();self.list_empty.setText('Noch keine Missionen gelesen.')
  r=self.current_device();self.replace_button.setEnabled(False);self.selected_label.setText('Kein Eintrag ausgewählt.')
  if hasattr(self,'checked_label'):self.update_checked()
  if r:self.device_note.setText(('iPad/iPhone: Neue Mission mit Name und Titelbild anlegen (geprüft).' if r['kind']=='ios' else 'Fernsteuerung: Bestehenden Eintrag nach Sicherung ersetzen (geprüft). Danach Neustart erforderlich.')+' Vor jeder Übertragung wird der Bestand gesichert.')
  else:self.device_note.setText('Gerät auswählen, um fortzufahren.')
  self.update_mode_notes()
 def changed_target(self):
  m=self.selected_row();self.replace_button.setEnabled(m is not None and m.get('localState')=='local');r=self.current_device()
  self.rename_button.setEnabled(m is not None);self.rename_button.setToolTip('Name in DJI Fly ändern (iPad/iPhone)' if r and r['kind']=='ios' else 'Auf Android nur das Etikett in der Bridge; der DJI-Fly-Name ist dort nicht erreichbar.')
  if m:self.selected_label.setText(f'Ausgewählt: {self.row_label(r,m,self.rows.index(m))}'+('' if m.get('localState')=='local' else ' · nur lokal vorhandene Missionen lassen sich ersetzen'))
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
  if path:self.adb.setText(path);self.settings.setValue('adb',path);self.adb_note.setText('Eigener ADB-Pfad aus den Einstellungen.')
 def set_source(self,path):
  original=Path(path);self.original_source=original;self.source_path=original;self.source_label.setText(original.name);self.source_label.setToolTip(str(original));self.name.setText(original.stem);self.invalidate()
  try:
   prepared=prepare_source(original,self.root/'cleaned');self.source_path=prepared['path'];details=inspect_kmz(self.source_path.read_bytes())
   text=f'{details["waypoints"]} Wegpunkte · {details["distance"]/1000:.2f} km · {len(details["segments"])} Flugroute(n)'
   if prepared['cleaned']:
    merged=', '.join(str(m['index']+1) for m in prepared['report']['merged']);text+=f' · Übertragungskopie: doppelter Schlusspunkt {merged} zusammengeführt (Stopp erhalten), Original unverändert';self.log_line(f'Übertragungskopie angelegt: {self.source_path} (Original {original})')
   self.source_meta.setText(text)
  except Exception as e:self.source_meta.setText('Datei kann nicht gelesen werden: '+str(e))
 def choose_kmz(self):
  path,_=QFileDialog.getOpenFileName(self,'DJI-KMZ auswählen','','DJI-KMZ (*.kmz *.KMZ)')
  if path:self.set_source(path)
 def set_preview_mode(self,mode,choose=True):
  if mode=='image' and choose:
   path,_=QFileDialog.getOpenFileName(self,'Bildhintergrund auswählen','','Bilder (*.jpg *.jpeg *.png)')
   if not path:self.set_preview_mode('image' if self.background_path else '3d',choose=False);return
   self.background_path=Path(path)
  if mode!='image':self.background_path=None
  self.preview_mode=mode if mode!='image' or self.background_path else '3d'
  if self.preview_mode!='image':self.settings.setValue('previewMode',self.preview_mode)
  for button,key in [(self.preview_3d,'3d'),(self.preview_map,'map'),(self.preview_image_button,'image')]:button.setChecked(key==self.preview_mode)
  self.preview_label.setText({'3d':'3D-Ansicht: Route schräg mit echten Wegpunkthöhen, offline erzeugt; ohne vergleichbare Höhen Draufsicht.','map':'Luftbild: Route auf dem basemap.at-Orthofoto (nur Österreich, braucht Internet). Fällt sonst auf die 3D-Ansicht zurück.','image':'Eigenes Bild: '+(self.background_path.name if self.background_path else '')}[self.preview_mode]);self.invalidate()
 def choose_preview(self):self.set_preview_mode('image')
 def clear_background(self):self.set_preview_mode('3d',choose=False)

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
  self.rows=rows;self.checked=set();self.render_device_list()
  self.list_note.setText(f'{len(rows)} Missionen auf {r["name"]}. Vergleiche Bild und Punktzahl mit DJI Fly.'+(' Der Listenname auf Android ist für die Bridge nicht lesbar.' if r['kind']=='android' else ''))
  self.status.setText(f'{len(rows)} Missionen gelesen.');self.changed_target()
 def visible_rows(self):
  q=self.device_search.text().strip().lower();r=self.current_device()
  return [(i,m) for i,m in enumerate(self.rows) if (not self.device_local_only.isChecked() or m.get('localState')=='local') and (not q or q in self.row_label(r,m,i).lower() or q in m['uuid'].lower())]
 def render_device_list(self,*args):
  r=self.current_device();current=self.selected_row();self.list.clear();self.device_rows_widgets=[]
  for i,m in self.visible_rows():
   item=QListWidgetItem();item.setSizeHint(QSize(0,THUMB.height()+18));item.setToolTip('Kennung: '+m['uuid']);item.setData(Qt.UserRole,i);self.list.addItem(item)
   widget=MissionRow(self.row_label(r,m,i),m,m.get('image'),checked=m['uuid'] in self.checked,on_toggle=self.toggle_checked);self.list.setItemWidget(item,widget);self.device_rows_widgets.append((m,widget))
   if current and current['uuid']==m['uuid']:self.list.setCurrentItem(item)
  visible=bool(self.device_rows_widgets);self.list.setVisible(visible);self.list_empty.setVisible(not visible);self.list_empty.setText('Keine Mission passt zu Suche und Filter.' if self.rows else 'Keine Missionen auf dem Gerät gefunden.');self.update_checked()
 def selected_row(self):
  item=self.list.currentItem();i=item.data(Qt.UserRole) if item and item.isSelected() else None
  return self.rows[i] if isinstance(i,int) and 0<=i<len(self.rows) else None
 def toggle_checked(self,uid,state):
  if state:self.checked.add(uid)
  else:self.checked.discard(uid)
  self.update_checked()
 def toggle_all_visible(self,state):
  for _,m in self.visible_rows():
   if state:self.checked.add(m['uuid'])
   else:self.checked.discard(m['uuid'])
  for m,widget in self.device_rows_widgets:widget.check.blockSignals(True);widget.check.setChecked(m['uuid'] in self.checked);widget.check.blockSignals(False)
  self.update_checked()
 def update_checked(self):
  local=[m for m in self.rows if m['uuid'] in self.checked and m.get('localState')=='local'];total=len([m for m in self.rows if m['uuid'] in self.checked])
  visible_ids={m['uuid'] for _,m in self.visible_rows()};hidden=len(self.checked-visible_ids)
  self.checked_label.setText(f'{total} ausgewählt'+(f' · {len(local)} lokal' if total and len(local)!=total else '')+(f' · {hidden} ausgeblendet' if hidden else ''))
  self.save_web_button.setEnabled(bool(local) and self.archive is not None);self.save_web_button.setToolTip('' if self.archive else 'Zuerst im Tab „Webarchiv“ anmelden.')
  visible=self.visible_rows();count=sum(m['uuid'] in self.checked for _,m in visible);state=Qt.Checked if visible and count==len(visible) else Qt.PartiallyChecked if count else Qt.Unchecked
  self.select_all.blockSignals(True);self.select_all.setCheckState(state);self.select_all.blockSignals(False)
 def rename_selected(self):
  m=self.selected_row()
  if not m:return
  try:r=self.selected_device()
  except Exception as e:self.error(str(e));return
  current=self.row_label(r,m,self.rows.index(m));name,ok=QInputDialog.getText(self,'Mission umbenennen','Neuer Name'+(' in DJI Fly' if r['kind']=='ios' else ' (Etikett in der Bridge)'),QLineEdit.Normal,current)
  name=name.strip() if ok else ''
  if not name or name==current:return
  if len(name)>200:self.error('Bitte einen Namen bis 200 Zeichen eingeben.');return
  if r['kind']!='ios':
   self.registry[r['serial']+':'+m['uuid']]=name;atomic_json(self.root/'names.json',self.registry);self.render_device_list();self.status.setText('Etikett gespeichert. Der Name in DJI Fly auf Android bleibt unverändert.');return
  if QMessageBox.question(self,'In DJI Fly umbenennen',f'„{current}“ wird auf dem iPad in „{name}“ umbenannt.\n\nIst DJI Fly vollständig geschlossen und kein Flug aktiv? Die Datenbank wird vorher gesichert und nach dem Schreiben zurückgelesen.')!=QMessageBox.Yes:return
  dest=self.root/'transfers'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');dest.parent.mkdir(parents=True,exist_ok=True);uid=m['uuid']
  def done(result):
   self.registry[r['serial']+':'+uid]=name;atomic_json(self.root/'names.json',self.registry)
   for row in self.rows:
    if row['uuid']==uid:row['name']=name
   self.render_device_list();self.log_line('Umbenannt und zurückgelesen: '+str(dest));self.status.setText(f'In DJI Fly umbenannt: „{name}“. Beim nächsten Öffnen von DJI Fly prüfen; Cloud-Synchronisation kann folgen.')
  self.task('Datenbank sichern, Namen schreiben und zurücklesen …',lambda:ios.run(ios.rename_mission(r['serial'],uid,name,dest,fly_closed=True)),done)
 def read_device_mission(self,r,m):
  """KMZ und Titelbild einer Mission vom Gerät lesen (nur lesen)."""
  if r['kind']=='ios':return ios.run(ios.read_mission(r['serial'],m['uuid']))
  a=self.adb_for(r);return {'kmz':a.read(m['path']) if m.get('path') else None,'preview':a.read(f'{BASE}/map_preview/{m["uuid"]}/{m["uuid"]}.jpg') if m.get('preview') else None}
 def save_to_archive(self):
  if not self.archive:self.tabs.setCurrentIndex(TAB_ARCHIVE);self.status.setText('Zuerst im Webarchiv anmelden, dann die Auswahl sichern.');return
  try:r=self.selected_device()
  except Exception as e:self.error(str(e));return
  picked=[(i,m) for i,m in enumerate(self.rows) if m['uuid'] in self.checked and m.get('localState')=='local']
  if not picked:return
  folders=[('Ohne Projektordner',None)]+[(f['path']+(' (archiviert)' if f['archived'] else ''),f['id']) for f in self.archive.folders]
  choice,ok=QInputDialog.getItem(self,'Im Webarchiv sichern',f'{len(picked)} Missionen als neue Einträge sichern. Projektordner im Archiv:',[name for name,_ in folders],0,False)
  if not ok:return
  folder=dict(folders)[choice];client=self.archive;labels={m['uuid']:self.row_label(r,m,i) for i,m in picked}
  def work():
   report={'saved':[],'skipped':[],'failed':[]}
   for i,m in picked:
    label=labels[m['uuid']]
    try:
     data=self.read_device_mission(r,m);raw=data.get('kmz')
     if not raw:report['skipped'].append(label+' (keine lokale KMZ)');continue
     inspect_kmz(raw);existing=client.find_by_sha(digest(raw))
     if existing:report['skipped'].append(f'{label} (bereits im Archiv als „{existing["name"]}“)');continue
     client.upload(label,label+'.kmz',raw,folder,data.get('preview'));report['saved'].append(label)
    except Exception as e:report['failed'].append(f'{label}: {e}')
   return report
  def done(report):
   for key,title in [('saved','Gesichert'),('skipped','Übersprungen'),('failed','Fehlgeschlagen')]:
    for line in report[key]:self.log_line(f'{title}: {line}')
   self.checked=set();self.render_device_list();self.archive_rows=client.missions;self.archive_filter();self.archive_previews()
   summary=f'{len(report["saved"])} gesichert, {len(report["skipped"])} übersprungen, {len(report["failed"])} fehlgeschlagen.';self.status.setText('Im Webarchiv gesichert: '+summary)
   QMessageBox.information(self,'Im Webarchiv gesichert',summary+('\n\nÜbersprungen:\n'+'\n'.join(report['skipped']) if report['skipped'] else '')+('\n\nFehlgeschlagen:\n'+'\n'.join(report['failed']) if report['failed'] else '')+'\n\nEinzelheiten im Tab „Protokoll“.')
  self.task(f'{len(picked)} Missionen vom Gerät lesen und im Webarchiv sichern …',work,done)
 def backup(self):
  try:r=self.selected_device();a=self.adb_for(r)
  except Exception as e:self.error(str(e));return
  if QMessageBox.question(self,'Bestand sichern','Ist kein Flug aktiv und DJI Fly vollständig geschlossen?\n\nDie Sicherung liest nur die vorhandenen Missionsdaten. Auf Android wird DJI Fly dabei beendet.')!=QMessageBox.Yes:return
  dest=self.root/'backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');dest.parent.mkdir(parents=True,exist_ok=True)
  self.task('Missionsbestand sichern und zurücklesen …',lambda:ios.run(ios.backup(r['serial'],dest)) if r['kind']=='ios' else a.snapshot(dest),lambda result:self.status.setText(f'{len(result["files"])} Dateien gesichert. Ablage im Tab „Protokoll“ öffnen.'))

 # ---------- Webarchiv ----------
 def archive_login(self):
  url=self.archive_url.text().strip();key=self.archive_key.text();remember=self.archive_remember.isChecked();pref=self.store_preference();self.archive_auto=False
  def connect():
   client=self.client_factory(url);client.login(key);return client,client.library()
  def done(result):
   client,rows=result;self.archive=client;self.settings.setValue('archiveURL',url);self.archive_rows=rows
   if remember:
    try:self.archive_forget.setEnabled(self.credential_store.save(url,key,self.root,preference=pref));self.log_line(f'Zugangsschlüssel gespeichert ({self.archive_store.currentText()}).')
    except Exception as e:self.log_line('Schlüssel konnte nicht gespeichert werden: '+str(e))
   else:self.credential_store.delete(url,self.root,preference=pref);self.archive_key.clear();self.archive_forget.setEnabled(False)
   self.archive_note.setText(f'Angemeldet als {"Eigentümer" if client.role=="owner" else "Freigabe"} · {len(rows)} Missionen in der Bibliothek.');self.status.setText(f'{len(rows)} Missionen aus dem Webarchiv geladen.');self.archive_filter();self.archive_previews();self.update_checked()
  self.task('Am Webarchiv anmelden und Bibliothek laden …',connect,done)
 def store_preference(self):return self.archive_store.currentData() or 'auto'
 def archive_restore_key(self):
  url=self.archive_url.text().strip();key=None
  if url:
   for pref in [self.store_preference()]+[k for k in self.credential_store.available() if k!=self.store_preference()]:
    key=self.credential_store.load(url,self.root,preference=pref)
    if key:index=self.archive_store.findData(pref);self.archive_store.setCurrentIndex(index if index>=0 else 0);break
  if key:self.archive_key.setText(key);self.archive_remember.setChecked(True);self.archive_forget.setEnabled(True);self.archive_auto=True;self.archive_note.setText('Zugangsschlüssel aus dem Schlüsselbund geladen. Die Bibliothek wird beim Öffnen des Tabs geladen.')
 def archive_forget_key(self):
  self.credential_store.delete(self.archive_url.text().strip(),self.root,preference=self.store_preference());self.archive_key.clear();self.archive_remember.setChecked(False);self.archive_forget.setEnabled(False);self.archive_auto=False;self.archive_note.setText('Gespeicherter Schlüssel entfernt. Für diese Sitzung erneut eingeben.');self.log_line('Gespeicherter Zugangsschlüssel entfernt.')
 def archive_import_config(self,path=None):
  if path is None:
   path,_=QFileDialog.getOpenFileName(self,'Bridge-Konfiguration auswählen','','Konfiguration (*.json)')
   if not path:return
  try:
   data=json.loads(Path(path).read_text(encoding='utf-8'))
   if not isinstance(data,dict) or data.get('format')!='dronemissions-bridge-config/1' or not isinstance(data.get('archiveURL'),str):raise BridgeError('Keine Bridge-Konfiguration aus dem Webarchiv.')
   if any(k in data for k in ('password','key','accessKey','token')):raise BridgeError('Die Konfiguration darf keinen Zugangsschlüssel enthalten.')
   from archive import normalize_url;url=normalize_url(data['archiveURL'])
  except BridgeError as e:self.error(str(e));return
  except (OSError,ValueError) as e:self.error('Konfiguration kann nicht gelesen werden: '+str(e));return
  self.archive_url.setText(url);self.settings.setValue('archiveURL',url)
  # A configuration selects an archive, not credentials. Do not retain another
  # archive's client/key; restore only the credential bound to the imported URL.
  self.archive=None;self.archive_rows=[];self.archive_auto=False;self.archive_key.clear();self.archive_remember.setChecked(False);self.archive_forget.setEnabled(False);self.archive_filter();self.archive_restore_key()
  hint=' Gespeicherter Schlüssel geladen. Jetzt anmelden.' if self.archive_key.text() else ' Jetzt mit dem Zugangsschlüssel anmelden; die Konfiguration enthält keinen Schlüssel.'
  self.archive_note.setText(f'Archiv-Adresse aus der Konfiguration übernommen{(" · "+data["authorName"]) if data.get("authorName") else ""}.'+hint);self.status.setText('Konfiguration geladen: '+url);self.archive_key.setFocus();self.log_line('Konfiguration geladen: '+url)
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
   preview_path=self.root/'previews'/(uuid.uuid4().hex+'.jpg');preview=None;target=None
   if self.mode=='replace':
    m=self.selected_row()
    if not m:raise BridgeError('Bitte im Tab „Gerät & Missionen“ den Eintrag wählen, der ersetzt werden soll.')
    if m.get('localState')!='local':raise BridgeError('Nur lokal vorhandene Missionen lassen sich ersetzen. Cloud-Mission zuerst in DJI Fly herunterladen.')
    target=m['uuid'];target_name='Ersetzt: '+self.row_label(r,m,self.rows.index(m))
   else:target_name='Neue Mission auf '+r['name']
  except Exception as e:self.error(str(e));return
  mode=self.mode;preview_mode=self.preview_mode;background=self.background_path;notes=[]
  def prepare_plan():
   nonlocal preview;chosen=background
   if preview_mode=='map':
    try:chosen=map_background(details,self.root/'previews'/(uuid.uuid4().hex+'-luftbild.jpg'),self.root/'tilecache')
    except Exception as e:notes.append('Luftbild nicht verfügbar ('+str(e)+'). 3D-Ansicht verwendet.')
   preview=render_preview(preview_path,name,details,chosen)
   prepared={'device':r,'source':str(source.resolve()),'originalSource':str(self.original_source.resolve()) if self.original_source else None,'sourceSha256':digest(raw),'name':name,'preview':str(preview),'previewSha256':digest(preview.read_bytes()),'previewMode':'3d' if notes else preview_mode,'kmz':details,'mode':'ios-replace' if target else 'ios-new','replace':target}
   if r['kind']=='ios':return prepared
   result=plan(self.adb_for(r),source,name,preview,target);result['device']=r;result['originalSource']=prepared['originalSource'];result['previewMode']=prepared['previewMode'];return result
  def done(p):
   self.transfer=p;pixmap=QPixmap(str(preview))
   for note in notes:self.log_line(note)
   self.image.setPixmap(pixmap.scaled(self.image.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation));self.review_image.setPixmap(pixmap.scaled(self.review_image.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
   self.summary_mode.setText(('ERSETZEN' if mode=='replace' else 'NEU ANLEGEN')+' · '+r['name']);self.summary_name.setText(name);self.summary_points.setText(f'{details["waypoints"]} Wegpunkte · {details["distance"]/1000:.2f} km');self.summary_target.setText(target_name)
   if r['kind']=='ios':text='Neue Mission mit Name und Titelbild. Anschließend in DJI Fly öffnen und bei Bedarf synchronisieren.' if mode=='new' else 'Der Eintrag wird nach Sicherung ersetzt (am iPad noch nicht geprüft). Anschließend in DJI Fly öffnen und Speichern prüfen.'
   else:text='Der gewählte Eintrag wird nach Sicherung ersetzt. Anschließend RC Pro 2 neu starten, Mission öffnen und Speichern prüfen.' if mode=='replace' else 'Experimentell: Neue Kennung wird geprüft übertragen. Anschließend RC Pro 2 neu starten und prüfen, ob DJI Fly die Mission anzeigt.'
   self.review_note.setText(text+((' '+' '.join(notes)) if notes else ''))
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
QCheckBox::indicator:checked{background:#254e3b;border:1px solid #254e3b;image:url("__CHECKMARK__")}
QCheckBox::indicator:indeterminate{background:#254e3b;border:1px solid #254e3b;image:url("__CHECKPARTIAL__")}
QCheckBox::indicator:disabled{border-color:#c7d0c6;background:#e5ebe2}
QProgressBar{background:#e1e9dc;border:none;border-radius:2px}QProgressBar::chunk{background:#7b9f68}
QScrollBar:vertical{background:transparent;width:10px}QScrollBar::handle:vertical{background:#cdd8c9;border-radius:5px;min-height:30px}
'''
STYLE=STYLE.replace('__CHECKMARK__',(Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'assets'/'checkmark.svg').as_posix()).replace('__CHECKPARTIAL__',(Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'assets'/'checkpartial.svg').as_posix())

def main():
 if '--diagnose' in sys.argv:
  target=Path(sys.argv[sys.argv.index('--diagnose')+1]);rows=ios.run(ios.discover());result={'iosDevices':len(rows),'paired':sum(r['state']=='device' for r in rows)}
  if rows and rows[0]['state']=='device':result['readableMissions']=len(ios.run(ios.list_missions(rows[0]['serial'],target.parent/'diagnostic-reads')))
  atomic_json(target,result);return
 app=QApplication(sys.argv);app.setOrganizationName('studiobaff');app.setApplicationName('Drone Missions Bridge');app.setStyle('Fusion');app.setStyleSheet(STYLE);app.setWindowIcon(app_icon());window=Window();window.show();sys.exit(app.exec())
if __name__=='__main__':main()
