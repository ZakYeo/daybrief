"""Capture native Codex hook context at a loopback model endpoint (no model)."""
import json
import os
from pathlib import Path
import shlex
import sys
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

requests = []


class Capture(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        requests.append(body)
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.end_headers()
        event = {'type': 'response.completed', 'response': {
            'id': 'probe-response', 'status': 'completed', 'output': [],
            'usage': {'input_tokens': 1, 'output_tokens': 0, 'total_tokens': 1},
        }}
        self.wfile.write(('event: response.completed\ndata: ' + json.dumps(event) + '\n\n').encode())

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
        environment = dict(os.environ, CODEX_HOME=directory)
        first = subprocess.run([
            'codex', '--no-daemon', 'exec', '--skip-git-repo-check',
            '--dangerously-bypass-hook-trust', '--json', 'Report the current brief.',
        ], cwd=root, env=environment, stdin=subprocess.DEVNULL,
            capture_output=True, timeout=30)
        assert first.returncode == 0, first.stderr.decode() + first.stdout.decode()
        messages = [json.loads(line) for line in first.stdout.splitlines()]
        session = next(message['thread_id'] for message in messages if message['type'] == 'thread.started')
        assert marker in json.dumps(json.loads(requests[-1]))
        withdrawal = 'Daybrief snapshot replaces all prior Daybrief snapshots. No active briefs. amber-dawn-731 is withdrawn.'
        (root / 'context.txt').write_text(withdrawal)
        second = subprocess.run([
            'codex', '--no-daemon', 'exec', 'resume', '--skip-git-repo-check',
            '--dangerously-bypass-hook-trust', '--json', session, 'Report the current brief again.',
        ], cwd=root, env=environment, stdin=subprocess.DEVNULL,
            capture_output=True, timeout=30)
        assert second.returncode == 0, second.stderr.decode() + second.stdout.decode()
        assert len(requests) == 2, len(requests)
        assert withdrawal in json.dumps(json.loads(requests[-1]))
        print('PASS: same Codex thread received initial snapshot and subsequent withdrawal.')
        print('Native client with synthetic endpoint; model behavior is not tested.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
