"""
Views
"""
import logging

from rest_framework import filters, viewsets
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from fin.serializers.portfolio.portfolio import (
    PortfolioSerializer,
    AccountSerializer,
    DetailedPortfolioSerializer,
    ExanteImportSerializer,
)
from .exceptions import BadRequest
from .mixins import UpdateTickersMixin, AdjustMixin
from .models.account import Account
from .models.index import Index, Source
from .models.portfolio import Portfolio, ExanteSettings
from .models.portfolio.portfolio_policy import PortfolioPolicy
from .serializers.index import IndexSerializer, DetailIndexSerializer
from .serializers.portfolio.exante_settings import ExanteSettingsSerializer
from .serializers.portfolio.portfolio_policy import PortfolioPolicySerializer
from .serializers.source import SourceSerializer
from .tasks.update_tickers_statements import update_model_tickers_statements_task

logger = logging.getLogger(__name__)


class AccountViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows accounts to be viewed or edited
    """

    queryset = Account.objects.all().order_by("updated")
    serializer_class = AccountSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = "__all__"


class ExanteSettingsViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    External interface for ExanteSettings model
    """

    queryset = ExanteSettings.objects.all()
    serializer_class = ExanteSettingsSerializer


class IndexViewSet(UpdateTickersMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows indices to be viewed or edited

    Send PUT request with the same data_source_url for reloading index data
    """

    queryset = Index.objects.all().order_by("updated")
    filter_backends = [filters.OrderingFilter]
    model = Index
    ordering_fields = "__all__"

    def get_serializer_class(self):
        if self.action == "retrieve" or self.action == "update":
            return DetailIndexSerializer
        return IndexSerializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        update_model_tickers_statements_task.delay(
            self.model.__name__, response.data.get("id")
        )
        return response


class PortfolioViewSet(AdjustMixin, UpdateTickersMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows to view portfolio
    """

    filter_backends = [filters.OrderingFilter]
    model = Portfolio
    ordering_fields = "__all__"

    def get_queryset(self):
        queryset = Portfolio.objects.filter(user=self.request.user).all()
        return queryset

    def get_serializer_class(self):
        if self.action == "metadata":
            if self.action_map == {"put": "import_from_exante"}:
                return ExanteImportSerializer
            return PortfolioSerializer
        if self.action == "import_from_exante":
            return ExanteImportSerializer

        if self.action == "retrieve":
            return DetailedPortfolioSerializer
        return PortfolioSerializer

    # pylint: disable=unused-argument
    @action(detail=True, url_path="adjust/indices/(?P<index_id>[^/.]+)")
    def adjust(self, request, *args, **kwargs):
        """
        Returns tickers that should be inside portfolio to make portfolio more similar to index
        """
        if self.money is None:
            raise BadRequest(detail="Money parameter is invalid")
        index_id = kwargs.get("index_id")
        portfolio_id = kwargs.get("pk")

        portfolio = Portfolio.objects.get(pk=portfolio_id)
        adjusted_portfolio = portfolio.adjust(index_id, self.money, self.adjust_options)

        return Response(data={"tickers": adjusted_portfolio})

    @action(detail=True, methods=["PUT"])
    def import_from_exante(self, request, *args, **kwargs):
        """
        Import portfolio from Exante
        """
        portfolio = self.get_object()

        serializer = self.get_serializer(data=request.data, instance=portfolio)
        serializer.is_valid(raise_exception=True)

        portfolio.import_from_exante(serializer.validated_data.pop("secret_key"))

        serializer = DetailedPortfolioSerializer(portfolio)
        return Response(serializer.data)

    # pylint: enable=unused-argument


class PortfolioPolicyViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows portfolio policy to be viewed or edited
    """

    serializer_class = PortfolioPolicySerializer

    def get_queryset(self):
        queryset = (
            PortfolioPolicy.objects.filter(portfolio__user_id=self.request.user)
            .order_by("-id")
            .all()
        )
        return queryset


class SourceViewSet(viewsets.ModelViewSet):
    """
    CRUD for the Source model
    """

    queryset = Source.objects.all()
    serializer_class = SourceSerializer
