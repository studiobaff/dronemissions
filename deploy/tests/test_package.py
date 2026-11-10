import importlib.util,json,tempfile,unittest,zipfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('package',Path(__file__).parents[1]/'package.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class PackageTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.public=self.root/'public';self.public.mkdir()
  for name in ('index.php','api.php','lib.php','view.html','app.js','style.css'):(self.public/name).write_text('example')
 def test_only_public_and_verified_manifest(self):
  (self.root/'private.key').write_text('PRIVATE')
  manifest=mod.package(self.public,self.root/'release.zip','a'*40)
  with zipfile.ZipFile(self.root/'release.zip') as z:
   self.assertEqual(set(z.namelist()),set(manifest['files'])|{'release.json'});self.assertEqual(json.loads(z.read('release.json'))['commit'],'a'*40)
 def test_font_license_allowed(self):
  (self.public/'vendor'/'fonts').mkdir(parents=True);(self.public/'vendor'/'fonts'/'DejaVu-LICENSE').write_text('license');(self.public/'vendor'/'fonts'/'DejaVuSans.woff').write_bytes(b'wOFF')
  self.assertIn('vendor/fonts/DejaVu-LICENSE',mod.package(self.public,self.root/'release.zip','a'*40)['files'])
  (self.public/'vendor'/'fonts'/'notes.txt').write_text('x')
  with self.assertRaises(ValueError):mod.package(self.public,self.root/'release.zip','a'*40)
 def test_private_config_rejected(self):
  (self.public/'config.json').write_text('{}')
  with self.assertRaises(ValueError):mod.package(self.public,self.root/'release.zip','a'*40)
 def test_symlink_rejected(self):
  (self.public/'leak.php').symlink_to(self.root/'private.key')
  with self.assertRaises(ValueError):mod.package(self.public,self.root/'release.zip','a'*40)
 def test_full_sha_required(self):
  with self.assertRaises(ValueError):mod.package(self.public,self.root/'release.zip','main')
