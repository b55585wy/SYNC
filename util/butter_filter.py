# import multiprocessing
# from scipy.signal import butter, lfilter, lfilter_zi
#
#
# def butter_lowpass(cutoff, fs, order=5):
#     nyq = 0.5 * fs
#     normal_cutoff = cutoff / nyq
#     b, a = butter(order, normal_cutoff, btype='low', analog=False)
#     return b, a
#
#
# def iir_filter(data, b, a, zi):
#     # 应用IIR滤波器，并返回当前滤波结果和更新后的滤波器状态
#     y, zi = lfilter(b, a, [data], zi=zi)
#     return y[0], zi
#
#
# def signal_filter(raw_data_queue, processed_data_queue, plot_data_queue):
#     # 定义滤波器参数
#     cutoff = 0.5
#     fs = 50.0
#     b, a = butter_lowpass(cutoff, fs)
#
#     # 初始化滤波器状态
#     zi = lfilter_zi(b, a) * 0
#
#     while True:
#         if not raw_data_queue.empty():
#             data_point = raw_data_queue.get()
#             value = data_point['data']  # 获取原始数据值
#
#             # 对单个数据点进行IIR滤波
#             filtered_value, zi = iir_filter(value, b, a, zi)
#
#             # 将滤波后的数据与时间戳一起保存
#             processed_data = {
#                 'timestamp': data_point['timestamp'],  # 使用原始数据的时间戳
#                 'filtered_data': filtered_value
#             }
#
#             # 将处理后的数据放入两个队列中
#             processed_data_queue.put(processed_data)
#             plot_data_queue.put(processed_data)
#
#
#
# def start_signal_filter(raw_data_queue, processed_data_queue, plot_data_queue):
#     multiprocessing.Process(
#         target=signal_filter,
#         args=(raw_data_queue, processed_data_queue, plot_data_queue),
#         daemon=True
#     ).start()


# close signal filter progress
import multiprocessing
from scipy.signal import butter, lfilter, lfilter_zi


def butter_lowpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return b, a


def iir_filter(data, b, a, zi):
    # 应用IIR滤波器，并返回当前滤波结果和更新后的滤波器状态
    y, zi = lfilter(b, a, [data], zi=zi)
    return y[0], zi


def signal_filter(raw_data_queue, processed_data_queue, plot_data_queue):
    # 定义滤波器参数
    cutoff = 0.5
    fs = 50.0
    b, a = butter_lowpass(cutoff, fs)

    # 初始化滤波器状态
    zi = lfilter_zi(b, a) * 0

    while True:
        if not raw_data_queue.empty():
            data_point = raw_data_queue.get()
            filtered_value = data_point['data']  # 获取原始数据值

            # 对单个数据点进行IIR滤波
            # filtered_value, zi = iir_filter(value, b, a, zi)

            # 将滤波后的数据与时间戳一起保存
            processed_data = {
                'timestamp': data_point['timestamp'],  # 使用原始数据的时间戳
                'filtered_data': filtered_value
            }

            # 将处理后的数据放入两个队列中
            processed_data_queue.put(processed_data)
            plot_data_queue.put(processed_data)



def start_signal_filter(raw_data_queue, processed_data_queue, plot_data_queue):
    multiprocessing.Process(
        target=signal_filter,
        args=(raw_data_queue, processed_data_queue, plot_data_queue),
        daemon=True
    ).start()