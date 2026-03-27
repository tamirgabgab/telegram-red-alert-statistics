from datetime import datetime


class CustomDateTime(datetime):
    def __str__(self):
        return self.strftime("%d/%m/%Y")


class CustomDateHour(datetime):
    def __new__(cls, hour=0, minute=0, *args, **kwargs):
        return super().__new__(cls, year=2020, month=1, day=1, hour=hour, minute=minute, *args, **kwargs)

    def __str__(self):
        return self.strftime("%H:%M")
