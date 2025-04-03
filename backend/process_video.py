import cv2
import easyocr
import torch
import os
import pandas as pd
import numpy as np
import re
import pytesseract
from ultralytics import YOLO
from collections import defaultdict
from database import insert_plate
import time
from scipy import ndimage

# Configure GPU if available
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

# Configure Tesseract path for Windows
pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'

# Load YOLO model with GPU acceleration
model = YOLO("models/best.pt")
model.to(device)

# Load EasyOCR reader with GPU acceleration - fixed initialization
use_gpu = torch.cuda.is_available()
easyocr_reader = easyocr.Reader(["en"], gpu=use_gpu)

def deskew(image):
    """Deskew the image to straighten text"""
    try:
        # Convert to grayscale if not already
        if len(image.shape) > 2:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # Calculate skew angle
        coords = np.column_stack(np.where(gray > 0))
        if len(coords) == 0:  # Check if coords is empty
            return image
            
        angle = cv2.minAreaRect(coords)[-1]
        
        # Adjust the angle
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
            
        # Rotate the image to correct skew
        (h, w) = gray.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, 
                                 borderMode=cv2.BORDER_REPLICATE)
        return rotated
    except Exception as e:
        print(f"Deskew error: {e}")
        return image

def perspective_correction(image):
    """Apply perspective correction to license plate"""
    try:
        # Convert to grayscale
        if len(image.shape) > 2:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # Find contours
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Find largest contour which should be the plate
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Approximate the contour to get a rectangle
            epsilon = 0.02 * cv2.arcLength(largest_contour, True)
            approx = cv2.approxPolyDP(largest_contour, epsilon, True)
            
            # If we have a quadrilateral with 4 corners
            if len(approx) == 4:
                # Order the points correctly
                pts = approx.reshape(4, 2)
                rect = np.zeros((4, 2), dtype="float32")
                
                # Get top-left, top-right, bottom-right, bottom-left
                s = pts.sum(axis=1)
                rect[0] = pts[np.argmin(s)]
                rect[2] = pts[np.argmax(s)]
                
                diff = np.diff(pts, axis=1)
                rect[1] = pts[np.argmin(diff)]
                rect[3] = pts[np.argmax(diff)]
                
                # Get width and height of the corrected image
                widthA = np.sqrt(((rect[2][0] - rect[3][0]) ** 2) + ((rect[2][1] - rect[3][1]) ** 2))
                widthB = np.sqrt(((rect[1][0] - rect[0][0]) ** 2) + ((rect[1][1] - rect[0][1]) ** 2))
                maxWidth = max(int(widthA), int(widthB))
                
                heightA = np.sqrt(((rect[1][0] - rect[2][0]) ** 2) + ((rect[1][1] - rect[2][1]) ** 2))
                heightB = np.sqrt(((rect[0][0] - rect[3][0]) ** 2) + ((rect[0][1] - rect[3][1]) ** 2))
                maxHeight = max(int(heightA), int(heightB))
                
                # Ensure we have valid dimensions
                if maxWidth <= 0 or maxHeight <= 0:
                    return image
                
                # Destination points
                dst = np.array([
                    [0, 0],
                    [maxWidth - 1, 0],
                    [maxWidth - 1, maxHeight - 1],
                    [0, maxHeight - 1]], dtype="float32")
                
                # Calculate perspective transform
                M = cv2.getPerspectiveTransform(rect, dst)
                warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
                
                return warped
    except Exception as e:
        print(f"Perspective correction error: {e}")
    
    return image

