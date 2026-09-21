import keras.ops as ops
from keras.metrics import categorical_accuracy


def word_acc(y_true, y_pred):
    """
    自定义指标：4 个位置都正确才算对
    """
    out = categorical_accuracy(y_true=y_true, y_pred=y_pred)
    return ops.min(out, axis=-1)