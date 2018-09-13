import traceback
import sys
import os
import time
import math
from PyQt5.QtWidgets import QWidget, QToolTip, QPushButton, QMainWindow, QApplication, QMessageBox, QDesktopWidget, \
    QFileDialog, QSlider, QAbstractSlider, QLineEdit, QGridLayout, QLabel, QTreeView, QFileSystemModel, QTreeWidget, \
    QTreeWidgetItem, QAbstractItemView, QHeaderView, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import Qt, QThread, pyqtSlot, pyqtSignal, QObject, QRunnable, QThreadPool
from PyQt5.QtGui import QFont, QIcon, QMovie, QStandardItemModel, QStandardItem
from copy import deepcopy
from compress_and_prune_v4_1 import read_and_count, simplify_tree, print_tree


# BUG ALERT
# BUG: simplify_tree crashes if all folders do not contain a single file due to dir_dict being empty
# OPTIMIZATION
# OPT: Bulk of processing time is from read_and_count, while simplify_tree is quick
# Instead of current simplify_tree_structure where read_and_count is called constantly, only call read_and_count
# when folder is changed.

class ZoomerMainWindow(QMainWindow):

    def __init__(self, parent=None):
        super(ZoomerMainWindow, self).__init__(parent)
        self.zoomer_widget = ZoomerWidget(self)
        self.setCentralWidget(self.zoomer_widget)
        self.initUI()

    def initUI(self):
        QToolTip.setFont(QFont('SansSerif', 10))
        self.statusBar().showMessage('Ready.')
        self.setToolTip('<b>GIMZoomer</b>: File structure simplication program.')
        self.resize(640, 480)
        self.center()

        self.setWindowTitle('GIMZoomer')
        self.show()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


class WorkerSignals(QObject):
    started = pyqtSignal()
    result = pyqtSignal(object)
    finished = pyqtSignal()


class Worker(QRunnable):

    # def __init__(self, root_path, dir_dict, prune_thold):
    #     super(SimplifyWorker, self).__init__()
    #     self.root_path = root_path
    #     self.dir_dict = dir_dict
    #     self.prune_thold = prune_thold
    #     self.signals = WorkerSignals()

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
            # simplified_dir_dict = simplify_tree(self.root_path, 1, self.dir_dict, 0.95, self.prune_thold, print_=False)
        except:
            traceback.print_exc()
            print('Error!')
            pass
        else:
            # self.signals.result.emit(simplified_dir_dict)
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


