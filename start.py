import backtrader as bt
import yfinance as yf
import pandas as pd
import datetime

def get_data(coin='BTC-USD'):
    # Download all available BTC historical data from Yahoo Finance
    data = yf.download(coin)
    data.to_csv(f"{coin}.csv")  # Save to CSV if you want to reuse it


def correct_file_data(coin='BTC-USD'):
    # Load the Excel file
    file_path = f"{coin}.csv"
    df = pd.read_csv(file_path)
    # Drop the 2nd and 3rd rows
    df = df.drop([0, 1 ])
    # Define the new header 
    new_header = ['Date', 'Adj Close', 'Close', 'High', 'Low', 'Open', 'Volume'] 
    # Assign the new header to the DataFrame 
    df.columns = new_header
    # Save the updated DataFrame back to CSV
    df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']]
    df.to_csv(f'updated_{coin}.csv', index=False)


# Create a Stratey
class TestStrategy(bt.Strategy):

    params = (
        ('rsi_period', 14),  # Default RSI period
    )
    
    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))
    
    def __init__(self):

        self.dataclose = self.datas[0].close
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        self.order = None
        self.target_percentage = 0.1
        self.buyprice = None
        self.profits = 0

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, %.2f' % order.executed.price)
            elif order.issell():
                self.log('SELL EXECUTED, %.2f' % order.executed.price)

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"{order.Canceled}, {order.Margin}, {order.Rejected}")
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    
    def notify_trade(self, trade):
        if not trade.isclosed:
            return  # Wait until the trade is closed (i.e., both buy and sell are executed)

        # Log trade results
        self.log(f'TRADE CLOSED - GROSS PnL: {trade.pnl:.2f}, NET PnL: {trade.pnlcomm:.2f}')

        # Determine if the trade was a win or loss
        if trade.pnl > 0:
            self.log(f'WINNING TRADE - PROFIT: {trade.pnl:.2f}')
        else:
            self.log(f'LOSING TRADE - LOSS: {trade.pnl:.2f}')
    
    def next(self):
        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return
        
         # Buy when RSI is below 30 and we are not in the market
        if self.rsi[0] < 30 and not self.position:
            cash = self.broker.get_cash()
            amount = self.target_percentage * cash
            price = self.dataclose[0]
            size = amount / price
            # BUY, BUY, BUY!!! (with default parameters)
            if cash >= amount:
                self.order = self.buy(size=size)
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.order = self.buy(size=size)
                print(f'Buying {size:.8f} shares at {price:.2f}')

        # Sell when RSI is above 70 and we have a position
        elif self.rsi[0] > 70 and self.position:
            self.log(f'SELL CREATE, {self.data.close[0]:.2f}')
            self.order = self.sell(size=self.position.size)


coin = 'BTC-USD'

# Example usage
get_data()
correct_file_data()

datapath = f'updated_{coin}.csv'
df = pd.read_csv(datapath)
print(df.tail(10))
# Create a Data Feed
data = bt.feeds.GenericCSVData(
    dataname=datapath,
    dtformat=("%Y-%m-%d %H:%M:%S%z"),  # Include timezone in format
    # Do not pass values before this date
    #fromdate=datetime.datetime(2022, 12, 1),
    # Do not pass values before this date
    #todate=datetime.datetime(2024, 11, 6),
    datetime=0,  # Index of the date column
    open=1,      # Index of the open price column
    high=2,      # Index of the high price column
    low=3,       # Index of the low price column
    close=4,     # Index of the close price column
    volume=5,    # Index of the volume column
    openinterest=-1,  # No open interest column
    header=True       # Skip the header row
   )

cerebro = bt.Cerebro()
cerebro.addstrategy(TestStrategy)

cerebro.adddata(data)
cerebro.broker.setcash(1000.0)

print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

cerebro.run()

print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

cerebro.plot(style='candlestick', barup='green', bardown='red')