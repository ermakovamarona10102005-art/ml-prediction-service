"""Local laboratory notification receiver; no external messages are sent."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
from datetime import datetime, timezone

EVENTS = Path('/data/notifications.jsonl')

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/dummy':
            self.send_error(404)
            return
        length = int(self.headers.get('Content-Length', '0'))
        if length <= 0 or length > 1048576:
            self.send_error(413)
            return
        try:
            data = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeError):
            self.send_error(400)
            return
        record = {'received_at': datetime.now(timezone.utc).isoformat(), **data}
        EVENTS.parent.mkdir(parents=True, exist_ok=True)
        with EVENTS.open('a') as stream:
            stream.write(json.dumps(record) + '\n')
        print(json.dumps({'status': data.get('status'), 'alerts': [
            x.get('labels', {}).get('alertname') for x in data.get('alerts', [])
        ]}), flush=True)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

ThreadingHTTPServer(('0.0.0.0', 5001), Handler).serve_forever()
