from __future__ import annotations

import base64
import copy
import csv
import io
import json
import os
import re
import uuid
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import portalocker

CATALOGUE = ['Q2612A', 'CAN703', 'FX10', 'CE285A', 'CAN725', 'CF230A', 'CAN051',
             'CF259X', 'CAN057H', 'CRG070H', 'W1490X', 'CAN057H with chip',
             'TN3480', 'TK-1260', 'TK-310', 'Epson 103']
TABLE_NAMES = {'rooms': 'Kabinetai', 'printers': 'Spausdintuvai', 'cartridges': 'Kasetės', 'compatibility': 'Suderinamumas'}
MOVEMENT_NAMES = {'receipt': 'Gavimas', 'issue': 'Išdavimas', 'adjustment': 'Koregavimas'}
SCHEMAS = {
    'rooms': ['department', 'floor', 'name'],
    'printers': ['name', 'model', 'ip', 'serial', 'room_id', 'status', 'image'],
    'cartridges': ['code', 'kind', 'chip', 'minimum', 'image'],
    'compatibility': ['printer_id', 'cartridge_id', 'evidence'],
}
REQUIRED = {'rooms': ['department', 'name'], 'printers': ['name', 'model', 'status'],
            'cartridges': ['code', 'kind'], 'compatibility': ['printer_id', 'cartridge_id', 'evidence']}


class ValidationError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def uid():
    return uuid.uuid4().hex


def data_dir():
    root = os.environ.get('LOCALAPPDATA')
    return Path(root) / 'PrintTrack' / 'data' if root else Path.home() / '.local' / 'share' / 'PrintTrack' / 'data'


def empty_state(demo=False, initial_catalogue=True):
    return dict(version=1, revision=0, demo=demo, rooms=[], printers=[],
                cartridges=[dict(id=uid(), code=c, kind='Originali', chip='Taip' if c.endswith('with chip') else 'Nežinoma', minimum=0, image='') for c in (CATALOGUE if initial_catalogue else [])],
                compatibility=[], movements=[], events=[], preferences={'theme': 'Šviesi'})


def integer(value, label, minimum=None):
    if isinstance(value, bool) or not re.fullmatch(r'-?\d+', str(value)):
        raise ValidationError(f'{label}: įveskite sveikąjį skaičių.')
    number = int(value)
    if minimum is not None and number < minimum:
        raise ValidationError(f'{label}: mažiausia reikšmė {minimum}.')
    return number


def stock(state, cartridge_id):
    return sum(m['quantity'] for m in state['movements'] if m['cartridge_id'] == cartridge_id)


def validate(state):
    if not isinstance(state, dict) or state.get('version') != 1:
        raise ValidationError('Neatpažintas duomenų formatas.')
    for key in [*SCHEMAS, 'movements', 'events']:
        if not isinstance(state.get(key), list):
            raise ValidationError(f'Netinkama duomenų lentelė: {key}.')
        ids = [r.get('id') for r in state[key] if isinstance(r, dict)]
        if len(ids) != len(state[key]) or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
            raise ValidationError('Neteisingi arba pasikartojantys identifikatoriai.')
    for kind, fields in SCHEMAS.items():
        for row in state[kind]:
            for field in fields:
                if field not in row:
                    raise ValidationError(f'Trūksta lauko: {field}.')
            for field in REQUIRED[kind]:
                if not isinstance(row[field], str) or not row[field].strip():
                    raise ValidationError('Privalomi laukai neužpildyti.')
    room_ids = {r['id'] for r in state['rooms']}
    printer_ids = {r['id'] for r in state['printers']}
    cartridge_ids = {r['id'] for r in state['cartridges']}
    for p in state['printers']:
        if p['room_id'] and p['room_id'] not in room_ids:
            raise ValidationError('Kabinetas nerastas.')
        if p['status'] not in ['Veikia', 'Remontas', 'Nenaudojamas', 'Nepriskirtas']:
            raise ValidationError('Nežinoma spausdintuvo būsena.')
        if p['ip']:
            import ipaddress
            try:
                ipaddress.ip_address(p['ip'])
            except ValueError:
                raise ValidationError('Netinkamas IP adresas.') from None
    codes = []
    for c in state['cartridges']:
        integer(c['minimum'], 'Minimalus likutis', 0)
        if c['kind'] not in ['Originali', 'Suderinama'] or c['chip'] not in ['Taip', 'Ne', 'Nežinoma']:
            raise ValidationError('Netinkamas kasetės tipas arba lusto reikšmė.')
        codes.append((c['code'].casefold(), c['kind'], c['chip']))
    if len(codes) != len(set(codes)):
        raise ValidationError('Tokia kasetė jau užregistruota.')
    pairs = set()
    for c in state['compatibility']:
        pair = (c['printer_id'], c['cartridge_id'])
        if pair in pairs or pair[0] not in printer_ids or pair[1] not in cartridge_ids or not c.get('verified_at'):
            raise ValidationError('Neteisingas suderinamumo patvirtinimas.')
        pairs.add(pair)
    balances = defaultdict(int)
    for m in state['movements']:
        if m.get('cartridge_id') not in cartridge_ids:
            raise ValidationError('Operacijos kasetė nerasta.')
        q = integer(m.get('quantity'), 'Kiekis')
        if not q or m.get('kind') not in ['receipt', 'issue', 'adjustment', 'restore']:
            raise ValidationError('Netinkama operacija.')
        if m['kind'] == 'issue' and (q >= 0 or not m.get('printer_id')):
            raise ValidationError('Netinkamas išdavimas.')
        if m['kind'] == 'receipt' and q < 0:
            raise ValidationError('Netinkamas gavimas.')
        try:
            datetime.fromisoformat(m['at'])
        except (KeyError, TypeError, ValueError):
            raise ValidationError('Netinkama operacijos data.') from None
        balances[m['cartridge_id']] += q
        if balances[m['cartridge_id']] < 0:
            raise ValidationError('Operacija sukurtų neigiamą likutį.')
    if not isinstance(state.get('preferences'), dict) or state['preferences'].get('theme') not in ['Šviesi', 'Tamsi']:
        raise ValidationError('Netinkami nustatymai.')
    integer(state.get('revision'), 'Duomenų versija', 0)


