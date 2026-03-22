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


import io
from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache
from django.contrib.auth.models import User


class MergeImportViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='staff2', password='pass', is_staff=True
        )
        self.client.login(username='staff2', password='pass')

    def test_get_renders_step1(self):
        response = self.client.get(reverse('tickets:merge_import'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('step', response.context or {})

    def test_post_valid_files_renders_step2(self):
        left = (
            "Pořadatel;MSIC\n"
            "Číslo objednávky;Číslo vstupenky;Příjmení;Jméno\n"
            "111;VST001;Novák;Jan\n"
        ).encode('utf-8-sig')
        right = (
            "Pořadatel;MSIC\n"
            "Číslo objednávky;Název organizace;E-mail;Kategorie\n"
            "111;Firma;jan@example.com;Basic\n"
        ).encode('utf-8-sig')

        left_file = io.BytesIO(left)
        left_file.name = 'odbaveni.csv'
        right_file = io.BytesIO(right)
        right_file.name = 'transakce.csv'

        response = self.client.post(
            reverse('tickets:merge_import'),
            {'file1': left_file, 'file2': right_file},
        )
        self.assertEqual(response.status_code, 200)
        ctx = response.context
        self.assertEqual(ctx['step'], 2)
        self.assertIn('Číslo objednávky', ctx['common_columns'])
        self.assertEqual(ctx['suggested_join_column'], 'Číslo objednávky')
        self.assertIn('session_key', ctx)

    def test_post_caches_file_bytes(self):
        left = (
            "Pořadatel;MSIC\n"
            "Číslo objednávky;Číslo vstupenky;Příjmení;Jméno\n"
            "111;VST001;Novák;Jan\n"
        ).encode('utf-8-sig')
        right = (
            "Pořadatel;MSIC\n"
            "Číslo objednávky;Název organizace;E-mail;Kategorie\n"
            "111;Firma;jan@example.com;Basic\n"
        ).encode('utf-8-sig')

        left_file = io.BytesIO(left)
        left_file.name = 'odbaveni.csv'
        right_file = io.BytesIO(right)
        right_file.name = 'transakce.csv'

        response = self.client.post(
            reverse('tickets:merge_import'),
            {'file1': left_file, 'file2': right_file},
        )
        session_key = response.context['session_key']
        cached = cache.get(f'merge_{session_key}')
        self.assertIsNotNone(cached)
        self.assertIn('file1_bytes', cached)
        self.assertIn('file2_bytes', cached)

    def test_post_no_common_columns_redirects_with_error(self):
        left = (
            "Pořadatel;MSIC\n"
            "UniqueA;UniqueB;UniqueC;UniqueD\n"
            "a;b;c;d\n"
        ).encode('utf-8-sig')
        right = (
            "Pořadatel;MSIC\n"
            "DifferentA;DifferentB;DifferentC;DifferentD\n"
            "1;2;3;4\n"
        ).encode('utf-8-sig')

        left_file = io.BytesIO(left)
        left_file.name = 'file1.csv'
        right_file = io.BytesIO(right)
        right_file.name = 'file2.csv'

        response = self.client.post(
            reverse('tickets:merge_import'),
            {'file1': left_file, 'file2': right_file},
            follow=True,
        )
        self.assertRedirects(response, reverse('tickets:merge_import'))
        messages_list = list(response.context['messages'])
        self.assertTrue(any('common' in str(m).lower() or 'No common' in str(m) for m in messages_list))


class ImportMappingGetBranchTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='staff3', password='pass', is_staff=True
        )
        self.client.login(username='staff3', password='pass')

    def _seed_import_cache(self):
        key = str(uuid.uuid4())
        cache.set(f'import_{key}', {
            'fieldnames': ['Číslo objednávky', 'Číslo vstupenky', 'Název organizace', 'Jméno'],
            'rows': [
                {'Číslo objednávky': '111', 'Číslo vstupenky': 'VST001', 'Název organizace': 'Firma', 'Jméno': 'Jan'},
            ],
            'filename': 'merged_goout.csv',
            'delimiter': ',',
        }, 60)
        return key

    def test_get_with_valid_session_key_renders_mapping(self):
        key = self._seed_import_cache()
        response = self.client.get(
            reverse('tickets:import_mapping') + f'?session_key={key}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tickets/import_mapping.html')
        ctx = response.context
        self.assertEqual(len(ctx['csv_columns']), 4)
        self.assertEqual(ctx['total_rows'], 1)
        self.assertEqual(ctx['session_key'], key)
        self.assertEqual(ctx['delimiter'], ',')
        self.assertIn('delimiter_name', ctx)
        self.assertIn('detected_profile', ctx)
        self.assertIn('profile_name', ctx)

    def test_get_with_expired_key_redirects_with_error(self):
        response = self.client.get(
            reverse('tickets:import_mapping') + '?session_key=expired-key',
            follow=True,
        )
        self.assertRedirects(response, reverse('tickets:merge_import'))
        msgs = list(response.context['messages'])
        self.assertTrue(any('expired' in str(m).lower() for m in msgs))


from datetime import date
from tickets.models import Event, Ticket, Log


class EventModelTest(TestCase):
    def test_create_event(self):
        event = Event.objects.create(
            name="Test Conference",
            date=date(2026, 6, 15),
            description="A test event"
        )
        self.assertEqual(str(event), "Test Conference (2026-06-15)")
        self.assertEqual(event.status, 'active')
        self.assertEqual(event.printer_1_name, 'TDP-2251')
        self.assertEqual(event.printer_2_name, 'TDP-2252')
        self.assertTrue(event.auto_print_on_scan)

    def test_ticket_event_fk(self):
        event = Event.objects.create(name="Test", date=date(2026, 1, 1))
        ticket = Ticket.objects.create(
            qr_code="EVT-001", name="Test User", event=event
        )
        self.assertEqual(ticket.event, event)

    def test_log_event_fk(self):
        event = Event.objects.create(name="Test", date=date(2026, 1, 1))
        log = Log.objects.create(
            event_type='SYSTEM', message='Test log', event=event
        )
        self.assertEqual(log.event, event)

    def test_event_ordering_newest_first(self):
        e1 = Event.objects.create(name="Old", date=date(2025, 1, 1))
        e2 = Event.objects.create(name="New", date=date(2026, 1, 1))
        events = list(Event.objects.all())
        self.assertEqual(events[0], e2)
        self.assertEqual(events[1], e1)


import io as _io
from openpyxl import load_workbook as _load_workbook


class ExportXlsxViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='staff_xlsx', password='pass', is_staff=True
        )
        self.client.login(username='staff_xlsx', password='pass')

    def _make_ticket(self):
        return Ticket.objects.create(
            qr_code='TEST001',
            name='Jana Nová',
            company_name='Firma s.r.o.',
            status='VALID',
        )

    def test_returns_200_with_xlsx_content_type(self):
        response = self.client.get(reverse('tickets:export_tickets_xlsx'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            response['Content-Type']
        )

    def test_content_disposition_is_attachment(self):
        response = self.client.get(reverse('tickets:export_tickets_xlsx'))
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('.xlsx', response['Content-Disposition'])

    def test_response_is_valid_xlsx_with_correct_data(self):
        self._make_ticket()
        response = self.client.get(reverse('tickets:export_tickets_xlsx'))
        wb = _load_workbook(_io.BytesIO(response.content))
        ws = wb.active
        self.assertEqual(ws.cell(1, 1).value, 'QR Code')
        self.assertEqual(ws.cell(1, 2).value, 'Name')
        self.assertEqual(ws.cell(2, 1).value, 'TEST001')
        self.assertEqual(ws.cell(2, 2).value, 'Jana Nová')

    def test_csv_export_still_works(self):
        response = self.client.get(reverse('tickets:export_tickets_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
