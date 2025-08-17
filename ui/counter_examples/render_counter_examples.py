from PyQt6.QtGui import QImage, QPixmap
import numpy as np

def array_to_qimage(array: np.ndarray) -> QImage:
    """Convert a 2D numpy array to a QImage.
    :param array: 2D numpy array representing a grayscale image.
    :return: QImage object.
    The array should be of shape (height, width) and dtype uint8."""
    # Ensure dtype is uint8
    array = array.astype(np.uint8)

    # Validate input
    if array.ndim != 2:
        raise ValueError("Expected a 2D grayscale array")
    height, width = array.shape
    if height != width:
        raise ValueError("Expected a square image")

    # Create QImage
    bytes_per_line = width
    return QImage(array.data, width, height, bytes_per_line, QImage.Format_Grayscale8)


def array_to_pixmap(array: np.ndarray) -> QPixmap:
    qimage = array_to_qimage(array)
    return QPixmap.fromImage(qimage)
