# coding=utf-8
"""Tests related to multiple plugins."""
import unittest
from unittest import SkipTest
from urllib.parse import urljoin
from pprint import pprint
from functools import reduce

from pulp_smash import api, config, utils
from pulp_smash.pulp3.constants import REPO_PATH
from pulp_smash.pulp3.utils import (
    gen_remote,
    gen_repo,
    gen_distribution,
    get_added_content_summary,
    get_content_summary,
    get_removed_content_summary,
    require_pulp_plugins,
    sync,
)

from pulpcore.tests.functional.api.using_plugin.constants import (
    CERTGUARD_X509_PATH,
    CERT_CA_FILE_PATH,
    CERT_CLIENT_FILE_PATH,
    FILE_DISTRIBUTION_PATH,
    FILE_FIXTURE_MANIFEST_URL,
    FILE_FIXTURE_SUMMARY,
    FILE_REMOTE_PATH,
    KEYS_CLIENT_FILE_PATH,
    RPM_FIXTURE_SUMMARY,
    RPM_REMOTE_PATH,
    RPM_UNSIGNED_FIXTURE_URL,
)
from pulpcore.tests.functional.api.using_plugin.utils import (
    create_file_publication,
    gen_file_remote,
)
from pulpcore.tests.functional.api.using_plugin.utils import set_up_module  # noqa


def setUpModule():
    """Conditions to skip tests.

    Skip tests if not testing Pulp 3, or if either pulpcore, pulp_file
    or pulp_rpm aren't installed.

    refer :meth:`pulpcore.tests.functional.api.using_plugin.utils.set_up_module`
    """
    set_up_module()
    require_pulp_plugins({"pulp_certguard"}, SkipTest)


class SyncSSLTestCase(unittest.TestCase):
    """Test sync of content protected by certificates."""

    def test_sync_ssl(self):
        """Test sync of content protected by certificates."""
        cfg = config.get_config()
        client = api.Client(cfg)

        with open(CERT_CLIENT_FILE_PATH, "r") as cert_client_file:
            # client_cert = str(cert_client_file.read()).replace('\n', '')
            client_cert = str(cert_client_file.read())

        with open(KEYS_CLIENT_FILE_PATH, "r") as keys_client_file:
            # client_key = str(keys_client_file.read()).replace('\n', '')
            client_key = str(keys_client_file.read())

        with open(CERT_CA_FILE_PATH, "rb") as cert_ca_file:
            certguard = client.post(
                CERTGUARD_X509_PATH,
                data={"name": utils.uuid4()},
                files={"ca_certificate": cert_ca_file},
            )

        self.addCleanup(client.delete, certguard["_href"])

        repo = client.post(REPO_PATH, gen_repo())
        self.addCleanup(client.delete, repo["_href"])

        remote = client.post(FILE_REMOTE_PATH, gen_file_remote())
        self.addCleanup(client.delete, remote["_href"])

        sync(cfg, remote, repo)
        repo = client.get(repo["_href"])

        publication = create_file_publication(cfg, repo)
        self.addCleanup(client.delete, publication["_href"])

        distribution = client.post(
            FILE_DISTRIBUTION_PATH,
            gen_distribution(
                publication=publication["_href"], content_guard=certguard["_href"]
            ),
        )
        self.addCleanup(client.delete, distribution["_href"])

        pulp_url = reduce(
            urljoin,
            (
                cfg.get_content_host_base_url(),
                "//" + distribution["base_url"] + "/",
                "PULP_MANIFEST",
            ),
        )

        repo = client.post(REPO_PATH, gen_repo())
        self.addCleanup(client.delete, repo["_href"])

        from ipdb import set_trace

        remote_ssl = client.post(
            FILE_REMOTE_PATH,
            gen_file_remote(
                url=pulp_url,
                ssl_client_certificate=client_cert,
                ssl_client_key=client_key,

            ),
        )
        self.addCleanup(client.delete, remote_ssl["_href"])

        set_trace()

        sync(cfg, remote_ssl, repo)
        repo = client.get(repo["_href"])
