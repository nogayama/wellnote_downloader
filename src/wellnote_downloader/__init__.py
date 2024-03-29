#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =================================================================
# wellnote downloader
#
# Copyright (c) 2022 Takahide Nogayama
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
# =================================================================

__version__ = "0.13.3"

import argparse
from argparse import ArgumentParser, Action, Namespace
from contextlib import contextmanager
from datetime import datetime
from getpass import getpass
import glob
import logging
import os
import re
import shutil
import sys
import tempfile
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webdriver import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from selenium.common.exceptions import StaleElementReferenceException

import filedate

# logger
_LOGGER: logging.Logger = logging.getLogger(__name__)

LOG_FORMAT: str = '%(asctime)s |  %(levelname)-7s | %(message)s (%(filename)s L%(lineno)s %(name)s)'

DEFAULT_INTERVAL: int = 1
NUM_OF_RETRIES: int = 3

def parse_date_str_int(date_s: str) -> tuple[str, str, str]:
    """
    2019年9月6日
    """
    match: re.Match = re.search("(\d+)\s*年\s*(\d+)\s*月\s*(\d+)\s*日", date_s)
    if match:
        year_i: int = int(match.group(1))
        month_i: int = int(match.group(2))
        day_i: int = int(match.group(3))
        return year_i, month_i, day_i
    raise ValueError("Could not parse date_s '%s'", date_s)

def disable_update_time_of_file(filepath, dt):
    filedate_file = filedate.File(filepath)
    
    _LOGGER.debug("Updating time of file='%s' with dt='%s'", filepath, dt)
    filedate_file.set(
        created = dt,
        modified = dt,
        accessed = dt
    )
    
    os.chmod(filepath, 0o644)

################################################################################
# Utilities for Selenium


def get_driver_and_wait(download_dir: str = None, browser: str = None, clear_profile = False) -> tuple[WebDriver, WebDriverWait, str, int]:

    timeout_sec: int = 60

    # download_dir: str = "/Users/nogayama1/Downloads"
    if not download_dir:
        # download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        download_dir = os.path.join(os.getcwd(), "Downloads")

    if not browser:
        browser = "chrome"

    driver: WebDriver = None
    if browser == "chrome":
        chrome_options = webdriver.ChromeOptions()
        
        profile_dir: str = os.path.join(tempfile.gettempdir(), "wellnote_downloader", "chrome_profile")
        _LOGGER.info("Using profile dir to reuse session with semi persistent temporary directory: %s", profile_dir)
        if clear_profile:
            _LOGGER.info("Deleting the profile dir to reset the session")
            if os.path.exists(profile_dir) and os.path.isdir(profile_dir):
                shutil.rmtree(profile_dir)
        os.makedirs(profile_dir, exist_ok=True)
        chrome_options.add_argument(f"--user-data-dir='{profile_dir}'")

        prefs = {'download.default_directory': download_dir}
        chrome_options.add_experimental_option('prefs', prefs)

        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), chrome_options=chrome_options)
    elif browser == "firefox":
        options = FirefoxOptions()
        
        profile_dir: str = os.path.join(tempfile.gettempdir(), "wellnote_downloader", "firefox_profile")
        _LOGGER.info("Using profile dir to reuse session with semi persistent temporary directory: %s", profile_dir)
        if clear_profile:
            _LOGGER.info("Deleting the profile dir to reset the session")
            if os.path.exists(profile_dir) and os.path.isdir(profile_dir):
                shutil.rmtree(profile_dir)
        os.makedirs(profile_dir, exist_ok=True)
        options.add_argument('-profile')
        options.add_argument(profile_dir)

        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.dir", download_dir)

        driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), \
                                    options=options)
    else:
        raise ValueError(f"browser type '{browser}' is not supported.")
    driver.implicitly_wait(timeout_sec)
    wait: WebDriverWait = WebDriverWait(driver, timeout_sec)
    return driver, wait, download_dir, timeout_sec

def is_attached(elem):
    try:
        elem.is_enabled()
        return True
    except StaleElementReferenceException:
        return False