class Store:
    def __init__(self, directory=None, demo=False, initial_catalogue=True, write_check=None):
        self.write_check = write_check
        self.directory = Path(directory or data_dir())
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'inventory.json'
        self.journal = self.directory / 'pending.json'
        self.backups = self.directory / 'backups'
        self.backups.mkdir(exist_ok=True)
        with self.lock():
            self._recover()
            if not self.path.exists():
                self._atomic(self.path, empty_state(demo, initial_catalogue))
            self._read()
            self._backup('startup')

    @contextmanager
    def lock(self):
        try:
            with portalocker.Lock(str(self.directory / '.lock'), timeout=5):
                yield
        except portalocker.exceptions.LockException:
            raise ValidationError('Duomenys užimti. Uždarykite kitą programos langą ir bandykite dar kartą.') from None

    def _atomic(self, path, value):
        temporary = path.with_suffix('.tmp')
        with open(temporary, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)

    def _read(self):
        try:
            state = json.loads(self.path.read_text('utf-8'))
            validate(state)
            return state
        except (OSError, ValueError, TypeError, KeyError) as e:
            raise ValidationError('Duomenų failas pažeistas. Atkurkite atsarginę kopiją iš paleidimo lango.') from e

    def _recover(self):
        if self.journal.exists():
            try:
                pending = json.loads(self.journal.read_text('utf-8'))
                validate(pending)
                if self.path.exists():
                    try:
                        current = self._read()
                    except ValidationError:
                        current = None
                    if current and current['revision'] > pending['revision']:
                        self.journal.unlink()
                        return
                self._atomic(self.path, pending)
                self.journal.unlink()
            except (ValueError, OSError, TypeError, KeyError) as e:
                raise ValidationError('Nepavyko atkurti nebaigtos operacijos. Išsaugokite duomenų aplanką ir kreipkitės pagalbos.') from e

    def _backup(self, label):
        name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '-' + label + '.json'
        self._atomic(self.backups / name, self._read())
        # Keep the latest 60 automatic copies; manually named copies are never pruned.
        automatic = sorted(p for p in self.backups.glob('*.json') if p.stem.endswith(('-startup', '-auto')))
        for p in automatic[:-60]:
            p.unlink(missing_ok=True)
        return self.backups / name

    def read(self):
        with self.lock():
            self._recover()
            return self._read()

    def mutate(self, operation, label):
        with self.lock():
            if self.write_check:
                self.write_check()
            self._recover()
            state = self._read()
            result = operation(state)
            state['revision'] += 1
            state['events'].append(dict(id=uid(), at=now(), action=label))
            validate(state)
            self._backup('auto')
            self._atomic(self.journal, state)
            self._atomic(self.path, state)
            self.journal.unlink()
            return result

    def _upsert(self, state, kind, values, row_id=None):
        if kind not in SCHEMAS:
            raise ValidationError('Nežinoma lentelė.')
        row = {k: values.get(k, '') for k in SCHEMAS[kind]}
        for k, v in row.items():
            if isinstance(v, str):
                row[k] = v.strip()
        row['id'] = row_id or uid()
        if kind == 'cartridges':
            row['minimum'] = integer(row['minimum'], 'Minimalus likutis', 0)
        if kind == 'compatibility':
            row['verified_at'] = now()
        if row_id:
            old = next((r for r in state[kind] if r['id'] == row_id), None)
            if old is None:
                raise ValidationError('Įrašas nerastas.')
            if kind == 'printers' and old['model'] != row['model']:
                state['compatibility'] = [c for c in state['compatibility'] if c['printer_id'] != row_id]
            if kind == 'cartridges' and any(old[k] != row[k] for k in ['code', 'kind', 'chip']):
                state['compatibility'] = [c for c in state['compatibility'] if c['cartridge_id'] != row_id]
            old.update(row)
        else:
            state[kind].append(row)
        return row['id']

    def save(self, kind, values, row_id=None):
        return self.mutate(lambda s: self._upsert(s, kind, values, row_id), f'Įrašas: {TABLE_NAMES[kind]} / {row_id or "naujas"}')

    def revoke(self, compatibility_id):
        def operation(s):
            s['compatibility'] = [r for r in s['compatibility'] if r['id'] != compatibility_id]
        self.mutate(operation, 'Suderinamumo patvirtinimas atšauktas')

    def movement(self, kind, cartridge_id, quantity, printer_id='', note=''):
        if kind not in ['receipt', 'issue', 'adjustment']:
            raise ValidationError('Nežinoma operacija.')
        quantity = integer(quantity, 'Kiekis')
        if not note.strip():
            raise ValidationError('Įrašykite dokumentą arba operacijos pagrindimą.')
        if kind in ['receipt', 'issue'] and quantity <= 0:
            raise ValidationError('Kiekis turi būti didesnis už nulį.')
        if kind == 'issue':
            quantity = -quantity
        if quantity == 0:
            raise ValidationError('Kiekis negali būti nulis.')
        def operation(s):
            c = next((c for c in s['cartridges'] if c['id'] == cartridge_id), None)
            if not c:
                raise ValidationError('Kasetė nerasta.')
            p = next((p for p in s['printers'] if p['id'] == printer_id), None)
            r = next((r for r in s['rooms'] if p and r['id'] == p['room_id']), {})
            evidence = ''
            if kind == 'issue':
                verified = next((x for x in s['compatibility'] if x['printer_id'] == printer_id and x['cartridge_id'] == cartridge_id), None)
                if not p or not verified:
                    raise ValidationError('Šiam spausdintuvui kasetės suderinamumas nepatvirtintas.')
                if p['status'] != 'Veikia':
                    raise ValidationError('Išduoti galima tik veikiančiam spausdintuvui.')
                evidence = verified['evidence']
            if stock(s, cartridge_id) + quantity < 0:
                raise ValidationError('Sandėlyje nepakanka kasečių.')
            s['movements'].append(dict(id=uid(), at=now(), kind=kind, cartridge_id=cartridge_id,
                code=c['code'], quantity=quantity, printer_id=printer_id if kind == 'issue' else '',
                printer=p['name'] if p and kind == 'issue' else '', department=r.get('department', '') if kind == 'issue' else '',
                room=r.get('name', '') if kind == 'issue' else '', evidence=evidence, note=note.strip()))
        self.mutate(operation, 'Sandėlio operacija: ' + MOVEMENT_NAMES[kind])

    def backup(self, target=None):
        with self.lock():
            self._recover()
            path = self._backup('manual')
            if target:
                self._atomic(Path(target), self._read())
            return path

    def restore(self, path):
        try:
            saved = json.loads(Path(path).read_text('utf-8'))
            validate(saved)
        except (OSError, ValueError, TypeError, KeyError) as e:
            raise ValidationError('Netinkama atsarginė kopija.') from e
        def operation(s):
            # Preserve every recorded movement; restore desired balances using new adjustments.
            for kind in ['rooms', 'printers', 'cartridges']:
                existing = {r['id']: r for r in s[kind]}
                existing.update({r['id']: copy.deepcopy(r) for r in saved[kind]})
                s[kind] = list(existing.values())
            # Only restore approvals whose evidence belongs to the restored entity identities.
            s['compatibility'] = copy.deepcopy(saved['compatibility'])
            for c in s['cartridges']:
                difference = stock(saved, c['id']) - stock(s, c['id'])
                if difference:
                    s['movements'].append(dict(id=uid(), at=now(), kind='restore', cartridge_id=c['id'], code=c['code'],
                        quantity=difference, printer_id='', printer='', department='', room='', evidence='', note='Atkurta kopija: ' + Path(path).name))
            s['preferences'] = copy.deepcopy(saved['preferences'])
        self.mutate(operation, 'Atkurta atsarginė kopija: ' + Path(path).name)

    @classmethod
    def recover_backup(cls, directory, backup):
        """Emergency recovery preserves unreadable originals for specialist recovery."""
        state = json.loads(Path(backup).read_text('utf-8'))
        validate(state)
        directory = Path(directory)
        with portalocker.Lock(str(directory / '.lock'), timeout=5):
            suffix = '.damaged-' + uid()
            for name in ['inventory.json', 'pending.json']:
                path = directory / name
                if path.exists():
                    path.rename(directory / (name + suffix))
            instance = object.__new__(cls)
            instance._atomic(directory / 'inventory.json', state)
        return cls(directory)

    def set_theme(self, theme):
        self.mutate(lambda s: s['preferences'].update(theme=theme), 'Pakeista tema')

    def import_csv(self, kind, path):
        if kind not in ['rooms', 'printers', 'cartridges']:
            raise ValidationError('Šios lentelės importuoti negalima.')
        with open(path, encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or not set(SCHEMAS[kind]).issubset(reader.fieldnames):
                raise ValidationError('CSV stulpeliai turi atitikti eksporto šabloną: ' + ', '.join(SCHEMAS[kind]))
            rows = list(reader)
        def operation(s):
            for row in rows:
                row_id = row.get('id', '')
                existing = next((r for r in s[kind] if r['id'] == row_id), None)
                self._upsert(s, kind, row, row_id if existing else None)
        self.mutate(operation, f'CSV importas: {TABLE_NAMES[kind]}, {len(rows)} įrašų')
        return len(rows)

    def export_csv(self, kind, path):
        s = self.read()
        rows = s[kind]
        fields = ['id'] + SCHEMAS[kind] + (['verified_at'] if kind == 'compatibility' else []) if kind in SCHEMAS else ['id', 'at', 'kind', 'cartridge_id', 'code', 'quantity', 'printer_id', 'printer', 'department', 'room', 'evidence', 'note']
        write_csv(path, fields, rows)


def write_csv(path, fields, rows):
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fields, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            # Guard spreadsheet formula injection while retaining numeric quantities.
            writer.writerow({k: ("'" + v if isinstance(v, str) and v[:1] in ['=', '+', '-', '@'] else v) for k, v in row.items() if k in fields})


def usage(state, group='month', month='', department='', room='', printer='', cartridge=''):
    totals = defaultdict(int)
    for m in state['movements']:
        if m['kind'] != 'issue':
            continue
        if month and not m['at'].startswith(month):
            continue
        if any(v and m.get(k) != v for k, v in [('department', department), ('room', room), ('printer', printer), ('code', cartridge)]):
            continue
        key = m['at'][:7] if group == 'month' else m.get(group, '')
        totals[key or 'Nepriskirta'] -= m['quantity']
    return sorted(totals.items())


def kpis(state):
    return dict(printers=len(state['printers']), stock=sum(stock(state, c['id']) for c in state['cartridges']),
                low=sum(stock(state, c['id']) <= c['minimum'] for c in state['cartridges'] if c['minimum'] > 0),
                issued=sum(-m['quantity'] for m in state['movements'] if m['kind'] == 'issue' and m['at'].startswith(now()[:7])))


def demo_store(directory):
    store = Store(directory, demo=True)
    if store.read()['printers']:
        return store
    room = store.save('rooms', dict(department='DEMO · Terapija', floor='2', name='201'))
    printer = store.save('printers', dict(name='DEMO · Registratūra', model='HP LaserJet 1020', ip='192.168.1.25', serial='DEMO-001', room_id=room, status='Veikia', image=''))
    c = store.read()['cartridges'][0]
    store.save('cartridges', dict(c, minimum=5), c['id'])
    store.save('compatibility', dict(printer_id=printer, cartridge_id=c['id'], evidence='DEMO: mokomasis patvirtinimas, netaikyti tikriems įrenginiams'))
    store.movement('receipt', c['id'], 12, note='DEMO gavimas')
    store.movement('issue', c['id'], 2, printer, 'DEMO išdavimas')
    return store
