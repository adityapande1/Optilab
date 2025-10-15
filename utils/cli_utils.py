# utils.py
import subprocess
import sys
from rich import print

def stream_command(cmd):
    print(f'\n🚀 Starting: {cmd}\n{"=" * 80}')
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, universal_newlines=True
    )

    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()

    process.wait()
    print(f'\n✅ Finished: {cmd} (exit code {process.returncode})')
    print('-' * 80)
    return {'cmd': cmd, 'returncode': process.returncode}
