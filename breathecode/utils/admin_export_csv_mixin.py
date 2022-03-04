import csv
from django.http import StreamingHttpResponse

__all__ = ['AdminExportCsvMixin']


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """
    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


class AdminExportCsvMixin:
    def export_as_csv(self, request, queryset):

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)

        writer.writerow(field_names)
        return StreamingHttpResponse(
            (writer.writerow((getattr(obj, field) for field in field_names)) for obj in queryset),
            content_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename={}.csv'.format(meta)},
        )

    export_as_csv.short_description = 'Export Selected as CSV'
