"""
Smartmeter API for Vienna Smartmeter webinterface
"""

import csv
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .WienerNetze_smartmeter import Smartmeter
from .WienerNetze_smartmeter.constants import Resolution

logger = logging.getLogger(__name__)


class SmartmeterApi:
    """Smartmeter API for Vienna Smartmeter webinterface"""

    def __init__(self, username: str, password: str) -> None:
        """
        Constructor

        :param username: Smartmeter website login username
        :param password: Smartmeter website login password
        """
        self._api = Smartmeter(username, password)
        self._api.login()
        self.yesterday = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(1)

    def get_statistics(
        self, date_from: datetime, date_to: datetime = None
    ) -> dict[datetime, int]:
        """
        Get quarter hourly consumption statistics from specified period
        HINT: date_to does not work in the ViennaSmartmeter rest api

        :param date_from: Datetime of period start
        :param date_to: Datetime of period end, default: None
        :return: Dictionary with timestamps and values
        """
        daily_statistics = self._api.verbrauch(
            date_from=date_from, date_to=date_to, resolution=Resolution.QUARTER_HOUR
        )

        # restructure dataset from api
        return {
            element["timestamp"]: element["value"]
            for element in daily_statistics["values"]
            if element["value"] is not None
        }

    def get_meter_reading(self) -> int:
        """
        Get meter reading from yesterday

        :return: Meter reading value
        """
        values = self._api.meter_readings()
        return values["meterReadings"][0]["value"] if values else None

    def get_daily_consumption(self) -> int:
        """
        Get daily consumption from yesterday

        :return: Daily consumption value
        """
        values = self._api.consumptions()
        return values["consumptionYesterday"]["value"] if values else None

    def get_statistics_full_day(self, date: datetime) -> dict[datetime, int]:
        """
        Get quarter hourly consumption statistics of one full day

        :param date: Datetime of full day
        :return: Dictionary with timestamps and values
        """
        date_from = date.replace(hour=0, minute=0)
        date_to = date.replace(hour=23, minute=45)
        logger.debug(f"{date_from} - {date_to}")

        return self.get_statistics(date_from, date_to)


def calculate_daily_consumption_from_statistics(
    statistics: dict[datetime, int]
) -> float:
    """
    Get daily consumption from daily statistics

    :param statistics: Daily statistics data
    :return: Daily consumption value
    """
    return sum(element for element in statistics.values() if element is not None)


def import_csv_meter_reading(csv_file: Path) -> dict[datetime, float]:
    """
    Import meter reading csv export from smartmeter website

    :param csv_file: Exported csv file
    :return: Dictionary with timestamps and values
    """
    with open(csv_file, encoding="utf8") as f:
        data = csv.reader(f, delimiter=";")
        # skip the headers
        next(data, None)
        # reorganize parsed data and convert to W
        return {
            datetime.strptime(row[0], r"%d.%m.%Y"): float(row[1].replace(",", "."))
            * 1000
            for row in data
            if row[1]
        }, "meter_reading"


def import_csv_daily_consumption(csv_file: Path) -> dict[datetime, float]:
    """
    Import daily consumption csv export from smartmeter website

    :param csv_file: Exported csv file
    :return: Dictionary with timestamps and values
    """
    with open(csv_file, encoding="utf8") as f:
        data = csv.reader(f, delimiter=";")
        # skip the headers
        next(data, None)
        # reorganize parsed data and convert to W
        return {
            datetime.strptime(row[0], r"%d.%m.%Y"): float(row[1].replace(",", "."))
            * 1000
            for row in data
            if row[1]
        }, "daily_consumption"


def import_csv_statistics(csv_file: Path) -> dict[datetime, float]:
    """
    Import consumption statistics csv export from smartmeter website

    :param csv_file: Exported csv file
    :return: Dictionary with timestamps and values
    """
    raise NotImplementedError(
        "Vienna Smartmeter website does not export data correctly, therefeore currently depreciated"
    )
    with open(csv_file, encoding="utf8") as f:
        data = csv.reader(f, delimiter=";")
        # skip the headers
        next(data, None)
        # reorganize parsed data
        return {
            datetime.strptime(f"{row[0]} {row[2]}", r"%d.%m.%Y %H:%M:%S"): float(
                row[3].replace(",", ".")
            )
            * 1000
            for row in data
            if row[3]
        }, "statistis"


def import_csv_statistics_econtrol(csv_file: Path) -> dict[datetime, float]:
    """
    Import consumption statistics csv export from smartmeter website

    :param csv_file: Exported csv file
    :return: Dictionary with timestamps and values
    """
    raise NotImplementedError(
        "Vienna Smartmeter website does not export data correctly, therefeore currently depreciated"
    )
    with open(csv_file, encoding="utf8") as f:
        data = csv.reader(f, delimiter=";")
        # skip the headers
        next(data, None)
        # reorganize parsed data
        return {
            datetime.fromisoformat(row[0]): float(row[3].replace(",", ".")) * 1000
            for row in data
            if row[3]
        }, "statistics"


csv_name_to_import_func_mapping = {
    "ZAEHLERSTAENDE": import_csv_meter_reading,
    "TAGESWERTE": import_csv_daily_consumption,
    "VIERTELSTUNDENWERTE": import_csv_statistics,
    "VIERTELSTUNDENWERTE_ECONTROL": import_csv_statistics_econtrol,
}


def import_csv(csv_file: Path) -> dict[datetime, float]:
    """
    Import csv export from smartmeter website

    :param csv_file: Exported csv file
    :return: Dictionary with timestamps and values
    """
    match = re.search(r"(\w+)-.*", str(csv_file))
    logger.debug(f"csv import match: {match.group(1)}")
    return csv_name_to_import_func_mapping[match.group(1)](csv_file)
