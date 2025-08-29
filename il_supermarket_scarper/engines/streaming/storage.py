"""Storage interface and implementations for streaming data."""

import os
import json
import time
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from il_supermarket_scarper.utils import Logger


class StorageInterface(ABC):
    """Abstract interface for different storage backends."""
    
    @abstractmethod
    async def store(self, data: Any) -> bool:
        """Store data. Returns True if successful."""
        pass
        
    @abstractmethod
    async def close(self):
        """Close the storage backend."""
        pass


class DiskStorage(StorageInterface):
    """File system storage implementation."""
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self._ensure_directory()
        
    def _ensure_directory(self):
        """Ensure the output directory exists."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
            
    async def store(self, data: Any) -> bool:
        """Store data to disk."""
        try:
            if isinstance(data, dict):
                # Check if this is download result data (already saved by save_and_extract)
                if 'download_result' in data and data.get('content') == '':
                    # File was already saved by save_and_extract, just log success
                    Logger.debug(f"File already saved by download process: {data.get('file_name', 'unknown')}")
                    return True
                
                # Handle structured data
                file_name = data.get('file_name', f'data_{int(time.time() * 1000)}.xml')
                content = data.get('content', '')
                
                if not file_name.endswith('.xml'):
                    file_name += '.xml'
                    
            else:
                # Handle raw content
                file_name = f'data_{int(time.time() * 1000)}.xml'
                content = str(data)
                
            file_path = os.path.join(self.output_dir, file_name)
            
            # Write content to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            Logger.debug(f"Stored data to {file_path}")
            return True
            
        except Exception as e:
            Logger.error(f"Error storing data to disk: {e}")
            return False
            
    async def close(self):
        """Close disk storage (no-op for disk)."""
        Logger.debug("Disk storage closed")


class QueueStorage(StorageInterface):
    """Queue-based storage implementation."""
    
    def __init__(self, queue_handler: Any):
        self.queue_handler = queue_handler
        self._closed = False
        
    async def store(self, data: Any) -> bool:
        """Store data to queue."""
        if self._closed:
            return False
            
        try:
            # Convert data to JSON for queue storage
            if isinstance(data, dict):
                queue_data = data
            else:
                queue_data = {
                    'content': str(data),
                    'timestamp': int(time.time() * 1000)
                }
                
            # Send to queue handler
            await self._send_to_queue(queue_data)
            Logger.debug(f"Stored data to queue")
            return True
            
        except Exception as e:
            Logger.error(f"Error storing data to queue: {e}")
            return False
            
    async def _send_to_queue(self, data: Dict[str, Any]):
        """Send data to the queue handler."""
        if hasattr(self.queue_handler, 'publish'):
            # Async queue handler
            await self.queue_handler.publish(data)
        elif hasattr(self.queue_handler, 'put'):
            # Sync queue handler
            self.queue_handler.put(json.dumps(data))
        else:
            # Generic handler - try to call it
            await self.queue_handler(data)
            
    async def close(self):
        """Close queue storage."""
        self._closed = True
        if hasattr(self.queue_handler, 'close'):
            await self.queue_handler.close()
        Logger.debug("Queue storage closed")


class CompositeStorage(StorageInterface):
    """Storage that can write to multiple backends simultaneously."""
    
    def __init__(self, storages: list[StorageInterface]):
        self.storages = storages
        
    async def store(self, data: Any) -> bool:
        """Store data to all configured storages."""
        results = []
        for storage in self.storages:
            try:
                result = await storage.store(data)
                results.append(result)
            except Exception as e:
                Logger.error(f"Error in composite storage: {e}")
                results.append(False)
                
        # Return True if at least one storage succeeded
        return any(results)
        
    async def close(self):
        """Close all storages."""
        for storage in self.storages:
            try:
                await storage.close()
            except Exception as e:
                Logger.error(f"Error closing storage: {e}")


class RetryStorage(StorageInterface):
    """Storage wrapper that adds retry logic."""
    
    def __init__(self, storage: StorageInterface, max_retries: int = 3, retry_delay: float = 1.0):
        self.storage = storage
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
    async def store(self, data: Any) -> bool:
        """Store data with retry logic."""
        for attempt in range(self.max_retries + 1):
            try:
                if await self.storage.store(data):
                    return True
            except Exception as e:
                Logger.warning(f"Storage attempt {attempt + 1} failed: {e}")
                
            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_delay)
                
        Logger.error(f"All storage attempts failed after {self.max_retries + 1} tries")
        return False
        
    async def close(self):
        """Close the underlying storage."""
        await self.storage.close()
