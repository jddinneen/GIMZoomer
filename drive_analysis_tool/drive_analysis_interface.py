import time
import pickle
import _pickle
import traceback
import json
import sys
import os
from PyQt5.QtWidgets import QWidget, QPushButton, QApplication, QFileDialog, QSlider, QGridLayout, QLabel, \
    QTreeView, QAbstractItemView, QHeaderView, QCheckBox, QTreeWidget, QTreeWidgetItem, QTextBrowser
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QObject, QRunnable, QThreadPool, QVariant, QItemSelectionModel
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from copy import deepcopy
from drive_analysis_tool.drive_analyzer import record_stat, compute_stat, anonymize_stat, find_all_children, \
    drive_measurement, check_collection_properties
from drive_analysis_tool.submit_data import compress_data, encrypt_data, dropbox_upload, generate_filename


# BUG ALERT
# BUG: simplify_tree crashes if all folders do not contain a single file due to dir_dict being empty
class WorkerSignals(QObject):
    started = pyqtSignal()
    result = pyqtSignal(object)
    finished = pyqtSignal()


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            self.signals.started.emit()
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


class DriveAnalysisWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Drive Analysis Tool')
        # self.root_path = os.path.expanduser('~')
        # self.root_path = os.path.expanduser('~\\Downloads')
        self.root_path = os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill'))
        self.dbx_json_dirpath = '/'
        self.threadpool = QThreadPool()
        self.expanded_items_list = []
        self.unchecked_items_list = []
        self.unchecked_items_set = set()
        self.renamed_items_dict = dict()

        # with open(os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'File Zoomer',
        #                                           'code', 'drive_analysis_tool', 'dir_dict.pkl')), 'rb') as ddf:
        #     self.og_dir_dict = pickle.load(ddf)
        # self.anon_dir_dict = deepcopy(self.og_dir_dict)

        self.og_dir_dict, self.anon_dir_dict = dict(), dict()
        self.user_folder_props = dict()
        self.user_folder_typical = True
        self.build_tree_structure_threaded(self.root_path)

        # test_btn = QPushButton()
        # test_btn.setText('Run tests')
        # test_btn.resize(test_btn.sizeHint())
        # test_btn.clicked.connect(self.test_script)

        select_btn = QPushButton('Select Folder', self)
        select_btn.setToolTip('Select <b>personal folder</b> for data collection.')
        select_btn.clicked.connect(self.show_file_dialog)
        select_btn.resize(select_btn.sizeHint())

        preview_btn = QPushButton('Preview', self)
        preview_btn.setToolTip('Preview folder data that will be used for research')
        preview_btn.clicked.connect(self.preview_anon_tree_threaded)
        preview_btn.resize(preview_btn.sizeHint())

        submit_btn = QPushButton('Submit', self)
        submit_btn.setToolTip('Submit encrypted folder data to the cloud')
        submit_btn.clicked.connect(self.upload_collected_data)
        submit_btn.resize(submit_btn.sizeHint())

        self.folder_edit = QLabel()
        self.folder_edit.setText(self.root_path)

        self.status_label = QLabel()
        self.status_label.setText('')
        self.status_label.setStyleSheet("color: red;"
                                        "font: bold;")

        self.user_folder_props_label = QLabel()
        self.user_folder_props_label.setText('\n'*21)

        self.user_folder_typical_label = QLabel()
        self.user_folder_typical_label.setText('\n')
        self.user_folder_typical_label.setStyleSheet("font: bold;")

        og_tree_label = QLabel()
        og_tree_label.setAlignment(Qt.AlignCenter)
        og_tree_label.setText('Original folders data')

        anon_tree_label = QLabel()
        anon_tree_label.setAlignment(Qt.AlignCenter)
        anon_tree_label.setText('Folders data to be used for research')

        self.og_tree = QTreeView()
        self.og_model = QStandardItemModel()
        self.og_tree.setModel(self.og_model)
        self.og_model.setHorizontalHeaderLabels(['Folder Name', 'Renamed Folder', 'Number of Files'])
        self.og_root_item = self.og_model.invisibleRootItem()
        self.refresh_treeview(self.og_model, self.og_tree, self.og_dir_dict)
        self.og_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.og_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.og_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.og_model.itemChanged.connect(self.on_item_change)

        self.anon_tree = QTreeView()
        self.anon_model = QStandardItemModel()
        self.anon_tree.setModel(self.anon_model)
        self.anon_model.setHorizontalHeaderLabels(['Folder Name', 'Number of Files'])
        self.anon_root_item = self.anon_model.invisibleRootItem()
        self.refresh_treeview(self.anon_model, self.anon_tree, self.anon_dir_dict, checkable=False, anon_tree=True)
        self.anon_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.anon_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)

        grid = QGridLayout()
        grid.addWidget(select_btn, 0, 0, 1, 1)
        grid.addWidget(self.folder_edit, 0, 1, 1, 7)
        grid.addWidget(self.status_label, 1, 0, 1, 8)
        grid.addWidget(og_tree_label, 2, 0, 1, 5)
        grid.addWidget(anon_tree_label, 2, 5, 1, 3)
        grid.addWidget(self.og_tree, 3, 0, 1, 5)
        grid.addWidget(self.anon_tree, 3, 5, 1, 3)
        grid.addWidget(preview_btn, 4, 6, 1, 1)
        grid.addWidget(submit_btn, 4, 7, 1, 1)
        grid.addWidget(self.user_folder_props_label, 5, 0, 1, 8)
        grid.addWidget(self.user_folder_typical_label, 6, 0, 1, 1)

        self.setLayout(grid)
        self.resize(1280, 720)
        self.show()

    def refresh_treeview(self, model, tree, dir_dict, checkable=True, anon_tree=False):
        model.removeRow(0)
        root_item = model.invisibleRootItem()
        self.append_all_children(1, dir_dict, root_item, checkable, anon_tree)  # dir_dict key starts at 1 since 0==False
        # tree.setModel(model)
        tree.expandToDepth(0)

    def append_all_children(self, dirkey, dir_dict, parent_item, checkable=True, anon_tree=False):
        if dirkey in dir_dict:
            dirname = QStandardItem(dir_dict[dirkey]['dirname'])
            dirname_edited = QStandardItem(dir_dict[dirkey]['dirname'])
            nfiles = QStandardItem(str(dir_dict[dirkey]['nfiles']))
            if anon_tree:
                items = [dirname, nfiles]
            else:
                items = [dirname, dirname_edited, nfiles]
            dirname.setData(dirkey, Qt.UserRole)
            dirname_edited.setData(dirkey, Qt.UserRole)
            if checkable:
                dirname.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserTristate | Qt.ItemIsUserCheckable)
                dirname.setCheckState(Qt.Checked)
                dirname_edited.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable)
                nfiles.setFlags(Qt.ItemIsEnabled)
            parent_item.appendRow(items)
            child_ix = parent_item.rowCount() - 1
            parent_item = parent_item.child(child_ix)
            children_keys = dir_dict[dirkey]['childkeys']
            for child_key in sorted(children_keys):
                self.append_all_children(child_key, dir_dict, parent_item, checkable, anon_tree)

    def on_item_change(self, item):
        if item.column() == 0:
            dirkey = item.data(Qt.UserRole)
            if item.rowCount() == 0 and item.checkState() == Qt.PartiallyChecked:
                item.setCheckState(Qt.Checked)
            item_checkstate = item.checkState()
            parent_item = item.parent()
            if parent_item is None:
                nchild = item.rowCount()
                if nchild > 0:
                    for child_ix in range(nchild):
                        self.propagate_checkstate_child(item, child_ix, item_checkstate)
            if parent_item is not None:
                child_ix = item.row()
                self.propagate_checkstate_child(parent_item, child_ix, item_checkstate)
                self.propagate_checkstate_parent(item, item_checkstate)
            # self.unchecked_items_list = []
            # self.list_unchecked(self.og_root_item, 0, self.unchecked_items_list)
            # print(self.unchecked_items_list)
            if item_checkstate == Qt.Unchecked:
                self.unchecked_items_set.add(dirkey)
                # if dirkey in self.renamed_items_dict:
                #     self.renamed_items_dict.pop(dirkey)
            elif item_checkstate in (Qt.Checked, Qt.PartiallyChecked):
                if dirkey in self.unchecked_items_set:
                    self.unchecked_items_set.remove(dirkey)
            self.status_label.setText('Click \'Preview\' to see changes')
        if item.column() == 1:
            dirkey = item.data(Qt.UserRole)
            self.renamed_items_dict[dirkey] = item.text()
            self.status_label.setText('Click \'Preview\' to see changes')

    def propagate_checkstate_child(self, parent_item, child_ix, parent_checkstate):
        if parent_checkstate != Qt.PartiallyChecked:
            parent_item.child(child_ix).setCheckState(parent_checkstate)
            parent_item = parent_item.child(child_ix)
            nchild = parent_item.rowCount()
            if nchild > 0:
                for child_ix in range(nchild):
                    self.propagate_checkstate_child(parent_item, child_ix, parent_checkstate)

    def propagate_checkstate_parent(self, item, item_checkstate):
        parent_item = item.parent()
        if parent_item is not None:
            if self.all_sibling_checked(item):
                parent_item.setCheckState(Qt.Checked)
            if item_checkstate in (Qt.Checked, Qt.PartiallyChecked) and parent_item.checkState() == Qt.Unchecked:
                parent_item.setCheckState(Qt.PartiallyChecked)
            if item_checkstate in (Qt.Unchecked, Qt.PartiallyChecked) and parent_item.checkState() == Qt.Checked:
                parent_item.setCheckState(Qt.PartiallyChecked)

    def all_sibling_checked(self, item):
        all_checked = True
        if item.parent() is not None:
            parent_item = item.parent()
            nchild = parent_item.rowCount()
            for child_ix in range(nchild):
                if parent_item.child(child_ix).checkState() in (Qt.Unchecked, Qt.PartiallyChecked):
                    all_checked = False
                    break
        return all_checked

    def expand_items(self, tree, parent_item, child_ix, expanded_items):
        item = parent_item.child(child_ix)
        if item.data(Qt.UserRole) in expanded_items:
            tree.setExpanded(item.index(), True)
        parent_item = parent_item.child(child_ix)
        nchild = parent_item.rowCount()
        if nchild > 0:
            for child_ix in range(nchild):
                self.expand_items(tree, parent_item, child_ix, expanded_items)

    def list_expanded(self, tree, parent_item, child_ix, expanded_items):
        # print(type(parent_item.child(0)))
        item = parent_item.child(child_ix)
        if tree.isExpanded(item.index()):
            expanded_items.append(item.data(Qt.UserRole))
        parent_item = parent_item.child(child_ix)
        nchild = parent_item.rowCount()
        if nchild > 0:
            for child_ix in range(nchild):
                self.list_expanded(tree, parent_item, child_ix, expanded_items)

    def list_unchecked(self, parent_item, child_ix, unchecked_items):
        item = parent_item.child(child_ix)
        if item.checkState() == Qt.Unchecked:
                unchecked_items.append(item.data(Qt.UserRole))
        parent_item = parent_item.child(child_ix)
        nchild = parent_item.rowCount()
        if nchild > 0:
            for child_ix in range(nchild):
                self.list_unchecked(parent_item, child_ix, unchecked_items)

    def on_item_change_threaded(self, item):
        worker = Worker(self.on_item_change, item)
        worker.signals.started.connect(self.on_item_change_started)
        worker.signals.result.connect(self.on_item_change_finished)
        self.threadpool.start(worker)

    def on_item_change_started(self):
        self.status_label.setText('Refreshing tree, please wait...')

    def on_item_change_finished(self):
        self.status_label.setText('')

    def build_tree_structure_threaded(self, root_path):
        worker = Worker(record_stat, root_path)
        worker.signals.started.connect(self.build_tree_started)
        worker.signals.result.connect(self.build_tree_finished)
        self.threadpool.start(worker)

    def build_tree_started(self):
        self.status_label.setText('Building tree, please wait...')

    def build_tree_finished(self, result):
        self.og_dir_dict = result
        # self.anon_dir_dict = deepcopy(self.og_dir_dict)
        self.anon_dir_dict = _pickle.loads(_pickle.dumps(self.og_dir_dict))
        self.refresh_treeview(self.og_model, self.og_tree, self.og_dir_dict)
        self.refresh_treeview(self.anon_model, self.anon_tree, self.anon_dir_dict, checkable=False, anon_tree=True)
        self.status_label.setText('')

    def preview_anon_tree(self):
        start = time.time()
        # self.anon_dir_dict = deepcopy(self.og_dir_dict)
        self.anon_dir_dict = _pickle.loads(_pickle.dumps(self.og_dir_dict))
        print(start - time.time())
        start = time.time()
        self.anon_dir_dict = anonymize_stat(self.anon_dir_dict, self.unchecked_items_set, self.renamed_items_dict)
        print(start - time.time())
        start = time.time()
        self.refresh_treeview(self.anon_model, self.anon_tree, self.anon_dir_dict, checkable=False, anon_tree=True)
        print(start - time.time())
        start = time.time()
        self.expanded_items_list = []
        self.list_expanded(self.og_tree, self.og_root_item, 0, self.expanded_items_list)
        self.expand_items(self.anon_tree, self.anon_root_item, 0, self.expanded_items_list)
        print(start - time.time())
        self.display_user_folder_props()

    def preview_anon_tree_threaded(self):
        worker = Worker(self.preview_anon_tree)
        worker.signals.started.connect(self.preview_anon_tree_started)
        worker.signals.result.connect(self.preview_anon_tree_finished)
        self.threadpool.start(worker)

    def preview_anon_tree_started(self):
        self.status_label.setText('Constructing preview tree, please wait...')

    def preview_anon_tree_finished(self):
        self.status_label.setText('')

    def display_user_folder_props(self):
        self.user_folder_props = drive_measurement(self.anon_dir_dict)
        self.user_folder_typical = check_collection_properties(self.user_folder_props)
        status_str = ''
        for key in self.user_folder_props.keys():
            status_str += key + ': ' + str(self.user_folder_props[key]) + '\n'
        self.user_folder_props_label.setText(status_str)
        self.user_folder_typical_label.setText('Values are typical: ' + str(self.user_folder_typical))

    def show_file_dialog(self):
        dirpath = QFileDialog.getExistingDirectory(self, 'Select Folder', self.root_path)
        if dirpath:
            self.root_path = os.path.abspath(dirpath)
            self.folder_edit.setText(self.root_path)
            self.build_tree_structure_threaded(self.root_path)

    def upload_collected_data(self, data):
        data = bytes(json.dumps(data), 'utf8')
        data = compress_data(data)
        encrypted_json, encrypted_jsonkey = encrypt_data(data)
        dropbox_upload(encrypted_json,
                       generate_filename(self.dbx_json_dirpath, suffix='_dir_dict.enc'))
        dropbox_upload(encrypted_jsonkey,
                       generate_filename(self.dbx_json_dirpath, suffix='_sym_key.enc'))

    def test_script(self):
        unchecked_items_list = []
        self.list_unchecked(self.root_item, 0, unchecked_items_list)
        print(set(self.og_dir_dict.keys()).difference(self.anon_dir_dict.keys()))
        print(unchecked_items_list)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    daw = DriveAnalysisWidget()
    sys.exit(app.exec_())