class ZoomerWidget(QWidget):
    # def __init__(self, parent=None):
    def __init__(self):
        super().__init__()
        # super(ZoomerWidget, self).__init__(parent)
        # self.parent = parent
        # self.initUI()

        self.setWindowTitle('GIMZoomer')
        # self.prune_thold = 95  # only use when slider scroll direction is reversed
        self.prune_thold = 4
        # self.root_path = os.path.expanduser('~')
        self.root_path = os.path.expanduser('C:\\Users\\ultra\\Dropbox\\mcgill')
        # self.root_path = os.path.expanduser('C:\\Users\\ultra\\Documents')
        self.threadpool = QThreadPool()

        # self.proc_lbl = QLabel()
        # self.proc_lbl.setAlignment(Qt.AlignCenter)
        # self.proc_mov = QMovie('ajax-loader.gif')
        # self.proc_lbl.setMovie(self.proc_mov)
        # # self.proc_lbl.setText('placeholder')
        # # self.proc_mov.start()

        select_btn = QPushButton('Select Folder', self)
        select_btn.setToolTip('Select <b>root folder</b> to simplify.')
        select_btn.clicked.connect(self.show_file_dialog)
        select_btn.resize(select_btn.sizeHint())

        # self.folder_edit = QLineEdit()
        # self.folder_edit.setReadOnly(True)
        self.folder_edit = QLabel()
        self.folder_edit.setText(self.root_path)

        self.abort_btn = QPushButton('Abort', self)
        self.abort_btn.setToolTip('Abort file structure simplification.')
        # self.abort_btn.clicked.connect(self.abort_workers)
        self.abort_btn.resize(self.abort_btn.sizeHint())
        self.abort_btn.setDisabled(True)

        self.status_label = QLabel()
        self.status_label.setText('')

        self.slider_label_top = QLabel()
        self.slider_label_top.setAlignment(Qt.AlignCenter)
        # self.slider_label_top.setText('Pruning\nThreshold:\n' + '{:.3f}'.format(self.scale_pruning(self.prune_thold)))
        self.slider_label_top.setText('Few important folders')

        self.slider_label_btm = QLabel()
        self.slider_label_btm.setAlignment(Qt.AlignCenter)
        self.slider_label_btm.setText('All folders')

        self.slider = QSlider(Qt.Vertical, self)  # for dynamically changing pruning threshold, default is 0.02
        self.slider.setValue(self.prune_thold)
        self.slider.setTickPosition(QSlider.TicksBothSides)
        self.slider.setTickInterval(10)
        self.slider.valueChanged[int].connect(self.slider_value_change)
        # self.slider.setInvertedAppearance(True)

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
        # self.ogtree.header().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.tree = QTreeView(self)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Folder Name', 'Accessible Files', 'Number of Files'])
        # self.tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)

        # self.dir_dict, self.og_dir_dict = self.build_tree_structure_threaded(self.root_path)
        self.dir_dict, self.og_dir_dict = dict(), dict()
        self.build_tree_structure_threaded(self.root_path, self.prune_thold)
        # self.simplify_tree_structure_threaded(self.root_path, self.dir_dict, self.prune_thold)
        # self.simplify_tree_structure()

        grid = QGridLayout()
        grid.addWidget(select_btn, 0, 0, 1, 1)
        grid.addWidget(self.folder_edit, 0, 1, 1, 6)
        grid.addWidget(self.status_label, 0, 7, 1, 1)
        grid.addWidget(self.abort_btn, 0, 8, 1, 1)
        grid.addWidget(ogtree_label, 1, 0, 1, 4)
        grid.addWidget(self.slider_label_top, 1, 4, 1, 1)
        grid.addWidget(tree_label, 1, 5, 1, 4)
        grid.addWidget(self.ogtree, 2, 0, 1, 4)
        grid.addWidget(self.slider, 2, 4, 1, 1, alignment=Qt.AlignHCenter)
        grid.addWidget(self.tree, 2, 5, 1, 4)
        grid.addWidget(self.slider_label_btm, 3, 4, 1, 1)

        self.setLayout(grid)
        self.resize(640, 480)
        self.show()

    def scale_pruning(self, prune_thold):
        # # for reversing the slider scroll direction
        # scale_dict = dict(zip(range(100), range(100)[::-1]))
        # return scale_dict[prune_thold] * 0.005
        return prune_thold * 0.005
        # return math.log(prune_thold, 10)/2
        # return math.exp(prune_thold)/math.exp(100)

    def show_file_dialog(self):
        dirpath = QFileDialog.getExistingDirectory(self, 'Select Folder', self.root_path)
        if dirpath:
            self.root_path = os.path.abspath(dirpath)
            self.folder_edit.setText(self.root_path)
            # self.dir_dict, self.og_dir_dict = self.build_tree_structure_threaded(self.root_path)
            self.build_tree_structure_threaded(self.root_path, self.prune_thold)
            # self.simplify_tree_structure_threaded(self.root_path, self.dir_dict, self.prune_thold)
            # worker = SimplifyWorker(self.execute_this_fn, self.root_path, self.dir_dict, self.scale_pruning(self.prune_thold))
            # worker.signals.started.connect(self.simplify_started)
            # worker.signals.result.connect(self.simplify_finished)
            # worker.signals.finished.connect(self.print_output)
            # self.threadpool.start(worker)

    def slider_value_change(self, value):
        # print(value)
        self.prune_thold = value
        # self.slider_label.setText('Pruning\nThreshold:\n' + '{:.3f}'.format(self.scale_pruning(self.prune_thold)))
        self.dir_dict = deepcopy(self.og_dir_dict)
        self.simplify_tree_structure_threaded(self.root_path, self.dir_dict, self.prune_thold)
        # worker = SimplifyWorker(self.execute_this_fn, self.root_path, self.dir_dict, self.scale_pruning(self.prune_thold))
        # worker.signals.started.connect(self.simplify_started)
        # worker.signals.result.connect(self.simplify_finished)
        # worker.signals.finished.connect(self.print_output)
        # self.threadpool.start(worker)

    def build_tree_structure_threaded(self, root_path, prune_thold):
        worker = Worker(self.build_tree_structure, root_path, prune_thold)
        worker.signals.started.connect(self.build_tree_started)
        worker.signals.result.connect(self.build_tree_finished)
        worker.signals.finished.connect(self.print_output)
        self.threadpool.start(worker)

    def simplify_tree_structure_threaded(self, root_path, dir_dict, prune_thold):
        # dir_dict = simplify_tree(root_path, 1, dir_dict, 0.95, self.scale_pruning(prune_thold), print_=False)
        # self.refresh_treeview(self.model, self.tree, dir_dict)
        # print_tree(root_path, dir_dict)
        worker = Worker(self.simplify_tree_structure, root_path, dir_dict, prune_thold)
        worker.signals.started.connect(self.simplify_tree_started)
        worker.signals.result.connect(self.simplify_tree_finished)
        worker.signals.finished.connect(self.print_output)
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

    def print_output(self):
        print('Done!')

    def build_tree_started(self):
        print('Build started.')
        self.abort_btn.setEnabled(True)
        self.status_label.setText('<font color="red"><b>Building tree, please wait...</b></font>')

    def build_tree_finished(self, result):
        print('Build finished!')
        self.abort_btn.setDisabled(True)
        self.og_dir_dict, self.dir_dict = result
        self.refresh_treeview(self.ogmodel, self.ogtree, self.og_dir_dict)
        self.refresh_treeview(self.model, self.tree, self.dir_dict)
        self.status_label.setText('')

    def simplify_tree_started(self):
        print('Simplify started.')
        self.abort_btn.setEnabled(True)
        self.status_label.setText('<font color="red"><b>Simplifying tree, simplifying tree...</b></font>')
        # self.parent.statusBar().showMessage('Please wait...')

    def simplify_tree_finished(self, dir_dict):
        print('Simplify finished!')
        self.abort_btn.setDisabled(True)
        self.refresh_treeview(self.model, self.tree, dir_dict)
        self.status_label.setText('')
        # self.parent.statusBar().showMessage('File structure simplified.')

    def refresh_treeview(self, model, tree, dir_dict):
        model.removeRow(0)
        parent = model.invisibleRootItem()
        self.append_all_children(1, dir_dict, parent)  # dir_dict key starts at 1 since 0==False
        tree.setModel(model)
        tree.expandToDepth(0)
        tree.resizeColumnToContents(0)
        tree.resizeColumnToContents(1)
        tree.resizeColumnToContents(2)

    def append_all_children(self, dirkey, dir_dict, qitem):
        qitem.appendRow([QStandardItem(dir_dict[dirkey][0]),
                         QStandardItem(str(dir_dict[dirkey][4])),
                         QStandardItem(str(len(dir_dict[dirkey][3])))])
        current_row = qitem.rowCount()-1
        # for child in sorted(dir_dict[dirkey][2]):
        #     self.append_all_children(child, dir_dict, qitem.child(current_row))
        children_keys = dir_dict[dirkey][2]
        children_names = [dir_dict[child][0].lower() for child in children_keys]
        for child_name, child_key in sorted(zip(children_names, children_keys)):
            self.append_all_children(child_key, dir_dict, qitem.child(current_row))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # zmw = ZoomerMainWindow()
    zw = ZoomerWidget()
    # zmw.show()
    sys.exit(app.exec_())
