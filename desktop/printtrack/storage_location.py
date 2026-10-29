"""Persist a workstation's selected inventory file separately from its records."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import portalocker

from .store import Store, ValidationError, data_dir, validate_filename


def default_config_path():
    return data_dir().parent / 'settings.json'


def selected_file(config_path=None):
    config = Path(config_path or default_config_path())
    if not config.exists():
        return None
    try:
        value = json.loads(config.read_text('utf-8'))['inventory_file']
        if not isinstance(value, str) or not value or not Path(value).is_absolute():
            raise ValueError('Invalid path')
        return Path(value)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValidationError('Nepavyko perskaityti duomenų vietos nustatymo. Pasirinkite duomenų failą iš naujo.') from error


def remember_file(path, config_path=None):
    config = Path(config_path or default_config_path())
    config.parent.mkdir(parents=True, exist_ok=True)
    with portalocker.Lock(str(config) + '.lock', timeout=5):
        values = {}
        if config.exists():
            try:
                values = json.loads(config.read_text('utf-8'))
                if not isinstance(values, dict):
                    values = {}
            except (OSError, ValueError):
                values = {}
        values['inventory_file'] = str(Path(path).absolute())
        temporary = config.with_suffix('.tmp')
        with temporary.open('w', encoding='utf-8') as f:
            json.dump(values, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, config)


def open_existing(path, config_path=None, expected_demo=False):
    path = Path(path).absolute()
    # A failed network path must never create an empty replacement inventory.
    store = Store(path.parent, filename=path.name, create=False)
    if store.read()['demo'] != expected_demo:
        raise ValidationError('Tikros ir DEMO saugyklos negali būti sujungiamos. Pasirinkite tinkamos aplinkos failą.')
    remember_file(path, config_path)
    return store


def relocate(store, destination, config_path=None):
    destination = Path(destination).absolute()
    validate_filename(destination.name)
    if destination == store.path.absolute():
        remember_file(destination, config_path)
        return store
    if not destination.parent.is_dir():
        raise ValidationError('Paskirties aplankas nepasiekiamas. Patikrinkite kelią ir tinklo ryšį.')
    if destination.exists():
        raise ValidationError('Paskirties failas jau egzistuoja. Jo neperrašysime. Naudokite „Pasirinkti esamą duomenų failą“.')
    journal = destination.parent / ('pending.json' if destination.name == 'inventory.json' else destination.name + '.pending.json')
    if journal.exists():
        raise ValidationError('Paskirties vietoje yra nebaigtos operacijos žurnalas. Pirmiausia atkurkite tą saugyklą.')
    with store.lock():
        store._recover()
        state = store._read()
        if state['demo']:
            raise ValidationError('DEMO duomenų vieta nekeičiama. Pereikite į pagrindinę programą.')
        store._backup('manual')
        # Exclusive creation also refuses a destination created after our checks.
        with destination.open('x', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
    target = Store(destination.parent, filename=destination.name, create=False)
    with store.lock():
        # Keep historical backups at the new location, retaining originals too.
        for backup in store.backups.glob('*.json'):
            copied = target.backups / backup.name
            if not copied.exists():
                with backup.open('rb') as src, copied.open('xb') as dst:
                    shutil.copyfileobj(src, dst)
                    dst.flush()
                    os.fsync(dst.fileno())
        remember_file(destination, config_path)
    return target
