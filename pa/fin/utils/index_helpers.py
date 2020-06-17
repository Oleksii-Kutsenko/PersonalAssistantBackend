from fin.models.index import Ticker
from fin.utils.yf_patch import YFinanceTicker


def update_tickers_industries():
    tickers_query = Ticker.objects \
        .filter(sector=Ticker.DEFAULT_VALUE) \
        .filter(industry=Ticker.DEFAULT_VALUE)

    for ticker in tickers_query:
        yf_ticker = YFinanceTicker(ticker.symbol.replace('.', '-'))
        ticker.country = yf_ticker.info.get('country', Ticker.DEFAULT_VALUE)
        ticker.industry = yf_ticker.info.get('industry', Ticker.DEFAULT_VALUE)
        ticker.sector = yf_ticker.info.get('sector', Ticker.DEFAULT_VALUE)
        ticker.save()
