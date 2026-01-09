import unittest
from datetime import datetime
from accounts import Account, get_share_price


class TestGetSharePrice(unittest.TestCase):
    def test_get_share_price_aapl(self):
        self.assertEqual(get_share_price('AAPL'), 150.0)

    def test_get_share_price_tsla(self):
        self.assertEqual(get_share_price('TSLA'), 250.0)

    def test_get_share_price_googl(self):
        self.assertEqual(get_share_price('GOOGL'), 140.0)

    def test_get_share_price_unknown_symbol(self):
        self.assertEqual(get_share_price('UNKNOWN'), 0.0)

    def test_get_share_price_empty_string(self):
        self.assertEqual(get_share_price(''), 0.0)


class TestAccountInitialization(unittest.TestCase):
    def test_account_initialization(self):
        account = Account('testuser')
        self.assertEqual(account.username, 'testuser')
        self.assertEqual(account.balance, 0.0)
        self.assertEqual(account.holdings, {})
        self.assertEqual(account.transactions, [])
        self.assertEqual(account.initial_deposit, 0.0)


class TestAccountDeposit(unittest.TestCase):
    def setUp(self):
        self.account = Account('testuser')

    def test_deposit_positive_amount(self):
        result = self.account.deposit(100.0)
        self.assertTrue(result)
        self.assertEqual(self.account.balance, 100.0)
        self.assertEqual(self.account.initial_deposit, 100.0)

    def test_deposit_multiple_times(self):
        self.account.deposit(100.0)
        self.account.deposit(50.0)
        self.assertEqual(self.account.balance, 150.0)
        self.assertEqual(self.account.initial_deposit, 150.0)

    def test_deposit_zero_amount(self):
        result = self.account.deposit(0.0)
        self.assertFalse(result)
        self.assertEqual(self.account.balance, 0.0)

    def test_deposit_negative_amount(self):
        result = self.account.deposit(-50.0)
        self.assertFalse(result)
        self.assertEqual(self.account.balance, 0.0)

    def test_deposit_creates_transaction(self):
        self.account.deposit(100.0)
        self.assertEqual(len(self.account.transactions), 1)
        transaction = self.account.transactions[0]
        self.assertEqual(transaction['type'], 'deposit')
        self.assertEqual(transaction['amount'], 100.0)
        self.assertEqual(transaction['balance_after'], 100.0)

    def test_deposit_large_amount(self):
        result = self.account.deposit(999999.99)
        self.assertTrue(result)
        self.assertEqual(self.account.balance, 999999.99)


class TestAccountWithdraw(unittest.TestCase):
    def setUp(self):
        self.account = Account('testuser')
        self.account.deposit(500.0)

    def test_withdraw_valid_amount(self):
        result = self.account.withdraw(100.0)
        self.assertTrue(result)
        self.assertEqual(self.account.balance, 400.0)

    def test_withdraw_entire_balance(self):
        result = self.account.withdraw(500.0)
        self.assertTrue(result)
        self.assertEqual(self.account.balance, 0.0)

    def test_withdraw_more_than_balance(self):
        result = self.account.withdraw(600.0)
        self.assertFalse(result)
        self.assertEqual(self.account.balance, 500.0)

    def test_withdraw_zero_amount(self):
        result = self.account.withdraw(0.0)
        self.assertFalse(result)
        self.assertEqual(self.account.balance, 500.0)

    def test_withdraw_negative_amount(self):
        result = self.account.withdraw(-50.0)
        self.assertFalse(result)
        self.assertEqual(self.account.balance, 500.0)

    def test_withdraw_creates_transaction(self):
        self.account.withdraw(100.0)
        self.assertEqual(len(self.account.transactions), 2)
        transaction = self.account.transactions[1]
        self.assertEqual(transaction['type'], 'withdrawal')
        self.assertEqual(transaction['amount'], 100.0)
        self.assertEqual(transaction['balance_after'], 400.0)

    def test_withdraw_from_empty_account(self):
        account = Account('emptyuser')
        result = account.withdraw(100.0)
        self.assertFalse(result)


