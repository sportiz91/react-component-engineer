import os
import shutil
import subprocess
import socket
from typing import Tuple, Optional


def run_yarn_install(base_path: str) -> Tuple[bool, str]:
    original_dir: str = os.getcwd()
    try:
        os.chdir(base_path)

        if shutil.which("yarn") is None:
            return False, "Yarn is not installed. Please install Yarn and try again."

        print("Running yarn install...")
        install_result: subprocess.CompletedProcess[str] = subprocess.run(["yarn", "install", "--force"], capture_output=True, text=True)
        if install_result.returncode != 0:
            return False, f"Error during yarn install:\n{install_result.stderr}"

        return True, "Yarn install completed successfully"
    except subprocess.CalledProcessError as e:
        return False, f"Error running yarn install: {str(e)}"
    except Exception as e:
        return False, f"An unexpected error occurred during yarn install: {str(e)}"
    finally:
        os.chdir(original_dir)


def find_available_port(start_port: int = 3000, max_port: int = 3010, address: str = "localhost") -> Optional[int]:
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((address, port))
                return port
            except socket.error:
                continue
    return None
