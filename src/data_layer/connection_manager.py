"""
Connection Management and Session Handling

This module provides centralized database connection management, session handling,
and connection pooling for the Policy Validation Copilot system.

Features:
- Database connection pooling and management
- Session lifecycle management with context managers
- Health checks and connection monitoring
- Retry logic and error handling
- Multi-database support (PostgreSQL, SQLite)
- Connection string validation and security
"""

import logging
import time
from contextlib import contextmanager
from typing import Dict, Optional, Any, Generator
from urllib.parse import urlparse

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, StaticPool

from .database import Base

logger = logging.getLogger(__name__)


class ConnectionConfig:
    """Database connection configuration"""
    
    def __init__(self, database_url: str, **kwargs):
        self.database_url = database_url
        self.pool_size = kwargs.get('pool_size', 10)
        self.max_overflow = kwargs.get('max_overflow', 20)
        self.pool_timeout = kwargs.get('pool_timeout', 30)
        self.pool_recycle = kwargs.get('pool_recycle', 3600)
        self.pool_pre_ping = kwargs.get('pool_pre_ping', True)
        self.echo = kwargs.get('echo', False)
        self.echo_pool = kwargs.get('echo_pool', False)
        
        # Connection retry settings
        self.max_retries = kwargs.get('max_retries', 3)
        self.retry_delay = kwargs.get('retry_delay', 1.0)
        
        # Health check settings
        self.health_check_interval = kwargs.get('health_check_interval', 60)
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration parameters"""
        if not self.database_url:
            raise ValueError("database_url is required")
        
        parsed = urlparse(self.database_url)
        if not parsed.scheme:
            raise ValueError("Invalid database URL format")
        
        if self.pool_size < 1:
            raise ValueError("pool_size must be at least 1")
        
        if self.max_overflow < 0:
            raise ValueError("max_overflow cannot be negative")


class DatabaseConnectionManager:
    """Centralized database connection manager"""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._connection_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'failed_connections': 0,
            'last_health_check': None,
            'health_status': 'unknown'
        }
        
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize database engine with connection pooling"""
        try:
            # Determine database type from URL
            parsed_url = urlparse(self.config.database_url)
            db_type = parsed_url.scheme.split('+')[0]
            
            # Configure engine based on database type
            if db_type == 'sqlite':
                self.engine = create_engine(
                    self.config.database_url,
                    poolclass=StaticPool,
                    connect_args={"check_same_thread": False},
                    echo=self.config.echo,
                    echo_pool=self.config.echo_pool
                )
            else:
                # PostgreSQL, MySQL, etc.
                self.engine = create_engine(
                    self.config.database_url,
                    poolclass=QueuePool,
                    pool_size=self.config.pool_size,
                    max_overflow=self.config.max_overflow,
                    pool_timeout=self.config.pool_timeout,
                    pool_recycle=self.config.pool_recycle,
                    pool_pre_ping=self.config.pool_pre_ping,
                    echo=self.config.echo,
                    echo_pool=self.config.echo_pool
                )
            
            # Set up event listeners
            self._setup_event_listeners()
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info(f"Database engine initialized: {db_type}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {e}")
            raise
    
    def _setup_event_listeners(self):
        """Set up SQLAlchemy event listeners for monitoring"""
        
        @event.listens_for(self.engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            self._connection_stats['total_connections'] += 1
            self._connection_stats['active_connections'] += 1
            logger.debug("Database connection established")
        
        @event.listens_for(self.engine, "close")
        def on_close(dbapi_connection, connection_record):
            self._connection_stats['active_connections'] -= 1
            logger.debug("Database connection closed")
        
        @event.listens_for(self.engine, "close_detached")
        def on_close_detached(dbapi_connection):
            self._connection_stats['active_connections'] -= 1
            logger.debug("Database connection detached and closed")
        
        @event.listens_for(self.engine, "invalid")
        def on_invalid(dbapi_connection, connection_record, exception):
            self._connection_stats['failed_connections'] += 1
            logger.warning(f"Database connection invalidated: {exception}")
    
    def get_engine(self) -> Engine:
        """Get database engine"""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        return self.engine
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with automatic cleanup"""
        if not self.SessionLocal:
            raise RuntimeError("Session factory not initialized")
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_direct(self) -> Session:
        """Get database session without context manager (manual cleanup required)"""
        if not self.SessionLocal:
            raise RuntimeError("Session factory not initialized")
        return self.SessionLocal()
    
    def execute_with_retry(self, operation, *args, **kwargs):
        """Execute database operation with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return operation(*args, **kwargs)
            
            except (SQLAlchemyError, DisconnectionError) as e:
                last_exception = e
                
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Database operation failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"Database operation failed after {self.config.max_retries + 1} attempts: {e}")
        
        raise last_exception
    
    def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            start_time = time.time()
            
            with self.get_session() as session:
                # Simple query to test connection
                result = session.execute(text("SELECT 1")).scalar()
                
                if result == 1:
                    response_time = time.time() - start_time
                    self._connection_stats['health_status'] = 'healthy'
                    self._connection_stats['last_health_check'] = time.time()
                    
                    return {
                        'status': 'healthy',
                        'response_time_ms': round(response_time * 1000, 2),
                        'connection_stats': self._connection_stats.copy(),
                        'pool_status': self._get_pool_status()
                    }
                else:
                    self._connection_stats['health_status'] = 'unhealthy'
                    return {
                        'status': 'unhealthy',
                        'error': 'Unexpected query result'
                    }
        
        except Exception as e:
            self._connection_stats['health_status'] = 'unhealthy'
            logger.error(f"Database health check failed: {e}")
            
            return {
                'status': 'unhealthy',
                'error': str(e),
                'connection_stats': self._connection_stats.copy()
            }
    
    def _get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status"""
        if hasattr(self.engine.pool, 'size'):
            return {
                'pool_size': self.engine.pool.size(),
                'checked_in': self.engine.pool.checkedin(),
                'checked_out': self.engine.pool.checkedout(),
                'overflow': self.engine.pool.overflow(),
                'invalid': self.engine.pool.invalid()
            }
        return {}
    
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all database tables"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    def close(self):
        """Close database connections and cleanup"""
        try:
            if self.engine:
                self.engine.dispose()
                logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")


class SessionManager:
    """Session manager with transaction support"""
    
    def __init__(self, connection_manager: DatabaseConnectionManager):
        self.connection_manager = connection_manager
    
    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """Context manager for database transactions"""
        with self.connection_manager.get_session() as session:
            try:
                yield session
                # Commit is handled by get_session context manager
            except Exception:
                # Rollback is handled by get_session context manager
                raise
    
    @contextmanager
    def read_only_session(self) -> Generator[Session, None, None]:
        """Context manager for read-only database sessions"""
        session = self.connection_manager.get_session_direct()
        try:
            # Disable autoflush for read-only operations
            session.autoflush = False
            yield session
        finally:
            session.close()
    
    def execute_in_transaction(self, operation, *args, **kwargs):
        """Execute operation within a transaction"""
        with self.transaction() as session:
            return operation(session, *args, **kwargs)


class DatabaseRegistry:
    """Registry for managing multiple database connections"""
    
    def __init__(self):
        self._connections: Dict[str, DatabaseConnectionManager] = {}
        self._session_managers: Dict[str, SessionManager] = {}
    
    def register_database(self, name: str, config: ConnectionConfig) -> DatabaseConnectionManager:
        """Register a database connection"""
        if name in self._connections:
            logger.warning(f"Database connection '{name}' already registered, replacing")
        
        connection_manager = DatabaseConnectionManager(config)
        self._connections[name] = connection_manager
        self._session_managers[name] = SessionManager(connection_manager)
        
        logger.info(f"Registered database connection: {name}")
        return connection_manager
    
    def get_connection(self, name: str = 'default') -> DatabaseConnectionManager:
        """Get database connection by name"""
        if name not in self._connections:
            raise ValueError(f"Database connection '{name}' not registered")
        return self._connections[name]
    
    def get_session_manager(self, name: str = 'default') -> SessionManager:
        """Get session manager by name"""
        if name not in self._session_managers:
            raise ValueError(f"Session manager '{name}' not found")
        return self._session_managers[name]
    
    def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Perform health check on all registered databases"""
        results = {}
        for name, connection in self._connections.items():
            results[name] = connection.health_check()
        return results
    
    def close_all(self):
        """Close all database connections"""
        for name, connection in self._connections.items():
            try:
                connection.close()
                logger.info(f"Closed database connection: {name}")
            except Exception as e:
                logger.error(f"Error closing database connection '{name}': {e}")
        
        self._connections.clear()
        self._session_managers.clear()


