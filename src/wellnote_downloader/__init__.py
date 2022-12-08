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

__version__ = "0.4.0"

import argparse
from argparse import ArgumentParser, Action, Namespace
from contextlib import contextmanager
from getpass import getpass
import glob
import logging
import os
import re
import shutil
import sys
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

# logger
_LOGGER: logging.Logger = logging.getLogger(__name__)

LOG_FORMAT: str = '%(asctime)s |  %(levelname)-7s | %(message)s (%(filename)s L%(lineno)s %(name)s)'

INTERVAL: int = 1

################################################################################
# Utilities for Selenium


@contextmanager
def inspect_mode(driver, original_timeout, inspect_sec=1):
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


def download_is_completed(download_dir, last_newest_file):

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


################################################################################
# Utilities for Wellnote


def download_album(start_year: int = 2009, start_month: int = 1, \
                   end_year: int = 2023, end_month: int = 12,  \
                   download_dir: str = None, browser: str = None) -> int:

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

    # download_dir: str = "/Users/nogayama1/Downloads"
    if not download_dir:
        # download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        download_dir = os.path.join(os.getcwd(), "Downloads")

    if not browser:
        browser = "firefox"
    timeout_sec: int = 60

    driver: WebDriver = None
    if browser == "chrome":
        chrome_options = webdriver.ChromeOptions()
        prefs = {'download.default_directory': download_dir}
        chrome_options.add_experimental_option('prefs', prefs)
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), chrome_options=chrome_options)
    elif browser == "firefox":
        options = FirefoxOptions()
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.dir", download_dir)
        driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
    else:
        raise ValueError(f"browser type '{browser}' is not supported.")
    driver.implicitly_wait(timeout_sec)
    wait = WebDriverWait(driver, timeout_sec)

    try:
        _LOGGER.info("Geting wellnote.jp")
        driver.get("https://wellnote.jp/")
        time.sleep(INTERVAL)

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
            time.sleep(INTERVAL)

            if True:
                wait.until(EC.staleness_of(password_form))

                _LOGGER.debug("Waiting until a clickable albums button is available")
                # <a class="sc-jWWnA hivVBT" href="/albums">
                album_button: WebElement = wait.until(EC.element_to_be_clickable([By.XPATH, "//a[@href='/albums']"]))

                _LOGGER.info("Clicking the album button")
                album_button.click()
                time.sleep(INTERVAL)

                if True:
                    ## Go to start year
                    year: int = 9999
                    while year >= 2009:  # We can't go back to the years before wellnote's inception

                        _LOGGER.debug("Waiting until a year text is available")
                        # year = wait.until(EC.visibility_of_element_located([By.XPATH, "//div[contains(text(), '年')]"])) # dont work
                        year_text: str = wait.until(EC.visibility_of_element_located([By.XPATH, "//div[@class='sc-bOtlzW fgPidp']"]))
                        year = int(year_text.text.replace("年", ""))

                        if year == start_year:
                            break

                        move_previous_year_button = None
                        with inspect_mode(driver, timeout_sec) as wait2:
                            _LOGGER.debug("Waiting until a clickable next button is available")
                            move_previous_year_button: WebElement = wait2.until(EC.element_to_be_clickable([By.XPATH, "//*[name()='svg' and @class='sc-jFkwbb ruuVe']"]))
                        if not move_previous_year_button:
                            _LOGGER.info("Breaking this year because previous button is not found")
                            start_month = 1
                            break

                        _LOGGER.info("Moving previous year of %s ", year)
                        move_previous_year_button.click()
                        time.sleep(INTERVAL)

                    ## Iterate over years
                    while year <= end_year:

                        _LOGGER.info("Starting year %s", year)

                        end_month_of_this_year = 12 if year != end_year else end_month
                        month: int
                        for month in range(start_month, end_month_of_this_year + 1):

                            _LOGGER.debug("Waiting until a clickable %s-th month button is available", month)
                            month_button: WebElement = wait.until(EC.element_to_be_clickable([By.XPATH, f"//li[text()='{month}']"]))
                            if "jAQwgG" in month_button.get_attribute("class"):
                                # selected
                                _LOGGER.info("Already at month %s", month)
                            else:
                                # if month_button.is_displayed() and month_button.is_enabled(): # dont work
                                if "RJZN" in month_button.get_attribute("class"):
                                    _LOGGER.info("Moving %s-th month", month)
                                    month_button.click()
                                    time.sleep(INTERVAL)
                                else:
                                    _LOGGER.info("Found month %s does not have data", month)
                                    continue

                            _LOGGER.debug("Waiting until a clickable upper left grid item is available")
                            first_grid_item: WebElement = wait.until(EC.element_to_be_clickable([By.CLASS_NAME, "virtuoso-grid-item"]))

                            _LOGGER.info("Clicking the upper left grid item")
                            first_grid_item.click()
                            time.sleep(INTERVAL)

                            idx: int = 0
                            last_date_s = None
                            while True:

                                _LOGGER.debug("Waiting until a visible date text is available")
                                date_elem: WebElement = wait.until(EC.visibility_of_element_located([By.CLASS_NAME, "sc-dWbSDx"]))
                                date_s: str = date_elem.text
                                _LOGGER.info("Found date %s", date_s)

                                if date_s != last_date_s:
                                    idx = 0
                                    last_date_s = date_s

                                match: re.Match = re.search("(\d+)\s*年\s*(\d+)\s*月\s*(\d+)\s*日", date_s)
                                year_i: int = int(match.group(1))
                                month_i: int = int(match.group(2))
                                day_i: int = int(match.group(3))

                                tareget_basename = f"wellnote_{year_i:04}-{month_i:02}-{day_i:02}_{idx:03}"
                                target_dir = os.path.join(download_dir, "wellnote", f"{year_i:04}")
                                target_filepath_woe = os.path.join(target_dir, tareget_basename)

                                # if os.path.exists(target_filepath):
                                if glob.glob(target_filepath_woe + ".*"):
                                    _LOGGER.warning("Skipping    %s because it exists", target_filepath_woe.replace(os.getcwd(), "."))
                                else:
                                    _LOGGER.warning("Downloading %s", target_filepath_woe.replace(os.getcwd(), "."))

                                    filepaths: list[str] = glob.glob(os.path.join(download_dir, "*"))
                                    last_newest_file = max(filepaths, key=lambda fp: os.path.getmtime(fp)) if filepaths else None

                                    _LOGGER.debug("Waiting until a clickable vdots button is available")
                                    vdots_button: WebElement = wait.until(EC.element_to_be_clickable([By.CLASS_NAME, "sc-hCwLRM"]))
                                    _LOGGER.info("Clicking vdots button")
                                    vdots_button.click()

                                    _LOGGER.debug("Waiting until a clickable download button is available")
                                    download_button: WebElement = wait.until(EC.element_to_be_clickable([By.CLASS_NAME, "sc-hLVXRe"]))
                                    _LOGGER.info("Clicking download button")
                                    download_button.click()

                                    time.sleep(INTERVAL)

                                    _LOGGER.debug("Waiting until the download is completed")
                                    downloaded_filepath = wait.until(download_is_completed(download_dir, last_newest_file))

                                    extension: str = downloaded_filepath.split(".")[-1]
                                    target_filepath = target_filepath_woe + "." + extension

                                    os.makedirs(os.path.join(target_dir), exist_ok=True)
                                    shutil.move(downloaded_filepath, target_filepath)

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
                                # time.sleep(INTERVAL)

                                idx += 1

                            _LOGGER.debug("Waiting until a clickable html body is available")
                            close_button: WebElement = wait2.until(EC.element_to_be_clickable([By.XPATH, "//*[name()='svg' and @class='sc-edERGn jYcwJ']"]))

                            _LOGGER.info("Closing the preview window")
                            close_button.click()

                        move_next_year_button = None
                        with inspect_mode(driver, timeout_sec) as wait2:
                            _LOGGER.debug("Waiting until a clickable next year button is available")
                            move_next_year_button: WebElement = wait2.until(EC.element_to_be_clickable([By.XPATH, "//*[name()='svg' and @class='sc-jFkwbb lbXnTj']"]))
                        if not move_next_year_button:
                            _LOGGER.info("Breaking this year because next year button is not found")
                            break

                        _LOGGER.info("Moving the next year of %s ", year)
                        move_next_year_button.click()
                        time.sleep(INTERVAL)

                        year += 1
                        start_month = 1
    finally:
        driver.quit()
    return 0


