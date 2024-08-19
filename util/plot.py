import sys
from collections import deque

import numpy as np
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
        self.std_respiration_clean = None
        self.avg_respiration_clean = None
        self.std_respiration_rate = None
        self.avg_respiration_rate = None
        self.respiration_rates = []
        self.respiration_clean = []
        self.queue = raw_data_queue
        self.data = []
        self.max_points = max_points

        self.rsp_analysis_outcome = rsp_data_queue

        # Initialize a deque to store the last 500 filtered data points
        self.recent_filtered_values = deque(maxlen=500)

        # Other variables for tracking
        self.avg_filtered_value = None
        self.std_filtered_value = None
        self.recording_duration = 0
        self.sampling_interval = 50 / 1000  # 50 ms timer interval
        self.respiration_rate_previous = None
        self.harmony_updates = 0
        self.harmony_reminders = 0
        self.reach_max_and_min = 0

        # Timer for delayed update of respiration_rate_previous
        self.update_rate_timer = QTimer()
        self.update_rate_timer.setSingleShot(True)
        self.update_rate_timer.timeout.connect(self.update_previous_respiration_rate)

        # Timer for reminders every 10 seconds
        self.reminder_timer = QTimer()
        self.reminder_timer.timeout.connect(self.check_reminder)
        self.reminder_timer.start(10000)  # Trigger every 10 seconds

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
        layout = QVBoxLayout()

        # Create the PlotWidget for signal plotting
        self.plot_widget = PlotWidget()
        self.plot_widget.setYRange(-500, 1500)
        self.plot_widget.setXRange(0, self.max_points)
        self.curve = self.plot_widget.plot(pen=pg.mkPen(color='b', width=2))

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
        self.force_slider.setVisible(False)
        h_layout.addWidget(self.force_slider)

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

        # Progress bars for respiration strength, emotional stress, and harmony
        self.respiration_strength_bar = QProgressBar()
        self.emotional_stress_bar = QProgressBar()
        self.harmony_bar = QProgressBar()

        for bar in [self.respiration_strength_bar, self.emotional_stress_bar, self.harmony_bar]:
            bar.setMinimum(0)
            bar.setMaximum(100)
            bar.setValue(50)
            bar.setStyleSheet("QProgressBar::chunk { background-color: blue; }")

        layout.addWidget(QLabel("Respiration Strength:"))
        layout.addWidget(self.respiration_strength_bar)
        layout.addWidget(QLabel("Emotional Stress:"))
        layout.addWidget(self.emotional_stress_bar)
        layout.addWidget(QLabel("Harmony:"))
        layout.addWidget(self.harmony_bar)

        # Reminder label
        self.reminder_label = QLabel("")
        self.reminder_label.setStyleSheet("font-size: 16px; color: red;")
        layout.addWidget(self.reminder_label)

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
            self.force_slider.setVisible(True)
        else:
            self.force_slider.setVisible(False)

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
            await asyncio.sleep(600)
            await client.stop_notify(uuid)

    def connect_heart_rate_band(self, state):
        if state == Qt.Checked:
            heart_rate_address = "D0:A4:69:B6:8F:A2"
            heart_rate_uuid = "00002a37-0000-1000-8000-00805f9b34fb"
            asyncio.run_coroutine_threadsafe(
                self.connect_device(heart_rate_address, heart_rate_uuid, self.heart_rate_notification_handler),
                self.loop
            )

    def connect_respiration_band(self, state):
        if state == Qt.Checked:
            respiration_address = "f0:f5:bd:b5:6a:f6"
            respiration_uuid = "FF01"
            asyncio.run_coroutine_threadsafe(
                self.connect_device(respiration_address, respiration_uuid, self.respiration_notification_handler),
                self.loop
            )

    def heart_rate_notification_handler(self, sender, data):
        heart_rate = data[1]
        self.heart_rate_label.setText(f"Heart Rate: {heart_rate} BPM")
        print(f"Heart Rate: {heart_rate} BPM")

    def respiration_notification_handler(self, sender, data):
        if len(data) > 1:
            length = data[0]
            if len(data) >= length + 1:
                imu_data = data[1:length + 1]
                x_acc = int.from_bytes(imu_data, byteorder='little', signed=False)
                print(f"IMU X-Axis Data: {x_acc}")
            else:
                print(f"Received incomplete data: {data}")
        else:
            print(f"Received invalid data: {data}")

    def update_plot(self):
        while not self.queue.empty():
            data_point = self.queue.get()

            if 'filtered_data' in data_point:
                self.data.append(data_point['filtered_data'])
                if len(self.data) > self.max_points:
                    self.data.pop(0)
                self.curve.setData(self.data)

                filtered_value = data_point['filtered_data']
                self.recent_filtered_values.append(filtered_value)

                if len(self.recent_filtered_values) == self.recent_filtered_values.maxlen:
                    self.avg_filtered_value = np.mean(self.recent_filtered_values)
                    self.std_filtered_value = np.std(self.recent_filtered_values)

                if not self.rsp_analysis_outcome.empty():
                    rsp_signals, _ = self.rsp_analysis_outcome.get()
                    if self.recording_duration < 0.2:
                        self.respiration_rates.append(rsp_signals["RSP_Rate"].iloc[-1])
                        self.respiration_clean.append(rsp_signals["RSP_Clean"].iloc[-1])
                        self.recording_duration += self.sampling_interval

                    elif self.recording_duration >= 0.2:
                        self.avg_respiration_rate = np.mean(self.respiration_rates)
                        self.std_respiration_rate = np.std(self.respiration_rates)
                        self.avg_respiration_clean = np.mean(self.respiration_clean)
                        self.std_respiration_clean = np.std(self.respiration_clean)
                        respiration_rate = rsp_signals["RSP_Rate"].iloc[-1]
                        self.respiration_rate_previous = respiration_rate
                        self.rate_label.setText(f"Respiration Rate: {respiration_rate:.2f} breaths/min")
                        self.update_rate_timer.start(10000)

                if self.avg_filtered_value is not None and self.std_filtered_value is not None and self.std_filtered_value != 0:
                    normalized_value = (filtered_value - self.avg_filtered_value) / self.std_filtered_value * 50 + 50
                    normalized_value = max(0, min(100, normalized_value))
                    self.respiration_strength_bar.setValue(int(normalized_value))

                    self.update_bar_color_based_on_value(filtered_value)

                    if normalized_value == 100 or normalized_value == 0:
                        self.reach_max_and_min += 1
                        if self.reach_max_and_min % 2 == 0:
                            print(f'Count when reach max and min: {self.reach_max_and_min // 2}')
                            self.update_harmony_bar()

    def update_previous_respiration_rate(self):
        if self.respiration_rate_previous is not None:
            self.respiration_rate_previous = float(self.rate_label.text().split()[-2])

    def update_bar_color_based_on_value(self, filtered_value):
        if self.avg_filtered_value is None or self.std_filtered_value is None:
            return

        distance_from_avg = abs(filtered_value - self.avg_filtered_value)
        if distance_from_avg > self.std_filtered_value:
            distance_from_avg = self.std_filtered_value

        r = int((distance_from_avg / self.std_filtered_value) * 255)
        g = 0
        b = 255 - r
        self.respiration_strength_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: rgb({r},{g},{b}); }}")

    def update_harmony_bar(self):
        if self.respiration_rate_previous is None:
            return

        current_rate = float(self.rate_label.text().split()[-2])
        difference = abs(current_rate - self.respiration_rate_previous)
        percentage_difference = (difference / self.respiration_rate_previous) * 100

        if percentage_difference <= 5:
            level = 100
        elif percentage_difference <= 10:
            level = 90
        elif percentage_difference <= 20:
            level = 80
        elif percentage_difference <= 30:
            level = 70
        elif percentage_difference <= 40:
            level = 60
        elif percentage_difference <= 50:
            level = 50
        elif percentage_difference <= 60:
            level = 40
        elif percentage_difference <= 70:
            level = 30
        elif percentage_difference <= 80:
            level = 20
        elif percentage_difference <= 90:
            level = 10
        else:
            level = 0

        self.harmony_bar.setValue(level)
        self.update_bar_color(self.harmony_bar, level)

        if level <= 50:
            self.reminder_label.setText("Breathing too fast!" if current_rate > self.respiration_rate_previous else "Breathing too slow!")
        else:
            self.reminder_label.setText("")

    def check_reminder(self):
        if self.harmony_bar.value() <= 50:
            print("Reminder: Check your breathing rate!")

    def update_bar_color(self, bar, value):
        r = 255 - int((value / 100) * 255)
        g = int((value / 100) * 255)
        b = 0
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
