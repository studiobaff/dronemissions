"""GPL-3.0-or-later. Desktop mission transfer UI.

Ablauf in vier Schritten: Gerät wählen → Missionen auswählen → Vorschauen prüfen → Übertragen.
Technische Einstellungen liegen in einem eigenen Fenster (⌘,), das Protokoll in einem eigenen Fenster.
Mehrere Missionen werden als Warteschlange seriell auf dasselbe Gerät übertragen.
Die Gerätefunktionen (core.py, ios.py, preview.py, map_preview.py) sind unverändert; diese Datei ist nur Oberfläche.
"""
from __future__ import annotations
import json,os,re,shutil,sys,uuid,shlex
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QThread,Signal,QSettings,QStandardPaths,Qt,QUrl,QTimer,QSize,QRectF
from PySide6.QtGui import QDesktopServices,QPixmap,QPainter,QColor,QFont,QIcon,QAction,QKeySequence,QImage
from PySide6.QtWidgets import (QLayout,QToolBar,QToolButton,QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QDialog,
 QLabel,QPushButton,QComboBox,QLineEdit,QFileDialog,QListWidget,QListWidgetItem,QPlainTextEdit,QTreeWidget,QTreeWidgetItem,
 QMessageBox,QCheckBox,QStackedWidget,QFrame,QProgressBar,QTabWidget,QTabBar,QButtonGroup,QSizePolicy,QScrollArea,QInputDialog,QSplitter)
from PySide6.QtSvg import QSvgRenderer
from core import Adb,devices,plan,apply,atomic_json,BridgeError,inspect_kmz,digest,BASE,prepare_source,bundled_adb
from preview import render_preview
from map_preview import map_background
from archive import ArchiveClient,safe_filename
from mission_list import sort_rows,archive_state,metadata,numeric,folder_tree,in_selected_folder
import credentials
import ios
import theme

VERSION='0.6.1'
APP_NAME='dronemissions-bridge'  # Wortmarke wie die Web-App: drone·missions, dazu -bridge
THUMB=QSize(176,118)
TAB_DEVICE,TAB_ARCHIVE,TAB_TRANSFER,TAB_RUN=0,1,2,3
STEP_TITLES=['Gerät wählen','Missionen auswählen','Vorschauen prüfen','Übertragen']
ARCHIVE_URL='https://service.studiobaff.com/dronemissions/'
STATE_LABELS={'local':'Lokal vorhanden','cloud-or-missing':'Nur Cloud / fehlt lokal','ambiguous':'Mehrere Dateien'}
STATUS_LABELS={'ready':'bereit','prepared':'geprüft','running':'läuft','done':'erfolgreich','failed':'fehlgeschlagen','skipped':'nicht gestartet'}

class Job(QThread):
 result=Signal(object);error=Signal(str);progress=Signal(object)
 def __init__(self,fn,parent=None,with_progress=False):super().__init__(parent);self.fn=fn;self.with_progress=with_progress
 def run(self):
  try:self.result.emit(self.fn(self.progress.emit) if self.with_progress else self.fn())
  except Exception as e:self.error.emit(str(e))

def android_name(description):
 model=re.search(r'\bmodel:(\S+)',description)
 if not model:return 'Android-Gerät'
 value=model.group(1)
 return {'DJI_RC_PRO_2':'DJI RC Pro 2','DJI_RC_PRO':'DJI RC Pro','DJI_RC_2':'DJI RC 2'}.get(value,value.replace('_',' '))

def asset(name):
 base=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
 for candidate in [base/'assets'/name,Path(__file__).resolve().parent/'assets'/name]:
  if candidate.is_file():return candidate
 return None
def app_icon():
 path=asset('icon.png');return QIcon(str(path)) if path else QIcon()

def placeholder(size,text):
 pixmap=QPixmap(size);pixmap.fill(QColor('#1b332b'));painter=QPainter(pixmap);painter.setPen(QColor('#a7c577'))
 painter.setFont(QFont(theme.system_font(),11));painter.drawText(pixmap.rect(),Qt.AlignCenter|Qt.TextWordWrap,text);painter.end();return pixmap

def picture_from(data,content_type='',size=THUMB):
 pixmap=QPixmap()
 if data and 'svg' in (content_type or ''):
  renderer=QSvgRenderer(data)
  if renderer.isValid():
   pixmap=QPixmap(size);pixmap.fill(QColor('#152e2b'));painter=QPainter(pixmap);renderer.render(painter);painter.end();return pixmap
 if data and pixmap.loadFromData(data):return pixmap.scaled(size,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation)
 return None

def archive_preview_file(raw,content_type,destination):
 """Vorschau aus dem Webarchiv als JPEG ablegen; SVG-Routenzeichnungen werden auf 900×600 gerastert. Liefert None bei leeren Daten."""
 if not raw:return None
 destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
 if 'svg' in (content_type or '') or raw.lstrip().startswith(b'<'):
  renderer=QSvgRenderer(raw)
  if not renderer.isValid():return None
  image=QImage(900,600,QImage.Format_RGB32);image.fill(QColor('#152e2b'));painter=QPainter(image);painter.setRenderHint(QPainter.Antialiasing)
  box=renderer.viewBoxF();ratio=min(900/max(box.width(),1),600/max(box.height(),1)) if box.width() and box.height() else 1;w,h=(box.width()*ratio,box.height()*ratio) if box.width() and box.height() else (900,600)
  renderer.render(painter,QRectF((900-w)/2,(600-h)/2,w,h));painter.end();path=destination.with_suffix('.jpg')
  return path if image.save(str(path),'JPEG',90) else None
 image=QImage.fromData(raw)
 if image.isNull():return None
 path=destination.with_suffix('.jpg');return path if image.convertToFormat(QImage.Format_RGB32).save(str(path),'JPEG',90) else None

def badge(text,kind):
 label=QLabel(text);label.setObjectName('missionBadge');label.setProperty('badge',kind);return label

class PreviewLabel(QLabel):
 """Großes Vorschaubild, das sich in den verfügbaren Platz einpasst statt den Platz zu bestimmen.

 Das Quellbild wird gemerkt und bei jeder Größenänderung neu skaliert; die Mindestgröße bleibt klein, damit der
 Infoblock und die Knöpfe darunter nie überdeckt werden. Ohne Bild erscheint ein beschrifteter Platzhalter.
 """
 def __init__(self,empty_text,minimum=QSize(320,200)):
  super().__init__();self.setObjectName('preview');self.setMinimumSize(minimum);self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding);self.setAlignment(Qt.AlignCenter);self.empty_text=empty_text;self.source=None;self.set_source(None)
 def set_source(self,pixmap):
  self.source=pixmap if pixmap is not None and not pixmap.isNull() else None;self.refresh()
 def refresh(self):
  size=self.size() if self.width()>1 and self.height()>1 else self.minimumSize()
  if self.source is None:QLabel.setPixmap(self,placeholder(QSize(min(size.width(),480),min(size.height(),320)),self.empty_text));return
  QLabel.setPixmap(self,self.source.scaled(size,Qt.KeepAspectRatio,Qt.SmoothTransformation))
 def resizeEvent(self,event):super().resizeEvent(event);self.refresh()
 def sizeHint(self):return self.minimumSize()

class ArchiveRow(QWidget):
 """Eine Zeile der Webarchiv-Liste: Hakerl, Vorschaubild, Name, Projektpfad, Format, Wegpunkte, Strecke."""
 def __init__(self,m,checked=False,on_toggle=None):
  super().__init__();layout=QHBoxLayout(self);layout.setContentsMargins(10,8,10,8);layout.setSpacing(16)
  self.check=QCheckBox();self.check.setChecked(checked);self.check.setEnabled(bool(m['transferable']));self.check.setToolTip('Zur Übertragung auswählen' if m['transferable'] else 'Projektdatei, kein DJI-KMZ: nicht übertragbar')
  if on_toggle:self.check.toggled.connect(lambda state:on_toggle(m['id'],state))
  layout.addWidget(self.check,alignment=Qt.AlignVCenter)
  self.picture=QLabel();self.picture.setFixedSize(THUMB);self.picture.setObjectName('thumb');self.picture.setAlignment(Qt.AlignCenter);self.picture.setPixmap(placeholder(THUMB,'Vorschau wird geladen …' if m['transferable'] else m['format']));layout.addWidget(self.picture)
  text=QVBoxLayout();text.setSpacing(4);title=QLabel(m['name']);title.setObjectName('rowTitle');title.setWordWrap(True);text.addWidget(title)
  folder=QLabel(m['folder']+(' · Archiv' if m['archived'] else ''));folder.setObjectName('muted');text.addWidget(folder)
  meta=f"{m['format']} · V{m.get('version') or '?'}"+(f" · {m['waypoints']} Wegpunkte · {m['distance']/1000:.2f} km" if m['waypoints'] is not None else ' · Planungsdatei, kein Flugexport')
  label=QLabel(meta);label.setObjectName('ident');text.addWidget(label);text.addStretch();layout.addLayout(text,1)
 def set_picture(self,pixmap):
  if pixmap:self.picture.setPixmap(pixmap)
  else:self.picture.setPixmap(placeholder(THUMB,'Kein Vorschaubild'))

class MissionRow(QWidget):
 """Eine Zeile der Geräteliste: Hakerl, Vorschaubild, Name, Wegpunkte, Bestand, Archivstatus."""
 def __init__(self,label,mission,image=None,checked=False,on_toggle=None,fallback=None):
  """image: JPEG vom Gerät; fallback: fertiges Pixmap (Archivbild der identischen Archivmission), wenn das Gerät kein Bild hat."""
  super().__init__();layout=QHBoxLayout(self);layout.setContentsMargins(10,8,10,8);layout.setSpacing(16)
  self.check=QCheckBox();self.check.setChecked(checked);self.check.setToolTip('Für „Im Webarchiv sichern“ auswählen')
  if on_toggle:self.check.toggled.connect(lambda state:on_toggle(mission['uuid'],state))
  layout.addWidget(self.check,alignment=Qt.AlignVCenter)
  picture=QLabel();picture.setFixedSize(THUMB);picture.setObjectName('thumb');picture.setAlignment(Qt.AlignCenter)
  pixmap=QPixmap()
  if image and pixmap.loadFromData(image):picture.setPixmap(pixmap.scaled(THUMB,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation))
  elif fallback is not None and not fallback.isNull():picture.setPixmap(fallback.scaled(THUMB,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation));picture.setToolTip('Vorschaubild aus dem Webarchiv (identische KMZ); auf dem Gerät fehlt das Bild.')
  else:picture.setPixmap(placeholder(THUMB,'Kein Vorschaubild'))
  layout.addWidget(picture)
  text=QVBoxLayout();text.setSpacing(4);title=QLabel(label);title.setObjectName('rowTitle');title.setWordWrap(True);text.addWidget(title)
  waypoints=mission.get('waypoints','—');meta=QLabel(f'{waypoints} Wegpunkte'+((' · '+metadata(mission)) if metadata(mission) else ''));meta.setObjectName('muted');text.addWidget(meta)
  badges=QHBoxLayout();badges.setSpacing(6)
  state=mission.get('localState');badges.addWidget(badge({'local':'Lokal','cloud-or-missing':'Nur Cloud','ambiguous':'Mehrere Dateien'}.get(state,'Unbekannt'),state or 'unknown'))
  saved=badge({'saved':'Im Webarchiv','missing':'Nicht im Webarchiv','unknown':'Archiv: nicht geprüft'}.get(mission.get('archiveState'),'Archiv: nicht geprüft'),mission.get('archiveState','unknown'));saved.setToolTip(mission.get('archiveStatus','Für den Vergleich im Webarchiv anmelden und lokale Missionen lesen.'));badges.addWidget(saved);badges.addStretch();text.addLayout(badges)
  ident=QLabel('Kennung '+mission['uuid']);ident.setObjectName('ident');text.addWidget(ident);text.addStretch();layout.addLayout(text,1)

class QueueRow(QWidget):
 """Eine Zeile der Warteschlange: Vorschau, Name, Herkunft, Modus/Ziel, Status."""
 def __init__(self,entry,index,current=False,checked=None,on_toggle=None):
  """checked/on_toggle: optionale Checkbox zum Markieren für „Markierte entfernen“ (None = keine Checkbox)."""
  super().__init__();layout=QHBoxLayout(self);layout.setContentsMargins(10,8,10,8);layout.setSpacing(14);self.check=None
  if on_toggle is not None:
   self.check=QCheckBox();self.check.setChecked(bool(checked));self.check.setToolTip('Zum Entfernen aus der Warteschlange markieren');self.check.setEnabled(entry['status']!='running');self.check.toggled.connect(lambda state:on_toggle(entry['id'],state));layout.addWidget(self.check,alignment=Qt.AlignVCenter)
  number=QLabel(str(index+1));number.setObjectName('queueNumber');number.setFixedWidth(26);number.setAlignment(Qt.AlignCenter);layout.addWidget(number)
  picture=QLabel();picture.setFixedSize(QSize(132,88));picture.setObjectName('thumb');picture.setAlignment(Qt.AlignCenter)
  pixmap=QPixmap(str(entry['preview'])) if entry.get('preview') and Path(entry['preview']).is_file() else QPixmap()
  picture.setPixmap(pixmap.scaled(132,88,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation) if not pixmap.isNull() else placeholder(QSize(132,88),'Vorschau folgt'));layout.addWidget(picture)
  text=QVBoxLayout();text.setSpacing(3);title=QLabel(entry['name'] or Path(entry['original']).stem);title.setObjectName('rowTitle');title.setWordWrap(False);title.setToolTip(entry['name']);text.addWidget(title)
  origin='Webarchiv: '+entry['archiveMission']['folder'] if entry.get('archiveMission') else 'Lokale Datei: '+Path(entry['original']).name
  meta=QLabel(origin+(f" · {entry['details']['waypoints']} Wegpunkte · {entry['details']['distance']/1000:.2f} km" if entry.get('details') else ''));meta.setObjectName('muted');meta.setWordWrap(True);text.addWidget(meta)
  badges=QHBoxLayout();badges.setSpacing(6);badges.addWidget(badge('Ersetzen: '+(entry.get('targetLabel') or 'Ziel fehlt') if entry['mode']=='replace' else 'Neu anlegen','replace' if entry['mode']=='replace' else 'new'))
  badges.addWidget(badge(STATUS_LABELS.get(entry['status'],entry['status']),'status-'+entry['status']))
  if entry.get('error'):err=QLabel(entry['error']);err.setObjectName('errorText');err.setWordWrap(True);badges.addWidget(err,1)
  badges.addStretch();text.addLayout(badges);text.addStretch();layout.addLayout(text,1)

