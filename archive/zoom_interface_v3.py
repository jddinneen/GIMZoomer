import sys
import os
from PyQt5.QtWidgets import QWidget, QToolTip, QPushButton, QMainWindow, QApplication, QDesktopWidget, \
    QFileDialog, QSlider, QLineEdit, QGridLayout, QLabel, QTreeView, QAbstractItemView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon, QStandardItemModel, QStandardItem
from copy import deepcopy
from archive.compress_and_prune_v4 import read_and_count, simplify_tree


# BUG ALERT
# BUG: simplify_tree crashes if all folders do not contain a single file due to dir_dict being empty
# OPTIMIZATION
# OPT: Bulk of processing time is from read_and_count, while simplify_tree is quick
# Instead of current simplifyStructure where read_and_count is called constantly, only call read_and_count
# when folder is changed.
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
        self.setWindowTitle('GIMZoomer')
        self.prune_thold = 4
        self.root_path = os.path.expanduser('~')
        # self.root_path = os.path.expanduser('C:\\Users\\ultra\\Dropbox\\mcgill')
        # self.root_path = os.path.expanduser('C:\\Users\\ultra\\Documents')

        # grid = QGridLayout()
        # grid.setSpacing(10)
        # grid.setColumnStretch(3, 8)

        # self.proc_lbl = QLabel()
        # self.proc_lbl.setAlignment(Qt.AlignCenter)
        # self.proc_mov = QMovie('ajax-loader.gif')
        # self.proc_lbl.setMovie(self.proc_mov)
        # # self.proc_lbl.setText('placeholder')
        # # self.proc_mov.start()

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
        self.slider_label.setText('Pruning\nThreshold:\n' + '{:.3f}'.format(self.scalePruning(self.prune_thold)))
        # grid.addWidget(self.slider_label, 1, 0)

        slider = QSlider(Qt.Vertical, self)  # for dynamically changing pruning threshold, default is 0.02
        slider.setValue(self.prune_thold)
        # grid.addWidget(slider, 2, 4, 1, 5)
        slider.setTickPosition(QSlider.TicksBothSides)
        slider.setTickInterval(10)
        slider.valueChanged[int].connect(self.changeValue)

        ogtree_label = QLabel()
        ogtree_label.setAlignment(Qt.AlignCenter)
        ogtree_label.setText('Original Structure')

        tree_label = QLabel()
        tree_label.setAlignment(Qt.AlignCenter)
        tree_label.setText('Pruned Structure\n(Ordered By Folder Importance)')

        self.ogtree = QTreeView(self)
        self.ogtree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ogmodel = QStandardItemModel()
        self.ogmodel.setHorizontalHeaderLabels(['Folder Name', 'Accessible Files', 'Number of Files'])
        # self.ogtree.header().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.tree = QTreeView(self)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Folder Name', 'Accessible Files', 'Number of Files'])
        # self.tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.dir_dict, self.og_dir_dict = self.buildStructure(self.root_path)
        self.simplifyStructure(self.root_path, self.dir_dict, self.prune_thold)

        grid = QGridLayout()
        grid.addWidget(select_btn, 0, 0, 1, 1)
        grid.addWidget(self.folder_edit, 0, 1, 1, 8)
        grid.addWidget(ogtree_label, 1, 0, 1, 4)
        grid.addWidget(self.slider_label, 1, 4, 1, 1)
        grid.addWidget(tree_label, 1, 5, 1, 4)
        grid.addWidget(self.ogtree, 2, 0, 1, 4)
        grid.addWidget(slider, 2, 4, 1, 1, alignment=Qt.AlignHCenter)
        grid.addWidget(self.tree, 2, 5, 1, 4)

        self.setLayout(grid)
        self.resize(640, 480)
        self.show()

    def scalePruning(self, prune_thold):
        return prune_thold * 0.005
        # return math.log(prune_thold, 10)/2
        # return math.exp(prune_thold)/math.exp(100)

    def showFileDialog(self):
        dirpath = QFileDialog.getExistingDirectory(self, 'Select Folder', self.root_path)
        if dirpath:
            self.root_path = os.path.abspath(dirpath)
            self.folder_edit.setText(self.root_path)
            self.dir_dict, self.og_dir_dict = self.buildStructure(self.root_path)
            self.simplifyStructure(self.root_path, self.dir_dict, self.prune_thold)

    def changeValue(self, value):
        # print(value)
        self.prune_thold = value
        self.slider_label.setText('Pruning\nThreshold:\n' + '{:.3f}'.format(self.scalePruning(self.prune_thold)))
        self.dir_dict = deepcopy(self.og_dir_dict)
        self.simplifyStructure(self.root_path, self.dir_dict, self.prune_thold)

    def buildStructure(self, root_path):
        dir_dict = read_and_count(root_path)
        og_dir_dict = deepcopy(dir_dict)
        self.refreshTreeView(self.ogmodel, self.ogtree, og_dir_dict)
        return og_dir_dict, dir_dict

    def simplifyStructure(self, root_path, dir_dict, prune_thold):
        # [0] directory name, [1] parent key, [2] children keys,
        # [3] names of files found in directory, [4] cumulative count of accessible files
        # root_path = 'C:\\Users\\ultra\\Dropbox\\mcgill'
        # dir_dict = read_and_count(root_path)
        # og_dir_dict = deepcopy(dir_dict)
        dir_dict = simplify_tree(root_path, 1, dir_dict, 0.95, self.scalePruning(prune_thold), print_=False)
        # print_tree(root_path, dir_dict)

        self.refreshTreeView(self.model, self.tree, dir_dict)

        # # self.ogmodel.clear()
        # # self.ogmodel.setHorizontalHeaderLabels(['Folder Name', 'Accessible Files', 'Number of Files'])
        # self.ogmodel.removeRow(0)
        # ogparent = self.ogmodel.invisibleRootItem()
        # self.append_all_children(1, og_dir_dict, ogparent)  # dir_dict key starts at 1 since 0==False
        # self.ogtree.setModel(self.ogmodel)
        # self.ogtree.expandAll()
        # self.ogtree.resizeColumnToContents(0)
        # self.ogtree.resizeColumnToContents(1)
        # self.ogtree.resizeColumnToContents(2)

        # # self.model.clear()
        # # self.model.setHorizontalHeaderLabels(['Folder Name', 'Accessible Files', 'Number of Files'])
        # self.model.removeRow(0)
        # parent = self.model.invisibleRootItem()
        # self.append_all_children(1, dir_dict, parent)  # dir_dict key starts at 1 since 0==False
        # self.tree.setModel(self.model)
        # self.tree.expandAll()
        # self.tree.resizeColumnToContents(0)
        # self.tree.resizeColumnToContents(1)
        # self.tree.resizeColumnToContents(2)

        # return dir_dict, og_dir_dict

    def refreshTreeView(self, model, tree, dir_dict):
        model.removeRow(0)
        parent = model.invisibleRootItem()
        self.append_all_children(1, dir_dict, parent)  # dir_dict key starts at 1 since 0==False
        tree.setModel(model)
        tree.expandAll()
        tree.resizeColumnToContents(0)
        tree.resizeColumnToContents(1)
        tree.resizeColumnToContents(2)

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
