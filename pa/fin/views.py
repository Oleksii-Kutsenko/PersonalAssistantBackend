"""
Views
"""
import json
import logging
import traceback
from decimal import Decimal, InvalidOperation
from json import JSONDecodeError
from threading import Thread

from rest_framework import filters, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.metadata import SimpleMetadata
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from .exceptions import BadRequest, TraderNetAPIUnavailable
from .models.index import Index, Ticker
from .models.models import Goal
from .models.portfolio import Portfolio, PortfolioTickers, Account
from .serializers.index import IndexSerializer, AdjustedTickerSerializer
from .serializers.portfolio import PortfolioSerializer, AccountSerializer
from .serializers.serializers import GoalSerializer
from .utils.PublicApiClient import PublicApiClient
from .utils.index_helpers import update_tickers_industries

logger = logging.getLogger(__name__)


class AccountViewSet(viewsets.ModelViewSet):
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
        Thread(target=update_tickers_industries, args=(response.data.get('id'),)).start()
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        Thread(target=update_tickers_industries, args=(response.data.get('id'),)).start()
        return response


class AdjustedIndex(APIView):
    """
    API endpoint that allows executing adjust method of the index
    """

    class AdjustedIndexMetadata(SimpleMetadata):
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
        money = request.GET.get('money')

        if money is None:
            raise BadRequest(detail='Money parameter is missing')

        try:
            money = Decimal(money)
            if money < 1:
                raise BadRequest(detail="Money parameter is invalid")
        except InvalidOperation:
            raise BadRequest(detail="Money parameter is invalid")

        index = get_object_or_404(queryset=Index.objects.all(), pk=index_id)

        options = {
            'skip_countries': request.GET.getlist('skip-country[]', []),
            'skip_sectors': request.GET.getlist('skip-sector[]', []),
            'skip_industries': request.GET.getlist('skip-industry[]', []),
            'skip_tickers': request.GET.getlist('skip-ticker[]', []),
        }
        adjusted_index, summary_cost = index.adjust(money, options)
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


class PortfolioAPI(APIView):
    """
    API endpoint that allows to view portfolio
    """
    permission_classes = (AllowAny,)

    def get(self, request):
        user = request.user
        portfolio_models = Portfolio.objects.filter(user=user.id)
        return Response(data=PortfolioSerializer(portfolio_models, many=True).data)

    def post(self, request):
        user = User.objects.get(pk=1)
        pub_ = request.GET.get('pub_')
        sec_ = request.GET.get('sec_')
        cmd_ = 'getPositionJson'

        tradernet_api = PublicApiClient(pub_, sec_, PublicApiClient().V2)

        response = tradernet_api.sendRequest(cmd_).content.decode('utf-8')
        try:
            json_portfolio = json.loads(response)['result']['ps']
        except JSONDecodeError as _:
            logger.error('TraderNet API is not responding')
            logger.error(str(response))
            logger.error(traceback.format_exc())
            raise TraderNetAPIUnavailable()

        portfolio_accounts = json_portfolio['acc']
        portfolio_tickers = json_portfolio['pos']

        portfolio_model = Portfolio(user=user)
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
            ticker_model = Ticker.objects.get_or_create(symbol=ticker_symbol, defaults=ticker_info)[0]
            ticker_model.save()
            portfolio_tickers = PortfolioTickers(portfolio=portfolio_model, ticker=ticker_model,
                                                 amount=ticker.get('q'))
            portfolio_tickers.save()

        return Response(data=PortfolioSerializer(portfolio_model).data)
