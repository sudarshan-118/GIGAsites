import cv2
import threading
import time
from pynput.mouse import Listener

log_lock = threading.Lock()

def log_event(event):
    with log_lock:
        with open("log.txt", "a") as f:
            f.write(f"{time.ctime()} - {event}\n")

def video_thread():
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if ret:
            cv2.imshow("Proctoring Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            log_event("Camera stopped")
            break
    cap.release()
    cv2.destroyAllWindows()

def mouse_thread_click(x, y, button, pressed):
    action = "Pressed" if pressed else "Released"
    log_event(f"Mouse {action} at {x},{y}")

def start_mouse_monitor():
    with Listener(on_click=mouse_thread_click) as listener:
        listener.join()

def main():
    t1 = threading.Thread(target=video_thread)
    t2 = threading.Thread(target=start_mouse_monitor)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

if __name__ == "__main__":
    main()
