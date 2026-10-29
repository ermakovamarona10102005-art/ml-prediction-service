#!/usr/bin/env python3
"""Generate explicitly labeled laboratory traffic; label 1 simulates wrong references."""
import argparse
import json
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser()
parser.add_argument('--count', type=int, default=20)
parser.add_argument('--reference-class', type=int, choices=[0, 1, 2], default=0)
args = parser.parse_args()
assert 0 < args.count <= 200
features = [14.23, 1.71, 2.43, 15.6, 127, 2.8, 3.06, 0.28, 2.29, 5.64, 1.04, 3.92, 1065]
body = json.dumps({'features': features, 'true_class': args.reference_class}).encode()
for _ in range(args.count):
    req = Request('http://127.0.0.1:5000/predict', body, {'Content-Type': 'application/json'})
    with urlopen(req, timeout=30) as response:
        result = json.load(response)
        assert result['class'] == 0
print(f'LAB TRAFFIC: {args.count} successful predictions; model class=0; reference class={args.reference_class}')
if args.reference_class != 0:
    print('Controlled fault exercise: intentionally mismatched reference labels, not measured production degradation.')
