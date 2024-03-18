import sys
from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit,
                             QTextEdit, QGridLayout, QApplication, QPushButton, QFileDialog, QMessageBox,
                             QComboBox, QVBoxLayout, QProgressBar, QHBoxLayout, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QMutex, QWaitCondition
import traceback
import os
import nibabel as nib
from Utils.nuc_preprocess import nifti2tiff
# Other imports and code follow here
import sys
import numpy as np
from glob import glob
from tqdm import tqdm
from tifffile import imread
from csbdeep.utils import Path, normalize
from stardist import fill_label_holes, random_label_cmap, calculate_extents, gputools_available
from stardist import Rays_GoldenSpiral
from stardist.matching import matching, matching_dataset
from stardist.models import Config3D, StarDist3D, StarDistData3D
np.random.seed(42)
lbl_cmap = random_label_cmap()




class Nucleus_Segmentation(QWidget):

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

        self.projectFolderEdit = QLineEdit()
        self.embryoNameEdit = QComboBox()
        self.embryoNameEdit.activated[str].connect(self.Autofillmodel)
        self.modelNameEdit = QComboBox()
        projectFolderBtn = QPushButton("Select")
        projectFolderBtn.clicked.connect(self.chooseProjectFolder)

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
        para = {}
        try:
            para["project_dir"] = self.projectFolderEdit.text()
            para['embryo_dir'] = self.embryoNameEdit.currentText()
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
        self.isCancel = False
        self.isPause = False
        self.cond = QWaitCondition()
        self.mutex = QMutex()
        #Load model
        self.model = StarDist3D(None, name='stardist_nuc', basedir='static/models')



    def cancel(self):
        self.isCancel = True

    def pause(self):
        self.isPause = True

    def resume(self):
        self.isPause = False
        self.cond.wakeAll()

    def run(self):
        try:
            self.nuc_seg()

        except Exception:
            self.cancel()


    def nuc_seg(self):
        # Preprocessing
        input_dir = os.path.join(self.project, 'RawStack', self.embryo, 'RawNuc')
        if not os.path.exists(input_dir):
            self.segmentexcSignal.emit('Please preprocessing to generate RawNuc')
            return
        output_dir = os.path.join(self.project, 'RawStack', self.embryo, 'RawNucSd')
        pred_dir = os.path.join(self.project, 'SegStack', self.embryo, self.model_name, 'SegNuc')
        nifti2tiff(input_dir, output_dir, False)
        self.segmentbarSignal.emit(1, 10)

        # Stardist dataloader
        testset = sorted(glob(os.path.join(output_dir, '*.tif')))
        testset_copy = testset.copy()
        testset = list(map(imread, testset))
        self.segmentbarSignal.emit(2, 10)
        n_channel = 1 if testset[0].ndim == 3 else testset[0].shape[-1]
        axis_norm = (0, 1, 2)

        # Save prediction
        if not os.path.exists(pred_dir):
            os.makedirs(pred_dir)
        for i, path_this in enumerate(testset):
            if self.isPause:
                self.cond.wait(self.mutex)
            if self.isCancel:
                break
            try:
                img = normalize(path_this, 1, 99.8, axis=axis_norm)
                labels, details = self.model.predict_instances(img)
                # Assuming testset and testset_copy have the same order and length
                embryo_tp = os.path.basename(testset_copy[i]).split('.')[0]
                pred_seg = labels.transpose([1, 2, 0])
                binary_pred = np.where(pred_seg > 0, 255, pred_seg)
                nib.save(nib.Nifti1Image(binary_pred, np.eye(4)),
                         os.path.join(pred_dir, embryo_tp + '_predNuc.nii.gz'))
                self.segmentbarSignal.emit(i + 1, len(testset))
            except Exception as e:
                self.segmentexcSignal.emit(e)
                self.segmentbarSignal.emit(i + 1, len(testset))
                self.mutex.unlock()



