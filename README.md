# vaultuno-python

`vaultuno-python` is a Python library for [Vaultuno Portfolio Management](https://www.vaultuno.com). 
Vaultuno provides intuitive apps and powerful APIs for management of investment portfolios. Investors can 
focus on the creative part of the investment process and rely on Vaultuno for optimal trade 
execution and portfolio maintenance.

# API Keys

You need to obtain an API to use this package. Go here to [signup](https://www.vaultuno.com)

# Registering a broker account 

As the first step, register a broker account. One broker account can be used to manage 
several portfolios. You can register any number of broker accounts. 

You only need to register an account once. The registration record persists until deleted.

Here is how one could register an [Alpaca](https://alpaca.markets) paper trading account: 

```py
from vaultuno import VUAPI, ProviderType

vu = VUAPI(VU_API_KEY)
alpaca_account_settings = {
    "type": "paper",
    "keyId": ALPACA_API_KEY,
    "keySecret": ALPACA_API_SECRET
}
broker_account = vu.register_broker_account(ProviderType.ALPACA_PROVIDER,
                                            "Alpaca Paper Trading",
                                            "I use this account to test investment strategies",
                                            alpaca_account_settings)
```

We recommend resetting your Alpaca paper trading account before registering it.

# Creating a portfolio

Once a broker account is registered, it can be used to create a portfolio: 

```py
portfolio = vu.create_portfolio(broker_account.id, "Stocks", "Used to test a portfolio")

```

Each portfolio has a weight, a number in the range of [0, 100]. A new portfolio is 
created with the weight of 0, which is enough for backtesting. To allocate funds to a portfolio, 
change its weight to number greater than 0. The sum of weights of all portfolios in 
an account cannot be greater than 100.

To update the weight of a portfolio, do the following:

```py
portfolio = vu.update_portfolio(portfolio.id, portfolio.name, portfolio.description, 50.0)
```

We just changed the weight of a portfolio to 50.

Each portfolio has a default position with the reserved symbol `$$$`. This position 
represents the unallocated portion of the portfolio, that is, cash. 

We can use the `update_positions` method to add assets to the portfolio: 

```py
positions = vu.update_positions(portfolio.id, {
    "AAPL": 50.0,
    "TSLA": 50.0
})
```

Our portfolio now has three positions, `AAPL`, `TSLA`, and `$$$`, with the weights of 
50, 50, and 0 respectively.

# Running a backtest 

Investment performance can be backtested at the portfolio or account level. 

To run a backtest at the portfolio level, use the `simulate_portfolio` method:

```py
end = datetime.now(timezone.utc)
start = end - timedelta(days=180)
portfolio_performance = vu.simulate_portfolio(portfolio.id, start, end)
```

To backtest the portfolio of all investment portfolios in a broker account, use the 
`simulate_broker_account` method: 

```py
account_performance = vu.simulate_broker_account(broker_account.id, start, end)
```

# Rebalancing portfolios 

Use the `rebalance_broker_account` method to rebalance all portolios in a broker account. 
The method chooses an optimal path to bring asset positions in a portfolio and portfolio 
positions in an account into accordance with their target weights: 

```py
broker_account = vu.rebalance_broker_account(broker_account.id)
```

**Important:** This method can only be run when the market is open. When the market is closed, 
orders are submitted but the method call returns with a timeout error. The orders can be canceled 
using the `cancel_rebalancing` method:

```py
vu.cancel_rebalancing(account.id)
```

# Analyzing performance

To analyze the performance of a portfolio or account and compare it with the performance of a benchmark, 
use the `analyze_portfolio` and `analyze_broker_account` methods:

```py
from vaultuno import ReportingPeriod
portfolio_performace = vu.analyze_portfolio(portfolio.id, ReportingPeriod.M6, 'SPY')
account_performance = vu.analyze_broker_account(account.id, ReportingPeriod.Y1, 'SPY')
```

# Liquidating and deleting

A portfolio must be liquidated, or sold, before it can be deleted. 

To liquidate a portfolio, use the `liquidate_portfolio` method:

```py
vu.liquidate_portfolio(account.id, portfolio.id)
```

Similarly, the entire account can be liquidated using the `liquidate_broker_account` method: 

```py
vu.liquidate_broker_account(account.id)
```

**Important:** These methods can only be run when the market is open. When the market is closed, 
orders are submitted but the methods return with a timeout error. The orders can be canceled 
using the `cancel_rebalancing` method:

```py
vu.cancel_rebalancing(account.id)
```

Portfolios and accounts that do not have any allocated assets can be deleted as follows:

```py
vu.delete_portfolio(portfolio.id)
vu.delete_broker_account(account.id)
```