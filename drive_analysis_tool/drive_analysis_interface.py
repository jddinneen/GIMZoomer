import traceback
import sys
import os
from PyQt5.QtWidgets import QWidget, QPushButton, QApplication, QFileDialog, QSlider, QGridLayout, QLabel, \
    QTreeView, QAbstractItemView, QHeaderView, QCheckBox
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QObject, QRunnable, QThreadPool
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from copy import deepcopy
from compress_and_prune_v4_1 import read_and_count, simplify_tree
from drive_analysis_tool.drive_analyzer import record_stat, anonymize_stat, find_all_children


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
        # self.root_path = os.path.expanduser('~')  # BUG 2018-09-18: No permission to access certain files for os.stat
        self.root_path = os.path.expanduser('~\\Downloads')
        self.threadpool = QThreadPool()

        select_btn = QPushButton('Select Folder', self)
        select_btn.setToolTip('Select <b>root folder</b> to simplify.')
        select_btn.clicked.connect(self.show_file_dialog)
        select_btn.resize(select_btn.sizeHint())

        self.folder_edit = QLabel()
        self.folder_edit.setText(self.root_path)

        self.status_label = QLabel()
        self.status_label.setText('')
        self.status_label.setStyleSheet("color: red;"
                                        "font: bold;")

        ogtree_label = QLabel()
        ogtree_label.setAlignment(Qt.AlignCenter)
        ogtree_label.setText('Original folders data')

        anontree_label = QLabel()
        anontree_label.setAlignment(Qt.AlignCenter)
        anontree_label.setText('Anonymized folders data used for research')

        self.ogtree = QTreeView(self)
        self.ogtree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ogmodel = QStandardItemModel()
        self.ogmodel.setHorizontalHeaderLabels(['Folder Name', 'Number of Files'])

        self.anontree = QTreeView(self)
        self.anontree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.anonmodel = QStandardItemModel()
        self.anonmodel.setHorizontalHeaderLabels(['Folder Name', 'Number of Files'])

        self.dir_dict, self.og_dir_dict = dict(), dict()
        self.build_tree_structure_threaded(self.root_path)

        grid = QGridLayout()
        grid.addWidget(select_btn, 0, 0, 1, 1)
        grid.addWidget(self.folder_edit, 0, 1, 1, 8)
        grid.addWidget(self.status_label, 1, 0, 1, 9)
        grid.addWidget(ogtree_label, 3, 0, 1, 4)
        grid.addWidget(anontree_label, 3, 5, 1, 4)
        grid.addWidget(self.ogtree, 4, 0, 1, 4)
        grid.addWidget(self.anontree, 4, 5, 1, 4)

        self.setLayout(grid)
        self.resize(640, 480)
        self.show()

    def refresh_tree_header(self, tree, resize_mode='dynamic'):
        if resize_mode == 'dynamic':
            tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            # tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        elif resize_mode == 'static':
            tree.header().setSectionResizeMode(0, QHeaderView.Interactive)
            tree.header().setSectionResizeMode(1, QHeaderView.Interactive)
            # tree.header().setSectionResizeMode(2, QHeaderView.Interactive)

    def show_file_dialog(self):
        dirpath = QFileDialog.getExistingDirectory(self, 'Select Folder', self.root_path)
        if dirpath:
            self.root_path = os.path.abspath(dirpath)
            self.folder_edit.setText(self.root_path)
            self.build_tree_structure_threaded(self.root_path, self.prune_thold)

    def build_tree_structure_threaded(self, root_path):
        worker = Worker(self.build_tree_structure, root_path)
        worker.signals.started.connect(self.build_tree_started)
        worker.signals.result.connect(self.build_tree_finished)
        self.threadpool.start(worker)

    def anonymize_tree_structure_threaded(self, root_path, dir_dict, rename_dict, remove_dict):
        worker = Worker(self.anonymize_tree_structure, root_path, dir_dict, rename_dict, remove_dict)
        worker.signals.started.connect(self.anonymize_tree_started)
        worker.signals.result.connect(self.anonymize_tree_finished)
        self.threadpool.start(worker)

    def build_tree_structure(self, root_path):
        # self.slider.setDisabled(True)
        dir_dict = record_stat(root_path)
        og_dir_dict = deepcopy(dir_dict)
        # dir_dict = simplify_tree(root_path, 1, dir_dict, 0.95, self.scale_pruning(prune_thold), print_=False)
        # self.slider.setEnabled(True)
        return og_dir_dict, dir_dict

    def anonymize_tree_structure(self, dir_dict, rename_dict, remove_dict):
        # dir_dict = simplify_tree(root_path, 1, dir_dict, 0.95, self.scale_pruning(prune_thold), print_=False)
        dir_dict = anonymize_stat(dir_dict, rename_dict, remove_dict)
        return dir_dict

    def build_tree_started(self):
        self.status_label.setText('Building tree, please wait...')

    def build_tree_finished(self, result):
        self.og_dir_dict, self.dir_dict = result
        print(self.og_dir_dict[1],self.og_dir_dict[2], self.og_dir_dict[3])

        # self.refresh_treeview(self.ogmodel, self.ogtree, self.og_dir_dict)
        # #BUG 2018-09-18: crashes the interface because i am referring to non-existent dictionary keys
        # (see append_all_children, e.g., dir_dict[dirkey][0])
        # I've updated my dir_dict to use string names instead of integers so append_all_children
        # needs to be updated as well.

        # self.refresh_treeview(self.anonmodel, self.anontree, self.dir_dict)
        self.status_label.setText('')

    def anonymize_tree_started(self):
        self.status_label.setText('Anonymizing tree, please wait...')

    def anonymize_tree_finished(self, dir_dict):
        self.refresh_treeview(self.anonmodel, self.anontree, dir_dict)
        self.status_label.setText('')

    def refresh_treeview(self, model, tree, dir_dict):
        model.removeRow(0)
        parent = model.invisibleRootItem()
        self.append_all_children(1, dir_dict, parent)  # dir_dict key starts at 1 since 0==False
        tree.setModel(model)
        self.refresh_tree_header(tree, self.resize_mode)
        tree.expandToDepth(0)

    def append_all_children(self, dirkey, dir_dict, qitem):
        qitem.appendRow([QStandardItem(dir_dict[dirkey][0]),
                         QStandardItem(str(dir_dict[dirkey][4])),
                         QStandardItem(str(len(dir_dict[dirkey][3])))])
        current_row = qitem.rowCount()-1
        children_keys = dir_dict[dirkey][2]
        children_names = [dir_dict[child][0].lower() for child in children_keys]
        for child_name, child_key in sorted(zip(children_names, children_keys)):
            self.append_all_children(child_key, dir_dict, qitem.child(current_row))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    daw = DriveAnalysisWidget()
    sys.exit(app.exec_())
