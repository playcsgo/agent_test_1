import gradio as gr
from accounts import Account, get_share_price

account = None

def create_account(username):
    global account
    account = Account(username)
    return f"Account created for {username}"

def deposit_funds(amount):
    global account
    if account is None:
        return "Error: No account created yet"
    try:
        amount = float(amount)
        if account.deposit(amount):
            return f"Deposited ${amount:.2f}. Balance: ${account.balance:.2f}"
        else:
            return "Error: Invalid amount"
    except:
        return "Error: Invalid input"

def withdraw_funds(amount):
    global account
    if account is None:
        return "Error: No account created yet"
    try:
        amount = float(amount)
        if account.withdraw(amount):
            return f"Withdrew ${amount:.2f}. Balance: ${account.balance:.2f}"
        else:
            return "Error: Cannot withdraw (insufficient funds or invalid amount)"
    except:
        return "Error: Invalid input"

def buy_stock(symbol, quantity):
    global account
    if account is None:
        return "Error: No account created yet"
    try:
        quantity = int(quantity)
        if account.buy_shares(symbol.upper(), quantity):
            price = get_share_price(symbol.upper())
            return f"Bought {quantity} shares of {symbol.upper()} @ ${price:.2f}. Balance: ${account.balance:.2f}"
        else:
            return "Error: Cannot buy (insufficient funds, invalid quantity, or unknown symbol)"
    except:
        return "Error: Invalid input"

def sell_stock(symbol, quantity):
    global account
    if account is None:
        return "Error: No account created yet"
    try:
        quantity = int(quantity)
        if account.sell_shares(symbol.upper(), quantity):
            price = get_share_price(symbol.upper())
            return f"Sold {quantity} shares of {symbol.upper()} @ ${price:.2f}. Balance: ${account.balance:.2f}"
        else:
            return "Error: Cannot sell (don't have enough shares or invalid quantity)"
    except:
        return "Error: Invalid input"

def get_holdings():
    global account
    if account is None:
        return "Error: No account created yet"
    return account.report_holdings()

def get_profit_loss():
    global account
    if account is None:
        return "Error: No account created yet"
    return account.report_profit_loss()

def get_transactions():
    global account
    if account is None:
        return "Error: No account created yet"
    history = account.get_transaction_history()
    if not history:
        return "No transactions yet"
    result = "Transaction History:\n"
    for tx in history:
        result += f"{tx['timestamp']}: {tx['type'].upper()}"
        if tx['type'] == 'deposit':
            result += f" ${tx['amount']:.2f}\n"
        elif tx['type'] == 'withdrawal':
            result += f" ${tx['amount']:.2f}\n"
        elif tx['type'] == 'buy':
            result += f" {tx['quantity']} x {tx['symbol']} @ ${tx['price']:.2f}\n"
        elif tx['type'] == 'sell':
            result += f" {tx['quantity']} x {tx['symbol']} @ ${tx['price']:.2f}\n"
    return result

def get_current_balance():
    global account
    if account is None:
        return "Error: No account created yet"
    return f"Current Balance: ${account.balance:.2f}\nInitial Deposit: ${account.initial_deposit:.2f}"

with gr.Blocks(title="Trading Simulator") as demo:
    gr.Markdown("# Trading Simulation Account Manager")
    
    with gr.Row():
        username_input = gr.Textbox(label="Username", placeholder="Enter username")
        create_btn = gr.Button("Create Account")
    
    create_output = gr.Textbox(label="Status", interactive=False)
    create_btn.click(create_account, inputs=username_input, outputs=create_output)
    
    gr.Markdown("## Account Operations")
    
    with gr.Row():
        deposit_amount = gr.Number(label="Amount", value=0)
        deposit_btn = gr.Button("Deposit")
    deposit_output = gr.Textbox(label="Deposit Result", interactive=False)
    deposit_btn.click(deposit_funds, inputs=deposit_amount, outputs=deposit_output)
    
    with gr.Row():
        withdraw_amount = gr.Number(label="Amount", value=0)
        withdraw_btn = gr.Button("Withdraw")
    withdraw_output = gr.Textbox(label="Withdrawal Result", interactive=False)
    withdraw_btn.click(withdraw_funds, inputs=withdraw_amount, outputs=withdraw_output)
    
    gr.Markdown("## Trading Operations")
    
    with gr.Row():
        buy_symbol = gr.Textbox(label="Symbol", placeholder="e.g., AAPL")
        buy_quantity = gr.Number(label="Quantity", value=0, precision=0)
        buy_btn = gr.Button("Buy Shares")
    buy_output = gr.Textbox(label="Buy Result", interactive=False)
    buy_btn.click(buy_stock, inputs=[buy_symbol, buy_quantity], outputs=buy_output)
    
    with gr.Row():
        sell_symbol = gr.Textbox(label="Symbol", placeholder="e.g., AAPL")
        sell_quantity = gr.Number(label="Quantity", value=0, precision=0)
        sell_btn = gr.Button("Sell Shares")
    sell_output = gr.Textbox(label="Sell Result", interactive=False)
    sell_btn.click(sell_stock, inputs=[sell_symbol, sell_quantity], outputs=sell_output)
    
    gr.Markdown("## Reports")
    
    with gr.Row():
        balance_btn = gr.Button("Show Balance")
        holdings_btn = gr.Button("Show Holdings")
        pl_btn = gr.Button("Show P&L")
        tx_btn = gr.Button("Show Transactions")
    
    balance_output = gr.Textbox(label="Balance", interactive=False)
    holdings_output = gr.Textbox(label="Holdings", interactive=False, lines=5)
    pl_output = gr.Textbox(label="Profit/Loss", interactive=False)
    tx_output = gr.Textbox(label="Transactions", interactive=False, lines=8)
    
    balance_btn.click(get_current_balance, outputs=balance_output)
    holdings_btn.click(get_holdings, outputs=holdings_output)
    pl_btn.click(get_profit_loss, outputs=pl_output)
    tx_btn.click(get_transactions, outputs=tx_output)
    
    gr.Markdown("### Available Symbols: AAPL ($150), TSLA ($250), GOOGL ($140)")

if __name__ == "__main__":
    demo.launch()