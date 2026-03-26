#!/usr/bin/env python3
"""
TicketBadgeManager Print Agent

Polls the TBM server for pending print jobs and prints them via:
  - Windows: TSCLIB.dll (TSC thermal printers)
  - macOS/Linux: lpr command

Usage:
    python agent.py [--config path/to/agent_config.ini]
    python agent.py --url https://myserver.com --event 1 --token abc123

Config file (agent_config.ini):
    [server]
    url = https://myserver.com
    event_pk = 1
    token = your-agent-token
    poll_interval = 2

    [printers]
    queue_1 = TSC TDP-225
    queue_2 =
"""
import argparse
import base64
import configparser
import os
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
import json


DEFAULT_POLL_INTERVAL = 2
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agent_config.ini')


def load_config(config_path, args):
    """Load configuration from INI file, then override with CLI args."""
    cfg = configparser.ConfigParser()
    cfg.read(config_path)

    url = getattr(args, 'url', None) or cfg.get('server', 'url', fallback='')
    event_pk = getattr(args, 'event', None) or cfg.get('server', 'event_pk', fallback='')
    token = getattr(args, 'token', None) or cfg.get('server', 'token', fallback='')
    poll_interval = int(cfg.get('server', 'poll_interval', fallback=str(DEFAULT_POLL_INTERVAL)))
    queue_1 = cfg.get('printers', 'queue_1', fallback='')
    queue_2 = cfg.get('printers', 'queue_2', fallback='')

    if not url or not event_pk or not token:
        print('ERROR: url, event_pk, and token are required (in config file or via CLI args)', file=sys.stderr)
        sys.exit(1)

    return {
        'url': url.rstrip('/'),
        'event_pk': event_pk,
        'token': token,
        'poll_interval': poll_interval,
        'printers': {'1': queue_1, '2': queue_2},
    }


def _http(url, token, method='GET', body=None):
    """Make an HTTP request with X-Agent-Token auth. Returns parsed JSON or None on error."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('X-Agent-Token', token)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f'HTTP {e.code} from server: {e.read().decode()[:200]}', file=sys.stderr)
        return None
    except Exception as e:
        print(f'Request failed: {e}', file=sys.stderr)
        return None


def poll(config, queue):
    """Poll for the next pending job on the given queue. Returns job dict or None."""
    url = f"{config['url']}/events/{config['event_pk']}/agent/poll/?queue={queue}"
    data = _http(url, config['token'])
    if data and 'job_id' in data:
        return data
    return None


def ack(config, job_id, success, error=''):
    """Acknowledge a print job result."""
    url = f"{config['url']}/events/{config['event_pk']}/agent/ack/"
    _http(url, config['token'], method='POST', body={
        'job_id': job_id,
        'success': success,
        'error': error,
    })


def print_windows(tspl_bytes, printer_name):
    """Print raw TSPL bytes via TSCLIB.dll on Windows."""
    import ctypes
    try:
        tsc = ctypes.WinDLL('TSCLIB.dll')
    except OSError as e:
        raise RuntimeError(f'Cannot load TSCLIB.dll: {e}') from e
    # Declare wide-string argtypes so ctypes marshals Python str correctly
    tsc.openportW.argtypes = [ctypes.c_wchar_p]
    tsc.printlabelW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
    tsc.openportW(printer_name)
    try:
        # sendcommand takes a C string (null-terminated); TSPL bytes must not contain null bytes
        buf = ctypes.create_string_buffer(tspl_bytes)
        tsc.sendcommand(buf)
        tsc.printlabelW('1', '1')
    finally:
        tsc.closeport()


def print_unix(tspl_bytes, printer_name):
    """Print raw TSPL bytes via lpr on macOS/Linux."""
    cmd = ['lpr', '-P', printer_name, '-o', 'raw']
    proc = subprocess.run(cmd, input=tspl_bytes, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f'lpr failed: {proc.stderr.decode()[:200]}')


def print_job(tspl_bytes, printer_name):
    """Dispatch to platform-appropriate print function."""
    if platform.system() == 'Windows':
        print_windows(tspl_bytes, printer_name)
    else:
        print_unix(tspl_bytes, printer_name)


def run_once(config):
    """Poll all configured queues once and process any pending job."""
    for queue, printer_name in config['printers'].items():
        if not printer_name:
            continue
        job = poll(config, queue)
        if not job:
            continue
        job_id = job['job_id']
        print_data = job['print_data']
        print(f'Job {job_id} received for queue {queue} ({printer_name})')
        try:
            tspl_bytes = base64.b64decode(print_data)
            print_job(tspl_bytes, printer_name)
            print(f'Job {job_id} printed OK')
            ack(config, job_id, success=True)
        except Exception as e:
            print(f'Job {job_id} FAILED: {e}', file=sys.stderr)
            ack(config, job_id, success=False, error=str(e))


def main():
    parser = argparse.ArgumentParser(description='TicketBadgeManager Print Agent')
    parser.add_argument('--config', default=CONFIG_FILE, help='Path to agent_config.ini')
    parser.add_argument('--url', help='Server URL (overrides config)')
    parser.add_argument('--event', help='Event PK (overrides config)')
    parser.add_argument('--token', help='Agent token (overrides config)')
    args = parser.parse_args()

    config = load_config(args.config, args)
    print(f"Agent started — server: {config['url']} event: {config['event_pk']} poll: {config['poll_interval']}s")

    while True:
        try:
            run_once(config)
        except Exception as e:
            print(f'Unexpected error: {e}', file=sys.stderr)
        time.sleep(config['poll_interval'])


if __name__ == '__main__':
    main()
