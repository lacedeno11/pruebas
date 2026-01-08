"""
Queue Management

This module implements queue management for asynchronous processing and task distribution,
supporting multiple queue backends (Redis, RabbitMQ, etc.).
"""

from typing import Dict, Any, List, Optional, Callable, Awaitable, Union
from datetime import datetime, timedelta
import logging
import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from enum import Enum
import pickle
import base64

logger = logging.getLogger(__name__)


class QueueBackend(str, Enum):
    """Queue backend types"""
    REDIS = "redis"
    RABBITMQ = "rabbitmq"
    MEMORY = "memory"
    SQS = "sqs"


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class QueueConfig:
    """Queue configuration"""
    backend: QueueBackend
    connection_url: Optional[str] = None
    host: str = "localhost"
    port: int = 6379
    username: Optional[str] = None
    password: Optional[str] = None
    database: int = 0
    queue_prefix: str = "policy_copilot"
    max_retries: int = 3
    retry_delay_seconds: int = 60
    task_timeout_seconds: int = 300
    dead_letter_queue: bool = True
    batch_size: int = 10


@dataclass
class QueueTask:
    """Queue task definition"""
    id: str
    queue_name: str
    task_type: str
    payload: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class QueueStats:
    """Queue statistics"""
    queue_name: str
    pending_tasks: int
    processing_tasks: int
    completed_tasks: int
    failed_tasks: int
    total_tasks: int
    avg_processing_time_ms: float
    last_updated: datetime


class TaskHandler:
    """Task handler for processing queue tasks"""
    
    def __init__(self, task_type: str, handler_func: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]):
        self.task_type = task_type
        self.handler_func = handler_func
        self.stats = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "avg_processing_time_ms": 0
        }
    
    async def process_task(self, task: QueueTask) -> QueueTask:
        """Process a queue task"""
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Processing task {task.id} of type {task.task_type}")
            
            # Update task status
            task.status = TaskStatus.PROCESSING
            task.started_at = start_time
            
            # Execute handler
            result = await self.handler_func(task.payload)
            
            # Update task with result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.result = result
            
            # Update statistics
            processing_time = (task.completed_at - start_time).total_seconds() * 1000
            self._update_stats(processing_time, True)
            
            logger.info(f"Task {task.id} completed successfully in {processing_time:.2f}ms")
            
            return task
            
        except Exception as e:
            # Update task with error
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            task.error_message = str(e)
            
            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._update_stats(processing_time, False)
            
            logger.error(f"Task {task.id} failed: {e}")
            
            return task
    
    def _update_stats(self, processing_time_ms: float, success: bool) -> None:
        """Update handler statistics"""
        self.stats["processed"] += 1
        
        if success:
            self.stats["succeeded"] += 1
        else:
            self.stats["failed"] += 1
        
        # Update average processing time
        current_avg = self.stats["avg_processing_time_ms"]
        total_processed = self.stats["processed"]
        new_avg = ((current_avg * (total_processed - 1)) + processing_time_ms) / total_processed
        self.stats["avg_processing_time_ms"] = new_avg


