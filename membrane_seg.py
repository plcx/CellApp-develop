import sys
from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit,
                             QTextEdit, QGridLayout, QApplication, QPushButton, QFileDialog, QMessageBox,
                             QComboBox, QVBoxLayout, QProgressBar, QHBoxLayout, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QMutex, QWaitCondition
import traceback
import os
from Utils.parser import read_yaml_to_dict, parse_tuple
from Utils import dataset
from torch.utils.data import DataLoader
import networks
import torch
import random
import numpy as np
import ast
from skimage.transform import resize
import nibabel as nib
import collections
from Utils.segment_lib import segmentation
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Pool, cpu_count
import numpy as np
from stardist import fill_label_holes, random_label_cmap, calculate_extents, gputools_available
np.random.seed(42)
lbl_cmap = random_label_cmap()




class Memb_Segmentation(QWidget):

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
        deviceName = QLabel('Device Name')
        Nuc = QLabel("Nucleus")
        # 栅格布局第二列是参数输入框
        self.projectFolderEdit = QLineEdit()
        #self.projectFolderEdit.setText(project_base_path)
        self.modelNameEdit = QComboBox()
        self.modelNameEdit.addItems(["TUNETr", "SwinUNETR", "VNet"])
        self.selected_device = "cpu"
        self.deviceNameEdit = QComboBox()
        self.deviceList = ["cpu"]
        if torch.cuda.is_available():
            num_gpus = torch.cuda.device_count()
            for i in range(num_gpus):
                self.deviceList.append('cuda:'+str(i))
        self.deviceNameEdit.addItems(self.deviceList)
        # 栅格布局第三列是参数选择按钮
        projectFolderBtn = QPushButton("Select")
        projectFolderBtn.clicked.connect(self.chooseProjectFolder)
        self.embryoNameBtn = QComboBox()

        grid = QGridLayout()
        grid.setSpacing(30)

        grid.addWidget(projectFolder, 1, 0)
        grid.addWidget(self.projectFolderEdit, 1, 1)
        grid.addWidget(projectFolderBtn, 1, 2)

        grid.addWidget(embryoName, 2, 0)
        grid.addWidget(self.embryoNameBtn, 2, 1)

        grid.addWidget(modelName, 3, 0)
        grid.addWidget(self.modelNameEdit, 3, 1)

        grid.addWidget(deviceName, 4, 0)
        grid.addWidget(self.deviceNameEdit, 4, 1)


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

    def runSegmentation(self):
        para = {}
        try:
            para = read_yaml_to_dict(os.path.join("./static/configs", self.modelNameEdit.currentText() + ".yaml"))
            self.selected_device = self.deviceNameEdit.currentText()
            if self.selected_device == 'cpu':
                para['GPU'] = False
            else:
                para['GPU'] = True
            para["project_folder"] = self.projectFolderEdit.text()
            para['embryo_name'] = self.embryoNameBtn.currentText()
            para['model_name'] = self.modelNameEdit.currentText()
            para['device_name'] = self.selected_device
            self.sthread = SegmentThread(para)


        except:
            para.clear()
            self.textEdit.setText(traceback.format_exc())
            QMessageBox.warning(self, 'Error!', 'Initialization Failure!')

        if para:
            try:
                self.textEdit.clear()
                self.textEdit.append("Running Segmentation!")
                self.textEdit.append(f"The embryo name is {self.embryoNameBtn.currentText()}")
                self.textEdit.append(f"The model name is {self.modelNameEdit.currentText()}")
                self.textEdit.append(f"The network parameters are {para.get('net_params')}")
                self.textEdit.append(f"The dataset name is {para.get('dataset_name')}")
                self.textEdit.append(f"Device name : {self.selected_device}")
                self.runsegmentBtn.setEnabled(False)
                self.resumesegmentBtn.setEnabled(False)
                self.cancelsegmentBtn.setEnabled(True)
                self.pausesegmentBtn.setEnabled(True)
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




