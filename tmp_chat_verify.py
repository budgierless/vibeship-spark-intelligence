import json
import requests

with open('scripts/.spark_pids.json', encoding='utf-8-sig') as f:
    port = json.load(f)['pulse_port']

for i in range(1, 6):
    try:
        r = requests.post(
            f'http://127.0.0.1:{port}/api/chat',
            json={'message': f'cleanup verify {i}', 'session_id': 'cleanup-verify'},
            timeout=40,
        )
        txt = r.text
        try:
            data = r.json()
        except Exception:
            data = {}
        t = data.get('type') or data.get('response_type') or data.get('mode')
        print(i, r.status_code, t, ('bridge_unavailable' in txt), txt[:180].replace('\n', ' '))
    except Exception as e:
        print(i, 'ERR', str(e))
