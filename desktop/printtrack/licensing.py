"""Offline, per-installation two-calendar-year free licence."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import portalocker

from .store import ValidationError

CONTACT = 'gedtre@gmail.com'
EXPIRED_MESSAGE = 'Nemokama licencija baigėsi. Kreipkitės el. paštu: ' + CONTACT
INVALID_MESSAGE = 'Nepavyko patikrinti nemokamos licencijos. Kreipkitės el. paštu: ' + CONTACT


def two_years_after(start):
    try:
        return start.replace(year=start.year + 2)
    except ValueError:
        # February 29 expires on February 28 in a non-leap expiry year.
        return start.replace(year=start.year + 2, day=28)


@dataclass(frozen=True)
class LicenceStatus:
    active: bool
    expires_at: datetime | None
    message: str


class Licence:
    def __init__(self, path, clock=None):
        self.path = Path(path)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with portalocker.Lock(str(self.path) + '.lock', timeout=5):
            if not self.path.exists():
                issued = self.clock().astimezone(timezone.utc)
                state = dict(version=1, issued_at=issued.isoformat(),
                             expires_at=two_years_after(issued).isoformat())
                temporary = self.path.with_suffix('.tmp')
                with temporary.open('w', encoding='utf-8') as f:
                    json.dump(state, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temporary, self.path)

    def status(self):
        try:
            state = json.loads(self.path.read_text('utf-8'))
            if state['version'] != 1:
                raise ValueError('Unsupported licence version')
            issued = datetime.fromisoformat(state['issued_at'])
            expiry = datetime.fromisoformat(state['expires_at'])
            if issued.utcoffset() is None or expiry.utcoffset() is None or expiry != two_years_after(issued):
                raise ValueError('Invalid licence dates')
            current = self.clock()
            if current < issued:
                return LicenceStatus(False, expiry, INVALID_MESSAGE)
            if current >= expiry:
                return LicenceStatus(False, expiry, EXPIRED_MESSAGE)
            return LicenceStatus(True, expiry, 'Nemokama licencija galioja iki ' + expiry.astimezone().strftime('%Y-%m-%d'))
        except (OSError, ValueError, KeyError, TypeError, OverflowError):
            # A missing/damaged existing licence is not silently restarted.
            return LicenceStatus(False, None, INVALID_MESSAGE)

    def require_active(self):
        status = self.status()
        if not status.active:
            raise ValidationError(status.message + '\nDuomenis galite peržiūrėti, eksportuoti ir išsaugoti jų kopiją.')