def scroll_to_show_element(driver, element, offset=0):
    _LOGGER.debug("Scrolling window to locate the element in window")
    driver.execute_script("arguments[0].scrollIntoView();", element)
    if offset != 0:
        driver.execute_script("window.scrollTo(0, window.pageYOffset + " + str(offset) + ");")

@contextmanager
def inspect_mode(driver: WebDriver, original_timeout: int, inspect_sec: int = 1):
    driver.implicitly_wait(inspect_sec)
    wait2 = WebDriverWait(driver, inspect_sec)
    try:
        yield wait2
    except NoSuchElementException:
        pass
    except TimeoutException:
        pass
    finally:
        driver.implicitly_wait(original_timeout)

class EC_OR:

    def __init__(self, timeout_sec, *args):
        self.timeout_sec = timeout_sec
        self.conditions = args
    
    def __call__(self, driver):
        with inspect_mode(driver, self.timeout_sec):
            for idx, condition in enumerate(self.conditions):
                time.sleep(1)
                try:
                    _LOGGER.debug("Waiting for condition %s / %s", idx + 1, len(self.conditions))
                    ans = condition(driver)
                    if ans:
                        return ans, idx
                except Exception:
                    pass
            return False


def download_is_completed(download_dir: str, last_newest_file: str = None):

    def _f(driver):
        filepaths: list[str] = glob.glob(os.path.join(download_dir, "*"))

        filepaths = [filepath for filepath in filepaths if os.path.isfile(filepath)]

        if not filepaths:  # empty
            _LOGGER.info("The download is not started yet because the download dir is empty")
            return False

        newest_file = max(filepaths, key=lambda fp: os.path.getmtime(fp))
        if newest_file == last_newest_file:
            _LOGGER.info("The download is not started yet")
            return False

        newest_file_basename: str = os.path.basename(newest_file)

        if "." not in newest_file_basename:
            _LOGGER.info("The latest file does not have an extension. Download may be finished.")
            return newest_file
        else:
            extension: str = newest_file_basename.split(".")[-1]
            if extension in ("part", "crdownload"):
                _LOGGER.info("Downloading...")
                return False
            else:
                _LOGGER.info("Download has been finished")
                return newest_file

    return _f


class DownloadResult:
    def __init__(self):
        self.downloaded_filepath = None

@contextmanager
def safe_download(driver: WebDriver, wait: WebDriverWait, download_dir: str):

    filepaths: list[str] = glob.glob(os.path.join(download_dir, "*"))
    last_newest_file = max(filepaths, key=lambda fp: os.path.getmtime(fp)) if filepaths else None

    download_result = DownloadResult()
    yield download_result

    _LOGGER.debug("Waiting until the download is completed")
    download_result.downloaded_filepath = wait.until(download_is_completed(download_dir, last_newest_file))


################################################################################
# Utilities for Wellnote
def get_email_and_password() -> tuple[str, str]:

    email: str = None
    password: str = None
    no_environ_vars = False
    try:
        email = os.environ['WELLNOTE_EMAIL']
    except KeyError:
        # print("エラー: 'export WELLNOTE_EMAIL=あなたのEmailアドレス' をコマンドラインで実行して下さい")
        # return 1
        no_environ_vars = True
        email = input("Enter your email: ")

    try:
        password = os.environ['WELLNOTE_PASSWORD']
    except KeyError:
        # print("エラー: 'export WELLNOTE_PASSWORD=あなたのパスワード' をコマンドラインで実行して下さい")
        # return 1
        no_environ_vars = True
        password = getpass("Enter your password: ")
    if no_environ_vars:
        _LOGGER.warning("You can omit username and password prompt by declaring environmental variables WELLNOTE_EMAIL and WELLNOTE_PASSWORD.")

    return email, password


