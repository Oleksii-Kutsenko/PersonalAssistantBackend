"""
Views
"""
from decimal import Decimal, InvalidOperation
from threading import Thread

from rest_framework import filters, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.metadata import SimpleMetadata
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import BadRequest
from .models import Account, Index, Goal, update_tickers_industries
from .serializers import AccountSerializer, IndexSerializer, GoalSerializer, \
    AdjustedTickerSerializer


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
