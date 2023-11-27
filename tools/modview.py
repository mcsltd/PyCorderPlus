from PyQt6.QtWidgets import QTableWidget, QStyledItemDelegate
from PyQt6.QtCore import QAbstractTableModel


class GenericTableWidget(QTableWidget):
    pass


class _DataTableModel(QAbstractTableModel):
    pass


class _DataItemDelegate(QStyledItemDelegate):
    pass