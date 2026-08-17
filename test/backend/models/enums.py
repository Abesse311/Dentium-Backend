from enum import Enum

class AppointmentStatus(str, Enum):
    SCHEDULED = "Scheduled"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    NO_SHOW = "No Show"

class AppointmentType(str, Enum):
    CHECKUP = "Checkup"
    CLEANING = "Cleaning"
    FILLING = "Filling"
    ROOT_CANAL = "Root Canal"
    EXTRACTION = "Extraction"
    CROWN_BRIDGE = "Crown / Bridge"
    FOLLOW_UP = "Follow-up"
    OTHER = "Other"

class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
