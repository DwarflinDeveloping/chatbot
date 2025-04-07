import threading
import time
from pynput import keyboard, keyboard as kb
import pyautogui

running = False

def type_hello():
    global running
    count = 1
    while True:
        if running:
            pyautogui.typewrite(f'DE \'{count}\n')
            count += 1
            time.sleep(6.25)
        else:
            time.sleep(0.1)

def toggle_typing(key):
    global running
    if key == keyboard.Key.f8:
        running = not running
        print("Typing started" if running else "Typing stopped")

# Start the typing thread
typing_thread = threading.Thread(target=type_hello, daemon=True)
typing_thread.start()

# Listen for the F8 key
with keyboard.Listener(on_press=toggle_typing) as listener:
    listener.join()
