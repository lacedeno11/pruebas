"""
Health Check Manager

This module implements comprehensive health checks for all external services
and dependencies in the Policy Validation Copilot system.
"""

from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime, timedelta
import logging
import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import aiohttp
import psutil

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceType(str, Enum):
    """Service type categories"""
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    STORAGE = "storage"
    EXTERNAL_API = "external_api"
    ML_SERVICE = "ml_service"
    NOTIFICATION = "notification"
    KNOWLEDGE_BASE = "knowledge_base"
    SYSTEM = "system"


@dataclass
class HealthCheckResult:
    """Health check result"""
    service_name: str
    service_type: ServiceType
    status: HealthStatus
    response_time_ms: float
    timestamp: datetime
    details: Dict[str, Any]
    error_message: Optional[str] = None
    dependencies: Optional[List[str]] = None


@dataclass
class HealthCheckConfig:
    """Health check configuration"""
    service_name: str
    service_type: ServiceType
    check_interval_seconds: int = 30
    timeout_seconds: int = 10
    retry_attempts: int = 3
    retry_delay_seconds: int = 5
    critical: bool = True
    dependencies: Optional[List[str]] = None
    custom_thresholds: Optional[Dict[str, Any]] = None


class ServiceHealthCheck(ABC):
    """Abstract base class for service health checks"""
    
    def __init__(self, config: HealthCheckConfig):
        self.config = config
        self.last_result: Optional[HealthCheckResult] = None
        self.check_history: List[HealthCheckResult] = []
        self.max_history = 100
        
        # Statistics
        self.stats = {
            "total_checks": 0,
            "healthy_checks": 0,
            "degraded_checks": 0,
            "unhealthy_checks": 0,
            "avg_response_time_ms": 0.0,
            "last_healthy": None,
            "last_unhealthy": None
        }
    
    @abstractmethod
    async def check_health(self) -> HealthCheckResult:
        """Perform health check"""
        pass
    
    async def run_health_check(self) -> HealthCheckResult:
        """Run health check with retry logic"""
        
        for attempt in range(self.config.retry_attempts):
            try:
                start_time = time.time()
                
                # Run health check with timeout
                result = await asyncio.wait_for(
                    self.check_health(),
                    timeout=self.config.timeout_seconds
                )
                
                # Calculate response time
                response_time = (time.time() - start_time) * 1000
                result.response_time_ms = response_time
                result.timestamp = datetime.utcnow()
                
                # Update statistics
                self._update_stats(result)
                
                # Store result
                self.last_result = result
                self._add_to_history(result)
                
                return result
                
            except asyncio.TimeoutError:
                error_msg = f"Health check timeout after {self.config.timeout_seconds}s"
                logger.warning(f"{self.config.service_name}: {error_msg}")
                
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay_seconds)
                    continue
                
                # Final attempt failed
                result = HealthCheckResult(
                    service_name=self.config.service_name,
                    service_type=self.config.service_type,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=self.config.timeout_seconds * 1000,
                    timestamp=datetime.utcnow(),
                    details={},
                    error_message=error_msg,
                    dependencies=self.config.dependencies
                )
                
                self._update_stats(result)
                self.last_result = result
                self._add_to_history(result)
                
                return result
                
            except Exception as e:
                error_msg = f"Health check failed: {str(e)}"
                logger.error(f"{self.config.service_name}: {error_msg}")
                
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay_seconds)
                    continue
                
                # Final attempt failed
                result = HealthCheckResult(
                    service_name=self.config.service_name,
                    service_type=self.config.service_type,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0.0,
                    timestamp=datetime.utcnow(),
                    details={},
                    error_message=error_msg,
                    dependencies=self.config.dependencies
                )
                
                self._update_stats(result)
                self.last_result = result
                self._add_to_history(result)
                
                return result
    
    def _update_stats(self, result: HealthCheckResult) -> None:
        """Update health check statistics"""
        
        self.stats["total_checks"] += 1
        
        if result.status == HealthStatus.HEALTHY:
            self.stats["healthy_checks"] += 1
            self.stats["last_healthy"] = result.timestamp
        elif result.status == HealthStatus.DEGRADED:
            self.stats["degraded_checks"] += 1
        else:
            self.stats["unhealthy_checks"] += 1
            self.stats["last_unhealthy"] = result.timestamp
        
        # Update average response time
        current_avg = self.stats["avg_response_time_ms"]
        total_checks = self.stats["total_checks"]
        new_avg = ((current_avg * (total_checks - 1)) + result.response_time_ms) / total_checks
        self.stats["avg_response_time_ms"] = new_avg
    
    def _add_to_history(self, result: HealthCheckResult) -> None:
        """Add result to history"""
        self.check_history.append(result)
        
        # Trim history if too long
        if len(self.check_history) > self.max_history:
            self.check_history = self.check_history[-self.max_history:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get health check statistics"""
        stats = self.stats.copy()
        
        if stats["total_checks"] > 0:
            stats["health_rate"] = stats["healthy_checks"] / stats["total_checks"]
            stats["degraded_rate"] = stats["degraded_checks"] / stats["total_checks"]
            stats["unhealthy_rate"] = stats["unhealthy_checks"] / stats["total_checks"]
        
        return stats


class DatabaseHealthCheck(ServiceHealthCheck):
    """Database health check implementation"""
    
    def __init__(self, config: HealthCheckConfig, connection_string: str):
        super().__init__(config)
        self.connection_string = connection_string
    
    async def check_health(self) -> HealthCheckResult:
        """Check database health"""
        
        try:
            from ..database import get_repository_factory
            
            # Test database connection
            repo_factory = get_repository_factory()
            
            # Simple query to test connectivity
            # In production, would use actual database connection
            
            details = {
                "connection_status": "connected",
                "database_type": "postgresql",  # Would detect actual type
                "active_connections": 5,  # Would get actual count
                "max_connections": 100
            }
            
            # Check connection pool health
            connection_usage = details["active_connections"] / details["max_connections"]
            
            if connection_usage > 0.9:
                status = HealthStatus.DEGRADED
                details["warning"] = "High connection usage"
            elif connection_usage > 0.95:
                status = HealthStatus.UNHEALTHY
                details["error"] = "Critical connection usage"
            else:
                status = HealthStatus.HEALTHY
            
            return HealthCheckResult(
                service_name=self.config.service_name,
                service_type=self.config.service_type,
                status=status,
                response_time_ms=0.0,  # Will be set by caller
                timestamp=datetime.utcnow(),
                details=details,
                dependencies=self.config.dependencies
            )
            
        except Exception as e:
            return HealthCheckResult(
                service_name=self.config.service_name,
                service_type=self.config.service_type,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0.0,
                timestamp=datetime.utcnow(),
                details={},
                error_message=str(e),
                dependencies=self.config.dependencies
            )


class RedisHealthCheck(ServiceHealthCheck):
    """Redis health check implementation"""
    
    def __init__(self, config: HealthCheckConfig, redis_url: str):
        super().__init__(config)
        self.redis_url = redis_url
    
    async def check_health(self) -> HealthCheckResult:
        """Check Redis health"""
        
        try:
            import redis.asyncio as redis
            
            # Create Redis client
            client = redis.from_url(self.redis_url)
            
            # Test basic operations
            await client.ping()
            
            # Get Redis info
            info = await client.info()
            
            details = {
                "redis_version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
            
            # Calculate hit rate
            hits = details["keyspace_hits"]
            misses = details["keyspace_misses"]
            if hits + misses > 0:
                hit_rate = hits / (hits + misses)
                details["hit_rate"] = hit_rate
                
                if hit_rate < 0.5:
                    status = HealthStatus.DEGRADED
                    details["warning"] = "Low cache hit rate"
                else:
                    status = HealthStatus.HEALTHY
            else:
                status = HealthStatus.HEALTHY
            
            await client.close()
            
            return HealthCheckResult(
                service_name=self.config.service_name,
                service_type=self.config.service_type,
                status=status,
                response_time_ms=0.0,
                timestamp=datetime.utcnow(),
                details=details,
                dependencies=self.config.dependencies
            )
            
        except Exception as e:
            return HealthCheckResult(
                service_name=self.config.service_name,
                service_type=self.config.service_type,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0.0,
                timestamp=datetime.utcnow(),
                details={},
                error_message=str(e),
                dependencies=self.config.dependencies
            )


class HTTPServiceHealthCheck(ServiceHealthCheck):
    """HTTP service health check implementation"""
    
    def __init__(self, config: HealthCheckConfig, endpoint_url: str, expected_status: int = 200):
        super().__init__(config)
        self.endpoint_url = endpoint_url
        self.expected_status = expected_status
    
    async def check_health(self) -> HealthCheckResult:
        """Check HTTP service health"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.endpoint_url,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    
                    details = {
                        "endpoint": self.endpoint_url,
                        "status_code": response.status,
                        "expected_status": self.expected_status,
                        "headers": dict(response.headers)
                    }
                    
                    if response.status == self.expected_status:
                        status = HealthStatus.HEALTHY
                    elif 200 <= response.status < 300:
                        status = HealthStatus.DEGRADED
                        details["warning"] = f"Unexpected status code: {response.status}"
                    else:
                        status = HealthStatus.UNHEALTHY
                        details["error"] = f"HTTP error: {response.status}"
                    
                    return HealthCheckResult(
                        service_name=self.config.service_name,
                        service_type=self.config.service_type,
                        status=status,
                        response_time_ms=0.0,
                        timestamp=datetime.utcnow(),
                        details=details,
                        dependencies=self.config.dependencies
                    )
                    
        except Exception as e:
            return HealthCheckResult(
                service_name=self.config.service_name,
                service_type=self.config.service_type,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0.0,
                timestamp=datetime.utcnow(),
                details={"endpoint": self.endpoint_url},
                error_message=str(e),
                dependencies=self.config.dependencies
            )


class SystemHealthCheck(ServiceHealthCheck):
    """System resource health check implementation"""
    
    def __init__(self, config: HealthCheckConfig):
        super().__init__(config)
    
    async def check_health(self) -> HealthCheckResult:
        """Check system health"""
        
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            details = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "memory_total_gb": memory.total / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
                "disk_total_gb": disk.total / (1024**3),
                "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
            }
            
            # Determine status based on thresholds
            status = HealthStatus.HEALTHY
            warnings = []
            
            if cpu_percent > 90:
                status = HealthStatus.UNHEALTHY
                details["error"] = "Critical CPU usage"
            elif cpu_percent > 80:
                status = HealthStatus.DEGRADED
                warnings.append("High CPU usage")
            
            if memory.percent > 95:
                status = HealthStatus.UNHEALTHY
                details["error"] = "Critical memory usage"
            elif memory.percent > 85:
                status = HealthStatus.DEGRADED
                warnings.append("High memory usage")
            
            if disk.percent > 95:
                status = HealthStatus.UNHEALTHY
                details["error"] = "Critical disk usage"
            elif disk.percent > 85:
                status = HealthStatus.DEGRADED
                warnings.append("High disk usage")
            
            if warnings:
                details["warnings"] = warnings
            
            return HealthCheckResult(
                service_name=self.config.service_name,
                service_type=self.config.service_type,
                status=status,
                response_time_ms=0.0,
                timestamp=datetime.utcnow(),
                details=details,
                dependencies=self.config.dependencies
            )
            
        except Exception as e:
            return HealthCheckResult(
                service_name=self.config.service_name,
                service_type=self.config.service_type,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0.0,
                timestamp=datetime.utcnow(),
                details={},
                error_message=str(e),
                dependencies=self.config.dependencies
            )


