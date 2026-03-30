from pydantic import BaseModel
import json
from dotenv import load_dotenv
from datetime import datetime
from market import get_share_price
from database import write_account, read_account, write_log


INITIAL_BALANCE = 10_000.0
SPREAD = 0.002


class Transaction(BaseModel):
    symbol: str
    quantity: int
    price: float
    timestamp: str
    rationale: str

    def total(self) -> float:
        return self.quantity * self.price
    
    def __repr__(self):
        return f'{abs(self.quantity)} shares of {self.symbol} at {self.price}'
    

class Account(BaseModel):
    name: str
    balance: float
    strategy: str
    holdings: dict[str, int]
    transactions: list[Transaction]
    portfolio_value_time_series: list[tuple[str, float]]

    @classmethod
    def get(cls, name: str):
        fields = read_account(name.lower())
        if not fields:
            fields = {
                "name": name.lower(),
                "balance": INITIAL_BALANCE,
                "strategy": "",
                "holdings": {},
                "transactions": [],
                "portfolio_value_time_series": []
            }
            write_account(name, fields)
        return cls(**fields)
    

    def save(self):
        # 使用model_dump()將資料轉為dict or json 才能存入資料庫
        write_account(self.name.lower(), self.model_dump())

    
    def reset(self, strategy: str):
        self.balance = INITIAL_BALANCE
        self.strategy = strategy
        self.holdings = {}
        self.transactions = []
        self.portfolio_value_time_series = []
        self.save()
    

    def deposit(self, amount: float):
        ''' Deposit funds into the account '''
        if amount <= 0:
            raise ValueError('Deposit amount should be positive number')
        self.balance += amount
        print(f'Deposied ${amount}. New balance: ${self.balance}')
        self.save()
    

    def withdraw(self, amount: float):
        ''' Withdraw funds from the account '''
        if amount > self.balance:
            raise ValueError('Insufficient funds for withdrawal.')
        self.balance -= amount
        print(f"Withdrew ${amount}. New balance: ${self.balance}")
        self.save()
    

    def buy_shares(self, symbol: str, quantity: int, rationale: str) -> str:
        ''' buy shares if sufficient funds '''
        price = get_share_price(symbol)
        buy_price = price * (1 + SPREAD)
        total_cost = buy_price * quantity

        if total_cost > self.balance:
            raise ValueError("Insufficient funds to buy shares.")
        elif price == 0:
            raise ValueError(f"Unrecognized symbol {symbol}")
        
        ## actions should be transaction in DB. this one just mock so keep as simple as it is.

        # update holdings
        self.holdings[symbol] = self.holdings.get(symbol, 0) + quantity
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # record transaction
        transaction = Transaction(symbol=symbol, quantity=quantity, price = buy_price, timestamp=timestamp, rationale=rationale)
        self.transactions.append(transaction)

        # update balance
        self.balance -= total_cost
        self.save()
        write_log(self.name, 'account', f'Bought {quantity} of {symbol}')
        return "Completed. Latest details:\n" + self.report()
    
    def sell_shares(self, symbol: str, quantity: int, rationale: str) -> str:
        ''' Sell shares if account got enough '''
        if self.holdings.get(symbol, 0) < quantity:
            raise ValueError(f"Cannot sell {quantity} shares of {symbol}. Not enough shares held.")
        price = get_share_price(symbol)
        sell_price = price * (1 - SPREAD)
        total_proceeds = sell_price * quantity

        self.holdings[symbol] -= quantity
        if self.holdings[symbol] == 0:
            del self.holdings[symbol]
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        transaction = Transaction(symbol=symbol, quantity=-quantity, price=sell_price, timestamp=timestamp, rationale=rationale)
        self.transactions.append(transaction)

        self.balance += total_proceeds
        self.save()
        write_log(self.name, 'account', f"Sold {quantity} of {symbol}")
        return "Completed. Latest details:\n" + self.report()
    

    def calculate_portfolio_value(self):
        """ Calculate the total value of the user's portfolio """
        total_value = self.balance
        for symbol, quantity in self.holdings.items():
            total_value += get_share_price(symbol) * quantity
        
        return total_value
    
    
    def calculate_profit_loss(self, porfolio_value: float):
        ''' Calculate account profit or loss from the initial spend '''
        initial_spend = sum(transaction.total() for transaction in self.transactions)
        return porfolio_value - initial_spend - self.balance
    

    def get_holdings(self):
        ''' Reoport curent hildings of account '''
        return self.holdings
    

    # def get_profit_loss(self):
    #     '''Report profit or loss '''
    #     return self.calculate_profit_loss() # how it can be call

    
    def list_transactions(self):
        '''List all transactions of this account'''
        return [transaction.model_dump() for transaction in self.transactions]
    

    def report(self) -> str:
        '''Return a json string representing the account. '''
        portfolio_value = self.calculate_portfolio_value()
        self.portfolio_value_time_series.append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), portfolio_value))
        self.save()

        pnl = self.calculate_profit_loss(portfolio_value)
        data = self.model_dump()
        data['total_portfolio_value'] = portfolio_value
        data["total_profit_loss"] = pnl

        write_log(self.name, 'account', f'Retrieved account details')
        return json.dumps(data)
    

    def get_strategy(self) -> str:
        """ Return the strategy of the account """
        write_log(self.name, "account", f"Retrieved strategy")
        return self.strategy
    

    def change_strategy(self, strategy: str) -> str:
        old_strategy = self.strategy
        self.strategy = strategy
        self.save()
        write_log(self.name, 'account', f"Changed strategy")
        return f'strategy changed from {old_strategy} to {strategy}'




        

