"""
Configuration of smartmeter package
"""

# tomllib supported from v3.12 on, therefore some
# not so elegant workaround to also support v3.10
# as this is the current version on Raspbian
try:
    import tomllib as toml

    TOML_OPEN_MODE = "rb"
except ImportError:
    import toml

    TOML_OPEN_MODE = "r"

    toml.TOMLDecodeError = toml.TomlDecodeError
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(Exception):
    """Configuration error"""


@dataclass
class SmartmeterConfiguration:
    """Smartmeter top level configuration"""

    username: str
    password: str


@dataclass
class MeasurementsConfiguration:
    """InfluxDb measurement configuration"""

    statistics: str
    daily_consumption: str
    meter_reading: str


@dataclass
class InfluxDbConfiguration:
    """InfluxDb top level configuration"""

    ip: str
    port: str
    database: str
    measurements: MeasurementsConfiguration


@dataclass
class Configuration:
    """Top level configuation class"""

    smartmeter: SmartmeterConfiguration
    influxdb: InfluxDbConfiguration


def load_settings(_file: Path) -> Configuration:
    """
    Load settings from toml file

    :param _file: Toml file
    :raises ConfigurationError: Missing key in toml file
    :raises ConfigurationError: Toml decode error
    :return: Configuration object
    """
    with open(_file, TOML_OPEN_MODE) as f:
        try:
            settings = toml.load(f)
            config = Configuration(
                smartmeter=SmartmeterConfiguration(
                    username=settings["smartmeter"]["username"],
                    password=settings["smartmeter"]["password"],
                ),
                influxdb=InfluxDbConfiguration(
                    ip=settings["influxdb"]["ip"],
                    port=settings["influxdb"]["port"],
                    database=settings["influxdb"]["database"],
                    measurements=MeasurementsConfiguration(
                        statistics=settings["influxdb"]["measurements"]["statistics"],
                        daily_consumption=settings["influxdb"]["measurements"][
                            "daily_consumption"
                        ],
                        meter_reading=settings["influxdb"]["measurements"][
                            "meter_reading"
                        ],
                    ),
                ),
            )
        except KeyError as e:
            raise ConfigurationError(
                f"Missing key {e} in settings file '{_file}'"
            ) from e
        except toml.TOMLDecodeError as e:
            raise ConfigurationError(f"{e} in toml format file '{_file}'") from e
    return config
