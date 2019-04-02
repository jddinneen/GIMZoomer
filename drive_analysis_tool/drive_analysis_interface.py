"""
waitingspinnerwidget from https://github.com/z3ntu/QtWaitingSpinner
"""

import _pickle
import json
import sys
import traceback
from pathlib import Path

from PyQt5.QtCore import (Qt, pyqtSlot, pyqtSignal, QObject, QRunnable,
                          QThreadPool)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont, QIcon
from PyQt5.QtWidgets import (QWidget, QPushButton, QApplication, QFileDialog,
                             QGridLayout, QLabel, QTreeView, QHeaderView,
                             QTableWidget, QTableWidgetItem, QTabWidget,
                             QMessageBox, QSplitter, QVBoxLayout)
from drive_analyzer import (record_stat, anonymize_stat, drive_measurement,
                            check_collection_properties)
from submit_data import (compress_data, encrypt_data, dropbox_upload,
                         generate_filename, get_filepath)
from waitingspinnerwidget import QtWaitingSpinner


def path_str(root_path):
    """ Converts path to string, returns '' if path is None """
    if root_path is None:
        return ''
    elif isinstance(root_path, Path):
        return str(root_path)
    else:
        raise TypeError('Invalid type used for root_path, '
                        'should be pathlib.Path or NoneType')


def is_root_overlap(rootx_name, rootx, root_list):
    """ Checks if rootx path overlaps with roots in root_list """
    rootx = Path(rootx)
    root_list = [Path(root) for root in root_list if root]
    for other_root in root_list:
        if other_root in rootx.parents:
            return ('Unable to select directory.\n' + rootx_name +
                    ' is a subdirectory of another root folder.')
        elif rootx in other_root.parents:
            return ('Unable to select directory.\n' + rootx_name +
                    ' is a parent directory of another root folder.')
        elif rootx == other_root:
            return ('Unable to select directory.\n' + rootx_name +
                    ' has already been selected in another tab.')
    return False


def str_none_num(value):
    """ If None, return an empty string. If a number, round it then return a
    formatted string. """
    if isinstance(value, (int, float)):
        return '{:,}'.format(round(value, 1))
    else:
        return ''


