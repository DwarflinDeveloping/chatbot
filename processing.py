import dataclasses
from dataclasses import field
import random
from datetime import datetime
from multiprocessing import Process, Value, Lock
from time import sleep
from typing import Dict, Tuple, List, Callable, Any

from seleniumbase import SB, BaseCase
from typing_extensions import TypeAlias

from browser import Browser
from chatvote import cooldowns
from data import load_acc_data, load_app_data, write_app_data, encode

import logging
logger = logging.getLogger(__name__)

"""My chat messages on all YouTube live streams no longer show to others. This was probably caused by myself contributing to a live stream that lets people type in a 2-letter code to vote for a country they like. I did not use bots or multiple accounts and think i've been blocked falsely."""


@dataclasses.dataclass
class Application:
    credentials: Dict[str, Dict[str, List[str]] | Dict[str, str]]
    f_msgs: List[str]
    max_accounts: Dict[str, int]
    security_wait: float = field(default_factory=lambda: 2)
    vote_cooldown: float = field(default_factory=lambda: None)
    invisible_mode: bool = field(default_factory=lambda: False)
    sb_args: Dict[str, Any] = field(default_factory=lambda: {'test': True, 'uc': True, 'headed': True})

    def __post_init__(self):
        self.active_processes: Dict[str, List[Process]] = {vid: [] for vid in self.max_accounts}

        self.data: dict = load_app_data()
        self.exit_var: Value = Value('i', False)
        self.count_var: Value = Value('i', self.data['count'])
        self.count_lock: Lock = Lock()

    def _count_listener(self) -> None:
        self.data['count'] = self.count_var.value
        write_app_data(self.data)

    def _voting_task(self, email: str, password: str, acc_name: str, vid: str):
        logger.info(f'Browser for {email}/{acc_name} starting...')

        with SB(**self.sb_args) as sb:
            if self.invisible_mode:
                sb.driver.execute_cdp_cmd("Network.enable", {})
                sb.driver.execute_cdp_cmd("Network.setBlockedURLs", {
                    "urls": ["*://www.youtube.com/youtubei/v1/live_chat/get_live_chat*"]
                })

            browser = Browser(sb, email, password, self.security_wait, self.invisible_mode)
            browser.prepare_vote(acc_name, self.f_msgs, self.exit_var, self.count_var, self.count_lock, self._count_listener)

            browser.login()
            browser.switch_channel()
            browser.open_livestream(vid)
            exit_reason = browser.vote_loop(self.vote_cooldown if self.vote_cooldown is not None else cooldowns[vid])

        logger.info(f'Voting for {browser.email}/{browser.channel_alias} ended with {str(exit_reason)}!')

    def _management_task(self, email: str, password: str, channel_name: str, channel_alias: str, creation: bool):
        logger.info(f'Management for {email}/{channel_alias} starting...')
        with SB(**self.sb_args) as sb:
            browser = Browser(sb, email, password, self.security_wait, self.invisible_mode)
            browser.login()
            if creation:
                browser.create_channel(channel_name, channel_alias)
            else:  # deletion
                browser.channel_name = channel_name
                browser.switch_channel()
                browser.delete_channel()


    def get_ready_accs(self) -> List[Tuple[str, str, str]]:
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

                acc = (email, password, acc_name)
                processes.append(acc)
                channels.append(acc_name)

        logger.debug(f'Fetched accounts: {", ".join(channels)}')
        return processes

    def run(self):
        try:
            while True:
                p_vid = None
                for vid in self.max_accounts:
                    # filter out finished processes
                    if len(self.active_processes[vid]) < self.max_accounts[vid]:
                        p_vid = vid  # stream with not enough accounts found
                        break

                if p_vid is None:  # currently all streams started
                    sleep(.5)
                    continue

                ready_accs = self.get_ready_accs()
                try:
                    args = random.choice(ready_accs)
                except IndexError:
                    logger.warning(f'{len(self.active_processes)} processes running but {self.active_processes} needed!\n'
                                   f'Trying again in 20s.')
                    sleep(20)
                else:
                    process = Process(name='/'.join((args[0], args[2])), target=self._voting_task,
                                      args=args+(p_vid,), daemon=True)
                    logger.info(f'Creating task {process.name}')
                    process.start()
                    self.active_processes[p_vid].append(process)
                    sleep(10)

        except KeyboardInterrupt:
            self.exit_var.value = True
            """for process in self.active_processes:
                process.join()"""

        finally:
            print('Finished!')
