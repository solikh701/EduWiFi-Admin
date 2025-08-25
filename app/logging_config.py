import os
import time
import gzip
import logging
from logging.handlers import TimedRotatingFileHandler

LOG_DIR  = r"D:/Abusolih/WIFI-ADMIN/app/logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
os.makedirs(LOG_DIR, exist_ok=True)

# --- yordamchi retry funksiyalar
def _replace_with_retry(src, dst, attempts=10, sleep=0.2):
    for _ in range(attempts):
        try:
            # Windows-da bor fayl ustidan yozadi
            os.replace(src, dst)
            return True
        except PermissionError:
            time.sleep(sleep)
        except FileNotFoundError:
            return False
    return False

def _remove_with_retry(path, attempts=10, sleep=0.2):
    for _ in range(attempts):
        try:
            if os.path.exists(path):
                os.remove(path)
            return True
        except PermissionError:
            time.sleep(sleep)
    return False

def _gzip_with_retry(src, dst, attempts=10, sleep=0.2):
    for _ in range(attempts):
        try:
            with open(src, "rb") as s, gzip.open(dst, "wb") as d:
                for chunk in iter(lambda: s.read(1024 * 64), b""):
                    d.write(chunk)
            return True
        except PermissionError:
            time.sleep(sleep)
    return False


class WinSafeDailyCompressingHandler(TimedRotatingFileHandler):
    """
    Kundalik rotation (when='midnight') + .N.gz backup, Windows-friendly.
    """
    def __init__(self, filename, when="midnight", interval=1,
                 backupCount=10, encoding="utf-8", utc=False, delay=True):
        super().__init__(filename, when, interval,
                         backupCount, encoding=encoding, utc=utc, delay=delay)

    def doRollover(self):
        # multi-thread xavfsizligi
        with self.lock:
            # 1) Ochiq streamni yopamiz
            if self.stream:
                try:
                    self.stream.flush()
                except Exception:
                    pass
                try:
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None

            # 2) Eski .gz backuplarni orqaga siljitamiz (N-1 -> N ...)
            if self.backupCount > 0:
                for i in range(self.backupCount - 1, 0, -1):
                    s = f"{self.baseFilename}.{i}.gz"
                    d = f"{self.baseFilename}.{i+1}.gz"
                    if os.path.exists(s):
                        _replace_with_retry(s, d)

            # 3) app.log -> app.log.1
            dfn = f"{self.baseFilename}.1"
            # agar .1 allaqachon bo'lsa, keyin o'chiramiz (yoki replace uni bosadi)
            _remove_with_retry(dfn)  # ehtiyot chorasi
            _replace_with_retry(self.baseFilename, dfn)

            # 4) .1 ni .1.gz ga siqamiz va .1 ni o'chiramiz
            if os.path.exists(dfn):
                _gzip_with_retry(dfn, f"{dfn}.gz")
                _remove_with_retry(dfn)

            # 5) Streamni qayta ochamiz
            self.mode = 'a'
            self.stream = self._open()

            # 6) Keyingi rollover vaqtini hisoblaymiz
            currentTime = int(time.time())
            self.rolloverAt = self.computeRollover(currentTime)


def configure_logging():
    """
    Root loggerni sozlaydi. Bir dona File handler + Console handler.
    Werkzeug loglari root’ga propagate bo‘ladi (double yozuv yo‘q).
    """
    fmt = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    file_handler = WinSafeDailyCompressingHandler(
        LOG_FILE, when="midnight", interval=1, backupCount=10,
        encoding="utf-8", utc=False, delay=True
    )
    file_handler.setFormatter(logging.Formatter(fmt, datefmt))
    file_handler.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(fmt, datefmt))
    console.setLevel(logging.INFO)

    root = logging.getLogger()
    # eski handlerlarni tozalaymiz (ayniqsa reloader paytida dubl bo‘lmasin)
    for h in list(root.handlers):
        root.removeHandler(h)

    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console)

    # werkzeug root’ga propagate qilsin, o‘zida handler bo‘lmasin
    wlog = logging.getLogger("werkzeug")
    wlog.handlers.clear()
    wlog.setLevel(logging.INFO)
    wlog.propagate = True

    # o'zingiz ishlatadigan nomli logger
    return logging.getLogger("app")