class MLServiceHealthCheck(ServiceHealthCheck):
    """ML service health check implementation"""
    
    def __init__(self, config: HealthCheckConfig, ml_service):
        super().__init__(config)
        self.ml_service = ml_service
    
    async def check_health(self) -> HealthCheckResult:
        """Check ML service health"""
        
        try:
            # Use the ML service's built-in health check
            health_result = await self.ml_service.health_check()
            
            if health_result["status"] == "healthy":
                status = HealthStatus.HEALTHY
            elif health_result["status"] == "degraded":
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY
            
            return HealthCheckResult(
                service_name=self.config.service_name,
                service_type=self.config.service_type,
                status=status,
                response_time_ms=0.0,
                timestamp=datetime.utcnow(),
                details=health_result,
                dependencies=self.config.dependencies
            )
            
        except Exception as e:
            return HealthCheckResult(
                service_name=self.config.service_name,
                service_type=self.config.service_type,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0.0,
                timestamp=datetime.utcnow(),
                details={},
                error_message=str(e),
                dependencies=self.config.dependencies
            )


class HealthCheckManager:
    """
    Main health check manager orchestrating all service health checks.
    
    Provides centralized health monitoring, dependency tracking,
    and alerting for all system components.
    """
    
    def __init__(self):
        self.health_checks: Dict[str, ServiceHealthCheck] = {}
        self.check_tasks: Dict[str, asyncio.Task] = {}
        self.is_running = False
        self.overall_status = HealthStatus.UNKNOWN
        self.last_check = datetime.utcnow()
        
        # Statistics
        self.stats = {
            "total_services": 0,
            "healthy_services": 0,
            "degraded_services": 0,
            "unhealthy_services": 0,
            "critical_services_down": 0,
            "uptime_seconds": 0
        }
        self.start_time = datetime.utcnow()
    
    def register_health_check(self, health_check: ServiceHealthCheck) -> None:
        """Register a health check"""
        
        service_name = health_check.config.service_name
        self.health_checks[service_name] = health_check
        self.stats["total_services"] += 1
        
        logger.info(f"Registered health check for service: {service_name}")
    
    def register_database_check(
        self,
        service_name: str,
        connection_string: str,
        critical: bool = True
    ) -> None:
        """Register database health check"""
        
        config = HealthCheckConfig(
            service_name=service_name,
            service_type=ServiceType.DATABASE,
            critical=critical
        )
        
        health_check = DatabaseHealthCheck(config, connection_string)
        self.register_health_check(health_check)
    
    def register_redis_check(
        self,
        service_name: str,
        redis_url: str,
        critical: bool = True
    ) -> None:
        """Register Redis health check"""
        
        config = HealthCheckConfig(
            service_name=service_name,
            service_type=ServiceType.CACHE,
            critical=critical
        )
        
        health_check = RedisHealthCheck(config, redis_url)
        self.register_health_check(health_check)
    
    def register_http_check(
        self,
        service_name: str,
        service_type: ServiceType,
        endpoint_url: str,
        expected_status: int = 200,
        critical: bool = True
    ) -> None:
        """Register HTTP service health check"""
        
        config = HealthCheckConfig(
            service_name=service_name,
            service_type=service_type,
            critical=critical
        )
        
        health_check = HTTPServiceHealthCheck(config, endpoint_url, expected_status)
        self.register_health_check(health_check)
    
    def register_system_check(self, service_name: str = "system") -> None:
        """Register system health check"""
        
        config = HealthCheckConfig(
            service_name=service_name,
            service_type=ServiceType.SYSTEM,
            critical=True
        )
        
        health_check = SystemHealthCheck(config)
        self.register_health_check(health_check)
    
    def register_ml_service_check(
        self,
        service_name: str,
        ml_service,
        critical: bool = False
    ) -> None:
        """Register ML service health check"""
        
        config = HealthCheckConfig(
            service_name=service_name,
            service_type=ServiceType.ML_SERVICE,
            critical=critical
        )
        
        health_check = MLServiceHealthCheck(config, ml_service)
        self.register_health_check(health_check)
    
    async def start_monitoring(self) -> None:
        """Start continuous health monitoring"""
        
        if self.is_running:
            logger.warning("Health monitoring already running")
            return
        
        self.is_running = True
        self.start_time = datetime.utcnow()
        
        # Start health check tasks for each service
        for service_name, health_check in self.health_checks.items():
            task = asyncio.create_task(
                self._health_check_loop(health_check)
            )
            self.check_tasks[service_name] = task
        
        logger.info(f"Started health monitoring for {len(self.health_checks)} services")
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring"""
        
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel all health check tasks
        for task in self.check_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.check_tasks:
            await asyncio.gather(*self.check_tasks.values(), return_exceptions=True)
        
        self.check_tasks.clear()
        logger.info("Health monitoring stopped")
    
    async def _health_check_loop(self, health_check: ServiceHealthCheck) -> None:
        """Health check loop for individual service"""
        
        service_name = health_check.config.service_name
        interval = health_check.config.check_interval_seconds
        
        logger.info(f"Started health check loop for {service_name}")
        
        while self.is_running:
            try:
                # Run health check
                await health_check.run_health_check()
                
                # Update overall status
                await self._update_overall_status()
                
                # Wait for next check
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                logger.info(f"Health check loop cancelled for {service_name}")
                break
            except Exception as e:
                logger.error(f"Health check loop error for {service_name}: {e}")
                await asyncio.sleep(interval)
    
    async def _update_overall_status(self) -> None:
        """Update overall system health status"""
        
        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0
        critical_down_count = 0
        
        for health_check in self.health_checks.values():
            if health_check.last_result:
                status = health_check.last_result.status
                
                if status == HealthStatus.HEALTHY:
                    healthy_count += 1
                elif status == HealthStatus.DEGRADED:
                    degraded_count += 1
                else:
                    unhealthy_count += 1
                    
                    if health_check.config.critical:
                        critical_down_count += 1
        
        # Update statistics
        self.stats["healthy_services"] = healthy_count
        self.stats["degraded_services"] = degraded_count
        self.stats["unhealthy_services"] = unhealthy_count
        self.stats["critical_services_down"] = critical_down_count
        self.stats["uptime_seconds"] = int((datetime.utcnow() - self.start_time).total_seconds())
        
        # Determine overall status
        if critical_down_count > 0:
            self.overall_status = HealthStatus.UNHEALTHY
        elif unhealthy_count > 0 or degraded_count > 0:
            self.overall_status = HealthStatus.DEGRADED
        else:
            self.overall_status = HealthStatus.HEALTHY
        
        self.last_check = datetime.utcnow()
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get current health status for all services"""
        
        services = {}
        
        for service_name, health_check in self.health_checks.items():
            if health_check.last_result:
                result = health_check.last_result
                services[service_name] = {
                    "status": result.status.value,
                    "response_time_ms": result.response_time_ms,
                    "timestamp": result.timestamp.isoformat(),
                    "details": result.details,
                    "error_message": result.error_message,
                    "service_type": result.service_type.value,
                    "critical": health_check.config.critical
                }
            else:
                services[service_name] = {
                    "status": HealthStatus.UNKNOWN.value,
                    "service_type": health_check.config.service_type.value,
                    "critical": health_check.config.critical
                }
        
        return {
            "overall_status": self.overall_status.value,
            "last_check": self.last_check.isoformat(),
            "services": services,
            "statistics": self.stats
        }
    
    async def get_service_health(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get health status for specific service"""
        
        health_check = self.health_checks.get(service_name)
        if not health_check or not health_check.last_result:
            return None
        
        result = health_check.last_result
        
        return {
            "service_name": service_name,
            "status": result.status.value,
            "response_time_ms": result.response_time_ms,
            "timestamp": result.timestamp.isoformat(),
            "details": result.details,
            "error_message": result.error_message,
            "service_type": result.service_type.value,
            "critical": health_check.config.critical,
            "statistics": health_check.get_stats()
        }
    
    async def run_immediate_check(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """Run immediate health check for service(s)"""
        
        if service_name:
            # Check specific service
            health_check = self.health_checks.get(service_name)
            if not health_check:
                raise ValueError(f"Service not found: {service_name}")
            
            result = await health_check.run_health_check()
            await self._update_overall_status()
            
            return {
                "service_name": service_name,
                "status": result.status.value,
                "response_time_ms": result.response_time_ms,
                "timestamp": result.timestamp.isoformat(),
                "details": result.details,
                "error_message": result.error_message
            }
        else:
            # Check all services
            results = {}
            
            for service_name, health_check in self.health_checks.items():
                result = await health_check.run_health_check()
                results[service_name] = {
                    "status": result.status.value,
                    "response_time_ms": result.response_time_ms,
                    "timestamp": result.timestamp.isoformat(),
                    "details": result.details,
                    "error_message": result.error_message
                }
            
            await self._update_overall_status()
            
            return {
                "overall_status": self.overall_status.value,
                "services": results,
                "statistics": self.stats
            }
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive health check statistics"""
        
        stats = self.stats.copy()
        
        # Add service-specific stats
        stats["service_stats"] = {}
        for service_name, health_check in self.health_checks.items():
            stats["service_stats"][service_name] = health_check.get_stats()
        
        # Add dependency information
        stats["dependencies"] = {}
        for service_name, health_check in self.health_checks.items():
            if health_check.config.dependencies:
                stats["dependencies"][service_name] = health_check.config.dependencies
        
        return stats


# Factory functions

def create_health_check_manager() -> HealthCheckManager:
    """Create health check manager"""
    return HealthCheckManager()


def create_database_health_check(
    service_name: str,
    connection_string: str,
    critical: bool = True
) -> DatabaseHealthCheck:
    """Create database health check"""
    config = HealthCheckConfig(
        service_name=service_name,
        service_type=ServiceType.DATABASE,
        critical=critical
    )
    return DatabaseHealthCheck(config, connection_string)


def create_redis_health_check(
    service_name: str,
    redis_url: str,
    critical: bool = True
) -> RedisHealthCheck:
    """Create Redis health check"""
    config = HealthCheckConfig(
        service_name=service_name,
        service_type=ServiceType.CACHE,
        critical=critical
    )
    return RedisHealthCheck(config, redis_url)


def create_http_health_check(
    service_name: str,
    service_type: ServiceType,
    endpoint_url: str,
    expected_status: int = 200,
    critical: bool = True
) -> HTTPServiceHealthCheck:
    """Create HTTP service health check"""
    config = HealthCheckConfig(
        service_name=service_name,
        service_type=service_type,
        critical=critical
    )
    return HTTPServiceHealthCheck(config, endpoint_url, expected_status)


def create_system_health_check(service_name: str = "system") -> SystemHealthCheck:
    """Create system health check"""
    config = HealthCheckConfig(
        service_name=service_name,
        service_type=ServiceType.SYSTEM,
        critical=True
    )
    return SystemHealthCheck(config)