def preprocess_plate_image(plate_img):
    """Apply comprehensive image processing to improve OCR readability"""
    if plate_img.size == 0 or plate_img is None:
        return {'original': plate_img}
        
    try:
        # Create a copy to avoid modifying the original
        processed = plate_img.copy()
        
        # Resize for better processing (maintain aspect ratio)
        height, width = processed.shape[:2]
        new_width = 300  # Target width
        new_height = int(height * (new_width / width))
        processed = cv2.resize(processed, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Apply perspective correction if possible
        processed = perspective_correction(processed)
        
        # Convert to grayscale
        gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        
        # Apply bilateral filter to reduce noise while preserving edges
        bilateral = cv2.bilateralFilter(gray, 11, 17, 17)
        
        # Apply advanced deblurring (Wiener filter)
        kernel = np.ones((5, 5), np.float32)/25
        deblurred = cv2.filter2D(bilateral, -1, kernel)
        
        # Deskew to correct rotation
        deskewed = deskew(deblurred)
        
        # Apply CLAHE for better contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 4))
        enhanced = clahe.apply(deskewed)
        
        # Apply adaptive thresholding for binarization
        thresh = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 13, 2)
                                      
        # Use morphological operations to clean up the image
        kernel = np.ones((1, 1), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
        
        # Final denoising
        final = cv2.fastNlMeansDenoising(closing, None, 10, 7, 21)
        
        # Create multiple versions for OCR to try
        versions = {
            'original': plate_img,
            'gray': gray,
            'enhanced': enhanced,
            'binary': thresh,
            'final': final
        }
        
        return versions
        
    except Exception as e:
        print(f"Error in preprocessing: {e}")
        return {'original': plate_img}  # Return original if processing fails

def is_valid_indian_plate(text):
    """Check if the detected text follows Indian license plate format"""
    # Remove all spaces and special characters
    cleaned_text = re.sub(r'[^A-Z0-9]', '', text.upper())
    
    # Standard format: 2 letters + 1-2 digits + 1-3 letters + 1-4 digits
    # Examples: MH12AB1234, KA51MD1492, DL3CAM1111
    standard_pattern = re.compile(r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{1,4}$')
    
    return bool(standard_pattern.match(cleaned_text))

def format_indian_plate(text):
    """Format the license plate text according to Indian standards"""
    # Remove all spaces and special characters
    cleaned_text = re.sub(r'[^A-Z0-9]', '', text.upper())
    
    if len(cleaned_text) >= 6:  # Minimum valid length
        # Extract components
        state_code = cleaned_text[:2]
        
        # Find where district number ends and letters begin
        district_end = 2
        while district_end < len(cleaned_text) and cleaned_text[district_end].isdigit():
            district_end += 1
        
        district_num = cleaned_text[2:district_end]
        
        # Find where letters end and final numbers begin
        series_end = district_end
        while series_end < len(cleaned_text) and cleaned_text[series_end].isalpha():
            series_end += 1
        
        series_letters = cleaned_text[district_end:series_end]
        reg_num = cleaned_text[series_end:]
        
        # Format with spaces
        return f"{state_code} {district_num}{series_letters} {reg_num}"
    
    return text  # Return original if can't format properly

def correct_plate_text(text):
    """Correct common OCR errors in license plate text"""
    # Common OCR mistakes in license plate recognition
    corrections = {
        '0': 'O', 'O': '0',
        '1': 'I', 'I': '1',
        '8': 'B', 'B': '8',
        '5': 'S', 'S': '5',
        '2': 'Z', 'Z': '2',
        '6': 'G', 'G': '6',
        '7': 'T', 'T': '7',
        '4': 'A', 'A': '4'
    }
    
    # First two characters should be letters (state code)
    # Convert to uppercase and clean non-alphanumeric characters
    cleaned_text = re.sub(r'[^A-Z0-9]', '', text.upper())
    
    # Make corrections based on position
    corrected = list(cleaned_text)
    
    if len(corrected) >= 2:
        # First two characters must be letters (state code)
        for i in range(2):
            if i < len(corrected) and corrected[i].isdigit():
                corrected[i] = corrections.get(corrected[i], corrected[i])
    
    if len(corrected) >= 4:
        # Characters after state code should be digits for district code
        for i in range(2, 4):
            if i < len(corrected) and corrected[i].isalpha():
                corrected[i] = corrections.get(corrected[i], corrected[i])
                
    return ''.join(corrected)

def process_video(video_name):
    video_path = os.path.join("backend/data", video_name)
    output_csv = os.path.join("backend/results", f"{video_name.split('.')[0]}.csv")
    output_video_path = os.path.join("backend/processed", video_name)
    frames_dir = os.path.join("backend/processed", f"{video_name.split('.')[0]}_frames")
    
    # Create directories if they don't exist
    os.makedirs("backend/results", exist_ok=True)
    os.makedirs("backend/processed", exist_ok=True)
    os.makedirs(frames_dir, exist_ok=True)
    
    # Check if file exists
    if not os.path.exists(video_path):
        print(f"Error: Video file {video_path} not found")
        return []
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return []
    
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Use MJPG codec for Windows compatibility
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))

    # Tracking vehicles and license plates across frames
    plate_candidates = defaultdict(lambda: {"occurrences": [], "versions": defaultdict(int)})
    
    print(f"Processing video: {video_name} with {frame_count} frames")
    start_time = time.time()
    
    # Process every nth frame to save time (adjust based on video fps)
    frame_step = max(1, round(fps/10))  # Process ~10 frames per second
    
    # Step 1: Convert video to frames and detect plates
    frame_number = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Skip frames as per frame_step
        if frame_number % frame_step != 0:
            frame_number += 1
            continue
            
        timestamp = frame_number / fps  # Calculate actual timestamp in seconds
        
        # Save frame
        frame_path = os.path.join(frames_dir, f"frame_{frame_number:06d}.jpg")
        cv2.imwrite(frame_path, frame)
        
        # Step 2: Apply license plate detection with GPU acceleration
        results = model(frame, conf=0.45)
        
        # Process each detection
        for i, result in enumerate(results):
            boxes = result.boxes
            
            for box in boxes:
                try:
                    # Get box coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    
                    # Extract license plate region with a margin
                    h, w = y2-y1, x2-x1
                    margin_x = int(w * 0.05)
                    margin_y = int(h * 0.05)
                    
                    # Ensure we don't go outside the image bounds
                    y1_safe = max(0, y1-margin_y)
                    y2_safe = min(frame.shape[0], y2+margin_y)
                    x1_safe = max(0, x1-margin_x)
                    x2_safe = min(frame.shape[1], x2+margin_x)
                    
                    plate_crop = frame[y1_safe:y2_safe, x1_safe:x2_safe]
                    
                    if plate_crop.size == 0 or plate_crop is None:
                        continue
                    
                    # Step 3: Apply comprehensive image processing for better OCR
                    processed_versions = preprocess_plate_image(plate_crop)
                    
                    # Save processed versions for debugging
                    debug_dir = os.path.join(frames_dir, "debug", f"frame_{frame_number:06d}_plate_{i}")
                    os.makedirs(debug_dir, exist_ok=True)
                    
                    for version_name, img in processed_versions.items():
                        if img is not None and img.size > 0:
                            cv2.imwrite(os.path.join(debug_dir, f"{version_name}.jpg"), img)
                    
                    # Step 4: Apply OCR to all processed versions
                    detected_texts = []
                    
                    # Try all image versions for best results
                    for version_name, img in processed_versions.items():
                        if img is None or img.size == 0:
                            continue
                            
                        # EasyOCR - better for less processed images
                        if version_name in ['original', 'gray', 'enhanced']:
                            try:
                                easyocr_results = easyocr_reader.readtext(img)
                                for _, text, prob in easyocr_results:
                                    if prob > 0.3 and text.strip():
                                        detected_texts.append((text.strip(), prob, "easyocr"))
                            except Exception as e:
                                print(f"EasyOCR error on {version_name}: {e}")
                        
                        # Tesseract - better for binary/processed images
                        if version_name in ['binary', 'final', 'enhanced']:
                            try:
                                # Try different PSM modes for best results
                                for psm in [6, 7, 8, 13]:  # 7=single line, 8=word, 6=block, 13=raw line
                                    tess_text = pytesseract.image_to_string(
                                        img, 
                                        config=f'--psm {psm} --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                                    ).strip()
                                    
                                    if tess_text:
                                        # Assign confidence based on length (simple heuristic)
                                        confidence = min(0.7, 0.4 + (len(tess_text) / 20))
                                        detected_texts.append((tess_text, confidence, "tesseract"))
                            except Exception as e:
                                print(f"Tesseract error on {version_name}: {e}")
                    
                    # Process detected texts
                    for text, confidence, source in detected_texts:
                        # Clean and correct text
                        corrected_text = correct_plate_text(text)
                        
                        # Check if it follows Indian plate format
                        if is_valid_indian_plate(corrected_text):
                            # Format according to Indian standards
                            formatted_text = format_indian_plate(corrected_text)
                            
                            # Clean text for tracking (remove spaces)
                            clean_key = re.sub(r'[^A-Z0-9]', '', formatted_text.upper())
                            
                            # Add to candidates with tracking info
                            plate_candidates[clean_key]["occurrences"].append({
                                "frame": frame_number,
                                "timestamp": timestamp,
                                "confidence": confidence * (1.2 if is_valid_indian_plate(corrected_text) else 0.8),
                                "box": (x1, y1, x2, y2)
                            })
                            
                            # Track different versions/readings of the same plate
                            plate_candidates[clean_key]["versions"][formatted_text] += 1
                            
                            # Draw on frame for visualization
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            cv2.putText(frame, formatted_text, (x1, y1-10),
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                except Exception as e:
                    print(f"Error processing detection: {e}")
                    continue
        
        # Write the annotated frame to output video
        out.write(frame)
        frame_number += 1
        
        # Print progress
        if frame_number % 100 == 0:
            elapsed = time.time() - start_time
            frames_per_sec = frame_number / elapsed if elapsed > 0 else 0
            print(f"Processed {frame_number}/{frame_count} frames ({frames_per_sec:.2f} fps)")
    
    # Step 5: Analyze tracking data to get the most accurate readings
    plate_data = []
    
    for plate_key, data in plate_candidates.items():
        occurrences = data["occurrences"]
        versions = data["versions"]
        
        # Only consider plates with sufficient occurrences
        if len(occurrences) >= 3:
            # Find the most common reading of this plate
            most_common_text = max(versions.items(), key=lambda x: x[1])[0]
            
            # Get the timestamp with highest confidence
            best_occurrence = max(occurrences, key=lambda x: x["confidence"])
            timestamp = int(best_occurrence["timestamp"])
            
            # Add to results
            plate_entry = {
                "video": video_name,
                "timestamp": timestamp,
                "plate": most_common_text
            }
            plate_data.append(plate_entry)
            
            # Insert into database
            insert_plate(video_name, most_common_text, str(timestamp))
    
    # Save results to CSV
    pd.DataFrame(plate_data).to_csv(output_csv, index=False)
    
    cap.release()
    out.release()
    
    # Print summary
    elapsed_time = time.time() - start_time
    print(f"Processed {video_name}: Found {len(plate_data)} unique license plates in {elapsed_time:.2f} seconds")
    
    return plate_data
