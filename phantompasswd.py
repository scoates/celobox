#!/usr/bin/env python

from selenium import webdriver
import sys
import json
import logging
import getpass
import os
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
import time

class PasswdDomainError(Exception):
    pass

class Passwd(object):
    def __enter__(self):
        dcap = dict(DesiredCapabilities.PHANTOMJS)
        if 'user_agent' in self.data:
            dcap["phantomjs.page.settings.userAgent"] = self.data['user_agent']


        service_args = [
            '--proxy=localhost:8080',
            '--proxy-type=http',
        ]

        self.driver = webdriver.PhantomJS(desired_capabilities=dcap, service_args=service_args)
        self.driver.set_window_size(1024, 768)
        return self

    def __exit__(self, type, value, traceback):
        self.driver.quit()

    def __init__(self, domain, debug=False):
        self.domain = domain
        self.data = self.load_data(domain)
        if debug:
            loglevel = logging.DEBUG
        else:
            loglevel = logging.INFO
        logging.basicConfig(level=loglevel)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Logging enabled')

    def load_data(self, domain):
        try:
            return json.load(open(os.path.join('manifests', '%s.json' % domain)))
        except IOError:
            raise PasswdDomainError('Manifest not found for %s' % domain)

    def test_success(self, container):
        if 'landing' == container['success']['test']:
            return container['success']['name'] == self.driver.current_url

        raise ValueError("Unknown login verification test")

    def sign_in(self, username, password):
        self.logger.debug('Signing in: %s' % username)
        login_data = self.data['login']

        self.driver.get(login_data['urls']['form'])
        time.sleep(10)
        self.driver.find_element_by_css_selector(login_data['form']['username']).send_keys(username)
        self.driver.find_element_by_css_selector(login_data['form']['password']).send_keys(password)

        self.driver.find_element_by_css_selector(login_data['form']['submit']).click()
        time.sleep(10)

        success = self.test_success(self.data['login'])
        if success:
            self.username = username
            self.old_pass = password
        return success

    # def change_password(self, password):
    #     self.logger.debug('Changing password.')
    #     form_page = self.session.get(
    #         self.data['password']['urls']['form']).content

    #     if 'literal' in self.data['password']['form']:
    #         payload = self.data['password']['form']['literal']
    #     else:
    #         payload = {}

    #     for field in self.data['password']['form']['new_password']:
    #         payload[field] = password

    #     if 'old_password' in self.data['password']['form']:
    #         payload = dict(payload.items() + {
    #             self.data['password']['form']['old_password']: self.old_pass
    #             }.items())

    #     if 'csrf' in self.data['password']['form']:
    #         csrf = self.get_csrf(form_page, 'password')
    #         payload = dict(payload.items() + {
    #             self.data['password']['form']['csrf']: csrf}.items())

    #     self.session.headers.update(
    #         {'referer': self.data['password']['urls']['form']})

    #     self.session.post(
    #         self.data['password']['urls']['post'], data=payload)
    #     success = self.sign_in(self.username, password)
    #     if success:
    #         self.old_pass = password
    #     return success

def main():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("domain", help="domain name of app")
    parser.add_argument(
        "-d", "--debug", help="show debug output", action="store_true")
    parser.add_argument(
        "--nochange",
        help="Sign in only; don't change password",
        action="store_true")
    parser.add_argument("--username", help="Username (avoids prompt)")
    parser.add_argument("--oldpass", help="Old Password (avoids prompt)")
    parser.add_argument("--newpass", help="New Password (avoids prompt)")
    args = parser.parse_args()

    with Passwd(args.domain, debug=args.debug) as passwd:
        if args.username:
            username = args.username
            print "Using provided username"
        else:
            username = raw_input('Username: ')

        if args.oldpass:
            old_pass = args.oldpass
            print "Using provided password"
        else:
            old_pass = getpass.getpass('Old password: ')

        if passwd.sign_in(username, old_pass):
            print "Sign in success."
        else:
            print "Sign in failed."
            sys.exit(1)

    if args.nochange:
        sys.exit(0)

    # if args.newpass:
    #     new_pass = args.newpass
    # else:
    #     while True:
    #         new_pass = getpass.getpass('New password: ')
    #         new_pass2 = getpass.getpass('New password (again): ')
    #         if new_pass == new_pass2:
    #             break
    #         else:
    #             print "Passwords do not match."

    # if passwd.change_password(new_pass):
    #     print "Password changed!"
    # else:
    #     print "Password change failed."


if __name__ == "__main__":
    main()
