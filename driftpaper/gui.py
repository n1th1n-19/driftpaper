"""Qt front end. Imported lazily so the CLI works without PySide6."""
import sys
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QListView,
                               QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout, QWidget)

from . import core

MEDIA = "Media (*.jpg *.jpeg *.png *.webp *.bmp *.avif *.mp4 *.webm *.mkv *.mov *.gif)"


class Studio(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Driftpaper")
        self.resize(900, 620)
        self.setAcceptDrops(True)

        self.grid = QListWidget(viewMode=QListView.IconMode, iconSize=QSize(240, 135), resizeMode=QListView.Adjust,
                                movement=QListView.Static, spacing=10, wordWrap=True)
        self.grid.itemDoubleClicked.connect(lambda _: self.apply())

        add, rm, ap = QPushButton("Add…"), QPushButton("Remove"), QPushButton("Apply")
        add.clicked.connect(self.add); rm.clicked.connect(self.remove); ap.clicked.connect(self.apply)
        ap.setDefault(True)
        self.target = QComboBox(); self.target.addItem("All screens", None)
        try:
            for s in core.screens():
                self.target.addItem(f"Screen {s + 1}", s)
        except core.Error:  # plasmashell unreachable: library still usable, apply will report
            pass
        self.pause_max = QCheckBox("Pause live when a window is maximized"); self.pause_max.setChecked(True)
        self.pause_bat = QCheckBox("Pause live on battery"); self.pause_bat.setChecked(True)
        self.msg = QLabel("Double-click a wallpaper to apply. Drop files here to add.")

        bar = QHBoxLayout()
        for w in (add, rm): bar.addWidget(w)
        bar.addStretch(); bar.addWidget(QLabel("Apply to:")); bar.addWidget(self.target); bar.addWidget(ap)
        opts = QHBoxLayout(); opts.addWidget(self.pause_max); opts.addWidget(self.pause_bat); opts.addStretch()
        lay = QVBoxLayout(self)
        lay.addLayout(bar); lay.addWidget(self.grid); lay.addLayout(opts); lay.addWidget(self.msg)
        self.reload()

    def reload(self):
        self.grid.clear()
        for f in core.items():
            t = core.thumb_path(f)
            if not t.exists():
                core.make_thumb(f)
            icon = QIcon(str(t if t.exists() else f)) if (t.exists() or core.kind(f) == "static") else QIcon()
            it = QListWidgetItem(icon, ("▶ " if core.kind(f) == "live" else "") + f.stem)
            it.setData(Qt.UserRole, str(f)); it.setSizeHint(QSize(260, 175))
            self.grid.addItem(it)

    def ingest(self, paths):
        bad = []
        for p in paths:
            try:
                core.import_file(Path(p))
            except core.Error as e:
                bad.append(str(e))
        self.reload()
        if bad:
            QMessageBox.warning(self, "Skipped", "\n".join(bad))

    def add(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Add wallpapers", str(Path.home() / "Pictures"), MEDIA)
        self.ingest(paths)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()

    def dropEvent(self, e):
        self.ingest([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])

    def remove(self):
        it = self.grid.currentItem()
        if not it: return
        f = Path(it.data(Qt.UserRole))
        if QMessageBox.question(self, "Remove", f"Delete {f.name} from the library?") == QMessageBox.Yes:
            core.remove(f); self.reload()

    def apply(self):
        it = self.grid.currentItem()
        if not it:
            self.msg.setText("Select a wallpaper first."); return
        f = Path(it.data(Qt.UserRole))
        try:
            live, _ = core.apply(f, self.target.currentData(), self.pause_max.isChecked(), self.pause_bat.isChecked())
            self.msg.setText(f"Applied {'live' if live else 'static'} wallpaper: {f.name}")
        except core.Error as e:
            self.msg.setText(f"Failed: {e}")


def run():
    app = QApplication(sys.argv[:1])
    w = Studio(); w.show()
    return app.exec()
