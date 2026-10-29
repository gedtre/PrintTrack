from __future__ import annotations

import base64
import html
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSize, QEvent
from shiboken6 import isValid
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap, QPen
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QScrollArea, QSpinBox, QStackedWidget,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget, QStyledItemDelegate)

from .store import SCHEMAS, Store, ValidationError, demo_store, kpis, stock, usage, write_csv
from .images import photo_png
from .photo_service import isolated_photo

LABELS = {'name': 'Pavadinimas', 'department': 'Skyrius', 'floor': 'Aukštas', 'model': 'Modelis',
          'ip': 'IP adresas', 'serial': 'Serijos numeris', 'room_id': 'Kabinetas', 'status': 'Būsena',
          'image': 'Nuotrauka', 'code': 'Kasetės kodas', 'kind': 'Tipas', 'chip': 'Lustas būtinas',
          'minimum': 'Minimalus likutis', 'printer_id': 'Spausdintuvas', 'cartridge_id': 'Kasetė',
          'evidence': 'Patvirtinimo šaltinis ir atsakingas asmuo', 'verified_at': 'Patvirtinta',
          'at': 'Data', 'quantity': 'Kiekis', 'printer': 'Spausdintuvas', 'room': 'Kabinetas',
          'note': 'Dokumentas / pagrindimas', 'action': 'Veiksmas'}
KINDS = {'receipt': 'Gavimas', 'issue': 'Išdavimas', 'adjustment': 'Koregavimas', 'restore': 'Atkūrimas'}
PAGES = [('◈', 'Valdymo skydelis'), ('▣', 'Spausdintuvai'), ('▦', 'Kabinetai'), ('▤', 'Kasetės'),
         ('✓', 'Suderinamumas'), ('▥', 'Sandėlis'), ('↗', 'Kasečių išdavimas'),
         ('◷', 'Operacijų istorija'), ('▧', 'Ataskaitos'), ('⚙', 'Nustatymai')]


def button(text, callback, primary=False):
    w = QPushButton(text)
    w.setCursor(Qt.PointingHandCursor)
    w.setProperty('primary', primary)
    w.clicked.connect(callback)
    return w


def title(text, small=False):
    w = QLabel(text)
    w.setObjectName('subtitle' if small else 'sectionTitle')
    w.setWordWrap(True)
    return w


def local_date(value):
    try:
        return datetime.fromisoformat(value).astimezone().strftime('%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        return value


class NumberItem(QTableWidgetItem):
    def __lt__(self, other):
        return self.data(Qt.UserRole + 1) < other.data(Qt.UserRole + 1)


class Chart(QWidget):
    def __init__(self, values, dark=False):
        super().__init__()
        self.values = values[-8:]
        self.dark = dark
        self.setMinimumHeight(200)
        self.setAccessibleName('Išduotų kasečių skaičius pagal mėnesį')

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor('#182338' if self.dark else '#ffffff'))
        fg = QColor('#a8b7cb' if self.dark else '#64748b')
        p.setPen(fg)
        if not self.values:
            p.drawText(self.rect(), Qt.AlignCenter, 'Dar nėra išdavimo duomenų')
            return
        margin, baseline = 36, self.height() - 35
        slot = (self.width() - 2 * margin) / len(self.values)
        maximum = max(v for _, v in self.values) or 1
        for i, (label, value) in enumerate(self.values):
            x = int(margin + i * slot + slot * .2)
            h = int(value / maximum * (self.height() - 75))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor('#10b981'))
            p.drawRoundedRect(x, baseline - h, int(slot * .6), h, 5, 5)
            p.setPen(fg)
            p.drawText(x - 8, baseline + 8, int(slot * .6) + 16, 22, Qt.AlignCenter, label)
            p.drawText(x, baseline - h - 24, int(slot * .6), 22, Qt.AlignCenter, str(value))


class PhotoLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original = QPixmap()
        self.popup = QLabel(self, Qt.ToolTip)
        self.popup.setAttribute(Qt.WA_ShowWithoutActivating)
        self.popup.setStyleSheet('background: white; border: 1px solid #94a3b8; padding: 8px;')
        self.setAlignment(Qt.AlignCenter)

    def setPixmap(self, pixmap):
        self.original = QPixmap(pixmap)
        super().setPixmap(pixmap.scaled(max(1, self.width()), max(1, self.height()), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def setText(self, text):
        if hasattr(self, 'original'):
            self.original = QPixmap()
            if isValid(self.popup):
                self.popup.hide()
        super().setText(text)

    def resizeEvent(self, event):
        if not self.original.isNull():
            super().setPixmap(self.original.scaled(max(1, self.width()), max(1, self.height()), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        super().resizeEvent(event)

    def enterEvent(self, event):
        if not self.original.isNull() and isValid(self.popup):
            pix = self.original.scaled(520, 520, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.popup.setPixmap(pix)
            self.popup.adjustSize()
            from PySide6.QtGui import QCursor
            point = QCursor.pos()
            screen = self.screen().availableGeometry()
            point.setX(max(screen.left(), min(point.x() + 18, screen.right() - self.popup.width())))
            point.setY(max(screen.top(), min(point.y() + 18, screen.bottom() - self.popup.height())))
            self.popup.move(point)
            self.popup.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if isValid(self.popup):
            self.popup.hide()
        super().leaveEvent(event)

    def hideEvent(self, event):
        if isValid(self.popup):
            self.popup.hide()
        super().hideEvent(event)


class PhotoDelegate(QStyledItemDelegate):
    """Paint table thumbnails as icons; avoid child-widget destruction on refresh."""
    def __init__(self, table):
        super().__init__(table)
        self.table = table
        self.popup = QLabel(table.window(), Qt.ToolTip)
        self.popup.setAttribute(Qt.WA_ShowWithoutActivating)
        self.popup.setStyleSheet('background: white; border: 1px solid #94a3b8; padding: 8px;')
        table.setMouseTracking(True)
        table.viewport().installEventFilter(self)
        popup = self.popup
        table.destroyed.connect(lambda: popup.deleteLater() if isValid(popup) else None)

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Leave, QEvent.Hide, QEvent.MouseButtonPress):
            if isValid(self.popup):
                self.popup.hide()
        elif event.type() == QEvent.MouseMove:
            index = self.table.indexAt(event.position().toPoint())
            icon = index.data(Qt.DecorationRole) if index.isValid() and index.column() == 0 else None
            if isinstance(icon, QIcon) and not icon.isNull():
                pix = icon.pixmap(520, 520)
                self.popup.setPixmap(pix)
                self.popup.adjustSize()
                point = self.table.viewport().mapToGlobal(event.position().toPoint())
                screen = self.table.screen().availableGeometry()
                point.setX(max(screen.left(), min(point.x() + 18, screen.right() - self.popup.width())))
                point.setY(max(screen.top(), min(point.y() + 18, screen.bottom() - self.popup.height())))
                self.popup.move(point)
                self.popup.show()
            else:
                self.popup.hide()
        return super().eventFilter(watched, event)


class ImageField(QWidget):
    """Keep encoded image data outside QLineEdit's 32,767-character limit."""
    def __init__(self, value=''):
        super().__init__()
        self.value = value

    def text(self):
        return self.value

    def setText(self, value):
        self.value = value

    def clear(self):
        self.value = ''


class RecordDialog(QDialog):
    def __init__(self, parent, kind, state, existing=None, image_loader=None):
        super().__init__(parent)
        self.kind, self.fields = kind, {}
        self.setWindowTitle('Redaguoti įrašą' if existing else 'Naujas įrašas')
        self.setMinimumWidth(540)
        self.resize(580, 580)
        layout = QVBoxLayout(self)
        layout.addWidget(title(self.windowTitle()))
        if kind == 'compatibility':
            layout.addWidget(title('Patvirtinkite tik patikrinę gamintojo dokumentaciją ar atlikę bandymą. Panašus kodas nėra suderinamumo įrodymas.', True))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        form = QFormLayout(body)
        form.setSpacing(16)
        existing = existing or {}
        for field in SCHEMAS[kind]:
            val = existing.get(field, '')
            if field in ['room_id', 'printer_id', 'cartridge_id']:
                w = QComboBox()
                target = {'room_id': 'rooms', 'printer_id': 'printers', 'cartridge_id': 'cartridges'}[field]
                w.addItem('— Pasirinkite —', '')
                for r in state[target]:
                    label = (r['department'] + ' · ' + r['name']) if target == 'rooms' else (r['code'] + ' · ' + r['kind'] + ' · ' + r['chip']) if target == 'cartridges' else r['name'] + ' · ' + r['model']
                    w.addItem(label, r['id'])
                w.setCurrentIndex(max(0, w.findData(val)))
            elif field in ['status', 'kind', 'chip']:
                w = QComboBox()
                w.addItems({'status': ['Nepriskirtas', 'Veikia', 'Remontas', 'Nenaudojamas'], 'kind': ['Originali', 'Suderinama'], 'chip': ['Nežinoma', 'Taip', 'Ne']}[field])
                if val:
                    w.setCurrentText(val)
            elif field == 'minimum':
                w = QSpinBox()
                w.setRange(0, 1000000)
                w.setValue(int(val or 0))
            elif field == 'image':
                w = ImageField(str(val))
                w.setVisible(False)
                box = QWidget()
                row = QHBoxLayout(box)
                row.setContentsMargins(0, 0, 0, 0)
                preview = PhotoLabel('Nuotrauka įkelta' if val else 'Neįkelta')
                preview.setFixedSize(150, 95)
                if val:
                    pix = QPixmap()
                    try:
                        pix.loadFromData(image_loader(val) if image_loader else base64.b64decode(val))
                    except (ValueError, OSError):
                        pass
                    if not pix.isNull():
                        preview.setPixmap(pix)
                row.addWidget(preview)
                row.addWidget(button('Pasirinkti…', lambda checked=False, field=w, label=preview: self.pick_image(field, label)))
                row.addWidget(button('Pašalinti', lambda checked=False, field=w, label=preview: (field.clear(), label.setText('Neįkelta'))))
                form.addRow(LABELS[field], box)
                self.fields[field] = w
                continue
            else:
                w = QLineEdit(str(val))
                w.setMaxLength(2000)
                if field == 'evidence':
                    w.setPlaceholderText('Pvz., gamintojo vadovas, psl. 12; V. Pavardenis')
            w.setAccessibleName(LABELS[field])
            self.fields[field] = w
            form.addRow(LABELS[field], w)
        scroll.setWidget(body)
        layout.addWidget(scroll)
        controls = QDialogButtonBox()
        controls.addButton('Atšaukti', QDialogButtonBox.RejectRole)
        controls.addButton('Išsaugoti', QDialogButtonBox.AcceptRole)
        controls.rejected.connect(self.reject)
        controls.accepted.connect(self.accept)
        layout.addWidget(controls)

    def pick_image(self, field, label):
        self.setEnabled(False)
        try:
            content = isolated_photo()
            if content is not None:
                self.apply_photo(content, field, label)
        except (ValidationError, RuntimeError) as error:
            QMessageBox.warning(self, 'Nuotrauka', str(error))
        finally:
            self.setEnabled(True)
            self.activateWindow()

    def load_photo(self, path, field, label):
        try:
            content = isolated_photo(path)
            self.apply_photo(content, field, label)
        except (ValidationError, RuntimeError) as error:
            QMessageBox.warning(self, 'Nuotrauka', str(error))

    def apply_photo(self, content, field, label):
        try:
            pix = QPixmap()
            if not pix.loadFromData(content, 'PNG'):
                raise ValidationError('Nepavyko parodyti nuotraukos. Ankstesnė nuotrauka nepakeista.')
        except (ValidationError, RuntimeError) as error:
            QMessageBox.warning(self, 'Nuotrauka', str(error))
            return
        field.setText(base64.b64encode(content).decode())
        label.setPixmap(pix if isinstance(label, PhotoLabel) else pix.scaled(140, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        label.setToolTip('Nuotrauka paruošta. Spauskite „Išsaugoti“.')

    def values(self):
        result = {}
        for key, w in self.fields.items():
            result[key] = w.currentData() if key.endswith('_id') else w.currentText() if isinstance(w, QComboBox) else w.value() if isinstance(w, QSpinBox) else w.text()
        return result


class Window(QMainWindow):
    def __init__(self, store, config_path=None):
        super().__init__()
        self.config_path = config_path
        self.store = store
        self.state = store.read()
        self.current = 0
        self.report_rows = []
        self.setWindowTitle('PrintTrack Desktop' + (' · DEMO' if self.state['demo'] else ''))
        self.setMinimumSize(1040, 650)
        self.resize(1366, 850)
        icon = Path(__file__).parent / 'assets' / 'icon.png'
        self.setWindowIcon(QIcon(str(icon)))
        root = QWidget()
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(235)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 28, 18, 22)
        brand = QLabel('◈  PrintTrack')
        brand.setObjectName('brand')
        side.addWidget(brand)
        sub = QLabel('SPAUSDINIMO APSKAITA')
        sub.setObjectName('brandSub')
        side.addWidget(sub)
        side.addSpacing(28)
        self.nav = QListWidget()
        self.nav.setObjectName('navigation')
        for icon, name in PAGES:
            item = QListWidgetItem(f'{icon}   {name}')
            item.setSizeHint(QSize(195, 44))
            self.nav.addItem(item)
        self.nav.setCurrentRow(0)
        self.nav.currentRowChanged.connect(self.navigate)
        side.addWidget(self.nav, 1)
        foot = QLabel('●  Vietinė saugykla\n\nDEMO aplinka' if self.state['demo'] else '●  Vietinė saugykla\n\nDuomenys šiame kompiuteryje')
        foot.setObjectName('brandSub')
        side.addWidget(foot)
        outer.addWidget(sidebar)
        content = QWidget()
        area = QVBoxLayout(content)
        area.setContentsMargins(30, 24, 30, 18)
        area.setSpacing(16)
        header = QHBoxLayout()
        self.heading = title(PAGES[0][1])
        self.heading.setObjectName('pageTitle')
        header.addWidget(self.heading, 1)
        header.addWidget(QLabel('DEMO · MOKOMIEJI DUOMENYS' if self.state['demo'] else 'PrintTrack Desktop  ·  1.0'))
        header.addWidget(button('↻  Atnaujinti', self.refresh))
        area.addLayout(header)
        self.hint = title('Aiški apskaita. Patikrintas suderinamumas. Kontroliuojami likučiai.', True)
        area.addWidget(self.hint)
        self.page_area = QScrollArea()
        self.page_area.setWidgetResizable(True)
        self.page_area.setFrameShape(QFrame.NoFrame)
        area.addWidget(self.page_area, 1)
        self.status = QLabel('')
        self.status.setObjectName('subtitle')
        area.addWidget(self.status)
        outer.addWidget(content, 1)
        self.setCentralWidget(root)
        self.apply_theme()
        self.refresh()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_revision)
        self.timer.start(5000)

    def check_revision(self):
        try:
            latest = self.store.read()
            if latest['revision'] != self.state['revision']:
                self.refresh()
        except (OSError, ValidationError):
            self.status.setText('Nepavyko perskaityti saugyklos. Patikrinkite duomenų aplanką.')

    def apply_theme(self):
        dark = self.state['preferences']['theme'] == 'Tamsi'
        bg, card, fg, muted, border = ('#101827', '#182338', '#edf2fa', '#a8b7cb', '#2a3950') if dark else ('#f6f8fb', '#ffffff', '#18243b', '#64748b', '#e3e8ef')
        self.setStyleSheet(f'''
            QWidget {{font-family: 'Segoe UI', 'Noto Sans', sans-serif; font-size: 13px; color: {fg};}}
            QMainWindow, QScrollArea, QScrollArea > QWidget > QWidget {{background: {bg};}}
            QDialog {{background: {bg};}}
            #sidebar {{background: #101d33;}}
            #brand {{font-size: 25px; font-weight: 700; color: white;}}
            #brandSub {{color: #95a8c5; font-size: 11px; line-height: 1.5;}}
            #navigation {{background: transparent; border: none; color: #b8c6db; outline: none;}}
            #navigation::item {{padding-left: 12px; border-radius: 8px; margin-bottom: 3px;}}
            #navigation::item:hover {{background: #1b2f4d;}}
            #navigation::item:selected {{background: #24466a; color: #ffffff;}}
            #pageTitle {{font-size: 27px; font-weight: 700;}}
            #sectionTitle {{font-size: 17px; font-weight: 600;}}
            #subtitle {{color: {muted};}}
            #card {{background: {card}; border: 1px solid {border}; border-radius: 12px;}}
            #kpi {{font-size: 31px; font-weight: 700; color: #10b981;}}
            QPushButton {{background: {card}; border: 1px solid {border}; border-radius: 7px; padding: 9px 14px; font-weight: 600;}}
            QPushButton:hover {{border-color: #10b981; color: #10b981;}}
            QPushButton:pressed {{background: #25465a; color: white;}}
            QPushButton[primary="true"] {{background: #0d9473; color: white; border-color: #0d9473;}}
            QPushButton[primary="true"]:hover {{background: #087f61;}}
            QLineEdit, QSpinBox, QComboBox, QTextEdit {{background: {card}; border: 1px solid {border}; border-radius: 6px; padding: 8px; min-height: 20px;}}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{border-color: #10b981;}}
            QTableWidget {{background: {card}; alternate-background-color: {bg}; border: 1px solid {border}; border-radius: 9px; gridline-color: {border}; selection-background-color: #225e77; selection-color: white;}}
            QHeaderView::section {{background: {bg}; color: {muted}; border: none; border-bottom: 1px solid {border}; padding: 12px 9px; font-weight: 600;}}
            QTableWidget::item {{padding: 8px; border-bottom: 1px solid {border};}}
            QScrollBar:vertical {{background: {bg}; width: 10px;}}
            QScrollBar::handle:vertical {{background: {border}; border-radius: 4px; min-height: 30px;}}
            QToolTip {{background: {card}; color: {fg}; border: 1px solid {border};}}
        ''')

    def guard(self, action):
        try:
            result = action()
            self.refresh()
            return result
        except (ValidationError, OSError, ValueError, KeyError) as e:
            QMessageBox.warning(self, 'Nepavyko atlikti veiksmo', str(e))
            return None

    def navigate(self, index):
        self.current = index
        self.refresh()

    def refresh(self):
        try:
            self.state = self.store.read()
        except (ValidationError, OSError) as e:
            QMessageBox.critical(self, 'Duomenų saugykla', str(e))
            return
        self.apply_theme()
        self.heading.setText(PAGES[self.current][1])
        page = QWidget()
        self.layout = QVBoxLayout(page)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(18)
        if self.current == 0:
            self.dashboard()
        elif self.current in [1, 2, 3, 4]:
            self.records({1: 'printers', 2: 'rooms', 3: 'cartridges', 4: 'compatibility'}[self.current])
        elif self.current == 5:
            self.warehouse()
        elif self.current == 6:
            self.issue_page()
        elif self.current == 7:
            self.history()
        elif self.current == 8:
            self.reports()
        else:
            self.settings()
        self.page_area.setWidget(page)
        self.status.setText(f'{"DEMO · " if self.state["demo"] else ""}Duomenų failas: {self.store.path}  ·  Versija {self.state["revision"]}')

    def card(self, heading):
        card = QFrame()
        card.setObjectName('card')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.addWidget(title(heading))
        self.layout.addWidget(card)
        return layout

    def make_table(self, fields, rows, height=350):
        table = QTableWidget(0, len(fields))
        table.setHorizontalHeaderLabels([LABELS.get(f, f) for f in fields])
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setMinimumHeight(height)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        for row in rows:
            n = table.rowCount()
            table.insertRow(n)
            for j, field in enumerate(fields):
                val = row.get(field, '')
                if field.endswith('_id'):
                    target = {'room_id': 'rooms', 'printer_id': 'printers', 'cartridge_id': 'cartridges'}.get(field)
                    record = next((r for r in self.state.get(target, []) if r['id'] == val), {})
                    val = (record.get('department', '') + ' · ' + record.get('name', '')) if target == 'rooms' and record else (record.get('code', '') + ' · ' + record.get('kind', '') + ' · ' + record.get('chip', '')) if target == 'cartridges' and record else record.get('name', 'Nepriskirta')
                if field in ['at', 'verified_at']:
                    val = local_date(val)
                if field == 'kind':
                    val = KINDS.get(val, val)
                item = NumberItem(str(val)) if isinstance(val, (int, float)) else QTableWidgetItem(str(val))
                if field == 'image':
                    pix = QPixmap()
                    try:
                        pix.loadFromData(self.store.image_bytes(val))
                    except (ValueError, TypeError, OSError):
                        pass
                    item.setText('Nėra' if pix.isNull() else '')
                    if not pix.isNull():
                        item.setIcon(QIcon(pix))
                item.setData(Qt.UserRole, row.get('id', ''))
                if isinstance(val, (int, float)):
                    item.setData(Qt.UserRole + 1, val)
                item.setToolTip(('Modelio nuotrauka' if val else 'Nuotrauka neįkelta') if field == 'image' else str(val))
                if field in ['status', 'Likutis', 'Būsena']:
                    color = '#ef6161' if str(val) in ['Nėra', 'Remontas'] else '#d49619' if str(val) in ['Mažas likutis', 'Nenaudojamas'] else '#0eaa80'
                    item.setForeground(QColor(color))
                table.setItem(n, j, item)
            table.setRowHeight(n, 72 if 'image' in fields else 46)
        if 'image' in fields:
            table.setIconSize(QSize(90, 60))
            table.setItemDelegateForColumn(0, PhotoDelegate(table))
        table.resizeColumnsToContents()
        for j in range(len(fields)):
            table.setColumnWidth(j, min(280, max(110, table.columnWidth(j))))
        table.setSortingEnabled(True)
        return table

    def search_bar(self, table, filters=None):
        row = QHBoxLayout()
        search = QLineEdit()
        search.setPlaceholderText('Ieškoti visuose stulpeliuose…')
        row.addWidget(search, 1)
        box = QComboBox() if filters else None
        if box:
            box.addItem('Visos būsenos')
            box.addItems(filters)
            row.addWidget(box)
        def apply():
            query = search.text().casefold()
            selected = box.currentText() if box and box.currentIndex() else ''
            for i in range(table.rowCount()):
                texts = [table.item(i, j).text() for j in range(table.columnCount())]
                table.setRowHidden(i, query not in ' '.join(texts).casefold() or bool(selected and selected not in texts))
        search.textChanged.connect(apply)
        if box:
            box.currentIndexChanged.connect(apply)
        self.layout.addLayout(row)
        return row

    def dashboard(self):
        grid = QHBoxLayout()
        counts = kpis(self.state)
        for label, key in [('Spausdintuvai', 'printers'), ('Kasetės sandėlyje', 'stock'), ('Reikia papildyti', 'low'), ('Išduota šį mėnesį', 'issued')]:
            card = QFrame()
            card.setObjectName('card')
            col = QVBoxLayout(card)
            col.setContentsMargins(20, 18, 20, 18)
            col.addWidget(title(label, True))
            number = QLabel(str(counts[key]))
            number.setObjectName('kpi')
            col.addWidget(number)
            grid.addWidget(card)
        self.layout.addLayout(grid)
        c = self.card('Kasečių naudojimas pagal mėnesį')
        c.addWidget(Chart(usage(self.state), self.state['preferences']['theme'] == 'Tamsi'))
        lows = [dict(code=c['code'], Likutis=stock(self.state, c['id']), minimum=c['minimum']) for c in self.state['cartridges'] if c['minimum'] > 0 and stock(self.state, c['id']) <= c['minimum']]
        self.layout.addWidget(title('Likučių įspėjimai'))
        if lows:
            self.layout.addWidget(self.make_table(['code', 'Likutis', 'minimum'], lows, 140))
        else:
            self.layout.addWidget(title('Aktyvių įspėjimų nėra. Minimalų likutį nustatykite kasetės kortelėje.', True))
        self.layout.addWidget(title('Naujausios operacijos'))
        self.layout.addWidget(self.make_table(['at', 'kind', 'code', 'quantity', 'printer'], list(reversed(self.state['movements'][-5:])), 180))

    def selected_id(self, table):
        if not isValid(table):
            return None
        row = table.currentRow()
        item = table.item(row, 0) if row >= 0 else None
        return item.data(Qt.UserRole) if item is not None else None

    def edit_record(self, kind, row_id=None):
        existing = next((r for r in self.state[kind] if r['id'] == row_id), None)
        dialog = RecordDialog(self, kind, self.state, existing, image_loader=self.store.image_bytes)
        # Keep form open when validation fails so entered data is not lost.
        while dialog.exec() == QDialog.Accepted:
            try:
                self.store.save(kind, dialog.values(), row_id)
                self.refresh()
                return
            except (ValidationError, OSError) as e:
                QMessageBox.warning(dialog, 'Patikrinkite įrašą', str(e))

    def records(self, kind):
        fields = (['image'] if kind == 'printers' else []) + [f for f in SCHEMAS[kind] if f != 'image']
        if kind == 'compatibility':
            fields.append('verified_at')
            self.layout.addWidget(title('Rodomi tik aiškiai patvirtinti ryšiai. Katalogas pats savaime suderinamumo nepatvirtina.', True))
        if kind == 'printers':
            self.layout.addWidget(title('Pakeitus modelį, jo suderinamumo patvirtinimai panaikinami ir turi būti patikrinti iš naujo.', True))
            self.layout.addWidget(title('Pradinės kortelės įvestos po vieną kiekvienam modeliui. Būsena „Nepriskirtas“ nereiškia patvirtinto įrenginių kiekio. Priskirkite kabinetą ir įrašykite tikro įrenginio serijos numerį. Kasečių kodai iš pateiktos lentelės nėra patvirtintas suderinamumas.', True))
        if kind == 'cartridges':
            self.layout.addWidget(title('Pradinis katalogas nepatikrintas. Pakeitus kodą, tipą ar lustą, susiję patvirtinimai panaikinami.', True))
        rows = [dict(r) for r in self.state[kind]]
        if kind == 'printers':
            fields.append('Kasečių kodai (šaltinis)')
            for r in rows:
                r['Kasečių kodai (šaltinis)'] = r.get('source_cartridge_codes', '') or 'Nenurodyta'
        if kind == 'rooms':
            fields.append('Spausdintuvų')
            for r in rows:
                r['Spausdintuvų'] = sum(p['room_id'] == r['id'] for p in self.state['printers'])
        table = self.make_table(fields, rows)
        toolbar = self.search_bar(table, ['Nepriskirtas', 'Veikia', 'Remontas', 'Nenaudojamas'] if kind == 'printers' else None)
        toolbar.addWidget(button('+  Naujas įrašas', lambda: self.edit_record(kind), True))
        toolbar.addWidget(button('Redaguoti', lambda: self.edit_selected(kind, table)))
        if kind == 'compatibility':
            toolbar.addWidget(button('Atšaukti patvirtinimą', lambda: self.revoke_selected(table)))
        table.doubleClicked.connect(lambda: self.edit_selected(kind, table))
        self.layout.addWidget(table, 1)
        if kind in ['printers', 'cartridges']:
            preview = PhotoLabel('Pasirinkite įrašą, kad pamatytumėte jo nuotrauką.')
            preview.setMinimumHeight(100)
            preview.setMaximumHeight(160)
            preview.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            source_label = QLabel()
            source_label.setTextFormat(Qt.PlainText)
            source_label.setWordWrap(True)
            def image_preview():
                r = next((r for r in self.state[kind] if r['id'] == self.selected_id(table)), {})
                source_label.setText('Nuotraukos šaltinis: ' + r['image_source'] if r.get('image_source') else '')
                pix = QPixmap()
                try:
                    pix.loadFromData(self.store.image_bytes(r.get('image', '')))
                except (ValueError, OSError):
                    pass
                if pix.isNull():
                    preview.clear()
                    preview.setText('Nuotrauka neįkelta.')
                else:
                    preview.setPixmap(pix)
            table.itemSelectionChanged.connect(image_preview)
            self.layout.addWidget(preview)
            self.layout.addWidget(source_label)
        if not rows:
            self.layout.addWidget(title('Įrašų dar nėra. Pradėkite nuo „Naujas įrašas“.', True))

    def edit_selected(self, kind, table):
        row_id = self.selected_id(table)
        if row_id:
            self.edit_record(kind, row_id)
        else:
            QMessageBox.information(self, 'Pasirinkimas', 'Pirmiausia pasirinkite lentelės eilutę.')

    def revoke_selected(self, table):
        row_id = self.selected_id(table)
        if row_id and self.confirm('Atšaukti pasirinktą suderinamumo patvirtinimą?'):
            self.guard(lambda: self.store.revoke(row_id))

    def warehouse(self):
        rows = []
        for c in self.state['cartridges']:
            count = stock(self.state, c['id'])
            rows.append(dict(c, Likutis=count, Būsena='Nėra' if count == 0 else 'Mažas likutis' if count <= c['minimum'] else 'Pakanka'))
        table = self.make_table(['code', 'kind', 'chip', 'Likutis', 'minimum', 'Būsena'], rows)
        toolbar = self.search_bar(table, ['Nėra', 'Mažas likutis', 'Pakanka'])
        toolbar.addWidget(button('+  Priimti kasetes', lambda: self.movement_dialog('receipt', self.selected_id(table)), True))
        toolbar.addWidget(button('Koreguoti likutį', lambda: self.movement_dialog('adjustment', self.selected_id(table))))
        self.layout.addWidget(table, 1)
        self.layout.addWidget(title('Likučiai apskaičiuojami iš operacijų. Koregavimui įveskite pokytį, pvz., −1 arba 2, ir pagrindimą.', True))

    def movement_dialog(self, kind, selected=None):
        dialog = QDialog(self)
        dialog.setWindowTitle('Kasečių gavimas' if kind == 'receipt' else 'Likučio koregavimas')
        dialog.setMinimumWidth(500)
        layout = QFormLayout(dialog)
        cartridges = QComboBox()
        for c in self.state['cartridges']:
            cartridges.addItem(c['code'] + ' · ' + c['kind'] + ' · ' + c['chip'], c['id'])
        cartridges.setCurrentIndex(max(0, cartridges.findData(selected)))
        qty = QSpinBox()
        qty.setRange(1 if kind == 'receipt' else -1000000, 1000000)
        qty.setValue(1)
        note = QLineEdit()
        note.setPlaceholderText('Dokumento Nr. arba koregavimo priežastis')
        layout.addRow('Kasetė', cartridges)
        layout.addRow('Kiekis' if kind == 'receipt' else 'Likučio pokytis (+ / −)', qty)
        layout.addRow('Pagrindimas', note)
        controls = QDialogButtonBox()
        controls.addButton('Atšaukti', QDialogButtonBox.RejectRole)
        controls.addButton('Įrašyti operaciją', QDialogButtonBox.AcceptRole)
        controls.rejected.connect(dialog.reject)
        controls.accepted.connect(dialog.accept)
        layout.addRow(controls)
        while dialog.exec() == QDialog.Accepted:
            try:
                self.store.movement(kind, cartridges.currentData(), qty.value(), note=note.text())
                self.refresh()
                return
            except (ValidationError, OSError) as e:
                QMessageBox.warning(dialog, 'Operacija neįrašyta', str(e))

    def issue_page(self):
        card = self.card('Išduoti kasetę spausdintuvui')
        card.addWidget(title('Galima pasirinkti tik patvirtintas kasetes. Likutis pakartotinai tikrinamas išsaugant operaciją.', True))
        form = QFormLayout()
        printers = QComboBox()
        printers.addItem('— Pasirinkite spausdintuvą —', '')
        for p in self.state['printers']:
            if p['status'] == 'Veikia':
                printers.addItem(p['name'] + ' · ' + p['model'], p['id'])
        cartridges = QComboBox()
        evidence = QLabel('Pirmiausia pasirinkite spausdintuvą.')
        evidence.setWordWrap(True)
        qty = QSpinBox()
        qty.setRange(1, 1000000)
        note = QLineEdit()
        note.setPlaceholderText('Išdavimo dokumentas arba pagrindimas')
        def choices():
            cartridges.clear()
            permitted = {c['cartridge_id'] for c in self.state['compatibility'] if c['printer_id'] == printers.currentData()}
            for c in self.state['cartridges']:
                if c['id'] in permitted:
                    cartridges.addItem(f'{c["code"]} · {c["kind"]} · lustas: {c["chip"]} · likutis {stock(self.state, c["id"])}', c['id'])
            if not permitted:
                evidence.setText('Patvirtintų kasečių nėra. Atverkite „Suderinamumas“ ir pridėkite patvirtinimą.')
            show_evidence()
        def show_evidence():
            c = next((c for c in self.state['compatibility'] if c['printer_id'] == printers.currentData() and c['cartridge_id'] == cartridges.currentData()), None)
            if c:
                evidence.setText('Patvirtinta: ' + c['evidence'] + ' · ' + local_date(c['verified_at']))
        printers.currentIndexChanged.connect(choices)
        cartridges.currentIndexChanged.connect(show_evidence)
        form.addRow('Spausdintuvas', printers)
        form.addRow('Patvirtinta kasetė', cartridges)
        form.addRow('Patvirtinimas', evidence)
        form.addRow('Kiekis', qty)
        form.addRow('Pagrindimas', note)
        card.addLayout(form)
        def issue():
            if not cartridges.currentData():
                QMessageBox.warning(self, 'Patikrinkite pasirinkimą', 'Pasirinkite patvirtintą kasetę.')
                return
            if self.confirm(f'Išduoti {qty.value()} vnt.? Operacija bus išsaugota istorijoje.'):
                self.guard(lambda: self.store.movement('issue', cartridges.currentData(), qty.value(), printers.currentData(), note.text()))
        card.addWidget(button('↗  Patvirtinti išdavimą', issue, True))
        self.layout.addStretch()

    def history(self):
        table = self.make_table(['at', 'kind', 'code', 'quantity', 'printer', 'department', 'room', 'note', 'evidence'], list(reversed(self.state['movements'])))
        toolbar = self.search_bar(table, list(KINDS.values()))
        toolbar.addWidget(button('Eksportuoti CSV', lambda: self.export('movements')))
        self.layout.addWidget(table, 1)
        self.layout.addWidget(title('Operacijos netrinamos. Klaidos taisomos nauja koregavimo operacija. Skyriaus ir kabineto duomenys išsaugomi išdavimo metu.', True))
        self.layout.addWidget(title('Pakeitimų žurnalas'))
        self.layout.addWidget(self.make_table(['at', 'action'], list(reversed(self.state['events'])), 180))

    def reports(self):
        form = QGridLayout()
        group = QComboBox()
        for label, key in [('Mėnuo', 'month'), ('Skyrius', 'department'), ('Kabinetas', 'room'), ('Spausdintuvas', 'printer'), ('Kasetė', 'code')]:
            group.addItem(label, key)
        filters = {}
        movements = [m for m in self.state['movements'] if m['kind'] == 'issue']
        for i, (label, key) in enumerate([('Mėnuo', 'month'), ('Skyrius', 'department'), ('Kabinetas', 'room'), ('Spausdintuvas', 'printer'), ('Kasetė', 'cartridge')]):
            box = QComboBox()
            box.addItem('Visi', '')
            values = sorted({m['at'][:7] if key == 'month' else m.get('code' if key == 'cartridge' else key, '') for m in movements} - {''})
            for v in values:
                box.addItem(v, v)
            filters[key] = box
            form.addWidget(QLabel(label), (i // 3) * 2, i % 3)
            form.addWidget(box, (i // 3) * 2 + 1, i % 3)
        self.layout.addLayout(form)
        row = QHBoxLayout()
        row.addWidget(QLabel('Grupuoti pagal'))
        row.addWidget(group, 1)
        row.addWidget(button('Eksportuoti ataskaitą', self.export_report))
        self.layout.addLayout(row)
        table = self.make_table(['Grupė', 'Išduota'], [], 320)
        total = title('Iš viso: 0 vnt.')
        def update():
            values = usage(self.state, group.currentData(), **{k: w.currentData() for k, w in filters.items()})
            self.report_rows = [dict(Grupė=k, Išduota=v) for k, v in values]
            table.setSortingEnabled(False)
            table.setRowCount(len(values))
            for i, (k, v) in enumerate(values):
                table.setItem(i, 0, QTableWidgetItem(k))
                item = NumberItem(str(v))
                item.setData(Qt.UserRole + 1, v)
                table.setItem(i, 1, item)
            table.setSortingEnabled(True)
            total.setText(f'Iš viso: {sum(v for _, v in values)} vnt.')
        for w in [group, *filters.values()]:
            w.currentIndexChanged.connect(update)
        update()
        self.layout.addWidget(table)
        self.layout.addWidget(total)
        self.layout.addWidget(title('Ataskaitos skaičiuoja išdavimus. Filtrai taikomi kartu; naudojami išdavimo metu užfiksuoti duomenys. Mėnesiai skaičiuojami pagal UTC.', True))

    def export_report(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Išsaugoti ataskaitą', 'PrintTrack-ataskaita.csv', 'CSV (*.csv)')
        if path:
            self.guard(lambda: write_csv(path, ['Grupė', 'Išduota'], self.report_rows))

    def export(self, kind):
        path, _ = QFileDialog.getSaveFileName(self, 'Eksportuoti CSV', f'PrintTrack-{kind}.csv', 'CSV (*.csv)')
        if path:
            self.guard(lambda: self.store.export_csv(kind, path))

    def settings(self):
        location = self.card('Duomenų failo vieta')
        current_path = QLineEdit(str(self.store.path))
        current_path.setReadOnly(True)
        current_path.setAccessibleName('Dabartinis duomenų failas')
        location.addWidget(current_path)
        if not self.state['demo']:
            row = QHBoxLayout()
            row.addWidget(button('Perkelti dabartinius duomenis…', self.move_data))
            row.addWidget(button('Pasirinkti esamą duomenų failą…', self.choose_data))
            location.addLayout(row)
        location.addWidget(title('Galite pasirinkti vietinį ar tinklo aplanką, pvz., \\\\SERVERIS\\PrintTrack\\inventory.json. Tinklo vietai reikia skaitymo ir rašymo teisių. Prieš keisdami vietą uždarykite kitus programos langus. Darbas iš kelių kompiuterių vienu metu nėra patikrintas.', True))
        card = self.card('Išvaizda')
        theme = QComboBox()
        theme.addItems(['Šviesi', 'Tamsi'])
        theme.setCurrentText(self.state['preferences']['theme'])
        theme.currentTextChanged.connect(lambda value: self.guard(lambda: self.store.set_theme(value)))
        card.addWidget(theme)
        backup = self.card('Atsarginės kopijos')
        backup.addWidget(title('Automatinės kopijos kuriamos paleidžiant ir prieš kiekvieną pakeitimą. Saugoma 60 naujausių automatinių kopijų. Rankinės kopijos saugomos be apribojimo.', True))
        row = QHBoxLayout()
        row.addWidget(button('Išsaugoti kopiją…', self.backup))
        row.addWidget(button('Atkurti kopiją…', self.restore))
        row.addWidget(button('Atverti duomenų aplanką', self.open_data))
        backup.addLayout(row)
        backup.addWidget(title('Atkūrimas išsaugo visą esamą operacijų istoriją, sujungia korteles ir naujomis operacijomis atkuria kopijos likučius. Vėliau sukurtos kortelės lieka.', True))
        card = self.card('CSV importas ir eksportas')
        table = QComboBox()
        for label, key in [('Kabinetai', 'rooms'), ('Spausdintuvai', 'printers'), ('Kasetės', 'cartridges'), ('Suderinamumas (tik eksportas)', 'compatibility'), ('Operacijos (tik eksportas)', 'movements')]:
            table.addItem(label, key)
        card.addWidget(table)
        row = QHBoxLayout()
        row.addWidget(button('Eksportuoti / gauti šabloną', lambda: self.export(table.currentData())))
        row.addWidget(button('Importuoti CSV…', lambda: self.import_csv(table.currentData())))
        card.addLayout(row)
        card.addWidget(title('CSV: UTF-8, kablelio skirtukas. Pirmiausia eksportuokite šabloną. Esamas ID atnaujina įrašą, tuščias ID sukuria naują. Kabinetų ir spausdintuvų ryšiams naudojami ID. Visas importas tikrinamas prieš išsaugant.', True))
        demo = self.card('Mokomoji aplinka')
        demo.addWidget(title('DEMO duomenys saugomi atskirai ir nekeičia tikro inventoriaus.', True))
        demo.addWidget(button('Atverti DEMO langą', self.open_demo))
        self.layout.addStretch()

    def open_demo(self):
        from .store import data_dir
        try:
            demo = Window(demo_store(data_dir().parent / 'demo'))
            QApplication.instance().demo_windows.append(demo)
            demo.show()
        except (ValidationError, OSError) as e:
            QMessageBox.warning(self, 'DEMO aplinka', str(e))

    def move_data(self):
        from .storage_location import relocate
        path, _ = QFileDialog.getSaveFileName(self, 'Nauja duomenų failo vieta',
            str(self.store.path), 'PrintTrack JSON (*.json)')
        if not path or not self.confirm('Perkelti dabartinius duomenis į pasirinktą failą ir toliau dirbti ten? Senas failas ir kopijos bus išsaugoti. Esamas paskirties failas nebus perrašytas. Kitus PrintTrack langus uždarykite.'):
            return
        def move():
            self.store = relocate(self.store, path, self.config_path)
        self.guard(move)

    def choose_data(self):
        from .storage_location import open_existing
        path, _ = QFileDialog.getOpenFileName(self, 'Pasirinkti esamą PrintTrack duomenų failą',
            str(self.store.directory), 'PrintTrack JSON (*.json)')
        if not path or not self.confirm('Pereiti prie pasirinkto failo? Bus rodomi jo įrašai. Dabartiniai ir pasirinkti duomenys nebus sujungiami, dabartinis failas liks išsaugotas. Kitus PrintTrack langus uždarykite.'):
            return
        def choose():
            self.store.backup()
            self.store = open_existing(path, self.config_path)
        self.guard(choose)

    def open_data(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.directory)))

    def backup(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Išsaugoti kopiją', 'PrintTrack-kopija.json', 'JSON (*.json)')
        if path:
            self.guard(lambda: self.store.backup(path))

    def restore(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Atkurti kopiją', str(self.store.backups), 'JSON (*.json)')
        if path and self.confirm('Atkurti kopijos likučius ir sujungti korteles? Dabartinė istorija bus išsaugota, prieš atkūrimą bus sukurta kopija.'):
            self.guard(lambda: self.store.restore(path))

    def import_csv(self, kind):
        if kind not in ['rooms', 'printers', 'cartridges']:
            QMessageBox.information(self, 'CSV importas', 'Suderinamumo ir operacijų lentelės skirtos tik eksportui.')
            return
        path, _ = QFileDialog.getOpenFileName(self, 'Importuoti CSV', '', 'CSV (*.csv)')
        if path and self.confirm('Importuoti visus CSV įrašus? Prieš pakeitimą bus sukurta atsarginė kopija.'):
            self.guard(lambda: self.store.import_csv(kind, path))

    def confirm(self, text):
        box = QMessageBox(self)
        box.setWindowTitle('Patvirtinkite veiksmą')
        box.setText(text)
        box.setIcon(QMessageBox.Question)
        yes = box.addButton('Patvirtinti', QMessageBox.AcceptRole)
        box.addButton('Atšaukti', QMessageBox.RejectRole)
        box.exec()
        return box.clickedButton() == yes
