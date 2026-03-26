#!/usr/bin/env python3
"""
Cancel-then-close loop. Cancels all orders before each round
to prevent order stacking from partial fills.

IMPORTANT: Shut down ARGUS before running this script.
"""

import asyncio
import logging
from ib_async import IB, MarketOrder

logging.getLogger("ib_async").setLevel(logging.CRITICAL)


async def cleanup():
    ib = IB()
    await ib.connectAsync("127.0.0.1", 4002, clientId=2)
    print(f"Connected. Account: {ib.managedAccounts()}\n")

    # Initial global cancel to clear ARGUS orphans
    print("Cancelling all open orders...")
    ib.reqGlobalCancel()
    await asyncio.sleep(30)
    print("Done.\n")

    round_num = 0
    max_rounds = 80

    while round_num < max_rounds:
        round_num += 1

        # Cancel any orders from previous round that haven't filled
        ib.reqGlobalCancel()
        await asyncio.sleep(5)

        # Fresh position snapshot
        await ib.reqPositionsAsync()
        positions = ib.positions()
        non_flat = [p for p in positions if p.position != 0]

        if not non_flat:
            print(f"\n✓ Account fully flat!")
            break

        total_shares = sum(abs(p.position) for p in non_flat)
        details = ", ".join(f"{p.contract.symbol}:{int(p.position)}" for p in non_flat)
        print(f"Round {round_num:>2}: {total_shares:,.0f} shares — {details}")

        # Submit ONE order per position, then wait for it to work
        for p in non_flat:
            contract = p.contract
            contract.exchange = "SMART"
            if p.position < 0:
                ib.placeOrder(contract, MarketOrder("BUY", abs(p.position)))
            else:
                ib.placeOrder(contract, MarketOrder("SELL", abs(p.position)))

        # Give this round time to fill before cancelling and retrying
        await asyncio.sleep(20)

    # Final
    await ib.reqPositionsAsync()
    final = [p for p in ib.positions() if p.position != 0]
    if final:
        print(f"\n{len(final)} positions still open:")
        for p in final:
            print(f"  {p.contract.symbol}: {p.position:,.0f}")
    else:
        print("\nAll clear. Submit the paper account reset now.")

    ib.disconnect()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(cleanup())