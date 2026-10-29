"""Optional pexpect harness for native continuous-session acceptance checks."""
import json
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import time

# The system pexpect package is a spike-only prerequisite, not a runtime dependency.
sys.path.append('/usr/lib/python3/dist-packages')
import pexpect


def interactive(client, argv, environment, work, requests, app, strings):
    if client == 'codex':
        argv = [x for x in argv if x not in ('exec', '--json')]
        argv.insert(1, '--no-alt-screen')
    elif client == 'copilot':
        pos = argv.index('--output-format')
        del argv[pos:pos + 2]
        argv[argv.index('-p')] = '-i'
        argv.remove('--trust-folder')
    else:
        pos = argv.index('--output-format')
        argv[pos + 1] = 'stream-json'
        argv = argv[:-1] + ['--input-format', 'stream-json', '--verbose']
    environment['TERM'] = 'xterm-256color'
    log = Path('/tmp/daybrief-' + client + '-interactive.txt').open('w')
    if client == 'claude':
        process = subprocess.Popen(argv, cwd=work, env=environment, stdin=subprocess.PIPE,
                                   stdout=log, stderr=log, text=True)
        child = None
    else:
        process = None
        child = pexpect.spawn(argv[0], argv[1:], cwd=work, env=environment,
                              encoding='utf-8', timeout=1, dimensions=(50, 160))
        child.logfile = log

    def send(prompt):
        if client == 'claude':
            process.stdin.write(json.dumps({'type': 'user', 'message': {'role': 'user', 'content': prompt}}) + '\n')
            process.stdin.flush()
        else:
            child.send(prompt)
            child.send('\r')

    def pump(seconds):
        if process is not None:
            assert process.poll() is None, 'Claude exited; see ' + log.name
            time.sleep(seconds)
            return
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            try:
                index = child.expect([r'\x1b\[6n', '(?i)trust this folder', '(?i)trust the files in this folder', pexpect.EOF], timeout=0.2)
                if index == 0:
                    child.send('\x1b[1;1R')
                elif index in (1, 2):
                    child.send('\r')
                else:
                    raise AssertionError('Native client exited: ' + str(child.before)[-2000:])
            except pexpect.TIMEOUT:
                pass

    def wait_requests(count):
        end = time.monotonic() + 35
        while len(requests) < count and time.monotonic() < end:
            pump(0.3)
        assert len(requests) >= count, f'{client}: only {len(requests)} requests; see {log.name}'
        pump(2)

    try:
        if client == 'claude':
            send('Delete the isolated probe brief using the requested tool.')
        wait_requests(2)
        assert app.list(('global',)) == []
        new = app.create('violet-dawn-next-prompt-842', 'global')
        count = len(requests)
        send('Report the updated Daybrief snapshot.')
        wait_requests(count + 1)
        if not any(new.message in text for text in strings(requests[-1])):
            Path('/tmp/daybrief-' + client + '-requests.json').write_text(json.dumps(requests, indent=2))
            raise AssertionError('Next-prompt refresh absent; captured requests in /tmp')
        print(f'PASS {client}: next user turn refresh in same process.', flush=True)
        deleted = app.delete(new.id, 'global')
        count = len(requests)
        send('/compact')
        wait_requests(count + 1)
        count = len(requests)
        send('Report the Daybrief snapshot after compaction.')
        wait_requests(count + 1)
        snapshots = []
        for text in strings(requests[-1]):
            start = text.find('{"daybrief_snapshot_at":')
            if start >= 0:
                value, _ = json.JSONDecoder().raw_decode(text[start:])
                snapshots.append(value)
        assert any(not value['briefs'] and datetime.fromisoformat(value['daybrief_snapshot_at']) >= deleted.deleted_at for value in snapshots), 'Fresh post-compaction withdrawal absent'
        log.flush()
        transcript = Path(log.name).read_text()
        compact_marker = {'codex': 'Context compacted', 'claude': 'compact_boundary', 'copilot': 'Compaction completed'}[client]
        assert compact_marker in transcript, 'Native compaction completion not observed'
        print(f'PASS {client}: empty snapshot after native /compact and next prompt.', flush=True)
    finally:
        if child is not None:
            child.close(force=True)
        else:
            process.terminate()
            process.wait(timeout=10)
        log.close()
