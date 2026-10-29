"""GA/T 1400 回调 Digest 校验与可靠 Stream 的回归测试。"""

import unittest

from module_gat1400.service.gat1400_digest_client import (
    compute_digest_response,
    issue_digest_nonce,
    validate_digest_nonce,
    verify_digest_authorization,
)


class NotifyDigestSecurityTests(unittest.TestCase):
    def test_nonce_is_signed_and_expires(self) -> None:
        nonce = issue_digest_nonce('secret', now=1000)
        self.assertTrue(validate_digest_nonce('secret', nonce, now=1001))
        self.assertFalse(validate_digest_nonce('other-secret', nonce, now=1001))
        self.assertFalse(validate_digest_nonce('secret', nonce, now=4601))

    def test_valid_digest_authorization_is_accepted(self) -> None:
        username = 'dahua'
        password = 'password'
        uri = '/VIID/SubscribeNotifications'
        nonce = issue_digest_nonce(password)
        response = compute_digest_response(username, password, 'GAT1400', 'POST', uri, nonce, 1, 'cnonce', 'auth')
        header = (
            f'Digest username="{username}", realm="GAT1400", nonce="{nonce}", uri="{uri}", '
            f'response="{response}", qop=auth, nc=00000001, cnonce="cnonce", algorithm=MD5'
        )
        verified, values = verify_digest_authorization(
            header, username=username, password=password, method='POST', uri=uri, nonce_secret=password
        )
        self.assertTrue(verified)
        self.assertEqual(values['nc'], '00000001')

    def test_digest_with_wrong_realm_or_signature_is_rejected(self) -> None:
        nonce = issue_digest_nonce('password')
        header = (
            f'Digest username="dahua", realm="wrong", nonce="{nonce}", '
            'uri="/VIID/SubscribeNotifications", response="bad", qop=auth, nc=00000001, cnonce="c"'
        )
        verified, _ = verify_digest_authorization(
            header,
            username='dahua',
            password='password',
            method='POST',
            uri='/VIID/SubscribeNotifications',
            nonce_secret='password',
        )
        self.assertFalse(verified)


if __name__ == '__main__':
    unittest.main()
