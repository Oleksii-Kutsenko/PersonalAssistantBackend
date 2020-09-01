"""
Views
"""
import json
import logging
import traceback
from decimal import Decimal, InvalidOperation
from json import JSONDecodeError

from django.db import transaction
from rest_framework import filters, viewsets, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.metadata import SimpleMetadata
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import BadRequest, TraderNetAPIUnavailable
from .external_api.tradernet.PublicApiClient import PublicApiClient
from .external_api.tradernet.error_codes import BAD_SIGN
from .models.index import Index
from .models.models import Goal
from .models.portfolio import Portfolio, PortfolioTickers, Account
from .models.ticker import Ticker
from .serializers.index import IndexSerializer
from .serializers.portfolio import PortfolioSerializer, AccountSerializer
from .serializers.serializers import GoalSerializer
from .serializers.ticker import AdjustedTickerSerializer
from .tasks import update_tickers_statements_task

logger = logging.getLogger(__name__)


class AdjustMixin:
    """
    Extracts required params for adjusting functionality from request
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.money = None
        self.options = {}

    def initial(self, request, *args, **kwargs):
        """
        Overriding the DRF View method that executes inside every View/Viewset
        """
        super().initial(request, *args, **kwargs)
        money = request.GET.get('money')
        try:
            self.money = Decimal(money)
        except (InvalidOperation, TypeError):
            self.money = None

        options = {
            'skip_countries': request.GET.getlist('skip-country[]', []),
            'skip_sectors': request.GET.getlist('skip-sector[]', []),
            'skip_industries': request.GET.getlist('skip-industry[]', []),
            'skip_tickers': request.GET.getlist('skip-ticker[]', []),
        }
        self.options.update(options)


class AccountViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows accounts to be viewed or edited
    """

    queryset = Account.objects.all().order_by('updated')
    serializer_class = AccountSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = '__all__'


class IndexViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows indices to be viewed or edited

    Send PUT request with the same data_source_url for reloading index data
    """
    queryset = Index.objects.all().order_by('updated')
    serializer_class = IndexSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = '__all__'

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        update_tickers_statements_task.delay()
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        update_tickers_statements_task.delay()
        return response


class AdjustedIndexView(AdjustMixin, APIView):
    """
    API endpoint that allows executing adjust method of the index
    """

    class AdjustedIndexMetadata(SimpleMetadata):
        """
        Metadata that helps frontend create filter form
        """

        def determine_metadata(self, request, view):
            base_metadata = super().determine_metadata(request, view)
            index = get_object_or_404(Index.objects.all(), pk=view.kwargs.get('index_id'))
            base_metadata['query_params'] = {
                'countries': index.tickers.values('country').distinct(),
                'sectors': index.tickers.values('sector').distinct(),
                'industries': index.tickers.values('industry').distinct(),
            }
            return base_metadata

    metadata_class = AdjustedIndexMetadata

    def get(self, request, index_id):
        """
        Calculate index adjusted by the amount of money
        """
        if self.money is None:
            raise BadRequest(detail="Money parameter is invalid")
        index = get_object_or_404(queryset=Index.objects.all(), pk=index_id)

        adjusted_index, summary_cost = index.adjust(self.money, self.options)
        serialized_index = AdjustedTickerSerializer(adjusted_index, many=True)
        return Response(data={'tickers': serialized_index.data, 'summary_cost': summary_cost})


class GoalViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows goals to be viewed or edited
    """
    queryset = Goal.objects.all().order_by('updated')
    serializer_class = GoalSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = '__all__'


class PortfolioViewSet(AdjustMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows to view portfolio
    """

    class PortfolioMetadata(SimpleMetadata):
        """
        Metadata that helps frontend to generate creation form
        """

        def determine_metadata(self, request, view):
            base_metadata = super().determine_metadata(request, view)
            base_metadata['actions']['POST']['query_params'] = {
                'pub_': {
                    'type': 'string',
                    'required': True,
                    'read_only': False,
                    'label': 'Public Key'
                },
                'sec_': {
                    'type': 'string',
                    'required': True,
                    'read_only': False,
                    'label': 'Secret Key'
                },
            }
            return base_metadata

    serializer_class = PortfolioSerializer
    metadata_class = PortfolioMetadata
    filter_backends = [filters.OrderingFilter]
    ordering_fields = '__all__'

    def get_queryset(self):
        queryset = Portfolio.objects.filter(user=self.request.user).all()
        return queryset

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
        adjusted_portfolio = portfolio.adjust(index_id, self.money, self.adjust_options)
        serialized_index = AdjustedTickerSerializer(adjusted_portfolio, many=True)
        return Response(data={'tickers': serialized_index.data})

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        pub_ = request.GET.get('pub_')
        sec_ = request.GET.get('sec_')
        name = json.loads(request.body.decode('utf-8')).get('name')
        cmd_ = 'getPositionJson'

        if pub_ is None and sec_ is None:
            raise BadRequest(detail='Missing pub_ or sec_ query params')

        tradernet_api = PublicApiClient(pub_, sec_, PublicApiClient().V2)

        raw_response = tradernet_api.sendRequest(cmd_).content.decode('utf-8')
        try:
            json_response = json.loads(raw_response)
        except JSONDecodeError as _:
            logger.error('TraderNet API is not responding')
            logger.error(str(raw_response))
            logger.error(traceback.format_exc())
            raise TraderNetAPIUnavailable()

        if json_response.get('code') == BAD_SIGN:
            raise BadRequest(detail=json_response['errMsg'])

        json_portfolio = json_response['result']['ps']

        portfolio_accounts = json_portfolio['acc']
        portfolio_tickers = json_portfolio['pos']

        portfolio_model = Portfolio(user=request.user, name=name)
        portfolio_model.save()

        for account in portfolio_accounts:
            account_model = Account(name=account.get('curr'),
                                    currency=account.get('curr'),
                                    value=account.get('s'),
                                    portfolio=portfolio_model)
            account_model.save()

        for ticker in portfolio_tickers:
            ticker_symbol = ticker.get('i').split('.')[0]
            ticker_info = {'company_name': ticker.get('name'),
                           'price': ticker.get('mkt_price')}
            ticker_model, _ = Ticker.objects.get_or_create(symbol=ticker_symbol,
                                                           defaults=ticker_info)
            ticker_model.save()
            portfolio_tickers = PortfolioTickers(portfolio=portfolio_model,
                                                 ticker=ticker_model,
                                                 amount=ticker.get('q'))
            portfolio_tickers.save()

        update_tickers_statements_task.delay()

        return Response(data=PortfolioSerializer(portfolio_model).data,
                        status=status.HTTP_201_CREATED)
