from app.domain import hourly_wage, monthly_scheduled_hours, recognition
from app.enums import DisabilityDegree as DD
from app.enums import RecognitionResult as RR
from app.enums import SalaryType


def test_monthly_hours():
    assert monthly_scheduled_hours(40) == 173.8
    assert monthly_scheduled_hours(12) == 52.1


def test_recognition_boundaries():
    assert recognition(DD.MILD, 60, 20, False)[0] == RR.SINGLE
    assert recognition(DD.MILD, 59.9, 20, False)[0] == RR.EXCLUDED
    assert recognition(DD.SEVERE, 60, 20, False)[0] == RR.DOUBLE
    assert recognition(DD.SEVERE, 54.3, 16, False)[0] == RR.SINGLE
    assert recognition(DD.SEVERE, 54.3, 15, False)[0] == RR.EXCLUDED
    assert recognition(DD.MILD, 173.8, 10, True)[0] == RR.NEEDS_REVIEW
    assert recognition(None, 173.8, 20, False)[0] == RR.NEEDS_REVIEW


def test_hourly_wage():
    assert hourly_wage(SalaryType.MONTHLY, 2_090_000, 40) == 10000  # 209h
    assert hourly_wage(SalaryType.HOURLY, 10_500, 12) == 10500
