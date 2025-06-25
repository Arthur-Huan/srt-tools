import whisperx
import gc
import re


# Pattern to match SRT timestamp lines (e.g. "00:00:01,500 --> 00:00:04,800")
timestamp_pattern = re.compile(r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})")

audio_file = "/content/0Complex.mp4"
output_path = audio_file[:-4] + ".srt"

model = "medium.en"
device = "cpu"
batch_size = 16 # Reduce if low on GPU memory
compute_type = "int8"


# 1. Transcribe with original whisper (batched)
model = whisperx.load_model(model, device, compute_type=compute_type)

audio = whisperx.load_audio(audio_file)
result = model.transcribe(audio, batch_size=batch_size)


# 2. Align whisper output
model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

print(result["segments"]) # after alignment

# delete model if low on GPU resources
# import gc; import torch; gc.collect(); torch.cuda.empty_cache(); del model_a

"""
# 3. Assign speaker labels
diarize_model = whisperx.diarize.DiarizationPipeline(use_auth_token=YOUR_HF_TOKEN, device=device)

# add min/max number of speakers if known
diarize_segments = diarize_model(audio)
# diarize_model(audio, min_speakers=min_speakers, max_speakers=max_speakers)

result = whisperx.assign_word_speakers(diarize_segments, result)
print(diarize_segments)
print(result["segments"]) # segments are now assigned speaker IDs
"""


def adjust_srt_timestamps(output_path):
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

def format_time(seconds):
    # Convert seconds to SRT time format: HH:MM:SS,mmm
    millisec = int((seconds - int(seconds)) * 1000)
    seconds = int(seconds)
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    sec = seconds % 60
    return f"{hrs:02d}:{mins:02d}:{sec:02d},{millisec:03d}"


punctuation = ",.!?;"  # Breaking punctuation that separates lines
min_words_limit = 8  # Minimum words before allowing line break
# Process the
with open(output_path, "w", encoding="utf-8") as srt_file:
    my_segment = ""
    word_cnt = 0
    start_time = None
    end_time = None
    subtitle_index = 1
    for segment in result["segments"]:
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

adjust_srt_timestamps(output_path)

print(f"Subtitles written to {output_path}")
