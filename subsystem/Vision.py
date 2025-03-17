import cv2

class Vision:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)

    def get_frame(self):
        return self.cap.read()
    
    def close(self):
        self.cap.release()

    def __del__(self):
        self.close()

    def serve_feed(self):
        while True:
            ret, frame = self.get_frame()
            if not ret:
                break
            cv2.imshow('frame', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        self.close()
