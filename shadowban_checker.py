import json
import logging
import random
import sys
from pathlib import Path

from selenium.webdriver import Keys
from seleniumbase import SB

from browser import Browser
from processing import Application
from chatvote import CHATVOTE_ID, country_tags

def load_credentials() -> dict:
    credentials_file = Path('data', 'credentials.json')
    if not credentials_file.exists():
        raise FileNotFoundError('No credentials file found! Create a file in the data directory called credentials.json!')

    return json.loads(credentials_file.read_text())

def main():
    credentials = load_credentials()
    for email in credentials:
        password = credentials[email]['password']
        for acc_name in credentials[email]['channels']:
            with SB(test=True, uc=True, headed=True) as sb:
                browser = Browser(sb, email, password, acc_name, None, None, None)
                browser.login()
                browser.switch_channel()
                browser.open_livestream(CHATVOTE_ID)

                f_msg = random.choice(country_tags)
                while f_msg not in ['DE']: f_msg = random.choice(country_tags)

                print(acc_name, f_msg)

                msg_input = 'html body yt-live-chat-app div#contents.style-scope.yt-live-chat-app yt-live-chat-renderer.style-scope.yt-live-chat-app tp-yt-iron-pages#content-pages.style-scope.yt-live-chat-renderer div#chat-messages.style-scope.yt-live-chat-renderer.iron-selected div#contents.style-scope.yt-live-chat-renderer tp-yt-iron-pages#panel-pages.style-scope.yt-live-chat-renderer div#input-panel.style-scope.yt-live-chat-renderer.iron-selected yt-live-chat-message-input-renderer#live-chat-message-input.style-scope.yt-live-chat-renderer div#container.style-scope.yt-live-chat-message-input-renderer div#top.style-scope.yt-live-chat-message-input-renderer div#input-container.style-scope.yt-live-chat-message-input-renderer yt-live-chat-text-input-field-renderer#input.style-scope.yt-live-chat-message-input-renderer div#input.style-scope.yt-live-chat-text-input-field-renderer'
                browser.browser.type(msg_input, f_msg + Keys.ENTER)

if __name__ == '__main__':
    main()
