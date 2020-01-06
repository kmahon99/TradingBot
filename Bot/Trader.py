from datetime import datetime, time
import json
import urllib.request
from Bot.Scraper import *

class TraderBot:
        class Position:
                def __init__(self):

                        self.num_shares = 0
                        self.aggregate_price = 0
                        self.current_price = 0
                        self.movement = 0
                        self.stop_loss = 0

                def Update(self, num_shares = 0):

                        if int(num_shares) != num_shares or (self.num_shares + num_shares) < 0:

                                print("Can't have fractional or negative shares: {}".format(num_shares))
                                return

                        self.num_shares += num_shares

                        net = float(num_shares * self.current_price)
                        self.aggregate_price = round(float(net + float(self.aggregate_price * (self.num_shares - num_shares))) / self.num_shares, 3)
                        self.stop_loss = round(self.aggregate_price - float(self.aggregate_price * 0.2), 3)

                def getOverallLossGain(self):
                        return (self.num_shares * self.current_price) - (self.num_shares * self.aggregate_price)

        def __init__(self,
                     market_open,
                     market_close,
                     api_key,
                     url_prices,
                     url_movement,
                     initial_capital,
                     max_positions,
                     save_file_path=None):

                self.initial_capital = initial_capital
                self.capital = initial_capital
                self.positions = {}
                self.max_positions = max_positions

                # Load previous state

                if save_file_path != None:
                        try:
                                file = open(save_file_path+"/state.json", "r")
                                data = json.load(file)

                                symbols = data["open_positions"].keys()

                                for symbol in symbols:
                                        # Need to ignore any positions that don't have any shares
                                        if data["open_positions"][symbol]["number_of_shares"] == 0:
                                                continue
                                        self.positions[symbol] = self.Position()
                                        self.positions[symbol].num_shares = data["open_positions"][symbol]["number_of_shares"]
                                        self.positions[symbol].aggregate_price = data["open_positions"][symbol]["aggregate_price"]
                                        self.positions[symbol].stop_loss = data["open_positions"][symbol]["stop_loss"]

                                self.initial_capital = data["initial_capital"]
                                self.capital = data["current_capital"]

                        except FileNotFoundError:
                                print("Can't find save file at location: {}".format(save_file_path+"/state.json"))
                                pass

                        except KeyError as e:
                                print("Badly formatted save file: {}".format(e))

                        except Exception as e:
                                print(e)

                self.market_open = market_open
                self.market_close = market_close
                self.api_key = api_key
                self.url_prices = url_prices
                self.url_movement = url_movement

        def timeInRange(self):

                open = list(int(unit) for unit in self.market_open.split(":"))
                close = list(int(unit) for unit in self.market_close.split(":"))
                open = time(open[0], open[1], 0)
                close = time(close[0], close[1], 0)
                current = time(datetime.now().hour, datetime.now().minute, datetime.now().second)
                midnight = time(0,0,0)

                # If the close time is past midnight, we need to check the outside of the range
                # instead of the inside

                if close < open:
                        if (current < midnight and current >= open) or (current >= midnight and current < close):
                                return True

                if current >= open and current < close:
                        return True

                return False

        def getPricesForAllSymbols(self):

                symbols = ",".join(self.positions.keys())
                response = urllib.request.urlopen(self.url_prices.format(self.api_key, symbols))

                if response.getcode() != 200:
                        print("Can't contact Alpha Vantage!")
                        return

                data = {}

                try:
                        data = json.load(response)["Stock Quotes"]
                except KeyError:
                        return

                result = {}

                try:
                        for entry in data:
                                price = float(entry['2. price'])
                                symbol = entry['1. symbol']
                                if price != 0:
                                        result[symbol] = price

                        for symbol in self.positions.keys():
                                if symbol not in result.keys() and self.positions[symbol].num_shares == 0:
                                        print("Removing {} due to lack of price info".format(symbol))
                                        self.positions = self.positions.pop(symbol)
                                elif symbol in result.keys():
                                        self.positions[symbol].current_price = result[symbol]

                except KeyError as e:
                        print("Can't find position or price: {}".format(e))
                        return

                print("\nPrices updated for {}\n".format(",".join(result.keys())))

        def Buy(self, symbol, amount):
                try:

                        if self.positions[symbol].current_price == 0:
                                return 0

                        num_shares = int(amount / self.positions[symbol].current_price)

                        if num_shares < 1 or amount > self.capital:
                                print("Not enough capital for at least one share of {}".format(symbol))
                                return 0

                        try:
                                self.positions[symbol].Update(num_shares)
                                print("Bought {} shares of {} @ ${}".format(num_shares, symbol, self.positions[symbol].current_price))

                        except KeyError:

                                print("{} isn't in the list of positions!".format(symbol))

                        self.capital-= round(num_shares * self.positions[symbol].current_price, 3)
                        return num_shares

                except KeyError:

                        print("Symbol: {} not in the list to buy from".format(symbol))
                        return 0

        def Sell(self, symbol, num_shares):
                try:
                        amount = num_shares

                        if amount > self.positions[symbol].num_shares:
                                amount = self.positions[symbol].num_shares

                        net = self.positions[symbol].getOverallLossGain()
                        self.positions[symbol].Update(-amount)
                        self.capital += round(amount * self.positions[symbol].current_price, 3)

                        if self.positions[symbol].num_shares == 0:
                                self.positions.pop(symbol)

                        print("Sold {} shares of {} @ {}, aggregate: {}".format(amount, symbol, self.positions[symbol].current_price, self.positions[symbol].aggregate_price))

                        if net <= 0:
                                print("Lost ${}".format(-net))
                        else:
                                print("Gained ${}".format(net))

                except KeyError:
                        print("{} not in available symbols to sell from".format(symbol))

        def getBestPerformers(self, amount):
                gainers = getBiggestMovers(amount, self.url_movement)

                # Update the percentage movement of all symbols

                for gainer in gainers.keys():
                        if gainer not in self.positions.keys() and len(self.positions) < self.max_positions:
                                self.positions[gainer] = self.Position()
                        else:
                                self.positions[gainer].movement = gainers[gainer]
                        self.positions[gainer].movement = gainers[gainer]
                return gainers

        def getWorstPerformers(self, amount):
                losers = getBiggestMovers(amount, self.url_movement, type="losers")

                # Update the percentage movement of all symbols

                for loser in losers.keys():
                        if loser not in self.positions.keys() and len(self.positions) < self.max_positions:
                                self.positions[loser] = self.Position()
                        else:
                                self.positions[loser].movement = losers[loser]
                        self.positions[loser].movement = losers[loser]
                return losers

        def getBiggestMovers(self):
                remaining_empty_positions = self.max_positions - len(self.positions)

                if remaining_empty_positions == 0:
                        return

                gainers = getBiggestMovers(int(remaining_empty_positions / 2), self.url_movement)
                losers = getBiggestMovers(int(remaining_empty_positions / 2), self.url_movement, type="losers")

                movers = gainers.copy()
                movers.update(losers)

                for mover in movers.keys():
                        print("Movers: {}".format(movers))
                        if mover not in self.positions.keys() and len(self.positions) < self.max_positions:
                                self.positions[mover] = self.Position()
                        else:
                                self.positions[mover].movement = movers[mover]
                        self.positions[mover].movement = movers[mover]

                return movers

        def Serialize(self, location):
                file = open(location+"/state.json", "w+")
                data = {}
                open_positions = {}
                for symbol in self.positions.keys():
                        open_positions[symbol] = {"number_of_shares" : self.positions[symbol].num_shares,
                                                  "aggregate_price" : self.positions[symbol].aggregate_price,
                                                  "stop_loss" : self.positions[symbol].stop_loss}
                data["open_positions"] = open_positions
                data["initial_capital"] = self.initial_capital
                data["current_capital"] = self.capital
                json.dump(data,file)