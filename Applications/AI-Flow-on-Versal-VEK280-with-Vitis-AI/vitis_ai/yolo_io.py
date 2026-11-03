"""Model input, shared by the notebook and the code that runs with VAISW."""
import cv2
import numpy as np

IMG_W, IMG_H = 640, 640       # the YOLOv8s default


def letterbox(width, height):
    """Where an image goes in the model input: scale, scaled size and offsets. The grey bars keep its aspect."""
    scale = min(IMG_W / width, IMG_H / height)
    w, h = round(width * scale), round(height * scale)
    return scale, w, h, (IMG_W - w) // 2, (IMG_H - h) // 2


def to_rgb(image_path):
    """Image file -> uint8 RGB at the model input size, with grey bars."""
    rgb = cv2.cvtColor(cv2.imread(str(image_path)), cv2.COLOR_BGR2RGB)
    _, w, h, dx, dy = letterbox(rgb.shape[1], rgb.shape[0])
    canvas = np.full((IMG_H, IMG_W, 3), 114, np.uint8)
    canvas[dy:dy + h, dx:dx + w] = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_LINEAR)
    return canvas


def to_input(image_path):
    """Image file -> float32 NCHW in [0, 1], the model input."""
    return to_rgb(image_path).transpose(2, 0, 1)[None].astype(np.float32) / 255
