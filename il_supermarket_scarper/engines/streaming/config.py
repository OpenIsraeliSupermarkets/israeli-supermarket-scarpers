"""Configuration classes for streaming infrastructure."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union
from enum import Enum


class StorageType(Enum):
    """Supported storage types."""
    DISK = "disk"
    QUEUE = "queue"
    COMPOSITE = "composite"


@dataclass
class StreamingConfig:
    """Configuration for streaming pipeline stages."""
    # Pipeline capacity limits
    link_discovery_cap: int = 100
    processing_cap: int = 50
    download_cap: int = 30
    storage_cap: int = 30  # Match download workers to prevent storage bottleneck
    
    # Queue sizes
    queue_size: int = 200
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Timeout configuration
    worker_timeout: float = 1.0
    shutdown_timeout: float = 5.0
    
    # Backpressure handling
    enable_backpressure: bool = True
    backpressure_threshold: float = 0.8  # Queue full percentage
    
    def validate(self) -> bool:
        """Validate configuration parameters."""
        if self.link_discovery_cap <= 0:
            raise ValueError("link_discovery_cap must be positive")
        if self.processing_cap <= 0:
            raise ValueError("processing_cap must be positive")
        if self.download_cap <= 0:
            raise ValueError("download_cap must be positive")
        if self.storage_cap <= 0:
            raise ValueError("storage_cap must be positive")
        if self.queue_size <= 0:
            raise ValueError("queue_size must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")
        return True


@dataclass 
class StorageConfig:
    """Configuration for storage backends."""
    storage_type: StorageType = StorageType.DISK
    config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate storage configuration after initialization."""
        if self.storage_type == StorageType.DISK:
            if 'output_dir' not in self.config:
                raise ValueError("Disk storage requires 'output_dir' in config")
        elif self.storage_type == StorageType.QUEUE:
            if 'queue_handler' not in self.config:
                raise ValueError("Queue storage requires 'queue_handler' in config")


@dataclass
class WebStreamingConfig:
    """Complete configuration for web streaming engine."""
    streaming: StreamingConfig = field(default_factory=StreamingConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    
    # Web-specific settings
    max_threads: int = 5
    max_retry: int = 2
    timeout: int = 30
    
    # Filtering options
    enable_filtering: bool = True
    filter_null: bool = True
    filter_zero: bool = True
    
    def validate(self) -> bool:
        """Validate the complete configuration."""
        self.streaming.validate()
        
        if self.max_threads <= 0:
            raise ValueError("max_threads must be positive")
        if self.max_retry < 0:
            raise ValueError("max_retry must be non-negative")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
            
        return True
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'WebStreamingConfig':
        """Create configuration from dictionary."""
        streaming_config = StreamingConfig(**config_dict.get('streaming', {}))
        storage_config = StorageConfig(**config_dict.get('storage', {}))
        
        web_config = cls(
            streaming=streaming_config,
            storage=storage_config
        )
        
        # Override web-specific settings
        for key, value in config_dict.items():
            if key not in ['streaming', 'storage'] and hasattr(web_config, key):
                setattr(web_config, key, value)
                
        return web_config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'streaming': {
                'link_discovery_cap': self.streaming.link_discovery_cap,
                'processing_cap': self.streaming.processing_cap,
                'download_cap': self.streaming.download_cap,
                'storage_cap': self.streaming.storage_cap,
                'queue_size': self.streaming.queue_size,
                'max_retries': self.streaming.max_retries,
                'retry_delay': self.streaming.retry_delay,
                'worker_timeout': self.streaming.worker_timeout,
                'shutdown_timeout': self.streaming.shutdown_timeout,
                'enable_backpressure': self.streaming.enable_backpressure,
                'backpressure_threshold': self.streaming.backpressure_threshold,
            },
            'storage': {
                'storage_type': self.storage.storage_type.value,
                'config': self.storage.config
            },
            'max_threads': self.max_threads,
            'max_retry': self.max_retry,
            'timeout': self.timeout,
            'enable_filtering': self.enable_filtering,
            'filter_null': self.filter_null,
            'filter_zero': self.filter_zero,
        }
