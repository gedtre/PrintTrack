"""PrintTrack Desktop entry point. No network services required."""
import argparse
import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QTranslator, QLibraryInfo
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from printtrack.store import Store, ValidationError, data_dir, demo_store
from printtrack.ui import Window


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
    try:
        store = demo_store(directory) if args.demo else Store(directory)
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
            store = Store.recover_backup(directory, path)
        except (OSError, ValueError) as error:
            QMessageBox.critical(None, 'Atkūrimas nepavyko', str(error))
            return 1
    window = Window(store)
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
