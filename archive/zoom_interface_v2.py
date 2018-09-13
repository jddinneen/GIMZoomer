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


class ZoomerWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.prune_thold = 2
        # self.root_path = os.path.expanduser('~')
        self.root_path = os.path.expanduser('C:\\Users\\ultra\\Dropbox\\mcgill')

        # grid = QGridLayout()
        # grid.setSpacing(10)
        # grid.setColumnStretch(3, 8)

        select_btn = QPushButton('Select Folder', self)
        select_btn.setToolTip('Select <b>root folder</b> to simplify.')
        select_btn.clicked.connect(self.showFileDialog)
        select_btn.resize(select_btn.sizeHint())
        # grid.addWidget(select_btn, 0, 0)

        self.folder_edit = QLineEdit()
        self.folder_edit.setReadOnly(True)
        self.folder_edit.setText(self.root_path)
        # grid.addWidget(self.folder_edit, 0, 1)

        self.slider_label = QLabel()
        self.slider_label.setAlignment(Qt.AlignCenter)
        self.slider_label.setText('Pruning\nThreshold:\n' + '{:.2f}'.format(self.prune_thold * 0.01))
        # grid.addWidget(self.slider_label, 1, 0)

        slider = QSlider(Qt.Vertical, self)  # for dynamically changing pruning threshold, default is 0.02
        slider.setValue(self.prune_thold)
        # grid.addWidget(slider, 2, 4, 1, 5)
        slider.setTickPosition(QSlider.TicksBothSides)
        slider.setTickInterval(10)
        slider.valueChanged[int].connect(self.changeValue)

        self.simplifyStructure(self.root_path, self.prune_thold)

        # dir_dict, og_dir_dict = self.simplifyStructure(self.root_path, self.prune_thold)

        # self.setGeometry(300, 300, 300, 200)
        # hbox0 = QHBoxLayout()
        # hbox1 = QHBoxLayout()
        # vbox = QVBoxLayout()
        # vbox_slider = QVBoxLayout()
        # hbox0.addWidget(select_btn)
        # hbox0.addWidget(self.folder_edit)
        # vbox_slider.addWidget(self.slider_label)
        # vbox_slider.addWidget(slider)
        # hbox1.addWidget(self.ogtree)
        # hbox1.addWidget(self.tree)
        # hbox1.addLayout(vbox_slider)
        # vbox.addLayout(hbox0)
        # self.setLayout(vbox)
        grid = QGridLayout()

        # grid.addWidget(select_btn, 0, 0)
        # grid.addWidget(self.folder_edit, 0, 1)
        # grid.addWidget(self.ogtree, 2, 0)
        # grid.addWidget(self.slider_label, 1, 1)
        # grid.addWidget(slider, 2, 1)
        # grid.addWidget(self.tree, 2, 2)

        grid.addWidget(select_btn, 0, 0, 1, 1)
        grid.addWidget(self.folder_edit, 0, 1, 1, 8)
        grid.addWidget(self.slider_label, 1, 4, 1, 1)
        grid.addWidget(self.ogtree, 2, 0, 1, 4)
        grid.addWidget(slider, 2, 4, 1, 1, alignment=Qt.AlignHCenter)
        grid.addWidget(self.tree, 2, 5, 1, 4)

        self.setLayout(grid)
        self.resize(640, 480)
        self.show()

    def showFileDialog(self):
        dirpath = QFileDialog.getExistingDirectory(self, 'Select Folder', self.root_path)
        self.root_path = os.path.abspath(dirpath)
        self.folder_edit.setText(self.root_path)
        self.simplifyStructure(self.root_path, self.prune_thold)

    def changeValue(self, value):
        print(value)
        self.prune_thold = value
        self.slider_label.setText('Pruning\nThreshold:\n' + '{:.2f}'.format(self.prune_thold*0.01))
        self.simplifyStructure(self.root_path, self.prune_thold)

    def simplifyStructure(self, root_path, prune_thold):
        # [0] directory name, [1] parent key, [2] children keys,
        # [3] names of files found in directory, [4] cumulative count of accessible files
        # root_path = 'C:\\Users\\ultra\\Dropbox\\mcgill'
        dir_dict = read_and_count(root_path)
        og_dir_dict = deepcopy(dir_dict)
        dir_dict = simplify_tree(root_path, 1, dir_dict, 0.95, prune_thold*0.01, print_=False)
        print_tree(root_path, dir_dict)

        self.ogtree = QTreeView(self)
        self.ogtree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ogmodel = QStandardItemModel()
        self.ogmodel.setHorizontalHeaderLabels(['Folder Name', 'Accessible Files', 'Number of Files'])
        self.ogtree.header().setDefaultSectionSize(280)
        self.ogtree.setModel(self.ogmodel)
        ogparent = self.ogmodel.invisibleRootItem()
        self.append_all_children(1, og_dir_dict, ogparent)  # dir_dict key starts at 1 since 0==False
        self.ogtree.expandAll()
        # grid.addWidget(self.ogtree, 2, 0, 3, 5)

        self.tree = QTreeView(self)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Folder Name', 'Accessible Files', 'Number of Files'])
        self.tree.header().setDefaultSectionSize(280)
        self.tree.setModel(self.model)
        parent = self.model.invisibleRootItem()
        self.append_all_children(1, dir_dict, parent)  # dir_dict key starts at 1 since 0==False
        self.tree.expandAll()
        self.tree.update()
        print("updated!")
        # grid.addWidget(self.tree, 2, 7, 3, 5)

        # return dir_dict, og_dir_dict

    def append_all_children(self, dirkey, dir_dict, qitem):
        qitem.appendRow([QStandardItem(dir_dict[dirkey][0]),
                         QStandardItem(str(dir_dict[dirkey][4])),
                         QStandardItem(str(len(dir_dict[dirkey][2])))])
        current_row = qitem.rowCount()-1
        for child in dir_dict[dirkey][2]:
            self.append_all_children(child, dir_dict, qitem.child(current_row))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # zmw = ZoomerMainWindow()
    zw = ZoomerWidget()
    # zmw.show()
    sys.exit(app.exec_())
