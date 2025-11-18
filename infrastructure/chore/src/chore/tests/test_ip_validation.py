"""Tests for IP validation and normalization."""

import unittest
from chore.commands.ip_whitelist import normalize_ip, validate_cidr


class TestIPValidation(unittest.TestCase):
    """Test IP validation and normalization."""
    
    def test_normalize_bare_ip(self):
        """Test normalizing bare IP address to CIDR."""
        result = normalize_ip("192.168.1.1")
        self.assertEqual(result, "192.168.1.1/32")
    
    def test_normalize_cidr(self):
        """Test normalizing CIDR notation (no change)."""
        result = normalize_ip("192.168.1.0/24")
        self.assertEqual(result, "192.168.1.0/24")
    
    def test_normalize_invalid(self):
        """Test normalizing invalid IP."""
        result = normalize_ip("not-an-ip")
        self.assertIsNone(result)
    
    def test_validate_cidr_valid(self):
        """Test validating valid CIDR."""
        self.assertTrue(validate_cidr("192.168.1.1/32"))
        self.assertTrue(validate_cidr("10.0.0.0/8"))
        self.assertTrue(validate_cidr("172.16.0.0/12"))
    
    def test_validate_cidr_invalid_octets(self):
        """Test validating CIDR with invalid octets."""
        self.assertFalse(validate_cidr("256.1.1.1/32"))
        self.assertFalse(validate_cidr("192.300.1.1/32"))
    
    def test_validate_cidr_invalid_mask(self):
        """Test validating CIDR with invalid mask."""
        self.assertFalse(validate_cidr("192.168.1.1/33"))
        self.assertFalse(validate_cidr("192.168.1.1/-1"))


if __name__ == "__main__":
    unittest.main()

