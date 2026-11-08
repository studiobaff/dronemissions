"""Warteschlange, Ordnerbaum und Mehrfachauswahl der Bridge 0.5 mit synthetischen Daten; keine Geräte, kein Netz, keine echten Einstellungen."""
import os,sys,tempfile,time,unittest
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_core import fixture
import test_desktop
from test_desktop import HAS_QT,UID
if HAS_QT:
    from unittest.mock import patch
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox
    from desktop import TAB_TRANSFER,TAB_ARCHIVE,TAB_RUN,TAB_DEVICE
    import desktop as desktop_module

KMZ=fixture() if HAS_QT else b''
FOLDERS=[{'id':'f1','name':'Demo','parent':None,'path':'Demo','archived':False},{'id':'f2','name':'Süd','parent':'f1','path':'Demo / Süd','archived':False},{'id':'f3','name':'Alt','parent':None,'path':'Alt','archived':True}]
def mission(id,name,folder,path,updated,fmt='KMZ',archived=False):
    return {'id':id,'revision':1,'folderId':folder,'name':name,'folder':path,'archived':archived,'format':fmt,'filename':name+('.kmz' if fmt=='KMZ' else '.mproj'),'sha256':'','bytes':1,'versionId':'v','version':1,'updated':updated,'waypoints':2,'distance':150.0,'transferable':fmt=='KMZ'}
MISSIONS=[mission('m1','Rundflug','f2','Demo / Süd','2026-11-07T10:00:00+00:00'),mission('m2','Seeufer','f1','Demo','2026-11-06T10:00:00+00:00'),mission('m3','Hof',None,'Ohne Projekt','2026-11-08T10:00:00+00:00'),mission('m4','Projekt','f1','Demo','2026-11-01T10:00:00+00:00',fmt='MPROJ'),mission('m5','Archiviert','f3','Alt','2026-10-01T10:00:00+00:00',archived=True)]

class FakeClient:
    role='owner'
    def __init__(self,url):self.url=url;self.folders=[dict(f) for f in FOLDERS];self.missions=[]
    def login(self,key):pass
    def library(self):self.missions=[dict(m) for m in MISSIONS];return self.missions
    def preview(self,m):return b'<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>','image/svg+xml'
    def download(self,m,destination):destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(KMZ);return destination

