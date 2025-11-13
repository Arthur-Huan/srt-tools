def timestamp_to_secs(timestamp):
    """
    :param timestamp: String in SRT time format: HH:MM:SS,mmm
    :return: Float of equivalent seconds
    """
    h, m, s_ms = timestamp.split(":")
    s, ms = s_ms.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def secs_to_timestamp(seconds: float) -> str:
    """
    :param seconds: Float representing seconds
    :return: String in SRT time format: HH:MM:SS,mmm
    """
    millisec = int(round((seconds - int(seconds)) * 1000))
    seconds = int(seconds)
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    sec = seconds % 60
    return f"{hrs:02d}:{mins:02d}:{sec:02d},{millisec:03d}"
