"""UI checks for the transfer confirmation boundary; no real devices or writes."""
import os,sys,tempfile,time,unittest
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_core import fixture
try:
    from PySide6.QtWidgets import QApplication
    from desktop import Window
    HAS_QT=True
except ImportError:
    HAS_QT=False

UID='12345678-1234-1234-1234-123456789ABC'

@unittest.skipUnless(HAS_QT,'Desktop dependencies not installed')
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):self.window=Window(autosearch=False)
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
        w=self.window;self.select('ios');w.start_new();self.assertEqual(w.tabs.currentIndex(),1);self.assertEqual(w.mode,'new')
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

if __name__=='__main__':unittest.main()
