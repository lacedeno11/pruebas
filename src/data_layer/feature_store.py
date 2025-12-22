"""
Feature Store for ML Services

This module provides feature storage and retrieval capabilities for the ML services
in the Policy Validation Copilot system. It supports feature engineering, versioning,
and serving for classification, anomaly detection, and ETA prediction models.

Features:
- Feature definition and schema management
- Feature computation and storage with versioning
- Feature serving for real-time ML inference
- Feature drift monitoring and alerting
- Historical feature access for model training
- Feature lineage and audit trails
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

import numpy as np
import pandas as pd
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text,
    UniqueConstraint, Index, create_engine
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from .database import Base, DatabaseManager

logger = logging.getLogger(__name__)


class FeatureDefinition(Base):
    """Feature definition and metadata"""
    __tablename__ = 'feature_definitions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    feature_name = Column(String(200), unique=True, nullable=False, index=True)
    feature_type = Column(String(50), nullable=False)  # numerical, categorical, boolean, text
    description = Column(Text, nullable=True)
    
    # Feature computation
    computation_logic = Column(JSON, nullable=False)  # Feature computation definition
    dependencies = Column(JSON, nullable=True)  # List of dependent features/data sources
    
    # Data types and constraints
    data_type = Column(String(50), nullable=False)  # int, float, string, boolean
    nullable = Column(Boolean, nullable=False, default=True)
    default_value = Column(String(500), nullable=True)
    
    # Validation rules
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    allowed_values = Column(JSON, nullable=True)  # For categorical features
    
    # Versioning and lifecycle
    version = Column(String(50), nullable=False, default="1.0.0")
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(String(100), nullable=False)
    
    # ML service associations
    ml_services = Column(JSON, nullable=True)  # List of ML services using this feature
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    feature_values = relationship("FeatureValue", back_populates="feature_definition", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_feature_name_version', 'feature_name', 'version'),
        Index('idx_feature_active_type', 'is_active', 'feature_type'),
    )


class FeatureValue(Base):
    """Feature values for specific entities (cases)"""
    __tablename__ = 'feature_values'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    feature_definition_id = Column(UUID(as_uuid=True), ForeignKey('feature_definitions.id'), nullable=False)
    
    # Entity identification
    entity_id = Column(String(100), nullable=False, index=True)  # case_id, customer_id, etc.
    entity_type = Column(String(50), nullable=False, default='case')
    
    # Feature value
    value_numeric = Column(Float, nullable=True)
    value_text = Column(Text, nullable=True)
    value_boolean = Column(Boolean, nullable=True)
    value_json = Column(JSON, nullable=True)  # For complex features
    
    # Computation metadata
    computation_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    computation_version = Column(String(50), nullable=False)
    computation_context = Column(JSON, nullable=True)  # Context used for computation
    
    # Quality and validation
    is_valid = Column(Boolean, nullable=False, default=True)
    validation_errors = Column(JSON, nullable=True)
    confidence_score = Column(Float, nullable=True)  # Confidence in feature value
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    feature_definition = relationship("FeatureDefinition", back_populates="feature_values")
    
    __table_args__ = (
        UniqueConstraint('feature_definition_id', 'entity_id', 'computation_version', 
                        name='uq_feature_entity_version'),
        Index('idx_feature_entity_timestamp', 'entity_id', 'computation_timestamp'),
        Index('idx_feature_valid_confidence', 'is_valid', 'confidence_score'),
    )


class FeatureSet(Base):
    """Feature sets for ML models"""
    __tablename__ = 'feature_sets'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    feature_set_name = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Feature set definition
    feature_names = Column(JSON, nullable=False)  # List of feature names
    ml_service = Column(String(100), nullable=False)  # ML service using this feature set
    model_version = Column(String(50), nullable=True)
    
    # Versioning
    version = Column(String(50), nullable=False, default="1.0.0")
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Performance tracking
    last_used = Column(DateTime, nullable=True)
    usage_count = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_featureset_service_version', 'ml_service', 'version'),
        Index('idx_featureset_active_usage', 'is_active', 'usage_count'),
    )


class FeatureDriftMetric(Base):
    """Feature drift monitoring metrics"""
    __tablename__ = 'feature_drift_metrics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    feature_definition_id = Column(UUID(as_uuid=True), ForeignKey('feature_definitions.id'), nullable=False)
    
    # Drift measurement
    measurement_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    reference_period_start = Column(DateTime, nullable=False)
    reference_period_end = Column(DateTime, nullable=False)
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    
    # Drift metrics
    drift_score = Column(Float, nullable=False)  # Overall drift score (0-1)
    drift_method = Column(String(50), nullable=False)  # KS test, PSI, etc.
    
    # Statistical measures
    reference_mean = Column(Float, nullable=True)
    current_mean = Column(Float, nullable=True)
    reference_std = Column(Float, nullable=True)
    current_std = Column(Float, nullable=True)
    
    # Distribution metrics
    distribution_metrics = Column(JSON, nullable=True)  # Detailed distribution comparison
    
    # Alert status
    drift_detected = Column(Boolean, nullable=False, default=False)
    alert_threshold = Column(Float, nullable=False, default=0.1)
    alert_sent = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    feature_definition = relationship("FeatureDefinition")
    
    __table_args__ = (
        Index('idx_drift_feature_date', 'feature_definition_id', 'measurement_date'),
        Index('idx_drift_detected_alert', 'drift_detected', 'alert_sent'),
    )


class FeatureComputer:
    """Feature computation engine"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.feature_definitions = {}
        self._load_feature_definitions()
    
    def _load_feature_definitions(self):
        """Load active feature definitions from database"""
        session = self.db_manager.get_session()
        try:
            definitions = session.query(FeatureDefinition).filter(
                FeatureDefinition.is_active == True
            ).all()
            
            for definition in definitions:
                self.feature_definitions[definition.feature_name] = definition
            
            logger.info(f"Loaded {len(self.feature_definitions)} feature definitions")
        finally:
            session.close()
    
    def compute_case_features(self, case_data: Dict, feature_names: List[str] = None) -> Dict[str, Any]:
        """Compute features for a case"""
        if feature_names is None:
            feature_names = list(self.feature_definitions.keys())
        
        computed_features = {}
        computation_context = {
            'case_id': case_data.get('case_id'),
            'computation_timestamp': datetime.utcnow().isoformat(),
            'input_data_hash': self._hash_dict(case_data)
        }
        
        for feature_name in feature_names:
            if feature_name not in self.feature_definitions:
                logger.warning(f"Feature definition not found: {feature_name}")
                continue
            
            try:
                feature_def = self.feature_definitions[feature_name]
                value = self._compute_single_feature(feature_def, case_data, computation_context)
                computed_features[feature_name] = value
                
            except Exception as e:
                logger.error(f"Failed to compute feature {feature_name}: {e}")
                computed_features[feature_name] = None
        
        return computed_features
    
    def _compute_single_feature(self, feature_def: FeatureDefinition, 
                               case_data: Dict, context: Dict) -> Any:
        """Compute a single feature value"""
        computation_logic = feature_def.computation_logic
        
        if computation_logic['type'] == 'direct_field':
            # Direct field extraction
            field_path = computation_logic['field_path']
            return self._extract_field_value(case_data, field_path)
        
        elif computation_logic['type'] == 'aggregation':
            # Aggregation-based feature
            return self._compute_aggregation_feature(computation_logic, case_data, context)
        
        elif computation_logic['type'] == 'derived':
            # Derived from other features
            return self._compute_derived_feature(computation_logic, case_data, context)
        
        elif computation_logic['type'] == 'temporal':
            # Time-based feature
            return self._compute_temporal_feature(computation_logic, case_data, context)
        
        else:
            raise ValueError(f"Unknown computation type: {computation_logic['type']}")
    
    def _extract_field_value(self, data: Dict, field_path: str) -> Any:
        """Extract value from nested dictionary using dot notation"""
        keys = field_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def _compute_aggregation_feature(self, logic: Dict, case_data: Dict, context: Dict) -> Any:
        """Compute aggregation-based feature"""
        # This would implement various aggregation functions
        # For now, a simplified implementation
        
        source_field = logic.get('source_field')
        aggregation_type = logic.get('aggregation_type', 'count')
        
        if source_field:
            values = self._extract_field_value(case_data, source_field)
            if isinstance(values, list):
                if aggregation_type == 'count':
                    return len(values)
                elif aggregation_type == 'sum' and all(isinstance(v, (int, float)) for v in values):
                    return sum(values)
                elif aggregation_type == 'avg' and all(isinstance(v, (int, float)) for v in values):
                    return sum(values) / len(values) if values else 0
        
        return 0
    
    def _compute_derived_feature(self, logic: Dict, case_data: Dict, context: Dict) -> Any:
        """Compute derived feature from other features"""
        # This would implement feature combinations and transformations
        # Simplified implementation
        
        dependencies = logic.get('dependencies', [])
        operation = logic.get('operation', 'identity')
        
        if operation == 'ratio' and len(dependencies) == 2:
            val1 = self._extract_field_value(case_data, dependencies[0])
            val2 = self._extract_field_value(case_data, dependencies[1])
            
            if val1 is not None and val2 is not None and val2 != 0:
                return float(val1) / float(val2)
        
        return None
    
    def _compute_temporal_feature(self, logic: Dict, case_data: Dict, context: Dict) -> Any:
        """Compute time-based feature"""
        # This would implement temporal features like time since, duration, etc.
        # Simplified implementation
        
        date_field = logic.get('date_field')
        operation = logic.get('operation', 'days_since')
        
        if date_field:
            date_value = self._extract_field_value(case_data, date_field)
            if date_value:
                if isinstance(date_value, str):
                    date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                elif isinstance(date_value, datetime):
                    pass
                else:
                    return None
                
                if operation == 'days_since':
                    return (datetime.utcnow() - date_value).days
                elif operation == 'hours_since':
                    return (datetime.utcnow() - date_value).total_seconds() / 3600
        
        return None
    
    def _hash_dict(self, data: Dict) -> str:
        """Create hash of dictionary for versioning"""
        import hashlib
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(json_str.encode()).hexdigest()


