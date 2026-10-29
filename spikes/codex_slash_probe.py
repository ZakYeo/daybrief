"""Capture native Codex hook context at a loopback model endpoint (no model)."""
import json
import os
from pathlib import Path
import shlex
import sys
import subprocess
import tempfile
import threading
import pexpect
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

requests = []


class Capture(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        requests.append(body)
        self.send_response(400)
        self.end_headers()
        self.wfile.write(b'{"error":{"message":"Probe complete","type":"invalid_request_error"}}')

    def log_message(self, *args):
        pass


with tempfile.TemporaryDirectory(prefix='daybrief-request-') as directory:
    root = Path(directory)
    server = HTTPServer(('127.0.0.1', 0), Capture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    marker = 'amber-dawn-731'
    (root / 'context.txt').write_text('Daybrief probe marker: ' + marker)
    command = shlex.join(['/usr/bin/python3', str(Path(__file__).with_name('hook_probe.py').resolve()), directory])
    (root / 'hooks.json').write_text(json.dumps({'hooks': {
        event: [{'hooks': [{'type': 'command', 'command': command}]}]
        for event in ['SessionStart', 'UserPromptSubmit']
    }}))
    (root / 'config.toml').write_text(f'''model = "probe"
model_provider = "probe"
[model_providers.probe]
name = "Loopback probe"
base_url = "http://127.0.0.1:{server.server_port}/v1"
wire_api = "responses"
requires_openai_auth = false
supports_websockets = false
request_max_retries = 0
''')
    skill_mode = True
    if skill_mode:
        skill = root / 'skills' / 'daybrief'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('---\nname: daybrief\ndescription: Daybrief command probe\n---\nReport violet-brief-842.\n')
    prompt = '$daybrief list' if skill_mode else 'Report the marker supplied in hook context. Do not use tools.'
    try:
        child = pexpect.spawn('codex', [
            '--no-daemon', '--no-alt-screen', '--dangerously-bypass-hook-trust',
            '-C', directory,
        ], cwd=root, env=dict(os.environ, CODEX_HOME=directory, TERM='xterm-256color'),
            encoding='utf-8', timeout=10, dimensions=(40, 120))
        transcript = open('/tmp/daybrief-codex-tui.txt', 'w')
        child.logfile = transcript
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                try:
                    index = child.expect([r'\[6n', 'trust', '›'], timeout=1)
                    if index == 0:
                        child.send('\x1b[1;1R')
                    elif index == 1:
                        child.sendline('')
                    else:
                        break
                except pexpect.TIMEOUT:
                    continue
            child.send('/daybrief list')
            child.send('\r')
            deadline = time.monotonic() + 10
            while not requests and time.monotonic() < deadline:
                try:
                    child.read_nonblocking(size=8192, timeout=0.5)
                except pexpect.TIMEOUT:
                    pass
        finally:
            child.close(force=True)
            transcript.close()
        transcript_text = Path('/tmp/daybrief-codex-tui.txt').read_text()
        assert "Unrecognized command '/daybrief'" in transcript_text
        assert not requests, 'Unexpected model request from rejected slash command'
        print('CONFIRMED: Codex 0.165.0 rejects bare /daybrief; use $daybrief.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
