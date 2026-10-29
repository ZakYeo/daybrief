"""Capture native Claude hook context at a loopback model endpoint (no model)."""
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
    (root / 'settings.json').write_text(json.dumps({'hooks': {
        event: [{'hooks': [{'type': 'command', 'command': command}]}]
        for event in ['SessionStart', 'UserPromptSubmit']
    }}))
    skill_mode = '--skill' in sys.argv
    if skill_mode:
        skill = root / 'skills' / 'daybrief'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text(
            '---\nname: daybrief\ndescription: Daybrief command probe\n---\n'
            'Report the skill marker violet-brief-842. Arguments: $ARGUMENTS\n'
        )
    prompt = '/daybrief list' if skill_mode else 'Report the marker supplied in hook context. Do not use tools.'
    try:
        environment = {key: os.environ[key] for key in ['PATH', 'HOME', 'LANG'] if key in os.environ}
        environment.update({
            'CLAUDE_CONFIG_DIR': directory,
            'ANTHROPIC_BASE_URL': f'http://127.0.0.1:{server.server_port}',
            'ANTHROPIC_API_KEY': 'local-probe-placeholder',
            'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
            'CLAUDE_CODE_MAX_RETRIES': '0',
        })
        result = subprocess.run([
            'claude', '-p', '--settings', str(root / 'settings.json'),
            '--setting-sources', 'user', '--strict-mcp-config', '--tools', '',
            '--output-format', 'json',
            prompt,
        ], cwd=root, env=environment,
            stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
        events = (root / 'events.jsonl').read_text() if (root / 'events.jsonl').exists() else 'none'
        print('Hook events:', events.strip())
        print('Captured requests:', len(requests))
        if not requests:
            raise AssertionError(result.stderr.decode()[-2000:] + result.stdout.decode()[-2000:])
        marker = 'violet-brief-842' if skill_mode else marker
        assert any(marker in json.dumps(json.loads(body)) for body in requests), 'Marker absent from model requests'
        print('PASS: native Claude transmitted ' + ('skill' if skill_mode else 'hook') + ' marker to loopback endpoint.')
        print('No live model was used; response intentionally rejected with HTTP 400.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
