"""Credential store: no real keychain or DPAPI calls; subprocess is patched."""
import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import credentials

class Tests(unittest.TestCase):
    def test_unsupported_backend_keeps_key_in_memory_only(self):
        with patch.object(credentials,'backend',return_value=None),tempfile.TemporaryDirectory() as t:
            self.assertFalse(credentials.save('https://a/','k',Path(t)));self.assertIsNone(credentials.load('https://a/',Path(t)));credentials.delete('https://a/',Path(t))
            self.assertEqual(list(Path(t).iterdir()),[])
    def test_keychain_uses_security_cli_with_service_and_account(self):
        calls=[]
        class Result:
            def __init__(self,code,out=''):self.returncode=code;self.stdout=out
        def fake_run(args,**kw):
            calls.append(args)
            return Result(0,'geheim\n') if args[1]=='find-generic-password' else Result(0)
        with patch.object(credentials,'backend',return_value='keychain'),patch.object(credentials.subprocess,'run',side_effect=fake_run):
            self.assertTrue(credentials.save('https://Example.com/dronemissions/','geheim'));self.assertEqual(credentials.load('https://example.com/dronemissions/'),'geheim');credentials.delete('https://example.com/dronemissions/')
        self.assertEqual([c[1] for c in calls],['add-generic-password','find-generic-password','delete-generic-password'])
        self.assertTrue(all('-s' in c and credentials.SERVICE in c and 'archive:https://example.com/dronemissions/' in c for c in calls))
        self.assertNotIn('geheim',calls[1]);self.assertNotIn('geheim',calls[2])
    def test_keychain_lookup_failure_returns_none(self):
        class Result:returncode=44;stdout=''
        with patch.object(credentials,'backend',return_value='keychain'),patch.object(credentials.subprocess,'run',return_value=Result()):
            self.assertIsNone(credentials.load('https://example.com/'))

    def test_1password_uses_op_cli_and_falls_back_to_create(self):
        calls=[]
        class Result:
            def __init__(self,code,out='',err=''):self.returncode=code;self.stdout=out;self.stderr=err
        def fake_run(args,**kw):
            calls.append(args)
            if args[1:3]==['item','edit']:return Result(1,'','not found')
            if args[1:3]==['item','get']:return Result(0,'geheim\n')
            return Result(0)
        with patch.object(credentials,'available',return_value=['keychain','1password']),patch.object(credentials.subprocess,'run',side_effect=fake_run):
            self.assertEqual(credentials.backend('1password'),'1password');self.assertEqual(credentials.backend('auto'),'keychain');self.assertIsNone(credentials.backend('dpapi'))
            self.assertTrue(credentials.save('https://example.com/dronemissions/','geheim',preference='1password'))
            self.assertEqual(credentials.load('https://example.com/dronemissions/',preference='1password'),'geheim');credentials.delete('https://example.com/dronemissions/',preference='1password')
        self.assertEqual([c[1:3] for c in calls],[['item','edit'],['item','create'],['item','get'],['item','delete']])
        self.assertTrue(all(c[0]=='op' and 'Drone Missions Bridge · example.com' in ' '.join(c) for c in calls))
        self.assertIn('--reveal',calls[2])

if __name__=='__main__':unittest.main()
