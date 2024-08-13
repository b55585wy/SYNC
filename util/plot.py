import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QSlider, QProgressBar, QHBoxLayout, QCheckBox
)
from PyQt5.QtCore import QTimer, Qt
import pyqtgraph as pg
from pyqtgraph import PlotWidget
import asyncio
from bleak import BleakClient
import threading

class SignalPlotter(QWidget):
    def __init__(self, raw_data_queue, rsp_data_queue, max_points=500):
        super().__init__()
        self.queue = raw_data_queue
        self.data = []
        self.max_points = max_points

        self.rsp_analysis_outcome = rsp_data_queue

        # Initialize PyQt UI
        self.init_ui()

        # Timer to update plot
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(50)  # Update every 50 ms

        # Initialize the loop and thread
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.start_asyncio_loop, args=(self.loop,), daemon=True)
        self.thread.start()

    def start_asyncio_loop(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def init_ui(self):
        # Create a vertical layout
        layout = QVBoxLayout()

        # Create the PlotWidget for signal plotting
        self.plot_widget = PlotWidget()
        self.plot_widget.setYRange(-500, 1500)
        self.plot_widget.setXRange(0, self.max_points)
        self.curve = self.plot_widget.plot(pen=pg.mkPen(color='b', width=2))

        # Add plot widget to layout
        layout.addWidget(self.plot_widget)

        # Respiration rate label
        self.rate_label = QLabel("Respiration Rate: N/A")
        self.rate_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.rate_label)

        # IMU data label
        self.imu_label = QLabel("IMU Data: N/A")
        self.imu_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.imu_label)

        # Angular acceleration label
        self.angular_acc_label = QLabel("Angular Acceleration: N/A")
        self.angular_acc_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.angular_acc_label)

        # Heart rate label
        self.heart_rate_label = QLabel("Heart Rate: N/A")
        self.heart_rate_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.heart_rate_label)

        # Create a horizontal layout for the Bluetooth switch, manual/auto switch, and force adjustment slider
        h_layout = QHBoxLayout()

        # Bluetooth switch button
        self.bluetooth_button = QPushButton("Bluetooth: OFF")
        self.bluetooth_button.setCheckable(True)
        self.bluetooth_button.clicked.connect(self.toggle_bluetooth)
        h_layout.addWidget(self.bluetooth_button)

        # Manual/Auto switch (CheckBox)
        self.manual_auto_switch = QCheckBox("Manual Force Adjustment")
        self.manual_auto_switch.stateChanged.connect(self.toggle_manual_auto)
        h_layout.addWidget(self.manual_auto_switch)

        # Force adjustment slider (10 levels)
        self.force_slider = QSlider(Qt.Horizontal)
        self.force_slider.setMinimum(1)
        self.force_slider.setMaximum(10)
        self.force_slider.setValue(5)
        self.force_slider.setTickInterval(1)
        self.force_slider.setTickPosition(QSlider.TicksBelow)
        self.force_slider.setToolTip("Adjust Force (1-10)")
        self.force_slider.setVisible(False)  # Initially hidden until manual mode is selected
        h_layout.addWidget(self.force_slider)

        # Add the horizontal layout to the main layout
        layout.addLayout(h_layout)

        # Bluetooth device selection checkboxes
        self.heart_rate_check = QCheckBox("Connect to Heart Rate Band")
        self.respiration_band_check = QCheckBox("Connect to Respiration Band")
        self.heart_rate_check.setVisible(False)
        self.respiration_band_check.setVisible(False)
        layout.addWidget(self.heart_rate_check)
        layout.addWidget(self.respiration_band_check)

        # Connect the checkboxes to their respective handlers
        self.heart_rate_check.stateChanged.connect(self.connect_heart_rate_band)
        self.respiration_band_check.stateChanged.connect(self.connect_respiration_band)

        # Progress bars for respiration strength, emotional stress, and disharmony
        self.respiration_strength_bar = QProgressBar()
        self.emotional_stress_bar = QProgressBar()
        self.disharmony_bar = QProgressBar()

        for bar in [self.respiration_strength_bar, self.emotional_stress_bar, self.disharmony_bar]:
            bar.setMinimum(0)
            bar.setMaximum(100)
            bar.setValue(50)  # Default value
            bar.setStyleSheet("QProgressBar::chunk { background-color: blue; }")

        layout.addWidget(QLabel("Respiration Strength:"))
        layout.addWidget(self.respiration_strength_bar)
        layout.addWidget(QLabel("Emotional Stress:"))
        layout.addWidget(self.emotional_stress_bar)
        layout.addWidget(QLabel("Disharmony:"))
        layout.addWidget(self.disharmony_bar)

        # Add bottom switches for Dimension Measurement and Massage Air Valve
        bottom_layout = QHBoxLayout()
        self.dimension_measurement_switch = QPushButton("Dimension Measurement: OFF")
        self.dimension_measurement_switch.setCheckable(True)
        self.dimension_measurement_switch.clicked.connect(self.toggle_dimension_measurement)
        bottom_layout.addWidget(self.dimension_measurement_switch)

        self.massage_air_valve_switch = QPushButton("Massage Air Valve: OFF")
        self.massage_air_valve_switch.setCheckable(True)
        self.massage_air_valve_switch.clicked.connect(self.toggle_massage_air_valve)
        bottom_layout.addWidget(self.massage_air_valve_switch)

        layout.addLayout(bottom_layout)

        # Set window layout
        self.setLayout(layout)
        self.setWindowTitle('SYNC')

    def toggle_bluetooth(self):
        if self.bluetooth_button.isChecked():
            self.bluetooth_button.setText("Bluetooth: ON")
            self.heart_rate_check.setVisible(True)
            self.respiration_band_check.setVisible(True)
        else:
            self.bluetooth_button.setText("Bluetooth: OFF")
            self.heart_rate_check.setVisible(False)
            self.respiration_band_check.setVisible(False)

    def toggle_manual_auto(self, state):
        if state == Qt.Checked:
            self.force_slider.setVisible(True)  # Show slider if manual mode is selected
        else:
            self.force_slider.setVisible(False)  # Hide slider if auto mode is selected

    def toggle_dimension_measurement(self):
        if self.dimension_measurement_switch.isChecked():
            self.dimension_measurement_switch.setText("Dimension Measurement: ON")
        else:
            self.dimension_measurement_switch.setText("Dimension Measurement: OFF")

    def toggle_massage_air_valve(self):
        if self.massage_air_valve_switch.isChecked():
            self.massage_air_valve_switch.setText("Massage Air Valve: ON")
        else:
            self.massage_air_valve_switch.setText("Massage Air Valve: OFF")

    async def connect_device(self, address, uuid, notification_handler):
        async with BleakClient(address) as client:
            await client.start_notify(uuid, notification_handler)
            await asyncio.sleep(600)  # Subscribe for 600 seconds
            await client.stop_notify(uuid)

    def connect_heart_rate_band(self, state):
        if state == Qt.Checked:
            heart_rate_address = "D0:A4:69:B6:8F:A2"  # Replace with the actual MAC address
            heart_rate_uuid = "00002a37-0000-1000-8000-00805f9b34fb"
            asyncio.run_coroutine_threadsafe(
                self.connect_device(heart_rate_address, heart_rate_uuid, self.heart_rate_notification_handler),
                self.loop
            )

    def connect_respiration_band(self, state):
        if state == Qt.Checked:
            respiration_address = "XX:XX:XX:XX:XX:XX"  # Replace with the actual MAC address
            respiration_uuid = "00002a38-0000-1000-8000-00805f9b34fb"  # Replace with the actual UUID
            asyncio.run_coroutine_threadsafe(
                self.connect_device(respiration_address, respiration_uuid, self.respiration_notification_handler),
                self.loop
            )

    def heart_rate_notification_handler(self, sender, data):
        heart_rate = data[1]
        self.heart_rate_label.setText(f"Heart Rate: {heart_rate} BPM")
        print(f"Heart Rate: {heart_rate} BPM")

    def respiration_notification_handler(self, sender, data):
        # Handle respiration data here
        print(f"Respiration Data: {data}")

    def update_plot(self):
        while not self.queue.empty():
            data_point = self.queue.get()

            if 'filtered_data' in data_point:
                self.data.append(data_point['filtered_data'])
                if len(self.data) > self.max_points:
                    self.data.pop(0)
                self.curve.setData(self.data)

            if not self.rsp_analysis_outcome.empty():
                if not self.rsp_analysis_outcome.empty():
                    rsp_signals, _ = self.rsp_analysis_outcome.get()

                    # Extract and display the latest respiration rate
                    respiration_rate = rsp_signals["RSP_Rate"].iloc[-1]  # Get the last value
                    self.rate_label.setText(f"Respiration Rate: {respiration_rate:.2f} breaths/min")
                else:
                    self.rate_label.setText("Respiration Rate: N/A")

            if 'IMU_Data' in data_point:
                imu_data = data_point['IMU_Data']
                self.imu_label.setText(f"IMU Data: {imu_data}")

            if 'Angular_Acceleration' in data_point:
                angular_acc = data_point['Angular_Acceleration']
                self.angular_acc_label.setText(f"Angular Acceleration: {angular_acc}")

            if 'Heart_Rate' in data_point:
                heart_rate = data_point['Heart_Rate']
                if heart_rate is not None:
                    self.heart_rate_label.setText(f"Heart Rate: {heart_rate} BPM")
                else:
                    self.heart_rate_label.setText("Heart Rate: N/A")

            if 'Respiration_Strength' in data_point:
                strength = data_point['Respiration_Strength']
                self.respiration_strength_bar.setValue(strength)
                self.update_bar_color(self.respiration_strength_bar, strength)

            if 'Emotional_Stress' in data_point:
                stress = data_point['Emotional_Stress']
                self.emotional_stress_bar.setValue(stress)
                self.update_bar_color(self.emotional_stress_bar, stress)

            if 'Disharmony' in data_point:
                disharmony = data_point['Disharmony']
                self.disharmony_bar.setValue(disharmony)
                self.update_bar_color(self.disharmony_bar, disharmony)

    def update_bar_color(self, bar, value):
        # Change the color from blue to red based on value
        r = int((value / 100) * 255)
        g = 0
        b = 255 - r
        bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: rgb({r},{g},{b}); }}")

    def start_plotting(self):
        self.show()

def start_signal_plotter(raw_data_queue, rsp_data_queue):
    try:
        app = QApplication(sys.argv)
        plotter = SignalPlotter(raw_data_queue, rsp_data_queue)

        # Start the GUI event loop
        plotter.start_plotting()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error in start_signal_plotter: {e}")
