import dataclasses
import multiprocessing
import random
from datetime import datetime
from multiprocessing import Process, Value, Lock
from time import sleep
from typing import Dict, Tuple, List, Callable

from seleniumbase import SB
from typing_extensions import TypeAlias

from browser import Browser
from data import load_acc_data, write_acc_data, load_app_data, write_app_data, encode

import logging
logger = logging.getLogger(__name__)

"""My chat messages on all YouTube live streams no longer show to others. This was probably caused by myself contributing to a live stream that lets people type in a 2-letter code to vote for a country they like. I did not use bots or multiple accounts and think i've been blocked falsely."""


@dataclasses.dataclass
class Application:
    credentials: Dict[str, Dict[str, List[str]] | Dict[str, str]]
    vid: str
    f_msg: str
    max_accounts: int
    vote_cooldown: float = 6
    security_wait: float = 2

    def __post_init__(self):
        self.active_processes: List[Process] = []

        self.data: dict = load_app_data()
        self.count_var: Value = Value('i', self.data['count'])
        self.count_lock: Lock = Lock()

    def _count_listener(self) -> None:
        self.data['count'] = self.count_var.value
        write_app_data(self.data)

    def _browser_task(self, email: str, password: str, acc_name: str):
        logger.info(f'Browser for {email}/{acc_name} starting...')

        with SB(test=True, uc=True, headed=True) as sb:
            browser = Browser(
                sb, email, password, acc_name, self.count_var, self.count_lock, self._count_listener,
                security_wait=self.security_wait
            )
            browser.login()
            browser.switch_channel()
            browser.open_livestream(self.vid)
            exit_reason = browser.vote_loop()

        logger.info(f'Voting for {browser.email} / {browser.channel_name} ended with {str(exit_reason)}!')

    def get_ready_accs(self) -> List[Process]:
        processes = []
        channels = []
        for email in self.credentials:
            password = self.credentials[email]['password']
            for acc_name in self.credentials[email]['channels']:
                acc_data = load_acc_data(encode(email), encode(acc_name))

                if acc_data['active']:
                    continue

                last_vote = acc_data['last_vote']
                if last_vote is None:
                    pass

                else:
                    dt_days = (datetime.now() - datetime.strptime(last_vote, '%Y-%m-%d %H:%M:%S')).total_seconds() / 60 / 60 / 24
                    dt_secs = (datetime.now() - datetime.strptime(last_vote, '%Y-%m-%d %H:%M:%S')).total_seconds()
                    if dt_days<1:
                        logger.debug(f'Account {acc_name} of {email} skipped ({dt_days}d<1d) ({dt_secs}s)')
                        continue

                process = Process(name='/'.join((email, acc_name)), target=self._browser_task,
                                  args=(email, password, acc_name), daemon=True)
                processes.append(process)
                channels.append(acc_name)

        logger.debug(f'Fetched accounts: {", ".join(channels)}')
        return processes

    def run(self):
        try:
            while True:
                self.active_processes = [p for p in self.active_processes if p.is_alive()]

                if len(self.active_processes) >= self.max_accounts:
                    sleep(.5)
                    continue

                ready_accs = self.get_ready_accs()
                try:
                    process = random.choice(ready_accs)
                except IndexError:
                    logger.warning(f'{len(self.active_processes)} processes running but {self.active_processes} needed!\n'
                                   f'Trying again in 20s.')
                    sleep(20)
                else:
                    logger.info(f'Creating task {process.name}')
                    process.start()
                    self.active_processes.append(process)
                    sleep(5)
        finally:
            print('Finished!')
