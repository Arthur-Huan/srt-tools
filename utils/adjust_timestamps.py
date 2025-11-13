def adjust_srt_timestamps(output_path):
    """ (Optional)
    Adjusts SRT timestamps to minimize gaps in time between subtitles.
    """
    with open(output_path, "r") as f:
        lines = f.readlines()

    # Gather the indices and parsed timestamps for lines that match the timestamp pattern
    timestamps = []  # each element is (line_index, start_time, end_time)
    for idx, line in enumerate(lines):
        match = TIMESTAMP_PATTERN.match(line)
        if match:
            start_str, end_str = match.groups()
            start_time = float(timestamp_to_secs(start_str))
            end_time = float(timestamp_to_secs(end_str))
            timestamps.append((idx, start_time, end_time))

    # Process each timestamp line comparing with the next block's start time
    for i in range(len(timestamps) - 1):
        idx, start_time, end_time = timestamps[i]
        _, next_start, _ = timestamps[i + 1]

        gap = next_start - end_time
        new_end = end_time  # default: no change

        if gap > 2.0:
            new_end = next_start - 0.2
        elif 0.1 < gap <= 2.0:
            new_end = next_start - 0.1

        # Ensure new_end doesn't fall before the start time
        if new_end > start_time:
            new_timestamp_line = f"{secs_to_timestamp(start_time)} --> {secs_to_timestamp(new_end)}\n"
            lines[idx] = new_timestamp_line

    with open(output_path, "w") as f:
        f.writelines(lines)
