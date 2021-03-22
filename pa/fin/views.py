"""
Views
"""
import json
import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Min
from django.utils import timezone
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_406_NOT_ACCEPTABLE, HTTP_200_OK, \
    HTTP_202_ACCEPTED

from fin.serializers.portfolio.portfolio import PortfolioSerializer, AccountSerializer, \
    DetailedPortfolioSerializer
from .exceptions import BadRequest
from .models.index import Index
from .models.portfolio import Portfolio, Account
from .models.portfolio.portfolio_policy import PortfolioPolicy
from .models.utils import UpdatingStatus
from .serializers.index import IndexSerializer, DetailIndexSerializer
from .serializers.portfolio.portfolio_policy import PortfolioPolicySerializer
from .tasks.update_tickers_statements import update_model_tickers_statements_task

logger = logging.getLogger(__name__)


# pylint: disable=unused-argument
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
            'skip_tickers': [json.loads(ticker) for ticker in request.GET.getlist('skip-ticker[]', [])],
        }
        self.adjust_options.update(options)


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


class AccountViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows accounts to be viewed or edited
    """

    queryset = Account.objects.all().order_by('updated')
    serializer_class = AccountSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = '__all__'


class IndexViewSet(UpdateTickersMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows indices to be viewed or edited

    Send PUT request with the same data_source_url for reloading index data
    """
    queryset = Index.objects.all().order_by('updated')
    filter_backends = [filters.OrderingFilter]
    model = Index
    ordering_fields = '__all__'

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DetailIndexSerializer
        return IndexSerializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        update_model_tickers_statements_task.delay(self.model.__name__, response.data.get('id'))
        return response


class PortfolioViewSet(AdjustMixin, UpdateTickersMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows to view portfolio
    """

    filter_backends = [filters.OrderingFilter]
    model = Portfolio
    ordering_fields = '__all__'

    def get_queryset(self):
        queryset = Portfolio.objects.filter(user=self.request.user).all()
        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DetailedPortfolioSerializer
        return PortfolioSerializer

    @action(detail=True, url_path='adjust/indices/(?P<index_id>[^/.]+)')
    def adjust(self, request, *args, **kwargs):
        """
        Returns tickers that should be inside portfolio to make portfolio more similar to index
        """
        if self.money is None:
            raise BadRequest(detail="Money parameter is invalid")
        index_id = kwargs.get('index_id')
        portfolio_id = kwargs.get('pk')

        portfolio = Portfolio.objects.get(pk=portfolio_id)
        self.adjust_options['pe_quantile'] = Decimal(portfolio.portfolio_policy.pe_quantile)
        adjusted_portfolio = portfolio.adjust(index_id, self.money, self.adjust_options)

        return Response(data={'tickers': adjusted_portfolio})


class PortfolioPolicyViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows portfolio policy to be viewed or edited
    """
    serializer_class = PortfolioPolicySerializer

    def get_queryset(self):
        queryset = PortfolioPolicy.objects.filter(portfolio__user_id=self.request.user).all()
        return queryset
