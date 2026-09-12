"""CPU diagnostic variant of the pinned POSIX qualification capture helper.

The historical GPU payload's runtime/bounded_process.py remains unchanged.
This variant adds opt-in bounded partial output for known non-secret commands.
The caller owns VM cleanup and supplies its own non-secret environment.
"""
import os
import selectors
import signal
import subprocess
import time


class ProcessError(RuntimeError):
    pass


def capture(command, *, timeout=60, stdout_limit=131073, stderr_limit=128,
            retain_on_error=False):
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
    except ProcessError as error:
        # Opt in only for known non-secret qualification output. Preserve the
        # same byte bounds; an overflow byte must never leak into retained data.
        if retain_on_error:
            error.stdout = bytes(outputs[0][:stdout_limit])
            error.stderr = bytes(outputs[1][:stderr_limit])
        raise
    finally:
        # Kill remaining descendants too, including when the leader already exited.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)
        process.stdout.close()
        process.stderr.close()
