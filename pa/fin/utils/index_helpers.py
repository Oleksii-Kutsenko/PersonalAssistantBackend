from fin.models.index import Index
from fin.utils.yf_patch import YFinanceTicker


def update_tickers_industries(index_id):
    for ticker in Index.objects.get(pk=index_id).tickers.all():
        yf_ticker = YFinanceTicker(ticker.symbol.replace('.', '-'))
        ticker.country = yf_ticker.info.get('country', 'Unknown')
        ticker.industry = yf_ticker.info.get('industry', 'Unknown')
        ticker.sector = yf_ticker.info.get('sector', 'Unknown')
        ticker.save()