@unittest.skipUnless(HAS_QT,'Desktop dependencies not installed')
class QueueTests(test_desktop.DesktopCase):
    def wait(self,condition,label):
        w=self.window;deadline=time.monotonic()+10
        while (w.job and w.job.isRunning()) or not condition():
            self.app.processEvents()
            if time.monotonic()>deadline:self.fail(label+' did not complete')
        self.app.processEvents()
    def connect_archive(self):
        w=self.window;w.client_factory=FakeClient;w.archive_url.setText('https://archive.test/dronemissions/');w.archive_key.setText('geheim');w.archive_login();self.wait(lambda:bool(w.archive_rows),'login')
    def pick_folder(self,key):
        w=self.window;w.select_folder_item(key);w.folder_selected()
    def visible_names(self):
        w=self.window;return [w.archive_list.item(i).toolTip().rsplit('.',1)[0] for i in range(w.archive_list.count())]
    def tree_texts(self):
        w=self.window;out=[]
        def walk(node,depth):
            out.append(('  '*depth)+node.text(0))
            for i in range(node.childCount()):walk(node.child(i),depth+1)
        for i in range(w.folder_tree.topLevelItemCount()):walk(w.folder_tree.topLevelItem(i),0)
        return out
    def add_local(self,folder,*names):
        w=self.window;paths=[]
        for n in names:
            path=Path(folder)/(n+'.kmz');path.write_bytes(KMZ);w.add_entry(path);paths.append(path)
        return paths
    def fake_ios(self,behaviour):
        """behaviour(call_index, plan_dict) -> uuid or raises. apply_new liefert statt einer Coroutine ein Dict, run wertet es aus."""
        calls=[]
        def apply_new(serial,source,name,preview,dest,fly_closed,replace=None):return {'serial':serial,'source':Path(source),'name':name,'preview':Path(preview),'dest':Path(dest),'fly_closed':fly_closed,'replace':replace}
        def run(job):
            calls.append(job);result=behaviour(len(calls),job)
            return {'uuid':result,'status':'verified'}
        a=patch.object(desktop_module.ios,'apply_new',apply_new);b=patch.object(desktop_module.ios,'run',run);a.start();b.start();self.addCleanup(a.stop);self.addCleanup(b.stop);return calls

    # ----- Ordnerbaum und Filter -----
    def test_folder_tree_mirrors_the_archive_and_filters_with_and_without_subfolders(self):
        w=self.window;self.connect_archive()
        self.assertEqual(self.tree_texts(),['Alle Missionen  (5)','Ohne Projekt  (1)','Alt · Archiv  (1)','Demo  (3)','  Süd  (1)'])
        self.assertEqual(w.archive_title.text(),'Alle Missionen');self.assertEqual(self.visible_names(),['Hof','Rundflug','Seeufer'])  # nur KMZ, nicht archiviert, neueste zuerst
        self.pick_folder('f1');self.assertEqual(w.archive_title.text(),'Demo');self.assertEqual(self.visible_names(),['Rundflug','Seeufer'])
        w.include_subfolders.setChecked(False);self.assertEqual(self.visible_names(),['Seeufer'])
        w.include_subfolders.setChecked(True);self.pick_folder('f2');self.assertEqual(self.visible_names(),['Rundflug'])
        self.pick_folder('none');self.assertEqual(w.archive_title.text(),'Ohne Projekt');self.assertEqual(self.visible_names(),['Hof'])
        self.pick_folder('f3');self.assertEqual(self.visible_names(),[]);self.assertFalse(w.archive_empty.isHidden());w.archive_archived.setChecked(True);self.assertEqual(self.visible_names(),['Archiviert'])
        self.pick_folder('all');w.archive_kmz_only.setChecked(False);self.assertEqual(self.visible_names(),['Hof','Rundflug','Seeufer','Projekt','Archiviert'])
        w.archive_search.setText('see');self.assertEqual(self.visible_names(),['Seeufer']);w.archive_search.setText('')
        w.archive_sort.setCurrentIndex(w.archive_sort.findData('name-asc'));self.assertEqual(self.visible_names(),['Archiviert','Hof','Projekt','Rundflug','Seeufer'])
    def test_multiselect_counts_hidden_items_and_hands_over_only_kmz_in_order(self):
        w=self.window;self.connect_archive();self.select('ios');w.archive_kmz_only.setChecked(False)
        rows=dict(w.archive_widgets and [(m['id'],widget) for m,widget in w.archive_widgets])
        self.assertFalse(rows['m4'].check.isEnabled())  # MPROJ hat keine aktive Checkbox
        rows['m1'].check.setChecked(True);rows['m3'].check.setChecked(True);self.assertEqual(w.archive_checked,{'m1','m3'});self.assertEqual(w.archive_selected.text(),'2 ausgewählt')
        self.pick_folder('f1');self.assertEqual(w.archive_selected.text(),'2 ausgewählt · 1 außerhalb von Ordner oder Filter');self.assertTrue(w.archive_use_button.isEnabled())
        w.archive_select_all.click();self.assertEqual(w.archive_checked,{'m1','m2','m3'});self.assertEqual(w.archive_select_all.checkState(),Qt.Checked)
        self.pick_folder('all');self.assertEqual(w.archive_select_all.checkState(),Qt.Checked);rows=dict([(m['id'],widget) for m,widget in w.archive_widgets]);rows['m2'].check.setChecked(False);self.assertEqual(w.archive_select_all.checkState(),Qt.PartiallyChecked)
        w.archive_use();self.wait(lambda:len(w.queue)==2,'download')
        self.assertEqual(w.tabs.currentIndex(),TAB_TRANSFER);self.assertEqual([e['name'] for e in w.queue],['Rundflug','Hof']);self.assertEqual(w.archive_checked,set());self.assertEqual(w.queue_count.text(),'2 Mission(en)')
        self.assertTrue(all(e['archiveMission'] for e in w.queue));self.assertEqual(w.queue[0]['source'].read_bytes(),KMZ);self.assertIn('Webarchiv',w.queue[0]['note'])
        # Archivbild: Vorschau aus dem Webarchiv wird gerastert, als Listenbild genutzt und ist Standard-Titelbild
        self.assertTrue(all(e['archivePreview'] and Path(e['archivePreview']).is_file() for e in w.queue));self.assertEqual([e['previewMode'] for e in w.queue],['archive','archive']);self.assertTrue(w.queue[0]['preview'] and Path(w.queue[0]['preview']).is_file())
        self.assertFalse(w.preview_archive.isHidden());self.assertTrue(w.preview_archive.isChecked());w.prepare();self.wait_review();self.assertEqual([e['plan']['previewMode'] for e in w.queue],['archive','archive']);self.assertEqual(w.summary_preview.text(),'Archivbild')
        with tempfile.TemporaryDirectory() as t:
            self.add_local(t,'Lokal');self.assertEqual(w.queue[2]['previewMode'],'3d');self.assertTrue(w.preview_archive.isHidden());w.set_preview_mode('archive');self.assertEqual(w.preview_mode,'3d')
    def test_local_kmz_can_be_queued_without_archive_login(self):
        w=self.window;self.assertIsNone(w.archive)
        with tempfile.TemporaryDirectory() as t:
            paths=self.add_local(t,'Eins','Zwei');self.assertEqual([e['name'] for e in w.queue],['Eins','Zwei']);self.assertEqual(w.current,1);self.assertEqual(w.name.text(),'Zwei')
            w.queue_list.setCurrentRow(0);w.queue_selected(0);self.assertEqual(w.name.text(),'Eins');w.remove_current();self.assertEqual([e['name'] for e in w.queue],['Zwei'])
            with patch('desktop.QFileDialog.getOpenFileNames',return_value=([str(paths[0])],'')):w.choose_kmz()
            self.assertEqual([e['name'] for e in w.queue],['Zwei','Eins']);self.assertEqual(w.tabs.currentIndex(),TAB_TRANSFER);w.clear_queue();self.assertEqual(w.queue,[]);self.assertFalse(w.tabs.isTabEnabled(TAB_RUN))

    # ----- Vorbereiten -----
    def test_prepare_requires_unique_local_replace_targets(self):
        w=self.window;self.select('ios');rows=[{'uuid':UID,'name':'Erste','waypoints':2,'localState':'local','preview':False},{'uuid':UID.replace('A','B'),'name':'Zweite','waypoints':3,'localState':'local','preview':False},{'uuid':UID.replace('A','C'),'name':'Cloud','waypoints':3,'localState':'cloud-or-missing','preview':False}]
        w.show_rows(w.device.currentData(),rows)
        with tempfile.TemporaryDirectory() as t,patch('desktop.QMessageBox.warning') as warning:
            self.add_local(t,'A','B');w.queue_list.setCurrentRow(0);w.queue_selected(0);w.set_mode('replace')
            w.prepare();self.assertEqual(w.stack.currentIndex(),0);self.assertIn('braucht ein Ziel',warning.call_args[0][2])
            w.list.setCurrentRow(0);w.start_replace();self.assertEqual(w.queue[0]['target'],UID);self.assertEqual(w.tabs.currentIndex(),TAB_TRANSFER)
            w.queue_list.setCurrentRow(1);w.queue_selected(1);w.set_mode('replace');w.list.setCurrentRow(0);w.start_replace();self.assertIsNone(w.queue[1]['target']);self.assertIn('bereits Ziel',w.status.text())
            w.list.setCurrentRow(2);w.start_replace();self.assertIsNone(w.queue[1]['target']);self.assertIn('lokal vorhandene',w.status.text())
            w.list.setCurrentRow(1);w.start_replace();self.assertEqual(w.queue[1]['target'],UID.replace('A','B'))
            w.queue[1]['target']=UID;w.prepare();self.assertIn('eigenes Ziel',warning.call_args[0][2]);w.queue[1]['target']=UID.replace('A','B')
            w.prepare();self.wait_review();self.assertEqual([e['plan']['mode'] for e in w.queue],['ios-replace','ios-replace']);self.assertEqual([e['plan']['replace'] for e in w.queue],[UID,UID.replace('A','B')]);self.assertEqual(w.queue_count.text(),'2 Mission(en) · 2 geprüft')
            self.assertEqual(w.summary_mode.text().split(' · ')[0],'ERSETZEN');self.assertIn('Ersetzt: Zweite',w.summary_target.text())
    def test_device_change_drops_targets_and_plans(self):
        w=self.window;self.select('ios');w.show_rows(w.device.currentData(),[{'uuid':UID,'name':'Erste','waypoints':2,'localState':'local','preview':False}])
        with tempfile.TemporaryDirectory() as t:
            self.add_local(t,'A');w.set_mode('replace');w.list.setCurrentRow(0);w.start_replace();w.prepare();self.wait_review();w.closed.setChecked(True);self.assertTrue(w.apply_button.isEnabled())
            from core import digest
            fake_plan=lambda adb,source,name,preview,target=None:{'mode':'android-new','source':str(Path(source).resolve()),'sourceSha256':digest(Path(source).read_bytes()),'preview':str(preview),'previewSha256':digest(Path(preview).read_bytes()),'name':name,'replace':target,'kmz':w.queue[0]['details']}
            plan_guard=patch('desktop.plan',fake_plan);plan_guard.start();self.addCleanup(plan_guard.stop)
            self.select('android','rc2');self.assertIsNone(w.queue[0]['target']);self.assertIsNone(w.queue[0]['plan']);self.assertEqual(w.queue[0]['status'],'ready');self.assertEqual(w.stack.currentIndex(),0);self.assertFalse(w.apply_button.isEnabled());self.assertEqual(w.rows,[])
            w.set_mode('new');w.prepare();self.wait_review();self.assertEqual(w.queue[0]['plan']['device']['serial'],'rc2')
            w.device.setCurrentIndex(0);self.assertIsNone(w.queue[0]['plan'])

    # ----- Übertragen -----
    def test_execute_runs_serially_stops_on_error_and_resume_skips_successful_entries(self):
        w=self.window;self.select('ios')
        with tempfile.TemporaryDirectory() as t,patch('desktop.QMessageBox.warning'),patch('desktop.QMessageBox.information'):
            self.add_local(t,'A','B','C');w.prepare();self.wait_review()
            w.execute();self.assertFalse(any(e['status']=='done' for e in w.queue))  # ohne Bestätigung passiert nichts
            w.closed.setChecked(True)
            def behaviour(n,job):
                if n==2:raise RuntimeError('Gerät hat die Datei abgelehnt')
                return 'uuid-'+job['name']
            calls=self.fake_ios(behaviour);w.execute();self.wait(lambda:not (w.job and w.job.isRunning()),'execute')
            self.assertEqual(w.tabs.currentIndex(),TAB_RUN);self.assertEqual([e['status'] for e in w.queue],['done','failed','skipped']);self.assertEqual([c['name'] for c in calls],['A','B'])
            self.assertTrue(all(c['fly_closed'] for c in calls));self.assertEqual(w.run_progress.text(),'1 von 3 übertragen');self.assertIn('Angehalten nach Fehler bei „B“',w.status.text())
            self.assertEqual(w.registry['demo:uuid-A'],'A');self.assertTrue((Path(self.root.name)/'names.json').exists());self.assertTrue(w.retry_button.isEnabled());self.assertTrue(w.resume_button.isEnabled())
            # Fortsetzen überträgt nur den nicht gestarteten Auftrag, der fehlgeschlagene braucht eine neue Prüfung.
            w.execute();self.wait(lambda:not (w.job and w.job.isRunning()),'resume')
            self.assertEqual([c['name'] for c in calls],['A','B','C']);self.assertEqual([e['status'] for e in w.queue],['done','failed','done']);self.assertFalse(w.resume_button.isEnabled())
            with patch('desktop.QMessageBox.question',return_value=QMessageBox.Yes):w.retry_failed()
            self.assertEqual([e['status'] for e in w.queue],['done','ready','done']);self.assertEqual(w.tabs.currentIndex(),TAB_TRANSFER)
            w.prepare();self.wait_review();self.assertEqual([e['status'] for e in w.queue],['done','prepared','done']);w.closed.setChecked(True);w.execute();self.wait(lambda:not (w.job and w.job.isRunning()),'retry')
            self.assertEqual([c['name'] for c in calls],['A','B','C','B']);self.assertEqual([e['status'] for e in w.queue],['done','done','done']);self.assertEqual(w.run_progress.text(),'3 von 3 übertragen')
    def test_stop_request_halts_after_the_current_job_and_resume_continues(self):
        w=self.window;self.select('ios')
        with tempfile.TemporaryDirectory() as t,patch('desktop.QMessageBox.information'):
            self.add_local(t,'A','B','C');w.prepare();self.wait_review();w.closed.setChecked(True)
            def behaviour(n,job):
                if n==1:w.stop_requested=True
                return 'uuid-'+job['name']
            calls=self.fake_ios(behaviour);w.execute();self.wait(lambda:not (w.job and w.job.isRunning()),'execute')
            self.assertEqual([c['name'] for c in calls],['A']);self.assertEqual([e['status'] for e in w.queue],['done','skipped','skipped']);self.assertIn('Angehalten. 1 von 3',w.status.text());self.assertTrue(w.resume_button.isEnabled())
            w.execute();self.wait(lambda:not (w.job and w.job.isRunning()),'resume');self.assertEqual([c['name'] for c in calls],['A','B','C']);self.assertEqual([e['status'] for e in w.queue],['done','done','done'])
    def test_changed_device_or_edited_file_blocks_the_transfer(self):
        w=self.window;self.select('ios')
        with tempfile.TemporaryDirectory() as t,patch('desktop.QMessageBox.warning') as warning:
            path=self.add_local(t,'A')[0];w.prepare();self.wait_review();w.closed.setChecked(True)
            w.queue[0]['plan']['device']={**w.queue[0]['plan']['device'],'serial':'other'};calls=self.fake_ios(lambda n,job:'x');w.execute();self.assertEqual(calls,[]);self.assertIn('Gerät wurde gewechselt',warning.call_args[0][2])
            w.queue[0]['plan']['device']['serial']='demo';Path(w.queue[0]['plan']['source']).write_bytes(KMZ+b' ');w.execute();self.assertEqual(calls,[]);self.assertIn('verändert',warning.call_args[0][2]);self.assertEqual(w.queue[0]['status'],'prepared')

    # ----- Einstellungen -----
    def test_connection_settings_live_in_the_settings_window_not_in_the_archive_step(self):
        w=self.window
        for widget in (w.archive_url,w.archive_key,w.archive_remember,w.archive_store,w.archive_forget,w.adb):self.assertIs(widget.window(),w.settings_dialog)
        self.assertIs(w.archive_status.window(),w);self.assertIs(w.archive_connect_button.window(),w);self.assertFalse(w.settings_dialog.isVisible())
        w.archive_key.clear();w.archive_connect_button.click();self.assertTrue(w.settings_dialog.isVisible());self.assertIn('nicht verbunden',w.archive_status.text())  # ohne Schlüssel öffnet „Verbinden“ die Einstellungen
        w.settings_dialog.close()
        with tempfile.TemporaryDirectory() as t:
            self.add_local(t,'A');w.preview_map.click();self.assertEqual(w.settings.value('previewMode'),'map');self.assertEqual(w.queue[0]['previewMode'],'map');w.preview_3d.click();self.assertEqual(w.settings.value('previewMode'),'3d')
    def test_settings_window_opens_from_the_archive_step_and_persists_the_url(self):
        w=self.window;link=next(b for b in w.tabs.widget(TAB_ARCHIVE).findChildren(type(w.archive_connect_button)) if b.text()=='Einstellungen …');link.click();self.assertTrue(w.settings_dialog.isVisible())
        w.archive_url.setText('https://archive.test/dronemissions/index.php');w.archive_url.editingFinished.emit();self.assertEqual(w.settings.value('archiveURL'),'https://archive.test/dronemissions/')
        w.settings_dialog.close()

