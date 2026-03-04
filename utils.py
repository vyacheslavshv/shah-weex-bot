import os
import sys
import threading
import logging
from loguru import logger
from tortoise import Tortoise
from config import TORTOISE_ORM


class SingleFileSink:
    def __init__(self, file_path, max_bytes=50 * 1024 * 1024, keep_bytes=40 * 1024 * 1024):
        self.file_path = file_path
        self.max_bytes = max_bytes
        self.keep_bytes = keep_bytes
        self.lock = threading.Lock()
        self._open()

    def _open(self):
        self.file = open(self.file_path, "a", encoding="utf-8")

    def _truncate_file(self):
        self.file.flush()
        with open(self.file_path, "rb") as reader:
            data = reader.read()

        if len(data) <= self.keep_bytes:
            return

        tail = data[-self.keep_bytes:]
        split = tail.find(b"\n")
        if split != -1:
            tail = tail[split + 1 :]

        self.file.close()
        with open(self.file_path, "wb") as writer:
            writer.write(tail)
        self._open()

    def write(self, message):
        with self.lock:
            self.file.write(str(message))
            self.file.flush()
            if self.file.tell() >= self.max_bytes:
                self._truncate_file()

    def stop(self):
        with self.lock:
            self.file.close()


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(file_path="logs/bot.log", level="DEBUG", max_file_bytes=50 * 1024 * 1024):
    logger.remove()
    log_dir = os.path.dirname(file_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    log_format = "<green>{time:MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    
    logger.add(sys.stderr, level=level, format=log_format)
    sink = SingleFileSink(file_path=file_path, max_bytes=max_file_bytes, keep_bytes=int(max_file_bytes * 0.8))
    logger.add(sink, level=level, format=log_format)
    
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    for name in (
        "aiogram.event",
        "aiosqlite",
        "apscheduler.scheduler",
        "apscheduler.executors.default",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)


async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas(safe=True)

async def close_db():
    await Tortoise.close_connections()
