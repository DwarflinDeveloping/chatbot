import dataclasses
import enum
import random
from datetime import datetime
from time import sleep

from multiprocessing import Value, Lock
from typing import Callable, List

from selenium import webdriver
from selenium.common import WebDriverException
from selenium.webdriver.common.by import By
from seleniumbase import BaseCase

from data import encode, get_acc_paths, load_acc_data, write_acc_data

from logging import getLogger, DEBUG, INFO, WARNING, FATAL
logger = getLogger(__name__)

SIGN_IN_URL = 'https://accounts.google.com/'
CHANNEL_SWITCHER_URL = 'https://youtube.com/channel_switcher'

F_LIVE_CHAT_URL = 'https://youtube.com/live_chat?v={}'
F_VIDEO_URL = 'https://youtube.com/watch?v={}'

class ExitReason(enum.Enum):
    FINISHED = 0    # properly reached max_votes
    WEBDRIVER = 1   # WebdriverException
    FORCED = 2      # user forcefully stopped the program
    UNKNOWN = 3     # unknown error occurred

@dataclasses.dataclass
class Browser:
    browser: BaseCase
    email: str
    password: str
    channel_name: str
    f_msgs: List[str]

    exit_var: Value
    alltime_count: Value
    alltime_count_lock: Lock
    alltime_count_listener: Callable = None

    refresh_interval: int = 100
    max_votes: int = 760
    security_wait: float = 2
    vote_cooldown: float = 6
    invisible_mode: bool = False

    def __post_init__(self):
        self.data = self.load_data()
        self.data['email'] = self.email
        self.data['channel_name'] = self.channel_name

    def log(self, level: int, text: str):
        logger.log(level, '/'.join((self.email, self.channel_name)) + ' - ' + text)

    @property
    def hashes(self):
        return encode(self.email), encode(self.channel_name)

    @property
    def acc_count(self):
        return self.data['count']

    @acc_count.setter
    def acc_count(self, value: int) -> None:
        self.data['count'] = value
        self.save_data()

    @property
    def active(self):
        return self.data['active']

    @active.setter
    def active(self, value: bool):
        self.data['active'] = value
        self.save_data()

    @property
    def last_vote(self):
        return self.data['last_vote']

    @last_vote.setter
    def last_vote(self, value: bool):
        self.data['last_vote'] = value
        self.save_data()

    @property
    def exit(self):
        return self.exit_var.value

    def save_data(self) -> None:
        write_acc_data(*self.hashes, data=self.data)

    def load_data(self) -> dict:
        return load_acc_data(*self.hashes)

    def _wait(self):
        sleep(self.security_wait)

    def login(self):
        self.log(INFO, f'Signing into {self.email}...')
        self.browser.open(SIGN_IN_URL)

        self.log(DEBUG, 'Typing out the mail...')
        self.browser.type('#identifierId', self.email)  # input email

        self.log(DEBUG, 'Clicking next button...')
        self.browser.click('#identifierNext')
        self._wait()

        self.log(DEBUG, 'Typing out the password...')
        self.browser.type('[name=Passwd]', self.password)  # input password
        self._wait()

        self.log(DEBUG, 'Clicking next button...')
        self.browser.click('#passwordNext > div > button')
        self._wait()

    def switch_channel(self):
        self.log(INFO, f'Switching to channel {self.channel_name}...')
        self.browser.open(CHANNEL_SWITCHER_URL)
        self._wait()

        channels = {}
        for i, channel_raw in enumerate(self.browser.find_elements(By.TAG_NAME, 'ytd-account-item-renderer')):
            title = channel_raw.find_element(By.ID, 'channel-title').find_element(By.XPATH, './following-sibling::*[1]').text
            channels[title] = channel_raw

        self.log(DEBUG, f'Found channels for {self.email}: {", ".join(channels.keys())}')
        channels[self.channel_name].click()

    def open_livestream(self, vid: str):
        self.log(INFO, f'Opening livestream {vid}...')
        self.browser.get(F_LIVE_CHAT_URL.format(vid))
        self._wait()

    def _vote(self, session_count: int):
        msg_input = 'html body yt-live-chat-app div#contents.style-scope.yt-live-chat-app yt-live-chat-renderer.style-scope.yt-live-chat-app tp-yt-iron-pages#content-pages.style-scope.yt-live-chat-renderer div#chat-messages.style-scope.yt-live-chat-renderer.iron-selected div#contents.style-scope.yt-live-chat-renderer tp-yt-iron-pages#panel-pages.style-scope.yt-live-chat-renderer div#input-panel.style-scope.yt-live-chat-renderer.iron-selected yt-live-chat-message-input-renderer#live-chat-message-input.style-scope.yt-live-chat-renderer div#container.style-scope.yt-live-chat-message-input-renderer div#top.style-scope.yt-live-chat-message-input-renderer div#input-container.style-scope.yt-live-chat-message-input-renderer yt-live-chat-text-input-field-renderer#input.style-scope.yt-live-chat-message-input-renderer div#input.style-scope.yt-live-chat-text-input-field-renderer'

        with self.alltime_count_lock:
            self.alltime_count.value += 1
            alltime_count_val = self.alltime_count.value

        self.browser.type(msg_input, random.choice(self.f_msgs).format(
            alltime=alltime_count_val, session=session_count) + webdriver.Keys.ENTER)  # send message
        self.log(DEBUG, f'Vote #{alltime_count_val} (#{self.acc_count} for account) (#{session_count} for session)')

        if self.invisible_mode:
            sleep(1)
            self.browser.execute_script("document.evaluate('(//yt-live-chat-text-message-renderer)[last()]//*[@id=\"menu-button\"]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue?.click();")
            # self.browser.click(By.XPATH, '(//yt-live-chat-text-message-renderer)[last()]//*[@id="menu-button"]')
            self.browser.click(By.TAG_NAME, 'ytd-menu-service-item-renderer')

        if self.alltime_count_listener:
            self.alltime_count_listener()

        if session_count % self.refresh_interval == 0:  # refresh page once every n (=100) votes
            self.log(DEBUG, f'Refreshing page...')
            self.browser.refresh()
            self._wait()

    def vote_loop(self) -> ExitReason:
        self.log(INFO, f'Starting vote loop...')
        self.active = True
        session_count = 0
        exit_reason = None

        try:
            while True:
                if self.exit:
                    raise KeyboardInterrupt()

                session_count += 1
                self.acc_count += 1
                self._vote(session_count)

                if session_count >= self.max_votes:  # stopping when max_votes is reached
                    break

                sleep(self.vote_cooldown * (31/30))  # cooldown + 1/30 wait

        except WebDriverException as exc:
            session_count -= 1
            self.log(FATAL, f'WebdriverException while running vote loop!\n{exc.msg}')
            exit_reason = ExitReason.WEBDRIVER

        except KeyboardInterrupt:
            self.log(DEBUG, f'KeyboardInterrupt while running vote loop!')
            exit_reason = ExitReason.FORCED

        except Exception as exc:
            exit_reason = ExitReason.UNKNOWN
            self.log(DEBUG, f'{exc.__class__.__name__} while running vote loop: ' +
                            exc.message if hasattr(exc, 'message') else exc)

        else:
            self.log(INFO, f'Successfully finished vote loop!')
            exit_reason = ExitReason.FINISHED

        finally:
            self.active = False
            self.last_vote = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return exit_reason
