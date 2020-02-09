from decimal import Decimal

from rest_framework import filters, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import BadRequest
from .models import Account, Index
from .serializers import AccountSerializer, IndexSerializer


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
    """
    queryset = Index.objects.all().order_by('updated')
    serializer_class = IndexSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = '__all__'

    def retrieve(self, request, *args, **kwargs):
        if request.GET.get('reload', ''):
            self.get_object().update()
        return super().retrieve(request, *args, **kwargs)


class AdjustedIndex(APIView):
    tickers = []

    def get(self, request, index_id):
        # TODO: create get_parameters_or_400
        money = Decimal(request.GET.get('money'))
        if not money:
            raise BadRequest(detail="Money parameter is missing")

        index = get_object_or_404(queryset=Index.objects.all(), pk=index_id)
        for ticker in index.tickers.all().order_by('weight'):
            self.tickers.append({'name': ticker.name, 'price': ticker.price, 'weight': ticker.weight, 'visible': True})

        for ticker in self.tickers:
            if ticker['weight'] * money < ticker['price']:
                ticker['visible'] = False
                coefficient = 1 / sum(ticker['weight'] for ticker in self.visible_tickers)
                for visible_ticker in self.visible_tickers:
                    visible_ticker['weight'] *= coefficient

        return Response(self.visible_tickers)

    @property
    def visible_tickers(self):
        return [ticker for ticker in self.tickers if ticker['visible']]
