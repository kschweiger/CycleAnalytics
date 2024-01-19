import functools
import logging
from os import getenv
from time import perf_counter

logger = logging.getLogger(__name__)


def initialize_flask_server_debugger_if_needed() -> None:
    # based on https://blog.theodo.com/2020/05/debug-flask-vscode/
    if getenv("DEBUGGER") == "True":
        import multiprocessing

        pid = multiprocessing.current_process().pid
        if pid is not None and pid > 1:
            import debugpy

            debugpy.listen(("0.0.0.0", 10001))
            # print(
            #     "⏳ VS Code debugger can now be attached, press F5 in VS Code ⏳",
            #     flush=True,
            # )
            # debugpy.wait_for_client()
            # print("🎉 VS Code debugger attached, enjoy debugging 🎉", flush=True)


def log_timing(func):
    """Print the runtime of the decorated function"""

    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = perf_counter()  # 1
        value = func(*args, **kwargs)
        end_time = perf_counter()  # 2
        run_time = end_time - start_time  # 3
        logger.debug("Finished %s in %s secs", func.__name__, round(run_time, 4))
        return value

    return wrapper_timer
