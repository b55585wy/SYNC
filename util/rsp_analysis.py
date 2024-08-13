import multiprocessing
import numpy as np

from backend.util.neurokit2 import rsp_process


def signal_analysis(processed_data_queue, rsp_data_queue):
    window_size = 1500
    step_size = 100
    data_buffer = []

    while True:
        # 如果队列中有数据，读取并添加到缓冲区
        if not processed_data_queue.empty():
            data_point = processed_data_queue.get()

            # 确保数据点是数值类型
            # if isinstance(data_point, (int, float)):
            data_buffer.append(data_point['filtered_data'])
            # print(data_point['filtered_data'])
        # 当缓冲区中的数据量达到window_size时进行处理
        if len(data_buffer) >= window_size:
            # 使用NeuroKit2进行呼吸信号分析
            try:
                rsp_signals, info = rsp_process(rsp_signal=np.array(data_buffer[:window_size]), sampling_rate=50,
                                                   report='txt')
                # 将分析结果放入rsp_data_queue
                rsp_data_queue.put((rsp_signals, info))

            except Exception as e:
                print(f"Error during rsp_process: {e}")

            # 滑动窗口，保留最后step_size的数据
            data_buffer = data_buffer[step_size:]

        # 如果队列为空且缓冲区数据不足，则继续等待
        else:
            continue


def start_rsp_analysis(processed_data_queue, rsp_data_queue):
    process = multiprocessing.Process(
        target=signal_analysis,
        args=(processed_data_queue, rsp_data_queue),
        daemon=True
    )
    process.start()
