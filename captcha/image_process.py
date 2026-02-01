import cv2


def img_process_norm(img, shape):
    """
    验证码图像预处理

    Args:
        img: BGR 格式的图像 (numpy array)
        shape: 目标尺寸 (width, height)

    Returns:
        处理后的图像，形状为 (height, width, 3)，值范围 [0, 1]
    """
    # 中值滤波降噪
    res = cv2.medianBlur(img, ksize=3)
    # 调整大小
    res = cv2.resize(src=res, dsize=shape)
    # 归一化到 [0, 1]
    cv2.normalize(src=res, dst=res, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
    return res