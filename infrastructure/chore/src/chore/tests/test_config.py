"""Tests for configuration parsing."""

import unittest
from pathlib import Path
from chore.core.config import ConfigParser


class TestConfigParser(unittest.TestCase):
    """Test configuration parser."""
    
    def test_parse_parameter_overrides(self):
        """Test parsing of parameter overrides string."""
        parser = ConfigParser(Path(__file__).parent / "fixtures" / "test_config.toml")
        
        overrides_str = 'AllowedIPRanges="192.168.1.1/32" LLMProvider="bedrock" OpenAIModel="gpt-4"'
        result = parser._parse_parameter_overrides(overrides_str)
        
        self.assertEqual(result["AllowedIPRanges"], "192.168.1.1/32")
        self.assertEqual(result["LLMProvider"], "bedrock")
        self.assertEqual(result["OpenAIModel"], "gpt-4")
    
    def test_parse_parameter_overrides_with_spaces(self):
        """Test parsing with spaces in values."""
        parser = ConfigParser(Path(__file__).parent / "fixtures" / "test_config.toml")
        
        overrides_str = 'Key1="value with spaces" Key2="another value"'
        result = parser._parse_parameter_overrides(overrides_str)
        
        self.assertEqual(result["Key1"], "value with spaces")
        self.assertEqual(result["Key2"], "another value")
    
    def test_parse_empty_overrides(self):
        """Test parsing empty overrides."""
        parser = ConfigParser(Path(__file__).parent / "fixtures" / "test_config.toml")
        
        result = parser._parse_parameter_overrides("")
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()

