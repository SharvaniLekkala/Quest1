def format_timestamp(seconds: float) -> str:
    milliseconds = round((seconds % 1) * 1000)
    whole = int(seconds)
    hours, remainder = divmod(whole, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"
