import threading
import webview
import os

def start_django():
    os.system("python manage.py runserver 127.0.0.1:8000")

if __name__ == '__main__':
    t = threading.Thread(target=start_django)
    t.daemon = True
    t.start()

    webview.create_window("OptiTime", "http://127.0.0.1:8000")
    webview.start()