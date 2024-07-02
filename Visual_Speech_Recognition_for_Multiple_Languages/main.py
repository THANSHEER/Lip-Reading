import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt
from recorded import RecordedWindow
from realtime import RealtimeWindow
from inference import InferencePipeline  # Import your InferencePipeline class


class MyWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lip Reading")
        self.resize(1200, 700)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)  # Set frameless window
        self.initUI()
        self.load_model()  # Load the model and create inference pipeline

    def initUI(self):
        main_layout = QVBoxLayout()

        # Background color
        background = QColor("#F7F6BB")
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), background)
        self.setPalette(p)

        # Title Label
        title_label = QLabel("<b>Lip Reading</b>")
        title_label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        title_label.setFont(QFont("Arial", 48, QFont.Bold))
        title_label.setStyleSheet("color: #87A922; "
                                  "border: 2px solid #FCDC2A; "
                                  "border-radius: 10px; "
                                  "padding: 30px 10px; "
                                  "margin: 15px 15px 300px 15px;")
        main_layout.addWidget(title_label)

        # Button layout
        button_layout = QHBoxLayout()

        # Button for Recorded Video
        self.button_recorded = QPushButton("Recorded Video", self)
        self.button_recorded.setFont(QFont("Arial", 36, QFont.Bold))
        self.button_recorded.clicked.connect(self.open_recorded_window)
        self.button_recorded.setStyleSheet("""
                              QPushButton{
                              text-align: center;
                              color: #87A922;
                              border: 2px solid #FCDC2A;
                              border-radius: 10px;
                              padding: 15px 20px;
                              }
                              QPushButton:hover {
                                color: #114232;
                                border: 2px solid #00F12A;
                                }
                              """)
        button_layout.addWidget(self.button_recorded)

        # Button for Real-Time
        self.button_realtime = QPushButton("Real-Time", self)
        self.button_realtime.setFont(QFont("Arial", 36, QFont.Bold))
        self.button_realtime.clicked.connect(self.open_realtime_window)  # Connect the signal
        self.button_realtime.setStyleSheet("""
                                          QPushButton{
                                          text-align: center;
                                          color: #87A922;
                                          border: 2px solid #FCDC2A;
                                          border-radius: 10px;
                                          padding: 15px 20px;
                                          }
                                          QPushButton:hover {
                                            color: #114232;
                                            border: 2px solid #00F12A;
                                            }
                                          """)
        button_layout.addWidget(self.button_realtime)

        main_layout.addLayout(button_layout)

        # Quit Button
        quit_button = QPushButton("Quit")
        quit_button.clicked.connect(self.clear_resources_and_close)
        quit_button.setStyleSheet("""
                      QPushButton{
                     	  color: #87A922;
                          border: 2px solid #FCDC2A;
                          border-radius: 10px;
                          padding: 20px

                      }
                      QPushButton:hover {
                        color: #114232;
                        border: 2px solid #00F12A;
                        }
                      """)
        quit_button.setFont(QFont("Arial", 18, QFont.Bold))
        main_layout.addWidget(quit_button)

        self.setLayout(main_layout)

    def open_recorded_window(self):
        self.recorded_window = RecordedWindow(self.pipeline)  # Pass the pipeline to the recorded window
        self.recorded_window.back_button_pressed.connect(self.show_main_window)  # Connect the signal
        self.recorded_window.show()
        self.hide()
        print("recorded window opened")

    def open_realtime_window(self):
        self.realtime_window = RealtimeWindow(self.pipeline)  # Pass the pipeline to the realtime window
        self.realtime_window.back_button_pressed.connect(self.show_main_window)  # Connect the signal
        self.realtime_window.show()
        self.hide()
        print("real time window opened")

    def show_main_window(self):
        self.show()

    def load_model(self):
        # Load model and create inference pipeline
        modality = "video"
        model_conf = "LRS3_V_WER19.1/model.json"
        model_path = "LRS3_V_WER19.1/model.pth"
        self.pipeline = InferencePipeline(modality, model_path, model_conf, face_track=True, device='cpu')
        print("model & function loaded")

    def clear_resources_and_close(self):
        # Clear resources stored in memory
        # For example, close any open files or release any resources used by the pipeline
        del self.pipeline  # Delete the pipeline object
        self.close()  # Close the application
        print("All resources cleared")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec())

