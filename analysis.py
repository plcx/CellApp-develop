import sys
from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit,
                             QTextEdit, QGridLayout, QApplication, QPushButton, QFileDialog, QMessageBox,
                             QComboBox, QVBoxLayout, QProgressBar, QHBoxLayout, QTabWidget)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from membrane_seg import Memb_Segmentation
from cell_matching import Cell_matching
from gui_generator import Gui_generator
import os

class Analysis(QWidget):
    def __init__(self):
        super().__init__()
        self.mainlayout = QGridLayout()
        self.subfunctionbar = QTabWidget()
        self.subfunctionbar.setLayoutDirection(Qt.LeftToRight)
        self.subfunctionbar.setTabBarAutoHide(False)

        self.cellmatching = Cell_matching()
        self.guigenerator = Gui_generator()
        self.subfunctionbar.addTab(self.cellmatching, "Matching")
        self.subfunctionbar.addTab(self.guigenerator, "GUI")
        self.subfunctionbar.setCurrentIndex(0)
        self.subfunctionbar.currentChanged.connect(self.updateBlankInfo)
        self.mainlayout.addWidget(self.subfunctionbar, 1, 0, 1, 1)
        self.setLayout(self.mainlayout)
        self.setGeometry(300, 300, 450, 500)
        self.show()

    def updateBlankInfo(self):
        if self.subfunctionbar.currentIndex() == 1:
            if self.cellmatching.projectFolderEdit.text():
                self.guigenerator.projectFolderEdit.setText(self.cellmatching.projectFolderEdit.text())
                self.guigenerator.embryoNameEdit.clear()
                if os.path.isdir(os.path.join(self.cellmatching.projectFolderEdit.text(), "SegStack")):
                    listdir = [x for x in os.listdir(os.path.join(self.cellmatching.projectFolderEdit.text(), "SegStack")) if not x.startswith(".")]
                    listdir.sort()
                    self.guigenerator.embryoNameEdit.addItems(listdir)
                else:
                    os.makedirs(os.path.join(self.cellmatching.projectFolderEdit.text(), "SegStack"))
        '''
        elif self.subfunctionbar.currentIndex() == 2:
            if self.cellmatching.projectFolderEdit.text():
                self.guigenerator.projectFolderEdit.setText(self.cellmatching.projectFolderEdit.text())
                self.guigenerator.embryoNameEdit.clear()
                if os.path.isdir(os.path.join(self.cellmatching.projectFolderEdit.text(), "SegStack")):
                    listdir = [x for x in os.listdir(os.path.join(self.cellmatching.projectFolderEdit.text(), "SegStack")) if not x.startswith(".")]
                    listdir.sort()
                    self.guigenerator.embryoNameEdit.addItems(listdir)
                else:
                    os.makedirs(os.path.join(self.cellmatching.projectFolderEdit.text(), "SegStack"))
        '''

