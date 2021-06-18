from datetime import timedelta

from django.db.models import Min
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_406_NOT_ACCEPTABLE, HTTP_202_ACCEPTED, HTTP_200_OK

from fin.models.utils import UpdatingStatus
from fin.tasks.update_tickers_statements import update_model_tickers_statements_task


class UpdateTickersMixin:
    """
    Mixin of ticker updating for models with tickers
    """
    acceptable_tickers_updated_period = timedelta(hours=1)

    @action(detail=True, methods=['put'], url_path='tickers')
    def update_tickers(self, request, *args, **kwargs):
        """
        Runs the task of updating tickers for models with tickers.
        """
        obj_id = kwargs.get('pk')
        obj = self.model.objects.get(pk=obj_id)
        if obj.status == UpdatingStatus.updating:
            return Response(status=HTTP_406_NOT_ACCEPTABLE)

        last_time_tickers_updated = obj.tickers.aggregate(Min('updated')).get('updated__min')
        tickers_can_updated_time = timezone.now() - self.acceptable_tickers_updated_period
        if tickers_can_updated_time >= last_time_tickers_updated:
            update_model_tickers_statements_task.delay(self.model.__name__, obj_id)
            return Response(status=HTTP_202_ACCEPTED)
        return Response(status=HTTP_200_OK)


class AdjustMixin:
    """
    Extracts required params for adjusting functionality from request
    """
    default_adjust_options = {
        'skip_countries': [],
        'skip_sectors': [],
        'skip_industries': [],
        'skip_tickers': [],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.money = None
        self.adjust_options = self.default_adjust_options

    def initial(self, request, *args, **kwargs):
        """
        Overriding the DRF View method that executes inside every View/Viewset
        """
        super().initial(request, *args, **kwargs)
        money = request.GET.get('money')
        try:
            self.money = float(money)
        except (TypeError, ValueError):
            self.money = None

        options = {
            'skip_countries': request.GET.getlist('skip-country[]', []),
            'skip_sectors': request.GET.getlist('skip-sector[]', []),
            'skip_industries': request.GET.getlist('skip-industry[]', []),
            'skip_tickers': request.GET.getlist('skip-ticker[]', []),
        }
        self.adjust_options.update(options)
