import traceback
import sys
import os
from PyQt5.QtWidgets import QWidget, QPushButton, QApplication, QFileDialog, QSlider, QGridLayout, QLabel, \
    QTreeView, QAbstractItemView, QHeaderView, QCheckBox
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QObject, QRunnable, QThreadPool
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from copy import deepcopy
from compress_and_prune_v4_1 import read_and_count, simplify_tree


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


class ZoomerWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('GIMZoomer')
        self.prune_thold = 4
        self.root_path = os.path.expanduser('~')
        self.threadpool = QThreadPool()
        self.resize_mode = 'dynamic'

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

        self.resize_mode_cb = QCheckBox('Resize columns automatically', self)
        self.resize_mode_cb.toggle()
        self.resize_mode_cb.stateChanged.connect(self.change_resize_mode)

        self.slider_label_top = QLabel()
        self.slider_label_top.setAlignment(Qt.AlignCenter)
        self.slider_label_top.setText('Few important folders')

        self.slider_label_btm = QLabel()
        self.slider_label_btm.setAlignment(Qt.AlignCenter)
        self.slider_label_btm.setText('All folders')

        self.slider = QSlider(Qt.Vertical, self)  # for dynamically changing pruning threshold, default is 0.02
        self.slider.setValue(self.prune_thold)
        self.slider.setTickPosition(QSlider.TicksBothSides)
        self.slider.setTickInterval(10)
        self.slider.valueChanged[int].connect(self.slider_value_change)

        ogtree_label = QLabel()
        ogtree_label.setAlignment(Qt.AlignCenter)
        ogtree_label.setText('Original Structure')

        tree_label = QLabel()
        tree_label.setAlignment(Qt.AlignCenter)
        tree_label.setText('Pruned Structure\n(Ordered by Folder Importance)')

        self.ogtree = QTreeView(self)
        self.ogtree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ogmodel = QStandardItemModel()
        self.ogmodel.setHorizontalHeaderLabels(['Folder Name', 'Accessible Files', 'Number of Files'])

        self.tree = QTreeView(self)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Folder Name', 'Accessible Files', 'Number of Files'])

        self.dir_dict, self.og_dir_dict = dict(), dict()
        self.build_tree_structure_threaded(self.root_path, self.prune_thold)

        grid = QGridLayout()
        grid.addWidget(select_btn, 0, 0, 1, 1)
        grid.addWidget(self.folder_edit, 0, 1, 1, 8)
        grid.addWidget(self.status_label, 1, 0, 1, 9)
        grid.addWidget(self.resize_mode_cb, 2, 0, 1, 3)
        grid.addWidget(ogtree_label, 3, 0, 1, 4)
        grid.addWidget(self.slider_label_top, 3, 4, 1, 1)
        grid.addWidget(tree_label, 3, 5, 1, 4)
        grid.addWidget(self.ogtree, 4, 0, 1, 4)
        grid.addWidget(self.slider, 4, 4, 1, 1, alignment=Qt.AlignHCenter)
        grid.addWidget(self.tree, 4, 5, 1, 4)
        grid.addWidget(self.slider_label_btm, 5, 4, 1, 1)

        self.setLayout(grid)
        self.resize(640, 480)
        self.show()

    def change_resize_mode(self, state):
        if state == Qt.Checked:
            self.resize_mode = 'dynamic'
        else:
            self.resize_mode = 'static'
        self.refresh_tree_header(self.ogtree, self.resize_mode)
        self.refresh_tree_header(self.tree, self.resize_mode)

    def refresh_tree_header(self, tree, resize_mode):
        if resize_mode == 'dynamic':
            tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        elif resize_mode == 'static':
            tree.header().setSectionResizeMode(0, QHeaderView.Interactive)
            tree.header().setSectionResizeMode(1, QHeaderView.Interactive)
            tree.header().setSectionResizeMode(2, QHeaderView.Interactive)

    def scale_pruning(self, prune_thold):
        return prune_thold * 0.005

    def show_file_dialog(self):
        dirpath = QFileDialog.getExistingDirectory(self, 'Select Folder', self.root_path)
        if dirpath:
            self.root_path = os.path.abspath(dirpath)
            self.folder_edit.setText(self.root_path)
            self.build_tree_structure_threaded(self.root_path, self.prune_thold)

    def slider_value_change(self, value):
        self.prune_thold = value
        self.dir_dict = deepcopy(self.og_dir_dict)
        self.simplify_tree_structure_threaded(self.root_path, self.dir_dict, self.prune_thold)

    def build_tree_structure_threaded(self, root_path, prune_thold):
        worker = Worker(self.build_tree_structure, root_path, prune_thold)
        worker.signals.started.connect(self.build_tree_started)
        worker.signals.result.connect(self.build_tree_finished)
        self.threadpool.start(worker)

    def simplify_tree_structure_threaded(self, root_path, dir_dict, prune_thold):
        worker = Worker(self.simplify_tree_structure, root_path, dir_dict, prune_thold)
        worker.signals.started.connect(self.simplify_tree_started)
        worker.signals.result.connect(self.simplify_tree_finished)
        self.threadpool.start(worker)

    def build_tree_structure(self, root_path, prune_thold):
        self.slider.setDisabled(True)
        dir_dict = read_and_count(root_path)
        og_dir_dict = deepcopy(dir_dict)
        dir_dict = simplify_tree(root_path, 1, dir_dict, 0.95, self.scale_pruning(prune_thold), print_=False)
        self.slider.setEnabled(True)
        return og_dir_dict, dir_dict

    def simplify_tree_structure(self, root_path, dir_dict, prune_thold):
        dir_dict = simplify_tree(root_path, 1, dir_dict, 0.95, self.scale_pruning(prune_thold), print_=False)
        return dir_dict

    def build_tree_started(self):
        self.status_label.setText('Building tree, slider disabled, please wait...')

    def build_tree_finished(self, result):
        self.og_dir_dict, self.dir_dict = result
        self.refresh_treeview(self.ogmodel, self.ogtree, self.og_dir_dict)
        self.refresh_treeview(self.model, self.tree, self.dir_dict)
        self.status_label.setText('')

    def simplify_tree_started(self):
        self.status_label.setText('Simplifying tree, please wait...')

    def simplify_tree_finished(self, dir_dict):
        self.refresh_treeview(self.model, self.tree, dir_dict)
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
    zw = ZoomerWidget()
    sys.exit(app.exec_())
