import shutil


def ffmpeg_executable():
    binary = shutil.which("ffmpeg")
    if binary:
        return binary

    try:
        import imageio_ffmpeg
    except ImportError:
        return None

    return imageio_ffmpeg.get_ffmpeg_exe()


def has_ffmpeg():
    return ffmpeg_executable() is not None
