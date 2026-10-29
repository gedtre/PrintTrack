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
from printtrack.storage_location import default_config_path, selected_file, open_existing


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
    config_path = (args.data_dir / 'settings.json') if args.data_dir else default_config_path()
    directory = args.data_dir or (data_dir().parent / 'demo' if args.demo else data_dir())
    filename = 'inventory.json'
    try:
        chosen = None if args.demo or args.data_dir else selected_file(config_path)
        if chosen:
            directory, filename = chosen.parent, chosen.name
        initial = None if args.demo else bundled_initial_data()
        if args.demo:
            store = demo_store(directory)
        elif chosen:
            store = Store(directory, filename=filename, create=False)
        else:
            store = Store(directory, initial_catalogue=initial is None)
        if not args.demo and initial and not chosen:
            apply_initial_data(store, initial)
    except (ValidationError, OSError) as e:
        if args.smoke_test:
            return 2
        box = QMessageBox()
        box.setWindowTitle('PrintTrack · Saugyklos atkūrimas')
        box.setText(str(e))
        restore = box.addButton('Atkurti kopiją…', QMessageBox.AcceptRole)
        choose = box.addButton('Pasirinkti kitą duomenų failą…', QMessageBox.ActionRole)
        box.addButton('Uždaryti', QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() == choose:
            path, _ = QFileDialog.getOpenFileName(None, 'Pasirinkti PrintTrack duomenų failą', '', 'JSON (*.json)')
            if not path:
                return 1
            try:
                store = open_existing(path, config_path, expected_demo=args.demo)
            except (OSError, ValueError) as error:
                QMessageBox.critical(None, 'Duomenų vieta', str(error))
                return 1
        elif box.clickedButton() != restore:
            return 1
        else:
            path, _ = QFileDialog.getOpenFileName(None, 'Pasirinkti atsarginę kopiją', str(directory / 'backups'), 'JSON (*.json)')
            if not path:
                return 1
            try:
                store = Store.recover_backup(directory, path, filename=filename)
            except (OSError, ValueError) as error:
                QMessageBox.critical(None, 'Atkūrimas nepavyko', str(error))
                return 1
    window = Window(store, config_path=None if args.demo else config_path)
    window.show()
    if args.smoke_test:
        def smoke():
            try:
                # Exercise the actual packaged PNG decoder and Qt display path.
                import tempfile
                from PIL import Image
                from PySide6.QtGui import QPixmap
                from printtrack.images import photo_png
                with tempfile.TemporaryDirectory(prefix='printtrack-photo-') as temporary:
                    photo = Path(temporary) / 'transparent-printer.png'
                    Image.new('RGBA', (960, 960), (40, 50, 60, 128)).save(photo)
                    pix = QPixmap()
                    assert pix.loadFromData(photo_png(photo), 'PNG')
                    assert pix.width() == 640 and pix.height() == 640
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
