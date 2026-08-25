import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioEnhancer:
    """Lightweight noise reduction using the noisereduce library.

    When ``noisereduce`` is installed the first 0.5 s of the audio is treated
    as a noise profile and subtracted from the full signal.  If the library is
    missing the audio is returned unchanged so the pipeline never breaks.
    """

    def enhance(self, audio_path: Path) -> Path:
        try:
            import numpy as np
            import noisereduce as nr
            from scipy.io import wavfile

            sample_rate, data = wavfile.read(str(audio_path))

            # Convert stereo to mono if necessary
            if data.ndim > 1:
                data = data.mean(axis=1).astype(data.dtype)

            # Use the first 0.5 s (or the whole clip if shorter) as a noise profile
            noise_sample_length = min(sample_rate // 2, len(data))
            reduced = nr.reduce_noise(
                y=data.astype(float),
                sr=sample_rate,
                y_noise=data[:noise_sample_length].astype(float),
                stationary=False,
                prop_decrease=0.8,
            )
            wavfile.write(str(audio_path), sample_rate, reduced.astype(np.int16))
            logger.info("Noise reduction applied to %s", audio_path.name)
        except ImportError:
            logger.debug("noisereduce not installed – skipping noise reduction")
        except Exception as exc:
            # Never let noise reduction crash the pipeline; log and continue
            logger.warning("Noise reduction failed (%s) – using original audio", exc)
        return audio_path
