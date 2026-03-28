"""
Cyphron Simulator entrypoint.

Minimal working check:
- prints "Simulator started"
- generates and prints one dummy transaction
"""

from simulator.tx_simulator import (
    generate_fanout_fraud,
    generate_normal_tx,
    generate_structuring_fraud,
)

if __name__ == "__main__":
    print("---- NORMAL ----")
    for _ in range(3):
        print(generate_normal_tx())

    print("\n---- FANOUT FRAUD ----")
    for tx in generate_fanout_fraud():
        print(tx)

    print("\n---- STRUCTURING FRAUD ----")
    for tx in generate_structuring_fraud():
        print(tx)
