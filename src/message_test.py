import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QMessageBox, QVBoxLayout, QWidget

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Message Box Example")
        self.setGeometry(100, 100, 400, 200)

        # Create a button to show the message box
        self.show_button = QPushButton("Show Message Box")
        self.show_button.clicked.connect(self.show_message_box)

        layout = QVBoxLayout()
        layout.addWidget(self.show_button)
        self.central_widget = QWidget()
        self.central_widget.setLayout(layout)
        self.setCentralWidget(self.central_widget)

    def show_message_box(self):
        msg_box = QMessageBox(self)
        msg_box.frameGeometry()
        msg_box.setText("This is a message without a title.")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

        msg_box.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec())
