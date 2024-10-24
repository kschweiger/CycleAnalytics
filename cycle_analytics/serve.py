import logging
from io import BytesIO
from typing import BinaryIO, Tuple

from geo_track_analyzer import ByteTrack

from .database.model import DatabaseSegment, DatabaseTrack, db

logger = logging.getLogger(__name__)


def get_track_download(track_id: int) -> Tuple[BinaryIO, str]:
    """Create the data for downloading the gpx file of a track

    :param track_id: id of the track to download
    :return: GPX file as BytesIO object and file name
    """
    logger.info("Serving gpx track for id %s", track_id)
    track = db.get_or_404(DatabaseTrack, track_id)

    binary_data = BytesIO(ByteTrack(track.content).get_xml().encode())
    file_name = f"track_{track_id}.gpx"

    return binary_data, file_name


def get_segment_download(segment_id: int) -> tuple[BytesIO, str]:
    """Create the data for downloading the gpx file of a segment

    :param track_id: id of the segment to download
    :return: GPX file as BytesIO object and file name
    """
    logger.info("Serving gpx track for segment with id %s", segment_id)

    segment = db.get_or_404(DatabaseSegment, segment_id)

    binary_data = BytesIO(ByteTrack(segment.gpx).get_xml().encode())
    file_name = f"segment_{segment_id}_{segment.name.replace(' ', '_')}.gpx"

    return binary_data, file_name
