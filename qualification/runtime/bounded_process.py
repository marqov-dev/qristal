"""POSIX qualification helper for fixed local commands, not hosted execution.

The caller owns container cleanup and supplies its own non-secret environment.
"""
import os
import selectors
import signal
import subprocess
import time


class ProcessError(RuntimeError):
    pass


def capture(command, *, timeout=60, stdout_limit=131073, stderr_limit=128):
    if timeout <= 0 or stdout_limit < 0 or stderr_limit < 0:
        raise ValueError('process_limits')
    # Fixed qualification commands only; never a shell command or tenant selector.
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    outputs = [bytearray(), bytearray()]
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            for index, stream in enumerate((process.stdout, process.stderr)):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, index)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ProcessError('process_timeout')
                for key, _ in selector.select(remaining):
                    index = key.data
                    limit = (stdout_limit, stderr_limit)[index]
                    block = os.read(key.fileobj.fileno(), min(4096, limit - len(outputs[index]) + 1))
                    if not block:
                        selector.unregister(key.fileobj)
                    else:
                        outputs[index].extend(block)
                        if len(outputs[index]) > limit:
                            raise ProcessError('process_output_limit')
            try:
                code = process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                raise ProcessError('process_timeout') from None
        return code, bytes(outputs[0]), bytes(outputs[1])
    finally:
        # Kill remaining descendants too, including when the leader already exited.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)
        process.stdout.close()
        process.stderr.close()
