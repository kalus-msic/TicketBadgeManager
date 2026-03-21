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


import io
import pandas as pd
from tickets.utils.merge_utils import find_header_row, read_file_to_dataframe


class FindHeaderRowTest(TestCase):

    def test_finds_header_with_many_string_cols(self):
        rows = [
            ['Pořadatel', 'MSIC', None, None],
            ['Akce', 'InnoVerse', None, None],
            ['Příjmení', 'Jméno', 'Číslo objednávky', 'Číslo vstupenky', 'Kategorie'],
        ]
        self.assertEqual(find_header_row(rows), 2)

    def test_skips_rows_with_fewer_than_4_strings(self):
        rows = [
            ['Label', 'Value', None, None],
            ['Another', 'Row', None, None],
            ['Col1', 'Col2', 'Col3', 'Col4'],
        ]
        self.assertEqual(find_header_row(rows), 2)

    def test_raises_if_no_header_found(self):
        rows = [
            ['A', 'B', None],
            ['C', 'D', None],
        ]
        with self.assertRaises(ValueError):
            find_header_row(rows)

    def test_ignores_nan_strings(self):
        # When CSV is parsed with dtype=str, empty cells become 'nan'
        rows = [
            ['Pořadatel', 'MSIC', 'nan', 'nan'],
            ['Col1', 'Col2', 'Col3', 'Col4'],
        ]
        # First row: only 2 real strings ('nan' excluded), so header is row 1
        self.assertEqual(find_header_row(rows), 1)


class ReadFileToDfTest(TestCase):

    def _make_csv_bytes(self, content):
        return content.encode('utf-8-sig')

    def test_reads_csv_with_semicolon_and_metadata(self):
        content = (
            "Pořadatel;MSIC\n"
            "Akce;InnoVerse\n"
            "Číslo objednávky;Číslo vstupenky;Kategorie;Příjmení\n"
            "12345;5648915060501;Základní vstupné;Novák\n"
        )
        df = read_file_to_dataframe(self._make_csv_bytes(content), 'test.csv')
        self.assertIn('Číslo objednávky', df.columns)
        self.assertEqual(df.iloc[0]['Číslo objednávky'], '12345')

    def test_reads_csv_with_comma_fallback(self):
        content = (
            "Label,Value\n"
            "Col1,Col2,Col3,Col4\n"
            "a,b,c,d\n"
        )
        df = read_file_to_dataframe(self._make_csv_bytes(content), 'test.csv')
        self.assertIn('Col1', df.columns)

    def test_order_numbers_stay_as_strings(self):
        content = (
            "Pořadatel;MSIC\n"
            "Číslo objednávky;Jméno;Příjmení;Kategorie\n"
            "34302271;Jana;Nová;Basic\n"
        )
        df = read_file_to_dataframe(self._make_csv_bytes(content), 'test.csv')
        self.assertEqual(df.iloc[0]['Číslo objednávky'], '34302271')
        self.assertNotIn('.0', df.iloc[0]['Číslo objednávky'])