@contextmanager
def wellnote(driver: WebDriver, wait: WebDriverWait, interval: int, email: str, password: str):
    try:
        _LOGGER.info("Geting wellnote.jp")
        driver.get("https://wellnote.jp/")
        time.sleep(interval)

        _, condition_idx = wait.until( \
            EC_OR(wait._timeout, \
                EC.element_to_be_clickable([By.XPATH, "//a[@href='/login']"]), \
                EC.element_to_be_clickable([By.XPATH, "//a[@href='/albums']"]) \
            )
        )

        if condition_idx == 1: # reuse session
            _LOGGER.info("Found past login session. Omitting the login process.")
        else:
            _LOGGER.debug("Waiting until a clickable login button is available")
            # <a variant="secondary" class="sc-ieecCq dqGvSl" href="/login">ログイン</a>
            login_button: WebElement = wait.until(EC.element_to_be_clickable([By.XPATH, "//a[@href='/login']"]))

            _LOGGER.info("Clicking the login button")
            login_button.click()

            if True:
                wait.until(EC.staleness_of(login_button))

                _LOGGER.debug("Waiting until a clickable login form is available")
                # <input id="loginId" type="email" autocomplete="username" inputmode="email" aria-required="true" name="loginId" class="sc-hmjpVf cdjdxJ">
                login_id_form: WebElement = wait.until(EC.element_to_be_clickable([By.ID, "loginId"]))
                login_id_form.click()
                login_id_form.send_keys(email)

                _LOGGER.debug("Waiting until a clickable password form is available")
                # <input id="password" type="password" autocomplete="current-password" aria-required="true" name="password" class="sc-hmjpVf cdjdxJ">
                password_form: WebElement = wait.until(EC.element_to_be_clickable([By.ID, "password"]))
                password_form.click()
                password_form.send_keys(password)

                _LOGGER.info("Sending the login form")
                password_form.send_keys(Keys.ENTER)
                time.sleep(interval)

                wait.until(EC.staleness_of(password_form))
        
        yield

    finally:
        driver.quit()


def download_home(start_year: int = 2009, start_month: int = 1, \
                   end_year: int = 2023, end_month: int = 12, \
                   interval: int = DEFAULT_INTERVAL, \
                   download_dir: str = None, browser: str = None, clear_profile:bool=False, disable_update_time=False) -> int:
    if interval < DEFAULT_INTERVAL:
        interval = DEFAULT_INTERVAL

    email: str; password: str
    email, password = get_email_and_password()

    driver: WebDriver; wait: WebDriverWait; timeout_sec: int
    driver, wait, download_dir, timeout_sec = get_driver_and_wait(download_dir, browser, clear_profile)

    num_of_download:int = 0
    try:
        _LOGGER.info("Maximizing browser window")
        driver.maximize_window()
        with wellnote(driver, wait, interval, email, password):

            _LOGGER.info("Deleting your family element")
            # <div class="sc-dkQkyq kcvKs"><div translate="no" class="sc-jivBlf fDaukR">あなたの家族</div></div>
            # <div class="sc-fIosxK betDep"><div translate="no" class="sc-gyElHZ eHwBVV">あなたの家族</div></div>
            your_family_elem = driver.find_element(By.CLASS_NAME, 'sc-fIosxK')
            driver.execute_script("var element = arguments[0]; element.parentNode.removeChild(element); ", your_family_elem)
            time.sleep(interval)
            
            if True: # already in home tab

                data_indexes_done: set[int] = set()

                sequence_check_count: int = 0
                while True:
                    # <section class="sc-dUbtfd sc-hxaKAp bYAYzG jdTirr">
                    # <div class="sc-jdhwqr hWjUjw" style="box-sizing: border-box; padding-top: 0px; padding-bottom: 19548px; margin-top: 0px;">
                    home_element_parent: WebElement = wait.until(EC.element_to_be_clickable([By.CLASS_NAME, "sc-jdhwqr"]))

                    home_elements: WebElement = home_element_parent.find_elements(By.XPATH, "./div")
                    _LOGGER.debug("Found %s home elements in display.", len(home_elements))

                    for home_element in home_elements:
                        
                        if not is_attached(home_element): # attached
                            sequence_check_count = 0
                            break

                        data_index: int = int(home_element.get_attribute("data-index"))
                        
                        if data_index not in data_indexes_done:
                            scroll_to_show_element(driver, home_element)
                            time.sleep(interval/3.0)
                            
                            # <time class="sc-hKTqa fqnSS" datetime="2019-11-05T20:05:24+09:00">2019年11月5日</time>
                            time_elem: WebElement = home_element.find_element(By.XPATH, ".//time")
                            datetime_iso_s:str = time_elem.get_attribute("datetime")
                            _LOGGER.info("Found data_index=%s, with datetime=%s", data_index, datetime_iso_s)
                            datetime_iso_s = datetime_iso_s.split("+")[0] # remove +90:00
                            dt: datetime = datetime.strptime(datetime_iso_s, "%Y-%m-%dT%H:%M:%S")
                            if dt.year > end_year or (dt.year == end_year and dt.month > end_month):
                                _LOGGER.warning("Skipping    %s because it is not in the target period", datetime_iso_s)
                                data_indexes_done.add(data_index)
                                break
                            if dt.year < start_year or (dt.year == start_year and dt.month < start_month):
                                _LOGGER.warning("Exiting because we reach the end of the target period: %s", datetime_iso_s)
                                return 0

                            datetime_s = datetime_iso_s.replace(":", "-")
                            datetime_s = datetime_s.replace("T", "_")
                            year_s = datetime_s.split("-")[0] #
                            
                            target_dir: str = os.path.join(download_dir, "wellnote", "home", year_s)
                            target_path: str = os.path.join(target_dir, f"wellnote_home_{datetime_s}.png")
                            
                            if os.path.exists(target_path):
                                _LOGGER.warning("Skipping    %s because it exists", target_path.replace(os.getcwd(), "."))
                            else:
                                _LOGGER.warning("Downloading %s because it does not exist", target_path.replace(os.getcwd(), "."))
                                os.makedirs(os.path.join(target_dir), exist_ok=True)
                                time.sleep(interval * 2)
                                home_element.screenshot(target_path)

                            if not disable_update_time:
                                disable_update_time_of_file(target_path, dt)

                            data_indexes_done.add(data_index)
                            
                            sequence_check_count = 0
                            break
                    else:
                        sequence_check_count += 1
                        if sequence_check_count >= NUM_OF_RETRIES:
                            _LOGGER.info("Found the end of the home element sequence")
                            break
                        time.sleep(interval)
                    
                    if home_element:
                        if not is_attached(home_element): # attached
                            sequence_check_count = 0
                            break

                        elem_height: int = home_element.size['height']
                        _LOGGER.debug("Scrolling the captured element to see next element with its heights=%s", elem_height)
                        driver.execute_script(f"window.scrollBy(0, {elem_height / 10});")
                    

    finally:
        _LOGGER.warning("Finishing album download. The number of downloaded pictures/movies is %s", num_of_download)
        driver.quit()
    
    return 0


