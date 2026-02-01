import numpy as np

WORDLIST = list('0123456789')


def decode(arr):
    """
    解码单个预测结果

    Args:
        arr: shape 为 (4, 10) 的二维数组

    Returns:
        4 位数字字符串
    """
    arr = arr.tolist()
    idx = list(np.argmax(arr, axis=1))
    result = ''.join(WORDLIST[i] for i in idx)
    return result


def decode_predict(predict):
    """
    批量解码预测结果

    Args:
        predict: shape 为 (batch_size, 4, 10) 的三维数组

    Returns:
        解码后的字符串列表
    """
    return [decode(arr) for arr in predict]