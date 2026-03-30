from polygon import RESTClient
from dotenv import load_dotenv
import os
from datetime import datetime
import random
from database import write_market, read_market
from functools import lru_cache
from datetime import timezone
from typing import cast
from polygon.rest.models import PreviousCloseAgg, GroupedDailyAgg, TickerSnapshot
import sys

load_dotenv(override=True)


polygon_api_key = os.getenv("POLYGON_API_KEY")
polygon_plan = os.getenv("POLYGON_PLAN")

is_paid_polygon = polygon_plan == "paid"
is_realtime_polygon = polygon_plan == "realtime"


def is_market_open() -> bool:
    client = RESTClient(polygon_api_key)
    market_status = client.get_market_status()
    # return market_status?.market == 'open' as .js
    return getattr(market_status, "market", None) == "open"


# def get_all_share_prices_polygon_eod() -> dict[str, float]:
#     client = RESTClient(polygon_api_key)

#     # probe = client.get_previous_close_agg("SPY")[0]
#     probe = client.get_previous_close_agg("SPY")
#     last_close = datetime.fromtimestamp(probe.timestamp / 1000, tz=timezone.utc).date()

#     results = client.get_grouped_daily_aggs(last_close, adjusted=True, include_otc=False)
#     return {
#         result.ticker: result.close
#         for result in results
#         if result.ticker is not None and result.close is not None
#     }

def get_all_share_prices_polygon_eod() -> dict[str, float]:
    # for multi request need to apply async 
    # from polygon import AsyncRESTClient
    client = RESTClient(polygon_api_key)
    agg_response = client.get_previous_close_agg("SPY")  # type: ignore
    probe = cast(PreviousCloseAgg, agg_response[0] if isinstance(agg_response, list) else agg_response)
    last_close = datetime.fromtimestamp(cast(float, probe.timestamp) / 1000, tz=timezone.utc).date()

    results = client.get_grouped_daily_aggs(last_close, adjusted=True, include_otc=False)

    out: dict[str, float] = {}
    for result in results:
        result = cast(GroupedDailyAgg, result)
        if result.ticker is not None and result.close is not None:
            out[cast(str, result.ticker)] = cast(float, result.close)
    return out


@lru_cache(maxsize=2)
def get_market_for_prior_date(today):
    market_data = read_market(today)
    if not market_data:
        market_data = get_all_share_prices_polygon_eod()
        write_market(today, market_data)
    return market_data


def get_share_price_polygon_eod(symbol) -> float:
    today = datetime.now().date().strftime("%Y-%m-%d")
    market_data = get_market_for_prior_date(today)
    return market_data.get(symbol, 0.0) #找不到的時候回傳 0


def get_share_price_polygon_min(symbol) -> float:
    client = RESTClient(polygon_api_key)
    #'stocks'   # 美股
    # 'options' # 選擇權
    # 'forex'   # 外匯
    # 'crypto'  # 加密貨幣
    result = cast(TickerSnapshot, client.get_snapshot_ticker('stocks', symbol))
    min_close = cast(float, result.min.close) if result.min and result.min.close is not None else None
    prev_close = cast(float, result.prev_day.close) if result.prev_day and result.prev_day.close is not None else 0.0
    return min_close if min_close is not None else prev_close

    # 使用 cast 等於 Typescript的 as 實際產品應該避免使用
    # 應使用 if isinstance(result, TickerSnapshot):
    #          result.min.close  # Pylance 確定是 TickerSnapshot


def get_share_price_polygon(symbol) -> float:
    if is_paid_polygon:
        return get_share_price_polygon_min(symbol)
    else:
        return get_share_price_polygon_eod(symbol)


def get_share_price(symbol) -> float:
    if polygon_api_key:
        try:
            return get_share_price_polygon(symbol)
        except Exception as e:
            print(f"Was not able to use the polygon API due to {e}; using a random number", file=sys.stderr)
    return float(random.randint(1, 100))