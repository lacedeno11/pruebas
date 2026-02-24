import subprocess
import sys


def test_hello():
    result = subprocess.run(
        [sys.executable, "hello.py"],
        capture_output=True,
        text=True
    )
    assert result.stdout.strip() == "Hello World"
