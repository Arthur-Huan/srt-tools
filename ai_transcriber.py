import whisperx
import re
import ast
import json

from utils.time_conversion import secs_to_timestamp
from utils.path_check import solve_path


# Adjustable options for users

INPUT_MEDIA_PATH = "/home/arthur/source.mp4"  # Edit this with actual path
OUTPUT_SRT_PATH = "output/output.srt"  # Edit this with actual path
SEGMENTS_OUTPUT_PATH = "output/segments.txt"
SEGMENTS_FILE_PATH = "output/segments.txt"  # Optional, set here to skip the AI transcription step

MODEL_NAME = "medium"
DEVICE = "cpu"
BATCH_SIZE = 16
COMPUTE_TYPE = "int8"
PUNCTUATION = ",.!?;，。！？；…"  # Breaking punctuation for sentence breaks
MIN_WORDS_LIMIT = 8  # Minimum number of words per SRT segment
MAX_WORDS_LIMIT = 32  # Maximum number of words per SRT segment


TIMESTAMP_PATTERN = re.compile(r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})")


def load_and_transcribe(input_media_path, model_name, device, batch_size, compute_type):
    model = whisperx.load_model(model_name, device, compute_type=compute_type)
    audio = whisperx.load_audio(input_media_path)
    result = model.transcribe(audio, batch_size=batch_size)
    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
    return result


def write_srt_output(output_path, segments, punctuation, min_words_limit):
    # Log the raw output
    print(segments)
    with open(SEGMENTS_OUTPUT_PATH, "w") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)
    # Process the subtitles and write to output SRT file
    with open(output_path, "w", encoding="utf-8") as srt_file:
        my_segment = ""
        word_cnt = 0
        start_time = 0.0
        end_time = 0.0
        subtitle_index = 1
        for segment in segments:
            for word_info in segment["words"]:
                if word_cnt == 0:
                    try:
                        start_time = float(word_info["start"])
                    except KeyError:
                          # Use the previous end_time as the new start_time
                          start_time = end_time
                word_text = word_info["word"].strip()
                my_segment += word_text + " "
                word_cnt += 1
                try:
                    end_time = float(word_info["end"])
                except KeyError:
                    # Whisper might fail to determine end time (and start time)
                    # Effectively give this word no time, relying on its context
                    # If next word has time, then this word's end time will be overwritten anyway
                    # If this is the end of the line, then the correct end time
                    # will be identified from the next line when `adjust_srt_timestamps` is run
                    pass
                if word_text[-1] in punctuation and word_cnt >= min_words_limit:
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


def write_plain_srt_output(output_path, segments):
    with open(output_path, "w", encoding="utf-8") as srt_file:
        for idx, segment in enumerate(segments, start=1):
            start_time = float(segment["start"])
            end_time = float(segment["end"])
            text = segment["text"].strip()
            srt_file.write(f"{idx}\n")
            srt_file.write(f"{secs_to_timestamp(start_time)} --> {secs_to_timestamp(end_time)}\n")
            srt_file.write(f"{text}\n\n")
    print(f"Plain subtitles written to {output_path}")


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

    for path in (output_srt_path):
        solve_path(path)

    # If segments_file_path is provided, read segments from it and skip transcription
    if segments_file_path:
        with open(segments_file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                # Remove all ", 'score': ...)" patterns (non-greedy, up to next ')')
                content_clean = re.sub(r", 'score': [^)]*\)", ")", content)
                try:
                    segments = ast.literal_eval(content_clean)
                except Exception as e:
                    print(f"Error parsing segments file: {e}")
                    segments = []
            else:
                segments = []
    else:
        results = load_and_transcribe(input_media_path, model_name, device, batch_size, compute_type)
        segments = results["segments"]
    write_srt_output(output_srt_path, segments, punctuation, min_words_limit)


if __name__ == "__main__":
    main()
