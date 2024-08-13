import multiprocessing
from multiprocessing import Queue

from backend.serial_device import SerialDevice
from backend.util.butter_filter import start_signal_filter
from backend.util.plot import start_signal_plotter
from backend.util.rsp_analysis import start_rsp_analysis


def main():
    raw_data_queue = Queue()  # 原始数据队列
    processed_data_queue = Queue()  # 处理后数据的队列
    plot_raw_data_queue = Queue()  # 绘图数据的队列
    rsp_data_queue = Queue()
    # 实例化 SerialDevice 类并启动数据采集进程
    serial_device = SerialDevice(data_queue=raw_data_queue)
    multiprocessing.Process(target=serial_device.collect_data, daemon=True).start()

    # 启动信号滤波进程
    # start_signal_filter(raw_data_queue, processed_data_queue, plot_raw_data_queue)

    # 关闭信号滤波进程
    start_signal_filter(raw_data_queue, processed_data_queue, plot_raw_data_queue)

    # 启动呼吸率计算进程
    start_rsp_analysis(processed_data_queue, rsp_data_queue)


    # 启动信号绘图
    start_signal_plotter(plot_raw_data_queue,rsp_data_queue)


if __name__ == '__main__':
    main()