class FeatureStore:
    """Main feature store interface"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.feature_computer = FeatureComputer(db_manager)
        self.cache = {}  # Simple in-memory cache
    
    def register_feature(self, feature_name: str, feature_type: str, 
                        computation_logic: Dict, description: str = None,
                        data_type: str = "float", **kwargs) -> bool:
        """Register a new feature definition"""
        session = self.db_manager.get_session()
        try:
            # Check if feature already exists
            existing = session.query(FeatureDefinition).filter(
                FeatureDefinition.feature_name == feature_name
            ).first()
            
            if existing:
                logger.warning(f"Feature {feature_name} already exists")
                return False
            
            # Create new feature definition
            feature_def = FeatureDefinition(
                feature_name=feature_name,
                feature_type=feature_type,
                description=description,
                computation_logic=computation_logic,
                data_type=data_type,
                created_by=kwargs.get('created_by', 'system'),
                **{k: v for k, v in kwargs.items() if k in [
                    'nullable', 'default_value', 'min_value', 'max_value', 
                    'allowed_values', 'dependencies', 'ml_services'
                ]}
            )
            
            session.add(feature_def)
            session.commit()
            
            # Reload feature definitions
            self.feature_computer._load_feature_definitions()
            
            logger.info(f"Registered feature: {feature_name}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to register feature {feature_name}: {e}")
            return False
        finally:
            session.close()
    
    def compute_and_store_features(self, entity_id: str, entity_data: Dict,
                                  feature_names: List[str] = None,
                                  entity_type: str = 'case') -> Dict[str, Any]:
        """Compute and store features for an entity"""
        # Compute features
        computed_features = self.feature_computer.compute_case_features(
            entity_data, feature_names
        )
        
        # Store feature values
        session = self.db_manager.get_session()
        try:
            for feature_name, value in computed_features.items():
                if feature_name not in self.feature_computer.feature_definitions:
                    continue
                
                feature_def = self.feature_computer.feature_definitions[feature_name]
                
                # Determine value storage based on data type
                value_fields = {}
                if feature_def.data_type == 'float' or feature_def.data_type == 'int':
                    value_fields['value_numeric'] = float(value) if value is not None else None
                elif feature_def.data_type == 'boolean':
                    value_fields['value_boolean'] = bool(value) if value is not None else None
                elif feature_def.data_type == 'string':
                    value_fields['value_text'] = str(value) if value is not None else None
                else:
                    value_fields['value_json'] = value
                
                # Create feature value record
                feature_value = FeatureValue(
                    feature_definition_id=feature_def.id,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    computation_version=feature_def.version,
                    **value_fields
                )
                
                session.add(feature_value)
            
            session.commit()
            logger.info(f"Stored {len(computed_features)} features for entity {entity_id}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store features for entity {entity_id}: {e}")
        finally:
            session.close()
        
        return computed_features
    
    def get_features(self, entity_id: str, feature_names: List[str],
                    entity_type: str = 'case', version: str = None) -> Dict[str, Any]:
        """Retrieve features for an entity"""
        cache_key = f"{entity_id}_{entity_type}_{'_'.join(sorted(feature_names))}"
        
        # Check cache first
        if cache_key in self.cache:
            cached_data, cache_time = self.cache[cache_key]
            if (datetime.utcnow() - cache_time).seconds < 300:  # 5 minute cache
                return cached_data
        
        session = self.db_manager.get_session()
        try:
            # Query feature values
            query = session.query(FeatureValue, FeatureDefinition).join(
                FeatureDefinition, FeatureValue.feature_definition_id == FeatureDefinition.id
            ).filter(
                FeatureValue.entity_id == entity_id,
                FeatureValue.entity_type == entity_type,
                FeatureDefinition.feature_name.in_(feature_names)
            )
            
            if version:
                query = query.filter(FeatureValue.computation_version == version)
            
            results = query.all()
            
            # Build feature dictionary
            features = {}
            for feature_value, feature_def in results:
                # Extract value based on data type
                if feature_def.data_type in ['float', 'int']:
                    value = feature_value.value_numeric
                elif feature_def.data_type == 'boolean':
                    value = feature_value.value_boolean
                elif feature_def.data_type == 'string':
                    value = feature_value.value_text
                else:
                    value = feature_value.value_json
                
                features[feature_def.feature_name] = value
            
            # Cache results
            self.cache[cache_key] = (features, datetime.utcnow())
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to get features for entity {entity_id}: {e}")
            return {}
        finally:
            session.close()
    
    def create_feature_set(self, feature_set_name: str, feature_names: List[str],
                          ml_service: str, description: str = None) -> bool:
        """Create a feature set for ML models"""
        session = self.db_manager.get_session()
        try:
            # Validate that all features exist
            existing_features = session.query(FeatureDefinition.feature_name).filter(
                FeatureDefinition.feature_name.in_(feature_names),
                FeatureDefinition.is_active == True
            ).all()
            
            existing_names = {f[0] for f in existing_features}
            missing_features = set(feature_names) - existing_names
            
            if missing_features:
                logger.error(f"Missing features for feature set: {missing_features}")
                return False
            
            # Create feature set
            feature_set = FeatureSet(
                feature_set_name=feature_set_name,
                description=description,
                feature_names=feature_names,
                ml_service=ml_service
            )
            
            session.add(feature_set)
            session.commit()
            
            logger.info(f"Created feature set: {feature_set_name}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create feature set {feature_set_name}: {e}")
            return False
        finally:
            session.close()
    
    def get_feature_set_data(self, feature_set_name: str, entity_ids: List[str],
                            entity_type: str = 'case') -> pd.DataFrame:
        """Get feature data for a feature set as DataFrame"""
        session = self.db_manager.get_session()
        try:
            # Get feature set definition
            feature_set = session.query(FeatureSet).filter(
                FeatureSet.feature_set_name == feature_set_name,
                FeatureSet.is_active == True
            ).first()
            
            if not feature_set:
                logger.error(f"Feature set not found: {feature_set_name}")
                return pd.DataFrame()
            
            # Get feature data for all entities
            all_features = []
            for entity_id in entity_ids:
                features = self.get_features(entity_id, feature_set.feature_names, entity_type)
                features['entity_id'] = entity_id
                all_features.append(features)
            
            # Convert to DataFrame
            df = pd.DataFrame(all_features)
            df.set_index('entity_id', inplace=True)
            
            # Update usage statistics
            feature_set.last_used = datetime.utcnow()
            feature_set.usage_count += 1
            session.commit()
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get feature set data: {e}")
            return pd.DataFrame()
        finally:
            session.close()
    
    def monitor_feature_drift(self, feature_name: str, 
                             reference_days: int = 30,
                             current_days: int = 7) -> Dict:
        """Monitor feature drift between time periods"""
        session = self.db_manager.get_session()
        try:
            # Get feature definition
            feature_def = session.query(FeatureDefinition).filter(
                FeatureDefinition.feature_name == feature_name,
                FeatureDefinition.is_active == True
            ).first()
            
            if not feature_def:
                return {'error': f'Feature not found: {feature_name}'}
            
            # Define time periods
            current_end = datetime.utcnow()
            current_start = current_end - timedelta(days=current_days)
            reference_end = current_start
            reference_start = reference_end - timedelta(days=reference_days)
            
            # Get feature values for both periods
            reference_values = session.query(FeatureValue.value_numeric).filter(
                FeatureValue.feature_definition_id == feature_def.id,
                FeatureValue.computation_timestamp.between(reference_start, reference_end),
                FeatureValue.value_numeric.isnot(None)
            ).all()
            
            current_values = session.query(FeatureValue.value_numeric).filter(
                FeatureValue.feature_definition_id == feature_def.id,
                FeatureValue.computation_timestamp.between(current_start, current_end),
                FeatureValue.value_numeric.isnot(None)
            ).all()
            
            if not reference_values or not current_values:
                return {'error': 'Insufficient data for drift analysis'}
            
            # Convert to numpy arrays
            ref_array = np.array([v[0] for v in reference_values])
            cur_array = np.array([v[0] for v in current_values])
            
            # Calculate drift metrics
            drift_score = self._calculate_drift_score(ref_array, cur_array)
            
            # Create drift metric record
            drift_metric = FeatureDriftMetric(
                feature_definition_id=feature_def.id,
                reference_period_start=reference_start,
                reference_period_end=reference_end,
                current_period_start=current_start,
                current_period_end=current_end,
                drift_score=drift_score,
                drift_method='statistical',
                reference_mean=float(np.mean(ref_array)),
                current_mean=float(np.mean(cur_array)),
                reference_std=float(np.std(ref_array)),
                current_std=float(np.std(cur_array)),
                drift_detected=drift_score > 0.1  # Default threshold
            )
            
            session.add(drift_metric)
            session.commit()
            
            return {
                'feature_name': feature_name,
                'drift_score': drift_score,
                'drift_detected': drift_score > 0.1,
                'reference_stats': {
                    'mean': float(np.mean(ref_array)),
                    'std': float(np.std(ref_array)),
                    'count': len(ref_array)
                },
                'current_stats': {
                    'mean': float(np.mean(cur_array)),
                    'std': float(np.std(cur_array)),
                    'count': len(cur_array)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to monitor drift for feature {feature_name}: {e}")
            return {'error': str(e)}
        finally:
            session.close()
    
    def _calculate_drift_score(self, reference: np.ndarray, current: np.ndarray) -> float:
        """Calculate drift score between two distributions"""
        try:
            from scipy import stats
            
            # Use Kolmogorov-Smirnov test
            ks_statistic, p_value = stats.ks_2samp(reference, current)
            
            # Convert to drift score (0-1 range)
            drift_score = min(ks_statistic, 1.0)
            
            return float(drift_score)
            
        except ImportError:
            # Fallback to simple statistical comparison
            ref_mean, ref_std = np.mean(reference), np.std(reference)
            cur_mean, cur_std = np.mean(current), np.std(current)
            
            # Normalized difference in means
            mean_diff = abs(cur_mean - ref_mean) / (ref_std + 1e-8)
            
            # Normalized difference in standard deviations
            std_diff = abs(cur_std - ref_std) / (ref_std + 1e-8)
            
            # Combined drift score
            drift_score = min((mean_diff + std_diff) / 2, 1.0)
            
            return float(drift_score)
    
    def get_feature_statistics(self) -> Dict:
        """Get feature store statistics"""
        session = self.db_manager.get_session()
        try:
            # Count features
            total_features = session.query(FeatureDefinition).count()
            active_features = session.query(FeatureDefinition).filter(
                FeatureDefinition.is_active == True
            ).count()
            
            # Count feature values
            total_values = session.query(FeatureValue).count()
            
            # Count feature sets
            total_feature_sets = session.query(FeatureSet).count()
            active_feature_sets = session.query(FeatureSet).filter(
                FeatureSet.is_active == True
            ).count()
            
            return {
                'total_features': total_features,
                'active_features': active_features,
                'total_feature_values': total_values,
                'total_feature_sets': total_feature_sets,
                'active_feature_sets': active_feature_sets
            }
            
        except Exception as e:
            logger.error(f"Failed to get feature statistics: {e}")
            return {}
        finally:
            session.close()


# Predefined feature definitions for common ML features
COMMON_FEATURES = {
    'case_age_hours': {
        'feature_type': 'numerical',
        'data_type': 'float',
        'description': 'Hours since case creation',
        'computation_logic': {
            'type': 'temporal',
            'date_field': 'created_at',
            'operation': 'hours_since'
        }
    },
    'attachment_count': {
        'feature_type': 'numerical',
        'data_type': 'int',
        'description': 'Number of attachments in case',
        'computation_logic': {
            'type': 'aggregation',
            'source_field': 'attachments',
            'aggregation_type': 'count'
        }
    },
    'priority_numeric': {
        'feature_type': 'numerical',
        'data_type': 'int',
        'description': 'Numeric representation of priority',
        'computation_logic': {
            'type': 'direct_field',
            'field_path': 'priority',
            'transformation': {
                'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4
            }
        }
    },
    'service_frequency': {
        'feature_type': 'numerical',
        'data_type': 'float',
        'description': 'Historical frequency of service code',
        'computation_logic': {
            'type': 'aggregation',
            'source_field': 'service_code',
            'aggregation_type': 'frequency',
            'time_window_days': 90
        }
    }
}


def initialize_common_features(feature_store: FeatureStore) -> int:
    """Initialize common features in the feature store"""
    initialized_count = 0
    
    for feature_name, config in COMMON_FEATURES.items():
        success = feature_store.register_feature(
            feature_name=feature_name,
            **config
        )
        if success:
            initialized_count += 1
    
    logger.info(f"Initialized {initialized_count} common features")
    return initialized_count


# Factory function for creating feature store
def create_feature_store(db_manager: DatabaseManager) -> FeatureStore:
    """Factory function to create feature store"""
    feature_store = FeatureStore(db_manager)
    
    # Initialize common features
    initialize_common_features(feature_store)
    
    return feature_store