class QueueAdapter(ABC):
    """Abstract base class for queue adapters"""
    
    def __init__(self, config: QueueConfig):
        self.config = config
        self.stats = {
            "tasks_enqueued": 0,
            "tasks_dequeued": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "connection_errors": 0
        }
    
    @abstractmethod
    async def enqueue_task(self, task: QueueTask) -> bool:
        """Enqueue a task"""
        pass
    
    @abstractmethod
    async def dequeue_task(self, queue_name: str) -> Optional[QueueTask]:
        """Dequeue a task"""
        pass
    
    @abstractmethod
    async def update_task_status(self, task: QueueTask) -> bool:
        """Update task status"""
        pass
    
    @abstractmethod
    async def get_queue_stats(self, queue_name: str) -> QueueStats:
        """Get queue statistics"""
        pass
    
    @abstractmethod
    async def list_queues(self) -> List[str]:
        """List all queues"""
        pass
    
    @abstractmethod
    async def purge_queue(self, queue_name: str) -> int:
        """Purge all tasks from queue"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check queue backend health"""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics"""
        return self.stats.copy()


class RedisQueueAdapter(QueueAdapter):
    """
    Redis queue adapter implementation.
    
    Uses Redis lists and hashes for task storage and management.
    """
    
    def __init__(self, config: QueueConfig):
        super().__init__(config)
        
        if config.backend != QueueBackend.REDIS:
            raise ValueError("RedisQueueAdapter requires REDIS backend configuration")
        
        self.redis_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Redis client"""
        try:
            import redis.asyncio as redis
            
            if self.config.connection_url:
                self.redis_client = redis.from_url(self.config.connection_url)
            else:
                self.redis_client = redis.Redis(
                    host=self.config.host,
                    port=self.config.port,
                    username=self.config.username,
                    password=self.config.password,
                    db=self.config.database,
                    decode_responses=False  # We'll handle encoding ourselves
                )
            
            logger.info("Redis queue client initialized")
            
        except ImportError:
            logger.error("Redis library not installed. Install with: pip install redis")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            raise
    
    def _get_queue_key(self, queue_name: str) -> str:
        """Get Redis key for queue"""
        return f"{self.config.queue_prefix}:queue:{queue_name}"
    
    def _get_task_key(self, task_id: str) -> str:
        """Get Redis key for task data"""
        return f"{self.config.queue_prefix}:task:{task_id}"
    
    def _get_processing_key(self, queue_name: str) -> str:
        """Get Redis key for processing tasks"""
        return f"{self.config.queue_prefix}:processing:{queue_name}"
    
    def _serialize_task(self, task: QueueTask) -> bytes:
        """Serialize task to bytes"""
        task_dict = asdict(task)
        # Convert datetime objects to ISO strings
        for key, value in task_dict.items():
            if isinstance(value, datetime):
                task_dict[key] = value.isoformat() if value else None
        
        return pickle.dumps(task_dict)
    
    def _deserialize_task(self, data: bytes) -> QueueTask:
        """Deserialize task from bytes"""
        task_dict = pickle.loads(data)
        
        # Convert ISO strings back to datetime objects
        datetime_fields = ['created_at', 'scheduled_at', 'expires_at', 'started_at', 'completed_at']
        for field in datetime_fields:
            if task_dict.get(field):
                task_dict[field] = datetime.fromisoformat(task_dict[field])
        
        # Convert enums
        task_dict['priority'] = TaskPriority(task_dict['priority'])
        task_dict['status'] = TaskStatus(task_dict['status'])
        
        return QueueTask(**task_dict)
    
    async def enqueue_task(self, task: QueueTask) -> bool:
        """Enqueue task in Redis"""
        try:
            # Serialize task
            task_data = self._serialize_task(task)
            
            # Store task data
            task_key = self._get_task_key(task.id)
            await self.redis_client.set(task_key, task_data)
            
            # Add to appropriate queue based on priority and scheduling
            if task.scheduled_at and task.scheduled_at > datetime.utcnow():
                # Scheduled task - add to delayed queue
                delay_key = f"{self.config.queue_prefix}:delayed"
                score = task.scheduled_at.timestamp()
                await self.redis_client.zadd(delay_key, {task.id: score})
            else:
                # Immediate task - add to priority queue
                queue_key = self._get_queue_key(task.queue_name)
                
                # Use priority as score (higher priority = lower score for ZPOP)
                priority_scores = {
                    TaskPriority.CRITICAL: 0,
                    TaskPriority.HIGH: 1,
                    TaskPriority.NORMAL: 2,
                    TaskPriority.LOW: 3
                }
                score = priority_scores.get(task.priority, 2)
                
                await self.redis_client.zadd(queue_key, {task.id: score})
            
            self.stats["tasks_enqueued"] += 1
            logger.info(f"Task {task.id} enqueued to {task.queue_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue task: {e}")
            self.stats["connection_errors"] += 1
            return False
    
    async def dequeue_task(self, queue_name: str) -> Optional[QueueTask]:
        """Dequeue task from Redis"""
        try:
            queue_key = self._get_queue_key(queue_name)
            processing_key = self._get_processing_key(queue_name)
            
            # Get highest priority task
            result = await self.redis_client.zpopmin(queue_key, 1)
            
            if not result:
                return None
            
            task_id, _ = result[0]
            task_id = task_id.decode('utf-8') if isinstance(task_id, bytes) else task_id
            
            # Get task data
            task_key = self._get_task_key(task_id)
            task_data = await self.redis_client.get(task_key)
            
            if not task_data:
                logger.warning(f"Task data not found for ID: {task_id}")
                return None
            
            # Deserialize task
            task = self._deserialize_task(task_data)
            
            # Move to processing queue
            await self.redis_client.zadd(processing_key, {task_id: datetime.utcnow().timestamp()})
            
            self.stats["tasks_dequeued"] += 1
            logger.info(f"Task {task.id} dequeued from {queue_name}")
            
            return task
            
        except Exception as e:
            logger.error(f"Failed to dequeue task: {e}")
            self.stats["connection_errors"] += 1
            return None
    
    async def update_task_status(self, task: QueueTask) -> bool:
        """Update task status in Redis"""
        try:
            # Update task data
            task_key = self._get_task_key(task.id)
            task_data = self._serialize_task(task)
            await self.redis_client.set(task_key, task_data)
            
            # Remove from processing queue if completed or failed
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                processing_key = self._get_processing_key(task.queue_name)
                await self.redis_client.zrem(processing_key, task.id)
                
                # Update statistics
                if task.status == TaskStatus.COMPLETED:
                    self.stats["tasks_completed"] += 1
                elif task.status == TaskStatus.FAILED:
                    self.stats["tasks_failed"] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            self.stats["connection_errors"] += 1
            return False
    
    async def get_queue_stats(self, queue_name: str) -> QueueStats:
        """Get queue statistics from Redis"""
        try:
            queue_key = self._get_queue_key(queue_name)
            processing_key = self._get_processing_key(queue_name)
            
            # Get counts
            pending_tasks = await self.redis_client.zcard(queue_key)
            processing_tasks = await self.redis_client.zcard(processing_key)
            
            # Get completed/failed counts from task data (simplified)
            # In production, would maintain separate counters
            completed_tasks = self.stats["tasks_completed"]
            failed_tasks = self.stats["tasks_failed"]
            total_tasks = pending_tasks + processing_tasks + completed_tasks + failed_tasks
            
            return QueueStats(
                queue_name=queue_name,
                pending_tasks=pending_tasks,
                processing_tasks=processing_tasks,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                total_tasks=total_tasks,
                avg_processing_time_ms=0.0,  # Would calculate from task data
                last_updated=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return QueueStats(
                queue_name=queue_name,
                pending_tasks=0,
                processing_tasks=0,
                completed_tasks=0,
                failed_tasks=0,
                total_tasks=0,
                avg_processing_time_ms=0.0,
                last_updated=datetime.utcnow()
            )
    
    async def list_queues(self) -> List[str]:
        """List all queues in Redis"""
        try:
            pattern = f"{self.config.queue_prefix}:queue:*"
            keys = await self.redis_client.keys(pattern)
            
            # Extract queue names
            queue_names = []
            prefix_len = len(f"{self.config.queue_prefix}:queue:")
            
            for key in keys:
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                queue_name = key[prefix_len:]
                queue_names.append(queue_name)
            
            return queue_names
            
        except Exception as e:
            logger.error(f"Failed to list queues: {e}")
            return []
    
    async def purge_queue(self, queue_name: str) -> int:
        """Purge all tasks from Redis queue"""
        try:
            queue_key = self._get_queue_key(queue_name)
            processing_key = self._get_processing_key(queue_name)
            
            # Get all task IDs
            pending_ids = await self.redis_client.zrange(queue_key, 0, -1)
            processing_ids = await self.redis_client.zrange(processing_key, 0, -1)
            
            all_ids = pending_ids + processing_ids
            
            # Delete task data
            if all_ids:
                task_keys = [self._get_task_key(task_id.decode('utf-8') if isinstance(task_id, bytes) else task_id) for task_id in all_ids]
                await self.redis_client.delete(*task_keys)
            
            # Clear queues
            await self.redis_client.delete(queue_key, processing_key)
            
            logger.info(f"Purged {len(all_ids)} tasks from queue {queue_name}")
            return len(all_ids)
            
        except Exception as e:
            logger.error(f"Failed to purge queue: {e}")
            return 0
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            # Test Redis connection
            await self.redis_client.ping()
            
            # Get Redis info
            info = await self.redis_client.info()
            
            return {
                "status": "healthy",
                "backend": "redis",
                "version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "unknown"),
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "redis",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def process_delayed_tasks(self) -> int:
        """Process delayed tasks that are ready to run"""
        try:
            delay_key = f"{self.config.queue_prefix}:delayed"
            current_time = datetime.utcnow().timestamp()
            
            # Get tasks ready to run
            ready_tasks = await self.redis_client.zrangebyscore(delay_key, 0, current_time)
            
            if not ready_tasks:
                return 0
            
            # Move tasks to their respective queues
            moved_count = 0
            for task_id in ready_tasks:
                task_id = task_id.decode('utf-8') if isinstance(task_id, bytes) else task_id
                
                # Get task data
                task_key = self._get_task_key(task_id)
                task_data = await self.redis_client.get(task_key)
                
                if task_data:
                    task = self._deserialize_task(task_data)
                    
                    # Move to regular queue
                    queue_key = self._get_queue_key(task.queue_name)
                    priority_scores = {
                        TaskPriority.CRITICAL: 0,
                        TaskPriority.HIGH: 1,
                        TaskPriority.NORMAL: 2,
                        TaskPriority.LOW: 3
                    }
                    score = priority_scores.get(task.priority, 2)
                    
                    await self.redis_client.zadd(queue_key, {task_id: score})
                    await self.redis_client.zrem(delay_key, task_id)
                    
                    moved_count += 1
            
            if moved_count > 0:
                logger.info(f"Moved {moved_count} delayed tasks to processing queues")
            
            return moved_count
            
        except Exception as e:
            logger.error(f"Failed to process delayed tasks: {e}")
            return 0


class RabbitMQAdapter(QueueAdapter):
    """
    RabbitMQ queue adapter implementation.
    
    Uses RabbitMQ for reliable message queuing with persistence.
    """
    
    def __init__(self, config: QueueConfig):
        super().__init__(config)
        
        if config.backend != QueueBackend.RABBITMQ:
            raise ValueError("RabbitMQAdapter requires RABBITMQ backend configuration")
        
        self.connection = None
        self.channel = None
        # RabbitMQ implementation would go here
        # For brevity, providing interface only
    
    async def enqueue_task(self, task: QueueTask) -> bool:
        """Enqueue task in RabbitMQ"""
        # Implementation would use aio-pika or similar
        logger.warning("RabbitMQ adapter not fully implemented")
        return False
    
    async def dequeue_task(self, queue_name: str) -> Optional[QueueTask]:
        """Dequeue task from RabbitMQ"""
        logger.warning("RabbitMQ adapter not fully implemented")
        return None
    
    async def update_task_status(self, task: QueueTask) -> bool:
        """Update task status in RabbitMQ"""
        logger.warning("RabbitMQ adapter not fully implemented")
        return False
    
    async def get_queue_stats(self, queue_name: str) -> QueueStats:
        """Get queue statistics from RabbitMQ"""
        return QueueStats(
            queue_name=queue_name,
            pending_tasks=0,
            processing_tasks=0,
            completed_tasks=0,
            failed_tasks=0,
            total_tasks=0,
            avg_processing_time_ms=0.0,
            last_updated=datetime.utcnow()
        )
    
    async def list_queues(self) -> List[str]:
        """List all queues in RabbitMQ"""
        return []
    
    async def purge_queue(self, queue_name: str) -> int:
        """Purge all tasks from RabbitMQ queue"""
        return 0
    
    async def health_check(self) -> Dict[str, Any]:
        """Check RabbitMQ health"""
        return {
            "status": "not_implemented",
            "backend": "rabbitmq",
            "last_check": datetime.utcnow().isoformat()
        }


class QueueManager:
    """
    Main queue manager orchestrating task processing.
    
    Provides unified interface for task queuing, processing,
    and monitoring across different queue backends.
    """
    
    def __init__(self, config: QueueConfig):
        self.config = config
        self.adapter = self._create_adapter()
        self.task_handlers: Dict[str, TaskHandler] = {}
        self.worker_tasks: List[asyncio.Task] = []
        self.is_running = False
        
        # Statistics
        self.stats = {
            "total_processed": 0,
            "total_succeeded": 0,
            "total_failed": 0,
            "workers_active": 0,
            "uptime_seconds": 0
        }
        self.start_time = datetime.utcnow()
    
    def _create_adapter(self) -> QueueAdapter:
        """Create queue adapter based on configuration"""
        if self.config.backend == QueueBackend.REDIS:
            return RedisQueueAdapter(self.config)
        elif self.config.backend == QueueBackend.RABBITMQ:
            return RabbitMQAdapter(self.config)
        else:
            raise ValueError(f"Unsupported queue backend: {self.config.backend}")
    
    def register_task_handler(
        self,
        task_type: str,
        handler_func: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
    ) -> None:
        """Register task handler for specific task type"""
        self.task_handlers[task_type] = TaskHandler(task_type, handler_func)
        logger.info(f"Registered task handler for type: {task_type}")
    
    async def enqueue_task(
        self,
        queue_name: str,
        task_type: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        scheduled_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None
    ) -> str:
        """Enqueue a new task"""
        
        task_id = str(uuid.uuid4())
        
        task = QueueTask(
            id=task_id,
            queue_name=queue_name,
            task_type=task_type,
            payload=payload,
            priority=priority,
            scheduled_at=scheduled_at,
            expires_at=expires_at,
            max_retries=self.config.max_retries
        )
        
        success = await self.adapter.enqueue_task(task)
        
        if success:
            logger.info(f"Task {task_id} enqueued to {queue_name}")
            return task_id
        else:
            raise Exception(f"Failed to enqueue task {task_id}")
    
    async def start_workers(self, queue_names: List[str], worker_count: int = 1) -> None:
        """Start worker processes for specified queues"""
        
        if self.is_running:
            logger.warning("Workers already running")
            return
        
        self.is_running = True
        self.start_time = datetime.utcnow()
        
        # Start workers for each queue
        for queue_name in queue_names:
            for i in range(worker_count):
                worker_task = asyncio.create_task(
                    self._worker_loop(queue_name, f"worker-{queue_name}-{i}")
                )
                self.worker_tasks.append(worker_task)
        
        # Start delayed task processor
        delayed_task = asyncio.create_task(self._delayed_task_processor())
        self.worker_tasks.append(delayed_task)
        
        self.stats["workers_active"] = len(self.worker_tasks)
        logger.info(f"Started {len(self.worker_tasks)} workers for queues: {queue_names}")
    
    async def stop_workers(self) -> None:
        """Stop all worker processes"""
        
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel all worker tasks
        for task in self.worker_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        self.worker_tasks.clear()
        self.stats["workers_active"] = 0
        
        logger.info("All workers stopped")
    
    async def _worker_loop(self, queue_name: str, worker_id: str) -> None:
        """Main worker loop for processing tasks"""
        
        logger.info(f"Worker {worker_id} started for queue {queue_name}")
        
        while self.is_running:
            try:
                # Dequeue task
                task = await self.adapter.dequeue_task(queue_name)
                
                if not task:
                    # No tasks available, wait before checking again
                    await asyncio.sleep(1)
                    continue
                
                # Check if task has expired
                if task.expires_at and task.expires_at < datetime.utcnow():
                    task.status = TaskStatus.CANCELLED
                    task.error_message = "Task expired"
                    await self.adapter.update_task_status(task)
                    continue
                
                # Get task handler
                handler = self.task_handlers.get(task.task_type)
                if not handler:
                    task.status = TaskStatus.FAILED
                    task.error_message = f"No handler registered for task type: {task.task_type}"
                    await self.adapter.update_task_status(task)
                    continue
                
                # Process task
                processed_task = await handler.process_task(task)
                
                # Update task status
                await self.adapter.update_task_status(processed_task)
                
                # Handle retries for failed tasks
                if processed_task.status == TaskStatus.FAILED and processed_task.retry_count < processed_task.max_retries:
                    await self._schedule_retry(processed_task)
                
                # Update statistics
                self.stats["total_processed"] += 1
                if processed_task.status == TaskStatus.COMPLETED:
                    self.stats["total_succeeded"] += 1
                else:
                    self.stats["total_failed"] += 1
                
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _delayed_task_processor(self) -> None:
        """Process delayed tasks that are ready to run"""
        
        logger.info("Delayed task processor started")
        
        while self.is_running:
            try:
                if hasattr(self.adapter, 'process_delayed_tasks'):
                    await self.adapter.process_delayed_tasks()
                
                # Check every 30 seconds
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                logger.info("Delayed task processor cancelled")
                break
            except Exception as e:
                logger.error(f"Delayed task processor error: {e}")
                await asyncio.sleep(60)
    
    async def _schedule_retry(self, task: QueueTask) -> None:
        """Schedule task for retry"""
        
        retry_task = QueueTask(
            id=str(uuid.uuid4()),
            queue_name=task.queue_name,
            task_type=task.task_type,
            payload=task.payload,
            priority=task.priority,
            scheduled_at=datetime.utcnow() + timedelta(seconds=self.config.retry_delay_seconds),
            expires_at=task.expires_at,
            retry_count=task.retry_count + 1,
            max_retries=task.max_retries
        )
        
        await self.adapter.enqueue_task(retry_task)
        logger.info(f"Scheduled retry for task {task.id}, attempt {retry_task.retry_count}")
    
    async def get_queue_stats(self, queue_name: str) -> QueueStats:
        """Get statistics for specific queue"""
        return await self.adapter.get_queue_stats(queue_name)
    
    async def get_all_queue_stats(self) -> Dict[str, QueueStats]:
        """Get statistics for all queues"""
        queue_names = await self.adapter.list_queues()
        stats = {}
        
        for queue_name in queue_names:
            stats[queue_name] = await self.adapter.get_queue_stats(queue_name)
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Check queue manager health"""
        adapter_health = await self.adapter.health_check()
        
        # Calculate uptime
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        self.stats["uptime_seconds"] = int(uptime)
        
        return {
            "status": "healthy" if adapter_health["status"] == "healthy" else "degraded",
            "adapter": adapter_health,
            "workers_active": self.stats["workers_active"],
            "is_running": self.is_running,
            "stats": self.stats,
            "last_check": datetime.utcnow().isoformat()
        }
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue manager statistics"""
        
        stats = self.stats.copy()
        stats["adapter_stats"] = self.adapter.get_stats()
        
        # Add handler stats
        stats["handler_stats"] = {}
        for task_type, handler in self.task_handlers.items():
            stats["handler_stats"][task_type] = handler.stats
        
        return stats


# Factory functions

def create_queue_manager(config: QueueConfig) -> QueueManager:
    """Create queue manager with configuration"""
    return QueueManager(config)


def create_redis_queue_config(
    host: str = "localhost",
    port: int = 6379,
    password: Optional[str] = None,
    database: int = 0
) -> QueueConfig:
    """Create Redis queue configuration"""
    return QueueConfig(
        backend=QueueBackend.REDIS,
        host=host,
        port=port,
        password=password,
        database=database
    )


def create_rabbitmq_queue_config(
    host: str = "localhost",
    port: int = 5672,
    username: str = "guest",
    password: str = "guest"
) -> QueueConfig:
    """Create RabbitMQ queue configuration"""
    return QueueConfig(
        backend=QueueBackend.RABBITMQ,
        host=host,
        port=port,
        username=username,
        password=password
    )
