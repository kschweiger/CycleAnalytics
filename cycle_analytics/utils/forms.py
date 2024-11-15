import logging

from flask import current_app, flash
from flask_wtf import FlaskForm
from geo_track_analyzer import ByteTrack, FITTrack, Track
from werkzeug.datastructures import FileStorage
from wtforms import Field

logger = logging.getLogger(__name__)


def allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in current_app.config["ALLOWED_TRACK_EXTENSIONS"]
    )


def get_track_from_wtf_form(form: FlaskForm, field_name: str) -> Track:
    field: Field = getattr(form, field_name)

    if not isinstance(field.data, FileStorage):
        raise RuntimeError("Field %s is not File", field_name)

    return get_track_from_file_storage(field.data)


def get_track_from_file_storage(data: FileStorage) -> Track:
    filename = data.filename

    if data is None or filename is None:
        raise RuntimeError("No file in form")

    if not allowed_file(filename):
        raise RuntimeError(
            "File has no valid file ending. Valid endings are %s"
            % ",".join(current_app.config["ALLOWED_TRACK_EXTENSIONS"]),
        )

    if filename.endswith(".fit"):
        return FITTrack(source=data.stream.read())
    else:
        return ByteTrack(data.stream.read())


def flash_form_error(form: FlaskForm) -> None:
    if not form.errors:
        return
    flash(
        "\n".join(
            ["<ul>"]
            + [
                f"<li>{field} - {','.join(error)} - Got **{form[field].data}**</li>"  # type: ignore
                for field, error in form.errors.items()
            ]
            + ["</ul>"]
        ),
        "alert-danger",
    )
    logger.error("Form errors:")
    for field, error in form.errors.items():
        logger.error("  %s : %s", field, error)
