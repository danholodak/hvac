from unittest import TestCase
from unittest import skipIf

from parameterized import parameterized

from hvac import exceptions, Client
from tests import utils
from tests.utils.hvac_integration_test_case import HvacIntegrationTestCase
import pytest


class TestCert(HvacIntegrationTestCase, TestCase):
    TEST_MOUNT_POINT = "cert-test"
    TEST_ROLE_NAME = "testrole"
    cert = utils.create_client()._adapter._kwargs.get("cert")
    with open(utils.get_config_file_path("client-cert.pem")) as fp:
        TEST_CERTIFICATE = fp.read()

    def setUp(self):
        super(TestCert, self).setUp()
        if "%s/" % self.TEST_MOUNT_POINT not in self.client.list_auth_backends():
            self.client.enable_auth_backend(
                backend_type="cert",
                mount_point=self.TEST_MOUNT_POINT,
            )
        _ = self.client.auth.cert.create_ca_certificate_role(
            name=self.TEST_ROLE_NAME,
            certificate=self.TEST_CERTIFICATE,
            mount_point=self.TEST_MOUNT_POINT,
        )

    def tearDown(self):
        super(TestCert, self).tearDown()

    def test_create_ca_certificate_role(self):
        response = self.client.auth.cert.create_ca_certificate_role(
            name="testrole2",
            certificate=self.TEST_CERTIFICATE,
            mount_point=self.TEST_MOUNT_POINT,
        )

        self.assertEqual(first=204, second=response.status_code)

    def test_read_ca_certificate_role(self):
        response = self.client.auth.cert.read_ca_certificate_role(
            name=self.TEST_ROLE_NAME,
            mount_point=self.TEST_MOUNT_POINT,
        )

        self.assertEqual(
            first=self.TEST_ROLE_NAME,
            second=response["data"]["display_name"],
        )

    def test_list_certificate_roles(self):
        response = self.client.auth.cert.list_certificate_roles(
            mount_point=self.TEST_MOUNT_POINT,
        )

        self.assertEqual(first=response["data"]["keys"], second=[self.TEST_ROLE_NAME])

    def test_delete_certificate_role(self):
        self.client.auth.cert.create_ca_certificate_role(
            name="testrole2",
            certificate=self.TEST_CERTIFICATE,
            mount_point=self.TEST_MOUNT_POINT,
        )
        response = self.client.auth.cert.delete_certificate_role(
            name="testrole2",
            mount_point=self.TEST_MOUNT_POINT,
        )

        self.assertEqual(first=204, second=response.status_code)

    def test_configure_tls_certificate(self):
        response = self.client.auth.cert.configure_tls_certificate(
            mount_point=self.TEST_MOUNT_POINT
        )

        self.assertEqual(first=204, second=response.status_code)

    def test_auth_tls_deprecation(self):
        # In order to raise this it is just easier to expect it to fail.
        with self.assertRaises(OSError):
            pytest.deprecated_call(Client().auth_tls())

    @parameterized.expand(
        [
            (TEST_ROLE_NAME, "", cert[0], cert[1], TEST_MOUNT_POINT),
            ("", "", cert[0], cert[1], TEST_MOUNT_POINT),
            ("testrole2", "", cert[0], cert[1], TEST_MOUNT_POINT),
            ("", "", "bad cert", cert[1], TEST_MOUNT_POINT),
            ("", "bad ca", cert[0], cert[1], TEST_MOUNT_POINT),
            ("", True, cert[0], cert[1], TEST_MOUNT_POINT),
            ("", False, " ", " ", TEST_MOUNT_POINT),
        ]
    )
    def test_login(self, name, cacert, cert_pem, key_pem, mount_point):
        if cacert or "bad" in [cacert, cert_pem, key_pem]:
            with self.assertRaises(exceptions.ParamValidationError):
                self.client.auth.cert.login(
                    name=name,
                    cacert=cacert,
                    cert_pem=cert_pem,
                    mount_point=mount_point,
                )
        # elif cacert:
        #     with self.assertRaises(OSError):
        #         self.client.auth.cert.login(
        #             name=name,
        #             cacert=cacert,
        #             cert_pem=cert_pem,
        #             mount_point=mount_point,
        #         )
        elif (
            name != ""
            and name
            not in self.client.auth.cert.list_certificate_roles(
                mount_point=self.TEST_MOUNT_POINT,
            )["data"]["keys"]
        ):
            with self.assertRaises(exceptions.InvalidRequest):
                with self.assertRaises(OSError):
                    self.client.auth.cert.login(
                        name=name,
                        cacert=cacert,
                        cert_pem=cert_pem,
                        mount_point=mount_point,
                    )
        elif "/" not in cert_pem:
            with self.assertRaises(OSError):
                self.client.auth.cert.login(
                    name=name,
                    cacert=cacert,
                    cert_pem=cert_pem,
                    mount_point=mount_point,
                )
        else:
            response = self.client.auth.cert.login(
                name=name,
                cacert=cacert,
                cert_pem=cert_pem,
                mount_point=mount_point,
            )

            if name in [self.TEST_ROLE_NAME, ""] and (cacert, cert_pem, key_pem) == (
                "",
                self.cert[0],
                self.cert[1],
            ):
                self.assertIsInstance(response, dict)
