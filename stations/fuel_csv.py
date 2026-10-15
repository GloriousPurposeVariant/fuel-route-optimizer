import csv
from dataclasses import dataclass
from decimal import Decimal

from .constants import US_STATES

DEFAULT_CSV = "data/fuel-prices-for-be-assessment.csv"


@dataclass
class ParsedStations:
    stations: dict
    total_rows: int
    non_us_rows: int

    @property
    def duplicate_rows(self):
        return self.total_rows - self.non_us_rows - len(self.stations)


def read_us_stations(csv_path):
    """Read the CSV, keep US rows only, and keep the cheapest row per OPIS ID."""
    total_rows = non_us_rows = 0
    cheapest = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        for raw in csv.DictReader(fh):
            total_rows += 1
            row = {k.strip(): (v or "").strip() for k, v in raw.items()}
            state = row["State"].upper()
            if state not in US_STATES:
                non_us_rows += 1
                continue
            opis_id = int(row["OPIS Truckstop ID"])
            price = Decimal(row["Retail Price"])
            if opis_id not in cheapest or price < cheapest[opis_id]["price"]:
                cheapest[opis_id] = {**row, "State": state, "price": price}
    return ParsedStations(cheapest, total_rows, non_us_rows)
