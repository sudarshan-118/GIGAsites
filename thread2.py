import cv2
import threading
import time
from pynput.mouse import Listener
import keyboard

# ------------- GLOBAL STATE -------------
log_lock = threading.Lock()
state_lock = threading.Lock()

running = True               # Global flag to stop all threads
last_mouse_time = time.time()  # For inactivity detection

# Load Haar Cascade for face detection (comes with opencv-python)
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# ------------- LOGGING FUNCTION -------------

def log_event(event):
    with log_lock:
        with open("log.txt", "a", encoding="utf-8", errors="ignore") as f:
            f.write(f"{time.ctime()} - {event}\n")



# ------------- THREAD 1: CAMERA + FACE DETECTION -------------

def video_thread():
    global running
    cap = cv2.VideoCapture(0)
    log_event("Camera monitoring started")

    if not cap.isOpened():
        log_event("ERROR: Could not open camera")
        running = False
        return

    while running:
        ret, frame = cap.read()
        if not ret:
            log_event("ERROR: Failed to read frame from camera")
            break

        # ----- Face detection -----
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        # Draw rectangles around faces
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        face_count = len(faces)
        if face_count == 0:
            log_event("⚠️ No face detected (student left / covered camera?)")
        elif face_count > 1:
            log_event("⚠️ Multiple faces detected (possible cheating)")

        # Display info on screen
        cv2.putText(frame, f"Faces: {face_count}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow("Proctoring - Press Q to Quit", frame)

        # Press Q in this window to stop everything
        if cv2.waitKey(1) & 0xFF == ord('q'):
            running = False
            log_event("Camera stopped by examiner (Q pressed)")
            break

    cap.release()
    cv2.destroyAllWindows()
    log_event("Camera thread exited")


# ------------- THREAD 2: MOUSE MONITORING -------------

def mouse_click(x, y, button, pressed):
    """Callback from pynput when mouse is clicked."""
    global last_mouse_time, running

    if not running:
        return False  # stop listener

    with state_lock:
        last_mouse_time = time.time()

    action = "Pressed" if pressed else "Released"
    log_event(f"Mouse {action} at ({x},{y})")


def mouse_thread():
    log_event("Mouse monitoring started")
    with Listener(on_click=mouse_click) as listener:
        listener.join()
    log_event("Mouse monitoring stopped")


# ------------- THREAD 3: INACTIVITY MONITOR -------------

def inactivity_thread(threshold_seconds=15):
    """
    If no mouse activity for 'threshold_seconds',
    log inactivity as suspicious.
    """
    log_event("Inactivity monitoring started")
    inactive_logged = False

    while running:
        time.sleep(2)
        with state_lock:
            idle_time = time.time() - last_mouse_time

        if idle_time > threshold_seconds and not inactive_logged:
            log_event(f"⚠️ Inactivity detected: no mouse movement for "
                      f"{int(idle_time)} seconds")
            inactive_logged = True
        elif idle_time <= threshold_seconds and inactive_logged:
            log_event("Activity resumed after inactivity")
            inactive_logged = False

    log_event("Inactivity monitoring stopped")


# ------------- THREAD 4: KEYBOARD + TAB-SWITCH MONITOR -------------

def keyboard_monitor_thread():
    """
    Monitors suspicious keyboard shortcuts like:
    ALT+TAB, CTRL+TAB, CTRL+T, CTRL+C/V, WIN, etc.
    These usually indicate tab/window switching or copying.
    """
    log_event("Keyboard & tab monitoring started")

    def on_press(event):
        global running
        if not running:
            return False  # stop hook

        name = event.name

        try:
            # ALT+TAB → switching windows
            if name == 'tab' and keyboard.is_pressed('alt'):
                log_event("⚠️ Window switch attempt detected (ALT+TAB)")

            # CTRL+TAB → switching tabs in browser
            elif name == 'tab' and keyboard.is_pressed('ctrl'):
                log_event("⚠️ Tab switch attempt detected (CTRL+TAB)")

            # CTRL+T → new tab
            elif name == 't' and keyboard.is_pressed('ctrl'):
                log_event("⚠️ New tab attempt detected (CTRL+T)")

            # CTRL+L → focus address bar
            elif name == 'l' and keyboard.is_pressed('ctrl'):
                log_event("⚠️ Address bar focus (CTRL+L) - possible search")

            # CTRL+C / CTRL+V
            elif name == 'c' and keyboard.is_pressed('ctrl'):
                log_event("⚠️ Copy attempt (CTRL+C)")
            elif name == 'v' and keyboard.is_pressed('ctrl'):
                log_event("⚠️ Paste attempt (CTRL+V)")

            # WIN key
            elif name in ('left windows', 'right windows', 'windows'):
                log_event("⚠️ Windows key pressed (start menu)")

        except:
            # keyboard.is_pressed can sometimes throw if device changes
            pass

    keyboard.on_press(on_press)

    # Keep this thread alive till running becomes False
    while running:
        time.sleep(0.1)

    keyboard.unhook_all()
    log_event("Keyboard & tab monitoring stopped")


# ------------- MAIN -------------

def main():
    global running
    running = True

    # Create threads
    t1 = threading.Thread(target=video_thread, name="CameraThread")
    t2 = threading.Thread(target=mouse_thread, name="MouseThread")
    t3 = threading.Thread(target=inactivity_thread, name="InactivityThread")
    t4 = threading.Thread(target=keyboard_monitor_thread,
                          name="KeyboardMonitorThread")

    # Start threads
    t1.start()
    t2.start()
    t3.start()
    t4.start()

    # Wait for camera thread to end (Q pressed)
    t1.join()

    # Signal stop (if not already)
    running = False

    # Wait for others to exit gracefully
    t2.join()
    t3.join()
    t4.join()


if __name__ == "__main__":
    log_event("===== Exam Proctoring Session Started =====")
    main()
    log_event("===== Exam Proctoring Session Ended =====")
