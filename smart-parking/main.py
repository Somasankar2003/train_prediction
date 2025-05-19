import cv2
import pytesseract
import sqlite3
import os
from datetime import datetime
import winsound  # For alert sounds (Windows only)

# Configure Tesseract path (ensure Tesseract is installed and the path is correct)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Create folder to store database
DB_FOLDER = "vehicle_data"
DB_PATH = os.path.join(DB_FOLDER, "vehicle_data.db")

if not os.path.exists(DB_FOLDER):
    os.makedirs(DB_FOLDER)

# Predefined vehicle numbers
PREDEFINED_VEHICLES = [
    {"plate_number": "RJ14CV0002", "entry_time": "2024-11-27 09:00:00", "last_entry_time": "2024-11-27 09:00:00"},
    {"plate_number": "22BH6517A", "entry_time": "2024-11-27 09:10:00", "last_entry_time": "2024-11-27 09:10:00"},
    {"plate_number": "KA18EQ0001", "entry_time": "2024-11-27 09:20:00", "last_entry_time": "2024-11-27 09:20"},
    {"plate_number": "KL65AN7722", "entry_time": "2024-11-27 09:30:00", "last_entry_time": "2024-11-27 09:30:00"},
]

# Initialize the SQLite database
def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT UNIQUE,
            entry_time TEXT,
            last_entry_time TEXT
        )
    ''')
        # Insert predefined vehicles
    for vehicle in PREDEFINED_VEHICLES:
        try:
            cursor.execute(
                "INSERT INTO logs (plate_number, entry_time, last_entry_time) VALUES (?, ?, ?)",
                (vehicle["plate_number"], vehicle["entry_time"], vehicle["last_entry_time"])
            )
        except sqlite3.IntegrityError:
            pass  # Ignore duplicates
    conn.commit()
    conn.close()

# Save detected plate to the database and check for new car
def log_plate(plate_number):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Normalize the plate number
    plate_number = plate_number.replace(" ", "").upper()

    # Check if the plate already exists in the database
    cursor.execute("SELECT * FROM logs WHERE plate_number = ?", (plate_number,))
    existing_plate = cursor.fetchone()

    if existing_plate is None:
        # Insert new car
        cursor.execute("INSERT INTO logs (plate_number, entry_time, last_entry_time) VALUES (?, ?, ?)",
                       (plate_number, timestamp, timestamp))
        conn.commit()
        conn.close()
        return True, None  # New car
    else:
        # Update last entry time for existing car
        last_entry_time = existing_plate[3]
        cursor.execute("UPDATE logs SET last_entry_time = ? WHERE plate_number = ?",
                       (timestamp, plate_number))
        conn.commit()
        conn.close()
        return False, last_entry_time  # Existing car

# Preprocess image for edge detection
def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 200)
    return edged

# Find license plate contour
def find_license_plate_contour(edged):
    contours, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / float(h)
        area = cv2.contourArea(contour)
        if 1.5 < aspect_ratio < 5 and area > 1000:
            return contour
    return None

# Extract license plate region
def extract_license_plate(image, contour):
    x, y, w, h = cv2.boundingRect(contour)
    return image[y:y+h, x:x+w]

# Clean OCR output
def clean_ocr_output(text):
    text = text.replace('O', '0').replace('I', '1').replace('l', '1').replace('Z', '2')
    text = text.replace('S', '5').replace('B', '8').replace(' ', '')
    return text.strip()

# Preprocess license plate image for better OCR
def preprocess_for_ocr(license_plate):
    gray_plate = cv2.cvtColor(license_plate, cv2.COLOR_BGR2GRAY)
    _, binary_plate = cv2.threshold(gray_plate, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary_plate

# Perform OCR and clean the output
def perform_ocr(license_plate):
    processed_plate = preprocess_for_ocr(license_plate)
    text = pytesseract.image_to_string(processed_plate, config="--psm 8")
    return clean_ocr_output(text)

# Play alert sound
def play_alert_sound():
    winsound.Beep(1000, 500)

# Capture video and process frames
def capture_video():
    cap = cv2.VideoCapture(0)  # Use webcam or replace with video file path

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        edged = preprocess_image(frame)
        contour = find_license_plate_contour(edged)

        if contour is not None:
            license_plate = extract_license_plate(frame, contour)
            plate_text = perform_ocr(license_plate)

            if plate_text:
                is_new_car, last_entry_time = log_plate(plate_text)
                if is_new_car:
                    play_alert_sound()
                    print(f"New Car Detected: {plate_text}")
                    cv2.putText(frame, f"New Car: {plate_text}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                else:
                    print(f"Existing Car: {plate_text} - Last entered at {last_entry_time}")
                    cv2.putText(frame, f"Existing Car: {plate_text}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                cv2.drawContours(frame, [contour], -1, (0, 255, 0), 2)
                cv2.putText(frame, plate_text, (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        cv2.imshow("Vehicle Monitoring System", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):  # Quit with 'q'
            break

    cap.release()
    cv2.destroyAllWindows()

# View database entries
def view_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs")
    rows = cursor.fetchall()
    conn.close()

    print("\n--- Stored Vehicle Data ---")
    for row in rows:
        print(f"ID: {row[0]}, Plate: {row[1]}, First Entry: {row[2]}, Last Entry: {row[3]}")

if __name__ == "__main__":
    init_database()  # Initialize the database
    capture_video()  # Start video capture
    view_database()  # View stored data after running
