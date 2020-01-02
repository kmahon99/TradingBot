import schedule
import os
from Settings import *
from Bot import Trader

# This strategy buys the most volatile stocks just after market open
# then sells on any margin of movement upwards in 1 minute time frames

class Strategy:
        def __init__(self):

                self.bot = Trader.TraderBot(MARKET_OPEN,
                        MARKET_CLOSE,
                        API_KEY,
                        URL_PRICES,
                        URL_MOVEMENT,
                        1000,
                        4,
                        os.path.dirname(os.path.realpath(__file__)))

                self.schedule()

        def performOpeningTrades(self, num_symbols_per_category):

                if not self.bot.timeInRange():
                        return

                print("\n====== Performing opening trades ======\n")

                movers = self.bot.getBiggestMovers()

                self.bot.getPricesForAllSymbols()

                # Get the amount we can spend on each symbol

                percent = float(1 / len(movers))

                for stock in movers.keys():
                        print("Capital before buy: {}".format(str(self.bot.capital)))
                        self.bot.Buy(stock, self.bot.initial_capital * percent)
                        print("Capital after buy: {}".format(str(self.bot.capital)))

                print("Remaining capital: {}".format(self.bot.capital))

                # Check if the money left over can buy anything extra

                print("\n====== Buying extra ======\n")

                while True:
                        canBuy = False
                        for symbol in movers.keys():
                                if self.bot.capital >= self.bot.positions[symbol].current_price:
                                        self.bot.Buy(symbol, self.bot.positions[symbol].current_price)
                                        canBuy = True
                        if canBuy == False:
                                break

                print("\nPosition summary:\n")

                for symbol in self.bot.positions.keys():
                        print("{}: {} shares".format(symbol, str(self.bot.positions[symbol].num_shares)))

                print("\n====== Finished initial buying period ======\n")

        def findSellingOpportunities(self):

                if not self.bot.timeInRange():
                        return

                print("\n====== Looking for potential sales ======\n")

                self.bot.getPricesForAllSymbols()
                for symbol in self.bot.positions.keys():
                        net = self.bot.positions[symbol].getOverallLossGain()
                        if net >= 1:
                                self.bot.Sell(symbol, self.bot.positions[symbol].num_shares)

                print("\n====== Finished sales round ======\n")

                print("\nOpen positions:\n")

                for symbol in self.bot.positions.keys():
                        if self.bot.positions[symbol].num_shares != 0:
                                print("{} : {} shares".format(symbol, self.bot.positions[symbol].num_shares))

                print("\nCurrent available capital: ${}".format(self.bot.capital))

                self.bot.Serialize(os.path.dirname(os.path.realpath(__file__)))

        def schedule(self):

                print("\n====== Scheduling strategy actions ======\n")

                schedule.every().day.at(MARKET_OPEN).do(self.performOpeningTrades, 5)
                schedule.every().minute.do(self.findSellingOpportunities)

                print("\n====== Done ======\n")
