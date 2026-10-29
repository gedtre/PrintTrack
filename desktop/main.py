"""PrintTrack Desktop entry point. No network services required."""
import argparse
import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QTranslator, QLibraryInfo
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from printtrack.store import Store, ValidationError, data_dir, demo_store
from printtrack.ui import Window
from printtrack.initial_data import apply_initial_data, bundled_initial_data
from printtrack.licensing import Licence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--smoke-test', action='store_true')
    parser.add_argument('--screenshot', type=Path)
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName('PrintTrack Desktop')
    app.setOrganizationName('PrintTrack')
    app.setStyle('Fusion')
    app.demo_windows = []
    translator = QTranslator(app)
    translator.load('qt_lt', QLibraryInfo.path(QLibraryInfo.TranslationsPath))
    app.installTranslator(translator)
    directory = args.data_dir or (data_dir().parent / 'demo' if args.demo else data_dir())
    licence_path = directory / 'license.json' if args.data_dir else data_dir().parent / 'license.json'
    licence = Licence(licence_path)
    try:
        initial = None if args.demo else bundled_initial_data()
        if args.demo and licence.status().active:
            store = demo_store(directory)
        else:
            store = Store(directory, demo=args.demo, initial_catalogue=initial is None,
                          write_check=licence.require_active)
        store.write_check = licence.require_active
        if not args.demo:
            if initial and licence.status().active:
                apply_initial_data(store, initial)
    except (ValidationError, OSError) as e:
        if args.smoke_test:
            return 2
        box = QMessageBox()
        box.setWindowTitle('PrintTrack · Saugyklos atkūrimas')
        box.setText(str(e))
        restore = box.addButton('Atkurti kopiją…', QMessageBox.AcceptRole)
        box.addButton('Uždaryti', QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() != restore:
            return 1
        path, _ = QFileDialog.getOpenFileName(None, 'Pasirinkti atsarginę kopiją', str(directory / 'backups'), 'JSON (*.json)')
        if not path:
            return 1
        try:
            licence.require_active()
            store = Store.recover_backup(directory, path)
        except (OSError, ValueError) as error:
            QMessageBox.critical(None, 'Atkūrimas nepavyko', str(error))
            return 1
    store.write_check = licence.require_active
    window = Window(store, licence=licence, licence_notifications=not args.smoke_test)
    window.show()
    if args.smoke_test:
        def smoke():
            try:
                for i in range(10):
                    window.nav.setCurrentRow(i)
                    app.processEvents()
                assert store.read()['version'] == 1
                if args.screenshot:
                    window.nav.setCurrentRow(0)
                    app.processEvents()
                    assert window.grab().save(str(args.screenshot))
                app.exit(0)
            except Exception:
                app.exit(3)
        QTimer.singleShot(500, smoke)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
