import cv2
import supervision as sv
from inference import get_model
import numpy as np
import time

# -------------------- Model Details --------------------
API_KEY = "6JHdvqSN5impXhSfA4Jb"  # Your Roboflow API key
MODEL_ID = "tic-tac-toe-fctyp-0e0ri/1"  # Your model ID

# -------------------- Grid Configuration --------------------
GRID_TOP_LEFT = (140, 40)      # (x1, y1)
GRID_BOTTOM_RIGHT = (500, 400) # (x2, y2)

# -------------------- Global variables for file writing --------------------
detection_sent = False
last_detection = ""
detection_history = []
processed_this_frame = set()

# -------------------- Timing variables --------------------
last_detection_time = 0
DETECTION_INTERVAL = 15  # seconds

# -------------------- Custom Mapping Function --------------------
def map_grid_position(camera_row, camera_col):
    """
    Custom mapping from camera coordinates to your desired coordinate system
    Modify this dictionary to match your setup
    """
    # Custom mapping: camera (row,col) -> desired (row,col)
    custom_mapping = {
        # Format: (camera_row, camera_col): (desired_row, desired_col)
        (0, 0): (0, 0),  # top-left stays top-left
        (0, 1): (0, 1),  # top-middle stays top-middle  
        (0, 2): (0, 2),  # top-right stays top-right
        (1, 0): (1, 0),  # middle-left stays middle-left
        (1, 1): (1, 1),  # center stays center
        (1, 2): (1, 2),  # middle-right stays middle-right
        (2, 0): (2, 0),  # bottom-left stays bottom-left
        (2, 1): (2, 1),  # bottom-middle stays bottom-middle
        (2, 2): (2, 2),  # bottom-right stays bottom-right
    }
    
    return custom_mapping.get((camera_row, camera_col), (camera_row, camera_col))

# -------------------- Helper Function --------------------
def get_grid_position(cx, cy, grid_tl, grid_br):
    grid_x1, grid_y1 = grid_tl
    grid_x2, grid_y2 = grid_br

    if not (grid_x1 < cx < grid_x2 and grid_y1 < cy < grid_y2):
        return None

    cell_width = (grid_x2 - grid_x1) / 3
    cell_height = (grid_y2 - grid_y1) / 3

    col = int((cx - grid_x1) / cell_width)
    row = int((cy - grid_y1) / cell_height)

    return row, col

# -------------------- File writing function --------------------
def write_to_notepad(symbol, row, col):
    global detection_sent, last_detection, detection_history
    
    symbol_upper = symbol.upper()
    if symbol_upper in ['X', 'O']:
        # Apply custom mapping
        mapped_row, mapped_col = map_grid_position(row, col)
        current_detection = f"{symbol_upper},{mapped_row},{mapped_col}"
        
        # Check if we've already processed this exact detection in this frame
        if current_detection in processed_this_frame:
            return False
            
        # Add to processed set for this frame
        processed_this_frame.add(current_detection)
        
        # Only write if this is a completely NEW detection (not in history)
        if current_detection not in detection_history:
            detection_history.append(current_detection)
            detection_sent = True
            last_detection = current_detection
            
            with open('abc.txt', 'w') as f:
                for detection in detection_history:
                    f.write(f"{detection}\n")
            
            # ONLY PRINT WHEN NEW DETECTION IS ADDED - in the format you want
            print(f"{symbol_upper},{row},{col}")
            return True
        else:
            return False
    else:
        return False

def reset_detection():
    global detection_sent, last_detection, detection_history, last_detection_time
    detection_sent = False
    last_detection = ""
    detection_history.clear()  # Clear the history
    last_detection_time = time.time()  # Reset timer
    # Clear the notepad file
    open('abc.txt', 'w').close()
    print("🔄 DETECTION RESET - History cleared and notepad file emptied!")

# -------------------- Load Model --------------------
print("Loading YOLO model...")
model = get_model(model_id=MODEL_ID, api_key=API_KEY)

# -------------------- Initialize Webcam --------------------
cap = cv2.VideoCapture(2)
if not cap.isOpened():
    raise IOError("Cannot open webcam")

