#!/usr/bin/env python
import sys
import os
import json
import logging
import getpass
import requests
from bs4 import BeautifulSoup


class Passwd(object):
    def __init__(self, domain, loader, debug=False):
        self.domain = domain
        self.data = loader(domain)
        self.csrf_token = None
        if debug:
            loglevel = logging.DEBUG
        else:
            loglevel = logging.INFO
        logging.basicConfig(level=loglevel)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('Logging enabled')
        self.session = requests.Session()
        self.session.headers.update(self.data.get('headers', {}))

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
            self.data['login']['urls']['post'], data=payload, verify=verify_ssl)
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


def interactive_reader(domain, field):
    """
        Gets username, old password, and new password info from the user
        via the TTY
    """
    if field == 'username':
        if 'USERNAME' in os.environ:
            sys.stderr.write("Using provided username\n")
            return os.environ['USERNAME']
        else:
            return raw_input('Username: ')
    elif field == 'old_password':
        if 'OLD_PASS' in os.environ:
            sys.stderr.write("Using provided password\n")
            return os.environ['OLD_PASS']
        else:
            return getpass.getpass('Old password: ')
    elif field == 'new_pass':
        return getpass.getpass('New password: ')
    elif field == 'new_pass2':
        return getpass.getpass('New password (again): ')
    else:
        return raw_input('%s: ' % field)


def json_loader(domain):
    """
        Load the login/change password data for the specified domain
    """
    try:
        return json.load(open('manifests/%s.json' % domain))
    except IOError:
        sys.exit('No manifest found for %s' % domain)


def change_password(domain, reader=interactive_reader):
    """
        Change the password for `domain`.  `reader` is a function that
        takes 2 arguments: the domain and the field to read.  It should
        return a unicode with the value for that field for that domain.
    """
    passwd = Passwd(domain, loader=json_loader, debug=('DEBUG' in os.environ))

    username = reader(domain, 'username')
    old_pass = reader(domain, 'old_password')

    if not passwd.sign_in(username, old_pass):
        sys.exit("Sign in failed.")

    while True:
        new_pass = reader(domain, 'new_pass')
        new_pass2 = reader(domain, 'new_pass2')
        if new_pass == new_pass2:
            break
        else:
            sys.stderr.write("Passwords do not match.\n")

    if passwd.change_password(new_pass):
        sys.stderr.write("Password changed!\n")
    else:
        sys.stderr.write("Password change failed.\n")


if __name__ == "__main__":

    try:
        domain = sys.argv[1]
    except IndexError:
        sys.exit("Usage: %s domain_name" % sys.argv[0])

    change_password(domain)

