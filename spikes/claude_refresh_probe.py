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
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.end_headers()
        events = [
            {'type': 'message_start', 'message': {'id': 'msg_probe', 'type': 'message', 'role': 'assistant', 'model': 'probe', 'content': [], 'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': 1, 'output_tokens': 0}}},
            {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}},
            {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': 'Probe acknowledged.'}},
            {'type': 'content_block_stop', 'index': 0},
            {'type': 'message_delta', 'delta': {'stop_reason': 'end_turn', 'stop_sequence': None}, 'usage': {'output_tokens': 1}},
            {'type': 'message_stop'},
        ]
        for event in events:
            self.wfile.write(('event: ' + event['type'] + '\ndata: ' + json.dumps(event) + '\n\n').encode())

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
    prompt = 'Report the current brief.'
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
        assert result.returncode == 0, result.stderr.decode() + result.stdout.decode()
        first = json.loads(result.stdout)
        assert any(marker in json.dumps(json.loads(body)) for body in requests)
        requests.clear()
        withdrawal = 'Daybrief snapshot replaces all prior Daybrief snapshots. No active briefs. amber-dawn-731 is withdrawn.'
        (root / 'context.txt').write_text(withdrawal)
        second = subprocess.run([
            'claude', '-p', '--settings', str(root / 'settings.json'),
            '--setting-sources', 'user', '--strict-mcp-config', '--tools', '',
            '--output-format', 'json', '--resume', first['session_id'],
            'Report the current brief again.',
        ], cwd=root, env=environment, stdin=subprocess.DEVNULL,
            capture_output=True, timeout=30)
        assert second.returncode == 0, second.stderr.decode() + second.stdout.decode()
        assert json.loads(second.stdout)['session_id'] == first['session_id']
        assert any(withdrawal in json.dumps(json.loads(body)) for body in requests)
        print('PASS: same Claude session received initial snapshot and subsequent withdrawal.')
        print('Native client with synthetic endpoint; model behavior is not tested.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
