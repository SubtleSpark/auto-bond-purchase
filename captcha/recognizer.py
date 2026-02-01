import os
from pathlib import Path

import cv2
import numpy as np
from keras.models import load_model

from .image_process import img_process_norm
from .label_process import decode_predict
from .model_utils import word_acc


class CaptchaRecognizer:
    """验证码识别器"""

    # 模型期望的输入尺寸
    IMG_WIDTH = 128
    IMG_HEIGHT = 32

    def __init__(self, model_path: str = None):
        """
        初始化识别器

        Args:
            model_path: 模型文件路径，默认使用项目 models/VGG.keras
        """
        if model_path is None:
            model_path = Path(__file__).parent.parent / "models" / "VGG.keras"

        self.model_path = str(model_path)
        self._model = None

    @property
    def model(self):
        """懒加载模型"""
        if self._model is None:
            self._model = load_model(
                self.model_path,
                custom_objects={"word_acc": word_acc}
            )
        return self._model

    def recognize(self, image_path: str) -> str:
        """
        识别验证码图片

        Args:
            image_path: 验证码图片路径

        Returns:
            识别出的 4 位数字字符串
        """
        # 读取图片 (BGR 格式)
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法读取图片: {image_path}")

        # 预处理
        processed = img_process_norm(
            img,
            shape=(self.IMG_WIDTH, self.IMG_HEIGHT)
        )

        # 添加 batch 维度
        batch = np.array([processed])

        # 推理
        predict = self.model.predict(batch, verbose=0)

        # 解码
        result = decode_predict(predict)
        return result[0]

    def recognize_from_bytes(self, image_bytes: bytes) -> str:
        """
        从字节数据识别验证码

        Args:
            image_bytes: 图片的字节数据

        Returns:
            识别出的 4 位数字字符串
        """
        # 从字节解码图片
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("无法解码图片数据")

        # 预处理
        processed = img_process_norm(
            img,
            shape=(self.IMG_WIDTH, self.IMG_HEIGHT)
        )

        # 添加 batch 维度
        batch = np.array([processed])

        # 推理
        predict = self.model.predict(batch, verbose=0)

        # 解码
        result = decode_predict(predict)
        return result[0]
