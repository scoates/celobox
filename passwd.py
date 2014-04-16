#!/usr/bin/env python
import sys
import os
import json
import logging
import getpass
import requests
from bs4 import BeautifulSoup


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
        self.session = requests.Session()

    def load_data(self, domain):
        return json.load(open('manifests/%s.json' % domain))

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

        raise ValueError("Unknown login verification test")

    def sign_in(self, username, password):
        self.logger.debug('Signing in: %s' % username)
        form_page = self.session.get(
            self.data['login']['urls']['form']).content

        payload = dict({
            self.data['login']['form']['username']: username,
            self.data['login']['form']['password']: password,
        }.items() + self.data['login']['form']['literal'].items())
        if 'csrf' in self.data['login']['form']:
            csrf = self.get_csrf(form_page)
            payload = dict(payload.items() + {
                self.data['login']['form']['csrf']: csrf}.items())

        post = self.session.post(
            self.data['login']['urls']['post'], data=payload)
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

        post = self.session.post(
            self.data['password']['urls']['post'], data=payload)
        success = self.test_success(post, self.data['password'])
        return success


if __name__ == "__main__":

    try:
        domain = sys.argv[1]
    except IndexError:
        print "Usage: %s domain_name" % sys.argv[0]
        sys.exit(255)

    passwd = Passwd(domain, debug=('DEBUG' in os.environ))

    if 'USERNAME' in os.environ:
        username = os.environ['USERNAME']
        print "Using provided username"
    else:
        username = raw_input('Username: ')

    if 'OLD_PASS' in os.environ:
        old_pass = os.environ['OLD_PASS']
        print "Using provided password"
    else:
        old_pass = getpass.getpass('Old password: ')

    if not passwd.sign_in(username, old_pass):
        print "Sign in failed."
        sys.exit(1)

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
