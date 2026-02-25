import pandas as pd
import numpy as np
from scipy.signal import find_peaks, detrend

def load_ecg_and_compute_bpm(filepath, fs=250):
    try:
        df = pd.read_csv(filepath)
        if "ECG" in df.columns:
            raw_signal = pd.to_numeric(df["ECG"], errors='coerce').fillna(0).values
        else:
            raw_signal = pd.to_numeric(df.iloc[:, 0], errors='coerce').fillna(0).values

        if len(raw_signal) < fs:
            return [], [], 0

        t = np.arange(len(raw_signal)) / fs
        ecg_clean = detrend(raw_signal)
        # Umbral adaptativo robusto
        height_threshold = np.mean(ecg_clean) + 1.0 * np.std(ecg_clean)
        peaks, _ = find_peaks(ecg_clean, distance=fs/2.5, height=height_threshold)

        if len(peaks) > 1:
            rr_intervals = np.diff(peaks) / fs
            avg_rr = np.mean(rr_intervals)
            bpm = 60 / avg_rr if avg_rr > 0 else 0
        else:
            bpm = 0

        return t, ecg_clean, bpm
    except Exception as e:
        # En caso de error devolvemos vacío pero no crash
        return [], [], 0