if __name__=='__main__':unittest.main()

@unittest.skipUnless(HAS_QT,'Desktop dependencies not installed')
class DeviceListTests(QueueTests.__bases__[0]):
    def test_run_tab_removes_an_entry_without_dropping_other_plans(self):
        w=self.window;self.select('ios')
        with tempfile.TemporaryDirectory() as t,patch('desktop.QMessageBox.information'):
            for n in ('A','B','C'):
                path=Path(t)/(n+'.kmz');path.write_bytes(KMZ);w.add_entry(path)
            w.prepare();QueueTests.wait_review(self);w.tabs.setCurrentIndex(TAB_RUN);self.assertFalse(w.run_remove_button.isEnabled())
            w.run_list.setCurrentRow(1);self.assertTrue(w.run_remove_button.isEnabled());w.remove_run_selected()
            self.assertEqual([e['name'] for e in w.queue],['A','C']);self.assertEqual([e['status'] for e in w.queue],['prepared','prepared']);self.assertEqual(w.stack.currentIndex(),1);self.assertEqual(w.review_list.count(),2)
            w.closed.setChecked(True);self.assertTrue(w.apply_button.isEnabled())
            calls=[]
            def apply_new(serial,source,name,preview,dest,fly_closed,replace=None):return {'name':name}
            def run(job):calls.append(job['name']);return {'uuid':'u-'+job['name'],'status':'verified'}
            with patch.object(desktop_module.ios,'apply_new',apply_new),patch.object(desktop_module.ios,'run',run):
                w.execute();QueueTests.wait(self,lambda:not (w.job and w.job.isRunning()),'execute')
            self.assertEqual(calls,['A','C']);w.run_list.setCurrentRow(0);w.remove_run_selected();self.assertEqual([e['name'] for e in w.queue],['C'])
    def test_checkboxes_remove_several_entries_at_once(self):
        w=self.window;self.select('ios')
        with tempfile.TemporaryDirectory() as t:
            for n in ('A','B','C','D'):
                path=Path(t)/(n+'.kmz');path.write_bytes(KMZ);w.add_entry(path)
            w.tabs.setCurrentIndex(TAB_RUN);rows=[w.run_list.itemWidget(w.run_list.item(i)) for i in range(w.run_list.count())]
            rows[0].check.setChecked(True);rows[2].check.setChecked(True);self.assertEqual(len(w.queue_checked),2);self.assertTrue(w.run_remove_button.isEnabled())
            w.remove_run_selected();self.assertEqual([e['name'] for e in w.queue],['B','D']);self.assertEqual(w.queue_checked,set());self.assertIn('2 Aufträge',w.status.text())
            w.tabs.setCurrentIndex(TAB_TRANSFER);rows=[w.queue_list.itemWidget(w.queue_list.item(i)) for i in range(w.queue_list.count())];rows[1].check.setChecked(True);w.remove_current();self.assertEqual([e['name'] for e in w.queue],['B'])
            w.remove_current();self.assertEqual(w.queue,[])  # ohne Haken: aktueller Auftrag
    def test_rename_is_available_for_a_single_checked_mission(self):
        w=self.window;self.select('ios');w.show_rows(w.device.currentData(),[{'uuid':UID,'name':'Eins','waypoints':2,'localState':'local','preview':False},{'uuid':UID.replace('A','B'),'name':'Zwei','waypoints':2,'localState':'local','preview':False}])
        w.list.clearSelection();w.list.setCurrentRow(-1);self.assertFalse(w.rename_button.isEnabled())
        w.device_rows_widgets[1][1].check.setChecked(True);self.assertTrue(w.rename_button.isEnabled());self.assertEqual(w.rename_target()['name'],'Zwei')
        w.device_rows_widgets[0][1].check.setChecked(True);self.assertFalse(w.rename_button.isEnabled());self.assertIsNone(w.rename_target())
    def test_device_rows_fall_back_to_the_archive_picture_and_sync_previews_to_the_archive(self):
        from core import digest
        from PySide6.QtGui import QPixmap
        w=self.window;self.select('ios');sha=digest(KMZ);saved=[];reloaded=[]
        class FakeClient:
            role='owner';folders=[]
            def __init__(self,url=''):self.missions=[]
            def login(self,key):pass
            def library(self):reloaded.append(1);self.missions=[mission('m1','Rundflug','f1','Demo','2026-11-07T10:00:00+00:00')|{'sha256':sha,'revision':2}];return self.missions
            def preview(self,m):return b'<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>','image/svg+xml'
            def save_preview(self,m,image,title=None):saved.append((m['id'],image,title));return {'ok':True,'revision':3}
        w.archive=FakeClient();w.archive_rows=w.archive.library();pix=QPixmap(4,4);pix.fill(Qt.red);w.archive_rows[0]['pixmap']=pix
        rows=[{'uuid':UID,'name':'Ohne Bild','waypoints':2,'localState':'local','preview':False,'sha256':sha},{'uuid':UID.replace('A','B'),'name':'Mit Bild','waypoints':2,'localState':'local','preview':True,'sha256':sha,'image':b'\xff\xd8bild'},{'uuid':UID.replace('A','C'),'name':'Fremd','waypoints':2,'localState':'local','preview':True,'sha256':'andere','image':b'\xff\xd8x'}]
        w.show_rows(w.device.currentData(),rows)
        pictures=[widget.findChildren(type(w.brand))[0] for m,widget in w.device_rows_widgets]
        self.assertIn('Webarchiv',pictures[0].toolTip());self.assertEqual(pictures[1].toolTip(),'');self.assertEqual(pictures[2].toolTip(),'')
        self.assertEqual([m['name'] for m,_ in w.preview_sync_candidates()],['Mit Bild']);self.assertTrue(w.sync_preview_button.isEnabled())
        with patch('desktop.QMessageBox.question',return_value=QMessageBox.Yes):
            w.sync_previews_to_archive();QueueTests.wait(self,lambda:not (w.job and w.job.isRunning()),'sync')
        self.assertEqual(saved,[('m1',b'\xff\xd8bild','Mit Bild')]);self.assertGreaterEqual(len(reloaded),2);self.assertIn('1 Vorschau(en)',w.status.text())
        w.archive=None;w.update_checked();self.assertFalse(w.sync_preview_button.isEnabled())