################################################################################
# Utilities for CLI


def main_cli(*args: list[str]) -> int:
    if not args:
        args = sys.argv[1:]

    logging.basicConfig(stream=sys.stderr, format=LOG_FORMAT, level=logging.WARNING)
    _LOGGER.setLevel(logging.INFO)

    ## "wellnote_downloader" command
    wellnote_downloader_ap: ArgumentParser = argparse.ArgumentParser( \
        prog="wellnote_downloader", description="Wellnote Downloader", \
        formatter_class=lambda prog: argparse.RawDescriptionHelpFormatter(prog, max_help_position=50, width=320))

    sub_parsers_action: Action = wellnote_downloader_ap.add_subparsers(help="sub commands")

    ## "wellnote_downloader album" command
    wellnote_downloader_album_ap: ArgumentParser = sub_parsers_action.add_parser("album", help="download album")
    wellnote_downloader_album_ap.add_argument("--start", dest="start_yearmonth", metavar="YYYY-MM", nargs=None, default=None, required=False, help="start year month")
    wellnote_downloader_album_ap.add_argument("--end", dest="end_yearmonth", metavar="YYYY-MM", nargs=None, default=None, required=False, help="end year month")
    wellnote_downloader_album_ap.add_argument("--dir", dest="download_dir", metavar="DIR", nargs=None, default=None, help="Download directry. Default is ./download")
    wellnote_downloader_album_ap.add_argument("--browser", dest="browser", metavar="STR", nargs=None, default=None, help="Browser to automate. either firefox or chrome. default is firefox.")
    wellnote_downloader_album_ap.set_defaults(handler=download_album)

    arg_ns: Namespace = wellnote_downloader_ap.parse_args(args)
    key2value = vars(arg_ns)

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
        ans = handler(**key2value)
    else:
        wellnote_downloader_ap.print_help()

    if ans == 0:
        _LOGGER.info("Cheers!🍺")
    return ans


if __name__ == "__main__":
    sys.exit(main_cli(*sys.argv[1:]))
