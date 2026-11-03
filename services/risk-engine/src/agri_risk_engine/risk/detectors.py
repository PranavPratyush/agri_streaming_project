"""Detector candidate implementations: Rolling Z-Score, EWMA, and Isolation Forest.

Provides modular statistical and machine learning anomaly detectors for environmental time series.
"""

from collections import deque
from dataclasses import dataclass, field
import math
import time
from typing import Any

try:
    from sklearn.ensemble import IsolationForest
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


@dataclass
class AnomalyDetectionResult:
    """Standardized detection result across statistical and ML detectors."""
    algorithm_name: str
    is_anomaly: bool
    anomaly_score: float
    threshold: float
    latency_microseconds: float
    explainability: str
    metadata: dict[str, Any] = field(default_factory=dict)


class RollingZScoreDetector:
    """Rolling Z-Score anomaly detector.
    
    Computes rolling mean and standard deviation over a sliding window W.
    Z = (X_t - mu) / max(eps, sigma).
    """

    def __init__(self, window_size: int = 24, z_threshold: float = 2.5) -> None:
        self.window_size = window_size
        self.z_threshold = z_threshold
        self.history: deque[float] = deque(maxlen=window_size)

    def evaluate(self, value: float) -> AnomalyDetectionResult:
        start_ns = time.perf_counter_ns()
        self.history.append(value)

        if len(self.history) < max(5, self.window_size // 4):
            latency = (time.perf_counter_ns() - start_ns) / 1000.0
            return AnomalyDetectionResult(
                algorithm_name="RollingZScore",
                is_anomaly=False,
                anomaly_score=0.0,
                threshold=self.z_threshold,
                latency_microseconds=latency,
                explainability="Insufficient samples to compute rolling Z-score.",
                metadata={"sample_count": len(self.history)},
            )

        n = len(self.history)
        mean_val = sum(self.history) / n
        variance = sum((x - mean_val) ** 2 for x in self.history) / max(1, n - 1)
        std_val = math.sqrt(variance)

        if std_val < 1e-4:
            # Low noise floor: no deviation
            z_score = 0.0
        else:
            z_score = (value - mean_val) / std_val

        is_anomaly = abs(z_score) > self.z_threshold
        latency = (time.perf_counter_ns() - start_ns) / 1000.0

        return AnomalyDetectionResult(
            algorithm_name="RollingZScore",
            is_anomaly=is_anomaly,
            anomaly_score=round(abs(z_score), 2),
            threshold=self.z_threshold,
            latency_microseconds=latency,
            explainability=f"Reading is {abs(z_score):.2f} standard deviations from rolling {self.window_size}-period mean ({mean_val:.2f}).",
            metadata={"mean": round(mean_val, 2), "std": round(std_val, 2), "z_score": round(z_score, 2)},
        )


class EWMADetector:
    """Exponentially Weighted Moving Average (EWMA) anomaly detector.
    
    S_t = alpha * X_t + (1 - alpha) * S_{t-1}.
    Tracks persistent trend shifts while smoothing high-frequency noise.
    """

    def __init__(self, alpha: float = 0.2, l_sigma: float = 2.5) -> None:
        self.alpha = alpha
        self.l_sigma = l_sigma
        self.s_t: float | None = None
        self.var_t: float = 0.0
        self.sample_count: int = 0

    def evaluate(self, value: float) -> AnomalyDetectionResult:
        start_ns = time.perf_counter_ns()
        self.sample_count += 1

        if self.s_t is None:
            self.s_t = value
            self.var_t = 0.1
            latency = (time.perf_counter_ns() - start_ns) / 1000.0
            return AnomalyDetectionResult(
                algorithm_name="EWMA",
                is_anomaly=False,
                anomaly_score=0.0,
                threshold=self.l_sigma,
                latency_microseconds=latency,
                explainability="Initialized EWMA baseline.",
            )

        prev_s = self.s_t
        sigma_ewma = math.sqrt(max(1e-4, self.var_t))

        # Evaluate current observation against prior EWMA baseline
        delta = abs(value - prev_s)
        score = delta / sigma_ewma
        is_anomaly = score > self.l_sigma

        # Update running variance and mean for subsequent steps
        self.s_t = self.alpha * value + (1.0 - self.alpha) * prev_s
        self.var_t = (1.0 - self.alpha) * (self.var_t + self.alpha * ((value - prev_s) ** 2))

        latency = (time.perf_counter_ns() - start_ns) / 1000.0

        return AnomalyDetectionResult(
            algorithm_name="EWMA",
            is_anomaly=is_anomaly,
            anomaly_score=round(score, 2),
            threshold=self.l_sigma,
            latency_microseconds=latency,
            explainability=f"Absolute deviation of {delta:.2f} is {score:.2f}x EWMA sigma ({sigma_ewma:.2f}).",
            metadata={"ewma_mean": round(self.s_t, 2), "ewma_sigma": round(sigma_ewma, 2)},
        )


class IsolationForestDetector:
    """Multi-variate tree-based anomaly detector using Isolation Forest.
    
    Identifies non-linear outliers across [temp, rh, vpd, soil_moisture].
    Note: Requires offline fitting; evaluated as comparative offline baseline.
    """

    def __init__(self, contamination: float = 0.05, n_estimators: int = 50) -> None:
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.model: Any = None
        self.is_fitted: bool = False

    def fit(self, training_data: list[list[float]]) -> None:
        """Fit model on multi-variate training vectors."""
        if not HAS_SKLEARN:
            return
        if len(training_data) < 10:
            return
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=42,
        )
        self.model.fit(training_data)
        self.is_fitted = True

    def evaluate(self, feature_vector: list[float]) -> AnomalyDetectionResult:
        start_ns = time.perf_counter_ns()
        if not HAS_SKLEARN or not self.is_fitted or self.model is None:
            latency = (time.perf_counter_ns() - start_ns) / 1000.0
            return AnomalyDetectionResult(
                algorithm_name="IsolationForest",
                is_anomaly=False,
                anomaly_score=0.0,
                threshold=0.0,
                latency_microseconds=latency,
                explainability="Isolation Forest not fitted or scikit-learn unavailable.",
            )

        # score_samples returns opposite of anomaly score (lower is more anomalous)
        decision_score = float(self.model.decision_function([feature_vector])[0])
        pred = int(self.model.predict([feature_vector])[0])  # -1 for anomaly, 1 for inlier
        is_anomaly = (pred == -1)
        normalized_score = round(max(0.0, -decision_score), 3)

        latency = (time.perf_counter_ns() - start_ns) / 1000.0
        return AnomalyDetectionResult(
            algorithm_name="IsolationForest",
            is_anomaly=is_anomaly,
            anomaly_score=normalized_score,
            threshold=0.0,
            latency_microseconds=latency,
            explainability=f"Tree isolation depth decision score is {decision_score:.3f} (anomaly: {is_anomaly}).",
            metadata={"decision_score": decision_score},
        )
