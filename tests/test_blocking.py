import unittest
from unittest.mock import MagicMock, patch
import app
import json

class TestBlockingLogic(unittest.TestCase):
    def setUp(self):
        app.app.testing = True
        self.client = app.app.test_client()
        # Mock session
        with self.client.session_transaction() as sess:
            sess['user'] = 'admin'
            sess['role'] = 'admin'

    @patch('app.contract')
    @patch('app.w3')
    @patch('app.cipher_suite')
    @patch('app.open')
    @patch('os.path.exists')
    def test_verify_report_blocking(self, mock_exists, mock_open, mock_cipher, mock_w3, mock_contract):
        # Setup Mocks
        mock_exists.return_value = True
        mock_w3.is_connected.return_value = True
        
        # Mock Blockchain response: (hash, time, uploader, exists)
        # We return a blockchain hash that is DIFFERENT from local hash
        mock_contract.functions.verifyReport.return_value.call.return_value = ["blockchain_hash_123", "time", "user", True]
        
        # Mock File Decryption
        mock_open.return_value.__enter__.return_value.read.return_value = b"encrypted_content"
        mock_cipher.decrypt.return_value = b"decrypted_content" # This will hash to something specific
        
        # Setup DB record
        app.ALL_UPLOADS = [{
            "hash": "blockchain_hash_123", # Original hash used to lookup
            "encrypted_filename": "test.enc",
            "uploader": "user",
            "time": "now",
            "verified": "Pending",
            "stored_on_chain": True
        }]
        app.SECURITY_MONITOR = {"user": {"blocked": False, "tamper_attempts": 0}}
        
        # Call Verify
        response = self.client.post('/verify_report', json={'hash': 'blockchain_hash_123'})
        data = response.get_json()
        
        # Assertions
        self.assertEqual(data.get('status'), 'QUARANTINED')
        self.assertFalse(data.get('on_chain'))
        
        # Verify DB updated
        self.assertEqual(app.ALL_UPLOADS[0]['verified'], 'QUARANTINED')

    def test_admin_unblock(self):
        # Setup DB record as blocked
        app.ALL_UPLOADS = [{
            "hash": "blocked_hash",
            "filename": "test.txt",
            "verified": "QUARANTINED",
            "uploader": "user"
        }]
        app.SECURITY_MONITOR = {"user": {"blocked": True, "tamper_attempts": 5}}
        
        response = self.client.post('/admin_unblock', json={'hash': 'blocked_hash'})
        data = response.get_json()
        
        self.assertTrue(data.get('success', False))
        self.assertEqual(app.ALL_UPLOADS[0]['verified'], 'Verified (Admin Override)')
        self.assertFalse(app.SECURITY_MONITOR['user']['blocked'])

if __name__ == '__main__':
    unittest.main()