class TestAccountBuyShares(unittest.TestCase):
    def setUp(self):
        self.account = Account('testuser')
        self.account.deposit(10000.0)

    def test_buy_shares_aapl(self):
        result = self.account.buy_shares('AAPL', 10)
        self.assertTrue(result)
        self.assertEqual(self.account.holdings['AAPL'], 10)
        self.assertEqual(self.account.balance, 10000.0 - (150.0 * 10))

    def test_buy_shares_tsla(self):
        result = self.account.buy_shares('TSLA', 5)
        self.assertTrue(result)
        self.assertEqual(self.account.holdings['TSLA'], 5)
        self.assertEqual(self.account.balance, 10000.0 - (250.0 * 5))

    def test_buy_shares_multiple_stocks(self):
        self.account.buy_shares('AAPL', 10)
        self.account.buy_shares('GOOGL', 20)
        self.assertEqual(self.account.holdings['AAPL'], 10)
        self.assertEqual(self.account.holdings['GOOGL'], 20)

    def test_buy_shares_same_stock_multiple_times(self):
        self.account.buy_shares('AAPL', 10)
        self.account.buy_shares('AAPL', 5)
        self.assertEqual(self.account.holdings['AAPL'], 15)

    def test_buy_shares_zero_quantity(self):
        result = self.account.buy_shares('AAPL', 0)
        self.assertFalse(result)
        self.assertNotIn('AAPL', self.account.holdings)

    def test_buy_shares_negative_quantity(self):
        result = self.account.buy_shares('AAPL', -5)
        self.assertFalse(result)
        self.assertNotIn('AAPL', self.account.holdings)

    def test_buy_shares_unknown_symbol(self):
        result = self.account.buy_shares('UNKNOWN', 10)
        self.assertFalse(result)
        self.assertNotIn('UNKNOWN', self.account.holdings)

    def test_buy_shares_insufficient_balance(self):
        result = self.account.buy_shares('AAPL', 100)
        self.assertFalse(result)
        self.assertNotIn('AAPL', self.account.holdings)
        self.assertEqual(self.account.balance, 10000.0)

    def test_buy_shares_creates_transaction(self):
        self.account.buy_shares('AAPL', 10)
        transaction = self.account.transactions[-1]
        self.assertEqual(transaction['type'], 'buy')
        self.assertEqual(transaction['symbol'], 'AAPL')
        self.assertEqual(transaction['quantity'], 10)
        self.assertEqual(transaction['price'], 150.0)
        self.assertEqual(transaction['total_cost'], 1500.0)

    def test_buy_shares_exact_balance(self):
        account = Account('exactuser')
        account.deposit(1500.0)
        result = account.buy_shares('AAPL', 10)
        self.assertTrue(result)
        self.assertEqual(account.balance, 0.0)


class TestAccountSellShares(unittest.TestCase):
    def setUp(self):
        self.account = Account('testuser')
        self.account.deposit(10000.0)
        self.account.buy_shares('AAPL', 20)

    def test_sell_shares_valid(self):
        result = self.account.sell_shares('AAPL', 10)
        self.assertTrue(result)
        self.assertEqual(self.account.holdings['AAPL'], 10)
        self.assertEqual(self.account.balance, 10000.0 - (150.0 * 20) + (150.0 * 10))

    def test_sell_all_shares(self):
        result = self.account.sell_shares('AAPL', 20)
        self.assertTrue(result)
        self.assertNotIn('AAPL', self.account.holdings)

    def test_sell_shares_zero_quantity(self):
        result = self.account.sell_shares('AAPL', 0)
        self.assertFalse(result)
        self.assertEqual(self.account.holdings['AAPL'], 20)

    def test_sell_shares_negative_quantity(self):
        result = self.account.sell_shares('AAPL', -5)
        self.assertFalse(result)
        self.assertEqual(self.account.holdings['AAPL'], 20)

    def test_sell_shares_more_than_held(self):
        result = self.account.sell_shares('AAPL', 30)
        self.assertFalse(result)
        self.assertEqual(self.account.holdings['AAPL'], 20)

    def test_sell_shares_not_owned(self):
        result = self.account.sell_shares('TSLA', 10)
        self.assertFalse(result)
        self.assertNotIn('TSLA', self.account.holdings)

    def test_sell_shares_unknown_symbol(self):
        result = self.account.sell_shares('UNKNOWN', 10)
        self.assertFalse(result)

    def test_sell_shares_creates_transaction(self):
        self.account.sell_shares('AAPL', 10)
        transaction = self.account.transactions[-1]
        self.assertEqual(transaction['type'], 'sell')
        self.assertEqual(transaction['symbol'], 'AAPL')
        self.assertEqual(transaction['quantity'], 10)
        self.assertEqual(transaction['price'], 150.0)
        self.assertEqual(transaction['total_proceeds'], 1500.0)

    def test_sell_shares_multiple_transactions(self):
        self.account.sell_shares('AAPL', 5)
        self.account.sell_shares('AAPL', 5)
        self.assertEqual(self.account.holdings['AAPL'], 10)


