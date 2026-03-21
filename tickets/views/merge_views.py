import uuid

import pandas as pd
from django.contrib import messages
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect

from ..decorators import staff_required
from ..utils.error_handlers import handle_view_errors
from ..utils.merge_utils import read_file_to_dataframe


@staff_required
@handle_view_errors
def merge_execute(request):
    """Execute the GoOut file merge: right-join two files and either download or import."""
    if request.method != 'POST':
        return redirect('tickets:merge_import')

    session_key = request.POST.get('session_key')
    join_column = request.POST.get('join_column')
    action = request.POST.get('action')  # 'download' or 'import'

    data = cache.get(f'merge_{session_key}')
    if not data:
        messages.error(request, "Session expired. Please upload the files again.")
        return redirect('tickets:merge_import')

    df1 = read_file_to_dataframe(data['file1_bytes'], data['file1_name'])
    df2 = read_file_to_dataframe(data['file2_bytes'], data['file2_name'])

    if join_column not in df1.columns or join_column not in df2.columns:
        messages.error(
            request,
            f"Join column '{join_column}' was not found in both files. "
            f"File 1 columns: {list(df1.columns)}. File 2 columns: {list(df2.columns)}."
        )
        return redirect('tickets:merge_import')

    merged = pd.merge(df1, df2, on=join_column, how='right')
    merged = merged.fillna('').astype(str).replace({'nan': '', 'None': ''})

    if action == 'download':
        # Keep merge cache alive — user may also want to import
        csv_content = merged.to_csv(index=False)
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="merged_goout.csv"'
        return response

    # action == 'import'
    rows = merged.to_dict('records')
    new_key = str(uuid.uuid4())
    cache.set(f'import_{new_key}', {
        'fieldnames': list(merged.columns),
        'rows': rows,
        'filename': 'merged_goout.csv',
        'delimiter': ',',
    }, 3600)
    cache.delete(f'merge_{session_key}')
    return redirect(f'/import/mapping/?session_key={new_key}')
