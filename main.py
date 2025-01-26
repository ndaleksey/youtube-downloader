#!/usr/bin/env python3
import sys
import os
import logging
from datetime import datetime

# Настраиваем логирование
log_dir = os.path.expanduser('~/.local/share/youtube_downloader/logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'youtube_downloader.log')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

# Перехватываем необработанные исключения
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error("Необработанное исключение:", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

try:
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                QLabel, QLineEdit, QPushButton, QMessageBox,
                                QProgressBar, QComboBox, QHBoxLayout, QDialog)
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
    import yt_dlp
    
    logging.info("Все модули успешно импортированы")
except Exception as e:
    logging.error(f"Ошибка при импорте модулей: {str(e)}", exc_info=True)
    sys.exit(1)

class DownloaderThread(QThread):
    progress = pyqtSignal(float, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    formats_loaded = pyqtSignal(list)

    def __init__(self, url, download_path, selected_format=None):
        super().__init__()
        self.url = url
        self.download_path = download_path
        self.is_cancelled = False
        self.ydl = None
        self.selected_format = selected_format
        self.is_format_check = selected_format is None

    def hook(self, d):
        if self.is_cancelled:
            raise Exception("Загрузка отменена пользователем")
            
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', 0)
            if total:
                percentage = (downloaded / total) * 100
                speed = d.get('speed', 0)
                if speed:
                    speed_mb = speed / 1024 / 1024
                    status = f'Скорость: {speed_mb:.1f} МБ/с'
                else:
                    status = 'Загрузка...'
                self.progress.emit(percentage, status)

    def cancel_download(self):
        self.is_cancelled = True
        if self.ydl:
            self.ydl.cancel_download()

    def get_formats(self):
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                formats = []
                seen_qualities = set()
                
                # Сначала получаем все доступные форматы
                for f in info.get('formats', []):
                    # Проверяем только видео форматы
                    if f.get('vcodec', 'none') != 'none':
                        height = f.get('height', 0)
                        if height and height not in seen_qualities:
                            # Добавляем стандартные разрешения
                            if height in [144, 240, 360, 480, 720, 1080, 1440, 2160, 4320]:
                                seen_qualities.add(height)
                                formats.append(f'{height}p')
                
                # Сортируем форматы по качеству (от высокого к низкому)
                formats.sort(key=lambda x: int(x[:-1]), reverse=True)
                
                if not formats:
                    # Если форматы не найдены, добавляем хотя бы один стандартный
                    formats = ['720p']
                
                return formats
                
        except Exception as e:
            self.error.emit(str(e))
            return ['720p']  # Возвращаем стандартное качество в случае ошибки

    def run(self):
        try:
            if self.is_format_check:
                formats = self.get_formats()
                self.formats_loaded.emit(formats)
                return

            format_height = self.selected_format[:-1]  # Убираем 'p' из строки
            ydl_opts = {
                'format': f'bestvideo[height<={format_height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={format_height}]',
                'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.hook],
                'quiet': True,
                'no_warnings': True,
                'merge_output_format': 'mp4',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
                'prefer_ffmpeg': True,
                'writesubtitles': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.ydl = ydl
                info = ydl.extract_info(self.url, download=False)
                title = info.get('title', 'video')
                
                if not self.is_cancelled:
                    self.progress.emit(0, f"Начинаем загрузку в {self.selected_format}")
                    ydl.download([self.url])
                    self.finished.emit(title)
                
        except Exception as e:
            if self.is_cancelled:
                self.error.emit("Загрузка отменена пользователем")
            else:
                self.error.emit(str(e))
        finally:
            self.ydl = None

class LoadingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Загрузка")
        self.setFixedSize(400, 120)  # Увеличили размер окна
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)  # Добавили отступы
        
        # Добавляем сообщение с переносом текста
        self.message = QLabel("Получение вариантов разрешения\nвидеоролика...")
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setStyleSheet("""
            QLabel {
                font-size: 11pt;
                qproperty-wordWrap: true;
                padding: 10px;
            }
        """)
        layout.addWidget(self.message)
        
        # Добавляем прогресс-бар
        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ccc;
                border-radius: 5px;
                text-align: center;
                height: 20px;
                margin-top: 10px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)  # Бесконечная анимация
        layout.addWidget(self.progress)

class YouTubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Загрузчик")
        self.setFixedSize(600, 300)  # Увеличили высоту для комбобокса
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.url_label = QLabel("Вставьте ссылку на YouTube видео:")
        self.url_label.setStyleSheet("font-size: 12pt;")
        layout.addWidget(self.url_label)
        
        self.url_entry = QLineEdit()
        self.url_entry.setStyleSheet("""
            QLineEdit {
                font-size: 11pt;
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """)
        self.url_entry.textChanged.connect(self.on_url_changed)
        layout.addWidget(self.url_entry)
        
        # Добавляем выбор качества
        quality_layout = QHBoxLayout()
        
        self.quality_label = QLabel("Качество видео:")
        self.quality_label.setStyleSheet("font-size: 11pt;")
        quality_layout.addWidget(self.quality_label)
        
        self.quality_combo = QComboBox()
        self.quality_combo.setStyleSheet("""
            QComboBox {
                font-size: 11pt;
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 4px;
                min-width: 100px;
            }
        """)
        self.quality_combo.setEnabled(False)
        quality_layout.addWidget(self.quality_combo)
        
        layout.addLayout(quality_layout)
        
        self.download_button = QPushButton("Скачать видео")
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 11pt;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.download_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_button.clicked.connect(self.start_download)
        self.download_button.setEnabled(False)
        layout.addWidget(self.download_button)
        
        self.cancel_button = QPushButton("Отменить загрузку")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 11pt;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.hide()
        layout.addWidget(self.cancel_button)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ccc;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 10pt;
                color: #666;
            }
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.hide()
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Добавляем таймер для задержки проверки форматов
        self.url_check_timer = QTimer()
        self.url_check_timer.setSingleShot(True)
        self.url_check_timer.timeout.connect(self.delayed_format_check)
        
        # Добавляем диалог загрузки как атрибут класса
        self.loading_dialog = None

    def on_url_changed(self, url):
        if url.strip():
            # Сбрасываем и запускаем таймер при каждом изменении URL
            self.url_check_timer.stop()
            self.url_check_timer.start(1000)  # 1 секунда задержки
        else:
            self.quality_combo.clear()
            self.quality_combo.setEnabled(False)
            self.download_button.setEnabled(False)

    def delayed_format_check(self):
        url = self.url_entry.text().strip()
        if url:
            self.check_formats(url)

    def check_formats(self, url):
        # Создаем и показываем диалог загрузки
        self.loading_dialog = LoadingDialog(self)
        self.loading_dialog.show()
        
        self.quality_combo.clear()
        self.quality_combo.setEnabled(False)
        self.download_button.setEnabled(False)
        
        self.format_checker = DownloaderThread(url, "", None)
        self.format_checker.formats_loaded.connect(self.on_formats_loaded)
        self.format_checker.error.connect(self.on_format_check_error)
        self.format_checker.start()

    def on_formats_loaded(self, formats):
        # Закрываем диалог загрузки
        if self.loading_dialog:
            self.loading_dialog.close()
            self.loading_dialog = None
        
        if formats:
            self.quality_combo.addItems(formats)
            self.quality_combo.setEnabled(True)
            self.download_button.setEnabled(True)

    def on_format_check_error(self, error):
        # Закрываем диалог загрузки при ошибке
        if self.loading_dialog:
            self.loading_dialog.close()
            self.loading_dialog = None
        
        self.download_error(error)

    def start_download(self):
        url = self.url_entry.text().strip()
        selected_quality = self.quality_combo.currentText()
        
        if not url or not selected_quality:
            QMessageBox.critical(
                self,
                "Ошибка",
                "Пожалуйста, введите ссылку на видео и выберите качество"
            )
            return
        
        downloads_path = os.path.join(os.getcwd(), "Downloads")
        if not os.path.exists(downloads_path):
            os.makedirs(downloads_path)
        
        self.download_button.hide()
        self.cancel_button.show()
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.status_label.show()
        self.status_label.setText("Подготовка к загрузке...")
        
        self.downloader = DownloaderThread(url, downloads_path, selected_quality)
        self.downloader.progress.connect(self.update_progress)
        self.downloader.finished.connect(self.download_finished)
        self.downloader.error.connect(self.download_error)
        self.downloader.start()

    def update_progress(self, percentage, status):
        self.progress_bar.setValue(int(percentage))
        self.status_label.setText(status)

    def cancel_download(self):
        if hasattr(self, 'downloader'):
            self.downloader.cancel_download()
            self.status_label.setText("Отмена загрузки...")
            self.cancel_button.setEnabled(False)
            # Восстанавливаем интерфейс после отмены
            QTimer.singleShot(1000, self.reset_interface)

    def reset_interface(self):
        """Восстановление интерфейса в исходное состояние"""
        self.cancel_button.hide()
        self.cancel_button.setEnabled(True)
        self.download_button.show()
        self.progress_bar.hide()
        self.status_label.hide()
        self.quality_combo.setEnabled(True)
        
        # Если URL все еще присутствует, активируем кнопку загрузки
        if self.url_entry.text().strip():
            self.download_button.setEnabled(True)

    def download_error(self, error_message):
        self.reset_interface()  # Используем общий метод для сброса интерфейса
        
        if "Загрузка отменена пользователем" in error_message:
            QMessageBox.information(
                self,
                "Отмена",
                "Загрузка была отменена"
            )
            return
            
        if "Private video" in error_message:
            error_message = "Видео является приватным"
        elif "not available" in error_message:
            error_message = "Видео недоступно"
        elif "age-restricted" in error_message:
            error_message = "Видео имеет возрастные ограничения"
        
        QMessageBox.critical(
            self,
            "Ошибка",
            f"Произошла ошибка при скачивании: {error_message}"
        )

    def download_finished(self, title):
        self.progress_bar.setValue(100)
        self.status_label.setText("Загрузка завершена!")
        self.reset_interface()  # Используем общий метод для сброса интерфейса
        self.url_entry.clear()  # Очищаем поле ввода URL
        
        QMessageBox.information(
            self,
            "Успех",
            f"Видео '{title}' успешно скачано в папку Downloads!"
        )

if __name__ == "__main__":
    try:
        logging.info("Запуск приложения")
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        window = YouTubeDownloader()
        window.show()
        logging.info("Окно приложения создано и отображено")
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"Ошибка при запуске приложения: {str(e)}", exc_info=True)
        sys.exit(1) 