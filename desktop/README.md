# PrintTrack Desktop

Python 3.12 / PySide6 application with Lithuanian UI, local JSON storage, no server.
User instructions: [NAUDOJIMAS.txt](NAUDOJIMAS.txt).

## Development

```sh
python -m venv .venv
# Activate .venv using the usual command for your platform.
python -m pip install -r desktop/requirements-dev.txt
python desktop/make_assets.py
python desktop/main.py
python -m pytest desktop/tests -q
```

Headless Qt checks: set `QT_QPA_PLATFORM=offscreen`.
`python desktop/main.py --demo` uses a separate demo directory.
`--data-dir PATH` isolates test storage; `--smoke-test` visits every screen and exits.

## Windows builds

`.github/workflows/build-windows.yml` runs on Windows for desktop changes, PRs,
manual dispatch, and version tags. It runs storage and GUI tests, builds a one-file
PrintTrack.exe, launches and relaunches the actual EXE, then uploads
PrintTrack-Windows-x64.zip and SHA256SUMS.txt. A `v*` tag creates a GitHub Release.
Normal app startup does not require Python, Qt, or an internet connection.

## Data integrity

One human-readable `inventory.json` snapshot holds all entities and append-only
inventory movements. Quantities are derived, never directly edited. An OS-backed
portalocker lock serializes reads and writes across processes. Each mutation
reloads state under the lock, validates, backs up, fsyncs a pending snapshot,
then atomically replaces the current snapshot. An interrupted commit replays the
validated journal at next access. Backups precede every change and startup;
latest 60 automatic copies and all manual copies are retained.

Normal restore merges saved entity cards and adds compensating movements to
restore balances while retaining all existing movement history. Emergency recovery
of an unreadable file preserves damaged originals alongside the restored snapshot.
Transactions snapshot department, room, printer and evidence at issue time.
Changing a printer model or cartridge identity invalidates compatibility records.
Compatibility starts empty, and requires evidence entered by a responsible user.

## Scope and limits

The application has no expiry or licence enforcement. Old `license.json` files
are ignored. In Settings, users can copy their complete current inventory and
backup history to a new JSON location, or select an existing inventory without
merging. The selected absolute path is stored per workstation in
`%LOCALAPPDATA%/PrintTrack/settings.json`. Existing destinations are never
replaced by relocation, and the original inventory and backups remain intact.
If the selected file is missing or offline, startup fails visibly and offers file
selection instead of silently creating a new local database. Network/UNC paths
are stored as paths, not copied into a local cache. An explicit `--data-dir`
argument overrides the saved path. An explicitly selected existing inventory
does not receive automatic catalogue merging on restart. Network/UNC paths
are accepted with normal operating-system filesystem permissions. Actual SMB/NAS
concurrent use and interrupted-network durability have not been validated.
The web/PostgreSQL variant remains the supported architecture for multiple
simultaneous clients; desktop-to-server migration requires a separate importer.

Single workstation, local filesystem. JSON is not encrypted or cryptographically
signed. Windows account/filesystem permissions govern access. History is protected
against application deletion, not deliberate external file editing. No network
printer discovery, SNMP monitoring, patient records, roles or authentication.
Reports use UTC month boundaries and show dates in the computer's local timezone.
CSV formula prefixes are escaped for safe opening in spreadsheets. CSV imports of
movements and compatibility are intentionally unavailable; enter them via validated
forms. Automatic backups are full snapshots, so storage scales with history size.
The executable is unsigned. A Windows build is successful only when its workflow
and actual EXE smoke test have passed; Linux tests alone do not establish that.
