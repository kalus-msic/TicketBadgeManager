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


import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache
from django.contrib.auth.models import User


class MergeExecuteViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='staff', password='pass', is_staff=True
        )
        self.client.login(username='staff', password='pass')

    def _make_pair(self):
        left = (
            "Pořadatel;MSIC\n"
            "Číslo objednávky;Číslo vstupenky;Příjmení;Jméno\n"
            "111;VST001;Novák;Jan\n"
            "222;VST002;Dvořák;Eva\n"
        ).encode('utf-8-sig')
        right = (
            "Pořadatel;MSIC\n"
            "Číslo objednávky;Název organizace;E-mail;Kategorie\n"
            "111;Firma s.r.o.;jan@example.com;Basic\n"
            "333;Jiná firma;jiri@example.com;VIP\n"
        ).encode('utf-8-sig')
        return left, right

    def _seed_cache(self, file1_bytes, file2_bytes):
        key = str(uuid.uuid4())
        cache.set(f'merge_{key}', {
            'file1_bytes': file1_bytes,
            'file1_name': 'odbaveni.csv',
            'file2_bytes': file2_bytes,
            'file2_name': 'transakce.csv',
        }, 60)
        return key

    def test_get_redirects_to_merge_import(self):
        url = reverse('tickets:merge_execute')
        response = self.client.get(url)
        self.assertRedirects(response, reverse('tickets:merge_import'))

    def test_expired_cache_redirects_with_error(self):
        url = reverse('tickets:merge_execute')
        response = self.client.post(url, {
            'session_key': 'nonexistent',
            'join_column': 'Číslo objednávky',
            'action': 'import',
        })
        self.assertRedirects(response, reverse('tickets:merge_import'))

    def test_download_action_returns_csv(self):
        left, right = self._make_pair()
        key = self._seed_cache(left, right)
        url = reverse('tickets:merge_execute')
        response = self.client.post(url, {
            'session_key': key,
            'join_column': 'Číslo objednávky',
            'action': 'download',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('merged_goout.csv', response['Content-Disposition'])

    def test_download_does_not_delete_merge_cache(self):
        left, right = self._make_pair()
        key = self._seed_cache(left, right)
        self.client.post(reverse('tickets:merge_execute'), {
            'session_key': key,
            'join_column': 'Číslo objednávky',
            'action': 'download',
        })
        self.assertIsNotNone(cache.get(f'merge_{key}'))

    def test_import_action_creates_import_cache_and_redirects(self):
        left, right = self._make_pair()
        key = self._seed_cache(left, right)
        response = self.client.post(reverse('tickets:merge_execute'), {
            'session_key': key,
            'join_column': 'Číslo objednávky',
            'action': 'import',
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        redirect_url = response['Location']
        self.assertIn('/import/mapping/', redirect_url)
        self.assertIn('session_key=', redirect_url)

    def test_import_deletes_merge_cache(self):
        left, right = self._make_pair()
        key = self._seed_cache(left, right)
        self.client.post(reverse('tickets:merge_execute'), {
            'session_key': key,
            'join_column': 'Číslo objednávky',
            'action': 'import',
        })
        self.assertIsNone(cache.get(f'merge_{key}'))

    def test_import_cache_has_correct_structure(self):
        left, right = self._make_pair()
        key = self._seed_cache(left, right)
        response = self.client.post(reverse('tickets:merge_execute'), {
            'session_key': key,
            'join_column': 'Číslo objednávky',
            'action': 'import',
        }, follow=False)
        redirect_url = response['Location']
        new_key = redirect_url.split('session_key=')[1]
        csv_data = cache.get(f'import_{new_key}')
        self.assertIsNotNone(csv_data)
        self.assertIn('fieldnames', csv_data)
        self.assertIn('rows', csv_data)
        self.assertIn('filename', csv_data)
        self.assertIn('delimiter', csv_data)
        # All row values must be strings
        for row in csv_data['rows']:
            for val in row.values():
                self.assertIsInstance(val, str)
        # No 'nan' values
        for row in csv_data['rows']:
            for val in row.values():
                self.assertNotEqual(val, 'nan')
