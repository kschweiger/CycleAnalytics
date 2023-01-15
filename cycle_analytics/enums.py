from enum import Enum


class FrameMaterial(str, Enum):
    ALUMINIUM = "aluminium"
    CARBON = "carbon"
    STEEL = "steel"
    TITANIUM = "titanium"

    @property
    def name(self) -> str:
        if self == FrameMaterial.ALUMINIUM:
            return "Aluminium"
        elif self == FrameMaterial.CARBON:
            return "Carbom"
        elif self == FrameMaterial.STEEL:
            return "Steel"
        elif self == FrameMaterial.TITANIUM:
            return "Titanium"
        else:
            raise NotImplementedError


class BikeType(str, Enum):
    MTB = "mtb"
    ROAD = "road"
    GRAVEL = "gravel"

    @property
    def name(self) -> str:
        if self == BikeType.MTB:
            return "Mountain bike"
        elif self == BikeType.ROAD:
            return "Road bike"
        elif self == BikeType.GRAVEL:
            return "Gravel bike"
        else:
            raise NotImplementedError
