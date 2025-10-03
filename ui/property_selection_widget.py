from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal


class PropertySelectionWidget(QWidget):
    selection_changed = pyqtSignal(list)  # list of selected property ids

    def __init__(self, parent=None):
        super().__init__(parent)
        self._properties = []  # {"id": str, "name": str}
        self.list = QListWidget()
        self.list.itemChanged.connect(self._emit_selection)
        self.status_label = QLabel("0 / 0 selected")

        btn_all = QPushButton("All")
        btn_none = QPushButton("None")
        btn_all.clicked.connect(self.select_all)
        btn_none.clicked.connect(self.select_none)

        btn_row = QHBoxLayout()
        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        btn_row.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addLayout(btn_row)
        layout.addWidget(self.list)

    def load_properties(self, props):
        """
        Loads a list of properties into the widget. Properties are a list of dictionaries in the form:
        (entityType: str, entitySort: str, entityName: str)
        """
        self._prop_items = []
        self.list.blockSignals(True)
        self.list.clear()
        for i, prop in enumerate(props):
            display = f"{prop['name']} : {prop['type']}"
            truncated = (display[:60] + "…") if len(display) > 60 else display
            item = QListWidgetItem(truncated)
            item.setToolTip(display)
            item.setData(Qt.ItemDataRole.UserRole, i)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.list.addItem(item)
            self._prop_items.append((prop["name"], item))
        self.list.blockSignals(False)
        self._update_status()
        self._emit_selection()

    def selected_properties(self):
        props = []
        for prop_name, item in self._prop_items:
            if item.checkState() == Qt.CheckState.Checked:
                props.append(prop_name)
        return props

    def select_all(self):
        self._set_all(Qt.CheckState.Checked)

    def select_none(self):
        self._set_all(Qt.CheckState.Unchecked)

    def _set_all(self, state):
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(state)
        self.list.blockSignals(False)
        self._update_status()
        self._emit_selection()

    def _emit_selection(self):
        self._update_status()
        self.selection_changed.emit(self.selected_properties())

    def _update_status(self):
        total = self.list.count()
        selected = len(self.selected_properties())
        self.status_label.setText(f"{selected} / {total} selected")

    @property
    def property_items(self):
        return self._prop_items