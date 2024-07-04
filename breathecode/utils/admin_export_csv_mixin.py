import csv
from django.http import StreamingHttpResponse
from django.contrib import messages
from django.utils.safestring import mark_safe

__all__ = ["AdminExportCsvMixin"]


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
            content_type="text/csv",
            headers={"Content-Disposition": "attachment; filename={}.csv".format(meta)},
        )

    def async_export_as_csv(self, request, queryset):
        from breathecode.monitoring.tasks import async_download_csv

        meta = self.model._meta
        ids = list(queryset.values_list("pk", flat=True))
        async_download_csv.delay(self.model.__module__, meta.object_name, ids)
        messages.add_message(
            request,
            messages.INFO,
            mark_safe(
                'Data is being downloaded, <a href="/admin/monitoring/csvdownload/">you can check your download here.</a>'
            ),
        )
