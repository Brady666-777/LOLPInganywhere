import json
import os
from pathlib import Path
from .core import TRIGGERS

DEFAULTS = {'enabled': False, 'trigger': next(iter(TRIGGERS)), 'volume': 55, 'scale': 100}


def load(path):
    result = DEFAULTS.copy()
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(raw, dict):
            return result
        if isinstance(raw.get('enabled'), bool):
            result['enabled'] = raw['enabled']
        if isinstance(raw.get('trigger'), str) and raw['trigger'] in TRIGGERS:
            result['trigger'] = raw['trigger']
        for key, low, high in [('volume', 0, 100), ('scale', 75, 150)]:
            if type(raw.get(key)) is int:
                result[key] = max(low, min(high, raw[key]))
    except (OSError, ValueError):
        pass
    return result


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def settings_path():
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'LoLPing' / 'settings.json'
