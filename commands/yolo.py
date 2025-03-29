import sys
import os
from ultralytics import YOLO

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from subsystem.Vision import RealsenseVision

# Initialize vision and YOLO model

def yolo():
    """
    Run YOLO detection on the current frame and return bounding boxes
    Returns: List of dictionaries containing detection info
    [
        {
            'class': str,      # Class name
            'confidence': float,# Confidence score
            'bbox': tuple      # (x1, y1, x2, y2) coordinates
        },
        ...
    ]
    """
    vision = RealsenseVision()
    model = YOLO('lib/cv/yolo/yolo11n.pt', task='detect')
    try:
        # Run detection
        results = vision.detect_objects(model)
        if results is None:
            return []

        # Extract bounding boxes and metadata
        detections = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])  # Bounding box coordinates
                conf = float(box.conf[0])  # Confidence score
                cls = int(box.cls[0])  # Class index
                class_name = model.names[cls]  # Class name

                detection = {
                    'class': class_name,
                    'confidence': conf,
                    'bbox': (x1, y1, x2, y2)
                }
                detections.append(detection)

        return detections

    except Exception as e:
        print(f"Error in yolo detection: {str(e)}")
        return []

def yolo_object_found(object_name):
    ret = yolo()
    if ret is None:
        return False
    for det in ret:
        if det['class'] == object_name:
            return True
    return False

if __name__ == '__main__':
    # Test the detection
    detections = yolo()
    for det in detections:
        print(f"Found {det['class']} with confidence {det['confidence']:.2f} at {det['bbox']}")
