# Adjustable options for users
INPUT_MEDIA_PATH = "example.mp4"  # Edit this with actual path
OUTPUT_SRT_PATH = "output.srt"  # Edit this with actual path
MODEL_NAME = "medium.en"
DEVICE = "cpu"
BATCH_SIZE = 16
COMPUTE_TYPE = "float16"
PUNCTUATION = ",.!?;"
MIN_WORDS_LIMIT = 8

import whisperx
import re

def load_and_transcribe(input_media_path, model_name, device, batch_size, compute_type):
    model = whisperx.load_model(model_name, device, compute_type=compute_type)
    audio = whisperx.load_audio(input_media_path)
    result = model.transcribe(audio, batch_size=batch_size)
    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
    return result

def adjust_srt_timestamps(output_path, timestamp_pattern):
    """ (Optional)
    Adjusts SRT timestamps to minimize gaps in time between subtitles.
    """
    def parse_timestamp(ts):
        h, m, s_ms = ts.split(":")
        s, ms = s_ms.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    def format_timestamp(total_seconds):
        h = int(total_seconds // 3600)
        m = int((total_seconds % 3600) // 60)
        s = int(total_seconds % 60)
        ms = int(round((total_seconds - int(total_seconds)) * 1000))
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    with open(output_path, "r") as f:
        lines = f.readlines()

    # Gather the indices and parsed timestamps for lines that match the timestamp pattern
    timestamps = []  # each element is (line_index, start_time, end_time)
    for idx, line in enumerate(lines):
        match = timestamp_pattern.match(line)
        if match:
            start_str, end_str = match.groups()
            start_time = parse_timestamp(start_str)
            end_time = parse_timestamp(end_str)
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
            new_timestamp_line = f"{format_timestamp(start_time)} --> {format_timestamp(new_end)}\n"
            lines[idx] = new_timestamp_line

    with open(output_path, "w") as f:
        f.writelines(lines)

def write_srt_output(output_path, segments, punctuation, min_words_limit):
    # Process the subtitles and write to output SRT file
    def format_time(seconds):
        # Convert seconds to SRT time format: HH:MM:SS,mmm
        millisec = int((seconds - int(seconds)) * 1000)
        seconds = int(seconds)
        hrs = seconds // 3600
        mins = (seconds % 3600) // 60
        sec = seconds % 60
        return f"{hrs:02d}:{mins:02d}:{sec:02d},{millisec:03d}"

    with open(output_path, "w", encoding="utf-8") as srt_file:
        my_segment = ""
        word_cnt = 0
        start_time = None
        end_time = None
        subtitle_index = 1
        for segment in segments:
            for word_info in segment["words"]:
                if word_cnt == 0:
                    start_time = format_time(word_info["start"])
                word_text = word_info["word"].strip()
                my_segment += word_text + " "
                word_cnt += 1
                end_time = format_time(word_info["end"])
                if word_text[-1] in punctuation and word_cnt >= min_words_limit:
                    srt_file.write(f"{subtitle_index}\n")
                    srt_file.write(f"{start_time} --> {end_time}\n")
                    srt_file.write(f"{my_segment}\n\n")
                    subtitle_index += 1
                    my_segment = ""
                    word_cnt = 0
        # Last segment wouldn't have been added if it didn't end with punctuation
        if my_segment != "":
            srt_file.write(f"{subtitle_index}\n")
            srt_file.write(f"{start_time} --> {end_time}\n")
            srt_file.write(f"{my_segment}\n\n")
    print(f"Subtitles written to {output_path}")

def main():
    input_media_path = INPUT_MEDIA_PATH
    output_srt_path = OUTPUT_SRT_PATH
    punctuation = PUNCTUATION
    min_words_limit = MIN_WORDS_LIMIT
    model_name = MODEL_NAME
    device = DEVICE
    batch_size = BATCH_SIZE
    compute_type = COMPUTE_TYPE
    timestamp_pattern = re.compile(r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})")

    result = load_and_transcribe(input_media_path, model_name, device, batch_size, compute_type)
    write_srt_output(output_srt_path, result["segments"], punctuation, min_words_limit)
    adjust_srt_timestamps(output_srt_path, timestamp_pattern)

if __name__ == "__main__":
    main()

