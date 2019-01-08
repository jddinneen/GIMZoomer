import time
import pickle
import _pickle
import traceback
import json
import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QPushButton, QApplication, QFileDialog, QSlider, QGridLayout, QLabel, \
    QTreeView, QAbstractItemView, QHeaderView, QCheckBox, QTreeWidget, QTreeWidgetItem, QTextBrowser, \
    QTableWidget, QTableWidgetItem, QTabWidget, QMessageBox, QErrorMessage
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QObject, QRunnable, QThreadPool, QVariant, QItemSelectionModel
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from copy import deepcopy
from drive_analyzer import record_stat, compute_stat, anonymize_stat, find_all_children, \
    drive_measurement, check_collection_properties
from submit_data import compress_data, encrypt_data, dropbox_upload, generate_filename, get_filepath
from functools import partial


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
        self.root_path = ''
        # self.root_path = os.path.expanduser('~')
        # self.root_path = os.path.expanduser('~\\Downloads')
        # self.root_path = os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'desjardins'))
        self.root_path_2 = ''
        # self.root_path_2 = os.path.expanduser(os.path.join('~', 'Dropbox', 'academic'))
        self.root_path_3 = ''
        # self.root_path_3 = os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'File Zoomer'))
        self.root_path_4 = ''
        # self.root_path_4 = os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', '2017 Fall'))
        self.dbx_json_dirpath = '/'
        self.threadpool = QThreadPool()
        self.expanded_items_list = []
        self.expanded_items_list_2 = []
        self.expanded_items_list_3 = []
        self.expanded_items_list_4 = []
        self.unchecked_items_list = []  # ??? unused except in testing ???
        self.unchecked_items_set = set()
        self.unchecked_items_set_2 = set()
        self.unchecked_items_set_3 = set()
        self.unchecked_items_set_4 = set()
        self.renamed_items_dict = dict()
        self.renamed_items_dict_2 = dict()
        self.renamed_items_dict_3 = dict()
        self.renamed_items_dict_4 = dict()

        # with open(os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'File Zoomer',
        #                                           'code', 'drive_analysis_tool', 'dir_dict.pkl')), 'rb') as ddf:
        #     self.og_dir_dict = pickle.load(ddf)
        # self.anon_dir_dict = deepcopy(self.og_dir_dict)

        self.og_dir_dict, self.anon_dir_dict = dict(), dict()
        self.og_dir_dict_2, self.anon_dir_dict_2 = dict(), dict()
        self.og_dir_dict_3, self.anon_dir_dict_3 = dict(), dict()
        self.og_dir_dict_4, self.anon_dir_dict_4 = dict(), dict()
        self.user_folder_props = dict()
        self.user_folder_typical = True

        # test_btn = QPushButton()
        # test_btn.setText('Run tests')
        # test_btn.resize(test_btn.sizeHint())
        # test_btn.clicked.connect(self.test_script)

        self.folder_edit = QLabel()
        self.folder_edit.setText(self.root_path)
        self.folder_edit_2 = QLabel()
        self.folder_edit_2.setText(self.root_path_2)
        self.folder_edit_3 = QLabel()
        self.folder_edit_3.setText(self.root_path_3)
        self.folder_edit_4 = QLabel()
        self.folder_edit_4.setText(self.root_path_4)

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

        select_btn = QPushButton('Select Root', self)
        select_btn.setToolTip('Select <b>personal folder</b> for data collection.')
        select_btn.clicked.connect(self.show_file_dialog)
        select_btn.resize(select_btn.sizeHint())
        select_btn_2 = QPushButton('Select Root', self)
        select_btn_2.setToolTip('Select <b>second personal folder (if any)</b> for data collection.')
        select_btn_2.clicked.connect(self.show_file_dialog_2)
        select_btn_2.resize(select_btn_2.sizeHint())
        select_btn_3 = QPushButton('Select Root', self)
        select_btn_3.setToolTip('Select <b>third personal folder (if any)</b> for data collection.')
        select_btn_3.clicked.connect(self.show_file_dialog_3)
        select_btn_3.resize(select_btn_3.sizeHint())
        select_btn_4 = QPushButton('Select Root', self)
        select_btn_4.setToolTip('Select <b>fourth personal folder (if any)</b> for data collection.')
        select_btn_4.clicked.connect(self.show_file_dialog_4)
        select_btn_4.resize(select_btn_4.sizeHint())

        clear_btn = QPushButton('Clear Selection', self)
        clear_btn.setToolTip('Remove Root Folder 1 from the data to be submitted.')
        clear_btn.clicked.connect(self.clear_root)
        clear_btn.resize(clear_btn.sizeHint())
        clear_btn_2 = QPushButton('Clear Selection', self)
        clear_btn_2.setToolTip('Remove Root Folder 2 from the data to be submitted.')
        clear_btn_2.clicked.connect(self.clear_root_2)
        clear_btn_2.resize(clear_btn_2.sizeHint())
        clear_btn_3 = QPushButton('Clear Selection', self)
        clear_btn_3.setToolTip('Remove Root Folder 3 from the data to be submitted.')
        clear_btn_3.clicked.connect(self.clear_root_3)
        clear_btn_3.resize(clear_btn_3.sizeHint())
        clear_btn_4 = QPushButton('Clear Selection', self)
        clear_btn_4.setToolTip('Remove Root Folder 4 from the data to be submitted.')
        clear_btn_4.clicked.connect(self.clear_root_4)
        clear_btn_4.resize(clear_btn_4.sizeHint())

        self.dir_error = QMessageBox()

        preview_btn = QPushButton('Preview', self)
        preview_btn.setToolTip('Preview folder data that will be used for research')
        preview_btn.clicked.connect(self.preview_anon_tree_threaded)
        preview_btn.resize(preview_btn.sizeHint())
        preview_btn_2 = QPushButton('Preview', self)
        preview_btn_2.setToolTip('Preview folder data that will be used for research')
        preview_btn_2.clicked.connect(self.preview_anon_tree_threaded_2)
        preview_btn_2.resize(preview_btn_2.sizeHint())
        preview_btn_3 = QPushButton('Preview', self)
        preview_btn_3.setToolTip('Preview folder data that will be used for research')
        preview_btn_3.clicked.connect(self.preview_anon_tree_threaded_3)
        preview_btn_3.resize(preview_btn_3.sizeHint())
        preview_btn_4 = QPushButton('Preview', self)
        preview_btn_4.setToolTip('Preview folder data that will be used for research')
        preview_btn_4.clicked.connect(self.preview_anon_tree_threaded_4)
        preview_btn_4.resize(preview_btn_4.sizeHint())

        self.submit_btn = QPushButton('Submit', self)
        self.submit_btn.setToolTip('Submit encrypted folder data to the cloud')
        self.submit_btn.clicked.connect(self.upload_collected_data)
        self.submit_btn.resize(self.submit_btn.sizeHint())
        self.submit_btn.setEnabled(False)

        self.status_label = QLabel()
        self.status_label.setText('')
        self.status_label.setStyleSheet("color: red;"
                                        "font: bold;")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.user_folder_props_label = QLabel()
        self.user_folder_props_label.setAlignment(Qt.AlignCenter)
        self.user_folder_props_label.setText('Characteristics of all roots\' structures')

        self.user_folder_props_table = QTableWidget()
        self.user_folder_props_table.setRowCount(22)
        self.user_folder_props_table.setColumnCount(2)
        labels = ['Total files', 'Total folders', 'Greatest breadth of folder tree', 'Average breadth of folder tree',
                  '# folders at root', '# leaf folders (folders without subfolders)',
                  '% leaf folders (folders without subfolders)',
                  'Average depth of leaf folders (folders without subfolders)',
                  '# switch folders (folders with subfolders and no files)',
                  '% switch folders (folders with subfolders and no files)',
                  'Average depth of switch folders (folders with subfolders and no files)',
                  'Greatest depth where folders are found',
                  'Folder waist (depth where folders are most commonly found)',
                  'Average depth where folders are found',
                  'Branching factor (average subfolders per folder, excepting leaf folders)',
                  '# files at root', 'Average # files in folders', '# empty folders', '% empty folders',
                  'Average depth where files are found', 'Depth where files are most commonly found',
                  '# files at depth where files are most commonly found']
        label_keys = ['n_files', 'n_folders', 'breadth_max', 'breadth_mean', 'root_n_folders', 'n_leaf_folders',
                      'pct_leaf_folders', 'depth_leaf_folders_mean', 'n_switch_folders', 'pct_switch_folders',
                      'depth_switch_folders_mean', 'depth_max', 'depth_folders_mode', 'depth_folders_mean',
                      'branching_factor', 'root_n_files', 'n_files_mean', 'n_empty_folders', 'pct_empty_folders',
                      'depth_files_mean', 'depth_files_mode', 'file_breadth_mode_n_files']
        for row, label, label_key in zip(range(22), labels, label_keys):
            label_item = QTableWidgetItem(label)
            label_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            value_item = QTableWidgetItem('?')
            value_item.setData(Qt.UserRole, label_key)
            value_item.setTextAlignment(Qt.AlignRight)
            value_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.user_folder_props_table.setItem(row, 0, label_item)
            self.user_folder_props_table.setItem(row, 1, value_item)
        self.user_folder_props_table.setHorizontalHeaderLabels(['Property', 'Value'])
        self.user_folder_props_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.user_folder_props_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        # print(self.user_folder_props_table.item(0, 1).data(Qt.UserRole))

        # self.user_folder_typical_label = QLabel()
        # self.user_folder_typical_label.setText('')
        # self.user_folder_typical_label.setStyleSheet("font: bold;")
        # self.user_folder_typical_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        og_tree_label = QLabel()
        og_tree_label.setAlignment(Qt.AlignCenter)
        og_tree_label.setText('Original folders data')

        anon_tree_label = QLabel()
        anon_tree_label.setAlignment(Qt.AlignCenter)
        anon_tree_label.setText('Folders data to be used for research')

        og_tree_label_2 = QLabel()
        og_tree_label_2.setAlignment(Qt.AlignCenter)
        og_tree_label_2.setText('Original folders data')

        anon_tree_label_2 = QLabel()
        anon_tree_label_2.setAlignment(Qt.AlignCenter)
        anon_tree_label_2.setText('Folders data to be used for research')

        og_tree_label_3 = QLabel()
        og_tree_label_3.setAlignment(Qt.AlignCenter)
        og_tree_label_3.setText('Original folders data')

        anon_tree_label_3 = QLabel()
        anon_tree_label_3.setAlignment(Qt.AlignCenter)
        anon_tree_label_3.setText('Folders data to be used for research')

        og_tree_label_4 = QLabel()
        og_tree_label_4.setAlignment(Qt.AlignCenter)
        og_tree_label_4.setText('Original folders data')

        anon_tree_label_4 = QLabel()
        anon_tree_label_4.setAlignment(Qt.AlignCenter)
        anon_tree_label_4.setText('Folders data to be used for research')

        # self.og_tree = QTreeView()
        # self.og_model = QStandardItemModel()
        self.og_tree.setModel(self.og_model)
        self.og_model.setHorizontalHeaderLabels(['Folder Name', 'Renamed Folder', 'Number of Files'])
        self.og_root_item = self.og_model.invisibleRootItem()
        self.refresh_treeview(self.og_model, self.og_tree, self.og_dir_dict)
        self.og_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.og_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.og_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.og_model.itemChanged.connect(self.on_item_change)

        # self.anon_tree = QTreeView()
        # self.anon_model = QStandardItemModel()
        self.anon_tree.setModel(self.anon_model)
        self.anon_model.setHorizontalHeaderLabels(['Folder Name', 'Number of Files'])
        self.anon_root_item = self.anon_model.invisibleRootItem()
        self.refresh_treeview(self.anon_model, self.anon_tree, self.anon_dir_dict, checkable=False, anon_tree=True)
        self.anon_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.anon_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)

        # self.og_tree_2 = QTreeView()
        # self.og_model_2 = QStandardItemModel()
        self.og_tree_2.setModel(self.og_model_2)
        self.og_model_2.setHorizontalHeaderLabels(['Folder Name', 'Renamed Folder', 'Number of Files'])
        self.og_root_item_2 = self.og_model_2.invisibleRootItem()
        self.refresh_treeview(self.og_model_2, self.og_tree_2, self.og_dir_dict_2)
        self.og_tree_2.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.og_tree_2.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.og_tree_2.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.og_model_2.itemChanged.connect(self.on_item_change_2)

        # self.anon_tree_2 = QTreeView()
        # self.anon_model_2 = QStandardItemModel()
        self.anon_tree_2.setModel(self.anon_model_2)
        self.anon_model_2.setHorizontalHeaderLabels(['Folder Name', 'Number of Files'])
        self.anon_root_item_2 = self.anon_model_2.invisibleRootItem()
        self.refresh_treeview(self.anon_model_2, self.anon_tree_2, self.anon_dir_dict_2, checkable=False, anon_tree=True)
        self.anon_tree_2.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.anon_tree_2.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)

        # self.og_tree_3 = QTreeView()
        # self.og_model_3 = QStandardItemModel()
        self.og_tree_3.setModel(self.og_model_3)
        self.og_model_3.setHorizontalHeaderLabels(['Folder Name', 'Renamed Folder', 'Number of Files'])
        self.og_root_item_3 = self.og_model_3.invisibleRootItem()
        self.refresh_treeview(self.og_model_3, self.og_tree_3, self.og_dir_dict_3)
        self.og_tree_3.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.og_tree_3.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.og_tree_3.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.og_model_3.itemChanged.connect(self.on_item_change_3)

        # self.anon_tree_3 = QTreeView()
        # self.anon_model_3 = QStandardItemModel()
        self.anon_tree_3.setModel(self.anon_model_3)
        self.anon_model_3.setHorizontalHeaderLabels(['Folder Name', 'Number of Files'])
        self.anon_root_item_3 = self.anon_model_3.invisibleRootItem()
        self.refresh_treeview(self.anon_model_3, self.anon_tree_3, self.anon_dir_dict_3, checkable=False, anon_tree=True)
        self.anon_tree_3.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.anon_tree_3.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)

        # self.og_tree_4 = QTreeView()
        # self.og_model_4 = QStandardItemModel()
        self.og_tree_4.setModel(self.og_model_4)
        self.og_model_4.setHorizontalHeaderLabels(['Folder Name', 'Renamed Folder', 'Number of Files'])
        self.og_root_item_4 = self.og_model_4.invisibleRootItem()
        self.refresh_treeview(self.og_model_4, self.og_tree_4, self.og_dir_dict_4)
        self.og_tree_4.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.og_tree_4.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.og_tree_4.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.og_model_4.itemChanged.connect(self.on_item_change_4)

        # self.anon_tree_4 = QTreeView()
        # self.anon_model_4 = QStandardItemModel()
        self.anon_tree_4.setModel(self.anon_model_4)
        self.anon_model_4.setHorizontalHeaderLabels(['Folder Name', 'Number of Files'])
        self.anon_root_item_4 = self.anon_model_4.invisibleRootItem()
        self.refresh_treeview(self.anon_model_4, self.anon_tree_4, self.anon_dir_dict_4, checkable=False, anon_tree=True)
        self.anon_tree_4.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.anon_tree_4.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)

        if self.root_path != '':
            self.build_tree_structure_threaded(self.root_path)
        if self.root_path_2 != '':
            self.build_tree_structure_threaded_2(self.root_path_2)
        if self.root_path_3 != '':
            self.build_tree_structure_threaded_3(self.root_path_3)
        if self.root_path_4 != '':
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
        self.tab1.layout.addWidget(clear_btn, 0, 1, 1, 1)
        self.tab1.layout.addWidget(self.folder_edit, 0, 2, 1, 6)
        self.tab1.layout.addWidget(og_tree_label, 1, 0, 1, 5)
        self.tab1.layout.addWidget(anon_tree_label, 1, 5, 1, 3)
        self.tab1.layout.addWidget(self.og_tree, 2, 0, 1, 5)
        self.tab1.layout.addWidget(self.anon_tree, 2, 5, 1, 3)
        self.tab1.layout.addWidget(preview_btn, 3, 7, 1, 1)
        self.tab1.setLayout(self.tab1.layout)
        # Create second tab
        self.tab2.layout = QGridLayout()
        self.tab2.layout.addWidget(select_btn_2, 0, 0, 1, 1)
        self.tab2.layout.addWidget(clear_btn_2, 0, 1, 1, 1)
        self.tab2.layout.addWidget(self.folder_edit_2, 0, 2, 1, 6)
        self.tab2.layout.addWidget(og_tree_label_2, 1, 0, 1, 5)
        self.tab2.layout.addWidget(anon_tree_label_2, 1, 5, 1, 3)
        self.tab2.layout.addWidget(self.og_tree_2, 2, 0, 1, 5)
        self.tab2.layout.addWidget(self.anon_tree_2, 2, 5, 1, 3)
        self.tab2.layout.addWidget(preview_btn_2, 3, 7, 1, 1)
        self.tab2.setLayout(self.tab2.layout)
        # Create third tab
        self.tab3.layout = QGridLayout()
        self.tab3.layout.addWidget(select_btn_3, 0, 0, 1, 1)
        self.tab3.layout.addWidget(clear_btn_3, 0, 1, 1, 1)
        self.tab3.layout.addWidget(self.folder_edit_3, 0, 2, 1, 6)
        self.tab3.layout.addWidget(og_tree_label_3, 1, 0, 1, 5)
        self.tab3.layout.addWidget(anon_tree_label_3, 1, 5, 1, 3)
        self.tab3.layout.addWidget(self.og_tree_3, 2, 0, 1, 5)
        self.tab3.layout.addWidget(self.anon_tree_3, 2, 5, 1, 3)
        self.tab3.layout.addWidget(preview_btn_3, 3, 7, 1, 1)
        self.tab3.setLayout(self.tab3.layout)
        # Create fourth tab
        self.tab4.layout = QGridLayout()
        self.tab4.layout.addWidget(select_btn_4, 0, 0, 1, 1)
        self.tab4.layout.addWidget(clear_btn_4, 0, 1, 1, 1)
        self.tab4.layout.addWidget(self.folder_edit_4, 0, 2, 1, 6)
        self.tab4.layout.addWidget(og_tree_label_4, 1, 0, 1, 5)
        self.tab4.layout.addWidget(anon_tree_label_4, 1, 5, 1, 3)
        self.tab4.layout.addWidget(self.og_tree_4, 2, 0, 1, 5)
        self.tab4.layout.addWidget(self.anon_tree_4, 2, 5, 1, 3)
        self.tab4.layout.addWidget(preview_btn_4, 3, 7, 1, 1)
        self.tab4.setLayout(self.tab4.layout)

        grid = QGridLayout()
        # grid.addWidget(select_btn, 0, 0, 1, 1)
        # grid.addWidget(self.folder_edit, 0, 1, 1, 7)
        # grid.addWidget(self.status_label, 1, 0, 1, 8)
        # grid.addWidget(og_tree_label, 1, 0, 1, 5)
        # grid.addWidget(anon_tree_label, 1, 5, 1, 3)
        # grid.addWidget(self.og_tree, 2, 0, 1, 5)
        # grid.addWidget(self.anon_tree, 2, 5, 1, 3)
        grid.addWidget(self.user_folder_props_label, 3, 0, 1, 8)
        grid.addWidget(self.user_folder_props_table, 4, 0, 2, 8)
        # grid.addWidget(self.user_folder_typical_label, 7, 0, 1, 6)
        grid.addWidget(self.status_label, 7, 0, 1, 7)
        # grid.addWidget(preview_btn, 7, 6, 1, 1)
        grid.addWidget(self.submit_btn, 7, 7, 1, 1)
        grid.addWidget(self.tabs, 0, 0, 1, 8)

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
            self.status_label.setText('Click \'Preview\' to apply and see changes')
        if item.column() == 1:
            dirkey = item.data(Qt.UserRole)
            self.renamed_items_dict[dirkey] = item.text()
            self.status_label.setText('Click \'Preview\' to apply and see changes')

    def on_item_change_2(self, item):
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
                self.unchecked_items_set_2.add(dirkey)
                # if dirkey in self.renamed_items_dict:
                #     self.renamed_items_dict.pop(dirkey)
            elif item_checkstate in (Qt.Checked, Qt.PartiallyChecked):
                if dirkey in self.unchecked_items_set_2:
                    self.unchecked_items_set_2.remove(dirkey)
            self.status_label.setText('Click \'Preview\' to apply and see changes')
        if item.column() == 1:
            dirkey = item.data(Qt.UserRole)
            self.renamed_items_dict_2[dirkey] = item.text()
            self.status_label.setText('Click \'Preview\' to apply and see changes')

    def on_item_change_3(self, item):
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
                self.unchecked_items_set_3.add(dirkey)
                # if dirkey in self.renamed_items_dict:
                #     self.renamed_items_dict.pop(dirkey)
            elif item_checkstate in (Qt.Checked, Qt.PartiallyChecked):
                if dirkey in self.unchecked_items_set_3:
                    self.unchecked_items_set_3.remove(dirkey)
            self.status_label.setText('Click \'Preview\' to apply and see changes')
        if item.column() == 1:
            dirkey = item.data(Qt.UserRole)
            self.renamed_items_dict_3[dirkey] = item.text()
            self.status_label.setText('Click \'Preview\' to apply and see changes')

    def on_item_change_4(self, item):
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
                self.unchecked_items_set_4.add(dirkey)
                # if dirkey in self.renamed_items_dict:
                #     self.renamed_items_dict.pop(dirkey)
            elif item_checkstate in (Qt.Checked, Qt.PartiallyChecked):
                if dirkey in self.unchecked_items_set_4:
                    self.unchecked_items_set_4.remove(dirkey)
            self.status_label.setText('Click \'Preview\' to apply and see changes')
        if item.column() == 1:
            dirkey = item.data(Qt.UserRole)
            self.renamed_items_dict_4[dirkey] = item.text()
            self.status_label.setText('Click \'Preview\' to apply and see changes')

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
        self.anon_dir_dict = _pickle.loads(_pickle.dumps(self.og_dir_dict))
        self.refresh_treeview(self.og_model, self.og_tree, self.og_dir_dict)
        self.refresh_treeview(self.anon_model, self.anon_tree, self.anon_dir_dict, checkable=False, anon_tree=True)
        self.status_label.setText('Click \'Preview\' to see changes')

    def build_tree_structure_threaded_2(self, root_path):
        worker = Worker(record_stat, root_path)
        worker.signals.started.connect(self.build_tree_started_2)
        worker.signals.result.connect(self.build_tree_finished_2)
        self.threadpool.start(worker)

    def build_tree_started_2(self):
        self.status_label.setText('Building tree, please wait...')

    def build_tree_finished_2(self, result):
        self.og_dir_dict_2 = result
        self.anon_dir_dict_2 = _pickle.loads(_pickle.dumps(self.og_dir_dict_2))
        self.refresh_treeview(self.og_model_2, self.og_tree_2, self.og_dir_dict_2)
        self.refresh_treeview(self.anon_model_2, self.anon_tree_2, self.anon_dir_dict_2, checkable=False, anon_tree=True)
        self.status_label.setText('Click \'Preview\' to see changes')

    def build_tree_structure_threaded_3(self, root_path):
        worker = Worker(record_stat, root_path)
        worker.signals.started.connect(self.build_tree_started_3)
        worker.signals.result.connect(self.build_tree_finished_3)
        self.threadpool.start(worker)

    def build_tree_started_3(self):
        self.status_label.setText('Building tree, please wait...')

    def build_tree_finished_3(self, result):
        self.og_dir_dict_3 = result
        self.anon_dir_dict_3 = _pickle.loads(_pickle.dumps(self.og_dir_dict_3))
        self.refresh_treeview(self.og_model_3, self.og_tree_3, self.og_dir_dict_3)
        self.refresh_treeview(self.anon_model_3, self.anon_tree_3, self.anon_dir_dict_3, checkable=False, anon_tree=True)
        self.status_label.setText('Click \'Preview\' to see changes')

    def build_tree_structure_threaded_4(self, root_path):
        worker = Worker(record_stat, root_path)
        worker.signals.started.connect(self.build_tree_started_4)
        worker.signals.result.connect(self.build_tree_finished_4)
        self.threadpool.start(worker)

    def build_tree_started_4(self):
        self.status_label.setText('Building tree, please wait...')

    def build_tree_finished_4(self, result):
        self.og_dir_dict_4 = result
        self.anon_dir_dict_4 = _pickle.loads(_pickle.dumps(self.og_dir_dict_4))
        self.refresh_treeview(self.og_model_4, self.og_tree_4, self.og_dir_dict_4)
        self.refresh_treeview(self.anon_model_4, self.anon_tree_4, self.anon_dir_dict_4, checkable=False, anon_tree=True)
        self.status_label.setText('Click \'Preview\' to see changes')

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

    def preview_anon_tree_threaded(self):
        if self.root_path != '':
            if len(self.unchecked_items_set) == len(self.og_dir_dict.keys()):
                self.anon_model.removeRow(0)
                for row in range(22):
                    label_key = self.user_folder_props_table.item(row, 1).data(Qt.UserRole)
                    value_item = QTableWidgetItem('?')
                    value_item.setData(Qt.UserRole, label_key)
                    value_item.setTextAlignment(Qt.AlignRight)
                    value_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    self.user_folder_props_table.setItem(row, 1, value_item)
                self.dir_error.about(self, 'Error', 'No folder selected, <b>click \'Clear Selection\'</b> to '
                                                    'exclude folder from submission.')
            else:
                worker = Worker(self.preview_anon_tree)
                worker.signals.started.connect(self.preview_anon_tree_started)
                worker.signals.result.connect(self.preview_anon_tree_finished)
                self.threadpool.start(worker)
        else:
            pass

    def preview_anon_tree_started(self):
        self.status_label.setText('Constructing preview tree, please wait...')

    def preview_anon_tree_finished(self):
        # self.status_label.setText('')
        self.display_user_folder_props()

    def preview_anon_tree_2(self):
        self.anon_dir_dict_2 = _pickle.loads(_pickle.dumps(self.og_dir_dict_2))
        self.anon_dir_dict_2 = anonymize_stat(self.anon_dir_dict_2,
                                              self.unchecked_items_set_2,
                                              self.renamed_items_dict_2)
        self.refresh_treeview(self.anon_model_2,
                              self.anon_tree_2,
                              self.anon_dir_dict_2,
                              checkable=False, anon_tree=True)
        self.expanded_items_list_2 = []
        self.list_expanded(self.og_tree_2, self.og_root_item_2, 0, self.expanded_items_list_2)
        self.expand_items(self.anon_tree_2, self.anon_root_item_2, 0, self.expanded_items_list_2)

    def preview_anon_tree_threaded_2(self):
        if self.root_path_2 != '':
            if len(self.unchecked_items_set_2) == len(self.og_dir_dict_2.keys()):
                self.anon_model_2.removeRow(0)
                for row in range(22):
                    label_key = self.user_folder_props_table.item(row, 1).data(Qt.UserRole)
                    value_item = QTableWidgetItem('?')
                    value_item.setData(Qt.UserRole, label_key)
                    value_item.setTextAlignment(Qt.AlignRight)
                    value_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    self.user_folder_props_table.setItem(row, 1, value_item)
                self.dir_error.about(self, 'Error', 'No folder selected, <b>click \'Clear Selection\'</b> to '
                                                    'exclude folder from submission.')
            else:
                worker = Worker(self.preview_anon_tree_2)
                worker.signals.started.connect(self.preview_anon_tree_started_2)
                worker.signals.result.connect(self.preview_anon_tree_finished_2)
                self.threadpool.start(worker)
        else:
            pass

    def preview_anon_tree_started_2(self):
        self.status_label.setText('Constructing preview tree, please wait...')

    def preview_anon_tree_finished_2(self):
        # self.status_label.setText('')
        self.display_user_folder_props()

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
        self.list_expanded(self.og_tree_3, self.og_root_item_3, 0, self.expanded_items_list_3)
        self.expand_items(self.anon_tree_3, self.anon_root_item_3, 0, self.expanded_items_list_3)

    def preview_anon_tree_threaded_3(self):
        if self.root_path_3 != '':
            if len(self.unchecked_items_set_3) == len(self.og_dir_dict_3.keys()):
                self.anon_model_3.removeRow(0)
                for row in range(22):
                    label_key = self.user_folder_props_table.item(row, 1).data(Qt.UserRole)
                    value_item = QTableWidgetItem('?')
                    value_item.setData(Qt.UserRole, label_key)
                    value_item.setTextAlignment(Qt.AlignRight)
                    value_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    self.user_folder_props_table.setItem(row, 1, value_item)
                self.dir_error.about(self, 'Error', 'No folder selected, <b>click \'Clear Selection\'</b> to '
                                                    'exclude folder from submission.')
            else:
                worker = Worker(self.preview_anon_tree_3)
                worker.signals.started.connect(self.preview_anon_tree_started_3)
                worker.signals.result.connect(self.preview_anon_tree_finished_3)
                self.threadpool.start(worker)
        else:
            pass

    def preview_anon_tree_started_3(self):
        self.status_label.setText('Constructing preview tree, please wait...')

    def preview_anon_tree_finished_3(self):
        # self.status_label.setText('')
        self.display_user_folder_props()

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
        self.list_expanded(self.og_tree_4, self.og_root_item_4, 0, self.expanded_items_list_4)
        self.expand_items(self.anon_tree_4, self.anon_root_item_4, 0, self.expanded_items_list_4)

    def preview_anon_tree_threaded_4(self):
        if self.root_path_4 != '':
            if len(self.unchecked_items_set_4) == len(self.og_dir_dict_4.keys()):
                self.anon_model_4.removeRow(0)
                for row in range(22):
                    label_key = self.user_folder_props_table.item(row, 1).data(Qt.UserRole)
                    value_item = QTableWidgetItem('?')
                    value_item.setData(Qt.UserRole, label_key)
                    value_item.setTextAlignment(Qt.AlignRight)
                    value_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    self.user_folder_props_table.setItem(row, 1, value_item)
                self.dir_error.about(self, 'Error', 'No folder selected, <b>click \'Clear Selection\'</b> to '
                                                    'exclude folder from submission.')
            else:
                worker = Worker(self.preview_anon_tree_4)
                worker.signals.started.connect(self.preview_anon_tree_started_4)
                worker.signals.result.connect(self.preview_anon_tree_finished_4)
                self.threadpool.start(worker)
        else:
            pass

    def preview_anon_tree_started_4(self):
        self.status_label.setText('Constructing preview tree, please wait...')

    def preview_anon_tree_finished_4(self):
        # self.status_label.setText('')
        self.display_user_folder_props()

    def display_user_folder_props(self):
        try:
            anon_dir_dict_list = []
            if self.root_path != '' and len(self.unchecked_items_set) != len(self.og_dir_dict.keys()):
                anon_dir_dict_list.append(self.anon_dir_dict)
            if self.root_path_2 != '' and len(self.unchecked_items_set_2) != len(self.og_dir_dict_2.keys()):
                anon_dir_dict_list.append(self.anon_dir_dict_2)
            if self.root_path_3 != '' and len(self.unchecked_items_set_3) != len(self.og_dir_dict_3.keys()):
                anon_dir_dict_list.append(self.anon_dir_dict_3)
            if self.root_path_4 != '' and len(self.unchecked_items_set_4) != len(self.og_dir_dict_4.keys()):
                anon_dir_dict_list.append(self.anon_dir_dict_4)
            self.user_folder_props = drive_measurement(anon_dir_dict_list)
            self.user_folder_typical = check_collection_properties(self.user_folder_props)
            for row in range(22):
                label_key = self.user_folder_props_table.item(row, 1).data(Qt.UserRole)
                value_item = QTableWidgetItem(str(round(self.user_folder_props[label_key], 1)))
                value_item.setData(Qt.UserRole, label_key)
                value_item.setTextAlignment(Qt.AlignRight)
                value_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.user_folder_props_table.setItem(row, 1, value_item)
            self.user_folder_props_table.reset()
        except Exception as e:
            print(e)
            self.dir_error.about(self, 'Error', 'Incapable of computing statistics with current '
                                                'root and/or folder selections: ' + str(e) + '<br><br>' +
                                                '<b>Please modify root and/or folder selections.</b>')
            self.user_folder_typical = False
            for row in range(22):
                label_key = self.user_folder_props_table.item(row, 1).data(Qt.UserRole)
                value_item = QTableWidgetItem('?')
                value_item.setData(Qt.UserRole, label_key)
                value_item.setTextAlignment(Qt.AlignRight)
                value_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.user_folder_props_table.setItem(row, 1, value_item)
        # self.user_folder_typical = True  # for testing upload, comment out if not testing
        if self.user_folder_typical:
            self.submit_btn.setEnabled(True)
            is_typical_str = 'Values in nominal range, submit?'
        elif not self.user_folder_typical:
            is_typical_str = 'Values are atypical, data not acceptable for submission.'
        # self.user_folder_typical_label.setText(is_typical_str)
        self.status_label.setText(is_typical_str)

    def show_file_dialog(self):
        dirpath = QFileDialog.getExistingDirectory(self, 'Select Folder', self.root_path)
        if dirpath:
            root2 = Path(self.root_path_2)
            root3 = Path(self.root_path_3)
            root4 = Path(self.root_path_4)
            root1 = Path(dirpath)
            if root2 in root1.parents or root3 in root1.parents or root4 in root1.parents:
                self.dir_error.about(self, 'Error', 'Unable to select directory.\n'
                                                    'Root Folder 1 is a subdirectory of another root folder.')
            elif root1 in root2.parents or root1 in root3.parents or root1 in root4.parents:
                self.dir_error.about(self, 'Error', 'Unable to select directory.\n'
                                                    'Root Folder 1 is a parent directory of another root folder.')
            elif root1 == root2 or root1 == root3 or root1 == root4:
                self.dir_error.about(self, 'Error', 'Unable to select directory.\n'
                                                    'Root Folder 1 has already been selected in another tab.')
            else:
                self.root_path = os.path.abspath(dirpath)
                self.folder_edit.setText(self.root_path)
                self.build_tree_structure_threaded(self.root_path)

    def show_file_dialog_2(self):
        dirpath = QFileDialog.getExistingDirectory(self, 'Select Folder', self.root_path_2)
        if dirpath:
            root1 = Path(self.root_path)
            root3 = Path(self.root_path_3)
            root4 = Path(self.root_path_4)
            root2 = Path(dirpath)
            if root1 in root2.parents or root3 in root2.parents or root4 in root2.parents:
                self.dir_error.about(self, 'Error', 'Unable to select directory.\n'
                                                    'Root Folder 2 is a subdirectory of another root folder.')
            elif root2 in root1.parents or root2 in root3.parents or root2 in root4.parents:
                self.dir_error.about(self, 'Error', 'Unable to select directory.\n'
                                                    'Root Folder 2 is a parent directory another root folder.')
            elif root2 == root1 or root2 == root3 or root2 == root4:
                self.dir_error.about(self, 'Error', 'Unable to select directory.\n'
                                                    'Root Folder 2 has already been selected in another tab.')
            else:
                self.root_path_2 = os.path.abspath(dirpath)
                self.folder_edit_2.setText(self.root_path_2)
                self.build_tree_structure_threaded_2(self.root_path_2)

    def show_file_dialog_3(self):
        dirpath = QFileDialog.getExistingDirectory(self, 'Select Folder', self.root_path_3)
        if dirpath:
            root1 = Path(self.root_path)
            root2 = Path(self.root_path_2)
            root4 = Path(self.root_path_4)
            root3 = Path(dirpath)
            if root1 in root3.parents or root2 in root3.parents or root4 in root3.parents:
                self.dir_error.about(self, 'Error', 'Unable to select directory.\n'
                                                    'Root Folder 3 is a subdirectory of another root folder.')
            elif root3 in root1.parents or root3 in root2.parents or root3 in root4.parents:
                self.dir_error.about(self, 'Error', 'Unable to select directory.\n'
                                                    'Root Folder 3 is a parent directory of another root folder.')
            elif root3 == root1 or root3 == root2 or root3 == root4:
                self.dir_error.about(self, 'Error', 'Unable to select directory.\n'
                                                    'Root Folder 3 has already been selected in another tab.')
            else:
                self.root_path_3 = os.path.abspath(dirpath)
                self.folder_edit_3.setText(self.root_path_3)
                self.build_tree_structure_threaded_3(self.root_path_3)

    def show_file_dialog_4(self):
        dirpath = QFileDialog.getExistingDirectory(self, 'Select Folder', self.root_path_4)
        if dirpath:
            root1 = Path(self.root_path)
            root2 = Path(self.root_path_2)
            root3 = Path(self.root_path_3)
            root4 = Path(dirpath)
            if root1 in root4.parents or root2 in root4.parents or root3 in root4.parents:
                self.dir_error.about(self, 'Error', 'Unable to select directory.\n'
                                                    'Root Folder 4 is a subdirectory of another root folder.')
            elif root4 in root1.parents or root4 in root2.parents or root4 in root3.parents:
                self.dir_error.about(self, 'Error', 'Unable to select directory.\n'
                                                    'Root Folder 4 is a parent directory of another root folder.')
            elif root4 == root1 or root4 == root2 or root4 == root3:
                self.dir_error.about(self, 'Error', 'Unable to select directory.\n'
                                                    'Root Folder 4 has already been selected in another tab.')
            else:
                self.root_path_4 = os.path.abspath(dirpath)
                self.folder_edit_4.setText(self.root_path_4)
                self.build_tree_structure_threaded_4(self.root_path_4)

    def clear_root(self):
        self.root_path = ''
        self.og_dir_dict, self.anon_dir_dict = dict(), dict()
        self.unchecked_items_set = set()
        self.renamed_items_dict = dict()
        self.folder_edit.setText(self.root_path)
        self.og_model.removeRow(0)
        self.anon_model.removeRow(0)
        self.status_label.setText('No root selected in this tab. Click \'Preview\' in another tab that has a root.')

    def clear_root_2(self):
        self.root_path_2 = ''
        self.og_dir_dict_2, self.anon_dir_dict_2 = dict(), dict()
        self.unchecked_items_set_2 = set()
        self.renamed_items_dict_2 = dict()
        # self.og_tree_2 = QTreeView()
        # self.og_model_2 = QStandardItemModel()
        # self.anon_tree_2 = QTreeView()
        # self.anon_model_2 = QStandardItemModel()
        self.folder_edit_2.setText(self.root_path_2)
        self.og_model_2.removeRow(0)
        self.anon_model_2.removeRow(0)
        # self.build_tree_structure_threaded_2(self.root_path_2)
        # self.refresh_treeview(self.og_model_2, self.og_tree_2, self.og_dir_dict_2)
        # self.refresh_treeview(self.anon_model_2, self.anon_tree_2, self.anon_dir_dict_2, checkable=False, anon_tree=True)
        self.status_label.setText('No root selected in this tab. Click \'Preview\' in another tab that has a root.')

    def clear_root_3(self):
        self.root_path_3 = ''
        self.og_dir_dict_3, self.anon_dir_dict_3 = dict(), dict()
        self.unchecked_items_set_3 = set()
        self.renamed_items_dict_3 = dict()
        self.folder_edit_3.setText(self.root_path_3)
        self.og_model_3.removeRow(0)
        self.anon_model_3.removeRow(0)
        self.status_label.setText('No root selected in this tab. Click \'Preview\' in another tab that has a root.')

    def clear_root_4(self):
        self.root_path_4 = ''
        self.og_dir_dict_4, self.anon_dir_dict_4 = dict(), dict()
        self.unchecked_items_set_4 = set()
        self.renamed_items_dict_4 = dict()
        self.folder_edit_4.setText(self.root_path_4)
        self.og_model_4.removeRow(0)
        self.anon_model_4.removeRow(0)
        self.status_label.setText('No root selected in this tab. Click \'Preview\' in another tab that has a root.')

    def upload_collected_data(self):
        # ATTENTION: For large files, this needs have its own separate thread
        data_list = []
        if self.root_path != '' and len(self.unchecked_items_set) != len(self.og_dir_dict.keys()):
            data_1 = bytes(json.dumps(self.anon_dir_dict), 'utf8')
            data_1 = compress_data(data_1)
            data_list.append(data_1)
        if self.root_path_2 != '' and len(self.unchecked_items_set_2) != len(self.og_dir_dict_2.keys()):
            data_2 = bytes(json.dumps(self.anon_dir_dict_2), 'utf8')
            data_2 = compress_data(data_2)
            data_list.append(data_2)
        if self.root_path_3 != '' and len(self.unchecked_items_set_3) != len(self.og_dir_dict_3.keys()):
            data_3 = bytes(json.dumps(self.anon_dir_dict_3), 'utf8')
            data_3 = compress_data(data_3)
            data_list.append(data_3)
        if self.root_path_4 != ''  and len(self.unchecked_items_set_4) != len(self.og_dir_dict_4.keys()):
            data_4 = bytes(json.dumps(self.anon_dir_dict_4), 'utf8')
            data_4 = compress_data(data_4)
            data_list.append(data_4)
        encrypted_json_list, encrypted_jsonkey = encrypt_data(data_list)
        unique_id = generate_filename()
        for ix, encrypted_json in enumerate(encrypted_json_list):
            dropbox_upload(encrypted_json,
                           get_filepath(self.dbx_json_dirpath, unique_id + '_dir_dict_' + str(ix+1) + '.enc'))
        dropbox_upload(encrypted_jsonkey,
                       get_filepath(self.dbx_json_dirpath, unique_id + '_sym_key.enc'))
        self.status_label.setText('Data uploaded. Thanks!')

    def test_script(self):
        unchecked_items_list = []
        self.list_unchecked(self.root_item, 0, unchecked_items_list)
        print(set(self.og_dir_dict.keys()).difference(self.anon_dir_dict.keys()))
        print(unchecked_items_list)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    daw = DriveAnalysisWidget()
    sys.exit(app.exec_())
