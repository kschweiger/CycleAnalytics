import logging
from typing import Type

from flask import current_app
from flask_sqlalchemy import SQLAlchemy

from .model import (
    CategoryModel,
    Difficulty,
    EventType,
    Material,
    SegmentType,
    Severity,
    TerrainType,
    TypeSpecification,
)

logger = logging.getLogger(__name__)


def _sync_categorical_values(
    database: SQLAlchemy, values: list[str], category_model_type: Type[CategoryModel]
) -> None:
    existing_elements = [c.text for c in category_model_type.query.all()]

    for value in values:
        if value in existing_elements:
            continue

        logger.info("Creating %s in %s", value, category_model_type.__name__)
        database.session.add(category_model_type(text=value))
        database.session.commit()


def sync_categorical_values(database: SQLAlchemy) -> None:
    values_to_sync: dict[str, list[str]] = current_app.config.categorized_values
    _sync_categorical_values(database, values_to_sync["terrain_types"], TerrainType)
    _sync_categorical_values(database, values_to_sync["event_types"], EventType)
    _sync_categorical_values(database, values_to_sync["segment_types"], SegmentType)
    _sync_categorical_values(database, values_to_sync["difficulties"], Difficulty)
    _sync_categorical_values(database, values_to_sync["severities"], Severity)
    _sync_categorical_values(database, values_to_sync["materials"], Material)
    _sync_categorical_values(
        database, values_to_sync["type_secification"], TypeSpecification
    )
