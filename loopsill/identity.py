from hashlib import sha256
import json
import re

from .errors import MediaError


def digest(payload):
    return sha256(payload).hexdigest()


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def identity(value):
    return digest(json_bytes(value))


def valid_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value):
        raise MediaError('内容编号无效')
    return value