# -------------------- Annotators --------------------
bounding_box_annotator = sv.BoxAnnotator()
label_annotator = sv.LabelAnnotator()

print("Running real-time detection... press 'q' to quit")
print("Press 'r' to reset detection and allow new moves")
print(f"Detection will run every {DETECTION_INTERVAL} seconds")
print("Each unique position-symbol combination will be written ONLY ONCE!")

# Clear file at start
open('abc.txt', 'w').close()
last_detection_time = time.time()

# -------------------- Main Loop --------------------
while True:
    ret, frame = cap.read()
    if not ret:
        continue

    # Reset frame processing at start of each frame
    processed_this_frame.clear()

    # Draw the Grid
    cv2.rectangle(frame, GRID_TOP_LEFT, GRID_BOTTOM_RIGHT, (0, 255, 0), 2)
    cell_w = (GRID_BOTTOM_RIGHT[0] - GRID_TOP_LEFT[0]) / 3
    cell_h = (GRID_BOTTOM_RIGHT[1] - GRID_TOP_LEFT[1]) / 3
    for i in range(1, 3):
        cv2.line(frame, (int(GRID_TOP_LEFT[0] + i * cell_w), GRID_TOP_LEFT[1]), (int(GRID_TOP_LEFT[0] + i * cell_w), GRID_BOTTOM_RIGHT[1]), (0, 255, 0), 1)
        cv2.line(frame, (GRID_TOP_LEFT[0], int(GRID_TOP_LEFT[1] + i * cell_h)), (GRID_BOTTOM_RIGHT[0], int(GRID_TOP_LEFT[1] + i * cell_h)), (0, 255, 0), 1)

    current_time = time.time()
    time_since_last_detection = current_time - last_detection_time
    
    # Run YOLO inference only every 10 seconds
    if time_since_last_detection >= DETECTION_INTERVAL:
        # Update last detection time
        last_detection_time = current_time
        
        # Run YOLO inference
        results = model.infer(frame)[0]
        detections = sv.Detections.from_inference(results)
        
        # Process detections
        detection_found = False
        for i in range(len(detections)):
            box = detections.xyxy[i]
            class_name = detections.data['class_name'][i]

            center_x = (box[0] + box[2]) / 2
            center_y = (box[1] + box[3]) / 2

            position = get_grid_position(center_x, center_y, GRID_TOP_LEFT, GRID_BOTTOM_RIGHT)

            if position is not None:
                row, col = position
                # Write to file (with STRICT duplicate prevention) - uses mapped coordinates
                if write_to_notepad(class_name, row, col):
                    detection_found = True
                
                # Visual feedback - show both original and mapped positions
                cv2.circle(frame, (int(center_x), int(center_y)), 5, (255, 0, 0), -1)
                # Show original position in red, mapped position in blue
                cv2.putText(frame, f"Cam:({row},{col})", (int(box[0]), int(box[1]) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        if not detection_found:
            print("⏰ No new detections found in this interval")
        
        # Annotate frame with detections
        annotated = bounding_box_annotator.annotate(scene=frame, detections=detections)
        annotated = label_annotator.annotate(scene=annotated, detections=detections)
    else:
        # Just show the frame without processing
        annotated = frame

    # Display status with countdown timer
    status = "WAITING FOR RESET (Press 'r')" if detection_sent else "READY FOR NEW DETECTION"
    time_remaining = max(0, DETECTION_INTERVAL - time_since_last_detection)
    
    cv2.putText(annotated, f"Status: {status}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(annotated, f"Next detection in: {time_remaining:.1f}s", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(annotated, "Press 'q' to quit, 'r' to reset", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(annotated, f"Unique detections: {len(detection_history)}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    if detection_sent:
        cv2.putText(annotated, f"Last: {last_detection}", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    cv2.imshow("XO Detection - With Custom Mapping", annotated)

    # Key handling
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('r'):
        reset_detection()

# Clean up
cap.release()
cv2.destroyAllWindows()
print(f"Final unique detections: {len(detection_history)}")
print("Detection stopped.")