class Window(QMainWindow):
 def __init__(self,autosearch=True,credential_store=None,client_factory=None,root=None):
  super().__init__();self.setWindowTitle(f'{APP_NAME} · {VERSION}');self.setWindowIcon(app_icon());self.resize(1240,860);self.setMinimumSize(1020,720)
  # root: Anwendungsdatenordner; Tests übergeben einen temporären Ordner, damit weder names.json noch Sicherungen des Nutzers berührt werden.
  self.settings=QSettings('studiobaff','DroneMissionsBridge');self.root=Path(root) if root else Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation));self.root.mkdir(parents=True,exist_ok=True)
  self.rows=[];self.registry={};self.job=None;self.prepared=None;self.stop_requested=False
  self.queue=[];self.current=-1;self.pending_target=None;self.mode='new';self.loose_transfer=None;self.queue_checked=set();self.quick_timer=QTimer(self);self.quick_timer.setSingleShot(True);self.quick_timer.setInterval(350);self.quick_timer.timeout.connect(self.quick_preview)
  self.archive=None;self.archive_rows=[];self.archive_widgets=[];self.archive_checked=set();self.archive_selection='all';self.client_factory=client_factory or ArchiveClient;self.credential_store=credential_store or credentials;self.archive_auto=False;self.checked=set();self.device_rows_widgets=[];self.preview_mode=self.settings.value('previewMode','3d') or '3d';self.background_path=None
  try:self.registry=json.loads((self.root/'names.json').read_text())
  except (OSError,ValueError):pass
  self.body=QWidget();outer=QVBoxLayout(self.body);outer.setContentsMargins(24,16,24,16);outer.setSpacing(12);self.setCentralWidget(self.body)
  self.build_settings_dialog();self.build_log_dialog();self.build_header(outer)
  self.tabs=QTabWidget();self.tabs.setObjectName('steps');self.tabs.tabBar().setExpanding(True);self.tabs.tabBar().setDrawBase(False);outer.addWidget(self.tabs,1)
  self.build_device_tab();self.build_archive_tab();self.build_transfer_tab();self.build_run_tab()
  self.progress=QProgressBar();self.progress.setRange(0,0);self.progress.setFixedHeight(4);self.progress.setTextVisible(False);self.progress.hide();outer.addWidget(self.progress)
  self.status=QLabel('iPad oder Fernsteuerung per USB verbinden.');self.status.setObjectName('status');self.status.setWordWrap(True);outer.addWidget(self.status)
  self.set_mode('new');self.changed_device();self.build_menu();self.update_steps()
  self.tabs.currentChanged.connect(self.tab_changed)
  if autosearch:QTimer.singleShot(0,self.refresh_devices)

 # ---------- Aufbau ----------
 def build_header(self,outer):
  """Symbolleiste wie in macOS-Programmen: Gerät links, Aktionen mit Icon und Beschriftung rechts."""
  bar=QToolBar('Hauptfunktionen');bar.setMovable(False);bar.setFloatable(False);bar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon);bar.setIconSize(QSize(22,22));bar.setContextMenuPolicy(Qt.PreventContextMenu);self.toolbar=bar;self.addToolBar(Qt.TopToolBarArea,bar)
  holder=QWidget();row=QHBoxLayout(holder);row.setContentsMargins(4,0,12,0);row.setSpacing(8)
  # Wortmarke wie in der Web-App: Zeichen auf dunklem Grund, „drone“ fett, „missions“ normal, dazu „-bridge“.
  mark=QLabel();mark.setObjectName('brandMark');mark.setFixedSize(30,30);mark.setPixmap(app_icon().pixmap(30,30));row.addWidget(mark)
  self.brand=QLabel(f'<span style="font-weight:700">drone</span><span style="font-weight:400">missions</span><span style="font-weight:400">-bridge</span>');self.brand.setObjectName('brandName');self.brand.setTextFormat(Qt.RichText);row.addWidget(self.brand);row.addSpacing(14);row.addWidget(QLabel('Gerät'))
  self.device=QComboBox();self.device.setMinimumHeight(40);self.device.setMinimumWidth(300);self.device.currentIndexChanged.connect(self.changed_device);row.addWidget(self.device,1);bar.addWidget(holder)
  self.tool_actions={};self.tool_buttons={}
  def add(name,text,slot,icon_name):
   # Wie in macOS 26: Icon im Kreis, Beschriftung darunter. Die QAction hält Icon und Zustand, der Kreis-Knopf löst sie aus.
   action=QAction(text,self);action.triggered.connect(lambda *_:slot());action.setProperty('iconName',icon_name);self.tool_actions[name]=action
   box=QWidget();box.setObjectName('toolAction');column=QVBoxLayout(box);column.setContentsMargins(6,2,6,2);column.setSpacing(3)
   button=QToolButton();button.setObjectName('circleButton');button.setDefaultAction(action);button.setToolButtonStyle(Qt.ToolButtonIconOnly);button.setIconSize(QSize(20,20));button.setAutoRaise(False);button.setToolTip(text);button.setText(text);button.setCursor(Qt.PointingHandCursor);column.addWidget(button,0,Qt.AlignHCenter)
   label=QLabel(text);label.setObjectName('toolLabel');label.setAlignment(Qt.AlignHCenter);column.addWidget(label);bar.addWidget(box);self.tool_buttons[name]=button;return button
  self.refresh_button=add('refresh','Neu suchen',self.refresh_devices,'refresh');add('list','Missionen lesen',self.list_missions,'list');add('backup','Gerät sichern',self.backup,'backup');bar.addSeparator()
  add('log','Protokoll',self.show_log,'log');add('settings','Einstellungen',self.show_settings,'settings')
  self.theme_changed(theme.scheme_for(QApplication.instance()))
  self.device_note=QLabel('Gerät auswählen, um fortzufahren.');self.device_note.setObjectName('muted');self.device_note.setWordWrap(True);outer.addWidget(self.device_note)
 def theme_changed(self,scheme):
  """Icons in der Textfarbe des aktuellen Schemas neu rendern."""
  colour=theme.tokens(scheme)['text']
  for action in getattr(self,'tool_actions',{}).values():action.setIcon(theme.icon(action.property('iconName'),colour))
  self.setProperty('dmScheme',scheme)
 def key_values(self,rows):
  """Infoblock wie im Festplattendienstprogramm: Schlüssel links in Grau, Wert rechts, Zeilen durch feine Linien getrennt."""
  box=QFrame();box.setObjectName('kvBox');layout=QVBoxLayout(box);layout.setContentsMargins(12,2,12,2);layout.setSpacing(0)
  for n,(key,value) in enumerate(rows):
   frame=QFrame();frame.setObjectName('kvRow');frame.setProperty('last','true' if n==len(rows)-1 else 'false');row=QHBoxLayout(frame);row.setContentsMargins(0,8,0,8);row.setSpacing(12)
   label=QLabel(key);label.setObjectName('kvKey');label.setMinimumWidth(96);row.addWidget(label);value.setObjectName('kvValue');value.setAlignment(Qt.AlignRight|Qt.AlignTop);row.addWidget(value,1);layout.addWidget(frame)
  return box
 def card(self,parent_layout,stretch=0):
  frame=QFrame();frame.setObjectName('card');layout=QVBoxLayout(frame);layout.setContentsMargins(22,20,22,20);layout.setSpacing(12);parent_layout.addWidget(frame,stretch);return layout
 def heading(self,layout,title,description=None):
  label=QLabel(title);label.setObjectName('pageTitle');layout.addWidget(label)
  if description:label=QLabel(description);label.setObjectName('muted');label.setWordWrap(True);layout.addWidget(label)
 def tab(self,title):
  widget=QWidget();layout=QVBoxLayout(widget);layout.setContentsMargins(0,14,0,0);layout.setSpacing(12);self.tabs.addTab(widget,title);return layout
 def update_steps(self):
  for i,title in enumerate(STEP_TITLES):self.tabs.setTabText(i,f'{i+1}  {title}'+('   ▸' if i<len(STEP_TITLES)-1 else ''))

 def build_device_tab(self):
  layout=self.tab('');card=self.card(layout,1)
  row=QHBoxLayout();text=QVBoxLayout();text.setSpacing(2);title=QLabel('Missionen auf dem Gerät');title.setObjectName('pageTitle');text.addWidget(title)
  self.list_note=QLabel('Gerät oben wählen und die Liste lesen: Bild, Wegpunkte und Bestand jeder Mission.');self.list_note.setObjectName('muted');self.list_note.setWordWrap(True);text.addWidget(self.list_note);row.addLayout(text,1)
  self.list_button=QPushButton('Missionen lesen');self.list_button.clicked.connect(self.list_missions);row.addWidget(self.list_button)
  self.backup_button=QPushButton('Gerät sichern');self.backup_button.setObjectName('quiet');self.backup_button.clicked.connect(self.backup);row.addWidget(self.backup_button);card.addLayout(row)
  tools=QHBoxLayout();self.device_search=QLineEdit();self.device_search.setMinimumWidth(220);self.device_search.setPlaceholderText('Name oder Kennung suchen …');self.device_search.textChanged.connect(self.render_device_list);tools.addWidget(self.device_search,1)
  self.device_local_only=QCheckBox('Nur lokal vorhanden');self.device_local_only.setToolTip('Nur Missionen mit heruntergeladener KMZ anzeigen; reine Cloud-Einträge ausblenden.');self.device_local_only.setChecked(self.settings.value('deviceLocalOnly',False,type=bool));self.device_local_only.toggled.connect(self.local_filter_changed)
  self.device_cloud_only=QCheckBox('Nur Cloud');self.device_cloud_only.setToolTip('Einträge ohne lokale KMZ; zum Herunterladen in DJI Fly öffnen.');self.device_cloud_only.toggled.connect(self.cloud_filter_changed)
  self.device_unsaved_only=QCheckBox('Nicht im Webarchiv');self.device_unsaved_only.setEnabled(False);self.device_unsaved_only.setToolTip('Nach Anmeldung: lokale Dateien ohne identische Prüfsumme im geladenen Archivbestand.');self.device_unsaved_only.toggled.connect(self.unsaved_filter_changed)
  self.select_all=QCheckBox('Alle sichtbaren');self.select_all.setTristate(True);self.select_all.toggled.connect(self.toggle_all_visible);tools.addWidget(self.select_all)
  self.checked_label=QLabel('0 ausgewählt');self.checked_label.setObjectName('muted');tools.addWidget(self.checked_label)
  self.save_web_button=QPushButton('Im Webarchiv sichern …');self.save_web_button.setEnabled(False);self.save_web_button.clicked.connect(self.save_to_archive);tools.addWidget(self.save_web_button)
  self.sync_preview_button=QPushButton('Vorschauen ins Webarchiv');self.sync_preview_button.setObjectName('quiet');self.sync_preview_button.setEnabled(False);self.sync_preview_button.setToolTip('DJI-Fly-Titelbilder der angehakten (sonst aller sichtbaren) Missionen, die identisch im Webarchiv liegen, dort als Vorschau speichern.');self.sync_preview_button.clicked.connect(self.sync_previews_to_archive);tools.addWidget(self.sync_preview_button);card.addLayout(tools)
  self.remove_device_button=QPushButton('Vom iPad entfernen …');self.remove_device_button.setObjectName('quiet');self.remove_device_button.setToolTip('Nur angehakte Missionen lokal entfernen. Vorher vollständige Sicherung; Webarchiv und Cloud-Kopien bleiben bestehen.');self.remove_device_button.setEnabled(False);self.remove_device_button.clicked.connect(self.remove_device_missions);
  sorting=QHBoxLayout();sorting.addWidget(QLabel('Sortieren nach'));self.device_sort=QComboBox()
  for text,key in [('Gerätereihenfolge','device'),('Name A–Z','name-asc'),('Name Z–A','name-desc'),('Datum: neueste zuerst','date-desc'),('Datum: älteste zuerst','date-asc'),('Strecke: kürzeste zuerst','distance-asc'),('Strecke: längste zuerst','distance-desc'),('Wegpunkte: wenige zuerst','points-asc'),('Wegpunkte: viele zuerst','points-desc')]:self.device_sort.addItem(text,key)
  saved=self.device_sort.findData(self.settings.value('deviceSort','device'));self.device_sort.setCurrentIndex(max(0,saved));self.device_sort.currentIndexChanged.connect(lambda _:(self.settings.setValue('deviceSort',self.device_sort.currentData()),self.render_device_list()));sorting.addWidget(self.device_sort);sorting.addSpacing(10);sorting.addWidget(self.device_local_only);sorting.addWidget(self.device_cloud_only);sorting.addWidget(self.device_unsaved_only);sorting.addStretch();self.device_count=QLabel('');self.device_count.setObjectName('muted');sorting.addWidget(self.device_count);sorting.addWidget(self.remove_device_button);card.addLayout(sorting)
  self.list=QListWidget();self.list.setObjectName('missions');self.list.setSelectionMode(QListWidget.SingleSelection);self.list.setSpacing(4);self.list.setUniformItemSizes(False);self.list.itemSelectionChanged.connect(self.changed_target);self.list.itemDoubleClicked.connect(lambda _:self.start_replace());card.addWidget(self.list,1)
  self.list_empty=QLabel('Noch keine Missionen gelesen.');self.list_empty.setObjectName('emptyList');self.list_empty.setAlignment(Qt.AlignCenter);card.addWidget(self.list_empty,1)
  actions=QHBoxLayout();self.selected_label=QLabel('Kein Eintrag ausgewählt.');self.selected_label.setObjectName('muted');self.selected_label.setWordWrap(True);actions.addWidget(self.selected_label,1)
  self.cloud_download_button=QPushButton('So lädst du Cloud-Missionen herunter …');self.cloud_download_button.setObjectName('quiet');self.cloud_download_button.setEnabled(False);self.cloud_download_button.clicked.connect(self.cloud_download_help);actions.addWidget(self.cloud_download_button)
  self.rename_button=QPushButton('Umbenennen …');self.rename_button.setObjectName('quiet');self.rename_button.setEnabled(False);self.rename_button.clicked.connect(self.rename_selected);actions.addWidget(self.rename_button)
  self.new_button=QPushButton('Neu anlegen  ▸');self.new_button.setObjectName('primary');self.new_button.clicked.connect(self.start_new);actions.addWidget(self.new_button)
  self.replace_button=QPushButton('Ausgewählte ersetzen  ▸');self.replace_button.setToolTip('Die markierte, lokal vorhandene Mission als Ziel eines Ersetzen-Auftrags vormerken.');self.replace_button.setEnabled(False);self.replace_button.clicked.connect(self.start_replace);actions.addWidget(self.replace_button);card.addLayout(actions)

 def build_archive_tab(self):
  layout=self.tab('')
  status=QHBoxLayout();self.archive_status=QLabel('Webarchiv: nicht verbunden.');self.archive_status.setObjectName('sectionTitle');self.archive_status.setWordWrap(True);status.addWidget(self.archive_status,1)
  self.archive_connect_button=QPushButton('Verbinden');self.archive_connect_button.clicked.connect(self.archive_login);status.addWidget(self.archive_connect_button)
  link=QPushButton('Einstellungen …');link.setObjectName('quiet');link.clicked.connect(self.show_settings);status.addWidget(link);layout.addLayout(status)
  split=QSplitter(Qt.Horizontal);split.setChildrenCollapsible(False);layout.addWidget(split,1)
  left=QFrame();left.setObjectName('card');lv=QVBoxLayout(left);lv.setContentsMargins(16,16,16,16);lv.setSpacing(8)
  title=QLabel('Projekte');title.setObjectName('sectionTitle');lv.addWidget(title)
  self.folder_tree=QTreeWidget();self.folder_tree.setObjectName('folders');self.folder_tree.setHeaderHidden(True);self.folder_tree.setIndentation(16);self.folder_tree.currentItemChanged.connect(lambda *_:self.folder_selected());lv.addWidget(self.folder_tree,1)
  self.include_subfolders=QCheckBox('Unterordner einbeziehen');self.include_subfolders.setChecked(True);self.include_subfolders.toggled.connect(self.archive_filter);lv.addWidget(self.include_subfolders)
  split.addWidget(left)
  right=QFrame();right.setObjectName('card');rv=QVBoxLayout(right);rv.setContentsMargins(16,16,16,16);rv.setSpacing(10)
  head=QHBoxLayout();self.archive_title=QLabel('Alle Missionen');self.archive_title.setObjectName('pageTitle');head.addWidget(self.archive_title,1)
  local=QPushButton('KMZ-Dateien vom Mac …');local.setObjectName('quiet');local.setToolTip('Lokale DJI-KMZ-Dateien ohne Webarchiv in die Warteschlange aufnehmen.');local.clicked.connect(self.choose_kmz);head.addWidget(local);rv.addLayout(head)
  tools=QHBoxLayout();self.archive_search=QLineEdit();self.archive_search.setPlaceholderText('Name, Projekt oder Dateiname suchen …');self.archive_search.textChanged.connect(self.archive_filter);tools.addWidget(self.archive_search,1)
  self.archive_sort=QComboBox()
  for text,key in [('Zuletzt geändert','updated-desc'),('Name A–Z','name-asc'),('Name Z–A','name-desc'),('Strecke: längste zuerst','distance-desc'),('Wegpunkte: viele zuerst','points-desc')]:self.archive_sort.addItem(text,key)
  self.archive_sort.currentIndexChanged.connect(self.archive_filter);tools.addWidget(self.archive_sort)
  self.archive_kmz_only=QCheckBox('Nur DJI-KMZ');self.archive_kmz_only.setChecked(True);self.archive_kmz_only.setToolTip('Nur übertragbare Flugexporte; Planungsdateien (MPROJ, LCHM, LCHZ) ausblenden.');self.archive_kmz_only.toggled.connect(self.archive_filter);tools.addWidget(self.archive_kmz_only)
  self.archive_archived=QCheckBox('Archivierte zeigen');self.archive_archived.toggled.connect(self.archive_filter);tools.addWidget(self.archive_archived);rv.addLayout(tools)
  self.archive_list=QListWidget();self.archive_list.setObjectName('missions');self.archive_list.setSelectionMode(QListWidget.SingleSelection);self.archive_list.setSpacing(4);self.archive_list.itemSelectionChanged.connect(self.archive_changed);self.archive_list.itemDoubleClicked.connect(lambda _:self.archive_use());rv.addWidget(self.archive_list,1)
  self.archive_empty=QLabel('Noch nicht verbunden. Oben „Verbinden“ oder eine KMZ-Datei vom Mac wählen.');self.archive_empty.setObjectName('emptyList');self.archive_empty.setAlignment(Qt.AlignCenter);self.archive_empty.setWordWrap(True);rv.addWidget(self.archive_empty,1);self.archive_list.hide()
  actions=QHBoxLayout();self.archive_select_all=QCheckBox('Alle sichtbaren');self.archive_select_all.setTristate(True);self.archive_select_all.clicked.connect(self.archive_toggle_all)  # clicked statt toggled: aus dem Teilzustand heraus ändert sich isChecked() nicht;actions.addWidget(self.archive_select_all)
  self.archive_selected=QLabel('Kein Eintrag ausgewählt.');self.archive_selected.setObjectName('muted');self.archive_selected.setWordWrap(True);actions.addWidget(self.archive_selected,1)
  self.archive_use_button=QPushButton('Zur Übertragung übernehmen  ▸');self.archive_use_button.setObjectName('primary');self.archive_use_button.setEnabled(False);self.archive_use_button.clicked.connect(self.archive_use);actions.addWidget(self.archive_use_button);rv.addLayout(actions)
  split.addWidget(right);split.setStretchFactor(0,1);split.setStretchFactor(1,3);split.setSizes([280,900])
  self.render_folder_tree()

 def build_transfer_tab(self):
  layout=self.tab('');self.stack=QStackedWidget();layout.addWidget(self.stack,1)
  # Seite 0: Warteschlange bearbeiten
  page=QWidget();columns=QHBoxLayout(page);columns.setContentsMargins(0,0,0,0);columns.setSpacing(14);self.stack.addWidget(page)
  left=self.card(columns,2);left.parentWidget().setMinimumWidth(440);head=QHBoxLayout();title=QLabel('Warteschlange');title.setObjectName('pageTitle');head.addWidget(title,1)
  self.queue_count=QLabel('');self.queue_count.setObjectName('muted');head.addWidget(self.queue_count);left.addLayout(head)
  self.queue_list=QListWidget();self.queue_list.setObjectName('missions');self.queue_list.setSelectionMode(QListWidget.SingleSelection);self.queue_list.setSpacing(4);self.queue_list.currentRowChanged.connect(self.queue_selected);left.addWidget(self.queue_list,1)
  self.queue_empty=QLabel('Noch keine Mission in der Warteschlange.\nIn Schritt 2 Missionen aus dem Webarchiv übernehmen oder KMZ-Dateien vom Mac wählen.');self.queue_empty.setObjectName('emptyList');self.queue_empty.setAlignment(Qt.AlignCenter);self.queue_empty.setWordWrap(True);left.addWidget(self.queue_empty,1)
  qa=QHBoxLayout();add=QPushButton('KMZ-Dateien hinzufügen …');add.setObjectName('quiet');add.clicked.connect(self.choose_kmz);qa.addWidget(add)
  self.queue_remove=QPushButton('Entfernen');self.queue_remove.setToolTip('Markierte Aufträge entfernen, sonst den aktuellen.');self.queue_remove.setObjectName('quiet');self.queue_remove.setEnabled(False);self.queue_remove.clicked.connect(self.remove_current);qa.addWidget(self.queue_remove)
  self.queue_clear=QPushButton('Leeren');self.queue_clear.setObjectName('quiet');self.queue_clear.setEnabled(False);self.queue_clear.clicked.connect(self.clear_queue);qa.addWidget(self.queue_clear);qa.addStretch();left.addLayout(qa)
  right=self.card(columns,3);self.editor=QWidget();self.editor.setMinimumWidth(520);ev=QVBoxLayout(self.editor);ev.setContentsMargins(0,0,0,0);ev.setSpacing(12);right.addWidget(self.editor,1)
  mode=QHBoxLayout();mode.setSpacing(6);self.mode_group=QButtonGroup(self);self.mode_group.setExclusive(True)
  self.mode_new=QPushButton('Neu anlegen');self.mode_new.setToolTip('Neue Mission mit eigener Kennung anlegen; bestehende bleiben unverändert.');self.mode_replace=QPushButton('Ersetzen');self.mode_replace.setToolTip('Einen bestehenden Eintrag nach Sicherung ersetzen; braucht ein Ziel aus Schritt 1.')
  for i,button in enumerate([self.mode_new,self.mode_replace]):button.setCheckable(True);button.setObjectName('segment');self.mode_group.addButton(button,i);mode.addWidget(button)
  mode.addStretch();ev.addLayout(mode);self.mode_group.idClicked.connect(lambda i:self.set_mode('replace' if i else 'new'))
  self.mode_note=QLabel();self.mode_note.setObjectName('hintBox');self.mode_note.setWordWrap(True);ev.addWidget(self.mode_note)
  self.target_panel=QFrame();self.target_panel.setObjectName('target');target=QHBoxLayout(self.target_panel);target.setContentsMargins(12,10,12,10);target.setSpacing(14)
  self.target_image=QLabel();self.target_image.setFixedSize(THUMB);self.target_image.setObjectName('thumb');target.addWidget(self.target_image)
  text=QVBoxLayout();text.setSpacing(3);label=QLabel('Zu ersetzender Eintrag auf dem Gerät');label.setObjectName('sectionTitle');text.addWidget(label)
  self.target_name=QLabel('Noch kein Eintrag gewählt.');self.target_name.setObjectName('rowTitle');self.target_name.setWordWrap(True);text.addWidget(self.target_name)
  self.target_meta=QLabel('');self.target_meta.setObjectName('muted');self.target_meta.setWordWrap(True);text.addWidget(self.target_meta);text.addStretch();target.addLayout(text,1)
  button=QPushButton('Eintrag wählen …');button.setObjectName('quiet');button.setToolTip('In Schritt 1 die zu ersetzende Mission markieren und „Ausgewählte ersetzen“ wählen.');button.clicked.connect(lambda:self.tabs.setCurrentIndex(TAB_DEVICE));target.addWidget(button,alignment=Qt.AlignTop);ev.addWidget(self.target_panel)
  self.new_note=QLabel();self.new_note.setObjectName('muted');self.new_note.setWordWrap(True);ev.addWidget(self.new_note)
  grid=QGridLayout();grid.setHorizontalSpacing(14);grid.setVerticalSpacing(4)
  label=QLabel('Quelle');label.setObjectName('sectionTitle');grid.addWidget(label,0,0);self.source_label=QLabel('Noch keine KMZ ausgewählt');self.source_label.setObjectName('fileName');self.source_label.setWordWrap(True);grid.addWidget(self.source_label,1,0)
  self.source_meta=QLabel('Export aus Litchi, Map Creator oder dem Webarchiv.');self.source_meta.setObjectName('muted');self.source_meta.setWordWrap(True);grid.addWidget(self.source_meta,2,0)
  label=QLabel('Missionsname');label.setObjectName('sectionTitle');grid.addWidget(label,0,1);self.name=QLineEdit();self.name.setPlaceholderText('Zum Beispiel: Baustelle Nord · Panorama');self.name.setMaxLength(200);self.name.textChanged.connect(self.name_edited);grid.addWidget(self.name,1,1)
  self.name_note=QLabel('Titel im Vorschaubild; auf dem iPad auch Listenname in DJI Fly. Auf Android ist der Listenname nicht setzbar.');self.name_note.setObjectName('muted');self.name_note.setWordWrap(True);grid.addWidget(self.name_note,2,1);grid.setColumnStretch(0,1);grid.setColumnStretch(1,1);ev.addLayout(grid)
  pv=QHBoxLayout();label=QLabel('Titelbild');label.setObjectName('sectionTitle');pv.addWidget(label);self.preview_group=QButtonGroup(self);self.preview_group.setExclusive(True)
  self.preview_3d=QPushButton('3D-Ansicht');self.preview_3d.setToolTip('Route schräg mit echten Wegpunkthöhen, offline.');self.preview_map=QPushButton('Luftbild');self.preview_map.setToolTip('Route auf dem Orthofoto; braucht Internet.');self.preview_image_button=QPushButton('Eigenes Bild …');self.preview_image_button.setToolTip('Eigenes Foto als Hintergrund wählen.');self.preview_archive=QPushButton('Archivbild');self.preview_archive.setToolTip('Vorschaubild aus dem Webarchiv (Routenzeichnung oder Bild aus dem Vorschau-Editor) als Titelbild.')
  for i,button in enumerate([self.preview_3d,self.preview_map,self.preview_image_button,self.preview_archive]):button.setCheckable(True);button.setObjectName('segment');self.preview_group.addButton(button,i);pv.addWidget(button)
  pv.addStretch();ev.addLayout(pv);self.preview_group.idClicked.connect(lambda i:self.set_preview_mode(['3d','map','image','archive'][i]))
  self.preview_label=QLabel();self.preview_label.setObjectName('muted');self.preview_label.setWordWrap(True);ev.addWidget(self.preview_label)
  self.image=PreviewLabel('Vorschau erscheint nach „Vorschauen erzeugen“',QSize(420,240));ev.addWidget(self.image,1)
  row=QHBoxLayout();back=QPushButton('◂  Missionen');back.setObjectName('quiet');back.clicked.connect(lambda:self.tabs.setCurrentIndex(TAB_ARCHIVE));row.addWidget(back);row.addStretch();self.prepare_button=QPushButton('Vorschauen erzeugen und prüfen  ▸');self.prepare_button.setObjectName('primary');self.prepare_button.clicked.connect(self.prepare);row.addWidget(self.prepare_button);right.addLayout(row)
  self.set_preview_mode(self.preview_mode,choose=False)
  # Seite 1: Prüfen
  page=QWidget();review=QHBoxLayout(page);review.setContentsMargins(0,0,0,0);review.setSpacing(14);self.stack.addWidget(page)
  left=self.card(review,3);self.heading(left,'Passt alles?','Jede Mission mit Titelbild, Name und Ziel prüfen. Vor jeder Übertragung wird der Bestand gesichert und jede Datei zurückgelesen.')
  self.review_list=QListWidget();self.review_list.setObjectName('missions');self.review_list.setSpacing(4);self.review_list.currentRowChanged.connect(self.review_selected);left.addWidget(self.review_list,1)
  right=self.card(review,3)
  self.review_image=PreviewLabel('Keine Vorschau',QSize(420,200));right.addWidget(self.review_image,1)
  self.summary_mode=QLabel();self.summary_mode.setObjectName('eyebrow');right.addWidget(self.summary_mode)
  self.summary_name=QLabel();self.summary_name.setObjectName('pageTitle');self.summary_name.setWordWrap(True);right.addWidget(self.summary_name)
  self.summary_points=QLabel();self.summary_target=QLabel();self.summary_target.setWordWrap(True);self.summary_source=QLabel();self.summary_source.setWordWrap(True);self.summary_preview=QLabel()
  right.addWidget(self.key_values([('Wegpunkte',self.summary_points),('Ziel',self.summary_target),('Quelle',self.summary_source),('Titelbild',self.summary_preview)]))
  self.review_note=QLabel();self.review_note.setWordWrap(True);self.review_note.setObjectName('hintBox');right.addWidget(self.review_note)
  self.closed=QCheckBox('DJI Fly ist vollständig geschlossen. Es ist kein Flug aktiv.');self.closed.toggled.connect(lambda checked:self.apply_button.setEnabled(checked and self.all_prepared()));right.addWidget(self.closed)
  row=QHBoxLayout();self.back_button=QPushButton('◂  Zurück');self.back_button.setObjectName('quiet');self.back_button.clicked.connect(lambda:self.stack.setCurrentIndex(0));row.addWidget(self.back_button);row.addStretch()
  self.apply_button=QPushButton('Jetzt übertragen  ▸');self.apply_button.setObjectName('primary');self.apply_button.setEnabled(False);self.apply_button.clicked.connect(self.execute);row.addWidget(self.apply_button);right.addLayout(row)

 def build_run_tab(self):
  layout=self.tab('');card=self.card(layout,1)
  head=QHBoxLayout();text=QVBoxLayout();text.setSpacing(2);title=QLabel('Übertragung');title.setObjectName('pageTitle');text.addWidget(title)
  self.run_note=QLabel('Die Warteschlange wird seriell auf das gewählte Gerät übertragen: sichern, schreiben, zurücklesen, dann die nächste Mission. Bei einem Fehler stoppt die Übertragung.');self.run_note.setObjectName('muted');self.run_note.setWordWrap(True);text.addWidget(self.run_note);head.addLayout(text,1)
  self.run_progress=QLabel('');self.run_progress.setObjectName('progressText');head.addWidget(self.run_progress);card.addLayout(head)
  self.run_list=QListWidget();self.run_list.setObjectName('missions');self.run_list.setSpacing(4);self.run_list.setSelectionMode(QListWidget.SingleSelection);self.run_list.currentRowChanged.connect(lambda *_:self.update_run_buttons());card.addWidget(self.run_list,1)
  self.run_empty=QLabel('Noch nichts übertragen. In Schritt 3 die Vorschauen prüfen und „Jetzt übertragen“ wählen.');self.run_empty.setObjectName('emptyList');self.run_empty.setAlignment(Qt.AlignCenter);self.run_empty.setWordWrap(True);card.addWidget(self.run_empty,1)
  row=QHBoxLayout();self.stop_button=QPushButton('Nach dem aktuellen Auftrag anhalten');self.stop_button.setObjectName('quiet');self.stop_button.setEnabled(False);self.stop_button.clicked.connect(self.request_stop);row.addWidget(self.stop_button)
  self.retry_button=QPushButton('Fehlgeschlagene erneut prüfen …');self.retry_button.setObjectName('quiet');self.retry_button.setEnabled(False);self.retry_button.clicked.connect(self.retry_failed);row.addWidget(self.retry_button)
  self.run_remove_button=QPushButton('Markierte entfernen');self.run_remove_button.setObjectName('quiet');self.run_remove_button.setEnabled(False);self.run_remove_button.setToolTip('Angehakte Aufträge (sonst den markierten) vor der Übertragung entfernen; die übrigen geprüften Aufträge bleiben bereit.');self.run_remove_button.clicked.connect(self.remove_run_selected);row.addWidget(self.run_remove_button);row.addStretch()
  self.resume_button=QPushButton('Fortsetzen  ▸');self.resume_button.setObjectName('primary');self.resume_button.setEnabled(False);self.resume_button.clicked.connect(self.execute);row.addWidget(self.resume_button);card.addLayout(row)

 def build_settings_dialog(self):
  d=QDialog(self);d.setWindowTitle('Einstellungen');d.setModal(False);d.resize(800,760);d.setMinimumSize(640,420);self.settings_dialog=d
  # Umbrechende Beschreibungen melden Qt eine zu kleine Mindesthöhe, die Karten würden sich bei kleinem Fenster überlagern.
  # Eine Scrollfläche mit widgetResizable berücksichtigt heightForWidth und hält die Zeilen auf jeder Fenstergröße auseinander.
  outer=QVBoxLayout(d);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0);scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);scroll.setObjectName('settingsScroll');outer.addWidget(scroll,1)
  content=QWidget();content.setObjectName('settingsContent');scroll.setWidget(content);layout=QVBoxLayout(content);layout.setContentsMargins(24,20,24,8);layout.setSpacing(14)
  card=self.card(layout);self.heading(card,'Webarchiv','Adresse des privaten Archivs und dein Zugangsschlüssel. Die Konfigurationsdatei aus dem Webarchiv (Bereich „Bridge“) enthält nur die Adresse.')
  grid=QGridLayout();grid.setHorizontalSpacing(10);grid.setVerticalSpacing(6)
  saved_url=self.settings.value('archiveURL','') or ''
  if re.match(r'^https?://(?:127\.0\.0\.1|localhost|\[::1\]|example\.(?:com|net|org))(?=[:/]|$)',saved_url,re.I) and not os.environ.get('DRONEMISSIONS_DEV'):saved_url='';self.settings.setValue('archiveURL',ARCHIVE_URL)
  grid.addWidget(QLabel('Archiv-Adresse'),0,0);self.archive_url=QLineEdit(saved_url or ARCHIVE_URL);self.archive_url.setPlaceholderText(ARCHIVE_URL);self.archive_url.editingFinished.connect(self.archive_url_edited);grid.addWidget(self.archive_url,1,0)
  grid.addWidget(QLabel('Zugangsschlüssel'),0,1);self.archive_key=QLineEdit();self.archive_key.setEchoMode(QLineEdit.Password);self.archive_key.setPlaceholderText('Nur für diese Sitzung, außer „merken“');self.archive_key.returnPressed.connect(self.archive_login);grid.addWidget(self.archive_key,1,1)
  self.archive_login_button=QPushButton('Verbinden');self.archive_login_button.setMinimumHeight(40);self.archive_login_button.clicked.connect(self.archive_login);grid.addWidget(self.archive_login_button,1,2,Qt.AlignTop);grid.setColumnStretch(0,3);grid.setColumnStretch(1,2);card.addLayout(grid)
  remember=QHBoxLayout();self.store_pref=self.settings.value('credentialStore','auto') or 'auto';stores=self.credential_store.available()
  self.archive_remember=QCheckBox('Schlüssel merken');self.archive_remember.setEnabled(bool(stores));remember.addWidget(self.archive_remember)
  remember.addWidget(QLabel('in'));self.archive_store=QComboBox();labels={'keychain':'macOS-Schlüsselbund','1password':'1Password','dpapi':'Windows (DPAPI)'}
  for key in stores:self.archive_store.addItem(labels[key],key)
  if not stores:self.archive_store.addItem('kein Schlüsselspeicher verfügbar',None)
  index=self.archive_store.findData(self.store_pref);self.archive_store.setCurrentIndex(index if index>=0 else 0);self.archive_store.currentIndexChanged.connect(lambda _:self.settings.setValue('credentialStore',self.archive_store.currentData() or 'auto'));remember.addWidget(self.archive_store)
  self.archive_forget=QPushButton('Schlüssel vergessen');self.archive_forget.setObjectName('quiet');self.archive_forget.setEnabled(False);self.archive_forget.clicked.connect(self.archive_forget_key);remember.addWidget(self.archive_forget)
  config=QPushButton('Konfiguration laden …');config.setObjectName('quiet');config.setToolTip('Konfigurationsdatei aus dem Webarchiv einlesen: setzt die Archiv-Adresse.');config.clicked.connect(lambda checked=False:self.archive_import_config());remember.addWidget(config);remember.addStretch();card.addLayout(remember)
  self.archive_note=QLabel('Noch nicht verbunden.');self.archive_note.setObjectName('muted');self.archive_note.setWordWrap(True);card.addWidget(self.archive_note)
  card=self.card(layout);self.heading(card,'Android-Verbindung','ADB wird nur für die Fernsteuerung benötigt. Für iPad/iPhone ist kein ADB nötig.')
  row=QHBoxLayout();self.adb=QLineEdit();self.adb.setReadOnly(True);bundled=bundled_adb();saved=self.settings.value('adb','')
  self.adb.setText(saved or (str(bundled) if bundled else '') or shutil.which('adb') or '');self.adb.textChanged.connect(self.invalidate);row.addWidget(self.adb,1)
  button=QPushButton('ADB wählen …');button.clicked.connect(self.choose_adb);row.addWidget(button)
  reset=QPushButton('Eingebautes ADB');reset.setObjectName('quiet');reset.setEnabled(bundled is not None);reset.clicked.connect(lambda:(self.settings.remove('adb'),self.adb.setText(str(bundled)),self.adb_note.setText('Eingebautes ADB aus den Android Platform-Tools 37.0.1, Prüfsumme bestätigt.')));row.addWidget(reset);card.addLayout(row)
  self.adb_note=QLabel('Eingebautes ADB aus den Android Platform-Tools 37.0.1, Prüfsumme bestätigt.' if bundled and not saved else ('Eigener ADB-Pfad aus den Einstellungen.' if saved else 'Kein ADB gefunden. Für die Fernsteuerung ADB wählen; iPad/iPhone funktioniert ohne.'));self.adb_note.setObjectName('muted');self.adb_note.setWordWrap(True);card.addWidget(self.adb_note)
  card=self.card(layout);self.heading(card,'Ablage','Sicherungen, Transferjournale, Übertragungskopien und geladene Archivdateien liegen im Anwendungsdatenordner.')
  row=QHBoxLayout();button=QPushButton('Ordner öffnen');button.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.root))));row.addWidget(button);path=QLabel(str(self.root));path.setObjectName('ident');path.setWordWrap(True);row.addWidget(path,1);card.addLayout(row)
  label=QLabel(f'{APP_NAME} {VERSION} · GPL-3.0-or-later · Lizenzen im Programmpaket. Dateiprüfung ist keine Bestätigung eines nutzbaren Flugplans.');label.setObjectName('muted');label.setWordWrap(True);layout.addWidget(label)
  layout.addStretch();foot=QHBoxLayout();foot.setContentsMargins(24,10,24,16);foot.addStretch();close=QPushButton('Schließen');close.clicked.connect(d.close);foot.addWidget(close);outer.addLayout(foot)
  self.archive_restore_key()
 def build_log_dialog(self):
  d=QDialog(self);d.setWindowTitle('Protokoll');d.setModal(False);d.resize(760,480);self.log_dialog=d;layout=QVBoxLayout(d);layout.setContentsMargins(20,16,20,16)
  self.log=QPlainTextEdit();self.log.setReadOnly(True);layout.addWidget(self.log,1)
  row=QHBoxLayout();button=QPushButton('Sicherungen öffnen');button.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.root))));row.addWidget(button);row.addStretch();close=QPushButton('Schließen');close.clicked.connect(d.close);row.addWidget(close);layout.addLayout(row)
 def show_settings(self):self.settings_dialog.show();self.settings_dialog.raise_();self.settings_dialog.activateWindow()
 def show_log(self):self.log_dialog.show();self.log_dialog.raise_();self.log_dialog.activateWindow()

 def build_menu(self):
  """Native Menüleiste (macOS oben, Windows im Fenster) mit den Hauptfunktionen und Tastenkürzeln."""
  bar=self.menuBar();bar.setNativeMenuBar(True);self.menu_actions={}
  def add(menu,text,slot,shortcut=None,role=None):
   action=QAction(text,self);action.triggered.connect(lambda *_:slot())
   if shortcut:action.setShortcut(QKeySequence(shortcut))
   if role is not None:action.setMenuRole(role)
   menu.addAction(action);self.menu_actions[text]=action;return action
  datei=bar.addMenu('Datei');add(datei,'KMZ-Dateien hinzufügen …',self.choose_kmz,'Ctrl+O');add(datei,'Eigenes Vorschaubild …',self.choose_preview,'Ctrl+Shift+O');add(datei,'Bridge-Konfiguration laden …',self.archive_import_config);datei.addSeparator()
  add(datei,'Einstellungen …',self.show_settings,'Ctrl+,',QAction.PreferencesRole);add(datei,'Protokoll',self.show_log,'Ctrl+Shift+P');add(datei,'Sicherungen öffnen',lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.root))));datei.addSeparator();add(datei,'Beenden',self.close,'Ctrl+Q',QAction.QuitRole)
  geraet=bar.addMenu('Gerät');add(geraet,'Geräte neu suchen',self.refresh_devices,'Ctrl+R');add(geraet,'Missionen lesen',self.list_missions,'Ctrl+L');add(geraet,'Gerät sichern …',self.backup,'Ctrl+B');geraet.addSeparator()
  add(geraet,'Umbenennen …',self.rename_selected,'Ctrl+E');add(geraet,'Neu anlegen',self.start_new,'Ctrl+N');add(geraet,'Ausgewählte ersetzen …',self.start_replace,'Ctrl+Shift+R');geraet.addSeparator();add(geraet,'Im Webarchiv sichern …',self.save_to_archive,'Ctrl+S')
  archiv=bar.addMenu('Webarchiv');add(archiv,'Verbinden und Bibliothek laden',lambda:(self.tabs.setCurrentIndex(TAB_ARCHIVE),self.archive_login()),'Ctrl+Shift+L');add(archiv,'Ausgewählte zur Übertragung übernehmen',self.archive_use,'Ctrl+U');archiv.addSeparator();add(archiv,'Webarchiv im Browser öffnen',lambda:QDesktopServices.openUrl(QUrl(self.archive_url.text().strip() or ARCHIVE_URL)))
  transfer=bar.addMenu('Übertragen');add(transfer,'Vorschauen erzeugen und prüfen',self.prepare,'Ctrl+Return');add(transfer,'Jetzt übertragen',self.execute,'Ctrl+Shift+Return');transfer.addSeparator();add(transfer,'Modus: Neu anlegen',lambda:self.set_mode('new'));add(transfer,'Modus: Ersetzen',lambda:self.set_mode('replace'));transfer.addSeparator();add(transfer,'Warteschlange leeren',self.clear_queue)
  ansicht=bar.addMenu('Ansicht')
  for i,title in enumerate(STEP_TITLES):add(ansicht,f'{i+1}  {title}',lambda i=i:self.tabs.setCurrentIndex(i),f'Ctrl+{i+1}')
  hilfe=bar.addMenu('Hilfe');add(hilfe,'Anleitung (README)',lambda:QDesktopServices.openUrl(QUrl('https://github.com/studiobaff/dronemissions/blob/main/dronemissions/docs/BRIDGE.md')));add(hilfe,'Über '+APP_NAME,self.about,None,QAction.AboutRole)
 def about(self):
  QMessageBox.about(self,'Über '+APP_NAME,f'<b>{APP_NAME} {VERSION}</b><br>Überträgt DJI-KMZ-Missionen aus dem Webarchiv per USB auf iPad, iPhone oder DJI-Fernsteuerung.<br><br>GPL-3.0-or-later · Lizenzen im Programmpaket.<br>Dateiprüfung ist keine Bestätigung eines nutzbaren Flugplans.')

 # ---------- Zustand ----------
 def log_line(self,text):self.log.appendPlainText(datetime.now().strftime('%H:%M:%S')+'  '+text)
 def current_device(self):return self.device.currentData()
 def is_ios(self):r=self.current_device();return bool(r and r['kind']=='ios')
 def row_label(self,r,m,index):return m.get('name') or (self.registry.get(r['serial']+':'+m['uuid']) if r else None) or 'Eintrag '+str(index+1)
 def tab_changed(self,i):
  if i==TAB_ARCHIVE and self.archive_auto and self.archive is None and not (self.job and self.job.isRunning()):self.archive_login()
  if i==TAB_TRANSFER:self.render_queue()
 # Warteschlange
 def entry(self):return self.queue[self.current] if 0<=self.current<len(self.queue) else None
 @property
 def transfer(self):
  e=self.entry();return e['plan'] if e else self.loose_transfer
 @transfer.setter
 def transfer(self,value):
  e=self.entry()
  if e:e['plan']=value;e['status']='prepared' if value else 'ready'
  else:self.loose_transfer=value
 @property
 def source_path(self):e=self.entry();return e['source'] if e else None
 @property
 def original_source(self):e=self.entry();return e['original'] if e else None
 def all_prepared(self):return bool(self.queue) and all(e['plan'] is not None for e in self.queue if e['status']!='done')
 def add_entry(self,path,name=None,archive_mission=None,archive_preview=None):
  """archive_preview: Bilddatei (JPEG/PNG) aus dem Webarchiv; Archivmissionen nutzen sie als Listenbild und standardmäßig als Titelbild."""
  original=Path(path);mode=self.preview_mode
  if archive_preview:mode='archive'
  elif mode=='archive':mode='3d'
  entry={'id':uuid.uuid4().hex,'original':original,'source':original,'name':name or original.stem,'mode':self.mode,'target':None,'targetLabel':None,'previewMode':mode,'background':self.background_path if mode=='image' else None,'archiveMission':archive_mission,'archivePreview':Path(archive_preview) if archive_preview else None,'details':None,'plan':None,'preview':None,'status':'ready','error':None,'note':''}
  try:
   prepared=prepare_source(original,self.root/'cleaned');entry['source']=prepared['path'];details=inspect_kmz(entry['source'].read_bytes());entry['details']=details
   text=f'{details["waypoints"]} Wegpunkte · {details["distance"]/1000:.2f} km · {len(details["segments"])} Flugroute(n)'
   if prepared['cleaned']:
    merged=', '.join(str(m['index']+1) for m in prepared['report']['merged']);text+=f' · Übertragungskopie: doppelter Schlusspunkt {merged} zusammengeführt (Stopp erhalten), Original unverändert';self.log_line(f'Übertragungskopie angelegt: {entry["source"]} (Original {original})')
   if archive_mission:text+=f' · aus dem Webarchiv, V{archive_mission.get("version") or "?"}, Prüfsumme bestätigt'
   entry['note']=text
   # Sofort eine schnelle Vorschau für Liste und Editor (Archivbild oder Offline-3D); das endgültige Titelbild entsteht bei „Vorschauen erzeugen“.
   try:entry['preview']=render_preview(self.root/'previews'/('quick-'+entry['id']+'.jpg'),entry['name'],details,entry['archivePreview'])
   except Exception as e:self.log_line('Schnellvorschau nicht möglich: '+str(e))
  except Exception as e:entry['note']='Datei kann nicht gelesen werden: '+str(e);entry['error']=str(e)
  if self.mode=='replace' and self.pending_target and not any(x.get('target')==self.pending_target['uuid'] for x in self.queue):
   entry['target']=self.pending_target['uuid'];entry['targetLabel']=self.pending_target['label'];self.pending_target=None
  self.queue.append(entry);self.current=len(self.queue)-1;self.loose_transfer=None;self.render_queue();self.show_entry();return entry
 def set_source(self,path):
  """Eine lokale KMZ in die Warteschlange aufnehmen und als aktuellen Eintrag anzeigen."""
  return self.add_entry(path)
 def choose_kmz(self):
  paths,_=QFileDialog.getOpenFileNames(self,'DJI-KMZ auswählen','','DJI-KMZ (*.kmz *.KMZ)')
  for path in paths:self.add_entry(path)
  if paths:self.tabs.setCurrentIndex(TAB_TRANSFER);self.status.setText(f'{len(paths)} Datei(en) in die Warteschlange aufgenommen. Namen prüfen, dann Vorschauen erzeugen.')
 def render_queue(self):
  self.queue_list.blockSignals(True);self.queue_list.clear()
  for i,e in enumerate(self.queue):
   row=QueueRow(e,i,i==self.current,checked=e['id'] in self.queue_checked,on_toggle=self.queue_toggle);item=QListWidgetItem();item.setSizeHint(QSize(0,max(104,row.sizeHint().height()+4)));self.queue_list.addItem(item);self.queue_list.setItemWidget(item,row)
  if 0<=self.current<len(self.queue):self.queue_list.setCurrentRow(self.current)
  self.queue_list.blockSignals(False);has=bool(self.queue);self.queue_list.setVisible(has);self.queue_empty.setVisible(not has);self.editor.setEnabled(has);self.queue_remove.setEnabled(self.entry() is not None);self.queue_clear.setEnabled(has);self.prepare_button.setEnabled(has)
  prepared=sum(1 for e in self.queue if e['plan']);self.queue_count.setText(f'{len(self.queue)} Mission(en)'+(f' · {prepared} geprüft' if prepared else ''))
  self.tabs.setTabEnabled(TAB_RUN,bool(self.queue));self.update_steps()
  if hasattr(self,'run_list') and not (self.job and self.job.isRunning()):self.render_run_list()  # Schritt 4 zeigt die Warteschlange schon vor der Übertragung
 def queue_selected(self,row):
  if row<0 or row>=len(self.queue) or row==self.current:return
  self.current=row;self.show_entry()
 def show_entry(self):
  e=self.entry()
  for w in (self.name,self.mode_new,self.mode_replace):w.blockSignals(True)
  if e:
   self.name.setText(e['name']);self.mode=e['mode'];self.mode_new.setChecked(e['mode']=='new');self.mode_replace.setChecked(e['mode']=='replace')
   self.source_label.setText(e['original'].name);self.source_label.setToolTip(str(e['original']));self.source_meta.setText(e['note'])
   self.preview_mode=e['previewMode'];self.background_path=e['background']
   self.preview_archive.setVisible(bool(e.get('archivePreview')))
   for button,key in [(self.preview_3d,'3d'),(self.preview_map,'map'),(self.preview_image_button,'image'),(self.preview_archive,'archive')]:button.setChecked(key==self.preview_mode)
   self.preview_label.setText(self.preview_text())
   pixmap=QPixmap(str(e['preview'])) if e.get('preview') and Path(e['preview']).is_file() else QPixmap()
   self.image.set_source(pixmap)
  else:self.name.setText('');self.source_label.setText('Noch keine KMZ ausgewählt');self.source_meta.setText('Export aus Litchi, Map Creator oder dem Webarchiv.');self.image.set_source(None)
  for w in (self.name,self.mode_new,self.mode_replace):w.blockSignals(False)
  self.target_panel.setVisible(self.mode=='replace');self.new_note.setVisible(self.mode=='new');self.update_mode_notes();self.queue_remove.setEnabled(e is not None)
 def name_edited(self,text):
  e=self.entry()
  if e and e['name']!=text:e['name']=text;self.invalidate();self.quick_timer.start()
 def quick_preview(self):
  """Schnellvorschau mit dem aktuellen Namen erneuern (entprellt, 350 ms nach der letzten Eingabe)."""
  e=self.entry()
  if not e or not e.get('details') or e['status']=='done':return
  try:e['preview']=render_preview(self.root/'previews'/('quick-'+e['id']+'.jpg'),e['name'].strip() or e['original'].stem,e['details'],e.get('archivePreview') if e['previewMode']=='archive' else None);self.image.set_source(QPixmap(str(e['preview'])));self.render_queue()
  except Exception as err:self.log_line('Schnellvorschau nicht möglich: '+str(err))
 def queue_toggle(self,entry_id,state):
  if state:self.queue_checked.add(entry_id)
  else:self.queue_checked.discard(entry_id)
  self.update_run_buttons();self.queue_remove.setEnabled(bool(self.queue_checked) or self.entry() is not None)
 def removal_targets(self,fallback):
  """Angehakte Aufträge, sonst der übergebene Einzelauftrag; laufende Aufträge nie."""
  picked=[e for e in self.queue if e['id'] in self.queue_checked and e['status']!='running']
  if picked:return picked
  return [fallback] if fallback and fallback['status']!='running' else []
 def remove_entries(self,entries):
  if not entries or (self.job and self.job.isRunning()):return 0
  ids={e['id'] for e in entries};current_id=self.entry()['id'] if self.entry() else None
  self.queue=[e for e in self.queue if e['id'] not in ids];self.queue_checked-=ids
  self.current=next((i for i,e in enumerate(self.queue) if e['id']==current_id),min(max(self.current,0),len(self.queue)-1) if self.queue else -1)
  if self.pending_target and any(e.get('target')==self.pending_target.get('uuid') for e in entries):self.pending_target=None
  return len(entries)
 def remove_current(self):
  targets=self.removal_targets(self.entry())
  if not targets:return
  count=self.remove_entries(targets);self.invalidate();self.render_queue();self.show_entry();self.status.setText(f'{count} Auftrag/Aufträge entfernt.')
 def clear_queue(self):
  if self.job and self.job.isRunning():return
  self.queue=[];self.current=-1;self.pending_target=None;self.invalidate();self.render_queue();self.show_entry();self.render_run_list()
 def set_mode(self,mode):
  self.mode=mode;e=self.entry()
  if e:
   if e['mode']!=mode:e['mode']=mode;self.invalidate()
   if mode=='new':e['target']=None;e['targetLabel']=None
  self.mode_new.setChecked(mode=='new');self.mode_replace.setChecked(mode=='replace')
  self.target_panel.setVisible(mode=='replace');self.new_note.setVisible(mode=='new');self.update_mode_notes();self.render_queue()
 def update_mode_notes(self):
  ios_device=self.is_ios();r=self.current_device()
  if self.mode=='new':
   self.mode_note.setText('Neue Mission mit eigener Kennung anlegen. Bestehende Missionen bleiben unverändert.'+('' if ios_device or not r else ' Auf Android ist der Neuimport experimentell: Die Dateien werden geprüft übertragen, die Sichtbarkeit in DJI Fly ist nicht bestätigt. Geprüfter Weg auf der RC Pro 2 ist „Ersetzen“.'))
   self.new_note.setText('Auf dem iPad/iPhone erscheint die Mission mit Name und Titelbild in DJI Fly.' if ios_device else 'Nach der Übertragung Gerät neu starten und in DJI Fly prüfen, ob die Mission erscheint.')
  else:
   self.mode_note.setText('Den gewählten Eintrag nach vollständiger Sicherung ersetzen. Jeder Auftrag braucht ein eigenes Ziel; Dateien werden zuerst unter temporärem Namen geschrieben und zurückgelesen.'+(' Auf dem iPad ist das Ersetzen noch nicht am Gerät geprüft; geprüfter Weg ist „Neu anlegen“.' if ios_device else ' Auf der RC Pro 2 ist danach ein Neustart erforderlich.'))
  self.update_target_card()
 def target_row(self,uid):return next((m for m in self.rows if m['uuid']==uid),None)
 def update_target_card(self):
  e=self.entry();r=self.current_device();m=self.target_row(e['target']) if e and e.get('target') else None
  if not e or not e.get('target'):self.target_image.setPixmap(placeholder(THUMB,'Kein Ziel'));self.target_name.setText('Noch kein Eintrag gewählt.');self.target_meta.setText('In Schritt 1 die zu ersetzende Mission markieren und „Ausgewählte ersetzen“ wählen.');return
  pixmap=QPixmap()
  if m and m.get('image') and pixmap.loadFromData(m['image']):self.target_image.setPixmap(pixmap.scaled(THUMB,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation))
  else:self.target_image.setPixmap(placeholder(THUMB,'Kein Vorschaubild'))
  self.target_name.setText(e.get('targetLabel') or e['target']);self.target_meta.setText((f'{m.get("waypoints","—")} Wegpunkte · {STATE_LABELS.get(m.get("localState"),"—")} · ' if m else 'Eintrag nicht in der aktuellen Geräteliste · ')+'Kennung '+e['target'])
 def changed_device(self,*args):
  self.invalidate();self.rows=[];self.checked=set();self.pending_target=None;self.list.clear();self.list.hide();self.list_empty.show();self.list_empty.setText('Noch keine Missionen gelesen.')
  for e in self.queue:
   if e.get('target'):e['target']=None;e['targetLabel']=None
  r=self.current_device();self.replace_button.setEnabled(False);self.selected_label.setText('Kein Eintrag ausgewählt.')
  if hasattr(self,'checked_label'):self.update_checked()
  if r:self.device_note.setText(('iPad/iPhone: Neue Mission mit Name und Titelbild anlegen (geprüft).' if r['kind']=='ios' else 'Fernsteuerung: Bestehenden Eintrag nach Sicherung ersetzen (geprüft). Danach Neustart erforderlich.')+' Vor jeder Übertragung wird der Bestand gesichert.')
  else:self.device_note.setText('Gerät auswählen, um fortzufahren.')
  self.update_mode_notes()
  if hasattr(self,'queue_list'):self.render_queue()
 def changed_target(self):
  device=self.current_device();self.remove_device_button.setEnabled(bool(self.checked) and bool(device and device.get('kind')=='ios'))
  m=self.selected_row();self.cloud_download_button.setEnabled(bool(m and m.get('localState')=='cloud-or-missing'));self.replace_button.setEnabled(m is not None and m.get('localState')=='local');r=self.current_device()
  self.rename_button.setEnabled(m is not None or len(self.checked)==1);self.rename_button.setToolTip('Name in DJI Fly ändern (iPad/iPhone)' if r and r['kind']=='ios' else 'Auf Android nur das Etikett in der Bridge; der DJI-Fly-Name ist dort nicht erreichbar.')
  if m:self.selected_label.setText(f'Ausgewählt: {self.row_label(r,m,self.rows.index(m))}'+('' if m.get('localState')=='local' else ' · nur lokal vorhandene Missionen lassen sich ersetzen'))
  else:self.selected_label.setText('Kein Eintrag ausgewählt.')
 def invalidate(self,*args):
  """Jede Änderung an Quelle, Name, Bild, Ziel oder Gerät verwirft alle vorbereiteten Pläne."""
  self.loose_transfer=None
  for e in self.queue:
   if e['status']!='done':e['plan']=None;e['status']='ready';e['error']=None
  if hasattr(self,'apply_button'):self.apply_button.setEnabled(False)
  if hasattr(self,'stack') and self.stack.currentIndex()==1:self.stack.setCurrentIndex(0)
  if hasattr(self,'resume_button'):self.resume_button.setEnabled(False)
 def start_new(self):
  self.pending_target=None;self.set_mode('new');self.tabs.setCurrentIndex(TAB_ARCHIVE if not self.queue else TAB_TRANSFER);self.status.setText('Neu anlegen: Missionen aus dem Webarchiv übernehmen oder KMZ-Dateien vom Mac wählen.')
 def start_replace(self):
  m=self.selected_row()
  if not m or m.get('localState')!='local':self.status.setText('Zuerst eine lokal vorhandene Mission in der Liste markieren.');return
  r=self.current_device();label=self.row_label(r,m,self.rows.index(m))
  if any(e.get('target')==m['uuid'] and e['status']!='done' for e in self.queue):self.status.setText(f'„{label}“ ist bereits Ziel eines Auftrags in der Warteschlange.');self.tabs.setCurrentIndex(TAB_TRANSFER);return
  e=self.entry()
  if e and e['mode']=='replace' and not e.get('target'):e['target']=m['uuid'];e['targetLabel']=label;self.invalidate();self.render_queue()
  else:self.pending_target={'uuid':m['uuid'],'label':label}
  self.set_mode('replace');self.tabs.setCurrentIndex(TAB_TRANSFER if (e and e.get('target')) else TAB_ARCHIVE);self.status.setText(f'Ersetzen von „{label}“: '+('Vorschauen erzeugen und prüfen.' if e and e.get('target') else 'Jetzt die Quelle wählen (Webarchiv oder KMZ-Datei).'))
 def closeEvent(self,event):
  if self.job and self.job.isRunning():QMessageBox.information(self,'Aktion läuft','Bitte die laufende Aktion abschließen lassen.');event.ignore()
  else:event.accept()
 def selected_device(self):
  r=self.current_device()
  if not r or r.get('state')!='device':raise BridgeError('Bitte ein verbundenes, entsperrtes Gerät auswählen.')
  return dict(r)
 def adb_for(self,r):return Adb(self.adb.text().strip(),r['serial'])
 def task(self,label,fn,done,progress=None):
  if self.job and self.job.isRunning():return
  self.status.setText(label);self.log_line(label);self.body.setEnabled(False);self.toolbar.setEnabled(False);self.menuBar().setEnabled(False);self.progress.show();j=Job(fn,self,with_progress=progress is not None);self.job=j
  def enable():self.body.setEnabled(True);self.toolbar.setEnabled(True);self.menuBar().setEnabled(True);self.progress.hide()
  def ok(result):
   enable()
   try:done(result)
   except Exception as e:self.error(str(e))
  def fail(text):enable();self.error(text)
  j.result.connect(ok);j.error.connect(fail)
  if progress:j.progress.connect(progress)
  j.start()
 def error(self,text):self.status.setText(text);self.log_line('FEHLER: '+text);QMessageBox.warning(self,'Bitte prüfen',text)

 # ---------- Dateien / Titelbild ----------
 def choose_adb(self):
  path,_=QFileDialog.getOpenFileName(self,'ADB auswählen')
  if path:self.adb.setText(path);self.settings.setValue('adb',path);self.adb_note.setText('Eigener ADB-Pfad aus den Einstellungen.')
 def preview_text(self):
  return {'3d':'3D-Ansicht: Route schräg mit echten Wegpunkthöhen, offline erzeugt; ohne vergleichbare Höhen Draufsicht.','map':'Luftbild: Route mit Wegpunktnummern auf dem Orthofoto; in Österreich basemap.at mit Beschriftung, sonst Esri World Imagery bzw. OpenStreetMap (braucht Internet). Ohne Kartenquelle 3D-Ansicht.','image':'Eigenes Bild: '+(self.background_path.name if self.background_path else ''),'archive':'Archivbild: Vorschau aus dem Webarchiv (Routenzeichnung oder Bild aus dem Vorschau-Editor) als Titelbild, ohne Internet.'}[self.preview_mode]
 def set_preview_mode(self,mode,choose=True):
  if mode=='image' and choose:
   path,_=QFileDialog.getOpenFileName(self,'Bildhintergrund auswählen','','Bilder (*.jpg *.jpeg *.png)')
   if not path:self.set_preview_mode('image' if self.background_path else '3d',choose=False);return
   self.background_path=Path(path)
  if mode!='image':self.background_path=None
  current=self.entry()
  if mode=='archive' and not (current and current.get('archivePreview')):mode='3d'  # Archivbild gibt es nur für Missionen aus dem Webarchiv
  self.preview_mode=mode if mode!='image' or self.background_path else '3d'
  if self.preview_mode!='image':self.settings.setValue('previewMode',self.preview_mode)
  for button,key in [(self.preview_3d,'3d'),(self.preview_map,'map'),(self.preview_image_button,'image'),(self.preview_archive,'archive')]:button.setChecked(key==self.preview_mode)
  self.preview_label.setText(self.preview_text())
  e=self.entry()
  if e and (e['previewMode']!=self.preview_mode or e['background']!=self.background_path):e['previewMode']=self.preview_mode;e['background']=self.background_path;self.invalidate()
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
     try:
      raw=a.read(m['path']);m['sha256']=digest(raw);details=inspect_kmz(raw);m.update(waypoints=details['waypoints'],distance=details['distance']);m['updated']=numeric(a.shell('stat -c %Y '+shlex.quote(m['path']),check=False))
     except BridgeError:m['waypoints']='prüfen'
    if m['preview']:
     try:m['image']=a.read(f'{BASE}/map_preview/{m["uuid"]}/{m["uuid"]}.jpg')
     except Exception:pass
   return rows
  self.task('Missionen auf dem Gerät lesen …',read,lambda rows:self.show_rows(r,rows))
 def show_rows(self,r,rows):
  self.rows=rows;self.checked=set();self.render_device_list()
  self.list_note.setText(f'{len(rows)} Missionen auf {r["name"]}. Vergleiche Bild und Punktzahl mit DJI Fly.'+(' Der Listenname auf Android ist für die Bridge nicht lesbar.' if r['kind']=='android' else ''))
  self.status.setText(f'{len(rows)} Missionen gelesen.');self.changed_target();self.update_target_card()
 def local_filter_changed(self,value):
  if value:self.device_cloud_only.setChecked(False)
  self.settings.setValue('deviceLocalOnly',value);self.render_device_list()
 def cloud_filter_changed(self,value):
  if value:self.device_local_only.setChecked(False);self.device_unsaved_only.setChecked(False)
  self.render_device_list()
 def unsaved_filter_changed(self,value):
  if value:self.device_cloud_only.setChecked(False);self.device_local_only.setChecked(True)
  self.render_device_list()
 def cloud_download_help(self):
  m=self.selected_row()
  if not m or m.get('localState')!='cloud-or-missing':return
  QMessageBox.information(self,'Cloud-Mission herunterladen',f'„{self.row_label(self.current_device(),m,self.rows.index(m))}“ hat keine lokale KMZ.\n\n1. DJI Fly auf dem Gerät öffnen.\n2. Im Missionsverlauf diese Mission öffnen/herunterladen (Internet nötig).\n3. Danach hier „Missionen lesen“ wählen.\n\nDie Bridge hat keinen direkten Zugriff auf den DJI-Cloud-Download. Der Archiv-Sicherungsstatus bleibt ohne lokale Datei ungeprüft.')
 def visible_rows(self):
  q=self.device_search.text().strip().lower();r=self.current_device()
  rows=[(i,m) for i,m in enumerate(self.rows) if (not self.device_local_only.isChecked() or m.get('localState')=='local') and (not self.device_cloud_only.isChecked() or m.get('localState')=='cloud-or-missing') and (not self.device_unsaved_only.isChecked() or archive_state(m,self.archive_rows,self.archive is not None)=='missing') and (not q or q in self.row_label(r,m,i).lower() or q in m['uuid'].lower())]
  return sort_rows(rows,self.device_sort.currentData(),lambda i,m:self.row_label(r,m,i))
 def render_device_list(self,*args):
  if self.archive is None and self.device_unsaved_only.isChecked():self.device_unsaved_only.blockSignals(True);self.device_unsaved_only.setChecked(False);self.device_unsaved_only.blockSignals(False)
  r=self.current_device();current=self.selected_row();self.list.clear();self.device_rows_widgets=[]
  for i,m in self.visible_rows():
   item=QListWidgetItem();item.setSizeHint(QSize(0,THUMB.height()+18));item.setToolTip('Kennung: '+m['uuid']);item.setData(Qt.UserRole,i);self.list.addItem(item)
   state=archive_state(m,self.archive_rows,self.archive is not None);display={**m,'archiveState':state,'archiveStatus':{'saved':'Im Webarchiv: identische KMZ','missing':'KMZ nicht im geladenen Webarchiv gefunden','unknown':'Archivstatus: nicht geprüft'}[state]}
   if state=='saved':
    matches=[entry for entry in self.archive_rows if entry.get('sha256')==m.get('sha256')];display['archiveStatus']+='\n'+('\n'.join(entry.get('name','')+' · '+entry.get('folder','') for entry in matches))
   fallback=next((entry['pixmap'] for entry in self.archive_rows if state=='saved' and entry.get('sha256')==m.get('sha256') and entry.get('pixmap') is not None),None) if not m.get('image') else None
   widget=MissionRow(self.row_label(r,m,i),display,m.get('image'),checked=m['uuid'] in self.checked,on_toggle=self.toggle_checked,fallback=fallback);self.list.setItemWidget(item,widget);self.device_rows_widgets.append((m,widget))
   if current and current['uuid']==m['uuid']:self.list.setCurrentItem(item)
  self.device_count.setText(f'{len(self.device_rows_widgets)} von {len(self.rows)} sichtbar');visible=bool(self.device_rows_widgets);self.list.setVisible(visible);self.list_empty.setVisible(not visible);self.list_empty.setText('Keine Mission passt zu Suche und Filter.' if self.rows else 'Keine Missionen auf dem Gerät gefunden.');self.update_checked()
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
  self.device_unsaved_only.setEnabled(self.archive is not None)
  self.save_web_button.setEnabled(bool(local) and self.archive is not None);self.save_web_button.setToolTip('' if self.archive else 'Zuerst mit dem Webarchiv verbinden (Schritt 2 oder Einstellungen).')
  self.sync_preview_button.setEnabled(self.archive is not None and bool(self.preview_sync_candidates()))
  self.rename_button.setEnabled(self.selected_row() is not None or len(self.checked)==1)
  device=self.current_device();self.remove_device_button.setEnabled(bool(total) and bool(device and device.get('kind')=='ios'))
  visible=self.visible_rows();count=sum(m['uuid'] in self.checked for _,m in visible);state=Qt.Checked if visible and count==len(visible) else Qt.PartiallyChecked if count else Qt.Unchecked
  self.select_all.blockSignals(True);self.select_all.setCheckState(state);self.select_all.blockSignals(False)
 def rename_target(self):
  """Markierte Zeile; sonst die einzige angehakte Mission."""
  m=self.selected_row()
  if m:return m
  if len(self.checked)==1:uid=next(iter(self.checked));return next((x for x in self.rows if x['uuid']==uid),None)
  return None
 def rename_selected(self):
  m=self.rename_target()
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
 def remove_device_missions(self):
  if self.job and self.job.isRunning():return
  try:r=self.selected_device()
  except Exception as e:self.error(str(e));return
  picked=[m for m in self.rows if m['uuid'] in self.checked]
  if r.get('kind')!='ios' or not picked:self.status.setText('Bitte zuerst die zu entfernenden iPad-Missionen anhaken.');return
  saved=sum(archive_state(m,self.archive_rows,self.archive is not None)=='saved' for m in picked)
  names=[self.row_label(r,m,self.rows.index(m)) for m in picked]
  note=f'{saved} von {len(picked)} sind als identische KMZ im geladenen Webarchiv bestätigt.'
  if saved<len(picked):note+='\nZum späteren Neuübertragen zuerst „Im Webarchiv sichern“ verwenden. Die lokale Sicherung ersetzt kein Webarchiv.'
  text=f'{len(picked)} angehakte Mission(en) nur vom iPad entfernen?\n\n'+'\n'.join(names)+'\n\n'+note+'\n\nVorher wird der vollständige Gerätebestand gesichert. Webarchiv und bestehende Cloud-Kopien werden nicht gelöscht; Cloud-Kopien können nach Synchronisation wieder erscheinen.'
  dialog=QMessageBox(self);dialog.setWindowTitle('Vom iPad entfernen');dialog.setIcon(QMessageBox.Warning);dialog.setText(text)
  closed=QCheckBox('DJI Fly ist vollständig geschlossen und kein Flug aktiv.');dialog.setCheckBox(closed)
  remove=dialog.addButton('Sichern und vom iPad entfernen',QMessageBox.DestructiveRole);cancel=dialog.addButton(QMessageBox.Cancel);dialog.setDefaultButton(cancel);remove.setEnabled(False);closed.toggled.connect(remove.setEnabled);dialog.exec()
  if dialog.clickedButton()!=remove or not closed.isChecked():return
  targets=[{k:m[k] for k in ('uuid','name','updated') if k in m} for m in picked];ids={m['uuid'] for m in picked}
  dest=self.root/'transfers'/(datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'-remove')
  def done(result):
   self.rows=[m for m in self.rows if m['uuid'] not in ids];self.checked.difference_update(ids)
   for e in self.queue:
    if e.get('target') in ids:e['target']=None;e['targetLabel']=None;e['plan']=None;e['status']='ready'
   self.render_device_list();self.changed_target();self.render_queue();self.update_target_card()
   self.list_note.setText(f'{len(self.rows)} Missionen auf {r["name"]}.');self.status.setText(f'{len(ids)} Mission(en) vom iPad entfernt und zurückgeprüft. Webarchiv unverändert.')
   self.log_line('Sicherung und Entfernen bestätigt: '+str(dest));QMessageBox.information(self,'Vom iPad entfernt',f'{len(ids)} Mission(en) lokal entfernt.\n\nWebarchiv und vorhandene Cloud-Kopien bleiben erhalten. Gesicherte Archivmissionen lassen sich später über Schritt 2 neu übertragen.\n\nVollständige lokale Sicherung: '+str(dest/'before'))
  self.task('Vollständig sichern, angehakte Missionen lokal entfernen und zurücklesen …',lambda:ios.run(ios.remove_missions(r['serial'],targets,dest,fly_closed=True)),done)
 def read_device_mission(self,r,m):
  """KMZ und Titelbild einer Mission vom Gerät lesen (nur lesen)."""
  if r['kind']=='ios':return ios.run(ios.read_mission(r['serial'],m['uuid']))
  a=self.adb_for(r);return {'kmz':a.read(m['path']) if m.get('path') else None,'preview':a.read(f'{BASE}/map_preview/{m["uuid"]}/{m["uuid"]}.jpg') if m.get('preview') else None}
 def preview_sync_candidates(self):
  """Gerätemissionen mit DJI-Fly-Bild, deren KMZ identisch im Webarchiv liegt: angehakte, sonst alle sichtbaren."""
  rows=[m for m in self.rows if m['uuid'] in self.checked] if self.checked else [m for _,m in self.visible_rows()]
  out=[]
  for m in rows:
   if not m.get('image') or archive_state(m,self.archive_rows,self.archive is not None)!='saved':continue
   matches=[a for a in self.archive_rows if a.get('sha256')==m.get('sha256')]
   if matches:out.append((m,matches))
  return out
 def sync_previews_to_archive(self):
  """DJI-Fly-Titelbilder als aktive Vorschau der identischen Archivmissionen speichern; keine KMZ wird angefasst."""
  client=self.archive;candidates=self.preview_sync_candidates()
  if not client or not candidates:self.status.setText('Keine Mission mit Gerätebild und identischer Archivkopie in der Auswahl.');return
  r=self.current_device();names=[self.row_label(r,m,self.rows.index(m)) for m,_ in candidates]
  if QMessageBox.question(self,'Vorschauen ins Webarchiv',f'{len(candidates)} Titelbild(er) vom Gerät als Vorschau im Webarchiv speichern?\n\n'+'\n'.join(names[:12])+('\n…' if len(names)>12 else '')+'\n\nDie bisherigen Vorschauen bleiben im Vorschau-Editor erhalten; die KMZ-Dateien werden nicht verändert.')!=QMessageBox.Yes:return
  def work():
   saved=[];errors=[]
   for m,matches in candidates:
    for a in matches:
     try:client.save_preview(a,m['image'],m.get('name') or a.get('name'));saved.append(a['id'])
     except Exception as e:errors.append(f'{a.get("name","?")}: {e}')
   return saved,errors
  def done(result):
   saved,errors=result
   for a in self.archive_rows:
    if a['id'] in saved:a.pop('pixmap',None)
   try:self.archive_rows=client.library()
   except Exception as e:self.log_line('Bibliothek nach dem Speichern nicht neu geladen: '+str(e))
   self.render_folder_tree();self.archive_filter();self.archive_previews();self.render_device_list()
   for line in errors:self.log_line('Vorschau nicht gespeichert: '+line)
   self.status.setText(f'{len(saved)} Vorschau(en) im Webarchiv gespeichert.'+(f' {len(errors)} fehlgeschlagen, siehe Protokoll.' if errors else ''))
  self.task(f'{len(candidates)} Vorschau(en) ins Webarchiv speichern …',work,done)
 def save_to_archive(self):
  if not self.archive:self.show_settings();self.status.setText('Zuerst mit dem Webarchiv verbinden, dann die Auswahl sichern.');return
  try:r=self.selected_device()
  except Exception as e:self.error(str(e));return
  picked=[(i,m) for i,m in enumerate(self.rows) if m['uuid'] in self.checked and m.get('localState')=='local']
  if not picked:return
  folders=[('Ohne Projektordner',None)]+[(f['path']+(' (archiviert)' if f['archived'] else ''),f['id']) for f in self.archive.folders]
  choice,ok=QInputDialog.getItem(self,'Im Webarchiv sichern',f'{len(picked)} Missionen sichern. Neue Dateien werden angelegt; identische vorhandene Archiveinträge werden in diesen Zielordner verschoben. Namen und Versionen bleiben erhalten. Projektordner:',[name for name,_ in folders],0,False)
  if not ok:return
  folder=dict(folders)[choice];client=self.archive;labels={m['uuid']:self.row_label(r,m,i) for i,m in picked}
  def work():
   report={'saved':[],'moved':[],'skipped':[],'failed':[],'hashes':{}}
   for i,m in picked:
    label=labels[m['uuid']]
    try:
     data=self.read_device_mission(r,m);raw=data.get('kmz')
     if not raw:report['skipped'].append(label+' (keine lokale KMZ)');continue
     inspect_kmz(raw);report['hashes'][m['uuid']]=digest(raw);matches=client.matches_by_sha(digest(raw))
     target=next((entry for entry in matches if entry.get('folderId')==folder),None)
     if target:report['skipped'].append(f'{label} (bereits im Zielordner als „{target["name"]}“)');continue
     if len(matches)>1:raise BridgeError('Mehrere Archiveinträge mit identischer KMZ gefunden. Bitte den gewünschten Eintrag im Webarchiv zuordnen.')
     if matches:
      client.move_existing(matches[0],folder);report['moved'].append(f'{label} (vorhandener Eintrag „{matches[0]["name"]}“)');continue
     client.upload(label,label+'.kmz',raw,folder,data.get('preview'));report['saved'].append(label)
    except Exception as e:report['failed'].append(f'{label}: {e}')
   return report
  def done(report):
   for m in self.rows:
    if m['uuid'] in report.get('hashes',{}):m['sha256']=report['hashes'][m['uuid']]
   for key,title in [('saved','Gesichert'),('moved','Verschoben'),('skipped','Übersprungen'),('failed','Fehlgeschlagen')]:
    for line in report[key]:self.log_line(f'{title}: {line}')
   self.checked=set();self.archive_rows=client.missions;self.render_device_list();self.render_folder_tree();self.archive_filter();self.archive_previews()
   summary=f'{len(report["saved"])} neu gesichert, {len(report["moved"])} verschoben, {len(report["skipped"])} bereits im Zielordner, {len(report["failed"])} fehlgeschlagen.';self.status.setText('Im Webarchiv gesichert: '+summary)
   QMessageBox.information(self,'Im Webarchiv gesichert',summary+('\n\nÜbersprungen:\n'+'\n'.join(report['skipped']) if report['skipped'] else '')+('\n\nFehlgeschlagen:\n'+'\n'.join(report['failed']) if report['failed'] else '')+'\n\nEinzelheiten im Protokoll.')
  self.task(f'{len(picked)} Missionen vom Gerät lesen und im Webarchiv sichern …',work,done)
 def backup(self):
  try:r=self.selected_device();a=self.adb_for(r)
  except Exception as e:self.error(str(e));return
  if QMessageBox.question(self,'Bestand sichern','Ist kein Flug aktiv und DJI Fly vollständig geschlossen?\n\nDie Sicherung liest nur die vorhandenen Missionsdaten. Auf Android wird DJI Fly dabei beendet.')!=QMessageBox.Yes:return
  dest=self.root/'backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');dest.parent.mkdir(parents=True,exist_ok=True)
  self.task('Missionsbestand sichern und zurücklesen …',lambda:ios.run(ios.backup(r['serial'],dest)) if r['kind']=='ios' else a.snapshot(dest),lambda result:self.status.setText(f'{len(result["files"])} Dateien gesichert. Ablage über „Protokoll“ öffnen.'))

 # ---------- Webarchiv ----------
 def archive_login(self):
  url=self.archive_url.text().strip();key=self.archive_key.text();remember=self.archive_remember.isChecked();pref=self.store_preference();self.archive_auto=False
  if not key and not self.archive:self.show_settings();self.archive_key.setFocus();self.status.setText('Zugangsschlüssel in den Einstellungen eingeben, dann verbinden.');return
  def connect():
   client=self.client_factory(url);client.login(key);return client,client.library()
  def done(result):
   client,rows=result;self.archive=client;self.settings.setValue('archiveURL',url);self.archive_rows=rows
   if remember:
    try:self.archive_forget.setEnabled(self.credential_store.save(url,key,self.root,preference=pref));self.log_line(f'Zugangsschlüssel gespeichert ({self.archive_store.currentText()}).')
    except Exception as e:self.log_line('Schlüssel konnte nicht gespeichert werden: '+str(e))
   else:self.credential_store.delete(url,self.root,preference=pref);self.archive_key.clear();self.archive_forget.setEnabled(False)
   who='Eigentümer' if client.role=='owner' else 'Freigabe';self.archive_note.setText(f'Verbunden als {who} · {len(rows)} Missionen in der Bibliothek.');self.archive_status.setText(f'Webarchiv: verbunden als {who} · {len(rows)} Missionen · {url}');self.archive_connect_button.setText('Neu laden')
   self.status.setText(f'{len(rows)} Missionen aus dem Webarchiv geladen.');self.render_folder_tree();self.archive_filter();self.archive_previews();self.render_device_list();self.update_checked()
  self.task('Mit dem Webarchiv verbinden und Bibliothek laden …',connect,done)
 def store_preference(self):return self.archive_store.currentData() or 'auto'
 def archive_restore_key(self):
  url=self.archive_url.text().strip();key=None
  if url:
   for pref in [self.store_preference()]+[k for k in self.credential_store.available() if k!=self.store_preference()]:
    key=self.credential_store.load(url,self.root,preference=pref)
    if key:index=self.archive_store.findData(pref);self.archive_store.setCurrentIndex(index if index>=0 else 0);break
  if key:self.archive_key.setText(key);self.archive_remember.setChecked(True);self.archive_forget.setEnabled(True);self.archive_auto=True;self.archive_note.setText('Zugangsschlüssel aus dem Schlüsselbund geladen. Die Bibliothek wird beim Öffnen von Schritt 2 geladen.')
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
  # Eine Konfiguration wählt ein Archiv, keine Zugangsdaten: nur den zu dieser Adresse gespeicherten Schlüssel laden.
  self.archive=None;self.archive_rows=[];self.archive_auto=False;self.archive_key.clear();self.archive_remember.setChecked(False);self.archive_forget.setEnabled(False);self.archive_status.setText('Webarchiv: nicht verbunden · '+url);self.archive_connect_button.setText('Verbinden');self.render_folder_tree();self.archive_filter();self.archive_restore_key()
  hint=' Gespeicherter Schlüssel geladen. Jetzt verbinden.' if self.archive_key.text() else ' Jetzt mit dem Zugangsschlüssel verbinden; die Konfiguration enthält keinen Schlüssel.'
  self.archive_note.setText(f'Archiv-Adresse aus der Konfiguration übernommen{(" · "+data["authorName"]) if data.get("authorName") else ""}.'+hint);self.status.setText('Konfiguration geladen: '+url);self.show_settings();self.archive_key.setFocus();self.log_line('Konfiguration geladen: '+url)
 def archive_url_edited(self):
  """Adresse aus dem Einstellungsfenster normalisiert übernehmen und merken; ungültige Eingaben bleiben stehen, bis „Verbinden“ sie meldet."""
  from archive import normalize_url
  try:url=normalize_url(self.archive_url.text())
  except BridgeError:return
  if url!=self.archive_url.text():self.archive_url.setText(url)
  self.settings.setValue('archiveURL',url)
  if self.archive is None:self.archive_status.setText('Webarchiv: nicht verbunden · '+url)
 def archive_folders(self):return list(getattr(self.archive,'folders',[]) or []) if self.archive else []
 def render_folder_tree(self):
  tree=self.folder_tree;tree.blockSignals(True);tree.clear();folders=self.archive_folders();counts={}
  for m in self.archive_rows:counts[m.get('folderId')]=counts.get(m.get('folderId'),0)+1
  def item(text,key,count=None):
   node=QTreeWidgetItem([text+(f'  ({count})' if count else '')]);node.setData(0,Qt.UserRole,key);return node
  root_all=item('Alle Missionen','all',len(self.archive_rows));tree.addTopLevelItem(root_all)
  tree.addTopLevelItem(item('Ohne Projekt','none',counts.get(None,0)))
  def total(node):return counts.get(node['id'],0)+sum(total(c) for c in node['children'])
  def build(parent,nodes):
   for n in nodes:
    child=item(n['name']+(' · Archiv' if n['archived'] else ''),n['id'],total(n));parent.addChild(child);build(child,n['children']);child.setExpanded(True)
  roots=folder_tree(folders)
  for n in roots:
   top=item(n['name']+(' · Archiv' if n['archived'] else ''),n['id'],total(n));tree.addTopLevelItem(top);build(top,n['children']);top.setExpanded(True)
  tree.blockSignals(False);self.select_folder_item(self.archive_selection)
 def select_folder_item(self,key):
  tree=self.folder_tree
  def walk(node):
   for i in range(node.childCount()):
    child=node.child(i)
    if child.data(0,Qt.UserRole)==key:return child
    found=walk(child)
    if found:return found
   return None
  target=None
  for i in range(tree.topLevelItemCount()):
   top=tree.topLevelItem(i)
   if top.data(0,Qt.UserRole)==key:target=top;break
   target=walk(top)
   if target:break
  tree.blockSignals(True);tree.setCurrentItem(target or tree.topLevelItem(0));tree.blockSignals(False)
  if not target:self.archive_selection='all'
 def folder_selected(self):
  item=self.folder_tree.currentItem();key=item.data(0,Qt.UserRole) if item else 'all'
  if key!=self.archive_selection:self.archive_selection=key;self.archive_filter()
 def archive_visible(self):
  q=self.archive_search.text().strip().lower();kmz=self.archive_kmz_only.isChecked();archived=self.archive_archived.isChecked();folders=self.archive_folders()
  rows=[m for m in self.archive_rows if (not kmz or m['transferable']) and (archived or not m['archived']) and in_selected_folder(m,self.archive_selection,folders,self.include_subfolders.isChecked()) and q in f"{m['name']} {m['folder']} {m['filename']}".lower()]
  mode=self.archive_sort.currentData() or 'updated-desc'
  key={'updated-desc':(lambda m:m.get('updated') or '',True),'name-asc':(lambda m:m['name'].casefold(),False),'name-desc':(lambda m:m['name'].casefold(),True),'distance-desc':(lambda m:m.get('distance') or 0,True),'points-desc':(lambda m:m.get('waypoints') or 0,True)}[mode]
  return sorted(rows,key=key[0],reverse=key[1])
 def archive_filter(self,*args):
  rows=self.archive_visible();current=self.archive_current();self.archive_list.blockSignals(True);self.archive_list.clear();self.archive_widgets=[]
  for m in rows:
   item=QListWidgetItem();item.setSizeHint(QSize(0,THUMB.height()+18));item.setToolTip(m['filename']);item.setData(Qt.UserRole,m['id']);self.archive_list.addItem(item);widget=ArchiveRow(m,checked=m['id'] in self.archive_checked,on_toggle=self.archive_toggle);self.archive_list.setItemWidget(item,widget);self.archive_widgets.append((m,widget))
   if m.get('pixmap') is not None:widget.set_picture(m['pixmap'])
   if current and current['id']==m['id']:self.archive_list.setCurrentItem(item)
  self.archive_list.blockSignals(False)
  self.archive_list.setVisible(bool(rows));self.archive_empty.setVisible(not rows);self.archive_empty.setText('Noch nicht verbunden. Oben „Verbinden“ oder eine KMZ-Datei vom Mac wählen.' if not self.archive else 'Keine Mission passt zu Ordner, Suche und Filter.')
  titles={'all':'Alle Missionen','none':'Ohne Projekt'};folder=next((f for f in self.archive_folders() if f['id']==self.archive_selection),None)
  self.archive_title.setText(titles.get(self.archive_selection,folder['path'] if folder else 'Missionen'));self.archive_changed()
 def archive_previews(self):
  client=self.archive;pending=[m for m in self.archive_rows if m['transferable'] and 'pixmap' not in m][:200]
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
   if self.rows:self.render_device_list()  # Archivbilder als Rückfall in der Geräteliste
  self.task('Vorschaubilder laden …',fetch,done)
 def archive_current(self):
  item=self.archive_list.currentItem()
  if not item or not item.isSelected():return None
  return next((m for m in self.archive_rows if m['id']==item.data(Qt.UserRole)),None)
 def archive_toggle(self,mission_id,state):
  if state:self.archive_checked.add(mission_id)
  else:self.archive_checked.discard(mission_id)
  self.archive_changed()
 def archive_toggle_all(self,state):
  for m in self.archive_visible():
   if not m['transferable']:continue
   if state:self.archive_checked.add(m['id'])
   else:self.archive_checked.discard(m['id'])
  for m,widget in self.archive_widgets:widget.check.blockSignals(True);widget.check.setChecked(m['id'] in self.archive_checked);widget.check.blockSignals(False)
  self.archive_changed()
 def archive_picked(self):
  """Angehakte übertragbare Missionen, sonst der markierte Eintrag."""
  checked=[m for m in self.archive_rows if m['id'] in self.archive_checked and m['transferable']]
  if checked:return checked
  m=self.archive_current();return [m] if m and m['transferable'] else []
 def archive_changed(self):
  picked=self.archive_picked();m=self.archive_current();visible_ids={x['id'] for x in self.archive_visible()};hidden=len([i for i in self.archive_checked if i not in visible_ids])
  self.archive_use_button.setEnabled(bool(picked))
  if self.archive_checked:self.archive_selected.setText(f'{len(self.archive_checked)} ausgewählt'+(f' · {hidden} außerhalb von Ordner oder Filter' if hidden else ''))
  elif m:self.archive_selected.setText(f'Markiert: {m["name"]} ({m["format"]})'+('' if m['transferable'] else ' · kein DJI-KMZ, nicht übertragbar'))
  else:self.archive_selected.setText('Kein Eintrag ausgewählt.')
  visible=[x for x in self.archive_visible() if x['transferable']];count=sum(x['id'] in self.archive_checked for x in visible);state=Qt.Checked if visible and count==len(visible) else Qt.PartiallyChecked if count else Qt.Unchecked
  self.archive_select_all.blockSignals(True);self.archive_select_all.setCheckState(state);self.archive_select_all.blockSignals(False)
 def archive_use(self):
  picked=self.archive_picked()
  if not picked or not self.archive:return
  client=self.archive
  def download():
   out=[]
   for m in picked:
    folder=self.root/'archive'/safe_filename(m['id']);destination=folder/(safe_filename(m['name'])+'.kmz');path=client.download(m,destination);preview=None
    try:
     raw,content_type=client.preview(m);preview=archive_preview_file(raw,content_type,folder/'vorschau')
    except Exception as err:self.log_line(f'Archivbild für „{m["name"]}“ nicht geladen: {err}')
    out.append((m,path,preview))
   return out
  def done(results):
   for m,path,preview in results:self.add_entry(path,name=m['name'],archive_mission=m,archive_preview=preview)
   self.archive_checked=set();self.archive_filter();self.tabs.setCurrentIndex(TAB_TRANSFER);self.status.setText(f'{len(results)} Mission(en) aus dem Webarchiv übernommen. Namen prüfen, dann Vorschauen erzeugen.')
  self.task(f'{len(picked)} KMZ aus dem Webarchiv laden und prüfen …',download,done)

 # ---------- Vorschauen erzeugen (Schritt 3) ----------
 def prepare(self):
  self.invalidate()
  try:
   r=self.selected_device()
   if not self.queue:raise BridgeError('Die Warteschlange ist leer. Zuerst Missionen auswählen.')
   seen=set()
   for e in self.queue:
    if e.get('error') and not e.get('details'):raise BridgeError(f'„{e["name"]}“: {e["error"]}')
    name=e['name'].strip()
    if not name or len(name)>200:raise BridgeError(f'„{e["original"].name}“: Bitte einen Missionsnamen bis 200 Zeichen eingeben.')
    if e['mode']=='replace':
     if not e.get('target'):raise BridgeError(f'„{name}“: Ersetzen braucht ein Ziel auf dem Gerät. In Schritt 1 die Mission markieren und „Ausgewählte ersetzen“ wählen.')
     if e['target'] in seen:raise BridgeError(f'„{name}“: Das Ziel ist schon einem anderen Auftrag zugeordnet. Jeder Auftrag braucht ein eigenes Ziel.')
     seen.add(e['target']);m=self.target_row(e['target'])
     if not m or m.get('localState')!='local':raise BridgeError(f'„{name}“: Das Ziel ist nicht (mehr) lokal auf dem Gerät vorhanden. Liste in Schritt 1 neu lesen.')
  except Exception as e:self.error(str(e));return
  entries=[e for e in self.queue if e['status']!='done'];notes=[]
  def work(report):
   results=[]
   for n,e in enumerate(entries):
    report((n,len(entries)));source=e['source'];raw=source.read_bytes();details=inspect_kmz(raw);name=e['name'].strip();preview_path=self.root/'previews'/(uuid.uuid4().hex+'.jpg');chosen=e['background'];mode_used=e['previewMode']
    if e['previewMode']=='archive':chosen=e.get('archivePreview')
    if e['previewMode']=='map':
     try:chosen=map_background(details,self.root/'previews'/(uuid.uuid4().hex+'-luftbild.jpg'),self.root/'tilecache')
     except Exception as err:notes.append(f'„{name}“: Luftbild nicht verfügbar ({err}). 3D-Ansicht verwendet.');mode_used='3d';chosen=None
    preview=render_preview(preview_path,name,details,chosen)
    prepared={'device':r,'source':str(source.resolve()),'originalSource':str(e['original'].resolve()),'sourceSha256':digest(raw),'name':name,'preview':str(preview),'previewSha256':digest(preview.read_bytes()),'previewMode':mode_used,'kmz':details,'mode':'ios-replace' if e.get('target') else 'ios-new','replace':e.get('target')}
    if r['kind']!='ios':
     result=plan(self.adb_for(r),source,name,preview,e.get('target'));result['device']=r;result['originalSource']=prepared['originalSource'];result['previewMode']=mode_used;prepared=result
    results.append((e['id'],prepared,preview,details))
   return results
  def done(results):
   for entry_id,prepared,preview,details in results:
    e=next(x for x in self.queue if x['id']==entry_id);e['plan']=prepared;e['preview']=preview;e['details']=details;e['status']='prepared';e['error']=None
   for note in notes:self.log_line(note)
   self.render_queue();self.show_entry();self.render_review();self.closed.setChecked(False);self.stack.setCurrentIndex(1);self.tabs.setCurrentIndex(TAB_TRANSFER)
   self.status.setText(f'{len(results)} Vorschau(en) erzeugt. Noch nichts übertragen: prüfen, DJI Fly schließen, dann übertragen.'+(' Hinweise im Protokoll.' if notes else ''))
  self.task('Vorschauen erzeugen und Übertragung vorbereiten …',work,done,progress=lambda p:self.status.setText(f'Vorschau {p[0]+1} von {p[1]} …'))
 def render_review(self):
  self.review_list.blockSignals(True);self.review_list.clear()
  for i,e in enumerate(self.queue):
   row=QueueRow(e,i);item=QListWidgetItem();item.setSizeHint(QSize(0,max(104,row.sizeHint().height()+4)));self.review_list.addItem(item);self.review_list.setItemWidget(item,row)
  self.review_list.blockSignals(False)
  if self.queue:self.review_list.setCurrentRow(max(0,min(self.current,len(self.queue)-1)));self.review_selected(self.review_list.currentRow())
 def review_selected(self,row):
  if row<0 or row>=len(self.queue):return
  e=self.queue[row];r=self.current_device() or {};mode=e['mode']
  pixmap=QPixmap(str(e['preview'])) if e.get('preview') else QPixmap()
  self.review_image.set_source(pixmap)
  self.summary_mode.setText(('ERSETZEN' if mode=='replace' else 'NEU ANLEGEN')+f' · {row+1} von {len(self.queue)} · '+r.get('name',''));self.summary_name.setText(e['name'])
  d=e.get('details');self.summary_points.setText(f'{d["waypoints"]} Wegpunkte · {d["distance"]/1000:.2f} km' if d else '');self.summary_target.setText(('Ersetzt: '+(e.get('targetLabel') or e.get('target') or '')) if mode=='replace' else 'Neue Mission auf '+r.get('name','dem Gerät'))
  self.summary_source.setText(('Webarchiv · '+e['archiveMission']['folder']+f" · V{e['archiveMission'].get('version') or '?'}") if e.get('archiveMission') else 'Lokale Datei · '+Path(e['original']).name);self.summary_preview.setText({'3d':'3D-Ansicht','map':'Luftbild','image':'Eigenes Bild','archive':'Archivbild'}.get((e.get('plan') or {}).get('previewMode') or e['previewMode'],'3D-Ansicht'))
  ios_device=r.get('kind')=='ios'
  if ios_device:text='Neue Mission mit Name und Titelbild. Anschließend in DJI Fly öffnen und bei Bedarf synchronisieren.' if mode=='new' else 'Der Eintrag wird nach Sicherung ersetzt (am iPad noch nicht geprüft). Anschließend in DJI Fly öffnen und Speichern prüfen.'
  else:text='Der gewählte Eintrag wird nach Sicherung ersetzt. Anschließend RC Pro 2 neu starten, Mission öffnen und Speichern prüfen.' if mode=='replace' else 'Experimentell: Neue Kennung wird geprüft übertragen. Anschließend RC Pro 2 neu starten und prüfen, ob DJI Fly die Mission anzeigt.'
  self.review_note.setText(text+' DJI Fly kann ein importiertes Titelbild später durch einen eigenen Kartenausschnitt ersetzen.')

 # ---------- Übertragen (Schritt 4) ----------
 def render_run_list(self):
  self.run_list.clear()
  for i,e in enumerate(self.queue):
   row=QueueRow(e,i,checked=e['id'] in self.queue_checked,on_toggle=self.queue_toggle);item=QListWidgetItem();item.setSizeHint(QSize(0,max(104,row.sizeHint().height()+4)));self.run_list.addItem(item);self.run_list.setItemWidget(item,row)
  has=bool(self.queue);self.run_list.setVisible(has);self.run_empty.setVisible(not has)
  done=sum(1 for e in self.queue if e['status']=='done');self.run_progress.setText(f'{done} von {len(self.queue)} übertragen' if self.queue else '')
  self.retry_button.setEnabled(any(e['status']=='failed' for e in self.queue));self.resume_button.setEnabled(any(e['status'] in ('prepared','skipped') and e['plan'] for e in self.queue) and not (self.job and self.job.isRunning()));self.update_run_buttons()
 def update_run_buttons(self):
  row=self.run_list.currentRow();e=self.queue[row] if 0<=row<len(self.queue) else None
  self.run_remove_button.setEnabled(bool(self.removal_targets(e)) and not (self.job and self.job.isRunning()))
 def remove_run_selected(self):
  """Angehakte (sonst den markierten) Auftrag in Schritt 4 entfernen, ohne die Prüfung der übrigen Aufträge zu verwerfen."""
  row=self.run_list.currentRow();targets=self.removal_targets(self.queue[row] if 0<=row<len(self.queue) else None)
  if (self.job and self.job.isRunning()) or not targets:return
  removed=targets[0];count=self.remove_entries(targets)
  self.render_queue();self.render_run_list();self.show_entry()
  if self.stack.currentIndex()==1:
   if self.queue:self.render_review()
   else:self.stack.setCurrentIndex(0)
  self.apply_button.setEnabled(bool(self.queue) and self.closed.isChecked() and self.all_prepared())
  self.status.setText((f'„{removed["name"]}“ aus der Warteschlange entfernt.' if count==1 else f'{count} Aufträge aus der Warteschlange entfernt.')+('' if self.queue else ' Die Warteschlange ist leer.'))
 def request_stop(self):self.stop_requested=True;self.stop_button.setEnabled(False);self.status.setText('Wird nach dem aktuellen Auftrag angehalten …')
 def retry_failed(self):
  failed=[e for e in self.queue if e['status']=='failed']
  if not failed:return
  if QMessageBox.question(self,'Erneut prüfen',f'{len(failed)} fehlgeschlagene Aufträge werden zurückgesetzt und müssen in Schritt 3 erneut geprüft werden. Bereits erfolgreiche Missionen werden nicht erneut angelegt.')!=QMessageBox.Yes:return
  for e in failed:e['status']='ready';e['plan']=None;e['error']=None
  self.render_queue();self.render_run_list();self.stack.setCurrentIndex(0);self.tabs.setCurrentIndex(TAB_TRANSFER)
 def execute(self):
  todo=[e for e in self.queue if e['status'] in ('prepared','skipped') and e['plan']]
  if not todo:return
  if not self.closed.isChecked():self.error('Bitte bestätigen, dass DJI Fly vollständig geschlossen ist und kein Flug aktiv ist.');return
  try:
   r=self.selected_device()
   for e in todo:
    p=e['plan']
    if p['device']!=r:raise BridgeError('Gerät wurde gewechselt. Bitte Vorschauen erneut erzeugen.')
    if digest(Path(p['source']).read_bytes())!=p['sourceSha256'] or digest(Path(p['preview']).read_bytes())!=p['previewSha256']:raise BridgeError(f'„{e["name"]}“: Datei oder Vorschau wurde verändert. Bitte erneut prüfen.')
   targets=[e['plan'].get('replace') for e in todo if e['plan'].get('replace')]
   if len(targets)!=len(set(targets)):raise BridgeError('Zwei Aufträge zielen auf dieselbe Mission. Jeder Auftrag braucht ein eigenes Ziel.')
  except Exception as e:self.error(str(e));return
  self.stop_requested=False;self.stop_button.setEnabled(True);self.resume_button.setEnabled(False);self.apply_button.setEnabled(False);self.tabs.setCurrentIndex(TAB_RUN);self.render_run_list()
  def work(report):
   outcome=[]
   for n,e in enumerate(todo):
    if self.stop_requested:outcome.append((e['id'],'skipped',None,None));continue
    p=e['plan'];dest=self.root/'transfers'/(datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'-'+str(n+1));dest.parent.mkdir(parents=True,exist_ok=True);report((e['id'],'running',n,len(todo)))
    try:
     result=ios.run(ios.apply_new(r['serial'],Path(p['source']),p['name'],Path(p['preview']),dest,fly_closed=True,replace=p.get('replace'))) if r['kind']=='ios' else apply(self.adb_for(r),p,dest)
     outcome.append((e['id'],'done',result,str(dest)));report((e['id'],'done',n,len(todo)))
    except Exception as err:
     outcome.append((e['id'],'failed',str(err),str(dest)));report((e['id'],'failed',n,len(todo)))
     for rest in todo[n+1:]:outcome.append((rest['id'],'skipped',None,None))
     break
   return outcome
  def progress(update):
   entry_id,status,n,total=update;e=next(x for x in self.queue if x['id']==entry_id);e['status']=status;self.render_run_list();self.run_progress.setText(f'{n+1} von {total} · {STATUS_LABELS[status]}')
  def done(outcome):
   self.stop_button.setEnabled(False);failed=None
   for entry_id,status,result,dest in outcome:
    e=next(x for x in self.queue if x['id']==entry_id)
    if status=='done':
     e['status']='done';self.registry[r['serial']+':'+result['uuid']]=e['name'];self.log_line(f'Übertragen und zurückgelesen: {e["name"]} · {dest}')
    elif status=='failed':e['status']='failed';e['error']=result;e['plan']=None;failed=e;self.log_line(f'FEHLER bei {e["name"]}: {result} · Journal {dest}')
    else:e['status']='skipped' if e['plan'] else 'ready'
   atomic_json(self.root/'names.json',self.registry);self.render_run_list();self.render_queue()
   done_count=sum(1 for e in self.queue if e['status']=='done');self.rows=[];self.list.clear();self.list.hide();self.list_empty.show();self.list_empty.setText('Liste erneut lesen, um den neuen Stand zu sehen.')
   if failed:
    self.status.setText(f'Angehalten nach Fehler bei „{failed["name"]}“: {failed["error"]}');QMessageBox.warning(self,'Übertragung angehalten',f'„{failed["name"]}“ ist fehlgeschlagen:\n{failed["error"]}\n\nDie Übertragung wurde gestoppt. {done_count} Mission(en) sind vollständig übertragen und werden nicht erneut angelegt. Sicherung und Journal liegen im Anwendungsdatenordner.')
   elif self.stop_requested:self.status.setText(f'Angehalten. {done_count} von {len(self.queue)} übertragen; mit „Fortsetzen“ geht es weiter.')
   else:
    self.status.setText(f'{done_count} von {len(self.queue)} übertragen und zurückgelesen. Jetzt in DJI Fly öffnen und Speichern prüfen.')
    QMessageBox.information(self,'Übertragung geprüft',f'{done_count} Mission(en) übertragen und zurückgelesen.\n\n'+('Jetzt DJI Fly öffnen und Mission sowie Cloud-Synchronisation prüfen.' if r['kind']=='ios' else 'Jetzt RC Pro 2 neu starten und Missionen in DJI Fly prüfen.')+'\n\nDie Sicherungen sind über „Protokoll“ erreichbar.')
  self.task(f'{len(todo)} Mission(en) sichern, übertragen und zurücklesen …',work,done,progress=progress)

STYLE=theme.stylesheet('light')  # Rückwärtskompatibel für Skripte; die App nutzt theme.apply_theme()

def main():
 if '--diagnose' in sys.argv:
  target=Path(sys.argv[sys.argv.index('--diagnose')+1]);rows=ios.run(ios.discover());result={'iosDevices':len(rows),'paired':sum(r['state']=='device' for r in rows)}
  if rows and rows[0]['state']=='device':result['readableMissions']=len(ios.run(ios.list_missions(rows[0]['serial'],target.parent/'diagnostic-reads')))
  atomic_json(target,result);return
 app=QApplication(sys.argv);app.setOrganizationName('studiobaff');app.setApplicationName('Drone Missions Bridge');app.setApplicationDisplayName(APP_NAME);app.setStyle('Fusion');theme.apply_theme(app);theme.follow_system(app);app.setWindowIcon(app_icon());window=Window();window.show();sys.exit(app.exec())
if __name__=='__main__':main()
