import sys
from glob import glob

from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit,
                             QTextEdit, QGridLayout, QApplication, QPushButton, QFileDialog, QMessageBox,
                             QComboBox, QVBoxLayout, QProgressBar, QHBoxLayout, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QMutex, QWaitCondition
import traceback
import os
from Utils.cell_morphological import cell_morphological_analysis
from Utils.cell_gui_data import cell_gui_data
class Gui_generator(QWidget):
    def __init__(self):
        super().__init__()
        self.output_path = os.path.join(os.getcwd(), 'GUI_output')
        self.mainlayout = QVBoxLayout()  # 组件的整体布局是垂直布局,第一层是一个栅格放参数,第二层是个水平布局放进度条, 最下层是一个反馈信息栏
        self.initUI()  # 设置参数相关的各种组件位置
        self.middlelayout = QGridLayout()
        self.runsegmentBtn = QPushButton("Run Segmentation")
        self.runsegmentBtn.clicked.connect(self.runSegmentation)
        self.cancelsegmentBtn = QPushButton("Cancel Segmentation")
        self.cancelsegmentBtn.setEnabled(False)
        self.cancelsegmentBtn.clicked.connect(self.cancelSegmentation)
        self.pausesegmentBtn = QPushButton("Pause Segmentation")
        self.cancelsegmentBtn.setEnabled(False)
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
        # 栅格布局第一列是参数名称
        projectFolder = QLabel('Project Folder')
        embryoName = QLabel('Embryo Name')
        modelName = QLabel('Model Name')
        # 栅格布局第二列是参数输入框
        self.projectFolderEdit = QLineEdit()
        self.embryoNameEdit = QComboBox()
        self.modelNameEdit = QComboBox()
        self.embryoNameEdit.activated[str].connect(self.Autofillmodel)
        # 栅格布局第三列是参数选择按钮
        projectFolderBtn = QPushButton("Select")
        projectFolderBtn.clicked.connect(self.chooseProjectFolder)
        self.sliceNumEdit = QLineEdit()
        self.xyLengthEdit = QLineEdit()
        self.zLengthEdit = QLineEdit()
        grid = QGridLayout()
        grid.setSpacing(30)
        grid.addWidget(projectFolder, 1, 0)
        grid.addWidget(self.projectFolderEdit, 1, 1)
        grid.addWidget(projectFolderBtn, 1, 2)
        grid.addWidget(embryoName, 2, 0)
        grid.addWidget(self.embryoNameEdit, 2, 1)
        grid.addWidget(modelName, 3, 0)
        grid.addWidget(self.modelNameEdit, 3, 1)
        self.mainlayout.addLayout(grid)

    def chooseProjectFolder(self):
        dirName = QFileDialog.getExistingDirectory(self, 'Choose RawStack Folder', './')
        try:
            self.textEdit.clear()
            self.embryoNameEdit.clear()
            self.edit = self.projectFolderEdit
            self.edit.setText(dirName)
            if dirName:
                listdir = [x for x in os.listdir(os.path.join(dirName, "RawStack")) if not x.startswith(".")]
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
        para = {}
        try:
            para["project_dir"] = self.projectFolderEdit.text()
            para['embryo_dir'] = self.embryoNameEdit.currentText()
            para['model_name'] = self.modelNameEdit.currentText()
            para['output_path'] = self.output_path + '_' + self.embryoNameEdit.currentText()+ '_' +self.modelNameEdit.currentText()
            self.sthread = SegmentThread(para)

        except:
            para.clear()
            self.textEdit.setText(traceback.format_exc())
            QMessageBox.warning(self, 'Error!', 'Initialization Failure!')

        if para:
            try:
                self.textEdit.clear()
                self.textEdit.append("Running Segmentation!")
                self.textEdit.append(f"The embryo name is {para.get('embryo_dir')}")
                self.textEdit.append(f"The model name is {self.modelNameEdit.currentText()}")
                self.textEdit.append(f"GUI output path is {self.output_path + '_' + self.embryoNameEdit.currentText()+ '_' +self.modelNameEdit.currentText()}")
                self.runsegmentBtn.setEnabled(False)
                self.resumesegmentBtn.setEnabled(False)
                self.cancelsegmentBtn.setEnabled(False)
                self.pausesegmentBtn.setEnabled(False)
                self.segmentBar.reset()
                self.sthread.segmentbarSignal.connect(self.showsegmentbar)
                self.sthread.segmentexcSignal.connect(self.segmentexc)
                self.sthread.start()

            except:
                self.textEdit.append(traceback.format_exc())
                QMessageBox.warning(self, 'Error!', 'Can not start Segmentation!')

    def cancelSegmentation(self):
        try:
            self.sthread.cancel()
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

    def pauseSegmentation(self):
        try:
            self.sthread.pause()
            self.runsegmentBtn.setEnabled(False)
            self.resumesegmentBtn.setEnabled(False)
            self.cancelsegmentBtn.setEnabled(False)
            self.pausesegmentBtn.setEnabled(False)
            self.textEdit.append("Segment Suspend!")
        except Exception:
            self.textEdit.append(traceback.format_exc())
            QMessageBox.warning(self, 'Warning!', 'Segment pause fail!.')

    def resumeSegmentation(self):
        try:
            self.sthread.resume()
            self.runsegmentBtn.setEnabled(False)
            self.resumesegmentBtn.setEnabled(False)
            self.cancelsegmentBtn.setEnabled(False)
            self.pausesegmentBtn.setEnabled(False)
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
        self.segmentBar.setValue(int(current * 100 / total))

    def segmentexc(self, text):
        try:
            self.sthread.cancel()
            self.runsegmentBtn.setEnabled(True)
            self.resumesegmentBtn.setEnabled(False)
            self.cancelsegmentBtn.setEnabled(False)
            self.pausesegmentBtn.setEnabled(False)
            self.textEdit.setText(text)
            self.segmentBar.setValue(0)
            QMessageBox.warning(self, 'Error!', 'Errors with Segmentation!!.')
        except:
            QMessageBox.warning(self, 'Warning!', 'Segment cancel fail!.')

