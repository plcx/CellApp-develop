import sys
from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit,
                             QTextEdit, QGridLayout, QApplication, QPushButton, QFileDialog, QMessageBox,
                             QComboBox, QVBoxLayout, QProgressBar, QHBoxLayout, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QMutex, QWaitCondition
import traceback
import os
from Utils.rendering_lib import render_and_export_obj


class Cell_rendering(QWidget):
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
        # 栅格布局第一列是参数名称
        projectFolder = QLabel('Project Folder')
        embryoName = QLabel('Embryo Name')
        modelName = QLabel('Model Name')
        # 栅格布局第二列是参数输入框
        self.projectFolderEdit = QLineEdit()
        self.modelNameEdit = QComboBox()
        # 栅格布局第三列是参数选择按钮
        projectFolderBtn = QPushButton("Select")
        projectFolderBtn.clicked.connect(self.chooseProjectFolder)
        self.embryoNameBtn = QComboBox()
        self.embryoNameBtn.activated[str].connect(self.Autofillmodel)
        grid = QGridLayout()
        grid.setSpacing(30)
        grid.addWidget(projectFolder, 1, 0)
        grid.addWidget(self.projectFolderEdit, 1, 1)
        grid.addWidget(projectFolderBtn, 1, 2)
        grid.addWidget(embryoName, 2, 0)
        grid.addWidget(self.embryoNameBtn, 2, 1)
        grid.addWidget(modelName, 3, 0)
        grid.addWidget(self.modelNameEdit, 3, 1)
        self.mainlayout.addLayout(grid)

    def chooseProjectFolder(self):
        dirName = QFileDialog.getExistingDirectory(self, 'Choose RawStack Folder', './')
        try:
            self.textEdit.clear()
            self.embryoNameBtn.clear()
            self.edit = self.projectFolderEdit
            self.edit.setText(dirName)
            if dirName:
                listdir = [x for x in os.listdir(os.path.join(dirName, "RawStack")) if not x.startswith(".")]
                listdir.sort()
                self.embryoNameBtn.addItems(listdir)
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
            para['embryo_dir'] = self.embryoNameBtn.currentText()
            para['model_name'] = self.modelNameEdit.currentText()
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
                self.runsegmentBtn.setEnabled(False)
                self.resumesegmentBtn.setEnabled(False)
                self.cancelsegmentBtn.setEnabled(True)
                self.pausesegmentBtn.setEnabled(True)
                self.segmentBar.reset()
                self.sthread.segmentbarSignal.connect(self.showsegmentbar)
                self.sthread.segmentexcSignal.connect(self.segmentexc)
                self.sthread.nuctexcSignal.connect(self.nuctexc)
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
            self.resumesegmentBtn.setEnabled(True)
            self.cancelsegmentBtn.setEnabled(True)
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

    def nuctexc(self, text):
        self.textEdit.setText(text)



class SegmentThread(QThread):
    segmentbarSignal = pyqtSignal(int, int)
    segmentexcSignal = pyqtSignal(str)
    nuctexcSignal = pyqtSignal(str)

    def __init__(self, para={}):
        super().__init__()
        #project_dir, embryo_dir, flag
        self.project = para.get("project_dir")
        self.embryo = para.get("embryo_dir")
        self.model_name = para.get("model_name")
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
            input_dir = os.path.join(self.project, 'SegStack', self.embryo, self.model_name, 'SegCell')
            output_dir = os.path.join(self.project, 'SegStack', self.embryo, self.model_name, 'CellRendering')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            files = os.listdir(input_dir)
            for i, file in enumerate(files):
                self.mutex.lock()
                if self.isPause:
                    self.cond.wait(self.mutex)
                if self.isCancel:
                    break

                input_file = os.path.join(input_dir, file)
                output_file = os.path.join(output_dir, file)
                render_and_export_obj(input_file, output_file)
                self.segmentbarSignal.emit(i + 1, len(files))

                self.mutex.unlock()

        except Exception:
            self.cancel()









