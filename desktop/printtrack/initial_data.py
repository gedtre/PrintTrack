"""Merge a bundled user catalogue without replacing existing inventory."""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path


def room_number(value):
    """Collapse source annotations while preserving lettered room numbers."""
    match = re.match(r'^\s*(\d+)([A-Za-z]?)', str(value))
    return str(int(match[1])) + match[2].upper() if match else ''


def bundled_initial_data():
    path = Path(__file__).parent / 'assets' / 'initial-data.json'
    return json.loads(path.read_text('utf-8')) if path.exists() else None


def apply_initial_data(store, payload):
    """Merge once under the store lock; do not create stock or approvals."""
    from .store import ValidationError

    if not isinstance(payload, dict) or payload.get('format') != 'printtrack-initial-v1':
        raise ValidationError('Neatpažintas pradinių duomenų formatas.')
    package_id = payload.get('id')
    if not isinstance(package_id, str) or not package_id:
        raise ValidationError('Trūksta pradinių duomenų rinkinio identifikatoriaus.')
    current = store.read()
    if current.get('demo') or package_id in current.get('initial_imports', []):
        return False

    def merge(state):
        if package_id in state.get('initial_imports', []):
            return False
        rooms = {room_number(r['name']) for r in state['rooms']}
        for source in payload['rooms']:
            number = room_number(source['name'])
            if not number:
                raise ValidationError('Netinkamas pradinis kabineto numeris.')
            if number not in rooms:
                store._upsert(state, 'rooms', dict(source, name=number))
                rooms.add(number)
        codes = {c['code'].casefold() for c in state['cartridges']}
        for code in payload['cartridges']:
            if not isinstance(code, str) or not code.strip():
                raise ValidationError('Netinkamas pradinis kasetės kodas.')
            if code.casefold() not in codes:
                store._upsert(state, 'cartridges', dict(code=code, kind='Originali',
                    chip='Nežinoma', minimum=0, image=''))
                codes.add(code.casefold())
        models = {p['model'].casefold() for p in state['printers']}
        for source in payload['printers']:
            model = source['model']
            if model.casefold() in models:
                continue
            state['printers'].append(dict(id=uuid.uuid4().hex, name=model, model=model,
                ip='', serial='', room_id='', status='Nepriskirtas',
                image=source.get('image', ''), image_source=source.get('image_source', ''),
                source_cartridge_codes=source['source_cartridge_codes'], initial_model_card=True))
            models.add(model.casefold())
        state.setdefault('initial_imports', []).append(package_id)
        return True

    return store.mutate(merge, 'Pradiniai duomenys: ' + package_id)