class SegmentThread(QThread):
    segmentbarSignal = pyqtSignal(int, int)
    segmentexcSignal = pyqtSignal(str)


    def __init__(self, para={}):
        super().__init__()
        #project_dir, embryo_dir, flag
        self.project = para.get("project_dir")
        self.embryo = para.get("embryo_dir")
        self.model_name = para.get("model_name")
        self.output_path = para.get("output_path")
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
            namedict_dir = os.path.join(self.project, 'name_dictionary.csv')
            cell_unified_dir = os.path.join(self.project, 'SegStack', self.embryo, self.model_name, 'SegCellUnified')
            cell_fate = os.path.join(self.project, 'CellFate.xls')
            cd_files_dir = os.path.join(self.project, 'CDfiles')
            cd_files = sorted(glob(os.path.join(cd_files_dir, "*.csv")))
            cdfile_embryo = os.path.join(self.project, 'CDfiles', self.embryo + '.csv')
            if len(cd_files) == 0:
                self.segmentexcSignal.emit('Please load CDfile folder')
                return
            if not os.path.exists(cdfile_embryo):
                self.segmentexcSignal.emit('Please load CDfile of'+self.embryo + '.csv')
                return
            if not os.path.exists(namedict_dir):
                self.segmentexcSignal.emit('Please load name_dictionary.csv or Run cell matching.')
                return
            if not os.path.exists(cell_unified_dir):
                self.segmentexcSignal.emit('Please run cell matching.')
                return
            if not os.path.exists(cell_fate):
                self.segmentexcSignal.emit('Please load CellFate.xls')
                return
            self.segmentbarSignal.emit(1, 10)
            cell_morphological_analysis(self.project, self.embryo, self.model_name, self.output_path)
            self.segmentbarSignal.emit(2, 10)
            cell_gui_data(self.project, self.embryo, self.model_name, self.output_path)
            self.segmentbarSignal.emit(10, 10)
        except Exception:
            self.cancel()

