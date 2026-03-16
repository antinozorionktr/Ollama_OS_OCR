import cv2
import numpy as np
from PIL import Image
import os

def deskew_image(image_path: str) -> np.ndarray:
    """Detects text skew and rotates the image to straighten it."""
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    
    # Thresholding to find text regions
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    
    # Find coordinates of all non-zero pixels
    coords = np.column_stack(np.where(thresh > 0))
    angle = cv2.minAreaRect(coords)[-1]
    
    # Normalize the angle
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
        
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return rotated

def apply_morphology(img: np.ndarray, op_type: str = 'both') -> np.ndarray:
    """Apply erosion and dilation to clean noise and thicken text."""
    kernel = np.ones((1, 1), np.uint8)
    
    if op_type == 'erosion' or op_type == 'both':
        img = cv2.erode(img, kernel, iterations=1)
    
    if op_type == 'dilation' or op_type == 'both':
        img = cv2.dilate(img, kernel, iterations=1)
        
    return img

def preprocess_for_ocr(image_path: str, output_path: str = None) -> str:
    """Full preprocessing pipeline: deskew -> grayscale -> morphology -> contrast."""
    # 1. Deskew
    rotated = deskew_image(image_path)
    
    # 2. Grayscale & Contrast
    gray = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)
    
    # Adaptive thresholding for better text visibility
    processed = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # 3. Morphology
    processed = apply_morphology(processed)
    
    # Save back to a temp file or the same path
    if output_path is None:
        output_path = image_path.replace(".png", "_preprocessed.png")
        
    cv2.imwrite(output_path, processed)
    return output_path

def preprocess_block_cv(img_pil: Image) -> Image:
    """OpenCV-based preprocessing for small crops/blocks."""
    # Convert PIL to CV2
    img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # Dilation to thicken faint text
    kernel = np.ones((2,2), np.uint8)
    dilated = cv2.dilate(gray, kernel, iterations=1)
    
    # Convert back to PIL
    return Image.fromarray(dilated)
