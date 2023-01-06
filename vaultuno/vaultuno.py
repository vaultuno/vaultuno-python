import json
import logging
import time
from datetime import datetime
from typing import Type, List, Dict, Optional

import requests
from requests.exceptions import HTTPError

from vaultuno import __version__
from .common import (
    get_base_url,
    get_api_version,
    URL
)
from .entity import (
    ProviderType,
    RebalanceState,
    Entity,
    Profile,
    BrokerAccount,
    Portfolio,
    Position,
    Performance,
    RebalancingFrequency,
    ReportingPeriod
)

logger = logging.getLogger(__name__)
BrokerAccounts = List[BrokerAccount]
Portfolios = List[Portfolio]
Positions = List[Position]


class RetryException(Exception):
    pass


class APIError(Exception):
    def __init__(self, error, http_error=None):
        super().__init__(error['message'])
        self._error = error
        self._http_error = http_error

    @property
    def code(self):
        return self._error['code']

    @property
    def status_code(self):
        http_error = self._http_error
        if http_error is not None and hasattr(http_error, 'response'):
            return http_error.response.status_code

    @property
    def request(self):
        if self._http_error is not None:
            return self._http_error.request

    @property
    def response(self):
        if self._http_error is not None:
            return self._http_error.response


class VUAPI(object):
    def __init__(self,
                 api_key: str = None,
                 base_url: URL = None,
                 api_version: str = None,
                 raw_data: bool = False):
        self.api_key = api_key
        self._base_url: URL = URL(base_url or get_base_url())
        self._use_raw_data = raw_data
        self._retry = 3
        self._retry_wait = 3
        self._retry_codes = (429, 504)
        self._api_version = get_api_version(api_version)
        self._session = requests.Session()

    def _request(self,
                 method,
                 path,
                 data=None,
                 base_url: URL = None,
                 api_version: str = None):
        base_url = base_url or self._base_url
        version = api_version if api_version else self._api_version
        url: URL = URL(base_url + '/' + version + path)
        headers = {
            'Authorization': 'Bearer ' + self.api_key,
            'User-Agent': 'VAULTUNO-SDK-PY/' + __version__
        }
        opts = {
            'headers': headers,
            'allow_redirects': False,
        }
        if method.upper() in ['GET', 'DELETE']:
            opts['params'] = data
        else:
            opts['json'] = data

        retry = self._retry
        if retry < 0:
            retry = 0
        while retry >= 0:
            try:
                return self._one_request(method, url, opts, retry)
            except RetryException:
                retry_wait = self._retry_wait
                logger.warning(
                    'sleep {} seconds and retrying {} '
                    '{} more time(s)...'.format(
                        retry_wait, url, retry))
                time.sleep(retry_wait)
                retry -= 1
                continue

    def _one_request(self, method: str, url: URL, opts: dict, retry: int):
        retry_codes = self._retry_codes
        resp = self._session.request(method, url, **opts)
        try:
            resp.raise_for_status()
        except HTTPError as http_error:
            if resp.status_code in retry_codes and retry > 0:
                raise RetryException()
            if 'code' in resp.text:
                error = resp.json()
                if 'code' in error:
                    raise APIError(error, http_error)
            else:
                raise
        if resp.text != '':
            return resp.json()
        return None

    def _get(self, path, data=None):
        return self._request('GET', path, data)

    def _get_all_pages(self, path, data=None):
        page = 0
        total_pages = 1
        entities = []
        while page < total_pages:
            paging = {
                "size": 100,
                "page": page
            }
            if data:
                paging.update(data)
            resp = self._get(path, paging)
            total_pages = resp['totalPages']
            content = resp['content']
            entities = entities + content
            page += 1
        return entities

    def _post(self, path, data=None):
        return self._request('POST', path, data)

    def _put(self, path, data=None):
        return self._request('PUT', path, data)

    def _patch(self, path, data=None):
        return self._request('PATCH', path, data)

    def _delete(self, path, data=None):
        return self._request('DELETE', path, data)

    def close(self):
        if self._session:
            self._session.close()

    def _response_wrapper(self, obj, entity: Type[Entity]):
        if self._use_raw_data:
            return obj
        else:
            return entity(obj)

    def _wait_for_account(self, account_id: str, seconds: int = 3, retry: int = 10,
                          state: RebalanceState = RebalanceState.READY) -> Optional[BrokerAccount]:
        while retry > 0:
            time.sleep(seconds)
            account = self.get_broker_account(account_id)
            if account.rebalanceState == state:
                return account
            retry -= 1
        return None

    # ----------------------------------------- User Profile ---------------------------------------

    def get_profile(self) -> Profile:
        resp = self._get('/users/me')
        return self._response_wrapper(resp, Profile)

    # ----------------------------------------- Broker Accounts ---------------------------------------

    def list_broker_accounts(self) -> BrokerAccounts:
        entities = self._get_all_pages('/accounts')
        return [self._response_wrapper(o, BrokerAccount) for o in entities]

    def register_broker_account(self, provider: ProviderType, name: str, description: str,
                                settings: Dict[str, str]) -> BrokerAccount:
        data = {
            "name": name,
            "description": description,
            "providerId": provider,
            "providerSettings": json.dumps(settings)
        }
        resp = self._post("/accounts", data)
        return self._response_wrapper(resp, BrokerAccount)

    def delete_broker_account(self, account_id: str) -> None:
        self._delete("/accounts/{}".format(account_id))

    def update_broker_account(self, account_id: str, name: str, description: str,
                              settings: Dict[str, str] = None) -> BrokerAccount:
        data = {
            "type": "paper",
            "name": name,
            "description": description,
        }
        if settings:
            data["providerSettings"] = json.dumps(settings)
        resp = self._put("/accounts/{}".format(account_id), data)
        return self._response_wrapper(resp, BrokerAccount)

    def simulate_broker_account(self, account_id: str, start: datetime, end: datetime, cash: float = 30000,
                                rebalancing_frequency: RebalancingFrequency = RebalancingFrequency.MONTHLY,
                                benchmark: str = 'SPY') -> Dict[str, Performance]:
        data = {
            "cash": cash,
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "rebalancingFrequency": rebalancing_frequency,
            "benchmarkSymbol": benchmark
        }
        resp = self._post("/accounts/{}/simulate".format(account_id), data)
        return {
            "assets": self._response_wrapper(resp["assets"], Performance),
            "benchmark": self._response_wrapper(resp["benchmark"], Performance) if resp["benchmark"] else None
        }

    def analyze_broker_account(self, account_id: str,
                               reporting_period: ReportingPeriod = ReportingPeriod.M1,
                               benchmark: str = 'SPY') -> Dict[str, Performance]:
        data = {
            "reportingPeriod": reporting_period,
            "benchmarkSymbol": benchmark
        }
        resp = self._post("/accounts/{}/report_performance".format(account_id), data)
        return {
            "assets": self._response_wrapper(resp["assets"], Performance),
            "benchmark": self._response_wrapper(resp["benchmark"], Performance) if resp["benchmark"] else None
        }

    def get_broker_account(self, account_id: str) -> BrokerAccount:
        resp = self._get("/accounts/{}".format(account_id))
        return self._response_wrapper(resp, BrokerAccount)

    def rebalance_broker_account(self, account_id: str) -> Optional[BrokerAccount]:
        self._post("/accounts/{}/rebalance".format(account_id))
        return self._wait_for_account(account_id)

    def liquidate_broker_account(self, account_id: str) -> Optional[BrokerAccount]:
        self._post("/accounts/{}/liquidate".format(account_id))
        return self._wait_for_account(account_id)

    def cancel_rebalancing(self, account_id: str) -> Optional[BrokerAccount]:
        self._post("/accounts/{}/rebalance".format(account_id))
        return self._wait_for_account(account_id)

    # ----------------------------------------- Portfolios ---------------------------------------

    def create_portfolio(self, account_id: str, name: str, description: str, weight: float = 0.0) -> Portfolio:
        data = {
            "name": name,
            "description": description,
            "weight": weight,
            "accountId": account_id
        }
        resp = self._post("/portfolios", data)
        return self._response_wrapper(resp, Portfolio)

    def list_portfolios(self, account_id: str) -> Portfolios:
        portfolios = self._get_all_pages("/portfolios", {"accountId": account_id})
        return [self._response_wrapper(o, Portfolio) for o in portfolios]

    def update_portfolio(self, portfolio_id: str, name: str, description: str, weight: float) -> Portfolio:
        data = {
            "name": name,
            "description": description,
            "weight": weight
        }
        resp = self._put("/portfolios/{}".format(portfolio_id), data)
        return self._response_wrapper(resp, Portfolio)

    def liquidate_portfolio(self, account_id: str, portfolio_id: str) -> None:
        self._post("/portfolios/{}/liquidate".format(portfolio_id))
        return self._wait_for_account(account_id)

    def delete_portfolio(self, portfolio_id: str) -> None:
        self._delete("/portfolios/{}".format(portfolio_id))

    def simulate_portfolio(self, portfolio_id: str, start: datetime, end: datetime, cash: float = 30000,
                           rebalancing_frequency: RebalancingFrequency = RebalancingFrequency.MONTHLY,
                           benchmark: str = 'SPY') -> Dict[str, Performance]:
        data = {
            "cash": cash,
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "rebalancingFrequency": rebalancing_frequency,
            "benchmarkSymbol": benchmark
        }
        resp = self._post("/portfolios/{}/simulate".format(portfolio_id), data)
        return {
            "assets": self._response_wrapper(resp["assets"], Performance),
            "benchmark": self._response_wrapper(resp["benchmark"], Performance) if resp["benchmark"] else None
        }

    def analyze_portfolio(self, portfolio_id: str,
                          reporting_period: ReportingPeriod = ReportingPeriod.M1,
                          benchmark: str = 'SPY') -> Dict[str, Performance]:
        data = {
            "reportingPeriod": reporting_period,
            "benchmarkSymbol": benchmark
        }
        resp = self._post("/portfolios/{}/report_performance".format(portfolio_id), data)
        return {
            "assets": self._response_wrapper(resp["assets"], Performance),
            "benchmark": self._response_wrapper(resp["benchmark"], Performance) if resp["benchmark"] else None
        }

    # ----------------------------------------- Positions ---------------------------------------

    def list_broker_account_positions(self, account_id: str) -> Positions:
        positions = self._get_all_pages("/accounts/{}/positions".format(account_id))
        return [self._response_wrapper(o, Position) for o in positions]

    def list_positions(self, portfolio_id: str) -> Positions:
        positions = self._get_all_pages("/portfolios/{}/positions".format(portfolio_id))
        return [self._response_wrapper(o, Position) for o in positions]

    def update_positions(self, portfolio_id: str, positions: Dict[str, float]) -> Positions:
        symbols = list(positions.keys())
        weights = list(positions.values())
        positions = self._put("/portfolios/{}/weights".format(portfolio_id), {
            "symbols": symbols,
            "weights": weights
        })
        return [self._response_wrapper(o, Position) for o in positions]
