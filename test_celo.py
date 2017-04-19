from __future__ import print_function
from passwd import Passwd
import json
import os
import pytest
from shutil import copyfile

root_dir = os.path.dirname(__file__)

data = {
    'credentials_filename': os.path.join(root_dir, "test_credentials.json"),
    'domains': [],
    'credentials': [],
    'wrote_backup': False,
}

def _get_domains():
    for (dirpath, dirnames, filenames) in os.walk(os.path.join(root_dir, "manifests")):
        data['domains'].extend(['.'.join(f.split('.')[:-1]) for f in filenames])
        break  # to prevent recursion

def _get_credentials():
    data['credentials'] = json.load(open(data['credentials_filename']))


def _do_backup():
    if data['wrote_backup']:
        return
    copyfile(data['credentials_filename'], data['credentials_filename'] + ".bak")


def _write_credentials():
    _do_backup()
    data['credentials'] = json.dump(open(data['credentials_filename'], 'w'))



_get_domains()
_get_credentials()

@pytest.mark.parametrize('domain', data['domains'])
def test_has_credentials(domain):
     assert domain in data['credentials'], "No credentials for domain {}".format(domain)


@pytest.mark.parametrize('domain', data['credentials'].keys())
def test_login(domain):
    creds = data['credentials'][domain]
    with Passwd(domain) as passwd:
        assert passwd.sign_in(creds['user'], creds['pass']), "Could not sign in to {}".format(domain)

@pytest.mark.parametrize('domain', data['credentials'].keys())
def test_fail_login(domain):
    creds = data['credentials'][domain]
    with Passwd(domain) as passwd:
        assert not passwd.sign_in(creds['user'], 'notmypassword'), "Could sign in to {} with invalid password".format(domain)

# @pytest.mark.parametrize('domain', data['credentials'].keys())
# def test_change(domain):
