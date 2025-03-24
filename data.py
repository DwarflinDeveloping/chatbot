import hashlib
import json
import os.path
from pathlib import Path

# data presets

APP_DATA_PRESET = {
    'count': 0
}

ACC_DATA_PRESET = {
    'count': 0,
    'last_vote': None,
    'active': False
}

# paths

DATA_FILE = Path('data', 'data.json')

def encode(inp: str) -> str:
    return hashlib.md5(inp.encode()).hexdigest()

def to_txt(data: dict) -> str:
    return json.dumps(data, indent=2)

def get_acc_paths(mail_hash: str, acc_hash: str) -> tuple[Path, Path]:
    mail_folder = Path('data', mail_hash)
    file_path = Path(mail_folder, acc_hash+'.json')
    return mail_folder, file_path

def load_acc_data(mail_hash: str, acc_hash: str) -> dict | None:
    mail_folder, file_path = get_acc_paths(mail_hash, acc_hash)
    if not os.path.isfile(file_path):
        return ACC_DATA_PRESET
    return json.loads(file_path.read_text())

# writing / loading functions

def write_acc_data(mail_hash: str, acc_hash: str, data: dict) -> None:
    mail_folder, file_path = get_acc_paths(mail_hash, acc_hash)
    if not os.path.isdir(mail_folder):
        os.mkdir(mail_folder)

    file_path.write_text(to_txt(data))

def load_app_data() -> dict:
    if not os.path.isfile(DATA_FILE):
        return APP_DATA_PRESET
    return json.loads(DATA_FILE.read_text())

def write_app_data(data: dict) -> None:
    DATA_FILE.write_text(to_txt(data))
