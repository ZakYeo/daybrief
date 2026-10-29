"""Real native clients + installed adapters; synthetic model, isolated data only.

Run with the installed Daybrief Python: python spikes/installed_adapter_probe.py CLIENT.
The synthetic tool call deletes a temporary brief, then checks post-tool withdrawal
within the same continuously running client process. No hosted model is contacted.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from daybrief.config import Config
from daybrief.install import install
from daybrief.service import Daybrief
from daybrief.storage import Store

parser = argparse.ArgumentParser()
parser.add_argument('client', choices=['codex', 'claude', 'copilot'])
parser.add_argument('--skill', action='store_true')
parser.add_argument('--interactive', action='store_true')
args = parser.parse_args()
requests = []


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)


class Capture(BaseHTTPRequestHandler):
    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        # Ignore token-counting requests, which are not model turns.
        if self.path.endswith('/count_tokens'):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"input_tokens": 100}')
            return
        auxiliary = any(text.startswith('Generate a concise, single-line task title') for text in strings(payload.get('input', [])))
        if not auxiliary:
            requests.append(payload)
        skill_turn = args.skill and args.client == 'copilot' and len(requests) == 1
        first = not auxiliary and len(requests) == (2 if args.skill and args.client == 'copilot' else 1)
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.end_headers()
        if args.client == 'codex':
            names = [t.get('name') for t in payload.get('tools', [])]
            if first and 'exec_command' not in names:
                raise AssertionError(f'Expected exec_command in {names}')
            output = [{'type': 'function_call', 'id': 'fc_probe', 'call_id': 'call_probe',
                       'name': 'exec_command', 'arguments': json.dumps({'cmd': command})}] if first else [{'type': 'message', 'id': 'msg_probe', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': 'Probe complete.'}]}]
            events = []
            if output:
                events.append({'type': 'response.output_item.done', 'output_index': 0, 'item': output[0]})
            events.append({'type': 'response.completed', 'response': {
                'id': 'resp_' + str(len(requests)), 'status': 'completed', 'output': output,
                'usage': {'input_tokens': 100, 'output_tokens': 10, 'total_tokens': 110}}})
            self.events(events)
        elif args.client == 'claude':
            block = {'type': 'tool_use', 'id': 'tool_probe', 'name': 'Bash', 'input': {}} if first else {'type': 'text', 'text': ''}
            delta = {'type': 'input_json_delta', 'partial_json': json.dumps({'command': command, 'description': 'Delete isolated probe brief'})} if first else {'type': 'text_delta', 'text': 'Probe complete.'}
            self.events([
                {'type': 'message_start', 'message': {'id': 'msg_probe', 'type': 'message', 'role': 'assistant', 'model': 'probe', 'content': [], 'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': 100, 'output_tokens': 0}}},
                {'type': 'content_block_start', 'index': 0, 'content_block': block},
                {'type': 'content_block_delta', 'index': 0, 'delta': delta},
                {'type': 'content_block_stop', 'index': 0},
                {'type': 'message_delta', 'delta': {'stop_reason': 'tool_use' if first else 'end_turn', 'stop_sequence': None}, 'usage': {'output_tokens': 10}},
                {'type': 'message_stop'},
            ])
        else:
            delta = {'role': 'assistant', 'tool_calls': [{'index': 0, 'id': 'tool_probe', 'type': 'function', 'function': {'name': 'bash', 'arguments': json.dumps({'command': command, 'description': 'Delete isolated probe brief'})}}]} if first else {'role': 'assistant', 'content': 'Probe complete.'}
            if skill_turn:
                delta = {'role': 'assistant', 'tool_calls': [{'index': 0, 'id': 'skill_probe', 'type': 'function', 'function': {'name': 'skill', 'arguments': '{"skill":"daybrief"}'}}]}
            for d, reason in [(delta, None), ({}, 'tool_calls' if first or skill_turn else 'stop')]:
                self.wfile.write(('data: ' + json.dumps({'choices': [{'index': 0, 'delta': d, 'finish_reason': reason}]}) + '\n\n').encode())
            self.wfile.write(b'data: [DONE]\n\n')

    def events(self, events):
        for event in events:
            self.wfile.write(('event: ' + event['type'] + '\ndata: ' + json.dumps(event) + '\n\n').encode())

    def log_message(self, *args):
        pass


with tempfile.TemporaryDirectory(prefix='daybrief-installed-') as directory:
    root = Path(directory)
    data = root / 'data'
    profile = root / 'profile'
    work = root / 'work'
    work.mkdir()
    subprocess.run(['git', 'init', '-q', str(work)], check=True)
    install(args.client, profile)
    app = Daybrief(Store(data / 'state.sqlite'), Config('UTC'))
    brief = app.create('amber-dawn-installed-731', 'global')
    command = shlex.join([sys.executable, '-m', 'daybrief', '--scope', 'global', 'delete', brief.id])
    server = HTTPServer(('127.0.0.1', 0), Capture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    environment = {key: os.environ[key] for key in ['PATH', 'HOME', 'LANG'] if key in os.environ}
    environment['DAYBRIEF_DATA_DIR'] = str(data)
    environment['HOME'] = str(root / 'home')
    (root / 'home').mkdir()
    endpoint = f'http://127.0.0.1:{server.server_port}'
    prompt = 'Run the requested tool to delete the isolated probe brief, then finish.'
    if args.skill:
        prompt = ('$daybrief' if args.client == 'codex' else '/daybrief') + ' list'
    if args.client == 'codex':
        environment['CODEX_HOME'] = str(profile)
        (profile / 'config.toml').write_text(f'''model = "probe"
model_provider = "probe"
[model_providers.probe]
name = "Loopback probe"
base_url = "{endpoint}/v1"
wire_api = "responses"
requires_openai_auth = false
supports_websockets = false
request_max_retries = 0
''')
        argv = ['codex', '--no-daemon', 'exec', '--dangerously-bypass-hook-trust', '--dangerously-bypass-approvals-and-sandbox', '--json', prompt]
    elif args.client == 'claude':
        environment.update(CLAUDE_CONFIG_DIR=str(profile), ANTHROPIC_BASE_URL=endpoint,
                           ANTHROPIC_API_KEY='local-probe-placeholder',
                           CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1', CLAUDE_CODE_MAX_RETRIES='0')
        argv = ['claude', '-p', '--settings', str(profile / 'settings.json'), '--setting-sources', 'user', '--strict-mcp-config', '--tools', 'Bash', '--allowedTools', 'Bash', '--output-format', 'json', prompt]
    else:
        environment.update(COPILOT_HOME=str(profile), XDG_CACHE_HOME='/tmp/daybrief-copilot-spike/cache',
                           COPILOT_PROVIDER_BASE_URL=endpoint + '/v1', COPILOT_MODEL='probe')
        argv = ['/tmp/daybrief-copilot-spike/node_modules/.bin/copilot', '--no-auto-update', '--disable-client-telemetry', '--disable-builtin-mcps', '--trust-folder', '--allow-tool', 'shell', '--allow-all-paths', '--output-format', 'json', '-p', prompt]
    try:
        if args.interactive:
            from native_interactive import interactive
            interactive(args.client, argv, environment, work, requests, app, strings)
            raise SystemExit(0)
        result = subprocess.run(argv, cwd=work, env=environment, stdin=subprocess.DEVNULL,
                                capture_output=True, timeout=45)
        assert result.returncode == 0, result.stderr.decode()[-3000:] + result.stdout.decode()[-3000:]
        assert len(requests) >= 2, f'Expected tool continuation, got {len(requests)} requests: ' + result.stdout.decode()[-3000:]
        assert any(brief.message in text for text in strings(requests[0]))
        assert app.list(('global',)) == [], 'Native tool did not delete brief: ' + result.stdout.decode()[-5000:] + json.dumps(requests[-1])[-5000:]
        assert any('"briefs": []' in text for text in strings(requests[-1])), 'Post-tool empty snapshot absent'
        if args.skill:
            assert any('Translate clear expiry requests' in text for request in requests for text in strings(request)), 'Packaged skill body was not loaded'
        print(f'PASS {args.client}: installed hooks supplied active snapshot and post-tool withdrawal in one process.')
        print('Real client, synthetic loopback model; no hosted-model interpretation claim.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
