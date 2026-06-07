"""Repair Outcome Predictor — predict probability of repair success."""

from __future__ import annotations

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from fixeragent.config import get_settings
from fixeragent.models import DiagnosticPayload, RepairTier, SafetyAssessment

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except Exception:
    XGBOOST_AVAILABLE = False
    logger.warning("xgboost not available; outcome predictor will use heuristic fallback")


class OutcomePredictor:
    """Predict repair success probability using XGBoost or heuristic fallback."""

    MODEL_PATH = "./data/models/outcome_predictor.json"
    FEATURES = [
        "tier",
        "fault_type_encoded",
        "device_category_encoded",
        "has_error_code",
        "has_led_pattern",
        "model_confidence",
        "fault_confidence",
        "user_skill_beginner",
        "user_skill_intermediate",
        "user_skill_advanced",
    ]

    def __init__(self) -> None:
        self.model: Any = None
        self.encoders: dict[str, dict[str, int]] = {
            "fault_type": {},
            "device_category": {},
        }
        self._load_model()

    def _load_model(self) -> None:
        if not XGBOOST_AVAILABLE:
            return
        path = Path(self.MODEL_PATH)
        if path.exists():
            try:
                self.model = xgb.Booster()
                self.model.load_model(str(path))
                enc_path = path.with_suffix(".encoders.pkl")
                if enc_path.exists():
                    with open(enc_path, "rb") as f:
                        self.encoders = pickle.load(f)
                logger.info("Outcome predictor model loaded")
            except Exception as e:
                logger.warning(f"Model load failed: {e}")

    def predict(
        self,
        diagnosis: DiagnosticPayload,
        safety: SafetyAssessment,
        user_skill_level: str = "beginner",
    ) -> dict[str, Any]:
        """Return success probability and contributing factors."""
        features = self._extract_features(diagnosis, safety, user_skill_level)

        if self.model and XGBOOST_AVAILABLE:
            try:
                import numpy as np
                vec = np.array([features[f] for f in self.FEATURES]).reshape(1, -1)
                dmat = xgb.DMatrix(vec, feature_names=self.FEATURES)
                prob = float(self.model.predict(dmat)[0])
                return {
                    "success_probability": round(prob, 4),
                    "model_used": "xgboost",
                    "features": features,
                }
            except Exception as e:
                logger.warning(f"XGBoost prediction failed: {e}; falling back to heuristic")

        return self._heuristic_predict(features)

    def _extract_features(
        self,
        diagnosis: DiagnosticPayload,
        safety: SafetyAssessment,
        user_skill_level: str,
    ) -> dict[str, float]:
        ft_map = self.encoders.get("fault_type", {})
        dc_map = self.encoders.get("device_category", {})
        ft_code = ft_map.get(diagnosis.fault_type.value, len(ft_map))
        dc_code = dc_map.get(diagnosis.device_info.device_category, len(dc_map))

        return {
            "tier": float(safety.tier.value),
            "fault_type_encoded": float(ft_code),
            "device_category_encoded": float(dc_code),
            "has_error_code": 1.0 if diagnosis.error_indicators.display_code else 0.0,
            "has_led_pattern": 1.0 if diagnosis.error_indicators.led_pattern else 0.0,
            "model_confidence": diagnosis.device_info.model_confidence,
            "fault_confidence": diagnosis.fault_confidence,
            "user_skill_beginner": 1.0 if user_skill_level == "beginner" else 0.0,
            "user_skill_intermediate": 1.0 if user_skill_level == "intermediate" else 0.0,
            "user_skill_advanced": 1.0 if user_skill_level == "advanced" else 0.0,
        }

    def _heuristic_predict(self, features: dict[str, float]) -> dict[str, Any]:
        """Rule-based fallback when model is unavailable."""
        tier = features["tier"]
        mc = features["model_confidence"]
        fc = features["fault_confidence"]
        has_code = features["has_error_code"]
        skill = features["user_skill_advanced"] * 0.15 + features["user_skill_intermediate"] * 0.05

        # Base probability logic aligned with tier difficulty
        base = {1: 0.85, 2: 0.70, 3: 0.50, 4: 0.0}.get(int(tier), 0.5)
        prob = base + (mc * 0.10) + (fc * 0.10) + (has_code * 0.05) + skill
        prob = max(0.0, min(1.0, prob))
        return {
            "success_probability": round(prob, 4),
            "model_used": "heuristic_fallback",
            "features": features,
        }

    def train(self, outcomes: list[dict[str, Any]]) -> None:
        """Train XGBoost classifier on historical outcomes."""
        if not XGBOOST_AVAILABLE:
            logger.error("xgboost not available; cannot train")
            return
        import numpy as np
        from sklearn.model_selection import train_test_split

        X, y = self._build_training_matrix(outcomes)
        if len(X) < 50:
            logger.warning(f"Insufficient data for training: {len(X)} samples")
            return

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=self.FEATURES)
        dtest = xgb.DMatrix(X_test, label=y_test, feature_names=self.FEATURES)

        params = {
            "objective": "binary:logistic",
            "eval_metric": "auc",
            "max_depth": 4,
            "eta": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
        }
        self.model = xgb.train(params, dtrain, num_boost_round=100, evals=[(dtest, "test")], early_stopping_rounds=10)

        model_dir = Path(self.MODEL_PATH).parent
        model_dir.mkdir(parents=True, exist_ok=True)
        self.model.save_model(self.MODEL_PATH)
        with open(model_dir / "outcome_predictor.encoders.pkl", "wb") as f:
            pickle.dump(self.encoders, f)
        logger.info("Outcome predictor model trained and saved")

    def _build_training_matrix(self, outcomes: list[dict[str, Any]]) -> tuple[Any, Any]:
        """Convert outcome logs to feature matrix and labels."""
        import numpy as np
        X: list[list[float]] = []
        y: list[int] = []
        for o in outcomes:
            diag = o.get("diagnosis", {})
            safety = o.get("safety", {})
            skill = o.get("user_skill_level", "beginner")
            # Build a minimal DiagnosticPayload-like dict
            dp = DiagnosticPayload(
                device_info={
                    "device_category": diag.get("device_category", "unknown"),
                    "brand": diag.get("brand"),
                    "model_candidates": diag.get("model_candidates", []),
                    "model_confidence": diag.get("model_confidence", 0.0),
                    "model_number_ocr": None,
                },
                error_indicators={
                    "led_pattern": diag.get("led_pattern"),
                    "display_code": diag.get("display_code"),
                    "physical_damage": [],
                    "audible_symptoms": [],
                    "user_description": diag.get("user_description", ""),
                },
                visible_components=[],
                fault_type=diag.get("fault_type", "unknown"),
                fault_confidence=diag.get("fault_confidence", 0.0),
            )
            sa = SafetyAssessment(
                tier=RepairTier(safety.get("tier", 1)),
                tier_label="",
                requires_unplug=True,
            )
            feats = self._extract_features(dp, sa, skill)
            X.append([feats[f] for f in self.FEATURES])
            y.append(1 if o.get("outcome") in ("fixed", "partial") else 0)
        return np.array(X), np.array(y)