"""Removal is opt-in, iPad only, confirmation-gated, and preserves unrelated rows."""
import sys,time,unittest
from pathlib import Path
from unittest.mock import patch,AsyncMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_desktop import DesktopCase,HAS_QT,UID
if HAS_QT:
 from PySide6.QtWidgets import QMessageBox
 import desktop as desktop_module

@unittest.skipUnless(HAS_QT,'Desktop dependencies not installed')
class RemovalUiTests(DesktopCase):
 def rows(self):return [{'uuid':UID,'name':'Selected','updated':'1','waypoints':2,'localState':'local','preview':False},{'uuid':UID.replace('1','2',1),'name':'Keep','updated':'2','waypoints':3,'localState':'local','preview':False}]
 def test_checkbox_only_and_ios_only(self):
  w=self.window;self.select('ios');w.show_rows(w.current_device(),self.rows());w.list.setCurrentRow(0);self.assertFalse(w.remove_device_button.isEnabled());w.toggle_checked(UID,True);self.assertTrue(w.remove_device_button.isEnabled());w.toggle_checked(UID,False);self.assertFalse(w.remove_device_button.isEnabled())
  self.select('android');w.show_rows(w.current_device(),self.rows());w.toggle_checked(UID,True);self.assertFalse(w.remove_device_button.isEnabled())
 def test_cancel_never_removes(self):
  w=self.window;self.select('ios');w.show_rows(w.current_device(),self.rows());w.toggle_checked(UID,True)
  with patch.object(QMessageBox,'exec',return_value=0),patch.object(desktop_module.ios,'remove_missions') as remove:w.remove_device_missions();remove.assert_not_called()
  self.assertEqual(len(w.rows),2)
 def test_confirmed_removal_receives_only_checked_even_when_filtered_out(self):
  w=self.window;self.select('ios');w.show_rows(w.current_device(),self.rows());w.toggle_checked(UID,True);w.device_search.setText('Keep')
  def confirm(dialog):
   self.assertIn('Selected',dialog.text());self.assertNotIn('\nKeep\n',dialog.text());self.assertIn('Webarchiv',dialog.text());self.assertFalse(dialog.checkBox().isChecked());dialog.checkBox().setChecked(True);dialog.test_choice=next(b for b in dialog.buttons() if dialog.buttonRole(b)==QMessageBox.DestructiveRole);return 0
  async def removed(*args,**kwargs):return {'status':'removed-and-verified','removed':1}
  with patch.object(QMessageBox,'exec',confirm),patch.object(QMessageBox,'clickedButton',lambda d:getattr(d,'test_choice',None)),patch.object(QMessageBox,'information'),patch.object(desktop_module.ios,'remove_missions',side_effect=removed) as remove:
   w.remove_device_missions();deadline=time.monotonic()+5
   while (w.job and w.job.isRunning()) or len(w.rows)!=1:
    self.app.processEvents()
    if time.monotonic()>deadline:self.fail('Removal did not complete')
   args,kwargs=remove.call_args;self.assertEqual(args[1],[{'uuid':UID,'name':'Selected','updated':'1'}]);self.assertTrue(kwargs['fly_closed'])
  self.assertEqual(w.rows[0]['name'],'Keep');self.assertFalse(w.checked);self.assertTrue(w.toolbar.isEnabled())
