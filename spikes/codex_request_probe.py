"""Capture native Codex hook context at a loopback model endpoint (no model)."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import threading
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
    try:
        result = subprocess.run([
            'codex', '--no-daemon', 'exec', '--skip-git-repo-check',
            '--dangerously-bypass-hook-trust', '--json',
            'Report the marker supplied in hook context. Do not use tools.',
        ], cwd=root, env=dict(os.environ, CODEX_HOME=directory),
            stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
        events = (root / 'events.jsonl').read_text()
        print('Hook events:', events.strip())
        print('Captured requests:', len(requests))
        if not requests:
            raise AssertionError(result.stderr.decode()[-2000:] + result.stdout.decode()[-2000:])
        payload = json.loads(requests[-1])
        assert marker in json.dumps(payload), 'Marker absent from model request'
        print('PASS: native Codex transmitted hook marker to loopback endpoint.')
        print('No live model was used; response intentionally rejected with HTTP 400.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