# Global database registry
db_registry = DatabaseRegistry()


# Convenience functions
def register_default_database(database_url: str, **kwargs) -> DatabaseConnectionManager:
    """Register default database connection"""
    config = ConnectionConfig(database_url, **kwargs)
    return db_registry.register_database('default', config)


def get_default_connection() -> DatabaseConnectionManager:
    """Get default database connection"""
    return db_registry.get_connection('default')


def get_default_session_manager() -> SessionManager:
    """Get default session manager"""
    return db_registry.get_session_manager('default')


@contextmanager
def get_db_session(database_name: str = 'default') -> Generator[Session, None, None]:
    """Get database session for specified database"""
    connection = db_registry.get_connection(database_name)
    with connection.get_session() as session:
        yield session


@contextmanager
def get_db_transaction(database_name: str = 'default') -> Generator[Session, None, None]:
    """Get database transaction for specified database"""
    session_manager = db_registry.get_session_manager(database_name)
    with session_manager.transaction() as session:
        yield session


# Database initialization utilities
def initialize_database(database_url: str, create_tables: bool = True, **kwargs) -> DatabaseConnectionManager:
    """Initialize database with default configuration"""
    connection_manager = register_default_database(database_url, **kwargs)
    
    if create_tables:
        connection_manager.create_tables()
    
    return connection_manager


