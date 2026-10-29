"""Capture native Copilot hook context at a loopback model endpoint (no model)."""
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
        for delta, finish in [({'role': 'assistant', 'content': 'Probe acknowledged.'}, None), ({}, 'stop')]:
            chunk = {'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
            self.wfile.write(('data: ' + json.dumps(chunk) + '\n\n').encode())
        self.wfile.write(b'data: [DONE]\n\n')

    def log_message(self, *args):
        pass


with tempfile.TemporaryDirectory(prefix='daybrief-request-') as directory:
    root = Path(directory)
    server = HTTPServer(('127.0.0.1', 0), Capture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    marker = 'amber-dawn-731'
    (root / 'context.txt').write_text('Daybrief probe marker: ' + marker)
    hook = root / 'copilot_hook.py'
    event = 'userPromptTransformed'
    if event not in {'sessionStart', 'userPromptTransformed'}:
        raise ValueError('Choose sessionStart or userPromptTransformed')
    hook.write_text("import json,sys\nfrom pathlib import Path\npayload=json.load(sys.stdin)\nroot=Path(sys.argv[1])\nevent=sys.argv[2]\nwith (root/'events.jsonl').open('a') as log: log.write(event+'\\n')\ncontext=(root/'context.txt').read_text()\noutput={'additionalContext':context} if event=='sessionStart' else {'modifiedTransformedPrompt':payload['transformedPrompt']+'\\n'+context}\nprint(json.dumps(output))\n")
    command = shlex.join(['/usr/bin/python3', str(hook), directory, event])
    (root / 'hooks').mkdir()
    (root / 'hooks' / 'daybrief.json').write_text(json.dumps({
        'version': 1, 'hooks': {event: [{'type': 'command', 'bash': command}]}
    }))
    prompt = 'Report the current brief.'
    try:
        environment = {key: os.environ[key] for key in ['PATH', 'HOME', 'LANG'] if key in os.environ}
        environment.update({
            'COPILOT_HOME': directory,
            'XDG_CACHE_HOME': '/tmp/daybrief-copilot-spike/cache',
            'COPILOT_PROVIDER_BASE_URL': f'http://127.0.0.1:{server.server_port}/v1',
            'COPILOT_MODEL': 'probe',
        })
        result = subprocess.run([
            '/tmp/daybrief-copilot-spike/node_modules/.bin/copilot',
            '--no-auto-update', '--disable-client-telemetry', '--disable-builtin-mcps',
            '--trust-folder', '--output-format', 'json',
            '-p', prompt,
        ], cwd=root, env=environment,
            stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
        assert result.returncode == 0, result.stderr.decode() + result.stdout.decode()
        messages = [json.loads(line) for line in result.stdout.splitlines()]
        session = next(message['sessionId'] for message in messages if message['type'] == 'result')
        assert marker in json.dumps(json.loads(requests[-1]))
        withdrawal = 'Daybrief snapshot replaces all prior Daybrief snapshots. No active briefs. amber-dawn-731 is withdrawn.'
        (root / 'context.txt').write_text(withdrawal)
        second = subprocess.run([
            '/tmp/daybrief-copilot-spike/node_modules/.bin/copilot',
            '--no-auto-update', '--disable-client-telemetry', '--disable-builtin-mcps',
            '--output-format', 'json', '--resume', session,
            '-p', 'Report the current brief again.',
        ], cwd=root, env=environment, stdin=subprocess.DEVNULL,
            capture_output=True, timeout=30)
        assert second.returncode == 0, second.stderr.decode() + second.stdout.decode()
        assert len(requests) >= 2
        assert withdrawal in json.dumps(json.loads(requests[-1]))
        print('PASS: same Copilot session received initial snapshot and subsequent withdrawal.')
        print('Native client with synthetic endpoint; model behavior is not tested.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
