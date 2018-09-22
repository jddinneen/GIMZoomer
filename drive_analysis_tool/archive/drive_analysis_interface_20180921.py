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

        with open(os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'File Zoomer',
                                                  'code', 'drive_analysis_tool', 'dir_dict.pkl')), 'rb') as ddf:
            dir_dict = pickle.load(ddf)

        test_btn = QPushButton()
        test_btn.setText('Run tests')
        test_btn.resize(test_btn.sizeHint())

        tree = QTreeWidget()
        tree.setColumnCount(2)
        tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)

        anon_tree = QTreeWidget()
        anon_tree.setColumnCount(2)
        anon_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        anon_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)

        prev_item = None
        curr_item = None

        def append_all_children(dirkey, dir_dict, parent_item, checkable=True):
            if dirkey in dir_dict:
                # print(type(parent_item), parent_item.text(0))
                item = QTreeWidgetItem(parent_item, [dir_dict[dirkey]['dirname'], str(dir_dict[dirkey]['nfiles'])])
                item.setData(0, Qt.UserRole, dirkey)
                if checkable:
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.Checked)
                    # parent_item.setFlags(parent_item.flags() | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable)
                    parent_item.setFlags(parent_item.flags() | Qt.ItemIsUserTristate | Qt.ItemIsUserCheckable)
                    # parent_item.setFlags(parent_item.flags() | Qt.ItemIsUserCheckable)
                parent_item.addChild(item)
                # print(type(item.parent()), type(parent_item))
                child_ix = parent_item.childCount() - 1
                # print(nchild, parent_item.child(nchild).text(0), type(parent_item.child(nchild)))
                parent_item = parent_item.child(child_ix)
                # print(type(parent_item))
                children_keys = dir_dict[dirkey]['childkeys']
                children_names = [dir_dict[child]['dirname'].lower() for child in children_keys]
                for child_name, child_key in sorted(zip(children_names, children_keys)):
                    append_all_children(child_key, dir_dict, parent_item, checkable)

        def on_current_item_change(item, previous_item):
            # tree.setCurrentItem(current_item)
            parent_item = item.parent()
            child_ix = parent_item.indexOfChild(item)
            item_checkstate = item.checkState(0)
            if previous_item is not None:
                if previous_item.parent() != item:
                    propagate_checkstate_child(parent_item, child_ix, item_checkstate)

        def on_item_change_old(item):
            if item.checkState(0) in (Qt.Checked, Qt.PartiallyChecked):
                # print(item.text(0))
                if item.parent() is not None:
                    if item.parent().checkState(0) == Qt.Unchecked and item.checkState(0) == Qt.PartiallyChecked:
                        # print('True!')
                        item.parent().setCheckState(Qt.PartiallyChecked)

        def on_item_change(item):
            #####
            ## This is meant to work with the following:
            ## -- in append_all_children:
            ##    parent_item.setFlags(parent_item.flags() | Qt.ItemIsUserTristate | Qt.ItemIsUserCheckable)
            ## -- the following functions are used:
            ##    propagate_checkstate_child, propagate_checkstate_parent
            ## -- Updating the parent from Qt.PartiallyChecked to Qt.Checked when all children are checked has not
            ##    been implemented.
            #####
            # tree.setCurrentItem(item)
            # curr_item = item
            item_checkstate = item.checkState(0)
            parent_item = item.parent()
            # print(type(item), type(parent_item))
            # print(item.text(0))
            if parent_item is None:
                # print(item.childCount())
                nchild = item.childCount()
                if nchild > 0:
                    for child_ix in range(nchild):
                        propagate_checkstate_child(item, child_ix, item_checkstate)
            if parent_item is not None:
                child_ix = parent_item.indexOfChild(item)
                # print('child parent ix: ', child_ix)
                # if prev_item is not None:
                #     if curr_item != prev_item.parent():
                propagate_checkstate_child(parent_item, child_ix, item_checkstate)  ### HOW DO I APPLY THIS TO THE ROOT ITEM AS WELL???? ###
                propagate_checkstate_parent(item, item_checkstate)
                # print(item.data(0, Qt.UserRole))
                # print("# selected items: ", len(tree.selectedItems()))
            unchecked_items_list = []
            list_unchecked(root_item, 0, unchecked_items_list)
            # print(unchecked_items_list)
            anon_tree.clear()
            anon_dir_dict = deepcopy(dir_dict)
            # print(unchecked_items_list)
            anon_dir_dict = anonymize_stat(anon_dir_dict, unchecked_items_list)
            # print(set(dir_dict.keys()).difference(anon_dir_dict.keys()))
            anon_root_item = QTreeWidget.invisibleRootItem(anon_tree)
            append_all_children(1, anon_dir_dict, anon_root_item, checkable=False)
            anon_tree.expandToDepth(0)
            # prev_item = item

        def propagate_checkstate_child(parent_item, child_ix, parent_checkstate):
            # print('child ix: ', child_ix)
            if parent_checkstate != Qt.PartiallyChecked:
                parent_item.child(child_ix).setCheckState(0, parent_checkstate)
                # print(parent_item.child(child_ix).data(0, Qt.UserRole))
                parent_item = parent_item.child(child_ix)
                nchild = parent_item.childCount()
                if nchild > 0:
                    for child_ix in range(nchild):
                        propagate_checkstate_child(parent_item, child_ix, parent_checkstate)

        def propagate_checkstate_child_root(item, item_checkstate):
            if item_checkstate != Qt.PartiallyChecked:
                item.setCheckState(0, item_checkstate)
                nchild = item.childCount()
                print(nchild)
                if nchild > 0:
                    for child_ix in range(nchild):
                        print(item.child(child_ix).text(0))
                #         propagate_checkstate_child_root(item, item_checkstate)

        def propagate_checkstate_parent(item, item_checkstate):
            parent_item = item.parent()
            if parent_item is not None:
                # print(all_sibling_checked(item))
                if all_sibling_checked(item):
                    parent_item.setCheckState(0, Qt.Checked)
                if item_checkstate == Qt.Checked and parent_item.checkState(0) == Qt.Unchecked:
                    parent_item.setCheckState(0, Qt.PartiallyChecked)
                if item_checkstate == Qt.PartiallyChecked:
                    parent_item.setCheckState(0, Qt.PartiallyChecked)
                if item_checkstate in (Qt.Unchecked, Qt.PartiallyChecked) and parent_item.checkState(0) == Qt.Checked:
                    parent_item.setCheckState(0, Qt.PartiallyChecked)

        def all_sibling_checked(item):
            all_checked = True
            if item.parent() is not None:
                parent_item = item.parent()
                nchild = parent_item.childCount()
                for child_ix in range(nchild):
                    if parent_item.child(child_ix).checkState(0) in (Qt.Unchecked, Qt.PartiallyChecked):
                        all_checked = False
                        break
            return all_checked

        def list_unchecked(parent_item, child_ix, unchecked_items):
            # the assumption is there are fewer deselected dirs than selected
            item = parent_item.child(child_ix)
            # print(item.checkState(0))
            # if item.checkState(0) in (Qt.Checked, Qt.PartiallyChecked):
            if item.checkState(0) == Qt.Unchecked:
                    unchecked_items.append(item.data(0, Qt.UserRole))
            parent_item = parent_item.child(child_ix)
            nchild = parent_item.childCount()
            if nchild > 0:
                for child_ix in range(nchild):
                    list_unchecked(parent_item, child_ix, unchecked_items)

        def test_script():
            unchecked_items_list = []
            list_unchecked(root_item, 0, unchecked_items_list)
            print(set(dir_dict.keys()).difference(anon_dir_dict.keys()))
            print(unchecked_items_list)

        # root_item = QTreeWidgetItem(tree, [dir_dict[1]['dirname'], str(dir_dict[1]['nfiles'])])
        root_item = QTreeWidget.invisibleRootItem(tree)
        # hidden_item = QTreeWidgetItem(root_item, ['hello', 'world']).setHidden(False)
        # root_item.addChild(hidden_item)
        append_all_children(1, dir_dict, root_item)
        # print(type(root_item), root_item.childCount(), root_item.parent())
        tree.expandToDepth(0)
        tree.itemChanged.connect(on_item_change)
        # tree.currentItemChanged.connect(on_current_item_change)
        test_btn.clicked.connect(test_script)
        # print("n_child: ", root_item.childCount())
        # print("n_child: ", root_item.child(0).childCount())
        # print(root_item.child(0).indexOfChild(root_item.child(0).child(10)))
        # unchecked_items_list = []
        # list_unchecked(root_item, 0, unchecked_items_list)
        # print(unchecked_items_list)
        anon_dir_dict = deepcopy(dir_dict)
        anon_root_item = QTreeWidget.invisibleRootItem(anon_tree)
        # unchecked_items_list = [2, 10]
        # anon_dir_dict = anonymize_stat(anon_dir_dict, unchecked_items_list)
        append_all_children(1, anon_dir_dict, anon_root_item, checkable=False)
        anon_tree.expandToDepth(0)


        # self.ogtree = QTreeWidget(self)
        # self.ogtree.setColumnCount(2)
        # items = []
        # for i in range(10):
        #     items.append(QTreeWidgetItem(self.ogtree, [str(i), str(i)]))
        # self.ogtree.insertTopLevelItems(999, items)
        # self.ogtree.addTopLevelItems(items)
        # self.ogtree.addTopLevelItems(items)
        # self.ogtree.insertTopLevelItem(12123123, QTreeWidgetItem(self.ogtree, ['hello', 'world']))
        # self.ogtree.insertTopLevelItem(12123123, QTreeWidgetItem(self.ogtree, ['hello', 'world']))
        # print(self.ogtree.indexOfTopLevelItem(items[9]))
        # items[1].addChild(QTreeWidgetItem(items[1], ['bad', 'juju']))

        grid = QGridLayout()
        # grid.addWidget(self.ogtree, 0, 0, 1, 4)
        grid.addWidget(test_btn, 0, 0, 1, 1)
        grid.addWidget(tree, 1, 0, 1, 4)
        grid.addWidget(anon_tree, 1, 5, 1, 4)

        self.setLayout(grid)
        self.resize(640, 480)
        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    daw = DriveAnalysisWidget()
    sys.exit(app.exec_())
