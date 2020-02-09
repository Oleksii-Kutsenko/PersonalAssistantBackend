from rest_framework import filters, viewsets

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