@contextmanager
def album_tab(driver: WebDriver, wait: WebDriverWait, \
                   interval: int = DEFAULT_INTERVAL):

    _LOGGER.debug("Waiting until a clickable albums button is available")
    # <a class="sc-jWWnA hivVBT" href="/albums">
    album_button: WebElement = wait.until(EC.element_to_be_clickable([By.XPATH, "//a[@href='/albums']"]))

    _LOGGER.info("Clicking the album button")
    album_button.click()
    time.sleep(interval)

    yield

def download_album(start_year: int = 2009, start_month: int = 1, \
                   end_year: int = 2023, end_month: int = 12, \
                   interval: int = DEFAULT_INTERVAL, \
                   download_dir: str = None, browser: str = None, clear_profile=False, disable_update_time=False) -> int:
    if interval < DEFAULT_INTERVAL:
        interval = DEFAULT_INTERVAL

    email: str; password: str
    email, password = get_email_and_password()

    driver: WebDriver; wait: WebDriverWait; timeout_sec: int
    driver, wait, download_dir, timeout_sec = get_driver_and_wait(download_dir, browser, clear_profile)

    num_of_download:int = 0
    try:
        with wellnote(driver, wait, interval, email, password):

            with album_tab(driver, wait, interval):

                ## Go to start year
                year: int = 9999
                while year >= 2009:  # We can't go back to the years before wellnote's inception

                    _LOGGER.debug("Waiting until a year text is available")
                    # year = wait.until(EC.visibility_of_element_located([By.XPATH, "//div[contains(text(), '年')]"])) # dont work
                    year_elem: WebElement = wait.until(EC.visibility_of_element_located([By.CLASS_NAME, "sc-bvFjSx"]))
                    year = int(year_elem.text.replace("年", ""))

                    if year == start_year:
                        break

                    move_previous_year_button = None
                    with inspect_mode(driver, timeout_sec) as wait2:
                        _LOGGER.debug("Waiting until a clickable previous year button is available")
                        move_previous_year_button: WebElement = wait2.until(EC.element_to_be_clickable([By.XPATH, "//*[name()='svg' and @class='sc-emDsmM fWHKrl']"]))
                        # move_previous_year_button: WebElement = wait2.until(EC.element_to_be_clickable([By.CLASS_NAME, "sc-emDsmM"]))
                    if not move_previous_year_button:
                        _LOGGER.info("Breaking this year because previous button is not found")
                        start_month = 1
                        break

                    _LOGGER.info("Moving previous year of %s ", year)
                    move_previous_year_button.click()
                    time.sleep(interval)

                _LOGGER.debug("Found year==%s, start_year==%s, end_year=%s", year, start_year, end_year)
                ## Iterate over years
                while year <= end_year:

                    _LOGGER.info("Starting year %s", year)

                    end_month_of_this_year = 12 if year != end_year else end_month
                    month: int
                    for month in range(start_month, end_month_of_this_year + 1):

                        # <li class="sc-bttaWv fQmbrI">1</li> # selected
                        # <li class="sc-bttaWv hEsndb" tabindex="0">1</li> # not selected 
                        # <li class="sc-bttaWv Bhkiq" disabled="">10</li> # disabled
                        _LOGGER.debug("Waiting until a clickable %s-th month button is available", month)
                        month_button: WebElement = wait.until(EC.element_to_be_clickable([By.XPATH, f"//li[text()='{month}']"]))
                        if "fQmbrI" in month_button.get_attribute("class"):
                            # selected
                            _LOGGER.info("Already at month %s", month)
                        else:
                            # if month_button.is_displayed() and month_button.is_enabled(): # dont work
                            if "hEsndb" in month_button.get_attribute("class"):
                                # note selected
                                _LOGGER.info("Moving %s-th month", month)
                                month_button.click()
                                time.sleep(interval)
                            else:
                                _LOGGER.info("Found month %s does not have data", month)
                                continue

                        _LOGGER.debug("Waiting until a clickable upper left grid item is available")
                        first_grid_item: WebElement = wait.until(EC.element_to_be_clickable([By.CLASS_NAME, "virtuoso-grid-item"]))

                        _LOGGER.info("Clicking the upper left grid item")
                        first_grid_item.click()
                        time.sleep(interval)

                        idx: int = 0
                        last_date_s = None
                        while True:

                            _LOGGER.debug("Waiting until a visible date text is available")
                            date_elem: WebElement = wait.until(EC.visibility_of_element_located([By.CLASS_NAME, "sc-hmvnCu"]))
                            date_s: str = date_elem.text # 2019年9月5日
                            _LOGGER.info("Found date %s", date_s)

                            if date_s != last_date_s:
                                idx = 0
                                last_date_s = date_s

                            year_i, month_i, day_i = parse_date_str_int(date_s)

                            tareget_basename = f"wellnote_{year_i:04}-{month_i:02}-{day_i:02}_{idx:03}"
                            target_dir = os.path.join(download_dir, "wellnote", "album", f"{year_i:04}")
                            target_filepath_woe = os.path.join(target_dir, tareget_basename)

                            # if os.path.exists(target_filepath):
                            if glob.glob(target_filepath_woe + ".*"):
                                _LOGGER.warning("Skipping    %s because it exists", target_filepath_woe.replace(os.getcwd(), "."))
                                target_filepath = glob.glob(target_filepath_woe + ".*")[0]
                            else:
                                _LOGGER.debug("Waiting until a clickable vdots button is available")
                                vdots_button: WebElement = wait.until(EC.element_to_be_clickable([By.CLASS_NAME, "sc-bGaVxB"]))
                                _LOGGER.info("Clicking vdots button")
                                vdots_button.click()

                                _LOGGER.debug("Waiting until a clickable download button is available")
                                download_button: WebElement = wait.until(EC.element_to_be_clickable([By.CLASS_NAME, "sc-gnnDb"]))

                                with safe_download(driver, wait, download_dir) as download_result:
                                    _LOGGER.warning("Downloading %s", target_filepath_woe.replace(os.getcwd(), "."))
                                    _LOGGER.info("Clicking download button")
                                    download_button.click()
                                    num_of_download += 1
                                    time.sleep(interval)

                                downloaded_filepath: str = download_result.downloaded_filepath

                                extension: str = downloaded_filepath.split(".")[-1]
                                target_filepath = target_filepath_woe + "." + extension

                                os.makedirs(os.path.join(target_dir), exist_ok=True)
                                shutil.move(downloaded_filepath, target_filepath)

                            if not disable_update_time:
                                dt: datetime = datetime(year=year_i, month=month_i, day=day_i, hour=12, minute=00, second=00, microsecond=0)
                                disable_update_time_of_file(target_filepath, dt)
                            
                            swiper_button_next = None
                            with inspect_mode(driver, timeout_sec) as wait2:
                                _LOGGER.debug("Waiting until a clickable next button is available")
                                swiper_button_next: WebElement = wait2.until(EC.element_to_be_clickable([By.CLASS_NAME, "swiper-button-next"]))
                            if not swiper_button_next \
                            or "swiper-button-disabled" in swiper_button_next.get_attribute("class"):
                                _LOGGER.info("Breaking this month because next button is not found")
                                break

                            _LOGGER.info("Clicking the swiper_button_next")
                            swiper_button_next.click()
                            time.sleep(interval/4)

                            idx += 1

                        _LOGGER.debug("Waiting until a clickable close button is available")
                        # close_button: WebElement = wait2.until(EC.element_to_be_clickable([By.XPATH, "//*[name()='svg' and @class='sc-eldieg ljoTWs']"]))
                        close_button: WebElement = wait2.until(EC.element_to_be_clickable([By.CLASS_NAME, "sc-eldieg"]))

                        _LOGGER.info("Closing the preview window")
                        close_button.click()

                    move_next_year_button = None
                    with inspect_mode(driver, timeout_sec) as wait2:
                        _LOGGER.debug("Waiting until a clickable next year button is available")
                        move_next_year_button: WebElement = wait2.until(EC.element_to_be_clickable([By.XPATH, "//*[name()='svg' and @class='sc-emDsmM dRpxwk']"]))
                        # move_next_year_button: WebElement = wait2.until(EC.element_to_be_clickable([By.CLASS_NAME, "sc-emDsmM"]))
                    if not move_next_year_button:
                        _LOGGER.info("Breaking this year because next year button is not found")
                        break

                    _LOGGER.info("Moving the next year of %s ", year)
                    move_next_year_button.click()
                    time.sleep(interval)

                    year += 1
                    start_month = 1
                

    finally:
        _LOGGER.warning("Finishing album download. The number of downloaded pictures/movies is %s", num_of_download)
        driver.quit()
    return 0


