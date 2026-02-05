"""
日志工具
统一的日志记录和管理
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class Logger:
    """
    日志管理器

    功能：
    1. 配置和控制台输出
    2. 文件日志记录
    3. 不同级别的日志过滤
    4. 结构化日志输出
    """

    # 类变量，用于单例模式
    _instances: dict = {}

    def __new__(cls, name: str = "guui", *args, **kwargs):
        """实现单例模式 - 同名 logger 返回同一实例"""
        if name not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[name] = instance
        return cls._instances[name]

    def __init__(self,
                 name: str = "guui",
                 log_file: Optional[Path] = None,
                 level: int = logging.INFO,
                 console: bool = True):
        """
        初始化日志器

        Args:
            name: 日志器名称
            log_file: 日志文件路径
            level: 日志级别
            console: 是否输出到控制台
        """
        # 避免重复初始化
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.handlers.clear()  # 清除已有处理器

        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 控制台处理器
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # 文件处理器
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    # ==================== 日志方法 ====================

    def debug(self, message: str) -> None:
        """调试级别日志"""
        self.logger.debug(message)

    def info(self, message: str) -> None:
        """信息级别日志"""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """警告级别日志"""
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False) -> None:
        """错误级别日志"""
        self.logger.error(message, exc_info=exc_info)

    def critical(self, message: str) -> None:
        """严重错误级别日志"""
        self.logger.critical(message)

    # ==================== 结构化日志 ====================

    def log_api_call(self, endpoint: str, method: str,
                    params: dict = None) -> None:
        """记录 API 调用"""
        self.info(f"API Call: {method} {endpoint}")
        if params:
            self.debug(f"Parameters: {params}")

    def log_api_response(self, endpoint: str, status: int,
                        duration: float) -> None:
        """记录 API 响应"""
        self.info(f"API Response: {endpoint} - Status: {status}, Duration: {duration:.2f}s")

    def log_api_error(self, endpoint: str, error: Exception) -> None:
        """记录 API 错误"""
        self.error(f"API Error: {endpoint} - {str(error)}")

    def log_task_start(self, task_type: str, task_id: str) -> None:
        """记录任务开始"""
        self.info(f"Task Started: {task_type} - {task_id}")

    def log_task_progress(self, task_type: str, task_id: str,
                         current: int, total: int) -> None:
        """记录任务进度"""
        progress = (current / total * 100) if total > 0 else 0
        self.info(f"Task Progress: {task_type} - {task_id} - {current}/{total} ({progress:.1f}%)")

    def log_task_complete(self, task_type: str, task_id: str,
                         duration: float) -> None:
        """记录任务完成"""
        self.info(f"Task Completed: {task_type} - {task_id} - Duration: {duration:.2f}s")

    def log_task_error(self, task_type: str, task_id: str, error: Exception) -> None:
        """记录任务错误"""
        self.error(f"Task Error: {task_type} - {task_id} - {str(error)}")

    def log_file_operation(self, operation: str, file_path: str,
                          success: bool = True) -> None:
        """记录文件操作"""
        status = "Success" if success else "Failed"
        level = self.info if success else self.error
        level(f"File {status}: {operation} - {file_path}")


# ==================== 便捷函数 ====================

def get_logger(name: str = "guui",
              log_file: Optional[Path] = None,
              level: int = logging.INFO) -> Logger:
    """
    获取日志器实例

    Args:
        name: 日志器名称
        log_file: 日志文件路径
        level: 日志级别

    Returns:
        Logger 实例
    """
    return Logger(name=name, log_file=log_file, level=level)


def setup_logging(log_dir: Path = None,
                 level: int = logging.INFO) -> Logger:
    """
    设置全局日志

    Args:
        log_dir: 日志目录
        level: 日志级别

    Returns:
        主日志器实例
    """
    if log_dir is None:
        log_dir = Path("logs")

    # 创建带日期的日志文件
    date_str = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"guui_{date_str}.log"

    return get_logger(name="guui", log_file=log_file, level=level)


# ==================== 上下文管理器 ====================

class LogContext:
    """日志上下文管理器 - 用于记录代码块的执行"""

    def __init__(self, logger: Logger, context_name: str):
        self.logger = logger
        self.context_name = context_name
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"Entering: {self.context_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()

        if exc_type is None:
            self.logger.info(f"Exiting: {self.context_name} - Duration: {duration:.2f}s")
        else:
            self.logger.error(f"Exiting with error: {self.context_name} - {exc_val}")

        return False  # 不抑制异常


# ==================== 装饰器 ====================

def log_execution(logger: Logger = None):
    """
    函数执行日志装饰器

    Args:
        logger: 日志器实例，为 None 则使用默认
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger()

            func_name = f"{func.__module__}.{func.__name__}"
            logger.debug(f"Calling: {func_name}")

            try:
                result = func(*args, **kwargs)
                logger.debug(f"Completed: {func_name}")
                return result
            except Exception as e:
                logger.error(f"Error in {func_name}: {str(e)}")
                raise

        return wrapper
    return decorator


def log_execution_time(logger: Logger = None):
    """
    函数执行时间日志装饰器

    Args:
        logger: 日志器实例，为 None 则使用默认
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger()

            import time
            func_name = f"{func.__module__}.{func.__name__}"
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"{func_name} completed in {duration:.2f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"{func_name} failed after {duration:.2f}s: {str(e)}")
                raise

        return wrapper
    return decorator
