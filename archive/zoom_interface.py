import sys
from PyQt5.QtWidgets import QWidget, QToolTip, QPushButton, QMainWindow, QApplication, QDesktopWidget, \
    QFileDialog, QSlider, QLineEdit, QGridLayout, QLabel, QTreeView, QAbstractItemView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon, QStandardItemModel, QStandardItem
import os
from copy import deepcopy
from archive.compress_and_prune_v4 import read_and_count, simplify_tree, print_tree


class ZoomerMainWindow(QMainWindow):

    def __init__(self, parent=None):
        super(ZoomerMainWindow, self).__init__(parent)
        self.zoomer_widget = ZoomerWidget()
        self.setCentralWidget(self.zoomer_widget)
        self.initUI()

    def initUI(self):
        QToolTip.setFont(QFont('SansSerif', 10))
        self.statusBar().showMessage('Status message goes here.')
        self.setToolTip('<b>GIMZoomer</b>: File structure simplication program.')
        # self.setGeometry(300, 300, 300, 200)
        self.resize(300, 200)
        self.center()

        self.setWindowTitle('GIMZoomer')
        self.setWindowIcon(QIcon('web.png'))
        self.show()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    # def closeEvent(self, event):
    #     reply = QMessageBox.question(self, 'Message',
    #                                  "Are you sure you want to quit?", QMessageBox.Yes |
    #                                  QMessageBox.No, QMessageBox.No)
    #     if reply == QMessageBox.Yes:
    #         event.accept()
    #     else:
    #         event.ignore()


class ZoomerWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        default_prune = 2

        grid = QGridLayout()
        grid.setSpacing(10)
        # grid.setColumnStretch(0, 1)
        # grid.setColumnStretch(3, 1)
        # grid.setWidthStretch(0, 1)
        # grid.setWidthStretch(3, 1)

        select_btn = QPushButton('Select Folder', self)
        select_btn.setToolTip('Select <b>root folder</b> to simplify.')
        select_btn.clicked.connect(self.showFileDialog)
        select_btn.resize(select_btn.sizeHint())
        grid.addWidget(select_btn, 0, 0)

        self.folder_edit = QLineEdit()
        self.folder_edit.setText(os.path.expanduser('~'))
        grid.addWidget(self.folder_edit, 0, 1)

        self.slider_label = QLabel()
        self.slider_label.setAlignment(Qt.AlignCenter)
        self.slider_label.setText('Pruning\nThreshold:\n' + '{:.2f}'.format(default_prune * 0.01))
        grid.addWidget(self.slider_label, 1, 0)

        slider = QSlider(Qt.Vertical, self)  # for dynamically changing pruning threshold, default is 0.02
        slider.setValue(default_prune)
        grid.addWidget(slider, 2, 0, 1, 5)
        slider.setTickPosition(QSlider.TicksBothSides)
        slider.setTickInterval(10)
        slider.valueChanged[int].connect(self.changeValue)

        # self.model = QFileSystemModel()
        # self.model.setRootPath(os.path.expanduser('~'))
        # self.tree = QTreeView()
        # self.tree.setModel(self.model)
        # # self.tree.setRootIndex(self.model.index(os.path.expanduser('~')))
        # self.tree.setRootIndex(self.model.index('C:\\Users\\ultra\\Dropbox\\mcgill'))
        # self.tree.header().setDefaultSectionSize(320)
        # grid.addWidget(self.tree, 8, 1, 2, 5)

        # treeWidget = QTreeWidget()
        # treeWidget.setColumnCount(1)
        # treeWidget.setHeaderLabels(["Folders"])
        # List1 = QTreeWidgetItem(["Item 1"])
        # List2 = QTreeWidgetItem(["Item 2"])
        # treeWidget.addTopLevelItems([List1, List2])
        # items = list()
        # for i in range(5):
        #     List1_Child = QTreeWidgetItem(["Item 1's Child No." + str(i)])
        #     List1.addChild(List1_Child)
        # for i in range(3):
        #     List2_Child = QTreeWidgetItem(["Item 2's Child No." + str(i)])
        #     List2.addChild(List2_Child)
        #     # test_child = QTreeWidgetItem["Hello"]
        #     # List2_Child.addChild(test_child)
        # grid.addWidget(treeWidget, 3, 1, 3, 5)

        self.tree = QTreeView(self)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Folder Name', 'Accessible Files', 'Number of Files'])
        self.tree.header().setDefaultSectionSize(280)
        # self.tree.resizeColumnToContents(0)
        # header = self.tree.header()
        # header.setSectionResizeMode(0, QHeaderView.Stretch)
        # header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        # header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tree.setModel(self.model)
        parent = self.model.invisibleRootItem()

        root_path = 'C:\\Users\\ultra\\Dropbox\\mcgill'
        dir_dict = read_and_count(root_path)
        og_dir_dict = deepcopy(dir_dict)
        dir_dict = simplify_tree(root_path, 1, dir_dict, 0.95, 0.02, print_=False)
        print_tree(root_path, dir_dict)
        # [0] directory name, [1] parent key, [2] children keys,
        # [3] names of files found in directory, [4] cumulative count of accessible files

        def append_all_children(dirkey, dir_dict, qitem):
            qitem.appendRow([QStandardItem(dir_dict[dirkey][0]),
                             QStandardItem(str(dir_dict[dirkey][4])),
                             QStandardItem(str(len(dir_dict[dirkey][2])))])
            current_row = qitem.rowCount()-1
            for child in dir_dict[dirkey][2]:
                append_all_children(child, dir_dict, qitem.child(current_row))

        append_all_children(1, og_dir_dict, parent)

        # self.tree = QTreeView(self)
        # self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # self.model = QStandardItemModel()
        # self.model.setHorizontalHeaderLabels(['Folder Name', 'Number of Files'])
        # self.tree.header().setDefaultSectionSize(180)
        # self.tree.setModel(self.model)
        # # self.importData(data)
        # self.model.setRowCount(0)
        # root = self.model.invisibleRootItem()
        # parent = root
        # parent.appendRow([QStandardItem("Hello1"), QStandardItem("World1"), ])
        # parent.appendRow([QStandardItem("Hello2"), QStandardItem("World2"), ])
        # parent.appendRow([QStandardItem("Hello3"), QStandardItem("World3"), ])
        # parent.child(1).appendRow([QStandardItem("Hello4"), QStandardItem("World4"), ])
        # parent.child(1).child(0).appendRow([QStandardItem("Hello5"), QStandardItem("World5"), ])

        self.tree.expandAll()
        grid.addWidget(self.tree, 2, 1, 3, 5)

        self.setLayout(grid)
        # self.setGeometry(300, 300, 300, 200)
        self.resize(640, 480)
        self.show()

    def showFileDialog(self):
        fname = QFileDialog.getExistingDirectory(self, 'Select Folder', os.path.expanduser('~'))
        self.folder_edit.setText(os.path.abspath(fname))

    def changeValue(self, value):
        print(value)
        self.slider_label.setText('Pruning\nThreshold:\n' + '{:.2f}'.format(value*0.01))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # zmw = ZoomerMainWindow()
    zw = ZoomerWidget()
    # zmw.show()
    sys.exit(app.exec_())
