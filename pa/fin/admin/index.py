"""
Admin stuff for Index model
"""
from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.forms import Form, FileField, ChoiceField
from django.shortcuts import render, redirect
from django.urls import path

from fin.models.index import Index
from fin.models.index.parsers import Source


class CsvImportForm(Form):
    """
    Form for creation Index model from CSV file
    """
    non_updatable_indexes = [(index, Source(index).label)
                             for index, parser in Index.url_parsers.items()
                             if not parser.updatable]
    index = ChoiceField(choices=non_updatable_indexes)
    csv_file = FileField()


class IndexAdmin(ModelAdmin):
    """
    Adds Index model to the admin panel
    """
    change_list_template = 'import_index_csv.html'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv, name='import-csv')
        ]
        return my_urls + urls

    def import_csv(self, request):
        """
        Creates Index from given CSV file
        """
        if request.method == 'POST':
            form = CsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data['csv_file'].read().decode('utf-8')
                index, _ = Index.objects.get_or_create(data_source_url=form.cleaned_data['index'])
                index.parser.csv_file = csv_file
                tickers_parsed_json = index.parser.parse()
                index.update_from_tickers_parsed_json(tickers_parsed_json)
                self.message_user(request, 'Your csv file has been imported')
                return redirect('..')
            self.message_user(request, 'Form is invalid', messages.ERROR)
            return render(
                request, 'csv_form.html', {'form': form}
            )
        form = CsvImportForm()
        payload = {'form': form}
        return render(
            request, 'csv_form.html', payload
        )


admin.site.register(Index, IndexAdmin)
