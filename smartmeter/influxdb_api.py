"""
InfluxDB API
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import requests
from influxdb import InfluxDBClient
from influxdb.client import InfluxDBClientError
from influxdb.resultset import ResultSet


class InfluxDbApiError(Exception):
    """Top level exception"""


@dataclass
class DataPoint:
    """InfluxDb datapoint representation"""

    measurement: str
    fields: dict[str, str]
    time: datetime
    tags: Optional[dict[str, str]] = None

    def to_dict(self) -> dict:
        """
        Convert to dictionary

        :return: Dictionary representation of class
        """
        return {
            "measurement": self.measurement,
            "fields": self.fields,
            "tags": self.tags,
            "time": self.time,
        }


class InfluxDbApi:
    """
    InfluxDb API
    """

    def __init__(self, ip: str, port: str, database_name: str) -> None:
        """
        Constructor

        :param ip: Server ip address
        :param port: Server port
        :param database_name: Database name
        :raises InfluxDbApiError: InfluxDb client error or ConnectTimeout
        """
        self._ip = ip
        self._database_name = database_name
        try:
            self._client = InfluxDBClient(host=ip, port=port)
            # print(self._client.get_list_database())
            self._client.create_database(self._database_name)
            self._client.switch_database(self._database_name)
        except (InfluxDBClientError, requests.exceptions.ConnectTimeout) as e:
            raise InfluxDbApiError(e) from e

    def write(self, data: list[DataPoint]) -> None:
        """
        Write data to InfluxDb database

        :param data: List of datapoints
        :raises InfluxDbApiError: Write error
        """
        try:
            if not self._client.write_points(data, time_precision="s"):
                raise InfluxDbApiError("Influxdb write not successful")
        except InfluxDBClientError as e:
            raise InfluxDbApiError(e) from e

    def get_last_timestamp(self, measurement: str) -> datetime:
        """
        Get last timestamp of measurement

        :param measurement: Measurement name of database
        :return: Last timestamp
        """
        result: ResultSet = self.query(
            f"SELECT * FROM {measurement} ORDER BY time DESC LIMIT 1"
        )

        return (
            datetime.strptime(
                result.raw["series"][0]["values"][0][0], r"%Y-%m-%dT%H:%M:%SZ"
            )
            if result
            else None
        )

    def query(self, query: str) -> Any:
        """
        Generic query

        :param query: Query
        :return: Query result
        """
        return self._client.query(query)
