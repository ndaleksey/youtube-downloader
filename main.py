#!/usr/bin/env python3
import sys
import os
import logging
from datetime import datetime
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QUrl, QTimer, QThread, QResource
from PyQt6.QtWidgets import QApplication
import re
import yt_dlp
from PyQt6.QtGui import QGuiApplication, QIcon

# Настраиваем логирование
script_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(script_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'youtube_downloader.log')

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
    logging.info("Все модули успешно импортированы")
except Exception as e:
    logging.error(f"Ошибка при импорте модулей: {str(e)}", exc_info=True)
    sys.exit(1)

class DownloadThread(QThread):
    """Отдельный класс для потока загрузки"""
    progress_signal = pyqtSignal(dict)  # Сигнал для передачи прогресса

    def __init__(self, url, opts, parent=None):
        super().__init__(parent)
        self.url = url
        self.opts = opts
        self.is_cancelled = False

    def run(self):
        try:
            def progress_hook(d):
                if self.is_cancelled:
                    raise Exception("Download cancelled")
                self.progress_signal.emit(d)

            # Добавляем обработчик для существующих файлов
            def already_downloaded_hook(info_dict):
                # Всегда разрешаем перезапись
                return True

            self.opts['progress_hooks'] = [progress_hook]
            self.opts['overwrites'] = True  # Разрешаем перезапись
            self.opts['nooverwrites'] = False  # Отключаем защиту от перезаписи
            self.opts['force_overwrites'] = True  # Принудительная перезапись
            self.opts['already_downloaded_hook'] = already_downloaded_hook
            
            with yt_dlp.YoutubeDL(self.opts) as ydl:
                ydl.download([self.url])
        except Exception as e:
            logging.error(f"Ошибка в потоке загрузки: {str(e)}", exc_info=True)

    def cancel(self):
        self.is_cancelled = True

