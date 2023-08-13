import logging
from io import BytesIO
from typing import BinaryIO, Tuple

from cycle_analytics.queries import get_segment_track, get_track

logger = logging.getLogger(__name__)


def get_track_download(track_id: int) -> Tuple[BinaryIO, str]:
    """Create the data for downloading the gpx file of a track

    :param track_id: id of the track to download
    :return: GPX file as BytesIO object and file name
    """
    logger.info("Serving gpx track for id %s", track_id)
    track = get_track(track_id)

    binary_data = BytesIO(track.get_xml().encode())
    file_name = f"track_{track_id}.gpx"

    return binary_data, file_name


def get_segment_download(segment_id: int):
    """Create the data for downloading the gpx file of a segment

    :param track_id: id of the segment to download
    :return: GPX file as BytesIO object and file name
    """
    logger.info("Serving gpx track for segment with id %s", segment_id)

    track, name = get_segment_track(segment_id)

    binary_data = BytesIO(track.get_xml().encode())
    file_name = f"segment_{segment_id}_{name.replace(' ', '_')}.gpx"

    return binary_data, file_name