# TODO: Fix: simplify_tree crashes when all folders do not contain a single
# file due to dir_dict being empty
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

        self.setWindowIcon(QIcon('images/icons8-opened-folder-480.png'))
        self.setWindowTitle('Drive Analysis Tool')
        self.root_path = None
        # self.root_path = Path('~/Dropbox/academic').expanduser()
        self.root_path_2 = None
        # self.root_path_2 = Path('~/Dropbox/personal').expanduser()
        self.root_path_3 = None
        # self.root_path_3 = Path('~/Dropbox/mcgill/2018 Winter').expanduser()
        self.root_path_4 = None
        # self.root_path_4 = Path('~/Dropbox/mcgill/2017 Fall').expanduser()
        self.dbx_json_dirpath = '/'
        self.threadpool = QThreadPool()
        self.expanded_items_list = []
        self.expanded_items_list_2 = []
        self.expanded_items_list_3 = []
        self.expanded_items_list_4 = []
        self.unchecked_items_set = set()
        self.unchecked_items_set_2 = set()
        self.unchecked_items_set_3 = set()
        self.unchecked_items_set_4 = set()
        self.renamed_items_dict = dict()
        self.renamed_items_dict_2 = dict()
        self.renamed_items_dict_3 = dict()
        self.renamed_items_dict_4 = dict()

        self.og_dir_dict, self.anon_dir_dict = dict(), dict()
        self.og_dir_dict_2, self.anon_dir_dict_2 = dict(), dict()
        self.og_dir_dict_3, self.anon_dir_dict_3 = dict(), dict()
        self.og_dir_dict_4, self.anon_dir_dict_4 = dict(), dict()
        self.user_folder_props = dict()
        self.typical_folder_props = dict()
        self.user_folder_diffs = dict()
        self.user_folder_typical = True

        self.folder_edit = QLabel()
        self.folder_edit.setText(path_str(self.root_path))
        self.folder_edit_2 = QLabel()
        self.folder_edit_2.setText(path_str(self.root_path_2))
        self.folder_edit_3 = QLabel()
        self.folder_edit_3.setText(path_str(self.root_path_3))
        self.folder_edit_4 = QLabel()
        self.folder_edit_4.setText(path_str(self.root_path_4))

        self.og_tree = QTreeView()
        self.og_model = QStandardItemModel()
        self.anon_tree = QTreeView()
        self.anon_model = QStandardItemModel()
        self.og_tree_2 = QTreeView()
        self.og_model_2 = QStandardItemModel()
        self.anon_tree_2 = QTreeView()
        self.anon_model_2 = QStandardItemModel()
        self.og_tree_3 = QTreeView()
        self.og_model_3 = QStandardItemModel()
        self.anon_tree_3 = QTreeView()
        self.anon_model_3 = QStandardItemModel()
        self.og_tree_4 = QTreeView()
        self.og_model_4 = QStandardItemModel()
        self.anon_tree_4 = QTreeView()
        self.anon_model_4 = QStandardItemModel()

        select_btn_txt = 'Select Root'
        select_btn = QPushButton(select_btn_txt, self)
        select_btn.setToolTip('Select <b>personal folder</b> '
                              'for data collection.')
        select_btn.clicked.connect(self.show_file_dialog)
        select_btn.resize(select_btn.sizeHint())
        select_btn_2 = QPushButton(select_btn_txt, self)
        select_btn_2.setToolTip('Select <b>second personal folder '
                                '(if any)</b> for data collection.')
        select_btn_2.clicked.connect(self.show_file_dialog_2)
        select_btn_2.resize(select_btn_2.sizeHint())
        select_btn_3 = QPushButton(select_btn_txt, self)
        select_btn_3.setToolTip('Select <b>third personal folder '
                                '(if any)</b> for data collection.')
        select_btn_3.clicked.connect(self.show_file_dialog_3)
        select_btn_3.resize(select_btn_3.sizeHint())
        select_btn_4 = QPushButton(select_btn_txt, self)
        select_btn_4.setToolTip('Select <b>fourth personal folder '
                                '(if any)</b> for data collection.')
        select_btn_4.clicked.connect(self.show_file_dialog_4)
        select_btn_4.resize(select_btn_4.sizeHint())

        self.alert_box = QMessageBox()
        self.no_root_error_msg = ('No folder selected. '
                                  'To exclude root folder from submission, '
                                  '<b>click \'Select Root\'</b> then '
                                  '<b>click \'Cancel\'</b>.')

        self.submit_btn = QPushButton('Submit', self)
        self.submit_btn.setToolTip('Submit encrypted folder data to the cloud')
        self.submit_btn.clicked.connect(self.upload_collected_data_threaded)
        self.submit_btn.resize(self.submit_btn.sizeHint())
        self.submit_btn.setEnabled(True)

        self.cancel_btn = QPushButton('Cancel')
        self.cancel_btn.setToolTip('Quit program without collecting any data.')
        self.cancel_btn.clicked.connect(self.close)
        self.cancel_btn.resize(self.cancel_btn.sizeHint())
        self.cancel_btn.setEnabled(True)

        self.user_folder_props_label = QLabel()
        self.user_folder_props_label.setAlignment(Qt.AlignCenter)
        self.user_folder_props_label.setText('Characteristics of '
                                             'all roots\' structures')

        labels = [
            'Scale',  # category header
            'Total files', 'Total folders',
            'Folder structure',  # category header
            'Greatest breadth of folder tree',
            'Average breadth of folder tree', '# folders at root',
            '# leaf folders (folders without subfolders)',
            '% leaf folders (folders without subfolders)',
            'Average depth of leaf folders (folders without subfolders)',
            '# switch folders (folders with subfolders and no files)',
            '% switch folders (folders with subfolders and no files)',
            'Average depth of switch folders '
            '(folders with subfolders and no files)',
            'Greatest depth where folders are found',
            'Folder waist (depth where folders are most commonly found)',
            'Average depth where folders are found',
            'Branching factor (average subfolders per folder, '
            'excepting leaf folders)',
            'File structure',  # category header
            '# files at root', 'Average # files in folders',
            '# empty folders', '% empty folders',
            'Average depth where files are found',
            'Depth where files are most commonly found',
            '# files at depth where files are most commonly found'
        ]
        label_keys = [
            '_CAT1',  # category header
            'n_files', 'n_folders',
            '_CAT2',  # category header
            'breadth_max', 'breadth_mean', 'root_n_folders', 'n_leaf_folders',
            'pct_leaf_folders', 'depth_leaf_folders_mean', 'n_switch_folders',
            'pct_switch_folders', 'depth_switch_folders_mean', 'depth_max',
            'depth_folders_mode', 'depth_folders_mean', 'branching_factor',
            '_CAT3',  # category header
            'root_n_files', 'n_files_mean', 'n_empty_folders',
            'pct_empty_folders', 'depth_files_mean', 'depth_files_mode',
            'file_breadth_mode_n_files'
        ]
        self.n_props = len(label_keys)
        self.user_folder_props_table = QTableWidget()
        self.user_folder_props_table.verticalHeader().setVisible(False)
        self.user_folder_props_table.setRowCount(self.n_props)
        self.user_folder_props_table.setColumnCount(5)
        for row, label, label_key in zip(
                range(self.n_props), labels, label_keys):
            if label_key[0] == '_':
                self.user_folder_props_table.setSpan(row, 0, 1, 5)
                label_item = QTableWidgetItem(label)
                label_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                q_font = QFont()
                q_font.setStyleHint(QFont.AnyStyle)
                q_font.setBold(True)
                label_item.setFont(q_font)
                label_item.setData(Qt.UserRole, label_key)
                self.user_folder_props_table.setItem(row, 0, label_item)
            else:
                label_item = QTableWidgetItem(label)
                label_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                label_item.setData(Qt.UserRole, label_key)
                value_item, min_item, max_item, diff_item = \
                    self.empty_folder_props()
                self.user_folder_props_table.setItem(row, 0, label_item)
                self.user_folder_props_table.setItem(row, 1, value_item)
                self.user_folder_props_table.setItem(row, 2, min_item)
                self.user_folder_props_table.setItem(row, 3, max_item)
                self.user_folder_props_table.setItem(row, 4, diff_item)
        self.user_folder_props_table.setHorizontalHeaderLabels([
            'Property', 'Value', 'min', 'max', 'diff'])
        self.header_autoresizable(
            self.user_folder_props_table.horizontalHeader())

        og_tree_txt = 'Original folders data'
        anon_tree_txt = 'Folders data to be used for research'
        # Label original and anonymized tree for root 1
        og_tree_label = QLabel()
        og_tree_label.setAlignment(Qt.AlignCenter)
        og_tree_label.setText(og_tree_txt)
        anon_tree_label = QLabel()
        anon_tree_label.setAlignment(Qt.AlignCenter)
        anon_tree_label.setText(anon_tree_txt)
        # Label original and anonymized tree for root 2
        og_tree_label_2 = QLabel()
        og_tree_label_2.setAlignment(Qt.AlignCenter)
        og_tree_label_2.setText(og_tree_txt)
        anon_tree_label_2 = QLabel()
        anon_tree_label_2.setAlignment(Qt.AlignCenter)
        anon_tree_label_2.setText(anon_tree_txt)
        # Label original and anonymized tree for root 3
        og_tree_label_3 = QLabel()
        og_tree_label_3.setAlignment(Qt.AlignCenter)
        og_tree_label_3.setText(og_tree_txt)
        anon_tree_label_3 = QLabel()
        anon_tree_label_3.setAlignment(Qt.AlignCenter)
        anon_tree_label_3.setText(anon_tree_txt)
        # Label original and anonymized tree for root 4
        og_tree_label_4 = QLabel()
        og_tree_label_4.setAlignment(Qt.AlignCenter)
        og_tree_label_4.setText(og_tree_txt)
        anon_tree_label_4 = QLabel()
        anon_tree_label_4.setAlignment(Qt.AlignCenter)
        anon_tree_label_4.setText(anon_tree_txt)

        og_model_headers = ['Folder Name', 'Renamed Folder', 'Number of Files']
        anon_model_headers = ['Folder Name', 'Number of Files']
        # Initialize model and tree for root 1
        self.og_tree.setModel(self.og_model)
        self.og_model.setHorizontalHeaderLabels(og_model_headers)
        self.og_root_item = self.og_model.invisibleRootItem()
        self.refresh_treeview(self.og_model, self.og_tree, self.og_dir_dict)
        self.og_model.itemChanged.connect(self.on_item_change_threaded)

        self.anon_tree.setModel(self.anon_model)
        self.anon_model.setHorizontalHeaderLabels(anon_model_headers)
        self.anon_root_item = self.anon_model.invisibleRootItem()
        self.refresh_treeview(
            self.anon_model, self.anon_tree, self.anon_dir_dict,
            checkable=False, anon_tree=True)

        # Initialize model and tree for root 2
        self.og_tree_2.setModel(self.og_model_2)
        self.og_model_2.setHorizontalHeaderLabels(og_model_headers)
        self.og_root_item_2 = self.og_model_2.invisibleRootItem()
        self.refresh_treeview(self.og_model_2, self.og_tree_2,
                              self.og_dir_dict_2)
        self.og_model_2.itemChanged.connect(self.on_item_change_threaded_2)

        self.anon_tree_2.setModel(self.anon_model_2)
        self.anon_model_2.setHorizontalHeaderLabels(anon_model_headers)
        self.anon_root_item_2 = self.anon_model_2.invisibleRootItem()
        self.refresh_treeview(
            self.anon_model_2, self.anon_tree_2, self.anon_dir_dict_2,
            checkable=False, anon_tree=True)

        # Initialize model and tree for root 3
        self.og_tree_3.setModel(self.og_model_3)
        self.og_model_3.setHorizontalHeaderLabels(og_model_headers)
        self.og_root_item_3 = self.og_model_3.invisibleRootItem()
        self.refresh_treeview(self.og_model_3, self.og_tree_3,
                              self.og_dir_dict_3)
        self.og_model_3.itemChanged.connect(self.on_item_change_threaded_3)

        self.anon_tree_3.setModel(self.anon_model_3)
        self.anon_model_3.setHorizontalHeaderLabels(anon_model_headers)
        self.anon_root_item_3 = self.anon_model_3.invisibleRootItem()
        self.refresh_treeview(
            self.anon_model_3, self.anon_tree_3, self.anon_dir_dict_3,
            checkable=False, anon_tree=True)

        # Initialize model and tree for root 4
        self.og_tree_4.setModel(self.og_model_4)
        self.og_model_4.setHorizontalHeaderLabels(og_model_headers)
        self.og_root_item_4 = self.og_model_4.invisibleRootItem()
        self.refresh_treeview(self.og_model_4, self.og_tree_4,
                              self.og_dir_dict_4)
        self.og_model_4.itemChanged.connect(self.on_item_change_threaded_4)

        self.anon_tree_4.setModel(self.anon_model_4)
        self.anon_model_4.setHorizontalHeaderLabels(anon_model_headers)
        self.anon_root_item_4 = self.anon_model_4.invisibleRootItem()
        self.refresh_treeview(
            self.anon_model_4, self.anon_tree_4, self.anon_dir_dict_4,
            checkable=False, anon_tree=True)

        if self.root_path:
            self.build_tree_structure_threaded(self.root_path)
        if self.root_path_2:
            self.build_tree_structure_threaded_2(self.root_path_2)
        if self.root_path_3:
            self.build_tree_structure_threaded_3(self.root_path_3)
        if self.root_path_4:
            self.build_tree_structure_threaded_4(self.root_path_4)

        # Initialize tab screen
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tab4 = QWidget()
        # Add tabs
        self.tabs.addTab(self.tab1, "Root Folder 1")
        self.tabs.addTab(self.tab2, "Root Folder 2")
        self.tabs.addTab(self.tab3, "Root Folder 3")
        self.tabs.addTab(self.tab4, "Root Folder 4")
        # Create first tab
        self.tab1.layout = QGridLayout()
        self.tab1.layout.addWidget(select_btn, 0, 0, 1, 1)
        self.tab1.layout.addWidget(self.folder_edit, 0, 1, 1, 6)
        self.tab1.layout.addWidget(og_tree_label, 1, 0, 1, 5)
        self.tab1.layout.addWidget(anon_tree_label, 1, 5, 1, 3)
        self.tab1.layout.addWidget(self.og_tree, 2, 0, 1, 5)
        self.tab1.layout.addWidget(self.anon_tree, 2, 5, 1, 3)
        self.tab1.setLayout(self.tab1.layout)
        # Create second tab
        self.tab2.layout = QGridLayout()
        self.tab2.layout.addWidget(select_btn_2, 0, 0, 1, 1)
        self.tab2.layout.addWidget(self.folder_edit_2, 0, 1, 1, 6)
        self.tab2.layout.addWidget(og_tree_label_2, 1, 0, 1, 5)
        self.tab2.layout.addWidget(anon_tree_label_2, 1, 5, 1, 3)
        self.tab2.layout.addWidget(self.og_tree_2, 2, 0, 1, 5)
        self.tab2.layout.addWidget(self.anon_tree_2, 2, 5, 1, 3)
        self.tab2.setLayout(self.tab2.layout)
        # Create third tab
        self.tab3.layout = QGridLayout()
        self.tab3.layout.addWidget(select_btn_3, 0, 0, 1, 1)
        self.tab3.layout.addWidget(self.folder_edit_3, 0, 1, 1, 6)
        self.tab3.layout.addWidget(og_tree_label_3, 1, 0, 1, 5)
        self.tab3.layout.addWidget(anon_tree_label_3, 1, 5, 1, 3)
        self.tab3.layout.addWidget(self.og_tree_3, 2, 0, 1, 5)
        self.tab3.layout.addWidget(self.anon_tree_3, 2, 5, 1, 3)
        self.tab3.setLayout(self.tab3.layout)
        # Create fourth tab
        self.tab4.layout = QGridLayout()
        self.tab4.layout.addWidget(select_btn_4, 0, 0, 1, 1)
        self.tab4.layout.addWidget(self.folder_edit_4, 0, 1, 1, 6)
        self.tab4.layout.addWidget(og_tree_label_4, 1, 0, 1, 5)
        self.tab4.layout.addWidget(anon_tree_label_4, 1, 5, 1, 3)
        self.tab4.layout.addWidget(self.og_tree_4, 2, 0, 1, 5)
        self.tab4.layout.addWidget(self.anon_tree_4, 2, 5, 1, 3)
        self.tab4.setLayout(self.tab4.layout)

        bottom_hbox = QGridLayout()
        bottom_hbox.setColumnStretch(0, 6)
        bottom_hbox.setColumnStretch(6, 1)
        bottom_hbox.setColumnStretch(7, 1)
        bottom_hbox.addWidget(self.submit_btn, 0, 6, 1, 1)
        bottom_hbox.addWidget(self.cancel_btn, 0, 7, 1, 1)
        bottom_grid = QVBoxLayout()
        bottom_grid.addWidget(self.user_folder_props_label)
        bottom_grid.addWidget(self.user_folder_props_table)
        bottom_grid.addLayout(bottom_hbox)

        bottom_grid_widget = QWidget()
        bottom_grid_widget.setLayout(bottom_grid)
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.tabs)
        splitter.addWidget(bottom_grid_widget)
        splitter.setStyleSheet(
            "QSplitter::handle {image: url(images/icons8-more-64.png);}")
        splitter.setHandleWidth(5)

        vbox = QVBoxLayout(self)
        vbox.addWidget(splitter)
        self.setLayout(vbox)
        self.resize(1280, 720)

        self.spinner = QtWaitingSpinner(self, True, True, Qt.ApplicationModal)
        self.spinner.setRoundness(70.0)
        self.spinner.setMinimumTrailOpacity(15.0)
        self.spinner.setTrailFadePercentage(70.0)
        self.spinner.setNumberOfLines(12)
        self.spinner.setLineLength(30)
        self.spinner.setLineWidth(10)
        self.spinner.setInnerRadius(15)
        self.spinner.setRevolutionsPerSecond(1)

        self.show()

    def refresh_treeview(self, model, tree, dir_dict,
                         checkable=True, anon_tree=False):
        model.removeRow(0)
        root_item = model.invisibleRootItem()
        # dir_dict key starts at 1 since 0==False
        self.append_all_children(1, dir_dict, root_item, checkable, anon_tree)
        tree.expandToDepth(0)
        self.header_autoresizable(tree.header())

    def append_all_children(self, dirkey, dir_dict, parent_item,
                            checkable=True, anon_tree=False):
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
                dirname.setFlags(
                    Qt.ItemIsEnabled | Qt.ItemIsUserTristate |
                    Qt.ItemIsUserCheckable)
                dirname.setCheckState(Qt.Checked)
                dirname_edited.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable)
                nfiles.setFlags(Qt.ItemIsEnabled)
            parent_item.appendRow(items)
            child_ix = parent_item.rowCount() - 1
            parent_item = parent_item.child(child_ix)
            children_keys = dir_dict[dirkey]['childkeys']
            for child_key in sorted(children_keys):
                self.append_all_children(child_key, dir_dict, parent_item,
                                         checkable, anon_tree)

    def on_item_change(self, item):
        if item.column() == 0:
            dirkey = item.data(Qt.UserRole)
            if (item.rowCount() == 0
                    and item.checkState() == Qt.PartiallyChecked):
                item.setCheckState(Qt.Checked)
            item_checkstate = item.checkState()
            parent_item = item.parent()
            if parent_item is None:
                nchild = item.rowCount()
                if nchild > 0:
                    for child_ix in range(nchild):
                        self.propagate_checkstate_child(
                            item, child_ix, item_checkstate,
                            self.unchecked_items_set)
            if parent_item is not None:
                child_ix = item.row()
                self.propagate_checkstate_child(
                    parent_item, child_ix, item_checkstate,
                    self.unchecked_items_set)
                self.propagate_checkstate_parent(
                    item, item_checkstate, self.unchecked_items_set)
            if item_checkstate == Qt.Unchecked:
                self.unchecked_items_set.add(dirkey)
            elif item_checkstate in (Qt.Checked, Qt.PartiallyChecked):
                if dirkey in self.unchecked_items_set:
                    self.unchecked_items_set.remove(dirkey)
        if item.column() == 1:
            dirkey = item.data(Qt.UserRole)
            self.renamed_items_dict[dirkey] = item.text()

    def on_item_change_threaded(self, item):
        worker = Worker(self.on_item_change, item)
        worker.signals.started.connect(self.on_item_change_started)
        worker.signals.result.connect(self.on_item_change_finished)
        self.threadpool.start(worker)

    def on_item_change_started(self):
        """ Status messages during tree modification should be placed here. """
        self.spinner.start()

    def on_item_change_finished(self):
        """ Status messages when tree modification is complete should be
        placed here. """
        self.preview_anon_tree_threaded()
        self.spinner.stop()

    def on_item_change_2(self, item):
        if item.column() == 0:
            dirkey = item.data(Qt.UserRole)
            if (item.rowCount() == 0
                    and item.checkState() == Qt.PartiallyChecked):
                item.setCheckState(Qt.Checked)
            item_checkstate = item.checkState()
            parent_item = item.parent()
            if parent_item is None:
                nchild = item.rowCount()
                if nchild > 0:
                    for child_ix in range(nchild):
                        self.propagate_checkstate_child(
                            item, child_ix, item_checkstate,
                            self.unchecked_items_set_2)
            if parent_item is not None:
                child_ix = item.row()
                self.propagate_checkstate_child(
                    parent_item, child_ix, item_checkstate,
                    self.unchecked_items_set_2)
                self.propagate_checkstate_parent(
                    item, item_checkstate, self.unchecked_items_set_2)
            if item_checkstate == Qt.Unchecked:
                self.unchecked_items_set_2.add(dirkey)
            elif item_checkstate in (Qt.Checked, Qt.PartiallyChecked):
                if dirkey in self.unchecked_items_set_2:
                    self.unchecked_items_set_2.remove(dirkey)
        if item.column() == 1:
            dirkey = item.data(Qt.UserRole)
            self.renamed_items_dict_2[dirkey] = item.text()

    def on_item_change_threaded_2(self, item):
        worker = Worker(self.on_item_change_2, item)
        worker.signals.started.connect(self.on_item_change_started_2)
        worker.signals.result.connect(self.on_item_change_finished_2)
        self.threadpool.start(worker)

    def on_item_change_started_2(self):
        """ Status messages during tree modification should be placed here. """
        self.spinner.start()

    def on_item_change_finished_2(self):
        """ Status messages when tree modification is complete should be
        placed here. """
        self.preview_anon_tree_threaded_2()
        self.spinner.stop()

    def on_item_change_3(self, item):
        if item.column() == 0:
            dirkey = item.data(Qt.UserRole)
            if (item.rowCount() == 0
                    and item.checkState() == Qt.PartiallyChecked):
                item.setCheckState(Qt.Checked)
            item_checkstate = item.checkState()
            parent_item = item.parent()
            if parent_item is None:
                nchild = item.rowCount()
                if nchild > 0:
                    for child_ix in range(nchild):
                        self.propagate_checkstate_child(
                            item, child_ix, item_checkstate,
                            self.unchecked_items_set_3)
            if parent_item is not None:
                child_ix = item.row()
                self.propagate_checkstate_child(
                    parent_item, child_ix, item_checkstate,
                    self.unchecked_items_set_3)
                self.propagate_checkstate_parent(
                    item, item_checkstate, self.unchecked_items_set_3)
            if item_checkstate == Qt.Unchecked:
                self.unchecked_items_set_3.add(dirkey)
            elif item_checkstate in (Qt.Checked, Qt.PartiallyChecked):
                if dirkey in self.unchecked_items_set_3:
                    self.unchecked_items_set_3.remove(dirkey)
        if item.column() == 1:
            dirkey = item.data(Qt.UserRole)
            self.renamed_items_dict_3[dirkey] = item.text()

    def on_item_change_threaded_3(self, item):
        worker = Worker(self.on_item_change_3, item)
        worker.signals.started.connect(self.on_item_change_started_3)
        worker.signals.result.connect(self.on_item_change_finished_3)
        self.threadpool.start(worker)

    def on_item_change_started_3(self):
        """ Status messages during tree modification should be placed here. """
        self.spinner.start()

    def on_item_change_finished_3(self):
        """ Status messages when tree modification is complete should be
        placed here. """
        self.preview_anon_tree_threaded_3()
        self.spinner.stop()

    def on_item_change_4(self, item):
        if item.column() == 0:
            dirkey = item.data(Qt.UserRole)
            if (item.rowCount() == 0
                    and item.checkState() == Qt.PartiallyChecked):
                item.setCheckState(Qt.Checked)
            item_checkstate = item.checkState()
            parent_item = item.parent()
            if parent_item is None:
                nchild = item.rowCount()
                if nchild > 0:
                    for child_ix in range(nchild):
                        self.propagate_checkstate_child(
                            item, child_ix, item_checkstate,
                            self.unchecked_items_set_4)
            if parent_item is not None:
                child_ix = item.row()
                self.propagate_checkstate_child(
                    parent_item, child_ix, item_checkstate,
                    self.unchecked_items_set_4)
                self.propagate_checkstate_parent(
                    item, item_checkstate, self.unchecked_items_set_4)
            if item_checkstate == Qt.Unchecked:
                self.unchecked_items_set_4.add(dirkey)
            elif item_checkstate in (Qt.Checked, Qt.PartiallyChecked):
                if dirkey in self.unchecked_items_set_4:
                    self.unchecked_items_set_4.remove(dirkey)
        if item.column() == 1:
            dirkey = item.data(Qt.UserRole)
            self.renamed_items_dict_4[dirkey] = item.text()

    def on_item_change_threaded_4(self, item):
        worker = Worker(self.on_item_change_4, item)
        worker.signals.started.connect(self.on_item_change_started_4)
        worker.signals.result.connect(self.on_item_change_finished_4)
        self.threadpool.start(worker)

    def on_item_change_started_4(self):
        """ Status messages during tree modification should be placed here. """
        self.spinner.start()

    def on_item_change_finished_4(self):
        """ Status messages when tree modification is complete should be
        placed here. """
        self.preview_anon_tree_threaded_4()
        self.spinner.stop()

    def propagate_checkstate_child(
            self, parent_item, child_ix, parent_checkstate,
            unchecked_set=None):
        """ If parent has a full/no checkmark, make sure all the children's
        checkboxes are ticked/not ticked as well. """
        if parent_checkstate != Qt.PartiallyChecked:
            parent_item.child(child_ix).setCheckState(parent_checkstate)
            parent_item = parent_item.child(child_ix)
            nchild = parent_item.rowCount()
            if unchecked_set is not None:
                dirkey = parent_item.data(Qt.UserRole)
                if parent_checkstate == Qt.Unchecked:
                    unchecked_set.add(dirkey)
                if parent_checkstate == Qt.Checked and dirkey in unchecked_set:
                    unchecked_set.remove(dirkey)
            if nchild > 0:
                for child_ix in range(nchild):
                    self.propagate_checkstate_child(
                        parent_item, child_ix, parent_checkstate,
                        unchecked_set)

    def propagate_checkstate_parent(self, item, item_checkstate,
                                    unchecked_set=None):
        """ If some children are unchecked, make parent partially checked.
        If all children are checked, give parent a full checkmark. """
        parent_item = item.parent()
        if parent_item is not None:
            checkstate_to_propagate = False
            dirkey = parent_item.data(Qt.UserRole)
            if self.all_sibling_checked(item):
                checkstate_to_propagate = Qt.Checked
            elif (item_checkstate in (Qt.Checked, Qt.PartiallyChecked)
                    and parent_item.checkState() == Qt.Unchecked):
                checkstate_to_propagate = Qt.PartiallyChecked
            elif (item_checkstate in (Qt.Unchecked, Qt.PartiallyChecked)
                    and parent_item.checkState() == Qt.Checked):
                checkstate_to_propagate = Qt.PartiallyChecked
            if checkstate_to_propagate:
                parent_item.setCheckState(checkstate_to_propagate)
                if unchecked_set is not None and dirkey in unchecked_set:
                    unchecked_set.remove(dirkey)
                self.propagate_checkstate_parent(
                    parent_item, checkstate_to_propagate, unchecked_set)

    def all_sibling_checked(self, item):
        """ Determine if siblings (items sharing the same parent and are on
        the same tree level) are all checked. """
        all_checked = True
        if item.parent() is not None:
            parent_item = item.parent()
            nchild = parent_item.rowCount()
            for child_ix in range(nchild):
                if parent_item.child(child_ix).checkState() in (
                        Qt.Unchecked, Qt.PartiallyChecked):
                    all_checked = False
                    break
        return all_checked

    def expand_items(self, tree, parent_item, child_ix, expanded_items):
        """ Have the expanded items on one tree mirror that of another tree """
        item = parent_item.child(child_ix)
        if item.data(Qt.UserRole) in expanded_items:
            tree.setExpanded(item.index(), True)
        parent_item = parent_item.child(child_ix)
        nchild = parent_item.rowCount()
        if nchild > 0:
            for child_ix in range(nchild):
                self.expand_items(tree, parent_item, child_ix, expanded_items)

    def list_expanded(self, tree, parent_item, child_ix, expanded_items):
        """ List the expanded items of a tree. """
        item = parent_item.child(child_ix)
        if tree.isExpanded(item.index()):
            expanded_items.append(item.data(Qt.UserRole))
        parent_item = parent_item.child(child_ix)
        nchild = parent_item.rowCount()
        if nchild > 0:
            for child_ix in range(nchild):
                self.list_expanded(tree, parent_item, child_ix, expanded_items)

    def list_unchecked(self, parent_item, child_ix, unchecked_items):
        """ List the unchecked items of a tree. """
        item = parent_item.child(child_ix)
        if item.checkState() == Qt.Unchecked:
                unchecked_items.append(item.data(Qt.UserRole))
        parent_item = parent_item.child(child_ix)
        nchild = parent_item.rowCount()
        if nchild > 0:
            for child_ix in range(nchild):
                self.list_unchecked(parent_item, child_ix, unchecked_items)

    def build_tree_structure_threaded(self, root_path):
        worker = Worker(record_stat, root_path)
        worker.signals.started.connect(self.build_tree_started)
        worker.signals.result.connect(self.build_tree_finished)
        self.threadpool.start(worker)

    def build_tree_started(self):
        """ Status messages when building a tree should be placed here. """
        self.expanded_items_list = []
        self.unchecked_items_set = set()
        self.renamed_items_dict = dict()
        self.spinner.start()

    def build_tree_finished(self, result):
        """ Status messages when tree building is complete should be
        placed here. """
        self.og_dir_dict = result
        self.anon_dir_dict = _pickle.loads(_pickle.dumps(self.og_dir_dict))
        self.refresh_treeview(self.og_model, self.og_tree, self.og_dir_dict)
        self.refresh_treeview(
            self.anon_model, self.anon_tree, self.anon_dir_dict,
            checkable=False, anon_tree=True)
        self.preview_anon_tree_threaded()
        self.spinner.stop()

    def build_tree_structure_threaded_2(self, root_path):
        worker = Worker(record_stat, root_path)
        worker.signals.started.connect(self.build_tree_started_2)
        worker.signals.result.connect(self.build_tree_finished_2)
        self.threadpool.start(worker)

    def build_tree_started_2(self):
        """ Status messages when building a tree should be placed here. """
        self.expanded_items_list_2 = []
        self.unchecked_items_set_2 = set()
        self.renamed_items_dict_2 = dict()
        self.spinner.start()

    def build_tree_finished_2(self, result):
        """ Status messages when tree building is complete should be
        placed here. """
        self.og_dir_dict_2 = result
        self.anon_dir_dict_2 = _pickle.loads(_pickle.dumps(self.og_dir_dict_2))
        self.refresh_treeview(
            self.og_model_2, self.og_tree_2, self.og_dir_dict_2)
        self.refresh_treeview(
            self.anon_model_2, self.anon_tree_2, self.anon_dir_dict_2,
            checkable=False, anon_tree=True)
        self.preview_anon_tree_threaded_2()
        self.spinner.stop()

    def build_tree_structure_threaded_3(self, root_path):
        worker = Worker(record_stat, root_path)
        worker.signals.started.connect(self.build_tree_started_3)
        worker.signals.result.connect(self.build_tree_finished_3)
        self.threadpool.start(worker)

    def build_tree_started_3(self):
        """ Status messages when building a tree should be placed here. """
        self.expanded_items_list_3 = []
        self.unchecked_items_set_3 = set()
        self.renamed_items_dict_3 = dict()
        self.spinner.start()

    def build_tree_finished_3(self, result):
        """ Status messages when tree building is complete should be
        placed here. """
        self.og_dir_dict_3 = result
        self.anon_dir_dict_3 = _pickle.loads(_pickle.dumps(self.og_dir_dict_3))
        self.refresh_treeview(
            self.og_model_3, self.og_tree_3, self.og_dir_dict_3)
        self.refresh_treeview(
            self.anon_model_3, self.anon_tree_3, self.anon_dir_dict_3,
            checkable=False, anon_tree=True)
        self.preview_anon_tree_threaded_3()
        self.spinner.stop()

    def build_tree_structure_threaded_4(self, root_path):
        worker = Worker(record_stat, root_path)
        worker.signals.started.connect(self.build_tree_started_4)
        worker.signals.result.connect(self.build_tree_finished_4)
        self.threadpool.start(worker)

    def build_tree_started_4(self):
        """ Status messages when building a tree should be placed here. """
        self.expanded_items_list_4 = []
        self.unchecked_items_set_4 = set()
        self.renamed_items_dict_4 = dict()
        self.spinner.start()

    def build_tree_finished_4(self, result):
        """ Status messages when tree building is complete should be
        placed here. """
        self.og_dir_dict_4 = result
        self.anon_dir_dict_4 = _pickle.loads(_pickle.dumps(self.og_dir_dict_4))
        self.refresh_treeview(
            self.og_model_4, self.og_tree_4, self.og_dir_dict_4)
        self.refresh_treeview(
            self.anon_model_4, self.anon_tree_4, self.anon_dir_dict_4,
            checkable=False, anon_tree=True)
        self.preview_anon_tree_threaded_4()
        self.spinner.stop()

    def preview_anon_tree(self):
        """ Preview anonymized tree. Quite an intensive task. Check the time
        taken to complete each function to see if there are opportunities for
        optimization. """
        self.anon_dir_dict = _pickle.loads(_pickle.dumps(self.og_dir_dict))
        self.anon_dir_dict = anonymize_stat(self.anon_dir_dict,
                                            self.unchecked_items_set,
                                            self.renamed_items_dict)
        self.refresh_treeview(
            self.anon_model, self.anon_tree, self.anon_dir_dict,
            checkable=False, anon_tree=True)
        self.expanded_items_list = []
        self.list_expanded(
            self.og_tree, self.og_root_item, 0, self.expanded_items_list)
        self.expand_items(
            self.anon_tree, self.anon_root_item, 0, self.expanded_items_list)

    def preview_anon_tree_threaded(self):
        if self.root_path:
            if len(self.unchecked_items_set) == len(self.og_dir_dict.keys()):
                self.anon_model.removeRow(0)
                for row in range(self.n_props):
                    label_key = self.user_folder_props_table.item(
                        row, 0).data(Qt.UserRole)
                    if label_key[0] == '_':
                        pass
                    else:
                        (value_item, min_item,
                         max_item, diff_item) = self.empty_folder_props()
                        self.user_folder_props_table.setItem(
                            row, 1, value_item)
                        self.user_folder_props_table.setItem(row, 2, min_item)
                        self.user_folder_props_table.setItem(row, 3, max_item)
                        self.user_folder_props_table.setItem(row, 4, diff_item)
                self.alert_box.about(
                    self, 'Error', self.no_root_error_msg)
            else:
                worker = Worker(self.preview_anon_tree)
                worker.signals.started.connect(self.preview_anon_tree_started)
                worker.signals.result.connect(self.preview_anon_tree_finished)
                self.threadpool.start(worker)
        else:
            pass

    def preview_anon_tree_started(self):
        """ Status messages when previewing an anonymized tree should be
        placed here. """
        self.spinner.start()

    def preview_anon_tree_finished(self):
        """ Status messages when an anonymized tree has been previewed should
        be placed here. """
        self.display_user_folder_props()
        self.spinner.stop()

    def preview_anon_tree_2(self):
        self.anon_dir_dict_2 = _pickle.loads(_pickle.dumps(self.og_dir_dict_2))
        self.anon_dir_dict_2 = anonymize_stat(self.anon_dir_dict_2,
                                              self.unchecked_items_set_2,
                                              self.renamed_items_dict_2)
        self.refresh_treeview(
            self.anon_model_2, self.anon_tree_2, self.anon_dir_dict_2,
            checkable=False, anon_tree=True)
        self.expanded_items_list_2 = []
        self.list_expanded(
            self.og_tree_2, self.og_root_item_2, 0, self.expanded_items_list_2)
        self.expand_items(
            self.anon_tree_2, self.anon_root_item_2, 0,
            self.expanded_items_list_2)

    def preview_anon_tree_threaded_2(self):
        if self.root_path_2:
            if len(self.unchecked_items_set_2) == len(
                    self.og_dir_dict_2.keys()):
                self.anon_model_2.removeRow(0)
                for row in range(self.n_props):
                    label_key = self.user_folder_props_table.item(
                        row, 0).data(Qt.UserRole)
                    if label_key[0] == '_':
                        pass
                    else:
                        (value_item, min_item,
                         max_item, diff_item) = self.empty_folder_props()
                        self.user_folder_props_table.setItem(
                            row, 1, value_item)
                        self.user_folder_props_table.setItem(row, 2, min_item)
                        self.user_folder_props_table.setItem(row, 3, max_item)
                        self.user_folder_props_table.setItem(row, 4, diff_item)
                self.alert_box.about(
                    self, 'Error', self.no_root_error_msg)
            else:
                worker = Worker(self.preview_anon_tree_2)
                worker.signals.started.connect(
                    self.preview_anon_tree_started_2)
                worker.signals.result.connect(
                    self.preview_anon_tree_finished_2)
                self.threadpool.start(worker)
        else:
            pass

    def preview_anon_tree_started_2(self):
        """ Status messages when previewing an anonymized tree should be
        placed here. """
        self.spinner.start()

    def preview_anon_tree_finished_2(self):
        """ Status messages when an anonymized tree has been previewed should
        be placed here. """
        self.display_user_folder_props()
        self.spinner.stop()

    def preview_anon_tree_3(self):
        self.anon_dir_dict_3 = _pickle.loads(_pickle.dumps(self.og_dir_dict_3))
        self.anon_dir_dict_3 = anonymize_stat(self.anon_dir_dict_3,
                                              self.unchecked_items_set_3,
                                              self.renamed_items_dict_3)
        self.refresh_treeview(self.anon_model_3,
                              self.anon_tree_3,
                              self.anon_dir_dict_3,
                              checkable=False, anon_tree=True)
        self.expanded_items_list_3 = []
        self.list_expanded(
            self.og_tree_3, self.og_root_item_3, 0, self.expanded_items_list_3)
        self.expand_items(
            self.anon_tree_3, self.anon_root_item_3, 0,
            self.expanded_items_list_3)

    def preview_anon_tree_threaded_3(self):
        if self.root_path_3:
            if len(self.unchecked_items_set_3) == len(
                    self.og_dir_dict_3.keys()):
                self.anon_model_3.removeRow(0)
                for row in range(self.n_props):
                    label_key = self.user_folder_props_table.item(
                        row, 0).data(Qt.UserRole)
                    if label_key[0] == '_':
                        pass
                    else:
                        (value_item, min_item,
                         max_item, diff_item) = self.empty_folder_props()
                        self.user_folder_props_table.setItem(
                            row, 1, value_item)
                        self.user_folder_props_table.setItem(row, 2, min_item)
                        self.user_folder_props_table.setItem(row, 3, max_item)
                        self.user_folder_props_table.setItem(row, 4, diff_item)
                self.alert_box.about(
                    self, 'Error', self.no_root_error_msg)
            else:
                worker = Worker(self.preview_anon_tree_3)
                worker.signals.started.connect(
                    self.preview_anon_tree_started_3)
                worker.signals.result.connect(
                    self.preview_anon_tree_finished_3)
                self.threadpool.start(worker)
        else:
            pass

    def preview_anon_tree_started_3(self):
        """ Status messages when previewing an anonymized tree should be
        placed here. """
        self.spinner.start()

    def preview_anon_tree_finished_3(self):
        """ Status messages when an anonymized tree has been previewed should
        be placed here. """
        self.display_user_folder_props()
        self.spinner.stop()

    def preview_anon_tree_4(self):
        self.anon_dir_dict_4 = _pickle.loads(_pickle.dumps(self.og_dir_dict_4))
        self.anon_dir_dict_4 = anonymize_stat(self.anon_dir_dict_4,
                                              self.unchecked_items_set_4,
                                              self.renamed_items_dict_4)
        self.refresh_treeview(self.anon_model_4,
                              self.anon_tree_4,
                              self.anon_dir_dict_4,
                              checkable=False, anon_tree=True)
        self.expanded_items_list_4 = []
        self.list_expanded(
            self.og_tree_4, self.og_root_item_4, 0, self.expanded_items_list_4)
        self.expand_items(
            self.anon_tree_4, self.anon_root_item_4, 0,
            self.expanded_items_list_4)

    def preview_anon_tree_threaded_4(self):
        if self.root_path_4:
            if len(self.unchecked_items_set_4) == len(
                    self.og_dir_dict_4.keys()):
                self.anon_model_4.removeRow(0)
                for row in range(self.n_props):
                    label_key = self.user_folder_props_table.item(
                        row, 0).data(Qt.UserRole)
                    if label_key[0] == '_':
                        pass
                    else:
                        (value_item, min_item,
                         max_item, diff_item) = self.empty_folder_props()
                        self.user_folder_props_table.setItem(
                            row, 1, value_item)
                        self.user_folder_props_table.setItem(row, 2, min_item)
                        self.user_folder_props_table.setItem(row, 3, max_item)
                        self.user_folder_props_table.setItem(row, 4, diff_item)
                self.alert_box.about(
                    self, 'Error', self.no_root_error_msg)
            else:
                worker = Worker(self.preview_anon_tree_4)
                worker.signals.started.connect(
                    self.preview_anon_tree_started_4)
                worker.signals.result.connect(
                    self.preview_anon_tree_finished_4)
                self.threadpool.start(worker)
        else:
            pass

    def preview_anon_tree_started_4(self):
        """ Status messages when previewing an anonymized tree should be
        placed here. """
        self.spinner.start()

    def preview_anon_tree_finished_4(self):
        """ Status messages when an anonymized tree has been previewed should
        be placed here. """
        self.display_user_folder_props()
        self.spinner.stop()

    def display_user_folder_props(self):
        try:
            anon_dir_dict_list = []
            if self.root_path and len(self.unchecked_items_set) != len(
                    self.og_dir_dict.keys()):
                anon_dir_dict_list.append(self.anon_dir_dict)
            if self.root_path_2 and len(self.unchecked_items_set_2) != len(
                    self.og_dir_dict_2.keys()):
                anon_dir_dict_list.append(self.anon_dir_dict_2)
            if self.root_path_3 and len(self.unchecked_items_set_3) != len(
                    self.og_dir_dict_3.keys()):
                anon_dir_dict_list.append(self.anon_dir_dict_3)
            if self.root_path_4 and len(self.unchecked_items_set_4) != len(
                    self.og_dir_dict_4.keys()):
                anon_dir_dict_list.append(self.anon_dir_dict_4)
            # Should we allow statistics errors (e.g., non-unique modes)?
            self.user_folder_props = drive_measurement(
                anon_dir_dict_list, allow_stat_error=True)
            (self.user_folder_typical, self.typical_folder_props,
             self.user_folder_diffs) = \
                check_collection_properties(self.user_folder_props)
            for row in range(self.n_props):
                label_key = self.user_folder_props_table.item(
                    row, 0).data(Qt.UserRole)
                if label_key[0] == '_':  # identifies section headers
                    pass
                else:
                    value_item = QTableWidgetItem(str_none_num(
                        self.user_folder_props[label_key]))
                    value_item.setTextAlignment(Qt.AlignRight)
                    value_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    min_item = QTableWidgetItem(str_none_num(
                        self.typical_folder_props[label_key][0]))
                    min_item.setTextAlignment(Qt.AlignRight)
                    min_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    max_item = QTableWidgetItem(str_none_num(
                        self.typical_folder_props[label_key][1]))
                    max_item.setTextAlignment(Qt.AlignRight)
                    max_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    self.user_folder_props_table.setItem(row, 1, value_item)
                    self.user_folder_props_table.setItem(row, 2, min_item)
                    self.user_folder_props_table.setItem(row, 3, max_item)
                    if self.user_folder_diffs[label_key]:
                        diff_item = QTableWidgetItem(str_none_num(
                            self.user_folder_diffs[label_key]))
                        diff_item.setTextAlignment(Qt.AlignRight)
                        diff_item.setFlags(Qt.ItemIsEnabled |
                                           Qt.ItemIsSelectable)
                        self.user_folder_props_table.setItem(row, 4, diff_item)
            self.user_folder_props_table.reset()
            self.header_autoresizable(
                self.user_folder_props_table.horizontalHeader())
        except Exception as e:
            self.alert_box.about(
                self, 'Error',
                'Incapable of computing statistics with current root and/or '
                'folder selections: ' + str(e) + '<br><br>' +
                'Please modify root and/or folder selections.' +
                '<br><br><b>You may submit the data regardless.</b>')
            self.user_folder_typical = False
            for row in range(self.n_props):
                label_key = self.user_folder_props_table.item(
                    row, 0).data(Qt.UserRole)
                if label_key[0] == '_':  # identifies section headers
                    pass
                else:
                    (value_item, min_item,
                     max_item, diff_item) = self.empty_folder_props()
                    self.user_folder_props_table.setItem(row, 1, value_item)
                    self.user_folder_props_table.setItem(row, 2, min_item)
                    self.user_folder_props_table.setItem(row, 3, max_item)
                    self.user_folder_props_table.setItem(row, 4, diff_item)

    def show_file_dialog(self):
        dirpath = QFileDialog.getExistingDirectory(
            self, 'Select Folder', str(self.root_path))
        if dirpath:
            root_overlap = is_root_overlap(
                'Root Folder 1', dirpath,
                [self.root_path_2, self.root_path_3, self.root_path_4])
            if root_overlap:
                self.alert_box.about(self, 'Error', root_overlap)
            else:
                self.root_path = Path(dirpath)
                self.folder_edit.setText(path_str(self.root_path))
                self.build_tree_structure_threaded(self.root_path)
        else:
            self.clear_root()

    def show_file_dialog_2(self):
        dirpath = QFileDialog.getExistingDirectory(
            self, 'Select Folder', str(self.root_path_2))
        if dirpath:
            root_overlap = is_root_overlap(
                'Root Folder 2', dirpath,
                [self.root_path, self.root_path_3, self.root_path_4])
            if root_overlap:
                self.alert_box.about(self, 'Error', root_overlap)
            else:
                self.root_path_2 = Path(dirpath)
                self.folder_edit_2.setText(path_str(self.root_path_2))
                self.build_tree_structure_threaded_2(self.root_path_2)
        else:
            self.clear_root_2()

    def show_file_dialog_3(self):
        dirpath = QFileDialog.getExistingDirectory(
            self, 'Select Folder', str(self.root_path_3))
        if dirpath:
            root_overlap = is_root_overlap(
                'Root Folder 3', dirpath,
                [self.root_path, self.root_path_2, self.root_path_4])
            if root_overlap:
                self.alert_box.about(self, 'Error', root_overlap)
            else:
                self.root_path_3 = Path(dirpath)
                self.folder_edit_3.setText(path_str(self.root_path_3))
                self.build_tree_structure_threaded_3(self.root_path_3)
        else:
            self.clear_root_3()

    def show_file_dialog_4(self):
        dirpath = QFileDialog.getExistingDirectory(
            self, 'Select Folder', str(self.root_path_4))
        if dirpath:
            root_overlap = is_root_overlap(
                'Root Folder 4', dirpath,
                [self.root_path, self.root_path_2, self.root_path_3])
            if root_overlap:
                self.alert_box.about(self, 'Error', root_overlap)
            else:
                self.root_path_4 = Path(dirpath)
                self.folder_edit_4.setText(path_str(self.root_path_4))
                self.build_tree_structure_threaded_4(self.root_path_4)
        else:
            self.clear_root_4()

    def clear_root(self):
        self.root_path = None
        self.og_dir_dict, self.anon_dir_dict = dict(), dict()
        self.unchecked_items_set = set()
        self.renamed_items_dict = dict()
        self.folder_edit.setText(path_str(self.root_path))
        self.og_model.removeRow(0)
        self.anon_model.removeRow(0)

    def clear_root_2(self):
        self.root_path_2 = None
        self.og_dir_dict_2, self.anon_dir_dict_2 = dict(), dict()
        self.unchecked_items_set_2 = set()
        self.renamed_items_dict_2 = dict()
        self.folder_edit_2.setText(path_str(self.root_path_2))
        self.og_model_2.removeRow(0)
        self.anon_model_2.removeRow(0)

    def clear_root_3(self):
        self.root_path_3 = None
        self.og_dir_dict_3, self.anon_dir_dict_3 = dict(), dict()
        self.unchecked_items_set_3 = set()
        self.renamed_items_dict_3 = dict()
        self.folder_edit_3.setText(path_str(self.root_path_3))
        self.og_model_3.removeRow(0)
        self.anon_model_3.removeRow(0)

    def clear_root_4(self):
        self.root_path_4 = None
        self.og_dir_dict_4, self.anon_dir_dict_4 = dict(), dict()
        self.unchecked_items_set_4 = set()
        self.renamed_items_dict_4 = dict()
        self.folder_edit_4.setText(path_str(self.root_path_4))
        self.og_model_4.removeRow(0)
        self.anon_model_4.removeRow(0)

    def upload_collected_data(self):
        data_list = []
        if self.root_path and len(self.unchecked_items_set) != len(
                self.og_dir_dict.keys()):
            data_1 = bytes(json.dumps(self.anon_dir_dict), 'utf8')
            data_1 = compress_data(data_1)
            data_list.append(data_1)
            with open('uploaded_file_1.json', 'w') as f1:
                json.dump(self.anon_dir_dict, f1, indent=4)
        if self.root_path_2 and len(self.unchecked_items_set_2) != len(
                self.og_dir_dict_2.keys()):
            data_2 = bytes(json.dumps(self.anon_dir_dict_2), 'utf8')
            data_2 = compress_data(data_2)
            data_list.append(data_2)
            with open('uploaded_file_2.json', 'w') as f2:
                json.dump(self.anon_dir_dict_2, f2, indent=4)
        if self.root_path_3 and len(self.unchecked_items_set_3) != len(
                self.og_dir_dict_3.keys()):
            data_3 = bytes(json.dumps(self.anon_dir_dict_3), 'utf8')
            data_3 = compress_data(data_3)
            data_list.append(data_3)
            with open('uploaded_file_3.json', 'w') as f3:
                json.dump(self.anon_dir_dict_3, f3, indent=4)
        if self.root_path_4 and len(self.unchecked_items_set_4) != len(
                self.og_dir_dict_4.keys()):
            data_4 = bytes(json.dumps(self.anon_dir_dict_4), 'utf8')
            data_4 = compress_data(data_4)
            data_list.append(data_4)
            with open('uploaded_file_4.json', 'w') as f4:
                json.dump(self.anon_dir_dict_4, f4, indent=4)
        encrypted_json_list, encrypted_jsonkey = encrypt_data(data_list)
        unique_id = generate_filename()
        for ix, encrypted_json in enumerate(encrypted_json_list):
            dir_dict_fname = unique_id + '_dir_dict_' + str(ix+1) + '.enc'
            sym_key_fname = unique_id + '_sym_key.enc'
            dropbox_upload(encrypted_json,
                           get_filepath(self.dbx_json_dirpath, dir_dict_fname))
        dropbox_upload(encrypted_jsonkey,
                       get_filepath(self.dbx_json_dirpath, sym_key_fname))

    def upload_collected_data_threaded(self):
        worker = Worker(self.upload_collected_data)
        worker.signals.started.connect(self.upload_collected_data_started)
        worker.signals.result.connect(self.upload_collected_data_finished)
        self.threadpool.start(worker)

    def upload_collected_data_started(self):
        self.spinner.start()

    def upload_collected_data_finished(self):
        self.spinner.stop()
        self.alert_box.about(
            self, 'Upload complete',
            'Folder data has been uploaded to the researchers.\n\nCopies of '
            'the uploaded data has been saved in the Drive Analysis Tool '
            'folder for user inspection. JSON files can be opened with text '
            'editors such as Notepad.')

    @staticmethod
    def header_autoresizable(header):
        """ Resize all sections to content and user interactive,
        see https://centaurialpha.github.io/resize-qheaderview-to-contents-and-interactive
        """

        for column in range(header.count()):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
            width = header.sectionSize(column)
            header.setSectionResizeMode(column, QHeaderView.Interactive)
            header.resizeSection(column, width)

    @staticmethod
    def empty_folder_props():
        """ Clear all the values in the user folder properties table """
        value_item = QTableWidgetItem('?')
        value_item.setTextAlignment(Qt.AlignRight)
        value_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        min_item = QTableWidgetItem('?')
        min_item.setTextAlignment(Qt.AlignRight)
        min_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        max_item = QTableWidgetItem('?')
        max_item.setTextAlignment(Qt.AlignRight)
        max_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        diff_item = QTableWidgetItem('')
        diff_item.setTextAlignment(Qt.AlignRight)
        diff_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        return value_item, min_item, max_item, diff_item


if __name__ == '__main__':
    app = QApplication(sys.argv)
    daw = DriveAnalysisWidget()
    sys.exit(app.exec_())
