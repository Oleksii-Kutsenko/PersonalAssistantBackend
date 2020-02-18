"""
Views
"""
from decimal import Decimal

from rest_framework import filters, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import BadRequest
from .models import Account, Index, Goal
from .serializers import AccountSerializer, IndexSerializer, GoalSerializer


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
    """
    API endpoint that allows calculating index for the money amount
    """
    tickers = []

    def get(self, request, index_id):
        """
        Calculate index adjusted by the amount of money
        """
        # check if money parameter exists
        money = Decimal(request.GET.get('money', 0))
        if not money:
            raise BadRequest(detail="Money parameter is missing")

        # check if index exists
        index = get_object_or_404(queryset=Index.objects.all(), pk=index_id)
        # create a list of ticker dicts
        for ticker in index.tickers.all().order_by('weight'):
            self.tickers.append({'name': ticker.name,
                                 'price': ticker.price,
                                 'weight': ticker.weight,
                                 'visible': True})

        # hide tickers which price is too high, and recalculate other tickers weights
        for ticker in self.tickers:
            if ticker['weight'] * money < ticker['price']:
                ticker['visible'] = False
                coefficient = 1 / sum(ticker['weight'] for ticker in self.visible_tickers)
                for visible_ticker in self.visible_tickers:
                    visible_ticker['weight'] *= coefficient

        return Response(self.visible_tickers)

    @property
    def visible_tickers(self):
        """
        Returns visible tickers
        """
        return [ticker for ticker in self.tickers if ticker['visible']]


class GoalViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows goals to be viewed or edited
    """
    queryset = Goal.objects.all().order_by('updated')
    serializer_class = GoalSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = '__all__'
