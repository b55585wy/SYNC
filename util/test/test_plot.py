import gc
import os, serial
from serial.tools import list_ports as lp
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLineEdit
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import numpy as np
import pyqtgraph as pg
import sys
import time
from scipy import signal
import neurokit2 as nk
import pandas as pd


# channel num
num_imu_channel = 6
psf_channel = 1

# sample rate
imu_sr = 100
psf_sr = 100

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-time Monitor")
        self.setGeometry(100, 100, 2048, 1000)

        layout = QVBoxLayout()
        self.pg_layout = pg.GraphicsLayoutWidget()
        layout.addWidget(self.pg_layout)

        self.input_field = QLineEdit()
        layout.addWidget(self.input_field)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_data)
        layout.addWidget(self.send_button)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.setup_data_stores()
        self.setup_plots()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())