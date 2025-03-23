import cv2
import numpy as np
import os

def nothing(x):
    """
    Callback function for trackbars. This function does nothing.
    
    Args:
        x (int): The trackbar position (unused).
    """
    pass

def get_valid_kernel_size(value):
    """
    Ensures the kernel size is always an odd number and at least 1.
    
    Args:
        value (int): The input kernel size.
    
    Returns:
        int: The nearest odd kernel size (minimum value is 1).
    """
    return max(1, value | 1)

def check_file_access(file_path):
    """
    Checks if the given file exists and is accessible.
    
    Args:
        file_path (str): The path to the file.
    
    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the path is not a valid file.
        PermissionError: If the file is not readable.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Error: File '{file_path}' does not exist.")
    if not os.path.isfile(file_path):
        raise ValueError(f"Error: '{file_path}' is not a valid file.")
    if not os.access(file_path, os.R_OK):
        raise PermissionError(f"Error: '{file_path}' is not readable or access is denied.")

def resize_with_aspect_ratio(image, width=None, height=None, inter=cv2.INTER_AREA):
    """
    Resizes an image while maintaining its aspect ratio.
    
    Args:
        image (numpy.ndarray): The input image.
        width (int, optional): The desired width. Default is None.
        height (int, optional): The desired height. Default is None.
        inter (cv2.InterpolationFlags, optional): The interpolation method. Default is cv2.INTER_AREA.
    
    Returns:
        numpy.ndarray: The resized image.
    """
    dim = None
    (h, w) = image.shape[:2]

    if width is None and height is None:
        return image

    if width is None:
        r = height / float(h)
        dim = (int(w * r), int(height))
    else:
        r = width / float(w)
        dim = (int(width), int(h * r))

    return cv2.resize(image, dim, interpolation=inter)

def load_image(image_path):
    """
    Loads and resizes an image from the specified path.
    
    Args:
        image_path (str): The name of the image file (assumed to be in the 'images' directory).
    
    Returns:
        numpy.ndarray: The loaded and resized image.
    
    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is unsupported or corrupted.
        RuntimeError: If an unexpected error occurs.
    """
    image_path = os.path.join('images', image_path)
    check_file_access(image_path)

    valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
    if not image_path.lower().endswith(valid_extensions):
        raise ValueError(f"Error: '{image_path}' is not an image file. Please provide a valid image format.")

    try:
        img = cv2.imread(image_path)
        if img is None or img.size == 0:
            raise ValueError(f"Error: Unable to load image '{image_path}'. It may be corrupted or unsupported.")
            
        return resize_with_aspect_ratio(img, width=512)
    except Exception as e:
        raise RuntimeError(f"Unexpected error while loading image '{image_path}': {str(e)}")

def load_video(video_path):
    """
    Loads a video file and returns a VideoCapture object.
    
    Args:
        video_path (str): The name of the video file (assumed to be in the 'videos' directory).
    
    Returns:
        cv2.VideoCapture: The video capture object.
    
    Raises:
        FileNotFoundError: If the video file does not exist.
        ValueError: If the file format is unsupported.
        RuntimeError: If an unexpected error occurs.
    """
    video_path = os.path.join('videos', video_path)
    check_file_access(video_path)

    valid_video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv')
    if not video_path.lower().endswith(valid_video_extensions):
        raise ValueError(f"Error: '{video_path}' is not a valid video file. Please provide a supported video format.")

    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Error: Unable to open video file '{video_path}'. It may be corrupted or unsupported.")

        return cap
    except Exception as e:
        raise RuntimeError(f"Unexpected error while loading video '{video_path}': {str(e)}")

def release_video(cap):
    """
    Safely releases a VideoCapture object.
    
    Args:
        cap (cv2.VideoCapture): The video capture object.
    """
    if cap is not None and cap.isOpened():
        cap.release()

def create_trackbars(window_name="Tracking"):
    """
    Creates HSV trackbars for interactive color segmentation.
    
    Args:
        window_name (str, optional): The name of the OpenCV window. Default is "Tracking".
    """
    cv2.namedWindow(window_name)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

    cv2.createTrackbar("LH", window_name, 0, 179, nothing)
    cv2.createTrackbar("LS", window_name, 50, 255, nothing)
    cv2.createTrackbar("LV", window_name, 50, 255, nothing)
    cv2.createTrackbar("UH", window_name, 179, 179, nothing)
    cv2.createTrackbar("US", window_name, 255, 255, nothing)
    cv2.createTrackbar("UV", window_name, 255, 255, nothing)

def get_trackbar_values(window_name="Tracking"):
    """
    Retrieves HSV values from trackbars.
    
    Args:
        window_name (str, optional): The name of the OpenCV window. Default is "Tracking".
    
    Returns:
        tuple: A pair of numpy arrays representing lower and upper HSV bounds.
    """
    l_h = cv2.getTrackbarPos("LH", window_name)
    l_s = cv2.getTrackbarPos("LS", window_name)
    l_v = cv2.getTrackbarPos("LV", window_name)
    u_h = cv2.getTrackbarPos("UH", window_name)
    u_s = cv2.getTrackbarPos("US", window_name)
    u_v = cv2.getTrackbarPos("UV", window_name)

    # Ensure lower bound is never greater than upper bound
    lower_bound = np.array([min(l_h, u_h), min(l_s, u_s), min(l_v, u_v)])
    upper_bound = np.array([max(l_h, u_h), max(l_s, u_s), max(l_v, u_v)])

    return lower_bound, upper_bound

def apply_mask(image, lower_bound, upper_bound, kernel_size=5):
    """
    Applies a mask to segment colors in the specified HSV range with optional noise reduction.
    
    Args:
        image (numpy.ndarray): The input image.
        lower_bound (numpy.ndarray): The lower HSV bound.
        upper_bound (numpy.ndarray): The upper HSV bound.
        kernel_size (int, optional): Kernel size for morphological operations. Default is 5.
    
    Returns:
        tuple: The binary mask and segmented result.
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_bound, upper_bound)

    if kernel_size > 1:
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    result = cv2.bitwise_and(image, image, mask=mask)
    return mask, result

def create_display_windows(input_type):
    """
    Create windows for displaying images and ensure they stay on top.
    
    Args:
    - input_type (str): "img" for image processing, "video" for real-time video.

    Raises:
    - ValueError: If the input_type is not "img" or "video".
    """
    if input_type not in ["img", "video"]:
        raise ValueError("Invalid input_type. Use 'img' for image or 'video' for real-time processing.")

    window_names = ["Mask", "Result", "Original"]

    for window in window_names:
        cv2.namedWindow(window)
        cv2.setWindowProperty(window, cv2.WND_PROP_TOPMOST, 1)

def display_results(original=None, mask=None, result=None, frame=None):
    """
    Display the results in OpenCV windows.

    Args:
    - original: The original image (None for video mode).
    - mask: The binary mask of the detected region.
    - result: The final segmented output.
    - frame: The current video frame (None for image mode).
    """
    if frame is not None:
        cv2.imshow("Original", frame)
    elif original is not None:
        cv2.imshow("Original", original)

    if mask is not None:
        cv2.imshow("Mask", mask)

    if result is not None:
        cv2.imshow("Result", result)
