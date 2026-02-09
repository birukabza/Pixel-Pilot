from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QMessageBox, QTextEdit)
from PySide6.QtCore import Qt, QThread, Signal
import asyncio
from backend_client import backend_client

class LoginDialog(QDialog):
    """Login dialog for backend authentication"""
    
    login_success = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PixelPilot - Login")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Login to PixelPilot Backend")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Email field
        email_layout = QHBoxLayout()
        email_label = QLabel("Email:")
        email_label.setFixedWidth(80)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        layout.addLayout(email_layout)
        
        # Password field
        password_layout = QHBoxLayout()
        password_label = QLabel("Password:")
        password_label.setFixedWidth(80)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter your password")
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: red; margin: 10px;")
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.register_button = QPushButton("Register")
        self.register_button.clicked.connect(self.register)
        
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.login)
        self.login_button.setDefault(True)
        
        button_layout.addWidget(self.register_button)
        button_layout.addWidget(self.login_button)
        layout.addLayout(button_layout)
        
        # Info text
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(80)
        info_text.setPlainText("New user? Click Register to create an account. "
                            "The backend server must be running at localhost:8000")
        info_text.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(info_text)
        
        self.setLayout(layout)
    
    def login(self):
        """Handle login"""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        
        if not email or not password:
            self.status_label.setText("Please enter email and password")
            return
        
        # Disable buttons during login
        self.login_button.setEnabled(False)
        self.register_button.setEnabled(False)
        self.status_label.setText("Logging in...")
        
        # Create login worker thread
        self.login_thread = LoginThread(email, password)
        self.login_thread.result.connect(self.on_login_result)
        self.login_thread.start()
    
    def register(self):
        """Handle registration"""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        
        if not email or not password:
            self.status_label.setText("Please enter email and password")
            return
        
        # Disable buttons during registration
        self.login_button.setEnabled(False)
        self.register_button.setEnabled(False)
        self.status_label.setText("Registering...")
        
        # Create registration worker thread
        self.register_thread = RegisterThread(email, password)
        self.register_thread.result.connect(self.on_register_result)
        self.register_thread.start()
    
    def on_login_result(self, success, message):
        """Handle login result"""
        self.login_button.setEnabled(True)
        self.register_button.setEnabled(True)
        
        if success:
            self.status_label.setText("Login successful!")
            self.login_success.emit()
            self.accept()
        else:
            self.status_label.setText(f"Login failed: {message}")
    
    def on_register_result(self, success, message):
        """Handle registration result"""
        self.login_button.setEnabled(True)
        self.register_button.setEnabled(True)
        
        if success:
            self.status_label.setText("Registration successful! You can now login.")
            # Clear password field for login
            self.password_input.clear()
        else:
            self.status_label.setText(f"Registration failed: {message}")


class LoginThread(QThread):
    """Worker thread for login"""
    result = Signal(bool, str)
    
    def __init__(self, email, password):
        super().__init__()
        self.email = email
        self.password = password
    
    def run(self):
        """Run login in background thread"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(backend_client.login(self.email, self.password))
            if success:
                self.result.emit(True, "Login successful")
            else:
                self.result.emit(False, "Invalid email or password")
        except Exception as e:
            self.result.emit(False, str(e))
        finally:
            loop.close()


class RegisterThread(QThread):
    """Worker thread for registration"""
    result = Signal(bool, str)
    
    def __init__(self, email, password):
        super().__init__()
        self.email = email
        self.password = password
    
    def run(self):
        """Run registration in background thread"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(backend_client.register(self.email, self.password))
            if success:
                self.result.emit(True, "Registration successful")
            else:
                self.result.emit(False, "Registration failed")
        except Exception as e:
            self.result.emit(False, str(e))
        finally:
            loop.close()


def show_login_dialog(parent=None):
    """Show login dialog and return result"""
    dialog = LoginDialog(parent)
    return dialog.exec_()