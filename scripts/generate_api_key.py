#!/usr/bin/env python

"""
Sets the Auth0 API key in AWS secrets manager
"""
import json
import os
import sys

import argparse

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # noqa
sys.path.insert(0, pkg_root)  # noqa

from fusillade.utils.api_key import generate_api_key, api_keys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--owner", required=True)
args = parser.parse_args()

key, secret = generate_api_key(args.owner)
print(f"This value will only be visible once. Record it now. API KEY: '{key}'")
print(secret)

try:
    keys = json.loads(api_keys.value)
except RuntimeError:
    print(f"Creating AWS Secret {api_keys.name}.")
    keys = {}
print(f"Updating AWS Secret {api_keys.name}.")
keys.update(secret)
api_keys.update(json.dumps(keys))