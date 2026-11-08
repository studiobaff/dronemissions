"""Run on the destination OS; PyInstaller does not cross-compile Windows executables."""
from pathlib import Path
import os,subprocess,sys
root=Path(__file__).resolve().parent
# Only QtCore, QtGui, QtWidgets and QtSvg are used. Everything else from Qt is excluded to keep the bundle small.
excluded=['tkinter','PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtWebEngineQuick','PySide6.QtWebChannel','PySide6.QtWebSockets','PySide6.QtQml','PySide6.QtQuick','PySide6.QtQuick3D','PySide6.QtQuickWidgets','PySide6.QtQuickControls2','PySide6.QtMultimedia','PySide6.QtMultimediaWidgets','PySide6.QtPdf','PySide6.QtPdfWidgets','PySide6.QtCharts','PySide6.QtDataVisualization','PySide6.QtGraphs','PySide6.Qt3DCore','PySide6.Qt3DRender','PySide6.Qt3DInput','PySide6.Qt3DLogic','PySide6.Qt3DAnimation','PySide6.Qt3DExtras','PySide6.QtDesigner','PySide6.QtUiTools','PySide6.QtHelp','PySide6.QtNetwork','PySide6.QtNetworkAuth','PySide6.QtOpenGL','PySide6.QtOpenGLWidgets','PySide6.QtPositioning','PySide6.QtLocation','PySide6.QtBluetooth','PySide6.QtNfc','PySide6.QtSensors','PySide6.QtSerialPort','PySide6.QtSerialBus','PySide6.QtSql','PySide6.QtTest','PySide6.QtXml','PySide6.QtRemoteObjects','PySide6.QtScxml','PySide6.QtStateMachine','PySide6.QtTextToSpeech','PySide6.QtSpatialAudio','PySide6.QtHttpServer','PySide6.QtDBus','PySide6.QtPrintSupport','PySide6.QtConcurrent','PySide6.QtSvgWidgets','PySide6.QtAsyncio']
command=[sys.executable,'-m','PyInstaller','--noconfirm','--windowed','--name','dronemissions-bridge','--distpath',str(root.parent/'outputs'),'--workpath',str(root.parent/'work/bridge-build'),'--specpath',str(root.parent/'work/bridge-build'),'--add-data',str(root/'licenses')+os.pathsep+'licenses','--add-data',str(root/'THIRD_PARTY.md')+os.pathsep+'.','--add-data',str(root/'LICENSE')+os.pathsep+'.','--copy-metadata','pymobiledevice3','--collect-data','pymobiledevice3']
if (root/'vendor'/'platform-tools').is_dir():command+=['--add-data',str(root/'vendor'/'platform-tools')+os.pathsep+'platform-tools']
icon=root/'assets'/('icon.ico' if sys.platform=='win32' else 'icon.icns')
if icon.is_file():command+=['--icon',str(icon),'--add-data',str(root/'assets')+os.pathsep+'assets']
for module in excluded:command+=['--exclude-module',module]
subprocess.run(command+[str(root/'desktop.py')],check=True)

# The installed bundle is ad-hoc signed after staging. Record a useful version
# in macOS crash reports instead of PyInstaller's default 0.0.0.
if sys.platform=='darwin':
 import plistlib
 info=root.parent/'outputs'/'dronemissions-bridge.app'/'Contents'/'Info.plist'
 with info.open('rb') as stream:metadata=plistlib.load(stream)
 metadata.update(CFBundleShortVersionString='0.6.1',CFBundleVersion='20261108.7',CFBundleName='dronemissions-bridge',CFBundleDisplayName='dronemissions-bridge',UIDesignRequiresCompatibility=True)
 with info.open('wb') as stream:plistlib.dump(metadata,stream)

 # PyInstaller thins and signs Mach-O inputs, so the bundled ADB is no longer
 # byte-identical to Google's universal upstream binary. Keep both hashes and
 # verify the exact shipped binary at runtime, without weakening verification.
 app=info.parents[1]
 subprocess.run(['codesign','--force','--deep','--sign','-',str(app)],check=True)
 import hashlib,json
 bundled=app/'Contents/Frameworks/platform-tools'
 provenance=bundled/'provenance.json'
 if provenance.is_file() and (bundled/'adb').is_file():
  original=json.loads((root/'vendor/platform-tools/provenance.json').read_text())
  original['sourceAdbSha256']=original['adbSha256']
  original['adbSha256']=hashlib.sha256((bundled/'adb').read_bytes()).hexdigest()
  original['packaging']='PyInstaller macOS architecture processing and ad-hoc signing'
  provenance.write_text(json.dumps(original,indent=2)+'\n')
 # Only the outer signature needs updating after the resource change. Rewriting
 # nested signatures here would invalidate the newly recorded executable hash.
 subprocess.run(['codesign','--force','--sign','-',str(app)],check=True)
 subprocess.run(['codesign','--verify','--deep','--strict',str(app)],check=True)
