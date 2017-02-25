from __future__ import print_function
from passwd import Passwd
import json
import os
import pytest

root_dir = os.path.dirname(__file__)

domains = []
for (dirpath, dirnames, filenames) in os.walk(os.path.join(root_dir, "manifests")):
    domains.extend(['.'.join(f.split('.')[:-1]) for f in filenames])
    break  # to prevent recursion

creds_file = os.path.join(root_dir, "test_credentials.json")
credentials = json.load(file(creds_file))

@pytest.mark.parametrize('domain', domains)
def test_has_credentials(domain):
     assert domain in credentials, "No credentials for domain {}".format(domain)

@pytest.mark.parametrize('domain', credentials.keys())
def test_login(domain):
    creds = credentials[domain]
    with Passwd(domain) as passwd:
        assert passwd.sign_in(creds['user'], creds['pass']), "Could not sign in to {}".format(domain)
