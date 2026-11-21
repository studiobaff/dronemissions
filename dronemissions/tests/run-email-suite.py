#!/usr/bin/env python3
"""Disposable loopback installation, actual STARTTLS SMTP, synthetic identities only."""
import email
import email.policy
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import socketserver
import sqlite3
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from integration import Client

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def main():
    with tempfile.TemporaryDirectory(prefix='dm-preview-') as tmp, tempfile.TemporaryDirectory(prefix='dm-web-') as web:
        private = Path(tmp)
        run('php', str(ROOT/'tests/setup-preview-test.php'), tmp)
        cert, key = private/'cert.pem', private/'key.pem'
        run('openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(key), '-out', str(cert), '-days', '1', '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cert, key)
        delivered = []

        class SMTP(socketserver.StreamRequestHandler):
            def handle(self):
                def send(line):
                    self.wfile.write((line+'\r\n').encode()); self.wfile.flush()
                send('220 localhost test SMTP')
                recipient = ''
                while True:
                    raw = self.rfile.readline()
                    if not raw: return
                    line = raw.decode().strip()
                    command = line.split(' ', 1)[0].upper()
                    if command == 'EHLO':
                        send('250-localhost'); send('250-STARTTLS'); send('250 AUTH PLAIN')
                    elif command == 'STARTTLS':
                        send('220 Ready')
                        self.connection = tls.wrap_socket(self.connection, server_side=True)
                        self.rfile = self.connection.makefile('rb')
                        self.wfile = self.connection.makefile('wb')
                    elif command == 'AUTH':
                        if len(line.split())<3:
                            send('334 ');self.rfile.readline()
                        send('235 Authenticated')
                    elif command == 'MAIL': send('250 OK')
                    elif command == 'RCPT':
                        recipient = re.search(r'<([^>]+)>', line).group(1)
                        send('550 Synthetic failure' if recipient == 'failure@example.test' else '250 OK')
                    elif command == 'DATA':
                        send('354 Continue')
                        chunks = []
                        while True:
                            chunk = self.rfile.readline()
                            if chunk in (b'.\r\n', b''): break
                            chunks.append(chunk[1:] if chunk.startswith(b'..') else chunk)
                        raw = b''.join(chunks)
                        (private/(hashlib.sha256(recipient.encode()).hexdigest()+'.eml')).write_bytes(raw)
                        delivered.append(recipient)
                        send('250 Accepted')
                    elif command == 'QUIT': send('221 Goodbye'); return
                    else: send('250 OK')

        smtp = socketserver.ThreadingTCPServer(('127.0.0.1', 0), SMTP)
        thread = threading.Thread(target=smtp.serve_forever, daemon=True); thread.start()
        users = sqlite3.connect(private/'users.sqlite')
        users.execute('CREATE TABLE users(email TEXT,active INTEGER,role TEXT)')
        users.executemany('INSERT INTO users VALUES(?,?,?)', [(name+'@example.test', active, role) for name,active,role in [('admin',1,'admin'),('super',1,'superadmin'),('inactive',0,'admin'),('reader',1,'viewer'),('failure',1,'admin')]])
        users.commit()
        smtp_config = {'smtp': {'host':'localhost','port':smtp.server_address[1],'username':'synthetic','password':'synthetic','sender':'noreply@example.test','caFile':str(cert)}}
        (private/'smtp.json').write_text(json.dumps(smtp_config))
        config = json.loads((private/'config.json').read_text())
        config['emailLogin'] = {'usersDatabase':str(private/'users.sqlite'),'smtpConfig':str(private/'smtp.json')}
        (private/'config.json').write_text(json.dumps(config))
        def access(address='admin@example.test'):
            return {'email':address,'mailbox':str(private/(hashlib.sha256(address.encode()).hexdigest()+'.eml'))}
        (private/'access.json').write_text(json.dumps(access()))
        Path(web,'dronemissions').symlink_to(ROOT/'public', target_is_directory=True)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); port = sock.getsockname()[1]
        base = f'http://127.0.0.1:{port}/dronemissions/'
        log = (private/'server.log').open('w')
        server = subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',web], env={**os.environ,'DRONEMISSIONS_PRIVATE':tmp}, stdout=log, stderr=log)
        try:
            for attempt in range(60):
                try: Client(base); break
                except Exception: time.sleep(.1)
            def clear_rates():
                with sqlite3.connect(private/'missions.sqlite') as db: db.execute('DELETE FROM login_attempts')
            def code(address='admin@example.test'):
                msg=email.message_from_bytes(Path(access(address)['mailbox']).read_bytes(),policy=email.policy.default)
                assert msg.is_multipart() and msg.get_body(preferencelist=('html',))
                return re.search(r'Anmeldecode für Drone Missions: (\d{6})', msg.get_body(preferencelist=('plain',)).get_content()).group(1)
            def session_file(c):
                jar=next(h.cookiejar for h in c.opener.handlers if hasattr(h,'cookiejar'))
                cookie=next(x for x in jar if x.name=='dm_session')
                return private/'sessions'/('sess_'+cookie.value),cookie
            def expire(c,field):
                file,_=session_file(c); content=file.read_text()
                # PHP session serialization: owner expiry vs nested OTP expiry.
                pattern = r'expires\|i:\d+' if field=='owner' else r'"expires";i:\d+'
                content,count=re.subn(pattern, 'expires|i:1' if field=='owner' else '"expires";i:1',content)
                assert count==1;file.write_text(content)
            c=Client(base)
            saved=c.csrf;c.csrf='wrong';c.call('login',{'email':'admin@example.test'},expected=403);c.csrf=saved
            import urllib.request, urllib.error
            req=urllib.request.Request(base+'api.php?action=login',data=json.dumps({'email':'admin@example.test'}).encode(),headers={'Content-Type':'application/json','X-CSRF-Token':c.csrf,'Origin':'https://foreign.example'})
            try: c.opener.open(req); raise AssertionError('foreign origin accepted')
            except urllib.error.HTTPError as e: assert e.code==403
            for address in ['missing','inactive','reader']:
                before=len(delivered);c.call('login',{'email':address+'@example.test'});c.call('login-verify',{'code':'000000'},expected=401);assert len(delivered)==before
            c.call('login',{'email':'admin@example.test'});otp=code();old_file,_=session_file(c)
            c.call('login-verify',{'code':otp});new_file,cookie=session_file(c)
            assert old_file!=new_file and not old_file.exists()
            assert 43195 <= cookie.expires-time.time() <= 43200
            assert cookie.has_nonstandard_attr('HttpOnly') and cookie.get_nonstandard_attr('SameSite')=='Strict'
            expiry=cookie.expires;assert c.call('session')['authenticated'];assert session_file(c)[1].expires==expiry
            c.call('login-verify',{'code':otp},expected=401)
            users.execute("UPDATE users SET role='viewer' WHERE email='admin@example.test'");users.commit()
            c.call('library',expected=401)
            users.execute("UPDATE users SET role='admin' WHERE email='admin@example.test'");users.commit()
            assert not c.call('session')['authenticated']
            clear_rates();c.login(access());expire(c,'owner');c.call('library',expected=401)
            c.login(access());c.call('logout',{});assert not c.call('session')['authenticated']
            c.call('login',{'email':'admin@example.test'});otp=code();expire(c,'otp');c.call('login-verify',{'code':otp},expected=401)
            clear_rates();c.call('login',{'email':'admin@example.test'});otp=code()
            wrong='000000' if otp!='000000' else '000001'
            for _ in range(5): c.call('login-verify',{'code':wrong},expected=401)
            c.call('login-verify',{'code':otp},expected=401)
            c.call('login',{'email':'admin@example.test'});otp=code();other=Client(base);other.call('login-verify',{'code':otp},expected=401)
            users.execute("UPDATE users SET active=0 WHERE email='admin@example.test'");users.commit()
            c.call('login-verify',{'code':otp},expected=401)
            users.execute("UPDATE users SET active=1 WHERE email='admin@example.test'");users.commit()
            clear_rates();superuser=Client(base);superuser.login(access('super@example.test'));assert superuser.call('session')['authenticated']
            c.call('login',{'email':'failure@example.test'},expected=503);c.call('login-verify',{'code':'000000'},expected=401)
            clear_rates()
            for _ in range(5): Client(base).call('login',{'email':'missing@example.test'})
            Client(base).call('login',{'email':'missing@example.test'},expected=429)
            clear_rates()
            for n in range(30): Client(base).call('login',{'email':f'missing{n}@example.test'})
            Client(base).call('login',{'email':'another@example.test'},expected=429)
            print('PASS: STARTTLS HTML/text delivery, active roles, rejection, revocation, CSRF/origin, replay, session rotation, absolute cookie/expiry, OTP expiry/attempts, cross-session rejection, SMTP failure, address/IP limits',flush=True)
            for script in ['integration.py','previews.py','project-maps-pois.py','planner-api.py','circle-grid-api.py','kmz-editor-api.py']:
                clear_rates()
                args=[sys.executable,str(ROOT/'tests'/script),'--base',base,'--access',str(private/'access.json')]
                if script=='integration.py':args.append('--allow-test-writes')
                run(*args)
            clear_rates()
            run(sys.executable,str(ROOT/'tests/device-access.py'),base,str(private/'access.json'),tmp)
            if os.environ.get('DM_BROWSER_TESTS')=='1':
                clear_rates()
                run('node',str(ROOT/'tests/email-browser.cjs'),base,str(private/'access.json'))
        finally:
            server.terminate();server.wait();log.close();smtp.shutdown();smtp.server_close();users.close()


if __name__=='__main__': main()
