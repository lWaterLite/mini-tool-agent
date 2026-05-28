from dataclasses import dataclass


@dataclass(frozen=True)
class CalculatorSettings:
    max_power_exponent: int = 8