class SegmentThread(QThread):
    segmentbarSignal = pyqtSignal(int, int)
    segmentexcSignal = pyqtSignal(str)

    def __init__(self, para={}):
        super().__init__()

        self.project = para.get("project_folder")
        self.embryo = para.get("embryo_name")
        self.model_name = para.get("model_name")
        self.device_name = para.get("device_name")
        self.gpu = para.get('GPU')

        self.isCancel = False
        self.isPause = False
        self.cond = QWaitCondition()
        self.mutex = QMutex()

        np.random.seed(para.get("seed"))
        random.seed(para.get("seed"))
        torch.manual_seed(para.get("seed"))
        torch.cuda.manual_seed(para.get("seed"))

        Network = getattr(networks, para.get("net"))
        net_params = para.get("net_params")
        if para.get("net") == "SwinUNETR":
            img_size = net_params.get("img_size")
            img_size = parse_tuple(img_size)
            net_params["img_size"] = img_size
        model = Network(**net_params)

        Dataset = getattr(dataset, para.get("dataset_name"))
        memb_dataset = Dataset(
            root=self.project,
            embryoname=self.embryo,
            is_input_nuc=True,
            transforms=para.get("transforms")
        )
        self.memb_loader = DataLoader(
            dataset=memb_dataset,
            batch_size=1,
            shuffle=False,
        )

        if self.gpu:
            assert torch.cuda.is_available()
        self.device = torch.device(self.device_name)
        self.model = model.to(self.device)
        check_point = torch.load(para.get("trained_model"), map_location=self.device_name)
        state = check_point.get("state_dict")
        new_state = collections.OrderedDict([(key[7:], value) for key, value in state.items()])
        self.model.load_state_dict(new_state)


    def cancel(self):
        self.isCancel = True

    def pause(self):
        self.isPause = True

    def resume(self):
        self.isPause = False
        self.cond.wakeAll()

    def run(self):
        try:
            if self.gpu:
                self.run_with_gpu()
            else:
                self.run_without_gpu()

        except Exception:
            self.cancel()

    def run_with_gpu(self):
        with torch.no_grad():
            self.model.eval()
            for i, data in enumerate(self.memb_loader):
                self.mutex.lock()
                if self.isPause:
                    self.cond.wait(self.mutex)
                if self.isCancel:
                    break
                try:
                    raw_memb = data[0]
                    raw_memb_shape = data[1]
                    embryo_name_tp = data[2][0]
                    raw_memb_shape = (raw_memb_shape[0].item(), raw_memb_shape[1].item(), raw_memb_shape[2].item())
                    pred_memb = self.model(raw_memb.to(self.device))
                    pred_memb = pred_memb[0] if len(pred_memb) > 1 else pred_memb

                    pred_memb = pred_memb[0, 0, :, :, :]
                    pred_memb = pred_memb.cpu().numpy().transpose([1, 2, 0])
                    pred_memb = resize(pred_memb,
                                       raw_memb_shape,
                                       mode='constant',
                                       cval=0,
                                       order=1,
                                       anti_aliasing=True)

                    save_path = os.path.join(self.project, "SegStack", self.embryo, self.model_name, "SegMemb")
                    if not os.path.isdir(save_path):
                        os.makedirs(save_path)
                    save_name = os.path.join(save_path, embryo_name_tp + "_segMemb.nii.gz")
                    nib_stack = nib.Nifti1Image((pred_memb * 256).astype(np.int16), np.eye(4))
                    nib.save(nib_stack, save_name)
                except Exception as e:
                    self.segmentexcSignal.emit(e)

                self.segmentbarSignal.emit(i + 1, len(self.memb_loader))
                self.mutex.unlock()

    def run_without_gpu(self):
        save_path = os.path.join(self.project, "SegStack", self.embryo, self.model_name, "SegMemb")
        if not os.path.isdir(save_path):
            os.makedirs(save_path)

        with ThreadPoolExecutor(cpu_count() + 1) as t:
            for i, data in enumerate(self.memb_loader):
                self.mutex.lock()
                if self.isPause:
                    self.cond.wait(self.mutex)
                if self.isCancel:
                    break
                configs = (data, self.model, self.device, save_path)
                exception = t.submit(segmentation, configs).result()
                if exception:
                    self.segmentexcSignal.emit(exception)
                    self.cancel()
                self.segmentbarSignal.emit(i + 1, len(self.memb_loader))
                self.mutex.unlock()