class Backend(QObject):
    progressChanged = pyqtSignal(float, float, str)  # percent, mbValue, speed
    downloadFinished = pyqtSignal(str)
    downloadError = pyqtSignal(str)
    formatsLoaded = pyqtSignal(list)
    loadingStarted = pyqtSignal()
    loadingFinished = pyqtSignal()
    downloadStarted = pyqtSignal()
    urlValidationError = pyqtSignal(str)  # Новый сигнал для ошибок валидации

    def __init__(self):
        super().__init__()
        self.download_thread = None
        
        # Создаем папку Downloads в директории приложения
        self.download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Downloads')
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)
            logging.info(f"Создана папка для загрузок: {self.download_path}")

        # Регулярное выражение для проверки YouTube URL
        self.youtube_regex = r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[a-zA-Z0-9_-]{11}.*$'

    def validate_youtube_url(self, url):
        if not re.match(self.youtube_regex, url):
            return False
        return True

    @pyqtSlot(str)
    def startDownload(self, url):
        try:
            if self.download_thread and self.download_thread.isRunning():
                logging.info("Отмена текущей загрузки")
                self.download_thread.cancel()
                self.download_thread.wait()
                return

            logging.info(f"Начало загрузки видео: {url}")
            self.downloadStarted.emit()
            
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'nocheckcertificate': True,
                'ignoreerrors': False,
                'no_warnings': False,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                },
                'socket_timeout': 10,
                'legacy_server_connect': True,
                'quiet': False,
                'no_color': True,
                'noprogress': False,
                'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
                'overwrites': True,  # Разрешаем перезапись
                'nooverwrites': False,  # Отключаем защиту от перезаписи
                'force_overwrites': True,  # Принудительная перезапись
            }
            
            self.download_thread = DownloadThread(url, ydl_opts, self)
            self.download_thread.progress_signal.connect(self._progress_hook)
            self.download_thread.start()

        except Exception as e:
            self.downloadError.emit(str(e))
            logging.error(f"Ошибка при скачивании: {str(e)}", exc_info=True)

    @pyqtSlot(str)
    def checkFormats(self, url):
        if not self.validate_youtube_url(url):
            self.urlValidationError.emit("Некорректная ссылка на YouTube видео")
            return

        try:
            self.loadingStarted.emit()
            logging.info(f"Получение форматов для URL: {url}")
            
            ydl_opts = {
                'quiet': True,
                'nocheckcertificate': True,
                'ignoreerrors': False,
                'no_warnings': False,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                },
                'socket_timeout': 10,
                'legacy_server_connect': True
            }

            # Создаем отдельный поток для получения форматов
            class FormatCheckThread(QThread):
                formatsReady = pyqtSignal(list)
                error = pyqtSignal(str)

                def __init__(self, url, opts):
                    super().__init__()
                    self.url = url
                    self.opts = opts

                def run(self):
                    try:
                        with yt_dlp.YoutubeDL(self.opts) as ydl:
                            info = ydl.extract_info(self.url, download=False)
                            formats = []
                            for f in info['formats']:
                                if 'height' in f and f['height'] is not None and 'ext' in f:
                                    format_str = f"{f['height']}p ({f['ext']})"
                                    formats.append(format_str)
                            
                            formats = sorted(list(set(formats)), 
                                          key=lambda x: int(x.split('p')[0]), 
                                          reverse=True)
                            self.formatsReady.emit(formats)
                    except Exception as e:
                        self.error.emit(str(e))

            # Создаем и настраиваем поток
            self.format_thread = FormatCheckThread(url, ydl_opts)
            self.format_thread.formatsReady.connect(self._on_formats_ready)
            self.format_thread.error.connect(self._on_format_check_error)
            self.format_thread.start()

        except Exception as e:
            self.downloadError.emit(str(e))
            self.loadingFinished.emit()
            logging.error(f"Ошибка при получении форматов: {str(e)}", exc_info=True)

    def _on_formats_ready(self, formats):
        logging.info(f"Найдены форматы: {formats}")
        self.formatsLoaded.emit(formats)
        self.loadingFinished.emit()

    def _on_format_check_error(self, error):
        self.downloadError.emit(error)
        self.loadingFinished.emit()

    def _progress_hook(self, d):
        try:
            if d['status'] == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 0)
                
                if total == 0:
                    total = d.get('total_bytes_estimate', 0)

                # Форматируем размер в МБ
                downloaded_mb = round(downloaded / 1024 / 1024, 1)
                total_mb = round(total / 1024 / 1024, 1) if total > 0 else 0

                # Вычисляем процент для прогресс-бара
                progress_percent = (downloaded / total * 100) if total > 0 else 0
                
                # Форматируем скорость
                speed = d.get('speed', 0)
                if speed:
                    speed_str = f"Скорость: {speed/1024/1024:.1f} МБ/с"
                else:
                    speed_str = "Вычисление скорости..."

                # Отправляем процент и значение в МБ как float, и скорость как str
                self.progressChanged.emit(float(progress_percent), float(downloaded_mb), speed_str)
            
            elif d['status'] == 'finished':
                filename = d.get('filename', 'Загрузка завершена')
                filename = os.path.basename(filename)
                logging.info(f"Загрузка завершена: {filename}")
                self.downloadFinished.emit(filename)

        except Exception as e:
            logging.error(f"Ошибка в progress_hook: {str(e)}", exc_info=True)
            self.downloadError.emit(str(e))

def main():
    app = QGuiApplication(sys.argv)
    
    # Устанавливаем иконку приложения
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons', 'app.svg')
    app.setWindowIcon(QIcon(icon_path))
    
    # Создаем экземпляр backend и регистрируем его в контексте QML
    backend = Backend()
    
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    
    # Получаем абсолютный путь к директории проекта
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Добавляем путь к папке с QML файлами в движок
    engine.addImportPath(current_dir)
    
    # Загружаем основной QML файл
    qml_file = os.path.join(current_dir, 'main.qml')
    engine.load(QUrl.fromLocalFile(qml_file))
    
    if not engine.rootObjects():
        logging.error("Ошибка загрузки QML файла")
        sys.exit(-1)
        
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 