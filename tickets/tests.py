from django.test import TestCase
from django.core.exceptions import ValidationError
from unittest.mock import MagicMock
from tickets.utils.validators import validate_merge_file


class ValidateMergeFileTest(TestCase):

    def _make_file(self, name, size=100, content=b'col1;col2\nval1;val2'):
        f = MagicMock()
        f.name = name
        f.size = size
        f.read.return_value = content
        return f

    def test_accepts_csv(self):
        f = self._make_file('data.csv')
        self.assertTrue(validate_merge_file(f))

    def test_accepts_xlsx(self):
        f = self._make_file('data.xlsx', content=b'binarydata')
        # xlsx files don't need UTF-8 decode check
        self.assertTrue(validate_merge_file(f))

    def test_rejects_txt(self):
        f = self._make_file('data.txt')
        with self.assertRaises(ValidationError):
            validate_merge_file(f)

    def test_rejects_oversized(self):
        f = self._make_file('data.csv', size=11 * 1024 * 1024)
        with self.assertRaises(ValidationError):
            validate_merge_file(f)

    def test_rejects_none(self):
        with self.assertRaises(ValidationError):
            validate_merge_file(None)
