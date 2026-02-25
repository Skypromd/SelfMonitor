"""
Automated Training Pipeline
Handles automated model training, validation, and registration 
"""

import asyncio
import logging
import sys
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline

import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient

import xgboost as xgb
from scipy.stats import chi2_contingency

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.config import MLOpsConfig, FRAUD_DETECTION_CONFIG, RECOMMENDATION_CONFIG, CATEGORIZATION_CONFIG
from src.utils.monitoring import MetricsCollector
from src.utils.notifications import NotificationManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrainingPipeline:
    """
    Automated training pipeline for SelfMonitor ML models
    """
    
    def __init__(self, config: MLOpsConfig):
        self.config = config
        self.mlflow_client = MlflowClient(config.tracking_uri)
        self.notification_manager = NotificationManager(config)
        self.metrics_collector = MetricsCollector(config)
        
        # Set MLflow tracking URI
        mlflow.set_tracking_uri(config.tracking_uri)
        
    async def run_fraud_detection_training(self) -> bool:
        """Train fraud detection model"""
        try:
            logger.info("Starting fraud detection model training")
            
            # Create or get experiment
            experiment_name = "fraud_detection"
            try:
                experiment_id = mlflow.create_experiment(experiment_name)
            except:
                experiment = mlflow.get_experiment_by_name(experiment_name)
                experiment_id = experiment.experiment_id
                
            # Generate synthetic training data (replace with real data loading)
            X_train, X_test, y_train, y_test = self._generate_fraud_detection_data()
            
            # Define models to try
            models = {
                "random_forest": {
                    "model": RandomForestClassifier(random_state=42),
                    "params": {
                        "n_estimators": [100, 200],
                        "max_depth": [10, 20, None],
                        "min_samples_split": [2, 5]
                    }
                },
                "xgboost": {
                    "model": xgb.XGBClassifier(random_state=42),
                    "params": {
                        "n_estimators": [100, 200],
                        "max_depth": [6, 10], 
                        "learning_rate": [0.1, 0.01]
                    }
                },
                "gradient_boosting": {
                    "model": GradientBoostingClassifier(random_state=42),
                    "params": {
                        "n_estimators": [100, 200],
                        "max_depth": [5, 10],
                        "learning_rate": [0.1, 0.01]
                    }
                }
            }
            
            best_model = None
            best_score = 0
            best_run_id = None
            
            # Train and evaluate each model
            for model_name, model_config in models.items():
                run_id = await self._train_single_model(
                    experiment_id=experiment_id,
                    model_name=f"fraud_detection_{model_name}",
                    model=model_config["model"],
                    param_grid=model_config["params"],
                    X_train=X_train,
                    X_test=X_test,
                    y_train=y_train,
                    y_test=y_test,
                    task_type="classification"
                )
                
                # Get model performance
                run = self.mlflow_client.get_run(run_id)
                accuracy = run.data.metrics.get("test_accuracy", 0)
                
                if accuracy > best_score:
                    best_score = accuracy
                    best_model = model_name
                    best_run_id = run_id
                    
            # Register best model
            if best_run_id and best_score > 0.8:  # Minimum threshold
                model_version = await self._register_model(
                    model_name="fraud_detection",
                    run_id=best_run_id,
                    description=f"Best fraud detection model: {best_model} (accuracy: {best_score:.3f})"
                )
                
                logger.info(f"Registered fraud detection model v{model_version} with accuracy {best_score:.3f}")
                
                # Send notification
                await self.notification_manager.send_training_completion(
                    model_name="fraud_detection",
                    experiment_id=experiment_id,
                    run_id=best_run_id,
                    metrics={"test_accuracy": best_score}
                )
                
                return True
            else:
                logger.warning(f"No model met minimum threshold. Best score: {best_score}")
                return False
                
        except Exception as e:
            logger.error(f"Fraud detection training failed: {str(e)}")
            await self.notification_manager.send_notification(
                message=f"Fraud detection training failed: {str(e)}",
                title="Training Failed",
                severity="error"
            )
            return False
            
    async def run_categorization_training(self) -> bool:
        """Train transaction categorization model"""
        try:
            logger.info("Starting transaction categorization model training")
            
            # Create or get experiment
            experiment_name = "transaction_categorization"
            try:
                experiment_id = mlflow.create_experiment(experiment_name)
            except:
                experiment = mlflow.get_experiment_by_name(experiment_name)
                experiment_id = experiment.experiment_id
                
            # Generate synthetic training data
            X_train, X_test, y_train, y_test = self._generate_categorization_data()
            
            # Use ensemble approach
            models = {
                "naive_bayes": {
                    "model": Pipeline([
                        ('scaler', StandardScaler()),
                        ('classifier', LogisticRegression(random_state=42, max_iter=1000))
                    ]),
                    "params": {
                        "classifier__C": [0.1, 1.0, 10.0],
                        "classifier__penalty": ["l1", "l2"]
                    }
                },
                "random_forest": {
                    "model": RandomForestClassifier(random_state=42),
                    "params": {
                        "n_estimators": [100, 200],
                        "max_depth": [15, 25]
                    }
                }
            }
            
            best_model = None
            best_score = 0
            best_run_id = None
            
            for model_name, model_config in models.items():
                run_id = await self._train_single_model(
                    experiment_id=experiment_id,
                    model_name=f"categorization_{model_name}",
                    model=model_config["model"],
                    param_grid=model_config["params"],
                    X_train=X_train,
                    X_test=X_test,
                    y_train=y_train,
                    y_test=y_test,
                    task_type="classification"
                )
                
                run = self.mlflow_client.get_run(run_id)
                accuracy = run.data.metrics.get("test_accuracy", 0)
                
                if accuracy > best_score:
                    best_score = accuracy
                    best_model = model_name
                    best_run_id = run_id
                    
            # Register best model
            if best_run_id and best_score > 0.75:
                model_version = await self._register_model(
                    model_name="transaction_categorization",
                    run_id=best_run_id,
                    description=f"Best categorization model: {best_model} (accuracy: {best_score:.3f})"
                )
                
                logger.info(f"Registered categorization model v{model_version} with accuracy {best_score:.3f}")
                return True
            else:
                logger.warning(f"No categorization model met threshold. Best score: {best_score}")
                return False
                
        except Exception as e:
            logger.error(f"Categorization training failed: {str(e)}")
            return False
            
    async def run_recommendation_training(self) -> bool:
        """Train recommendation engine model"""
        try:
            logger.info("Starting recommendation engine model training")
            
            # Create experiment
            experiment_name = "recommendation_engine"
            try:
                experiment_id = mlflow.create_experiment(experiment_name)
            except:
                experiment = mlflow.get_experiment_by_name(experiment_name)
                experiment_id = experiment.experiment_id
                
            # This would typically involve collaborative filtering or content-based models
            # For now, using a simplified approach with user-item interactions
            
            X_train, X_test, y_train, y_test = self._generate_recommendation_data()
            
            # Use matrix factorization approach (simplified)
            model = Pipeline([
                ('scaler', StandardScaler()),
                ('regressor', RandomForestClassifier(n_estimators=100, random_state=42))
            ])
            
            run_id = await self._train_single_model(
                experiment_id=experiment_id,
                model_name="recommendation_engine",
                model=model,
                param_grid={},  # No hyperparameter tuning for this example
                X_train=X_train,
                X_test=X_test,
                y_train=y_train,
                y_test=y_test,
                task_type="classification"
            )
            
            # Register model
            run = self.mlflow_client.get_run(run_id)
            accuracy = run.data.metrics.get("test_accuracy", 0)
            
            if accuracy > 0.6:  # Lower threshold for recommendation systems
                model_version = await self._register_model(
                    model_name="recommendation_engine",
                    run_id=run_id,
                    description=f"Recommendation engine model (accuracy: {accuracy:.3f})"
                )
                
                logger.info(f"Registered recommendation model v{model_version}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Recommendation training failed: {str(e)}")
            return False
            
    async def _train_single_model(
        self,
        experiment_id: str,
        model_name: str,
        model: Any,
        param_grid: Dict[str, List],
        X_train: pd.DataFrame,
        X_test: pd.DataFrame, 
        y_train: pd.Series,
        y_test: pd.Series,
        task_type: str = "classification"
    ) -> str:
        """Train a single model with hyperparameter tuning"""
        
        with mlflow.start_run(experiment_id=experiment_id, run_name=f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}") as run:
            
            # Log basic info
            mlflow.log_param("model_type", model.__class__.__name__)
            mlflow.log_param("training_samples", len(X_train))
            mlflow.log_param("test_samples", len(X_test))
            mlflow.log_param("feature_count", X_train.shape[1])
            mlflow.log_param("task_type", task_type)
            
            # Hyperparameter tuning if parameters provided
            if param_grid:
                logger.info(f"Performing hyperparameter tuning for {model_name}")
                grid_search = GridSearchCV(
                    model,
                    param_grid,
                    cv=3,
                    scoring='accuracy' if task_type == "classification" else 'neg_mean_squared_error',
                    n_jobs=-1
                )
                
                grid_search.fit(X_train, y_train)
                best_model = grid_search.best_estimator_
                
                # Log best parameters
                for param, value in grid_search.best_params_.items():
                    mlflow.log_param(f"best_{param}", value)
                    
                mlflow.log_metric("cv_best_score", grid_search.best_score_)
                
            else:
                # Train without tuning
                best_model = model
                best_model.fit(X_train, y_train)
                
            # Make predictions
            train_pred = best_model.predict(X_train)
            test_pred = best_model.predict(X_test)
            
            # Calculate metrics
            if task_type == "classification":
                train_accuracy = accuracy_score(y_train, train_pred)
                test_accuracy = accuracy_score(y_test, test_pred)
                
                mlflow.log_metric("train_accuracy", train_accuracy)
                mlflow.log_metric("test_accuracy", test_accuracy)
                
                # Classification report
                report = classification_report(y_test, test_pred, output_dict=True)
                mlflow.log_metric("precision", report['weighted avg']['precision'])
                mlflow.log_metric("recall", report['weighted avg']['recall'])
                mlflow.log_metric("f1_score", report['weighted avg']['f1-score'])
                
                # Log confusion matrix as artifact
                cm = confusion_matrix(y_test, test_pred)
                np.savetxt("confusion_matrix.csv", cm, delimiter=",")
                mlflow.log_artifact("confusion_matrix.csv")
                
            else:  # regression
                from sklearn.metrics import mean_squared_error, r2_score
                
                train_mse = mean_squared_error(y_train, train_pred)
                test_mse = mean_squared_error(y_test, test_pred)
                train_r2 = r2_score(y_train, train_pred)
                test_r2 = r2_score(y_test, test_pred)
                
                mlflow.log_metric("train_mse", train_mse)
                mlflow.log_metric("test_mse", test_mse)
                mlflow.log_metric("train_r2", train_r2)
                mlflow.log_metric("test_r2", test_r2)
                
            # Cross-validation score
            cv_scores = cross_val_score(best_model, X_train, y_train, cv=3)
            mlflow.log_metric("cv_mean_score", cv_scores.mean())
            mlflow.log_metric("cv_std_score", cv_scores.std())
            
            # Log model
            mlflow.sklearn.log_model(
                sk_model=best_model,
                artifact_path="model",
                registered_model_name=None  # Will register separately if good enough
            )
            
            # Log feature importance if available
            if hasattr(best_model, 'feature_importances_'):
                importance_df = pd.DataFrame({
                    'feature': X_train.columns,
                    'importance': best_model.feature_importances_
                }).sort_values('importance', ascending=False)
                
                importance_df.to_csv("feature_importance.csv", index=False)
                mlflow.log_artifact("feature_importance.csv")
                
                # Log top 10 most important features
                for i, row in importance_df.head(10).iterrows():
                    mlflow.log_param(f"top_feature_{i+1}", f"{row['feature']} ({row['importance']:.3f})")
                    
            return run.info.run_id
            
    async def _register_model(
        self,
        model_name: str,
        run_id: str,
        description: str
    ) -> str:
        """Register model in MLflow model registry"""
        try:
            model_uri = f"runs:/{run_id}/model"
            
            # Create registered model if it doesn't exist
            try:
                self.mlflow_client.create_registered_model(
                    model_name,
                    description=f"SelfMonitor {model_name} model"
                )
            except:
                pass  # Model already exists
                
            # Create new version
            model_version = self.mlflow_client.create_model_version(
                name=model_name,
                source=model_uri,
                run_id=run_id,
                description=description
            )
            
            return model_version.version
            
        except Exception as e:
            logger.error(f"Failed to register model {model_name}: {str(e)}")
            raise
            
    def _generate_fraud_detection_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Generate synthetic fraud detection training data"""
        np.random.seed(42)
        n_samples = 10000
        
        # Features: amount, hour, day_of_week, merchant_category, user_age, account_age, etc.
        data = {
            'amount': np.random.lognormal(2, 1, n_samples),  # Transaction amount
            'hour': np.random.randint(0, 24, n_samples),
            'day_of_week': np.random.randint(0, 7, n_samples),
            'merchant_category': np.random.randint(1, 20, n_samples),
            'user_age': np.random.normal(35, 15, n_samples),
            'account_age_days': np.random.exponential(365, n_samples),
            'transactions_last_24h': np.random.poisson(2, n_samples),
            'avg_amount_last_30d': np.random.lognormal(2, 0.5, n_samples),
            'num_merchants_last_30d': np.random.poisson(10, n_samples),
            'is_weekend': np.random.binomial(1, 0.286, n_samples)  # 2/7 chance
        }
        
        df = pd.DataFrame(data)
        
        # Generate fraud labels (5% fraud rate)
        # Fraud more likely for: high amounts, unusual hours, new accounts
        fraud_probability = (
            (df['amount'] > df['amount'].quantile(0.95)).astype(float) * 0.3 +
            ((df['hour'] < 6) | (df['hour'] > 23)).astype(float) * 0.2 +
            (df['account_age_days'] < 30).astype(float) * 0.4 +
            (df['transactions_last_24h'] > 10).astype(float) * 0.3
        )
        
        fraud_labels = np.random.binomial(1, np.clip(fraud_probability * 0.1, 0, 0.2), n_samples)
        
        X_train, X_test, y_train, y_test = train_test_split(
            df, fraud_labels, test_size=0.3, random_state=42, stratify=fraud_labels
        )
        
        return X_train, X_test, pd.Series(y_train), pd.Series(y_test)
        
    def _generate_categorization_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Generate synthetic transaction categorization training data"""
        np.random.seed(42)
        n_samples = 15000
        
        # Categories
        categories = [
            'groceries', 'transportation', 'entertainment', 'utilities', 'healthcare',
            'dining', 'shopping', 'education', 'travel', 'insurance'
        ]
        
        # Merchants for each category
        merchant_patterns = {
            'groceries': ['market', 'grocery', 'supermarket', 'food'],
            'transportation': ['uber', 'taxi', 'gas', 'fuel', 'metro'],
            'entertainment': ['cinema', 'theater', 'netflix', 'spotify', 'game'],
            'utilities': ['electric', 'water', 'phone', 'internet', 'utility'],
            'healthcare': ['hospital', 'clinic', 'pharmacy', 'doctor', 'medical'],
            'dining': ['restaurant', 'cafe', 'pizza', 'burger', 'diner'],
            'shopping': ['amazon', 'store', 'shop', 'retail', 'clothes'],
            'education': ['school', 'university', 'course', 'book', 'tuition'],
            'travel': ['hotel', 'airline', 'booking', 'travel', 'trip'],
            'insurance': ['insurance', 'policy', 'premium', 'coverage']
        }
        
        data = []
        labels = []
        
        for _ in range(n_samples):
            # Choose category
            category = np.random.choice(categories)
            labels.append(category)
            
            # Generate merchant name with category-specific patterns
            patterns = merchant_patterns[category]
            base_pattern = np.random.choice(patterns)
            merchant = f"{base_pattern}_{np.random.randint(1, 100)}"
            
            # Generate amount based on category
            if category == 'groceries':
                amount = np.random.lognormal(3, 0.5)
            elif category == 'transportation':
                amount = np.random.lognormal(2, 0.8)
            elif category == 'utilities':
                amount = np.random.normal(100, 30)
            else:
                amount = np.random.lognormal(2.5, 1)
                
            # Generate features
            row = {
                'amount': amount,
                'merchant_name_length': len(merchant),
                'hour': np.random.randint(0, 24),
                'day_of_week': np.random.randint(0, 7),
                'is_weekend': np.random.binint(1, 0.286),
                'amount_log': np.log(amount + 1),
                # Simplified text features (in practice, would use TF-IDF or embeddings)
                'merchant_contains_pattern': int(any(p in merchant.lower() for p in patterns)),
            }
            
            # Add category-specific features
            for cat in categories:
                row[f'merchant_pattern_{cat}'] = int(any(p in merchant.lower() for p in merchant_patterns[cat]))
                
            data.append(row)
            
        df = pd.DataFrame(data)
        
        X_train, X_test, y_train, y_test = train_test_split(
            df, labels, test_size=0.3, random_state=42, stratify=labels
        )
        
        return X_train, X_test, pd.Series(y_train), pd.Series(y_test)
        
    def _generate_recommendation_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Generate synthetic recommendation training data"""
        np.random.seed(42)
        n_samples = 20000
        
        # User features and product features for collaborative filtering
        n_users = 1000
        n_products = 500
        
        data = {
            'user_id': np.random.randint(1, n_users + 1, n_samples),
            'product_id': np.random.randint(1, n_products + 1, n_samples),
            'user_age': np.random.normal(35, 12, n_samples),
            'user_income': np.random.lognormal(10, 0.5, n_samples),
            'user_tenure_days': np.random.exponential(365, n_samples),
            'product_category': np.random.randint(1, 20, n_samples),
            'product_price': np.random.lognormal(3, 1, n_samples),
            'previous_interactions': np.random.poisson(3, n_samples),
            'session_length_min': np.random.exponential(10, n_samples),
            'time_since_last_purchase': np.random.exponential(30, n_samples)
        }
        
        df = pd.DataFrame(data)
        
        # Generate interaction labels (will user interact with product?)
        interaction_probability = (
            (df['previous_interactions'] > 2).astype(float) * 0.4 +
            (df['session_length_min'] > 15).astype(float) * 0.3 +
            (df['time_since_last_purchase'] < 7).astype(float) * 0.2
        )
        
        labels = np.random.binomial(1, np.clip(interaction_probability * 0.3, 0.05, 0.8), n_samples)
        
        X_train, X_test, y_train, y_test = train_test_split(
            df, labels, test_size=0.3, random_state=42, stratify=labels
        )
        
        return X_train, X_test, pd.Series(y_train), pd.Series(y_test)


async def main():
    """Main training pipeline execution"""
    try:
        config = MLOpsConfig()
        pipeline = TrainingPipeline(config)
        
        logger.info("Starting automated training pipeline")
        
        # Initialize metrics collector
        await pipeline.metrics_collector.initialize()
        
        results = {}
        
        # Run fraud detection training
        logger.info("="*50)
        logger.info(" FRAUD DETECTION MODEL TRAINING")
        logger.info("="*50)
        results['fraud_detection'] = await pipeline.run_fraud_detection_training()
        
        # Run categorization training
        logger.info("="*50)
        logger.info(" TRANSACTION CATEGORIZATION MODEL TRAINING")
        logger.info("="*50)
        results['categorization'] = await pipeline.run_categorization_training()
        
        # Run recommendation training
        logger.info("="*50)
        logger.info(" RECOMMENDATION ENGINE MODEL TRAINING")
        logger.info("="*50)
        results['recommendation'] = await pipeline.run_recommendation_training()
        
        # Summary
        logger.info("="*50)
        logger.info(" TRAINING PIPELINE SUMMARY")
        logger.info("="*50)
        
        successful_models = []
        failed_models = []
        
        for model_name, success in results.items():
            if success:
                successful_models.append(model_name)
                logger.info(f"✅ {model_name}: SUCCESS")
            else:
                failed_models.append(model_name)
                logger.error(f"❌ {model_name}: FAILED")
                
        # Send summary notification
        summary_message = f"""
Training Pipeline Completed

**Successful Models**: {', '.join(successful_models) if successful_models else 'None'}
**Failed Models**: {', '.join(failed_models) if failed_models else 'None'}

**Success Rate**: {len(successful_models)/len(results)*100:.1f}%
        """
        
        await pipeline.notification_manager.send_notification(
            message=summary_message,
            title="🤖 Training Pipeline Summary",
            severity="success" if len(successful_models) > 0 else "warning"
        )
        
        logger.info(f"Training pipeline completed. {len(successful_models)}/{len(results)} models trained successfully.")
        
    except Exception as e:
        logger.error(f"Training pipeline failed: {str(e)}")
        
        # Send failure notification
        config = MLOpsConfig()
        notification_manager = NotificationManager(config)
        await notification_manager.send_notification(
            message=f"Training pipeline failed with error: {str(e)}",
            title="❌ Training Pipeline Failed",
            severity="error"
        )
        
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())