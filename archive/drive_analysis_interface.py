import os
import sys
from PyQt5.QtWidgets import QWidget, QPushButton, QApplication, QFileDialog, QSlider, QGridLayout, QLabel, \
    QTreeView, QAbstractItemView, QHeaderView, QCheckBox, QDirModel, QFileSystemModel
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QObject, QRunnable, QThreadPool, QDir
from PyQt5.QtGui import QStandardItemModel, QStandardItem


class CheckableFileSystemModel(QFileSystemModel):
    def __init__(self, parent=None):
        QFileSystemModel.__init__(self, None)
        self.checks = {}

    def data(self, index, role=Qt.DisplayRole):
        if role != Qt.CheckStateRole:
            return QFileSystemModel.data(self, index, role)
        else:
            if index.column() == 0:
                return self.checkState(index)

    def flags(self, index):
        return QFileSystemModel.flags(self, index) | Qt.ItemIsUserCheckable

    def checkState(self, index):
        if index in self.checks:
            return self.checks[index]
        else:
            return Qt.Checked

    def setData(self, index, value, role):
        if role == Qt.CheckStateRole and index.column() == 0:
            self.checks[index] = value
            self.dataChanged.emit(index, index)
            return True
        return QFileSystemModel.setData(self, index, value, role)


class DriveAnalysisWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('GIMZoomer')
        self.root_path = os.path.expanduser('~')

        model_filter = QDir.Dirs | QDir.NoDotAndDotDot | QDir.NoSymLinks

        # model = QDirModel()
        # model = QFileSystemModel()
        model = CheckableFileSystemModel()
        model.setRootPath(self.root_path)
        model.setFilter(model_filter)

        tree = QTreeView()
        tree.setModel(model)
        tree.setRootIndex(model.index(self.root_path))
        tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)

        grid = QGridLayout()
        grid.addWidget(tree, 0, 0, 1, 1)

        self.setLayout(grid)
        self.resize(640, 480)
        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    zw = DriveAnalysisWidget()
    sys.exit(app.exec_())
