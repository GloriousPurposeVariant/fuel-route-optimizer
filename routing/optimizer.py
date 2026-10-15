from dataclasses import dataclass

from .exceptions import FuelGap

EPSILON = 1e-6


@dataclass(frozen=True)
class FuelStop:
    station_id: int
    mile_marker: float
    price: float
    gallons: float
    cost: float


@dataclass(frozen=True)
class FuelPlan:
    stops: list
    total_gallons: float
    total_cost: float


def plan_fuel_stops(stations, total_miles, tank_range_miles, miles_per_gallon):
    """
    Cheapest refuelling plan along a fixed route (the greedy "gas station problem").

    `stations` must be sorted by mile_marker. The tank starts empty; the first fill-up is at the
    first station and also covers the miles from the origin to it; the truck arrives empty.

    At each station:
      1. If a cheaper station is within range, buy only enough to reach the nearest one.
      2. Else, if the destination is within range, buy only enough to finish.
      3. Else, fill the tank and drive to the cheapest station within range.
    """
    if total_miles <= EPSILON:
        return FuelPlan(stops=[], total_gallons=0.0, total_cost=0.0)
    if not stations:
        raise FuelGap(_gap_message(0.0, total_miles, tank_range_miles))
    if stations[0].mile_marker > tank_range_miles:
        raise FuelGap(_gap_message(0.0, stations[0].mile_marker, tank_range_miles))

    positions = [station.mile_marker for station in stations]
    positions[0] = 0.0

    purchases = []
    fuel = 0.0
    i = 0
    while True:
        here, price = positions[i], stations[i].price
        reach = here + tank_range_miles

        j = i + 1
        cheaper = None
        while j < len(stations) and positions[j] <= reach + EPSILON:
            if stations[j].price < price:
                cheaper = j
                break
            j += 1

        if cheaper is not None:
            next_index, leg = cheaper, positions[cheaper] - here
        elif total_miles <= reach + EPSILON:
            next_index, leg = None, total_miles - here
        else:
            if j == i + 1:
                gap_end = positions[j] if j < len(stations) else total_miles
                raise FuelGap(_gap_message(stations[i].mile_marker, gap_end, tank_range_miles))
            next_index = min(range(i + 1, j), key=lambda k: (stations[k].price, -positions[k]))
            purchases.append((stations[i], tank_range_miles - fuel))
            fuel = tank_range_miles - (positions[next_index] - here)
            i = next_index
            continue

        bought = max(0.0, leg - fuel)
        purchases.append((stations[i], bought))
        fuel += bought - leg
        if next_index is None:
            break
        i = next_index

    return _build_plan(purchases, miles_per_gallon)


def _build_plan(purchases, miles_per_gallon):
    stops = []
    for station, miles in purchases:
        if miles <= EPSILON:
            continue
        gallons = miles / miles_per_gallon
        stops.append(
            FuelStop(
                station_id=station.station_id,
                mile_marker=station.mile_marker,
                price=station.price,
                gallons=round(gallons, 3),
                cost=round(gallons * station.price, 2),
            )
        )
    total_gallons = sum(miles for _, miles in purchases) / miles_per_gallon
    return FuelPlan(
        stops=stops,
        total_gallons=round(total_gallons, 3),
        total_cost=round(sum(stop.cost for stop in stops), 2),
    )


def _gap_message(start_mile, end_mile, tank_range_miles):
    return (
        f"No fuel station within {tank_range_miles:.0f} miles between mile {start_mile:.0f} "
        f"and mile {end_mile:.0f} of the route."
    )