class TestAccountPortfolioValue(unittest.TestCase):
    def setUp(self):
        self.account = Account('testuser')
        self.account.deposit(10000.0)

    def test_portfolio_value_cash_only(self):
        value = self.account.calculate_portfolio_value()
        self.assertEqual(value, 10000.0)

    def test_portfolio_value_with_shares(self):
        self.account.buy_shares('AAPL', 10)
        value = self.account.calculate_portfolio_value()
        expected = (10000.0 - 1500.0) + (150.0 * 10)
        self.assertEqual(value, expected)

    def test_portfolio_value_multiple_holdings(self):
        self.account.buy_shares('AAPL', 10)
        self.account.buy_shares('TSLA', 5)
        value = self.account.calculate_portfolio_value()
        cash = 10000.0 - (150.0 * 10) - (250.0 * 5)
        expected = cash + (150.0 * 10) + (250.0 * 5)
        self.assertEqual(value, expected)

    def test_portfolio_value_after_sell(self):
        self.account.buy_shares('AAPL', 10)
        initial_value = self.account.calculate_portfolio_value()
        self.account.sell_shares('AAPL', 5)
        new_value = self.account.calculate_portfolio_value()
        self.assertEqual(new_value, initial_value)

    def test_portfolio_value_empty_account(self):
        account = Account('emptyuser')
        value = account.calculate_portfolio_value()
        self.assertEqual(value, 0.0)


class TestAccountProfitLoss(unittest.TestCase):
    def setUp(self):
        self.account = Account('testuser')
        self.account.deposit(10000.0)

    def test_profit_loss_no_activity(self):
        pl = self.account.calculate_profit_loss()
        self.assertEqual(pl, 0.0)

    def test_profit_loss_with_cash_only(self):
        pl = self.account.calculate_profit_loss()
        self.assertEqual(pl, 0.0)

    def test_profit_loss_positive(self):
        self.account.buy_shares('AAPL', 10)
        self.account.sell_shares('AAPL', 10)
        pl = self.account.calculate_profit_loss()
        self.assertEqual(pl, 0.0)

    def test_profit_loss_with_holdings(self):
        self.account.buy_shares('AAPL', 10)
        pl = self.account.calculate_profit_loss()
        self.assertEqual(pl, 0.0)

    def test_profit_loss_empty_account(self):
        account = Account('emptyuser')
        pl = account.calculate_profit_loss()
        self.assertEqual(pl, 0.0)


class TestAccountGetHoldings(unittest.TestCase):
    def setUp(self):
        self.account = Account('testuser')
        self.account.deposit(10000.0)

    def test_get_holdings_empty(self):
        holdings = self.account.get_holdings()
        self.assertEqual(holdings, {})

    def test_get_holdings_single_stock(self):
        self.account.buy_shares('AAPL', 10)
        holdings = self.account.get_holdings()
        self.assertEqual(holdings['AAPL'], 10)

    def test_get_holdings_multiple_stocks(self):
        self.account.buy_shares('AAPL', 10)
        self.account.buy_shares('TSLA', 5)
        holdings = self.account.get_holdings()
        self.assertEqual(holdings['AAPL'], 10)
        self.assertEqual(holdings['TSLA'], 5)

    def test_get_holdings_returns_copy(self):
        self.account.buy_shares('AAPL', 10)
        holdings = self.account.get_holdings()
        holdings['AAPL'] = 100
        self.assertEqual(self.account.holdings['AAPL'], 10)


class TestAccountTransactionHistory(unittest.TestCase):
    def setUp(self):
        self.account = Account('testuser')

    def test_get_transaction_history_empty(self):
        history = self.account.get_transaction_history()
        self.assertEqual(history, [])

    def test_get_transaction_history_single_deposit(self):
        self.account.deposit(100.0)
        history = self.account.get_transaction_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['type'], 'deposit')

    def test_get_transaction_history_multiple_transactions(self):
        self.account.deposit(1000.0)
        self.account.withdraw(100.0)
        self.account.buy_shares('AAPL', 5)