import schedule, time as t
from Strategies.MarketOpenStrategy import Strategy as MOS

# ============ Market Open Strategy ============

strategy = MOS.Strategy()

while True:

        schedule.run_pending()

        t.sleep(1)