################################################################################
# Utilities for CLI

class VersionAction(argparse.Action):
        
    def __call__(self, parser: argparse.ArgumentParser, namespace: argparse.Namespace, values, option_string=None):
        print(__version__)
        parser.exit()

def main_cli(*args: list[str]) -> int:
    if not args:
        args = sys.argv[1:]

    logging.basicConfig(stream=sys.stderr, format=LOG_FORMAT, level=logging.WARNING)

    ## "wellnote_downloader" command
    wellnote_downloader_ap: ArgumentParser = argparse.ArgumentParser( \
        prog="wellnote_downloader", description="Wellnote Downloader", \
        formatter_class=lambda prog: argparse.RawDescriptionHelpFormatter(prog, max_help_position=50, width=320))

    wellnote_downloader_ap.add_argument('--version', nargs=0, action=VersionAction, help="show program's version number and exit")

    _acceptable_levels = list(logging._nameToLevel.keys())
    _acceptable_levels.remove("NOTSET")

    sub_parsers_action: Action = wellnote_downloader_ap.add_subparsers(help="sub commands")

    ## "wellnote_downloader home" command
    wellnote_downloader_home_ap: ArgumentParser = sub_parsers_action.add_parser("home", help="download home")
    wellnote_downloader_home_ap.add_argument("--start", dest="start_yearmonth", metavar="YYYY-MM", nargs=None, default=None, required=False, help="Start year month")
    wellnote_downloader_home_ap.add_argument("--end", dest="end_yearmonth", metavar="YYYY-MM", nargs=None, default=None, required=False, help="End year month")
    wellnote_downloader_home_ap.add_argument("--interval", dest="interval", metavar="INT", nargs=None, type=int, default=DEFAULT_INTERVAL, help="Sleep time (sec) before sending next browser event")
    wellnote_downloader_home_ap.add_argument("--dir", dest="download_dir", metavar="DIR", nargs=None, default=None, help="Download directry. Default is ./download")
    wellnote_downloader_home_ap.add_argument("--browser", dest="browser", metavar="STR", nargs=None, default=None, help="Browser to automate. either firefox or chrome. default is firefox.")
    wellnote_downloader_home_ap.add_argument('--clear-profile', dest="clear_profile", action='store_true', default=False, help="Clear the browser profile to reset session, loaded files, etc.")
    wellnote_downloader_home_ap.add_argument('--disable-update-time', dest="disable_update_time", action='store_true', default=False, help="Disable to update birth/modify/access time of file.")
    wellnote_downloader_home_ap.add_argument('--loglevel', dest="log_level", metavar="LEVEL", nargs=None, default=None, help=f"Log level either {_acceptable_levels}.")
    wellnote_downloader_home_ap.set_defaults(handler=download_home)

    ## "wellnote_downloader album" command
    wellnote_downloader_album_ap: ArgumentParser = sub_parsers_action.add_parser("album", help="download album")
    wellnote_downloader_album_ap.add_argument("--start", dest="start_yearmonth", metavar="YYYY-MM", nargs=None, default=None, required=False, help="Start year month")
    wellnote_downloader_album_ap.add_argument("--end", dest="end_yearmonth", metavar="YYYY-MM", nargs=None, default=None, required=False, help="End year month")
    wellnote_downloader_album_ap.add_argument("--interval", dest="interval", metavar="INT", nargs=None, type=int, default=DEFAULT_INTERVAL, help="Sleep time (sec) before sending next browser event")
    wellnote_downloader_album_ap.add_argument("--dir", dest="download_dir", metavar="DIR", nargs=None, default=None, help="Download directry. Default is ./download")
    wellnote_downloader_album_ap.add_argument("--browser", dest="browser", metavar="STR", nargs=None, default=None, help="Browser to automate. either firefox or chrome. default is firefox.")
    wellnote_downloader_album_ap.add_argument('--clear-profile', dest="clear_profile", action='store_true', default=False, help="Clear the browser profile to reset session, loaded files, etc.")
    wellnote_downloader_album_ap.add_argument('--disable-update-time', dest="disable_update_time", action='store_true', default=False, help="Disable to update birth/modify/access time of file.")
    wellnote_downloader_album_ap.add_argument('--loglevel', dest="log_level", metavar="LEVEL", nargs=None, default=None, help=f"Log level either {_acceptable_levels}.")
    wellnote_downloader_album_ap.set_defaults(handler=download_album)


    arg_ns: Namespace = wellnote_downloader_ap.parse_args(args)
    key2value = vars(arg_ns)

    if "version" in key2value:
        del key2value["version"]

    if "log_level" in key2value:
        log_level: str = key2value.pop("log_level")
        if log_level:
            _LOGGER.setLevel(log_level.upper())

    if "start_yearmonth" in key2value:
        start_yearmonth = key2value.pop("start_yearmonth")
        if start_yearmonth:
            key2value["start_year"] = int(start_yearmonth.split("-")[0])
            key2value["start_month"] = int(start_yearmonth.split("-")[1])
    if "end_yearmonth" in key2value:
        end_yearmonth = key2value.pop("end_yearmonth")
        if end_yearmonth:
            key2value["end_year"] = int(end_yearmonth.split("-")[0])
            key2value["end_month"] = int(end_yearmonth.split("-")[1])

    if "handler" in key2value:
        handler = key2value.pop("handler")
        ans: int = handler(**key2value)
        if ans == 0:
            _LOGGER.info("Cheers!🍺")
    else:
        wellnote_downloader_ap.print_help()
    
    return 1

if __name__ == "__main__":
    # sys.exit(main_cli(*sys.argv[1:]))
    sys.exit(main_cli("home"))
