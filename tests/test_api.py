from vaultuno import VUAPI, URL, ProviderType, RebalanceState
from datetime import datetime, timedelta, timezone
from typing import Dict
import unittest

VU_API_KEY = "Your Vaultuno API Key"
VU_BASE_URL = "https://api.vaultuno.com"

ALPACA_API_KEY = "Your Alpaca Paper API Key"
ALPACA_API_SECRET = "Your Alpaca Paper API Secret"


def alpaca_settings() -> Dict[str, str]:
    return {
        "type": "paper",
        "keyId": ALPACA_API_KEY,
        "keySecret": ALPACA_API_SECRET
    }


class VUTest(unittest.TestCase):
    def test_accounts(self):
        vu = VUAPI(VU_API_KEY, URL(VU_BASE_URL))

        broker_accounts = vu.list_broker_accounts()
        self.assertIsNotNone(broker_accounts)
        number_of_accounts = len(broker_accounts)

        broker_account = vu.register_broker_account(ProviderType.ALPACA_PROVIDER,
                                                    "Some Account",
                                                    "Used to test account creation",
                                                    alpaca_settings())
        self.assertEqual(broker_account.name, "Some Account")
        self.assertEqual(broker_account.description, "Used to test account creation")

        broker_account = vu.update_broker_account(broker_account.id, "Some other name", "Some other description")
        self.assertEqual(broker_account.name, "Some other name")
        self.assertEqual(broker_account.description, "Some other description")

        broker_accounts = vu.list_broker_accounts()
        self.assertEqual(number_of_accounts+1, len(broker_accounts))

        vu.delete_broker_account(broker_account.id)

        broker_accounts = vu.list_broker_accounts()
        self.assertEqual(number_of_accounts, len(broker_accounts))

        vu.close()

    def test_portfolios(self):
        vu = VUAPI(VU_API_KEY, URL(VU_BASE_URL))
        broker_account = vu.register_broker_account(ProviderType.ALPACA_PROVIDER,
                                                    "Some Account",
                                                    "Used to test portfolios",
                                                    alpaca_settings())
        self.assertEqual(broker_account.name, "Some Account")
        self.assertEqual(broker_account.description, "Used to test portfolios")

        portfolio = vu.create_portfolio(broker_account.id, "Some Portfolio", "Used to test portfolios")
        self.assertEqual(portfolio.name, "Some Portfolio")
        self.assertEqual(portfolio.description, "Used to test portfolios")
        self.assertEqual(portfolio.weight, 0.0)

        portfolios = vu.list_portfolios(broker_account.id)
        self.assertIsNotNone(portfolios)
        self.assertEqual(len(portfolios), 1)

        portfolio = vu.update_portfolio(portfolio.id, portfolio.name, portfolio.description, 50.0)
        self.assertEqual(portfolio.weight, 50.0)

        positions = vu.list_positions(portfolio.id)
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0].weight, 100.0)
        self.assertEqual(positions[0].symbol, "$$$")

        positions = vu.update_positions(portfolio.id, {
            "AAPL": 50.0,
            "TSLA": 50.0
        })
        self.assertEqual(len(positions), 3)
        for position in positions:
            if position.symbol == "AAPL":
                self.assertEqual(position.weight, 50.0)
            elif position.symbol == "TSLA":
                self.assertEqual(position.weight, 50.0)
            elif position.symbol == "$$$":
                self.assertEqual(position.weight, 0.0)

        positions = vu.update_positions(portfolio.id, {
            "AAPL": 40.0
        })
        self.assertEqual(len(positions), 3)
        for position in positions:
            if position.symbol == "AAPL":
                self.assertEqual(position.weight, 40.0)
            elif position.symbol == "TSLA":
                self.assertEqual(position.weight, 0.0)
            elif position.symbol == "$$$":
                self.assertEqual(position.weight, 60.0)

        vu.delete_portfolio(portfolio.id)

        portfolios = vu.list_portfolios(broker_account.id)
        self.assertIsNotNone(portfolios)
        self.assertEqual(len(portfolios), 0)

        vu.delete_broker_account(broker_account.id)
        vu.close()

    def test_simulation(self):
        vu = VUAPI(VU_API_KEY, URL(VU_BASE_URL))
        broker_account = vu.register_broker_account(ProviderType.ALPACA_PROVIDER,
                                                    "Some Account",
                                                    "Used to test portfolios",
                                                    alpaca_settings())
        portfolio = vu.create_portfolio(broker_account.id, "Some Portfolio", "Used to test portfolios", 100.0)
        vu.update_positions(portfolio.id, {
            "AAPL": 50.0,
            "TSLA": 50.0
        })

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=180)

        portfolio_performance = vu.simulate_portfolio(portfolio.id, start, end)
        account_performance = vu.simulate_broker_account(broker_account.id, start, end)
        self.assertEqual(round(portfolio_performance['assets'].cagr, 2), round(account_performance['assets'].cagr, 2))

        vu.delete_broker_account(broker_account.id)
        vu.close()

    def test_rebalancing(self):
        vu = VUAPI(VU_API_KEY, URL(VU_BASE_URL))
        broker_account = vu.register_broker_account(ProviderType.ALPACA_PROVIDER,
                                                    "Some Account",
                                                    "Used to test portfolios",
                                                    alpaca_settings())
        portfolio = vu.create_portfolio(broker_account.id, "Some Portfolio", "Used to test portfolios", 40.0)
        vu.update_positions(portfolio.id, {
            "AAPL": 50.0,
            "TSLA": 50.0
        })

        broker_account = vu.rebalance_broker_account(broker_account.id)
        self.assertEqual(broker_account.rebalanceState, RebalanceState.READY)

        positions = vu.list_positions(portfolio.id)
        for position in positions:
            self.assertTrue(position.quantity > 0 or position.assetClass == "CASH")

        broker_account_positions = vu.list_broker_account_positions(broker_account.id)
        for broker_account_position in broker_account_positions:
            for position in positions:
                if position.assetClass != 'CASH' and broker_account_position.symbol == position.symbol:
                    self.assertEqual(broker_account_position.quantity, position.quantity)
                    self.assertEqual(broker_account_position.averageEntryPrice, position.averageEntryPrice)

        broker_account = vu.liquidate_broker_account(broker_account.id)
        self.assertEqual(broker_account.rebalanceState, RebalanceState.READY)

        positions = vu.list_positions(portfolio.id)
        for position in positions:
            self.assertTrue(position.quantity == 0 or position.assetClass == "CASH")

        vu.delete_broker_account(broker_account.id)
        vu.close()


if __name__ == "__main__":
    unittest.main(failfast=True)
