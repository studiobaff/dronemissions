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

@unittest.skipUnless(HAS_QT,'Desktop dependencies not installed')
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):self.window=Window(autosearch=False)
    def tearDown(self):self.window.close();self.app.processEvents()
    def select(self,kind,serial='demo'):
        self.window.device.addItem('Demo',{'kind':kind,'serial':serial,'state':'device','name':'Demo'})
        self.window.device.setCurrentIndex(self.window.device.count()-1)
    def test_confirmation_is_required_and_source_edit_invalidates_it(self):
        w=self.window;self.select('ios');w.advance();self.assertEqual(w.step,1)
        with tempfile.TemporaryDirectory() as t:
            source=Path(t)/'Demo.kmz';source.write_bytes(fixture());w.set_source(source);w.prepare()
            deadline=time.monotonic()+10
            while w.job.isRunning() or w.step!=2:
                self.app.processEvents()
                if time.monotonic()>deadline:self.fail('Review did not complete')
            self.assertFalse(w.apply_button.isEnabled());self.assertFalse(w.closed.isChecked())
            w.closed.setChecked(True);self.assertTrue(w.apply_button.isEnabled())
            w.name.setText('Different mission');self.assertIsNone(w.transfer);self.assertFalse(w.apply_button.isEnabled())
    def test_replacement_list_only_appears_for_android(self):
        w=self.window;self.select('ios');self.assertTrue(w.target_panel.isHidden());self.assertFalse(w.new_note.isHidden())
        w.transfer={'test':'prepared'};self.select('android','other')
        self.assertFalse(w.target_panel.isHidden());self.assertTrue(w.new_note.isHidden());self.assertIsNone(w.transfer)

if __name__=='__main__':unittest.main()
