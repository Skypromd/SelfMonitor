"""
Model Performance Monitoring System
Real-time monitoring and alerting for ML models in production
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import json

import numpy as np  # type: ignore
import pandas as pd  # type: ignore

# Conditional imports with fallbacks
try:
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score  # type: ignore[import-untyped]
except ImportError:
    # Create fallback implementations
    def accuracy_score(*args: Any, **kwargs: Any) -> float: return 0.0
    def precision_score(*args: Any, **kwargs: Any) -> float: return 0.0
    def recall_score(*args: Any, **kwargs: Any) -> float: return 0.0
    def f1_score(*args: Any, **kwargs: Any) -> float: return 0.0
    def roc_auc_score(*args: Any, **kwargs: Any) -> float: return 0.0

try:
    from scipy.stats import ks_2samp, chi2_contingency  # type: ignore[import-untyped]
except ImportError:
    def ks_2samp(*args: Any) -> Tuple[float, float]: return (0.0, 1.0)
    def chi2_contingency(*args: Any) -> Tuple[float, float, int, Any]: return (0.0, 1.0, 1, None)

import redis.asyncio as redis

try:
    from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, push_to_gateway  # type: ignore[import-untyped]
except ImportError:
    class PrometheusMetricFallback:
        """Base fallback class for prometheus metrics"""
        def __init__(self, *args: Any, **kwargs: Any):
            self._name = args[0] if args else "unknown"
            self._documentation = args[1] if len(args) > 1 else ""
            self._labelnames = kwargs.get('labelnames', [])
            
        def labels(self, **label_values: Any) -> 'PrometheusMetricFallback':
            """Return self for chaining - allows .labels().inc() pattern"""
            return self
            
        def inc(self, amount: float = 1.0) -> None:
            """Increment metric"""
            pass
            
        def observe(self, amount: float) -> None:
            """Record observation (for Histogram)"""
            pass
            
        def set(self, value: float) -> None:
            """Set value (for Gauge)"""
            pass
    
    class Counter(PrometheusMetricFallback):
        """Fallback Counter implementation"""
        pass
    
    class Histogram(PrometheusMetricFallback):
        """Fallback Histogram implementation"""
        def time(self) -> Any:
            """Context manager for timing operations"""
            class TimerContext:
                def __enter__(self) -> None:
                    pass
                def __exit__(self, *args: Any) -> None:
                    pass
            return TimerContext()
        
    class Gauge(PrometheusMetricFallback):
        """Fallback Gauge implementation"""
        def dec(self, amount: float = 1.0) -> None:
            """Decrement gauge"""
            pass
        
    class CollectorRegistry:
        """Fallback CollectorRegistry implementation"""
        def __init__(self) -> None: 
            pass
        
        def register(self, collector: Any) -> None:
            """Register a collector"""
            pass
        
    def push_to_gateway(*args: Any, **kwargs: Any) -> None:
        """Fallback push to gateway function"""
        pass

try:
    import asyncpg  # type: ignore[import-untyped]
except ImportError:
    class MockConnection:
        async def execute(self, *args: Any, **kwargs: Any) -> Any:
            return None
    
    class MockPool:
        def acquire(self) -> 'MockContextManager':
            return MockContextManager(MockConnection())
        
    class MockContextManager:
        def __init__(self, connection: MockConnection):
            self.connection = connection
            
        async def __aenter__(self) -> MockConnection:
            return self.connection
            
        async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            pass
    
    class asyncpg:
        @staticmethod
        async def create_pool(*args: Any, **kwargs: Any) -> MockPool:
            return MockPool()

try:
    from evidently import ColumnMapping  # type: ignore[import-untyped]
    from evidently.report import Report  # type: ignore[import-untyped]
    from evidently.metric_preset import DataDriftPreset, TargetDriftPreset  # type: ignore[import-untyped]
    from evidently.test_suite import TestSuite  # type: ignore[import-untyped]
    from evidently.tests import TestShareOfMissingValues, TestMeanInNSigmas  # type: ignore[import-untyped]
except ImportError:
    class ColumnMapping: 
        def __init__(self, *args: Any, **kwargs: Any): pass
    class Report: 
        def __init__(self, *args: Any, **kwargs: Any): pass
        def run(self, *args: Any, **kwargs: Any) -> None: pass
    class DataDriftPreset: 
        def __init__(self, *args: Any, **kwargs: Any): pass
    class TargetDriftPreset: 
        def __init__(self, *args: Any, **kwargs: Any): pass
    class TestSuite: 
        def __init__(self, *args: Any, **kwargs: Any): pass
        def run(self, *args: Any, **kwargs: Any) -> None: pass
    class TestShareOfMissingValues: 
        def __init__(self, *args: Any, **kwargs: Any): pass
    class TestMeanInNSigmas: 
        def __init__(self, *args: Any, **kwargs: Any): pass

try:
    from alibi_detect import TabularDrift  # type: ignore[import-untyped]
except ImportError:
    class TabularDrift: 
        def __init__(self, *args: Any, **kwargs: Any): pass
        def predict(self, *args: Any, **kwargs: Any) -> Any: return {'data': {'is_drift': 0, 'distance': 0.0}}

try:
    import whylogs as why  # type: ignore[import-untyped]
    from whylogs.api.writer.s3 import S3Writer  # type: ignore[import-untyped]
except ImportError:
    class MockWhyLogs:
        @staticmethod
        def log(*args: Any, **kwargs: Any) -> Any: return None
    why = MockWhyLogs()
    
    class S3Writer: 
        def __init__(self, *args: Any, **kwargs: Any): pass

from .config import MLOpsConfig
from .notifications import SlackNotifier

logger = logging.getLogger(__name__)

@dataclass
class ModelPrediction:
    """Single model prediction with metadata"""
    model_name: str
    model_version: str
    prediction_id: str
    features: Dict[str, Any]
    prediction: Any
    confidence: float
    timestamp: datetime
    user_id: Optional[str] = None
    actual_outcome: Optional[Any] = None
    feedback_received: bool = False

@dataclass
class PerformanceMetric:
    """Performance metric with metadata"""
    model_name: str
    metric_name: str
    metric_value: float
    timestamp: datetime
    period: str  # "hour", "day", "week"
    sample_size: int

@dataclass
class DriftAlert:
    """Data/target drift alert"""
    model_name: str
    drift_type: str  # "data", "target", "prediction"
    severity: str  # "low", "medium", "high", "critical"
    drift_score: float
    threshold: float
    affected_features: List[str]
    timestamp: datetime
    mitigation_suggestions: List[str]

class MetricsCollector:
    """
    Collects and stores model performance metrics
    """
    
    def __init__(self, config: MLOpsConfig):
        self.config = config
        self.redis_client: Optional[redis.Redis[str]] = None
        self.db_pool: Optional[Any] = None
        self.registry: CollectorRegistry = CollectorRegistry()
        
        # Prometheus metrics
        self.prediction_counter: Counter = Counter(
            'model_predictions_total',
            'Total number of model predictions',
            ['model_name', 'model_version', 'status'],
            registry=self.registry
        )
        
        self.prediction_latency: Histogram = Histogram(
            'model_prediction_latency_seconds',
            'Model prediction latency',
            ['model_name', 'model_version'],
            registry=self.registry
        )
        
        self.accuracy_gauge: Gauge = Gauge(
            'model_accuracy',
            'Current model accuracy',
            ['model_name', 'model_version', 'period'],
            registry=self.registry
        )
        
        self.drift_score_gauge: Gauge = Gauge(
            'model_drift_score',
            'Model drift score',
            ['model_name', 'drift_type'],
            registry=self.registry
        )
        
    async def initialize(self):
        """Initialize connections"""
        # Redis connection
        self.redis_client = redis.from_url(  # type: ignore[misc]
            self.config.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        
        # PostgreSQL connection pool
        self.db_pool = await asyncpg.create_pool(  # type: ignore[misc]
            self.config.database_url,
            min_size=5,
            max_size=20
        )
        
        # Create tables if they don't exist
        await self._create_tables()
        
    async def _create_tables(self):
        """Create monitoring tables"""
        if not self.db_pool:
            logger.warning("Database pool not initialized")
            return
            
        async with self.db_pool.acquire() as conn:  # type: ignore[misc]
            await conn.execute("""  # type: ignore[misc]
                CREATE TABLE IF NOT EXISTS model_predictions (
                    id SERIAL PRIMARY KEY,
                    model_name VARCHAR(255) NOT NULL,
                    model_version VARCHAR(50) NOT NULL,
                    prediction_id UUID NOT NULL UNIQUE,
                    features JSONB NOT NULL,
                    prediction JSONB NOT NULL,
                    confidence FLOAT NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                    user_id VARCHAR(255),
                    actual_outcome JSONB,
                    feedback_received BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_predictions_model_timestamp 
                ON model_predictions(model_name, timestamp);
                
                CREATE INDEX IF NOT EXISTS idx_predictions_user_id
                ON model_predictions(user_id);
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id SERIAL PRIMARY KEY,
                    model_name VARCHAR(255) NOT NULL,
                    metric_name VARCHAR(100) NOT NULL,
                    metric_value FLOAT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    period VARCHAR(20) NOT NULL,
                    sample_size INTEGER NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_metrics_model_metric_timestamp
                ON performance_metrics(model_name, metric_name, timestamp);
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS drift_alerts (
                    id SERIAL PRIMARY KEY,
                    model_name VARCHAR(255) NOT NULL,
                    drift_type VARCHAR(50) NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    drift_score FLOAT NOT NULL,
                    threshold FLOAT NOT NULL,
                    affected_features JSONB,
                    timestamp TIMESTAMP NOT NULL,
                    mitigation_suggestions JSONB,
                    acknowledged BOOLEAN DEFAULT FALSE,
                    resolved BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_alerts_model_timestamp
                ON drift_alerts(model_name, timestamp);
            """)
            
    async def record_prediction(self, prediction: ModelPrediction):
        """Record a model prediction"""
        if not self.db_pool:
            logger.warning("Database pool not initialized")
            return
            
        try:
            # Store in database
            async with self.db_pool.acquire() as conn:  # type: ignore[misc]
                await conn.execute("""
                    INSERT INTO model_predictions (
                        model_name, model_version, prediction_id, features, 
                        prediction, confidence, timestamp, user_id
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, 
                prediction.model_name,
                prediction.model_version,
                prediction.prediction_id,
                json.dumps(prediction.features),
                json.dumps(prediction.prediction),
                prediction.confidence,
                prediction.timestamp,
                prediction.user_id
                )
                
            # Cache in Redis for real-time access (if available)
            if self.redis_client:
                try:
                    # Store prediction data - hset returns int, not awaitable
                    self.redis_client.hset(  # type: ignore[misc]
                        f"predictions:{prediction.model_name}",
                        prediction.prediction_id,
                        json.dumps({
                            "prediction": prediction.prediction,
                            "confidence": prediction.confidence,
                            "timestamp": prediction.timestamp.isoformat(),
                            "features": prediction.features
                        })
                    )
                    
                    # Set expiry for Redis cache (24 hours)
                    await self.redis_client.expire(
                        f"predictions:{prediction.model_name}",
                        86400
                    )
                except Exception as redis_error:
                    logger.warning(f"Redis operation failed: {redis_error}")
            
            # Update Prometheus metrics
            try:
                counter_with_labels = self.prediction_counter.labels(
                    model_name=prediction.model_name,
                    model_version=prediction.model_version,
                    status="success"
                )
                counter_with_labels.inc()
            except AttributeError:
                # Fallback for prometheus client fallbacks
                self.prediction_counter.inc()
            
            logger.debug(f"Recorded prediction for {prediction.model_name}: {prediction.prediction_id}")
            
        except Exception as e:
            logger.error(f"Failed to record prediction: {str(e)}")
            try:
                error_counter_with_labels = self.prediction_counter.labels(
                    model_name=prediction.model_name,
                    model_version=prediction.model_version,
                    status="error"
                )
                error_counter_with_labels.inc()
            except (AttributeError, Exception):
                # Fallback for prometheus client fallbacks
                self.prediction_counter.inc()
            raise
            
    async def update_actual_outcome(
        self,
        prediction_id: str,
        actual_outcome: Any,
        model_name: str
    ):
        """Update prediction with actual outcome for performance calculation"""
        if not self.db_pool:
            logger.warning("Database pool not initialized")
            return
            
        try:
            async with self.db_pool.acquire() as conn:  # type: ignore[misc]
                await conn.execute("""
                    UPDATE model_predictions 
                    SET actual_outcome = $1, feedback_received = TRUE
                    WHERE prediction_id = $2 AND model_name = $3
                """,
                json.dumps(actual_outcome),
                prediction_id,
                model_name
                )
                
            logger.debug(f"Updated actual outcome for prediction {prediction_id}")
            
        except Exception as e:
            logger.error(f"Failed to update actual outcome: {str(e)}")
            raise
            
    async def calculate_performance_metrics(
        self,
        model_name: str,
        period: str = "day",
        days_back: int = 1
    ) -> Dict[str, float]:
        """Calculate performance metrics for a given period"""
        if not self.db_pool:
            logger.warning("Database pool not initialized")
            return {}
            
        try:
            end_time = datetime.now(timezone.utc)
            if period == "hour":
                start_time = end_time - timedelta(hours=days_back)
            elif period == "day":
                start_time = end_time - timedelta(days=days_back)
            elif period == "week":
                start_time = end_time - timedelta(weeks=days_back)
            else:
                raise ValueError(f"Invalid period: {period}")
                
            # Get predictions with actual outcomes
            async with self.db_pool.acquire() as conn:  # type: ignore[misc]
                rows = await conn.fetch("""
                    SELECT prediction, actual_outcome, confidence
                    FROM model_predictions
                    WHERE model_name = $1 
                    AND timestamp >= $2 
                    AND timestamp <= $3
                    AND feedback_received = TRUE
                """, model_name, start_time, end_time)
                
            if not rows:
                return {}
                
            # Extract predictions and actuals
            predictions = []
            actuals = []
            confidences = []
            
            predictions: List[Any] = []
            actuals: List[Any] = []
            confidences: List[float] = []
            
            for row in rows:
                pred = json.loads(row['prediction'])
                actual = json.loads(row['actual_outcome'])
                confidence_val: float = float(row['confidence'])
                confidences.append(confidence_val)
                
                # Handle different prediction formats
                if isinstance(pred, dict):
                    pred_value: Any = pred.get('class', pred.get('value', 0))  # type: ignore[misc]
                    predictions.append(pred_value)
                else:
                    predictions.append(pred)
                    
                if isinstance(actual, dict):
                    actual_value: Any = actual.get('class', actual.get('value', 0))  # type: ignore[misc]
                    actuals.append(actual_value)
                else:
                    actuals.append(actual)
                    
            predictions_array = np.array(predictions)  # type: ignore[call-arg]
            actuals_array = np.array(actuals)  # type: ignore[call-arg]
            confidences_array = np.array(confidences)  # type: ignore[call-arg]
            
            # Calculate metrics
            metrics: Dict[str, float] = {}
            
            # Classification metrics
            if len(np.unique(actuals_array)) <= 10:  # Assume classification  # type: ignore[call-arg]
                metrics['accuracy'] = accuracy_score(actuals_array, predictions_array)  # type: ignore[call-arg]
                metrics['precision'] = precision_score(actuals_array, predictions_array, average='weighted', zero_division=0)  # type: ignore[call-arg]
                metrics['recall'] = recall_score(actuals_array, predictions_array, average='weighted', zero_division=0)  # type: ignore[call-arg]
                metrics['f1_score'] = f1_score(actuals_array, predictions_array, average='weighted', zero_division=0)  # type: ignore[call-arg]
                
                # AUC for binary classification
                if len(np.unique(actuals_array)) == 2:  # type: ignore[call-arg]
                    try:
                        metrics['auc'] = roc_auc_score(actuals_array, confidences_array)  # type: ignore[call-arg]
                    except Exception:
                        pass
            else:
                # Regression metrics  
                mse_val = np.mean((actuals_array - predictions_array) ** 2)  # type: ignore[operator]
                metrics['mse'] = float(mse_val)  # type: ignore[call-arg]
                metrics['rmse'] = float(np.sqrt(mse_val))  # type: ignore[call-arg]
                metrics['mae'] = float(np.mean(np.abs(actuals_array - predictions_array)))  # type: ignore[call-arg,operator]
                
                # R-squared
                ss_res = float(np.sum((actuals_array - predictions_array) ** 2))  # type: ignore[call-arg,operator]
                ss_tot = float(np.sum((actuals_array - np.mean(actuals_array)) ** 2))  # type: ignore[call-arg,operator]
                metrics['r2'] = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                
            # General metrics
            metrics['sample_size'] = len(predictions)
            metrics['avg_confidence'] = float(np.mean(confidences_array))  # type: ignore[call-arg]
            metrics['prediction_variance'] = float(np.var(predictions_array))  # type: ignore[call-arg]
            
            # Store calculated metrics
            for metric_name, metric_value in metrics.items():
                await self._store_performance_metric(
                    model_name, metric_name, metric_value, period, len(predictions)
                )
                
                # Update Prometheus gauge
                if metric_name in ['accuracy', 'auc', 'r2', 'avg_confidence']:
                    self.accuracy_gauge.labels(
                        model_name=model_name,
                        model_version="current",
                        period=period
                    ).set(metric_value)
                    
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate performance metrics: {str(e)}")
            return {}
            
    async def _store_performance_metric(
        self,
        model_name: str,
        metric_name: str,
        metric_value: float,
        period: str,
        sample_size: int
    ):
        """Store performance metric in database"""
        if not self.db_pool:
            logger.warning("Database pool not initialized")
            return
            
        async with self.db_pool.acquire() as conn:  # type: ignore[misc]
            await conn.execute("""
                INSERT INTO performance_metrics (
                    model_name, metric_name, metric_value, timestamp, period, sample_size
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """,
            model_name,
            metric_name,
            metric_value,
            datetime.now(timezone.utc),
            period,
            sample_size
            )
            
    async def get_model_metrics(
        self,
        model_name: str,
        days: int = 30
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get historical model metrics"""
        if not self.db_pool:
            logger.warning("Database pool not initialized")
            return {}
            
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)
            
            async with self.db_pool.acquire() as conn:  # type: ignore[misc]
                rows = await conn.fetch("""
                    SELECT metric_name, metric_value, timestamp, period, sample_size
                    FROM performance_metrics
                    WHERE model_name = $1 
                    AND timestamp >= $2
                    ORDER BY timestamp DESC
                """, model_name, start_time)
                
            metrics: Dict[str, List[Dict[str, Any]]] = {}
            for row in rows:
                metric_name = row['metric_name']
                if metric_name not in metrics:
                    metrics[metric_name] = []
                    
                metrics[metric_name].append({  # type: ignore[misc]
                    'value': row['metric_value'],
                    'timestamp': row['timestamp'].isoformat(),
                    'period': row['period'],
                    'sample_size': row['sample_size']
                })
                
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get model metrics: {str(e)}")
            return {}


class DriftDetector:
    """
    Detect data and target drift in model inputs/outputs
    """
    
    def __init__(self, config: MLOpsConfig):
        self.config = config
        self.detectors: Dict[str, Any] = {}  # Store drift detectors per model
        self.reference_data: Dict[str, pd.DataFrame] = {}  # Store reference datasets
        self.notifier = SlackNotifier(config.slack_webhook_url)
        
    async def initialize_detector(
        self,
        model_name: str,
        reference_data: pd.DataFrame,
        categorical_features: Optional[List[str]] = None
    ):
        """Initialize drift detector for a model"""
        try:
            # Create Alibi-Detect tabular drift detector
            detector: Any = TabularDrift(
                x_ref=reference_data.values,  # type: ignore[attr-defined]
                p_val=self.config.drift_threshold,
                categories_per_feature=categorical_features
            )
            
            self.detectors[model_name] = detector
            self.reference_data[model_name] = reference_data
            
            logger.info(f"Initialized drift detector for {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize drift detector for {model_name}: {str(e)}")
            raise
            
    async def detect_data_drift(
        self,
        model_name: str,
        current_data: pd.DataFrame,
        feature_names: Optional[List[str]] = None
    ) -> Optional[DriftAlert]:
        """Detect data drift in model inputs"""
        try:
            if model_name not in self.detectors:
                logger.warning(f"No drift detector found for {model_name}")
                return None
                
            detector: Any = self.detectors[model_name]
            
            # Run drift detection
            drift_result: Dict[str, Any] = detector.predict(current_data.values)  # type: ignore[attr-defined,misc]
            
            if drift_result['data']['is_drift']:
                # Calculate drift score
                drift_score: float = float(drift_result['data']['distance'])  # type: ignore[misc]
                
                # Identify affected features
                affected_features: List[str] = []
                if 'feature_score' in drift_result['data']:
                    feature_scores: Any = drift_result['data']['feature_score']  # type: ignore[misc]
                    if feature_names:
                        affected_features = [
                            feature_names[i] for i in range(len(feature_scores))  # type: ignore[misc]
                            if feature_scores[i] > self.config.drift_threshold  # type: ignore[misc]
                        ]
                        
                # Determine severity
                severity: str = self._calculate_drift_severity(drift_score)
                
                # Generate mitigation suggestions
                suggestions: List[str] = self._generate_drift_suggestions(
                    model_name, affected_features, severity
                )
                
                # Create alert
                alert = DriftAlert(
                    model_name=model_name,
                    drift_type="data",
                    severity=severity,
                    drift_score=drift_score,
                    threshold=self.config.drift_threshold,
                    affected_features=affected_features,
                    timestamp=datetime.now(timezone.utc),
                    mitigation_suggestions=suggestions
                )
                
                # Send notification
                await self._send_drift_notification(alert)
                
                return alert
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to detect data drift for {model_name}: {str(e)}")
            return None
            
    async def detect_target_drift(
        self,
        model_name: str,
        reference_targets: np.ndarray,  # type: ignore[name-defined]
        current_targets: np.ndarray  # type: ignore[name-defined]
    ) -> Optional[DriftAlert]:
        """Detect target drift in model outputs"""
        try:
            # Use KS test for continuous targets, Chi-square for categorical
            if len(np.unique(current_targets)) > 10:  # Continuous  # type: ignore[misc,call-arg]
                _, p_value = ks_2samp(reference_targets, current_targets)  # type: ignore[misc]
                drift_detected = p_value < self.config.drift_threshold
                drift_score = 1 - p_value
            else:  # Categorical
                # Create contingency table
                ref_counts = pd.Series(reference_targets).value_counts()  # type: ignore[misc]
                curr_counts = pd.Series(current_targets).value_counts()  # type: ignore[misc]
                
                # Align categories
                all_categories = set(ref_counts.index) | set(curr_counts.index)
                ref_aligned = [ref_counts.get(cat, 0) for cat in all_categories]
                curr_aligned = [curr_counts.get(cat, 0) for cat in all_categories]
                
                _, p_value, _, _ = chi2_contingency([ref_aligned, curr_aligned])  # type: ignore[misc]
                drift_detected = p_value < self.config.drift_threshold
                drift_score = 1 - p_value
                
            if drift_detected:
                severity = self._calculate_drift_severity(drift_score)
                
                alert = DriftAlert(
                    model_name=model_name,
                    drift_type="target",
                    severity=severity,
                    drift_score=drift_score,
                    threshold=self.config.drift_threshold,
                    affected_features=[],
                    timestamp=datetime.now(timezone.utc),
                    mitigation_suggestions=self._generate_drift_suggestions(
                        model_name, [], severity, drift_type="target"
                    )
                )
                
                await self._send_drift_notification(alert)
                return alert
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to detect target drift for {model_name}: {str(e)}")
            return None
            
    def _calculate_drift_severity(self, drift_score: float) -> str:
        """Calculate drift severity based on score"""
        if drift_score >= 0.8:
            return "critical"
        elif drift_score >= 0.6:
            return "high"  
        elif drift_score >= 0.4:
            return "medium"
        else:
            return "low"
            
    def _generate_drift_suggestions(
        self,
        model_name: str,
        affected_features: List[str],
        severity: str,
        drift_type: str = "data"
    ) -> List[str]:
        """Generate mitigation suggestions for drift"""
        suggestions: List[str] = []
        
        if drift_type == "data":
            suggestions.append("Investigate data quality issues in affected features")  # type: ignore[misc]
            suggestions.append("Review feature engineering pipeline")  # type: ignore[misc]
            if affected_features:
                suggestions.append(f"Focus on features: {', '.join(affected_features[:3])}")  # type: ignore[misc]
                
            if severity in ["high", "critical"]:
                suggestions.append("Consider retraining the model with recent data")  # type: ignore[misc]
                suggestions.append("Implement real-time feature monitoring")  # type: ignore[misc]
                suggestions.append("Review data collection process")  # type: ignore[misc]
        else:  # target drift
            suggestions.append("Analyze changes in target variable distribution")  # type: ignore[misc]
            suggestions.append("Review business context for changes")
            
            if severity in ["high", "critical"]:
                suggestions.append("Retrain model with recent target distribution")
                suggestions.append("Consider concept drift adaptation techniques")
                
        return suggestions
        
    async def _send_drift_notification(self, alert: DriftAlert):
        """Send drift alert notification"""
        try:
            message = f"""
🚨 **Drift Detection Alert** 🚨

**Model**: {alert.model_name}
**Type**: {alert.drift_type.title()} Drift
**Severity**: {alert.severity.upper()}
**Score**: {alert.drift_score:.3f} (threshold: {alert.threshold:.3f})

**Affected Features**: {', '.join(alert.affected_features) if alert.affected_features else 'N/A'}

**Mitigation Suggestions**:
{chr(10).join(f"• {suggestion}" for suggestion in alert.mitigation_suggestions)}

**Timestamp**: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
            """
            
            await self.notifier.send_message(message, channel="ml-alerts")
            
        except Exception as e:
            logger.error(f"Failed to send drift notification: {str(e)}")


class ModelMonitoringOrchestrator:
    """
    Orchestrates all monitoring activities
    """
    
    def __init__(self, config: MLOpsConfig):
        self.config = config
        self.metrics_collector = MetricsCollector(config)
        self.drift_detector = DriftDetector(config)
        self.monitoring_tasks: Dict[str, asyncio.Task[None]] = {}
        
    async def initialize(self):
        """Initialize monitoring system"""
        await self.metrics_collector.initialize()
        logger.info("Model monitoring system initialized")
        
    async def start_monitoring(self, model_name: str):
        """Start monitoring for a specific model"""
        if model_name in self.monitoring_tasks:
            logger.warning(f"Monitoring already active for {model_name}")
            return
            
        # Start periodic monitoring tasks
        task = asyncio.create_task(self._monitoring_loop(model_name))
        self.monitoring_tasks[model_name] = task
        
        logger.info(f"Started monitoring for {model_name}")
        
    async def stop_monitoring(self, model_name: str):
        """Stop monitoring for a specific model"""
        if model_name in self.monitoring_tasks:
            self.monitoring_tasks[model_name].cancel()
            del self.monitoring_tasks[model_name]
            logger.info(f"Stopped monitoring for {model_name}")
            
    async def _monitoring_loop(self, model_name: str):
        """Main monitoring loop for a model"""
        while True:
            try:
                # Calculate performance metrics every hour
                metrics = await self.metrics_collector.calculate_performance_metrics(
                    model_name, period="hour"
                )
                
                if metrics:
                    logger.info(f"Updated metrics for {model_name}: {metrics}")
                    
                # Check for performance degradation
                await self._check_performance_degradation(model_name, metrics)
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                logger.info(f"Monitoring cancelled for {model_name}")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop for {model_name}: {str(e)}")
                await asyncio.sleep(300)  # Sleep 5 minutes on error
                
    async def _check_performance_degradation(
        self,
        model_name: str,
        current_metrics: Dict[str, float]
    ):
        """Check for performance degradation and alert if necessary"""
        # Implementation depends on specific metrics and thresholds
        # This is a simplified version
        for metric_name, value in current_metrics.items():
            if metric_name in ['accuracy', 'auc', 'r2'] and value < 0.8:
                await self._send_performance_alert(model_name, metric_name, value)
                
    async def _send_performance_alert(
        self,
        model_name: str,
        metric_name: str, 
        value: float
    ):
        """Send performance degradation alert"""
        # Implementation would send alerts via Slack/email
        logger.warning(f"Performance degradation detected: {model_name} {metric_name}: {value}")