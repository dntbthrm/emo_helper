import subprocess

def convert_to_wav(input_ogg, output_wav):
    command = [
        "ffmpeg", "-y", "-i", input_ogg,
        "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000", output_wav
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"Ошибка конвертации: {result.stderr.decode()}")
