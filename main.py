"""
Smartmeter to InfluxDb 
"""
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Sequence

from smartmeter.configuration import Configuration, ConfigurationError, load_settings
from smartmeter.influxdb_api import DataPoint, InfluxDbApi, InfluxDbApiError
from smartmeter.smartmeter_api import (
    SmartmeterApi,
    import_csv,
    calculate_daily_consumption_from_statistics,
)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Main function

    :param argv: Argument values, defaults to None
    :return: 0 on success else 1
    """
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug log")
    parser.add_argument(
        "--statistics", "-s", action="store_true", help="Get statistics data"
    )
    parser.add_argument(
        "--meter-readings", "-m", action="store_true", help="Get statistics data"
    )
    parser.add_argument(
        "--daily-consumption", "-d", action="store_true", help="Get statistics data"
    )
    parser.add_argument("--all", "-a", action="store_true", help="Get statistics data")
    parser.add_argument(
        "--date-from",
        type=datetime.fromisoformat,
        help="ISOformat: YYYY-MM-DD; if date-to is not specified, today is used as date-to",
    )
    parser.add_argument(
        "--date-to", type=datetime.fromisoformat, help="ISOformat: YYYY-MM-DD"
    )
    parser.add_argument(
        "--import-csv", "-i", type=Path, help="Impot export from smartmeter website"
    )
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--log", "-l", type=Path, help="Log file path")
    args = parser.parse_args(argv)
    log_file = args.log if args.log else "smartmeter.log"

    # setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s|%(levelname)-7s|%(name)s| %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file)],
    )
    logging.debug(args)

    # load configuration
    try:
        config: Configuration = load_settings("settings.toml")
    except (ConfigurationError, OSError) as e:
        logging.error(e)
        return 1
    logging.debug(config)

    # setup incluxdb connection
    try:
        influxdb = InfluxDbApi(
            config.influxdb.ip, config.influxdb.port, config.influxdb.database
        )
    except InfluxDbApiError as e:
        logging.error(e)
        return 1

    # argument handling
    if not args.statistics and not args.meter_readings and not args.daily_consumption:
        parser.error(
            "No mandatory argument specified: statistics, meter-readings, daily-consumption or all"
        )
    if args.all:
        args.statistics = args.meter_readings = args.daily_consumption = True

    try:
        # import csv exported from smartmeter website and write data to database
        if args.import_csv:
            data, measurement_name = import_csv(args.import_csv)
            logging.info("Write meter reading to database")
            influxdb.write(
                [
                    DataPoint(
                        measurement=getattr(
                            config.influxdb.measurements, measurement_name
                        ),
                        fields={"value": value},
                        time=timestamp,
                    ).to_dict()
                    for timestamp, value in data.items()
                ]
            )

        else:
            # setup smartmeter api connection
            smartmeter = SmartmeterApi(
                config.smartmeter.username, config.smartmeter.password
            )

            # handle date range if specified else set last timestamp in database
            if args.date_from:
                if not args.date_to:
                    logging.warning("No date_to specified, therefore using today")
                    args.date_to = datetime.today()

                date_curr = args.date_from
                date_to = args.date_to
            else:
                date_curr = influxdb.get_last_timestamp(
                    config.influxdb.measurements.statistics
                ) + timedelta(1)
                if not date_curr:
                    logging.error(
                        "No last timestamp found. Specify starting point by 'date-from' argument"
                    )
                    return 1

                date_to = datetime.today()
            logging.debug(f"Date range: {date_curr} - {date_to}")

            # execute commands
            while date_curr.date() < date_to.date():
                logging.info(f"Process date {date_curr.date()}")
                # Get and write statistics data
                if args.statistics or args.daily_consumption:
                    # Get daily statistics from smartmeter api
                    logging.info("Get daily statistics from smartmeter website")
                    statistics = smartmeter.get_statistics_full_day(date_curr)
                    logging.debug(f"{statistics=}")

                    # write data to database if received
                    if not statistics:
                        logging.warning(
                            "No date received for this date, therefore no database write"
                        )
                    else:
                        logging.info("Write daily statistics to database")
                        influxdb.write(
                            [
                                DataPoint(
                                    measurement=config.influxdb.measurements.statistics,
                                    fields={"consumption": consumption},
                                    time=timestamp,
                                ).to_dict()
                                for timestamp, consumption in statistics.items()
                            ]
                        )

                # Get and write daily consumption data
                if args.daily_consumption:
                    logging.info("Calculate daily consumption from statistics")
                    daily_consumption_calc = (
                        calculate_daily_consumption_from_statistics(statistics)
                    )
                    logging.debug(f"{daily_consumption_calc=}")

                    logging.info("Write daily consumption to database")
                    influxdb.write(
                        [
                            DataPoint(
                                measurement=config.influxdb.measurements.daily_consumption,
                                fields={"daily_consumption": daily_consumption_calc},
                                time=date_curr,
                            ).to_dict()
                        ]
                    )

                # Set to next day
                date_curr += timedelta(1)

    except InfluxDbApiError as e:
        logging.error(e)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
