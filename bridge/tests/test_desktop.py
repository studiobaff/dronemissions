"""UI checks for the transfer confirmation boundary; no real devices or writes."""
import os,sys,tempfile,time,unittest
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_core import fixture,helix_fixture
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QSettings
    from desktop import Window,TAB_TRANSFER,TAB_ARCHIVE
    from PySide6.QtWidgets import QMessageBox
    import desktop as desktop_module
    HAS_QT=True
except ImportError:
    HAS_QT=False

UID='12345678-1234-1234-1234-123456789ABC'

@unittest.skipUnless(HAS_QT,'Desktop dependencies not installed')
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Tests must never touch the user's real settings or keychain.
        cls.tmp=tempfile.TemporaryDirectory();QSettings.setDefaultFormat(QSettings.IniFormat);QSettings.setPath(QSettings.IniFormat,QSettings.UserScope,cls.tmp.name)
        cls.app=QApplication.instance() or QApplication([])
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    class FakeStore:
        def __init__(self,kind='keychain'):self.kind=kind;self.data={}
        def available(self):return [self.kind]
        def backend(self,preference='auto'):return self.kind
        def save(self,url,key,root=None,preference='auto'):self.data[url]=key;return True
        def load(self,url,root=None,preference='auto'):return self.data.get(url)
        def delete(self,url,root=None,preference='auto'):self.data.pop(url,None)
    def setUp(self):self.window=Window(autosearch=False,credential_store=self.FakeStore())  # never the real keychain
    def tearDown(self):self.window.close();self.app.processEvents()
    def select(self,kind,serial='demo'):
        self.window.device.addItem('Demo',{'kind':kind,'serial':serial,'state':'device','name':'Demo'})
        self.window.device.setCurrentIndex(self.window.device.count()-1)
    def wait_review(self):
        w=self.window;deadline=time.monotonic()+10
        while (w.job and w.job.isRunning()) or w.stack.currentIndex()!=1:
            self.app.processEvents()
            if time.monotonic()>deadline:self.fail('Review did not complete')
    def test_confirmation_is_required_and_source_edit_invalidates_it(self):
        w=self.window;self.select('ios');w.start_new();self.assertEqual(w.tabs.currentIndex(),TAB_TRANSFER);self.assertEqual(w.mode,'new')
        with tempfile.TemporaryDirectory() as t:
            source=Path(t)/'Demo.kmz';source.write_bytes(fixture());w.set_source(source);w.prepare();self.wait_review()
            self.assertFalse(w.apply_button.isEnabled());self.assertFalse(w.closed.isChecked());self.assertEqual(w.transfer['mode'],'ios-new');self.assertIsNone(w.transfer['replace'])
            w.closed.setChecked(True);self.assertTrue(w.apply_button.isEnabled())
            w.name.setText('Different mission');self.assertIsNone(w.transfer);self.assertFalse(w.apply_button.isEnabled());self.assertEqual(w.stack.currentIndex(),0)
    def test_replace_needs_a_local_selected_entry(self):
        w=self.window;self.select('ios');rows=[{'uuid':UID,'name':'Erste','waypoints':2,'localState':'cloud-or-missing','preview':False},{'uuid':UID.replace('A','B'),'name':'Zweite','waypoints':3,'localState':'local','preview':False}]
        w.show_rows(w.device.currentData(),rows)
        w.list.setCurrentRow(0);self.assertFalse(w.replace_button.isEnabled())
        w.list.setCurrentRow(1);self.assertTrue(w.replace_button.isEnabled());w.start_replace();self.assertEqual(w.mode,'replace');self.assertFalse(w.target_panel.isHidden());self.assertTrue(w.new_note.isHidden())
        with tempfile.TemporaryDirectory() as t:
            source=Path(t)/'Demo.kmz';source.write_bytes(fixture());w.set_source(source);w.prepare();self.wait_review()
            self.assertEqual(w.transfer['mode'],'ios-replace');self.assertEqual(w.transfer['replace'],UID.replace('A','B'))
    def test_device_change_clears_list_and_plan(self):
        w=self.window;self.select('android');w.show_rows(w.device.currentData(),[{'uuid':UID,'path':'/x','waypoints':2,'localState':'local','preview':False}]);w.list.setCurrentRow(0)
        w.transfer={'test':'prepared'};self.select('ios','other')
        self.assertIsNone(w.transfer);self.assertEqual(w.rows,[]);self.assertEqual(w.list.count(),0);self.assertFalse(w.replace_button.isEnabled())
    def test_new_mode_is_default_and_marks_android_as_experimental(self):
        w=self.window;self.select('android');w.set_mode('new');self.assertTrue(w.target_panel.isHidden());self.assertIn('experimentell',w.mode_note.text())
        self.select('ios','ipad');w.set_mode('new');self.assertNotIn('experimentell',w.mode_note.text())

    def test_archive_tab_loads_library_and_hands_over_a_verified_kmz(self):
        w=self.window;kmz=fixture()
        class FakeClient:
            role='owner';logins=[]
            def __init__(self,url):self.url=url
            def login(self,key):FakeClient.logins.append(key);
            def library(self):return [{'id':'m1','name':'Rundflug','folder':'Demo / Süd','archived':False,'format':'KMZ','filename':'a.kmz','sha256':'','bytes':1,'versionId':'v1','version':2,'updated':'','waypoints':2,'distance':150.0,'transferable':True},{'id':'m2','name':'Projekt','folder':'Ohne Projekt','archived':False,'format':'MPROJ','filename':'b.mproj','sha256':'','bytes':1,'versionId':'v2','version':1,'updated':'','waypoints':None,'distance':0,'transferable':False}]
            def preview(self,m):return b'<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>','image/svg+xml'
            def download(self,m,destination):destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(kmz);return destination
        w.client_factory=FakeClient;w.archive_url.setText('http://127.0.0.1/dronemissions/');w.archive_key.setText('geheim');w.archive_login()
        deadline=time.monotonic()+10
        while w.job and w.job.isRunning() or not w.archive_rows:
            self.app.processEvents()
            if time.monotonic()>deadline:self.fail('Archive login did not complete')
        self.app.processEvents();self.assertEqual(FakeClient.logins,['geheim']);self.assertEqual(w.archive_key.text(),'');self.assertEqual(w.archive_list.count(),1)
        w.archive_kmz_only.setChecked(False);self.assertEqual(w.archive_list.count(),2)
        w.archive_list.setCurrentRow(1);self.assertFalse(w.archive_use_button.isEnabled())
        w.archive_list.setCurrentRow(0);self.assertTrue(w.archive_use_button.isEnabled());self.select('ios');w.archive_use()
        deadline=time.monotonic()+10
        while (w.job and w.job.isRunning()) or w.source_path is None:
            self.app.processEvents()
            if time.monotonic()>deadline:self.fail('Download did not complete')
        self.assertEqual(w.tabs.currentIndex(),TAB_TRANSFER);self.assertEqual(w.name.text(),'Rundflug');self.assertEqual(w.source_path.read_bytes(),kmz);self.assertIn('Webarchiv',w.source_meta.text())

    def test_set_source_uses_a_cleaned_copy_for_the_helix_case(self):
        w=self.window;self.select('ios')
        with tempfile.TemporaryDirectory() as t:
            source=Path(t)/'Double Helix.kmz';raw=helix_fixture();source.write_bytes(raw);w.set_source(source)
            self.assertEqual(w.original_source,source);self.assertNotEqual(w.source_path,source);self.assertEqual(w.source_path.name,'Double Helix (bereinigt).kmz');self.assertEqual(source.read_bytes(),raw)
            self.assertIn('Übertragungskopie',w.source_meta.text());self.assertEqual(w.name.text(),'Double Helix')
            w.prepare();self.wait_review();self.assertEqual(Path(w.transfer['source']),w.source_path.resolve());self.assertEqual(Path(w.transfer['originalSource']),source.resolve());self.assertEqual(w.transfer['kmz']['waypoints'],3)

    def test_config_import_sets_archive_url_and_rejects_keys(self):
        w=self.window
        with tempfile.TemporaryDirectory() as t:
            good=Path(t)/'c.json';good.write_text('{"format":"dronemissions-bridge-config/1","archiveURL":"https://example.com/dronemissions/index.php","authorName":"Demo"}')
            w.archive_import_config(str(good));self.assertEqual(w.archive_url.text(),'https://example.com/dronemissions/');self.assertIn('Demo',w.archive_note.text())
            bad=Path(t)/'bad.json';bad.write_text('{"format":"dronemissions-bridge-config/1","archiveURL":"https://example.com/","password":"x"}')
            from unittest.mock import patch
            with patch('desktop.QMessageBox.warning'):w.archive_import_config(str(bad))
            self.assertEqual(w.archive_url.text(),'https://example.com/dronemissions/')

    def test_remembered_key_is_stored_in_the_credential_store_and_logs_in_automatically(self):
        w=self.window;store=w.credential_store;logins=[]
        class FakeClient:
            role='owner'
            def __init__(self,url):self.url=url
            def login(self,key):logins.append((self.url,key))
            def library(self):return []
            def preview(self,m):return b'',''
        w.client_factory=FakeClient;w.archive_url.setText('https://example.com/dronemissions/');w.archive_key.setText('geheim');w.archive_remember.setChecked(True);w.archive_login()
        deadline=time.monotonic()+10
        while w.job and w.job.isRunning() or w.archive is None:
            self.app.processEvents()
            if time.monotonic()>deadline:self.fail('login did not complete')
        self.app.processEvents();self.assertEqual(store.data,{'https://example.com/dronemissions/':'geheim'});self.assertTrue(w.archive_forget.isEnabled())
        w.archive_forget_key();self.assertEqual(store.data,{});self.assertEqual(w.archive_key.text(),'')
        # A stored key is restored on start and used when the tab opens.
        store.data['https://example.com/dronemissions/']='geheim';w2=Window(autosearch=False,credential_store=store,client_factory=FakeClient);w2.archive_url.setText('https://example.com/dronemissions/');w2.archive_restore_key()
        self.assertEqual(w2.archive_key.text(),'geheim');self.assertTrue(w2.archive_auto);w2.tabs.setCurrentIndex(TAB_ARCHIVE)
        deadline=time.monotonic()+10
        while w2.job and w2.job.isRunning() or w2.archive is None:
            self.app.processEvents()
            if time.monotonic()>deadline:self.fail('auto login did not complete')
        self.assertEqual(logins[-1],('https://example.com/dronemissions/','geheim'));w2.close()
    def test_loopback_archive_url_from_tests_is_not_restored(self):
        QSettings('studiobaff','DroneMissionsBridge').setValue('archiveURL','http://127.0.0.1/dronemissions/')
        w=Window(autosearch=False,credential_store=self.FakeStore());self.assertTrue(w.archive_url.text().startswith('https://'));w.close()

    def test_search_multiselect_and_save_to_archive(self):
        from unittest.mock import patch
        w=self.window;self.select('ios');kmz=fixture();uploads=[]
        class FakeClient:
            role='owner';folders=[{'id':'f1','path':'Demo','archived':False}];missions=[]
            def __init__(self,url):pass
            def login(self,key):pass
            def library(self):return []
            def find_by_sha(self,sha):return {'name':'Schon da'} if sha=='dup' else None
            def upload(self,name,filename,raw,folder=None,preview=None):uploads.append((name,filename,raw,folder,preview));return {'id':'x'}
            def preview(self,m):return b'',''
        w.archive=FakeClient('');rows=[{'uuid':UID,'name':'Alpha','waypoints':2,'localState':'local','preview':True},{'uuid':UID.replace('A','B'),'name':'Beta','waypoints':2,'localState':'cloud-or-missing','preview':False},{'uuid':UID.replace('A','C'),'name':'Gamma','waypoints':2,'localState':'local','preview':False}]
        w.show_rows(w.device.currentData(),rows);self.assertEqual(w.list.count(),3)
        w.device_search.setText('alp');self.assertEqual(w.list.count(),1);w.select_all.setChecked(True);self.assertEqual(w.checked,{UID});w.device_search.setText('')
        self.assertEqual(w.list.count(),3);w.device_rows_widgets[2][1].check.setChecked(True);self.assertEqual(w.checked,{UID,UID.replace('A','C')});self.assertTrue(w.save_web_button.isEnabled())
        w.read_device_mission=lambda r,m:{'kmz':kmz,'preview':b'\xff\xd8img'}
        with patch('desktop.QInputDialog.getItem',return_value=('Demo',True)),patch('desktop.QMessageBox.information'):
            w.save_to_archive()
            deadline=time.monotonic()+10
            while w.job and w.job.isRunning():
                self.app.processEvents()
                if time.monotonic()>deadline:self.fail('save did not complete')
            self.app.processEvents()
        self.assertEqual([(u[0],u[1],u[3]) for u in uploads],[('Alpha','Alpha.kmz','f1'),('Gamma','Gamma.kmz','f1')]);self.assertEqual(uploads[0][2],kmz);self.assertEqual(uploads[0][4],b'\xff\xd8img');self.assertEqual(w.checked,set())
    def test_rename_on_ipad_uses_the_database_transaction(self):
        from unittest.mock import patch
        w=self.window;self.select('ios');calls=[]
        w.show_rows(w.device.currentData(),[{'uuid':UID,'name':'Alt','waypoints':2,'localState':'local','preview':False}]);w.list.setCurrentRow(0);self.assertTrue(w.rename_button.isEnabled())
        async def fake_rename(serial,uid,name,work,*,fly_closed):calls.append((serial,uid,name,fly_closed));return {'status':'db-verified'}
        with patch('desktop.QInputDialog.getText',return_value=('Neu',True)),patch('desktop.QMessageBox.question',return_value=QMessageBox.Yes),patch.object(desktop_module.ios,'rename_mission',fake_rename):
            w.rename_selected()
            deadline=time.monotonic()+10
            while w.job and w.job.isRunning():
                self.app.processEvents()
                if time.monotonic()>deadline:self.fail('rename did not complete')
            self.app.processEvents()
        self.assertEqual(calls,[('demo',UID,'Neu',True)]);self.assertEqual(w.rows[0]['name'],'Neu');self.assertEqual(w.registry['demo:'+UID],'Neu')

    def test_menu_offers_main_functions_with_shortcuts(self):
        w=self.window;titles=[m.title() for m in w.menuBar().findChildren(type(w.menuBar().addMenu('x')))]
        self.assertTrue({'Datei','Gerät','Webarchiv','Übertragen','Ansicht','Hilfe'}<=set(titles))
        self.assertEqual(w.menu_actions['KMZ auswählen …'].shortcut().toString(),'Ctrl+O');self.assertEqual(w.menu_actions['Im Webarchiv sichern …'].shortcut().toString(),'Ctrl+S')
        w.menu_actions['Übertragen'].trigger();self.assertEqual(w.tabs.currentIndex(),TAB_TRANSFER);w.menu_actions['Modus: Ersetzen'].trigger();self.assertEqual(w.mode,'replace')

if __name__=='__main__':unittest.main()
