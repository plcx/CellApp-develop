import sys
from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit,
                             QTextEdit, QGridLayout, QApplication, QPushButton, QFileDialog, QMessageBox,
                             QComboBox, QVBoxLayout, QProgressBar, QHBoxLayout, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QMutex, QWaitCondition
import traceback
import os
import glob
import nibabel as nib
from Utils.segment_lib import segmentation
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import cpu_count
from Utils.segment_lib import instance_segmentation_with_nucleus, instance_segmentation_without_nucleus


class Cell_Segmentation(QWidget):

    def __init__(self):
        super().__init__()
        self.mainlayout = QVBoxLayout()  # 组件的整体布局是垂直布局,第一层是一个栅格放参数,第二层是个水平布局放进度条, 最下层是一个反馈信息栏
        self.initUI()  # 设置参数相关的各种组件位置
        self.middlelayout = QGridLayout()
        self.runsegmentBtn = QPushButton("Run Segmentation")
        self.runsegmentBtn.clicked.connect(self.runSegmentation)
        self.cancelsegmentBtn = QPushButton("Cancel Segmentation")
        self.cancelsegmentBtn.setEnabled(False)
        self.cancelsegmentBtn.clicked.connect(self.cancelSegmentation)
        self.pausesegmentBtn = QPushButton("Pause Segmentation")
        self.pausesegmentBtn.setEnabled(False)
        self.pausesegmentBtn.clicked.connect(self.pauseSegmentation)
        self.resumesegmentBtn = QPushButton("Resume Segmentation")
        self.resumesegmentBtn.setEnabled(False)
        self.resumesegmentBtn.clicked.connect(self.resumeSegmentation)
        self.segmentBar = QProgressBar()
        self.segmentBar.valueChanged.connect(self.completeSegmentation)
        self.middlelayout.addWidget(self.runsegmentBtn, 0, 1)
        self.middlelayout.addWidget(self.cancelsegmentBtn, 0, 2)
        self.middlelayout.addWidget(self.pausesegmentBtn, 2, 1)
        self.middlelayout.addWidget(self.resumesegmentBtn, 2, 2)
        self.middlelayout.addWidget(self.segmentBar, 1, 3)
        self.mainlayout.addStretch(1)
        self.mainlayout.addLayout(self.middlelayout)

        self.textEdit = QTextEdit()  # 初始化反馈信息栏
        self.textEdit.setFocusPolicy(Qt.NoFocus)  # 将反馈信息栏设置为无法主动编辑
        self.mainlayout.addStretch(1)  # 将反馈信息栏压到垂直布局的底层
        self.mainlayout.addWidget(self.textEdit)  # 将反馈信息栏添加到整体布局中

        self.setLayout(self.mainlayout)
        self.setGeometry(300, 300, 450, 500)
        self.show()

    def initUI(self):

        projectFolder = QLabel('Project Folder')
        embryoName = QLabel('Embryo Name')
        modelName = QLabel('Model Name')
        kernelSize = QLabel('Kernel Size')
        kernelStructure = QLabel('Kernel Structure')
        Nuc = QLabel("Nucleus Position")

        self.projectFolderEdit = QLineEdit()
        self.embryoNameEdit = QComboBox()
        self.embryoNameEdit.activated[str].connect(self.Autofillmodel)
        self.modelNameEdit = QComboBox()
        self.kernelStructureEdit = QComboBox()
        self.kernelStructureEdit.addItems(["cube", "ball"])
        self.kernelSizeEdit = QComboBox()
        self.kernelSizeEdit.addItems(["3", "5", "7"])
        self.Nuc = QCheckBox('Whether to use segmented Nucleus position to segment whole cell')
        self.Nuc.stateChanged.connect(self.Nucchange)
        self.Nucinput = False

        projectFolderBtn = QPushButton("Select")
        projectFolderBtn.clicked.connect(self.chooseProjectFolder)

        grid = QGridLayout()
        grid.setSpacing(20)

        grid.addWidget(projectFolder, 1, 0)
        grid.addWidget(self.projectFolderEdit, 1, 1)
        grid.addWidget(projectFolderBtn, 1, 2)

        grid.addWidget(embryoName, 2, 0)
        grid.addWidget(self.embryoNameEdit, 2, 1)

        grid.addWidget(modelName, 3, 0)
        grid.addWidget(self.modelNameEdit, 3, 1)

        grid.addWidget(kernelStructure, 4, 0)
        grid.addWidget(self.kernelStructureEdit, 4, 1)

        grid.addWidget(kernelSize, 5, 0)
        grid.addWidget(self.kernelSizeEdit, 5, 1)

        grid.addWidget(Nuc, 6, 0)
        grid.addWidget(self.Nuc, 6, 1)

        self.mainlayout.addLayout(grid)

    def chooseProjectFolder(self):
        dirName = QFileDialog.getExistingDirectory(self, 'Choose RawStack Folder', './')
        try:
            self.textEdit.clear()
            self.embryoNameEdit.clear()
            self.projectFolderEdit.setText(dirName)
            if dirName:
                listdir = [x for x in os.listdir(os.path.join(dirName, "SegStack")) if not x.startswith(".")]
                listdir.sort()
                self.embryoNameEdit.addItems(listdir)
        except Exception as e:
            self.textEdit.setText(traceback.format_exc())
            QMessageBox.warning(self, 'Warning!', 'Please Choose Right Folder!')

    def Autofillmodel(self, embryo_name):
        try:
            self.modelNameEdit.clear()
            model_list = [x for x in os.listdir(os.path.join(self.projectFolderEdit.text(), "SegStack", embryo_name)) if
                          not (x.startswith(".") or x == "SegNuc")]
            model_list.sort()
            self.modelNameEdit.addItems(model_list)

        except:
            self.textEdit.setText(traceback.format_exc())
            QMessageBox.warning(self, 'Error!', 'Please check your path!')

    def runSegmentation(self):
        config = {}
        try:
            self.textEdit.clear()
            seg_memb_files = glob.glob(
                os.path.join(self.projectFolderEdit.text(), "SegStack", self.embryoNameEdit.currentText(),
                             self.modelNameEdit.currentText(), "SegMemb", "*.nii.gz"))

            seg_nuc_files = []
            assert len(seg_memb_files) > 0
            if self.Nucinput:
                seg_nuc_files = glob.glob(
                    os.path.join(self.projectFolderEdit.text(), "SegStack", self.embryoNameEdit.currentText(),
                                 self.modelNameEdit.currentText(), "SegNuc", "*.nii.gz"))
                assert len(seg_nuc_files) == len(seg_memb_files)
            config['project_folder'] = self.projectFolderEdit.text()
            config["embryo_name"] = self.embryoNameEdit.currentText()
            config['model_name'] = self.modelNameEdit.currentText()
            config["memb_files"] = seg_memb_files
            config["nuc_files"] = seg_nuc_files
            config["structure"] = self.kernelStructureEdit.currentText()
            config["size"] = int(self.kernelSizeEdit.currentText())
            config["nuc_input"] = self.Nucinput


        except AssertionError as e:
            config.clear()
            self.textEdit.append(traceback.format_exc())
            QMessageBox.warning(self, 'Error!', 'Membrane files do not match nucleus files')

        except Exception:
            config.clear()
            self.textEdit.append(traceback.format_exc())
            QMessageBox.warning(self, 'Error!', 'Please check your configs!')

        if config:
            try:
                self.textEdit.clear()
                self.textEdit.append("Running Cell Instance Segmentation!")
                self.textEdit.append(f"The embryo name is {config.get('embryo_name')}")
                self.textEdit.append(f"The model name is {config.get('model_name')}")
                self.textEdit.append(f"The structure is  {config.get('structure')}")
                self.textEdit.append(f"The kernel size is  {config.get('size')}")
                self.textEdit.append(f"Whether to use segment nucleus information {config.get('nuc_input')}")
                self.runsegmentBtn.setEnabled(False)
                self.resumesegmentBtn.setEnabled(False)
                self.cancelsegmentBtn.setEnabled(True)
                self.pausesegmentBtn.setEnabled(True)
                self.segmentBar.reset()
                self.cthread = CellSegmentThread(config)
                self.cthread.segmentbarSignal.connect(self.showsegmentbar)
                self.cthread.segmentexcSignal.connect(self.segmentexc)
                self.cthread.start()
            except:
                self.textEdit.append(traceback.format_exc())
                QMessageBox.warning(self, 'Error!', 'Can not start Preprocess!')

    def pauseSegmentation(self):
        try:
            self.cthread.pause()
            self.runsegmentBtn.setEnabled(False)
            self.resumesegmentBtn.setEnabled(True)
            self.cancelsegmentBtn.setEnabled(True)
            self.pausesegmentBtn.setEnabled(False)
            self.textEdit.append("Segment Suspend!")
        except Exception:
            self.textEdit.append(traceback.format_exc())
            QMessageBox.warning(self, 'Warning!', 'Segment pause fail!.')

    def cancelSegmentation(self):
        try:
            self.cthread.cancel()
            self.runsegmentBtn.setEnabled(True)
            self.resumesegmentBtn.setEnabled(False)
            self.cancelsegmentBtn.setEnabled(False)
            self.pausesegmentBtn.setEnabled(False)
            self.textEdit.setText("Segment Cancel!")
            self.segmentBar.setValue(0)
            QMessageBox.information(self, 'Tips', 'Segmentation has been terminated.')
        except Exception:
            self.textEdit.append(traceback.format_exc())
            QMessageBox.warning(self, 'Warning!', 'Segmentation cancel fail!.')

    def resumeSegmentation(self):
        try:
            self.cthread.resume()
            self.runsegmentBtn.setEnabled(False)
            self.resumesegmentBtn.setEnabled(False)
            self.cancelsegmentBtn.setEnabled(True)
            self.pausesegmentBtn.setEnabled(True)
            self.textEdit.append("Segment Restart!")
        except Exception:
            self.textEdit.append(traceback.format_exc())
            QMessageBox.warning(self, 'Warning!', 'Segment resume fail!.')

    def completeSegmentation(self, value):
        if value == 100:
            self.textEdit.append("Segment Complete!")
            self.runsegmentBtn.setEnabled(True)
            self.resumesegmentBtn.setEnabled(False)
            self.pausesegmentBtn.setEnabled(False)
            self.cancelsegmentBtn.setEnabled(False)

    def showsegmentbar(self, current, total):
        self.segmentBar.setValue(int((current + 1) * 100 / total))

    def segmentexc(self, text):
        try:
            self.cthread.cancel()
            self.runsegmentBtn.setEnabled(True)
            self.resumesegmentBtn.setEnabled(False)
            self.cancelsegmentBtn.setEnabled(False)
            self.pausesegmentBtn.setEnabled(False)
            self.textEdit.setText(text)
            self.segmentBar.setValue(0)
            QMessageBox.warning(self, 'Error!', 'Errors with Segmentation!!.')
        except:
            QMessageBox.warning(self, 'Warning!', 'Segment cancel fail!.')

    def Nucchange(self, state):
        if state == Qt.Checked:
            self.Nuc.setText("Use segmented Nucleus infomation")
            self.Nucinput = True
        else:
            self.Nuc.setText("Use h_maxima to calculate nucleus position")
            self.Nucinput = False


