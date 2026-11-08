"""Erscheinungsbild: beide Schemata rendern vollständig, Icons entstehen, die Symbolleiste trägt die Hauptfunktionen."""
import os,sys,unittest,re,unittest.mock
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
try:
    import theme
    from PySide6.QtWidgets import QApplication,QToolButton
    import test_desktop
    HAS_QT=True
except ImportError:HAS_QT=False

@unittest.skipUnless(HAS_QT,'Desktop dependencies not installed')
class ThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_both_schemes_render_without_leftover_tokens(self):
        for scheme in ('light','dark'):
            css=theme.stylesheet(scheme,font='Demo Sans')
            self.assertNotIn('$',css,scheme);self.assertNotIn('__CHE',css);self.assertIn('"Demo Sans"',css);self.assertIn(theme.tokens(scheme)['bg'],css)
        self.assertNotEqual(theme.stylesheet('light'),theme.stylesheet('dark'));self.assertEqual(set(theme.LIGHT),set(theme.DARK))
        for name in theme.LIGHT:self.assertRegex(theme.LIGHT[name],r'^#[0-9a-f]{6}$');self.assertRegex(theme.DARK[name],r'^#[0-9a-f]{6}$')
    def test_environment_variable_forces_scheme(self):
        with unittest.mock.patch.dict(os.environ,{'DRONEMISSIONS_THEME':'dark'}):self.assertEqual(theme.scheme_for(self.app),'dark')
        with unittest.mock.patch.dict(os.environ,{'DRONEMISSIONS_THEME':'light'}):self.assertEqual(theme.scheme_for(self.app),'light')
        with unittest.mock.patch.dict(os.environ,{'DRONEMISSIONS_THEME':''}):self.assertIn(theme.scheme_for(self.app),('light','dark'))
    def test_icons_render_for_every_name(self):
        for name in theme.ICONS:
            icon=theme.icon(name,'#123456');self.assertFalse(icon.isNull());pixmap=icon.pixmap(22,22);self.assertFalse(pixmap.isNull())
    def test_apply_theme_updates_open_windows(self):
        with unittest.mock.patch.dict(os.environ,{'DRONEMISSIONS_THEME':''}):
            self.assertEqual(theme.apply_theme(self.app,'dark'),'dark');self.assertEqual(self.app.property('dmScheme'),'dark')
            self.assertIn(theme.DARK['bg'],self.app.styleSheet());theme.apply_theme(self.app,'light');self.assertEqual(self.app.property('dmScheme'),'light')

@unittest.skipUnless(HAS_QT,'Desktop dependencies not installed')
class ToolbarTests(test_desktop.DesktopCase):
    def test_toolbar_carries_main_actions_with_icons(self):
        w=self.window;self.assertEqual(list(w.tool_actions),['refresh','list','backup','log','settings'])
        for action in w.tool_actions.values():self.assertFalse(action.icon().isNull());self.assertTrue(action.text())
        self.assertIsInstance(w.refresh_button,QToolButton);self.assertEqual(w.refresh_button.text(),'Neu suchen');self.assertIs(w.device.window(),w)
        w.tool_actions['settings'].trigger();self.assertTrue(w.settings_dialog.isVisible());w.settings_dialog.close()
        w.theme_changed('dark');self.assertEqual(w.property('dmScheme'),'dark');self.assertFalse(w.tool_actions['log'].icon().isNull())
    def test_review_shows_key_value_rows(self):
        import tempfile,time
        from test_core import fixture
        w=self.window;self.select('ios')
        with tempfile.TemporaryDirectory() as t:
            source=Path(t)/'Demo.kmz';source.write_bytes(fixture());w.set_source(source);w.prepare();self.wait_review()
            self.assertEqual(w.summary_points.text(),'2 Wegpunkte · 0.13 km');self.assertEqual(w.summary_source.text(),'Lokale Datei · Demo.kmz');self.assertEqual(w.summary_preview.text(),'3D-Ansicht');self.assertEqual(w.summary_target.text(),'Neue Mission auf Demo')

if __name__=='__main__':unittest.main()
