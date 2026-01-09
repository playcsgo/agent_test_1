from datetime import datetime

def get_share_price(symbol: str) -> float:
    prices = {
        'AAPL': 150.0,
        'TSLA': 250.0,
        'GOOGL': 140.0
    }
    return prices.get(symbol, 0.0)

class Account:
    def __init__(self, username: str) -> None:
        self.username = username
        self.balance = 0.0
        self.holdings = {}
        self.transactions = []
        self.initial_deposit = 0.0

    def deposit(self, amount: float) -> bool:
        if amount <= 0:
            return False
        self.balance += amount
        self.initial_deposit += amount
        transaction = {
            'type': 'deposit',
            'amount': amount,
            'timestamp': datetime.now().isoformat(),
            'balance_after': self.balance
        }
        self.transactions.append(transaction)
        return True

    def withdraw(self, amount: float) -> bool:
        if amount <= 0 or amount > self.balance:
            return False
        self.balance -= amount
        transaction = {
            'type': 'withdrawal',
            'amount': amount,
            'timestamp': datetime.now().isoformat(),
            'balance_after': self.balance
        }
        self.transactions.append(transaction)
        return True

    def buy_shares(self, symbol: str, quantity: int) -> bool:
        if quantity <= 0:
            return False
        price = get_share_price(symbol)
        if price == 0.0:
            return False
        total_cost = price * quantity
        if total_cost > self.balance:
            return False
        self.balance -= total_cost
        if symbol not in self.holdings:
            self.holdings[symbol] = 0
        self.holdings[symbol] += quantity
        transaction = {
            'type': 'buy',
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'total_cost': total_cost,
            'timestamp': datetime.now().isoformat(),
            'balance_after': self.balance
        }
        self.transactions.append(transaction)
        return True

    def sell_shares(self, symbol: str, quantity: int) -> bool:
        if quantity <= 0:
            return False
        if symbol not in self.holdings or self.holdings[symbol] < quantity:
            return False
        price = get_share_price(symbol)
        if price == 0.0:
            return False
        total_proceeds = price * quantity
        self.balance += total_proceeds
        self.holdings[symbol] -= quantity
        if self.holdings[symbol] == 0:
            del self.holdings[symbol]
        transaction = {
            'type': 'sell',
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'total_proceeds': total_proceeds,
            'timestamp': datetime.now().isoformat(),
            'balance_after': self.balance
        }
        self.transactions.append(transaction)
        return True

    def calculate_portfolio_value(self) -> float:
        value = self.balance
        for symbol, quantity in self.holdings.items():
            price = get_share_price(symbol)
            value += price * quantity
        return value

    def calculate_profit_loss(self) -> float:
        portfolio_value = self.calculate_portfolio_value()
        return portfolio_value - self.initial_deposit

    def get_holdings(self) -> dict:
        return dict(self.holdings)

    def get_transaction_history(self) -> list:
        return list(self.transactions)

    def report_holdings(self) -> str:
        if not self.holdings:
            return "Current Holdings: None"
        report = "Current Holdings:\n"
        for symbol, quantity in self.holdings.items():
            price = get_share_price(symbol)
            value = price * quantity
            report += f"  {symbol}: {quantity} shares @ ${price:.2f} = ${value:.2f}\n"
        report += f"Cash Balance: ${self.balance:.2f}"
        return report

    def report_profit_loss(self) -> str:
        pl = self.calculate_profit_loss()
        portfolio_value = self.calculate_portfolio_value()
        if pl >= 0:
            return f"Portfolio Value: ${portfolio_value:.2f}\nProfit: ${pl:.2f}"
        else:
            return f"Portfolio Value: ${portfolio_value:.2f}\nLoss: ${abs(pl):.2f}"