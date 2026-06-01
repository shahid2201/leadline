from datetime import datetime

from pydantic import BaseModel


class CalendarAvailabilityResponse(BaseModel):
    start: str
    end: str


class CalendarBookingCreate(BaseModel):
    calendar_id: str
    summary: str
    start: datetime
    end: datetime


class CalendarBookingResult(BaseModel):
    booked: bool
