import json
import logging
import sys
from pathlib import Path

from processing import Application
from chatvote import *

root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

max_accounts = {
    # CHATVOTE_ID: 1,
    # IDLECHATVOTE_ID: 1,
    CHATVOTECOMBO_ID: 1
}

def load_credentials() -> dict:
    credentials_file = Path('data', 'credentials.json')
    if not credentials_file.exists():
        raise FileNotFoundError('No credentials file found! Create a file in the data directory called credentials.json!')

    return json.loads(credentials_file.read_text())

def main():
    credentials = load_credentials()

    app = Application(
        credentials=credentials, f_msg='DE #{}', max_accounts=max_accounts)
    app.run()

if __name__ == '__main__':
    main()
