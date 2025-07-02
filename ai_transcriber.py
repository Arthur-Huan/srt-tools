# Adjustable options for users
INPUT_MEDIA_PATH = "example.mp4"  # Edit this with actual path
OUTPUT_SRT_PATH = "output.srt"  # Edit this with actual path
SEGMENTS_FILE_PATH = None  # Optional, set here to skip the AI transcription step

MODEL_NAME = "medium.en"
DEVICE = "cpu"
BATCH_SIZE = 16
COMPUTE_TYPE = "int8"
PUNCTUATION = ",.!?;"  # Breaking punctuation for sentence breaks
MIN_WORDS_LIMIT = 8  # Minimum number of words per SRT segment
MAX_WORDS_LIMIT = 79  # Maximum number of words per SRT segment

import whisperx
import re
import ast


TIMESTAMP_PATTERN = re.compile(r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})")


def load_and_transcribe(input_media_path, model_name, device, batch_size, compute_type):
    model = whisperx.load_model(model_name, device, compute_type=compute_type)
    audio = whisperx.load_audio(input_media_path)
    result = model.transcribe(audio, batch_size=batch_size)
    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
    return result

def write_srt_output(output_path, segments, punctuation, min_words_limit):
    # Process the subtitles and write to output SRT file
    with open(output_path, "w", encoding="utf-8") as srt_file:
        my_segment = ""
        word_cnt = 0
        start_time = None
        end_time = None
        subtitle_index = 1
        for segment in segments:
            for word_info in segment["words"]:
                if word_cnt == 0:
                    try:
                        start_time = float(word_info["start"])
                    except KeyError:
                        if start_time is None:
                            start_time = 0.0
                        else:
                            # Use the previous end_time as the new start_time
                            start_time = float(end_time) if end_time is not None else 0.0
                word_text = word_info["word"].strip()
                my_segment += word_text + " "
                word_cnt += 1
                try:
                    end_time = float(word_info["end"])
                except KeyError:
                    end_time = start_time
                if word_text[-1] in punctuation and word_cnt >= min_words_limit:
                    # Break if punctuation reached and minimum words reached
                    srt_file.write(f"{subtitle_index}\n")
                    srt_file.write(f"{secs_to_timestamp(start_time or 0.0)} --> {secs_to_timestamp(end_time or 0.0)}\n")
                    srt_file.write(f"{my_segment}\n\n")
                    subtitle_index += 1
                    my_segment = ""
                    word_cnt = 0
                if word_cnt >= MAX_WORDS_LIMIT:
                    # Force break if maximum words reached
                    srt_file.write(f"{subtitle_index}\n")
                    srt_file.write(f"{secs_to_timestamp(start_time or 0.0)} --> {secs_to_timestamp(end_time or 0.0)}\n")
                    srt_file.write(f"{my_segment}\n\n")
                    subtitle_index += 1
                    my_segment = ""
                    word_cnt = 0
        # Last segment wouldn't have been added if it didn't end with punctuation
        if my_segment != "":
            srt_file.write(f"{subtitle_index}\n")
            srt_file.write(f"{secs_to_timestamp(start_time or 0.0)} --> {secs_to_timestamp(end_time or 0.0)}\n")
            srt_file.write(f"{my_segment}\n\n")
    print(f"Subtitles written to {output_path}")

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

def main():
    input_media_path = INPUT_MEDIA_PATH
    output_srt_path = OUTPUT_SRT_PATH
    segments_file_path = SEGMENTS_FILE_PATH
    punctuation = PUNCTUATION
    min_words_limit = MIN_WORDS_LIMIT
    model_name = MODEL_NAME
    device = DEVICE
    batch_size = BATCH_SIZE
    compute_type = COMPUTE_TYPE
    # If segments_file_path is provided, read segments from it and skip transcription
    if segments_file_path:
        with open(segments_file_path, "r", encoding="utf-8") as f:
            line = f.readline().strip()
            if line:
                # Remove all ', 'score': ...)' patterns (non-greedy, up to next ) )
                line_clean = re.sub(r", 'score': [^)]*\)", "", line)
                segments = ast.literal_eval(line_clean)
            else:
                segments = []
    else:
        results = load_and_transcribe(input_media_path, model_name, device, batch_size, compute_type)
        segments = results["segments"]
    write_srt_output(output_srt_path, segments, punctuation, min_words_limit)
    adjust_srt_timestamps(output_srt_path)

if __name__ == "__main__":
    main()
