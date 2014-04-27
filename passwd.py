#!/usr/bin/env python
import sys
import json
import logging
import getpass
import requests
from bs4 import BeautifulSoup


class PasswdDomainException(Exception):
    pass


class Passwd:
    def __init__(self, domain, debug=False):
        self.domain = domain
        self.data = self.load_data(domain)
        self.csrf_token = None
        if debug:
            loglevel = logging.DEBUG
        else:
            loglevel = logging.INFO
        logging.basicConfig(level=loglevel)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Logging enabled')
        self.new_session()

    def new_session(self):
        self.session = requests.Session()

    def load_data(self, domain):
        try:
            return json.load(open('manifests/%s.json' % domain))
        except (IOError):
            raise PasswdDomainException

    def get_csrf(self, page_data):
        bs = BeautifulSoup(page_data)
        el = bs.select(self.data['csrf_token']['selector'])[0]
        token = el[self.data['csrf_token']['attribute']]
        self.logger.debug('Found CSRF token: %s' % token)
        return token

    def test_success(self, post, container):
        if 'header-present' == container['success']['test']:
            return container['success']['name'] in post.headers

        if 'landing' == container['success']['test']:
            return container['success']['name'] == post.request.url

        if 'page' == container['success']['test']:
            r = self.session.get(container['success']['name'])
            return r.status_code == requests.codes.ok

        raise ValueError("Unknown login verification test")

    def sign_in(self, username, password):
        self.logger.debug('Signing in: %s' % username)

        verify_ssl = self.data.get('verify_ssl', True)

        form_page = self.session.get(
            self.data['login']['urls']['form'], verify=verify_ssl).content

        payload = dict({
            self.data['login']['form']['username']: username,
            self.data['login']['form']['password']: password,
        }.items() + self.data['login']['form'].get('literal', {}).items())
        if 'csrf' in self.data['login']['form']:
            csrf = self.get_csrf(form_page)
            payload = dict(payload.items() + {
                self.data['login']['form']['csrf']: csrf}.items())

        post = self.session.post(
            self.data['login']['urls']['post'],
            data=payload,
            verify=verify_ssl)
        success = self.test_success(post, self.data['login'])
        if success:
            self.username = username
            self.old_pass = password
        return success

    def change_password(self, password):
        self.logger.debug('Changing password.')
        form_page = self.session.get(
            self.data['password']['urls']['form']).content

        if 'literal' in self.data['password']['form']:
            payload = self.data['password']['form']['literal']
        else:
            payload = {}

        for field in self.data['password']['form']['new_password']:
            payload[field] = password

        if 'old_password' in self.data['password']['form']:
            payload = dict(payload.items() + {
                self.data['password']['form']['old_password']: self.old_pass
                }.items())

        if 'csrf' in self.data['password']['form']:
            csrf = self.get_csrf(form_page)
            payload = dict(payload.items() + {
                self.data['password']['form']['csrf']: csrf}.items())

        self.session.post(self.data['password']['urls']['post'], data=payload)
        success = self.sign_in(self.username, password)
        if success:
            self.new_session()
            self.old_pass = password
        return success


if __name__ == "__main__":

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

    try:
        passwd = Passwd(args.domain, debug=args.debug)
    except (PasswdDomainException):
        print "Invalid domain"
        sys.exit(255)

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
