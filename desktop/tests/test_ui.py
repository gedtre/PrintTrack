from PySide6.QtWidgets import QLineEdit, QTableWidget
from printtrack.store import Store, demo_store
from printtrack.ui import Window, RecordDialog


def test_all_pages_and_themes(qtbot, tmp_path):
    w = Window(demo_store(tmp_path))
    qtbot.addWidget(w)
    for size in [(1366, 768), (1920, 1080)]:
        w.resize(*size)
        w.show()
        for theme in ['Šviesi', 'Tamsi']:
            w.store.set_theme(theme)
            for i in range(10):
                w.nav.setCurrentRow(i)
                w.refresh()
                assert w.page_area.widget() is not None
                assert w.heading.text()
    w.close()


def test_forms_and_search(qtbot, tmp_path):
    store = demo_store(tmp_path)
    window = Window(store)
    qtbot.addWidget(window)
    for kind in ['rooms', 'printers', 'cartridges', 'compatibility']:
        dialog = RecordDialog(window, kind, store.read())
        qtbot.addWidget(dialog)
        assert dialog.values() is not None
    window.nav.setCurrentRow(1)
    table = window.page_area.widget().findChild(QTableWidget)
    search = window.page_area.widget().findChild(QLineEdit)
    search.setText('NERASTAS-SPAUSDINTUVAS')
    assert table.isRowHidden(0)
    search.clear()
    assert not table.isRowHidden(0)
