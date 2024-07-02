import os
import cv2
import datetime
from PySide6.QtWidgets import QMainWindow, QPushButton, QApplication, QLabel, QWidget, QHBoxLayout
from PySide6.QtCore import QTimer, Signal, Qt, QThread
from PySide6.QtGui import QImage, QPixmap
import shutil
import dlib
import sys


class PredictionThread(QThread):
    output_ready = Signal(str)

    def __init__(self, pipeline=None, parent=None):
        super().__init__(parent)
        self.pipeline = pipeline  # Store the pipeline instance
        self.video_dir = "live_video"
        self.current_video_index = 1
        self.running = False

    def run(self):
        self.running = True
        concatenated_output = ""  # Initialize concatenated output
        while self.running:
            video_path = os.path.join(self.video_dir, f"{self.current_video_index}.mp4")
            if not os.path.exists(video_path):
                print(f"Video file {self.current_video_index}.mp4 not found. Waiting for the next file...")
                QThread.msleep(3000)  # Sleep for 3 seconds without blocking the UI
                continue

            # Perform lip reading on the current video
            output = self.pipeline.forward(video_path)
            print(output)

            # Concatenate the current output to previous outputs
            concatenated_output += output

            # Emit the concatenated output signal
            self.output_ready.emit(concatenated_output)

            # Increment the index for the next video
            self.current_video_index += 1

    def stop(self):
        self.running = False
        self.wait()  # Ensure the thread has fully stopped


class VideoThread(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cap = cv2.VideoCapture(0)
        self.video_save_path = "live_video"
        self.clip_duration = 3
        self.running = False

    def run(self):
        self.running = True
        self.record_video()

    def stop(self):
        self.running = False
        self.wait()  # Ensure the thread has fully stopped

    def record_video(self):
        if not os.path.exists(self.video_save_path):
            os.makedirs(self.video_save_path)

        # Define video recording parameters
        frame_width = 1280
        frame_height = 720
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        out = None
        start_time = None
        file_counter = 1
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                break

            resized_frame = cv2.resize(frame, (frame_width, frame_height))  # Resize the frame to match video dimensions
            if start_time is None or (datetime.datetime.now() - start_time).total_seconds() >= self.clip_duration:
                if out is not None:
                    out.release()
                filename = os.path.join(self.video_save_path, f"{file_counter}.mp4")
                out = cv2.VideoWriter(filename, fourcc, 20.0, (frame_width, frame_height))
                start_time = datetime.datetime.now()
                file_counter += 1
            if out is not None:
                out.write(resized_frame)  # Write the resized frame

        self.cap.release()
        if out is not None:
            out.release()
        cv2.destroyAllWindows()


class RealtimeWindow(QMainWindow):
    back_button_pressed = Signal()

    def __init__(self, pipeline=None):
        super().__init__()
        self.pipeline = pipeline  # Store the pipeline instance
        self.setWindowTitle("Real-time Lip Reading")
        self.resize(1200, 700)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.detector = dlib.get_frontal_face_detector()  # Initialize face detector
        self.predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")  # Initialize landmark predictor

        self.camera_widget = QLabel()
        self.camera_widget.setMinimumSize(900, 700)
        self.camera_widget.setAlignment(Qt.AlignCenter)

        self.predicted_output_widget = QLabel()
        self.predicted_output_widget.setMinimumSize(300, 700)
        self.predicted_output_widget.setAlignment(Qt.AlignCenter)
        self.predicted_output_widget.setWordWrap(True)  # Enable text wrapping

        self.central_layout = QHBoxLayout()
        self.central_layout.addWidget(self.camera_widget)
        self.central_layout.addWidget(self.predicted_output_widget)

        self.central_widget = QWidget()
        self.central_widget.setLayout(self.central_layout)
        self.setCentralWidget(self.central_widget)

        self.back_button = QPushButton("Back", self)
        self.back_button.clicked.connect(self.back_button_clicked)
        self.back_button.move(10, 10)

        self.start_stop_button = QPushButton("Start", self)
        self.start_stop_button.clicked.connect(self.start_stop_button_clicked)
        self.start_stop_button.move(1010, 650)

        self.camera = cv2.VideoCapture(0)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 900)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 700)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.display_frame)

        self.video_thread = VideoThread()

        self.start_camera()

        self.prediction_thread = None  # Initialize prediction thread

    def back_button_clicked(self):
        self.timer.stop()
        self.video_thread.stop()
        if self.prediction_thread is not None:
            self.prediction_thread.stop()
        self.hide()
        self.back_button_pressed.emit()

    def start_stop_button_clicked(self):
        if self.start_stop_button.text() == "Start":
            self.back_button.hide()
            self.start_stop_button.setText("Stop")
            self.predicted_output_widget.setText("")  # Clear the text inside the predicted_output_widget
            self.predicted_output_widget.show()
            self.video_thread.start()
            QTimer.singleShot(4000, self.start_prediction_thread)  # Start the prediction thread after 4 seconds
        else:
            self.back_button.show()
            self.start_stop_button.setText("Start")
            self.predicted_output_widget.hide()
            self.video_thread.stop()
            if self.prediction_thread is not None:
                self.prediction_thread.stop()
            shutil.rmtree('live_video')
            print("Folder deleted")

    def start_prediction_thread(self):
        self.prediction_thread = PredictionThread(self.pipeline)  # Pass the pipeline to the prediction thread
        self.prediction_thread.output_ready.connect(self.update_prediction_output)
        self.prediction_thread.start()

    def start_camera(self):
        self.timer.start(30)

    def display_frame(self):
        ret, frame = self.camera.read()
        if ret:
            # Detect faces in the frame
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.detector(gray_frame)

            # Iterate over detected faces
            for face in faces:
                x1, y1, x2, y2 = face.left(), face.top(), face.right(), face.bottom()

                # Draw rectangle around the face
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Detect landmarks
                landmarks = self.predictor(gray_frame, face)

                # Draw landmarks
                for n in range(0, 68):
                    x = landmarks.part(n).x
                    y = landmarks.part(n).y
                    cv2.circle(frame, (x, y), 1, (255, 0, 0), -1)

            # Convert frame to Qt format and display
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            convert_to_Qt_format = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(convert_to_Qt_format)
            self.camera_widget.setPixmap(pixmap)

    def update_prediction_output(self, output):
        self.predicted_output_widget.setText(output)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RealtimeWindow()
    window.show()
    sys.exit(app.exec())
