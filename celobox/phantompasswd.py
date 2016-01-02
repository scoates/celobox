#!/usr/bin/env python

from selenium import webdriver
import sys
import json
import logging
import getpass
import os
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from enum import Enum
import time
import requests
import yaml
from pkg_resources import resource_filename

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36"


class PasswdDomainError(Exception):
    pass


class ContentTypes(Enum):
    """Enumerate possible content type hints."""

    JSON = 'json'
    YAML = 'yaml'


class Passwd(object):

    def __init__(self, domain, debug=False, service_args='', ignore_ssl_errors=False):
        self.domain = domain
        self.ignore_ssl_errors = ignore_ssl_errors
        self.service_args = service_args
        if ignore_ssl_errors:
            self.service_args = (self.service_args or []) + ['--ignore-ssl-errors=yes']
        if debug:
            loglevel = logging.DEBUG
        else:
            loglevel = logging.INFO
        logging.basicConfig(level=loglevel)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Logging enabled')

    def __enter__(self):
        dcap = dict(DesiredCapabilities.PHANTOMJS)
        dcap["phantomjs.page.settings.userAgent"] = USER_AGENT
        self.driver = webdriver.PhantomJS(desired_capabilities=dcap, service_args=self.service_args)
        self.driver.set_window_size(1024, 768)

        self.data = self.load_data(self.domain)

        return self

    def __exit__(self, type, value, traceback):
        self.driver.quit()

    @property
    def throttle(self):
        return self.data.get('throttle', 0)

    def load_manifest(self, domain):
        self.driver.get("http://{domain}".format(domain=domain))
        try:
            elt = self.driver.find_element_by_css_selector('link[rel="password-manifest"]')
            resp = requests.get(elt.get_attribute('href'), verify=not self.ignore_ssl_errors)
            return self.load_data_from_content(resp.content)
        except NoSuchElementException:
            return {}

    def load_data(self, domain):
        manifests_path = self._get_manifests_path()
        domain = self._get_safe_domain(domain)

        for content_type in ContentTypes:
            try:
                content = open(os.path.join(manifests_path, '{}.{}'.format(domain, content_type.value)))
                return self.load_data_from_content(content, content_type)
            except IOError:
                # file unreadable (not found)
                pass

        # have not yet found a local manifest, so try to load via web
        return self.load_manifest(domain)


    def load_data_from_content(self, content, hint=None):
        if hint is None or hint == ContentTypes.JSON:
            try:
                return json.load(content)
            except ValueError:
                if hint == self.JSON:
                    return False
                # otherwise: pass through to other parsers

        if hint is None or hint == ContentTypes.YAML:
            try:
                parsed = yaml.safe_load(content)
                # most strings parse to be valid YAML (it's very permissive)
                # so, let's check a known key to be sure.
                if parsed and 'celobox_manifest' in parsed:
                    return parsed
                if hint == self.YAML:
                    # no key in expected-to-be-YAML content
                    return False
                # otherwise: pass through (this is not YAML)
            except yaml.YAMLError:
                if hint == self.YAML:
                    return False
                # otherwise: pass through to other parsers

        # out of parsers; no return yet, means we couldn't parse the content
        return False


    def _get_manifests_path(self):
        """ todo """
        return resource_filename(__name__, 'manifests')


    def _get_safe_domain(self, domain):
        """ todo: avoid "/path/to/somesecret" or "../../etc/whatever" """
        return domain


    def test_success(self, container):
        if 'landing' == container['success']['test']:
            return container['success']['name'] == self.driver.current_url

        raise ValueError("Unknown login verification test")

    def click_login_url(self):
        for a in self.driver.find_elements_by_tag_name('a'):
            text = a.text.lower()
            if 'log in' in text or 'login' in text or 'sign in' in text:
                self.driver.get(a.get_attribute('href'))
                return True
        return False

    def find_login_form(self):
        for form in self.driver.find_elements_by_tag_name('form'):
            text_input = form.find_elements_by_css_selector('input[type="text"]')
            password_input = form.find_elements_by_css_selector('input[type="password"]')

            if len(text_input) == 1 and len(password_input) == 1:
                return form

    def heuristic_sign_in(self, username, password):
        self.driver.get('http://{domain}'.format(domain=self.domain))
        time.sleep(3)
        login_clicked = self.click_login_url()
        if login_clicked:
            time.sleep(3)
            url = self.driver.current_url
            form = self.find_login_form()
            if form:
                form.find_element_by_css_selector('input[type="text"]').send_keys(username)
                form.find_element_by_css_selector('input[type="password"]').send_keys(password)
                form.find_element_by_css_selector('input[type="password"]').submit()
                time.sleep(3)
                return url != self.driver.current_url

        return False

    def sign_in(self, username, password):
        self.logger.debug('Signing in: %s' % username)
        login_data = self.data.get('login')
        if login_data is None:
            success = self.heuristic_sign_in(username, password)
        else:
            self.driver.get(login_data['url'])
            time.sleep(self.throttle)
            self.driver.find_element_by_css_selector(login_data['form']['username']).send_keys(username)
            self.driver.find_element_by_css_selector(login_data['form']['password']).send_keys(password)

            self.driver.find_element_by_css_selector(login_data['form']['submit']).submit()
            time.sleep(self.throttle)

            success = self.test_success(self.data['login'])
        if success:
            self.username = username
            self.old_pass = password
        return success

    def change_password(self, password):
        self.logger.debug('Changing password.')
        password_data = self.data['password']
        self.driver.get(password_data['url'])

        time.sleep(self.throttle)
        if 'old_password' in password_data['form']:
            self.driver.find_element_by_css_selector(password_data['form']['old_password']).send_keys(self.old_pass)
        self.driver.find_element_by_css_selector(password_data['form']['new_password']).send_keys(password)
        if 'verify_password' in password_data['form']:
            self.driver.find_element_by_css_selector(password_data['form']['verify_password']).send_keys(password)

        self.driver.find_element_by_css_selector(password_data['form']['submit']).submit()
        time.sleep(self.throttle)

        self.driver.delete_all_cookies()

        success = self.sign_in(self.username, password)
        if success:
            self.old_pass = password
        return success

def main():
    from argparse import ArgumentParser, REMAINDER

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
    parser.add_argument("--ignore-ssl-errors", help="Ignore SSL certificate errors", action="store_true")
    parser.add_argument("--phantom", help="PhantomJS arguments (use this last; it gobbles up the remainder)", nargs=REMAINDER)
    args = parser.parse_args()

    with Passwd(args.domain, debug=args.debug, service_args=args.phantom, ignore_ssl_errors=args.ignore_ssl_errors) as passwd:
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

        if args.newpass:
            new_pass = args.newpass
        else:
            while True:
                new_pass = getpass.getpass('New password: ')
                new_pass2 = getpass.getpass('New password (again): ')
                if new_pass == new_pass2:
                    break
                else:
                    print "Passwords do not match."

        if passwd.change_password(new_pass):
            print "Password changed!"
        else:
            print "Password change failed."


if __name__ == "__main__":
    main()
