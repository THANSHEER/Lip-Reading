import os
import cv2
import sys
import shutil
import subprocess
from PySide6.QtCore import Signal, Qt, QFileInfo, QTimer, QThread
from PySide6.QtWidgets import QMainWindow, QPushButton, QFileDialog, QApplication, QLabel, QMessageBox, QTextEdit
from PySide6.QtGui import QImage, QPixmap, QFont, QColor, QTextCursor
from gtts import gTTS

class VideoDisplayThread(QThread):
    frame_ready = Signal(QImage)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        cap = cv2.VideoCapture(self.file_path)
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.frame_ready.emit(qt_image)


class RecordedWindow(QMainWindow):
    back_button_pressed = Signal()  # Define a custom signal

    def __init__(self, pipeline):  # Accept pipeline as a parameter
        super().__init__()
        self.pipeline = pipeline  # Store the pipeline instance
        self.initUI()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)  # Set frameless window
        self.cap = None  # Video capture object
        self.playing = False  # Flag to track video playing state
        self.audio_playing = False  # Flag to track audio playing state
        self.video_timer = QTimer(self)  # Add a QTimer for video playback
        self.video_timer.timeout.connect(self.next_frame)

    def initUI(self):

        # Background color
        background = QColor("#F7F6BB")
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), background)
        self.setPalette(p)

        # Back Button
        self.back_button = QPushButton('Back', self)
        self.back_button.setGeometry(10, 10, 75, 30)
        self.back_button.clicked.connect(self.back_button_clicked)
        self.back_button.setStyleSheet("""
                                              QPushButton{
                                              text-align: center;
                                              color: #87A922;
                                              border: 2px solid #FCDC2A;
                                              border-radius: 5px;
                                              padding: 5px 5px;
                                              font-weight: bold;
                                              }
                                              QPushButton:hover {
                                                color: #114232;
                                                }
                                              """)

        # Choose File Button
        self.choose_file_button = QPushButton(self)
        self.choose_file_button.setGeometry(250, 160, 200, 30)
        self.choose_file_button.setText('Choose File[mp4, mpg, mov[only][less than 200MB]')
        self.choose_file_button.clicked.connect(self.choose_file)
        self.choose_file_button.move(410, 80)  # Move the choose file  button to the bottom middle
        self.choose_file_button.setStyleSheet("""
                                      QPushButton{
                                      text-align: center;
                                      color: #87A922;
                                      border: 2px solid #FCDC2A;
                                      border-radius: 5px;
                                      padding: 5px 5px;
                                      font-weight: bold;
                                      min-width: 400px;
                                      min-height: 30px;
                                      }
                                      QPushButton:hover {
                                        color: #114232;
                                        }
                                      """)


        # Label for dropping files
        self.drop_label = QLabel("", self)
        self.drop_label.setGeometry(150, 100, 300, 30)
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setFont(QFont("Arial", 16))

        # Video display label
        self.video_label = QLabel(self)
        self.video_label.setGeometry(100, 150, 1000, 400)
        self.video_label.setAlignment(Qt.AlignCenter)

        # Play/Pause Button
        self.play_pause_button = QPushButton("Play", self)
        self.play_pause_button.setGeometry(200, 570, 75, 30)
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.play_pause_button.setStyleSheet("""
                                          QPushButton{
                                          color: black;
                                          }
                                      """)
        self.play_pause_button.hide()  # Initially hide the Play/Pause button

        # Forward Button
        self.forward_button = QPushButton("Forward", self)
        self.forward_button.setGeometry(300, 570, 75, 30)
        self.forward_button.clicked.connect(self.forward_video)
        self.forward_button.setStyleSheet("""
                                          QPushButton{
                                          color: black;
                                          }
                                      """)
        self.forward_button.hide()  # Initially hide the Forward button

        # Reverse Button
        self.reverse_button = QPushButton("Reverse", self)
        self.reverse_button.setGeometry(100, 570, 75, 30)
        self.reverse_button.clicked.connect(self.reverse_video)
        self.reverse_button.setStyleSheet("""
                                          QPushButton{
                                          color: black;
                                          }
                                      """)
        self.reverse_button.hide()  # Initially hide the Reverse button

        # Add the QTextEdit widget to the initUI method of the RecordedWindow class
        self.text_edit = QTextEdit(self)
        self.text_edit.setGeometry(700, 150, 300, 400)  # Adjust the position and size as needed
        self.text_edit.setReadOnly(True)  # Make it read-only to prevent user input
        self.text_edit.hide()  # Initially hide the text edit field

        # Play/Mute Audio Toggle Button
        self.audio_button = QPushButton("Play Audio", self)
        self.audio_button.setGeometry(400, 570, 75, 30)
        self.audio_button.clicked.connect(self.toggle_audio)
        self.audio_button.setStyleSheet("""
                    QPushButton{
                        color: black;
                    }
                """)
        self.audio_button.hide()

        # Allow dropping files onto the window
        self.setAcceptDrops(True)

        # Set fixed window size
        self.setFixedSize(1200, 700)

    # back button function
    def back_button_clicked(self):
        self.hide()
        self.back_button_pressed.emit()  # Emit the signal when back button is clicked
        print("Back Button Clicked")

    # Inside your class where you handle the typing effect
    def type_text(self):
        if self.transcript_index < len(self.transcript):
            # Get the next character to display
            char_to_display = self.transcript[self.transcript_index]
            # Insert the character at the end of the current line
            self.text_edit.insertPlainText(char_to_display)
            # Increment the index for the next character
            self.transcript_index += 1
        else:
            # Stop the timer if all characters are displayed
            self.typing_timer.stop()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()  # Accept the event
            self.drop_label.setText("Drop here")  # Update label text to indicate drop is accepted
        else:
            event.ignore()  # Ignore the event if it doesn't contain file URLs

    def dragLeaveEvent(self, event):
        self.drop_label.setText("Drop video file here")  # Reset label text

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            print("Dropped file:", file_path)
            # Stop the video timer if a video is already playing
            self.video_timer.stop()
            # Display video content
            self.display_video(file_path)
            # Show control buttons
            self.play_pause_button.show()
            self.forward_button.show()
            self.reverse_button.show()
            self.drop_label.hide()  # Hide the drop label
            self.text_edit.show()  # Show the text edit field
            self.text_edit.clear()

            duration = float(subprocess.check_output(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of',
                 'default=noprint_wrappers=1:nokey=1', file_path]))
            print(duration)

            if duration < 8:
                transcript = self.pipeline.forward(file_path)
                self.transcript = transcript
                self.transcript_index = 0
                self.typing_timer = QTimer(self)
                self.typing_timer.timeout.connect(self.type_text)
                self.typing_timer.start(25)  # Adjust the typing speed as needed
                print("Transcript displayed in the GUI")
                self.audio_button.show()
                return

            else:
                shutil.rmtree('partition_video')
                print("Folder deleted")
                self.partition_video(file_path)
                print("completed partition")
                folder_path = "partition_video"

                # List all files in the directory
                files = sorted(os.listdir(folder_path))

                for filename in files:
                    if filename.endswith(".mp4"):
                        file_path = os.path.join(folder_path, filename)  # Join directory path with filename
                        print(file_path)
                        transcript = self.pipeline.forward(file_path)
                        print(transcript)
                        # Display the predicted transcript
                        self.predicted_output_display(transcript)
                        self.audio_button.show()

    def toggle_play_pause(self):
        self.playing = not self.playing
        if self.playing:
            self.play_pause_button.setText("Pause")
            self.video_timer.start(1000 // 30)  # Update every 33ms for approximately 30 FPS
        else:
            self.play_pause_button.setText("Play")
            self.video_timer.stop()

    def forward_video(self):
        if self.cap is not None:
            current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            new_frame = min(current_frame + 10, self.total_frames)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)
            self.next_frame()  # Display the new frame

    def reverse_video(self):
        if self.cap is not None:
            current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            new_frame = max(current_frame - 10, 0)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)
            self.next_frame()  # Display the new frame

    def next_frame(self):
        if self.cap is not None:
            ret, frame = self.cap.read()
            if ret:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                self.update_frame(qt_image)
            else:
                # Loop the video by setting the frame position to the beginning
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.next_frame()  # Recursively call to display the first frame

    def choose_file(self):
        self.text_edit.setPlainText("")  # Clear previous text
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("Video files (*.mp4 *.mpg *.mov)")
        file_dialog.setDirectory('.')
        file_dialog.setOption(QFileDialog.DontUseNativeDialog, True)  # Use PySide6 dialog instead of native dialog
        if file_dialog.exec_():
            file_paths = file_dialog.selectedFiles()
            file_path = file_paths[0]  # Assignment of file_path
            print("Selected file:", file_path)
            # Check file extension
            allowed_extensions = ['.mp4', '.mpg', '.mov']
            if not any(file_path.lower().endswith(ext) for ext in allowed_extensions):
                print("File format not supported. Please select a video file with .mp4, .mpg, or .mov extension.")
                return
            # Check file size
            file_size = QFileInfo(file_path).size()  # Use QFileInfo from PySide6.QtCore
            if file_size > 200 * 1024 * 1024:  # 200MB in bytes
                # Display pop-up window for file size exceeded
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setText("File size exceeds the limit (200MB)")
                msg.setWindowTitle("File Size Exceeded")
                msg.exec_()
                print("file is selected")
                return
            # Stop the video timer if a video is already playing
            self.video_timer.stop()
            # Display video content
            self.display_video(file_path)
            print("Video is displayed")
            # Show control buttons
            self.play_pause_button.show()
            self.forward_button.show()
            self.reverse_button.show()
            self.drop_label.hide()  # Hide the drop label

            self.text_edit.show()  # Show the text edit field
            self.text_edit.clear()
            duration = float(subprocess.check_output(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of',
                 'default=noprint_wrappers=1:nokey=1', file_path]))
            print(duration)

            if duration < 20:
                transcript = self.pipeline.forward(file_path)
                self.transcript = transcript
                self.transcript_index = 0
                self.typing_timer = QTimer(self)
                self.typing_timer.timeout.connect(self.type_text)
                self.typing_timer.start(25)  # Adjust the typing speed as needed
                print("Transcript displayed in the GUI")
                self.audio_button.show()
                return

            else:
                shutil.rmtree('partition_video')
                self.partition_video(file_path)
                print("completed partition")
                folder_path = "partition_video"

                # List all files in the directory
                files = sorted(os.listdir(folder_path))

                for filename in files:
                    if filename.endswith(".mp4"):
                        file_path = os.path.join(folder_path, filename)  # Join directory path with filename
                        # print(file_path)
                        transcript = self.pipeline.forward(file_path)
                        # print(transcript)
                        # Display the predicted transcript
                        self.predicted_output_display(transcript)
            # time.sleep(1)
            self.audio_button.show()
        else:
            print("No file selected")  # Handle the case where no file is selected by the user

    def display_video(self, file_path):
        if self.cap is not None:
            self.cap.release()
        self.cap = cv2.VideoCapture(file_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.next_frame()  # Display the first frame
        self.playing = False
        self.play_pause_button.setText("Play")
        # Set the geometry of the video label to position it within the window
        video_width = 600  # Adjust width as needed
        video_height = 400  # Adjust height as needed
        video_x = 50  # Adjust the x-coordinate to position on the left side
        video_y = 150  # Adjust the vertical position as needed
        self.video_label.setGeometry(video_x, video_y, video_width, video_height)

    def update_frame(self, qt_image):
        pixmap = QPixmap.fromImage(qt_image)
        self.video_label.setPixmap(pixmap)

    def predicted_output_display(self, transcript):
        print("Transcript in the GUI")
        self.transcript = transcript
        self.transcript_index = 0
        self.typing_timer = QTimer(self)
        self.typing_timer.timeout.connect(self.type_text)
        self.typing_timer.start(25)  # Adjust the typing speed as needed

    def partition_video(self, video_path):
        if not os.path.exists('partition_video'):
            os.makedirs('partition_video')
        else:
            shutil.rmtree('partition_video')  # Delete the folder and its contents
            os.makedirs('partition_video')  # Create a new empty folder

        output_dir = 'partition_video'
        command = [
            'ffmpeg',
            '-i', video_path,
            '-c', 'copy',
            '-map', '0',
            '-segment_time', '8',
            '-f', 'segment',
            '-reset_timestamps', '1',
            os.path.join(output_dir, 'output%03d.mp4')
        ]
        subprocess.run(command)

    def toggle_audio(self):
        self.audio_playing = not self.audio_playing
        if self.audio_playing:
            self.audio_button.setText("Mute Audio")
            self.play_audio(self.transcript)  # Play the transcript as audio
        else:
            self.audio_button.setText("Play Audio")
            # Code to stop the audio (if applicable)

    def play_audio(self, text):
        tts = gTTS(text=text, lang='en')
        audio_path = 'temp_audio.mp3'
        tts.save(audio_path)
        # Play the audio file
        subprocess.run(['ffplay', '-nodisp', '-autoexit', audio_path])


if __name__ == "__main__":
    class DummyPipeline:
        def forward(self, file_path):
            # Dummy implementation, replace with your actual pipeline logic
            return "This is a dummy transcript for the video."

    app = QApplication(sys.argv)
    window = RecordedWindow(DummyPipeline())
    window.show()
    sys.exit(app.exec())