def setup_test_database(database_url: str = "sqlite:///:memory:") -> DatabaseConnectionManager:
    """Set up in-memory database for testing"""
    config = ConnectionConfig(
        database_url=database_url,
        pool_size=1,
        max_overflow=0,
        echo=False
    )
    
    connection_manager = DatabaseConnectionManager(config)
    connection_manager.create_tables()
    
    return connection_manager


# Health monitoring utilities
def monitor_database_health(interval: int = 60):
    """Monitor database health at regular intervals"""
    import threading
    import time
    
    def health_monitor():
        while True:
            try:
                results = db_registry.health_check_all()
                for db_name, health_info in results.items():
                    if health_info['status'] != 'healthy':
                        logger.warning(f"Database '{db_name}' health check failed: {health_info}")
                    else:
                        logger.debug(f"Database '{db_name}' health check passed")
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                time.sleep(interval)
    
    # Start health monitoring in background thread
    monitor_thread = threading.Thread(target=health_monitor, daemon=True)
    monitor_thread.start()
    
    logger.info(f"Database health monitoring started (interval: {interval}s)")


# Connection string utilities
def build_postgresql_url(host: str, port: int, database: str, username: str, password: str, **kwargs) -> str:
    """Build PostgreSQL connection URL"""
    base_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    # Add query parameters
    params = []
    for key, value in kwargs.items():
        params.append(f"{key}={value}")
    
    if params:
        base_url += "?" + "&".join(params)
    
    return base_url


def build_sqlite_url(database_path: str) -> str:
    """Build SQLite connection URL"""
    if database_path == ":memory:":
        return "sqlite:///:memory:"
    return f"sqlite:///{database_path}"


def validate_connection_string(database_url: str) -> bool:
    """Validate database connection string format"""
    try:
        parsed = urlparse(database_url)
        return bool(parsed.scheme and (parsed.netloc or parsed.path))
    except Exception:
        return False
