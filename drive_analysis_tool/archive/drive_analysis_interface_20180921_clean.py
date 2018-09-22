import pickle
import traceback
import sys
import os
from PyQt5.QtWidgets import QWidget, QPushButton, QApplication, QFileDialog, QSlider, QGridLayout, QLabel, \
    QTreeView, QAbstractItemView, QHeaderView, QCheckBox, QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QObject, QRunnable, QThreadPool, QVariant, QItemSelectionModel
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from copy import deepcopy
from compress_and_prune_v4_1 import read_and_count, simplify_tree
from drive_analysis_tool.drive_analyzer import record_stat, anonymize_stat, find_all_children

class DriveAnalysisWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Drive Analysis Tool')
        # self.root_path = os.path.expanduser('~')  # BUG 2018-09-18: No permission to access certain files for os.stat
        self.root_path = os.path.expanduser('~\\Downloads')
        self.threadpool = QThreadPool()
        self.resize_mode = 'dynamic'
        self.unchecked_items_list = []

        with open(os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'File Zoomer',
                                                  'code', 'drive_analysis_tool', 'dir_dict.pkl')), 'rb') as ddf:
            self.og_dir_dict = pickle.load(ddf)

        test_btn = QPushButton()
        test_btn.setText('Run tests')
        test_btn.resize(test_btn.sizeHint())
        test_btn.clicked.connect(self.test_script)

        self.og_tree = QTreeWidget()
        self.og_tree.setColumnCount(3)
        self.og_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.og_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.og_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.og_tree.setHeaderLabels(['Folder', 'Renamed Folder', 'Number of Files'])

        self.anon_tree = QTreeWidget()
        self.anon_tree.setColumnCount(3)
        self.anon_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.anon_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.anon_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.anon_tree.setHeaderLabels(['Folder', 'Renamed Folder', 'Number of Files'])

        self.og_root_item = QTreeWidget.invisibleRootItem(self.og_tree)
        self.append_all_children(1, self.og_dir_dict, self.og_root_item)
        self.og_tree.expandToDepth(0)
        self.og_tree.itemChanged.connect(self.on_item_change)
        self.anon_dir_dict = deepcopy(self.og_dir_dict)
        self.anon_root_item = QTreeWidget.invisibleRootItem(self.anon_tree)
        self.append_all_children(1, self.anon_dir_dict, self.anon_root_item, checkable=False)
        self.anon_tree.expandToDepth(0)

        grid = QGridLayout()
        grid.addWidget(test_btn, 0, 0, 1, 1)
        grid.addWidget(self.og_tree, 1, 0, 1, 4)
        grid.addWidget(self.anon_tree, 1, 5, 1, 4)

        self.setLayout(grid)
        self.resize(640, 480)
        self.show()

    def append_all_children(self, dirkey, dir_dict, parent_item, checkable=True):
        if dirkey in dir_dict:
            item = QTreeWidgetItem(parent_item, [dir_dict[dirkey]['dirname'], dir_dict[dirkey]['dirname'], str(dir_dict[dirkey]['nfiles'])])
            item.setData(0, Qt.UserRole, dirkey)
            if checkable:
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
                item.setCheckState(0, Qt.Checked)
                parent_item.setFlags(parent_item.flags() | Qt.ItemIsUserTristate | Qt.ItemIsUserCheckable)
            parent_item.addChild(item)
            child_ix = parent_item.childCount() - 1
            parent_item = parent_item.child(child_ix)
            children_keys = dir_dict[dirkey]['childkeys']
            children_names = [dir_dict[child]['dirname'].lower() for child in children_keys]
            for child_name, child_key in sorted(zip(children_names, children_keys)):
                self.append_all_children(child_key, dir_dict, parent_item, checkable)

    def on_item_change(self, item):
        item_checkstate = item.checkState(0)
        parent_item = item.parent()
        if parent_item is None:
            nchild = item.childCount()
            if nchild > 0:
                for child_ix in range(nchild):
                    self.propagate_checkstate_child(item, child_ix, item_checkstate)
        if parent_item is not None:
            child_ix = parent_item.indexOfChild(item)
            self.propagate_checkstate_child(parent_item, child_ix, item_checkstate)
            self.propagate_checkstate_parent(item, item_checkstate)
        self.unchecked_items_list = []
        self.list_unchecked(self.og_root_item, 0, self.unchecked_items_list)
        self.anon_tree.clear()
        self.anon_dir_dict = deepcopy(self.og_dir_dict)
        self.anon_dir_dict = anonymize_stat(self.anon_dir_dict, self.unchecked_items_list)
        self.anon_root_item = QTreeWidget.invisibleRootItem(self.anon_tree)
        self.append_all_children(1, self.anon_dir_dict, self.anon_root_item, checkable=False)
        self.anon_tree.expandToDepth(0)

    def propagate_checkstate_child(self, parent_item, child_ix, parent_checkstate):
        if parent_checkstate != Qt.PartiallyChecked:
            parent_item.child(child_ix).setCheckState(0, parent_checkstate)
            parent_item = parent_item.child(child_ix)
            nchild = parent_item.childCount()
            if nchild > 0:
                for child_ix in range(nchild):
                    self.propagate_checkstate_child(parent_item, child_ix, parent_checkstate)

    def propagate_checkstate_parent(self, item, item_checkstate):
        parent_item = item.parent()
        if parent_item is not None:
            if self.all_sibling_checked(item):
                parent_item.setCheckState(0, Qt.Checked)
            if item_checkstate == Qt.Checked and parent_item.checkState(0) == Qt.Unchecked:
                parent_item.setCheckState(0, Qt.PartiallyChecked)
            if item_checkstate == Qt.PartiallyChecked:
                parent_item.setCheckState(0, Qt.PartiallyChecked)
            if item_checkstate in (Qt.Unchecked, Qt.PartiallyChecked) and parent_item.checkState(0) == Qt.Checked:
                parent_item.setCheckState(0, Qt.PartiallyChecked)

    def all_sibling_checked(self, item):
        all_checked = True
        if item.parent() is not None:
            parent_item = item.parent()
            nchild = parent_item.childCount()
            for child_ix in range(nchild):
                if parent_item.child(child_ix).checkState(0) in (Qt.Unchecked, Qt.PartiallyChecked):
                    all_checked = False
                    break
        return all_checked

    def list_unchecked(self, parent_item, child_ix, unchecked_items):
        item = parent_item.child(child_ix)
        if item.checkState(0) == Qt.Unchecked:
                unchecked_items.append(item.data(0, Qt.UserRole))
        parent_item = parent_item.child(child_ix)
        nchild = parent_item.childCount()
        if nchild > 0:
            for child_ix in range(nchild):
                self.list_unchecked(parent_item, child_ix, unchecked_items)

    def test_script(self):
        unchecked_items_list = []
        self.list_unchecked(self.root_item, 0, unchecked_items_list)
        print(set(self.og_dir_dict.keys()).difference(self.anon_dir_dict.keys()))
        print(unchecked_items_list)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    daw = DriveAnalysisWidget()
    sys.exit(app.exec_())
