"""Run on the destination OS; PyInstaller does not cross-compile Windows executables."""
from pathlib import Path
import os,subprocess,sys
root=Path(__file__).resolve().parent
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--windowed','--name','Drone Missions Bridge','--distpath',str(root.parent/'outputs'),'--workpath',str(root.parent/'work/bridge-build'),'--specpath',str(root.parent/'work/bridge-build'),'--add-data',str(root/'licenses')+os.pathsep+'licenses','--add-data',str(root/'THIRD_PARTY.md')+os.pathsep+'.','--add-data',str(root/'LICENSE')+os.pathsep+'.','--copy-metadata','pymobiledevice3','--collect-data','pymobiledevice3','--exclude-module','tkinter','--exclude-module','PySide6.QtWebEngineCore','--exclude-module','PySide6.QtWebEngineWidgets','--exclude-module','PySide6.QtQml',str(root/'desktop.py')],check=True)