class CellSegmentThread(QThread):
    segmentbarSignal = pyqtSignal(int, int)
    segmentexcSignal = pyqtSignal(str)

    def __init__(self, config={}):
        super().__init__()

        self.project = config.get("project_folder")
        self.embryo = config.get("embryo_name")
        self.memb_files = config.get("memb_files")
        self.model = config.get("model_name")
        self.nuc_files = config.get("nuc_files")
        self.structure = config.get("structure")
        self.size = config.get("size")
        self.nuc_input = config.get("nuc_input")
        self.isCancel = False
        self.isPause = False
        self.cond = QWaitCondition()
        self.mutex = QMutex()

    def cancel(self):
        self.isCancel = True

    def pause(self):
        self.isPause = True

    def resume(self):
        self.isPause = False
        self.cond.wakeAll()

    def run(self):
        try:
            if self.nuc_input:
                self.cell_seg_with_nuc()
            else:
                self.cell_seg_without_nuc()

        except Exception:
            self.cancel()

    def cell_seg_with_nuc(self):
        self.memb_files.sort()
        self.nuc_files.sort()

        save_path = os.path.join(self.project, "SegStack", self.embryo, self.model, "SegCell")
        if not os.path.isdir(save_path):
            os.makedirs(save_path)

        with ThreadPoolExecutor(cpu_count() + 1) as t:
            for tp in range(0, len(self.memb_files)):
                self.mutex.lock()
                if self.isPause:
                    self.cond.wait(self.mutex)
                if self.isCancel:
                    break
                configs = (self.memb_files, self.nuc_files, save_path, tp, self.structure, self.size)
                exception = t.submit(instance_segmentation_with_nucleus, configs).result()
                self.segmentbarSignal.emit(tp, len(self.memb_files))
                if exception:
                    self.segmentexcSignal.emit(exception)
                self.mutex.unlock()

    def cell_seg_without_nuc(self):
        self.memb_files.sort()
        save_path = os.path.join(self.project, "SegStack", self.embryo, self.model, "SegCell")
        if not os.path.isdir(save_path):
            os.makedirs(save_path)

        with ThreadPoolExecutor(cpu_count() + 1) as t:
            for tp in range(0, len(self.memb_files)):
                self.mutex.lock()
                if self.isPause:
                    self.cond.wait(self.mutex)
                if self.isCancel:
                    break
                configs = (self.memb_files, save_path, tp, self.structure, self.size)
                exception = t.submit(instance_segmentation_without_nucleus, configs).result()
                self.segmentbarSignal.emit(tp, len(self.memb_files))
                if exception:
                    self.segmentexcSignal.emit(exception)
                self.mutex.unlock()


#if __name__ == '__main__':
    #app = QApplication(sys.argv)
    #ex = Cell_Segmentation()
    #sys.exit(app.exec_())
