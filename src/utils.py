from datetime import datetime, timedelta


def get_end_time_from_load_plan(start_time: datetime, load_plan: list[list[int]]) -> datetime:
    return start_time + timedelta(minutes=sum([step[0] + step[1] + step[2] for step in load_plan]))