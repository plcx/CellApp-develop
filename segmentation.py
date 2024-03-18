import sys
from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit,
                             QTextEdit, QGridLayout, QApplication, QPushButton, QFileDialog, QMessageBox,
                             QComboBox, QVBoxLayout, QProgressBar, QHBoxLayout, QTabWidget)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from membrane_seg import Memb_Segmentation
from nucleus_seg import Nucleus_Segmentation
from cell_seg import Cell_Segmentation
import os

class Segmentation(QWidget):
    def __init__(self):
        super().__init__()
        self.mainlayout = QGridLayout()
        self.subfunctionbar = QTabWidget()
        self.subfunctionbar.setLayoutDirection(Qt.LeftToRight)
        self.subfunctionbar.setTabBarAutoHide(False)
        self.membsegment = Memb_Segmentation()
        self.nucsegment = Nucleus_Segmentation()
        self.cellsegment = Cell_Segmentation()
        self.subfunctionbar.addTab(self.membsegment, "Membrane")
        self.subfunctionbar.addTab(self.nucsegment, "Nucleus")
        self.subfunctionbar.addTab(self.cellsegment, "Cell")
        self.subfunctionbar.setCurrentIndex(0)
        self.subfunctionbar.currentChanged.connect(self.updateBlankInfo)
        self.mainlayout.addWidget(self.subfunctionbar, 1, 0, 1, 1)
        self.setLayout(self.mainlayout)
        self.setGeometry(300, 300, 450, 500)
        self.show()

    def updateBlankInfo(self):
        if self.subfunctionbar.currentIndex() == 1: #当按钮点到 nucleus segmentation
            if self.membsegment.projectFolderEdit.text():
                self.nucsegment.projectFolderEdit.setText(self.membsegment.projectFolderEdit.text())
                self.nucsegment.embryoNameEdit.clear()
                if os.path.isdir(os.path.join(self.membsegment.projectFolderEdit.text(), "SegStack")):
                    listdir = [x for x in os.listdir(os.path.join(self.membsegment.projectFolderEdit.text(), "SegStack")) if not x.startswith(".")]
                    listdir.sort()
                    self.nucsegment.embryoNameEdit.addItems(listdir)
                else:
                    os.makedirs(os.path.join(self.membsegment.projectFolderEdit.text(), "SegStack"))

        elif self.subfunctionbar.currentIndex() == 2:
            if self.membsegment.projectFolderEdit.text():
                self.cellsegment.projectFolderEdit.setText(self.membsegment.projectFolderEdit.text())
                self.cellsegment.embryoNameEdit.clear()
                if os.path.isdir(os.path.join(self.membsegment.projectFolderEdit.text(), "SegStack")):
                    listdir = [x for x in os.listdir(os.path.join(self.membsegment.projectFolderEdit.text(), "SegStack")) if not x.startswith(".")]
                    listdir.sort()
                    self.cellsegment.embryoNameEdit.addItems(listdir)
                else:
                    os.makedirs(os.path.join(self.membsegment.projectFolderEdit.text(), "SegStack"))


