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
    hook = root / 'copilot_hook.py'
    event = sys.argv[1] if len(sys.argv) > 1 else 'sessionStart'
    if event not in {'sessionStart', 'userPromptTransformed'}:
        raise ValueError('Choose sessionStart or userPromptTransformed')
    hook.write_text("import json,sys\nfrom pathlib import Path\npayload=json.load(sys.stdin)\nroot=Path(sys.argv[1])\nevent=sys.argv[2]\nwith (root/'events.jsonl').open('a') as log: log.write(event+'\\n')\ncontext=(root/'context.txt').read_text()\noutput={'additionalContext':context} if event=='sessionStart' else {'modifiedTransformedPrompt':payload['transformedPrompt']+'\\n'+context}\nprint(json.dumps(output))\n")
    command = shlex.join(['/usr/bin/python3', str(hook), directory, event])
    (root / 'hooks').mkdir()
    (root / 'hooks' / 'daybrief.json').write_text(json.dumps({
        'version': 1, 'hooks': {event: [{'type': 'command', 'bash': command}]}
    }))
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
            '--no-custom-instructions', '--trust-folder', '--output-format', 'json',
            '-p', 'Report the marker supplied in hook context. Do not use tools.',
        ], cwd=root, env=environment,
            stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
        events = (root / 'events.jsonl').read_text() if (root / 'events.jsonl').exists() else 'none'
        print('Hook events:', events.strip())
        print('Captured requests:', len(requests))
        if not requests:
            raise AssertionError(result.stderr.decode()[-2000:] + result.stdout.decode()[-2000:])
        assert any(marker in json.dumps(json.loads(body)) for body in requests), 'Marker absent from model requests'
        print('PASS: native Copilot transmitted hook marker to loopback endpoint.')
        print('No live model was used; response intentionally rejected with HTTP 400.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
