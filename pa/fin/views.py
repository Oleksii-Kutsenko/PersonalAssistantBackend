"""
Views
"""
from decimal import Decimal, InvalidOperation

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

    Send PUT request with the same data_source_url for reloading index data
    """
    queryset = Index.objects.all().order_by('updated')
    serializer_class = IndexSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = '__all__'


class AdjustedIndex(APIView):
    """
    API endpoint that allows executing adjust method of the index
    """
    money = None

    def get(self, request, index_id):
        """
        Calculate index adjusted by the amount of money
        """
        try:
            self.money = Decimal(request.GET.get('money'))
        except InvalidOperation:
            raise BadRequest(detail="Money parameter is missing or invalid")

        index = get_object_or_404(queryset=Index.objects.all(), pk=index_id)

        return Response(index.adjust(self.money))


class GoalViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows goals to be viewed or edited
    """
    queryset = Goal.objects.all().order_by('updated')
    serializer_class = GoalSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = '__all__'
