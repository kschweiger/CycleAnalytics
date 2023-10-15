from flask import current_app
from flask_wtf import FlaskForm
from track_analyzer import FITTrack
from werkzeug.datastructures import FileStorage
from wtforms import Field


def allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in current_app.config["ALLOWED_TRACK_EXTENSIONS"]
    )


def get_track_data_from_form(form: FlaskForm, field_name: str) -> bytes:
    field: Field = getattr(form, field_name)

    if not isinstance(field.data, FileStorage):
        raise RuntimeError("Field %s is not File", field_name)

    data: FileStorage = field.data
    filename = data.filename

    if data is None or filename is None:
        raise RuntimeError("No file in form")

    if not allowed_file(filename):
        raise RuntimeError(
            "File has no valid file ending. Valid endings are %s",
            ",".join(current_app.config["ALLOWED_TRACK_EXTENSIONS"]),
        )

    if filename.endswith(".fit"):
        track = FITTrack(source=data.stream.read())
        return track.get_xml().encode()
    else:
        return data.stream.read()
