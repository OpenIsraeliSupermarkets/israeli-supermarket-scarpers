"""Bounded queues and streaming pipeline infrastructure."""

import asyncio
import threading
from typing import Any, Optional, Callable, Dict, List
from queue import Queue, Full, Empty
from dataclasses import dataclass
from il_supermarket_scarper.utils import Logger


class BoundedQueue:
    """Thread-safe bounded queue with backpressure handling."""
    
    def __init__(self, maxsize: int = 100):
        self.maxsize = maxsize
        self._queue = Queue(maxsize=maxsize)
        self._closed = False
        
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> bool:
        """Put an item into the queue. Returns False if queue is closed."""
        if self._closed:
            return False
            
        try:
            self._queue.put(item, block=block, timeout=timeout)
            return True
        except Full:
            Logger.warning(f"Queue is full (size: {self.qsize()}), applying backpressure")
            return False
            
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Any]:
        """Get an item from the queue. Returns None if queue is empty and closed."""
        try:
            return self._queue.get(block=block, timeout=timeout)
        except Empty:
            if self._closed:
                return None
            raise
            
    def qsize(self) -> int:
        """Return the current queue size."""
        return self._queue.qsize()
        
    def empty(self) -> bool:
        """Return True if the queue is empty."""
        return self._queue.empty()
        
    def full(self) -> bool:
        """Return True if the queue is full."""
        return self._queue.full()
        
    def close(self):
        """Close the queue to new items."""
        self._closed = True
        
    def is_closed(self) -> bool:
        """Return True if the queue is closed."""
        return self._closed


@dataclass
class StreamingConfig:
    """Configuration for streaming pipeline stages."""
    link_discovery_cap: int = 100
    processing_cap: int = 50
    download_cap: int = 30
    storage_cap: int = 30
    queue_size: int = 200
    max_retries: int = 3
    retry_delay: float = 1.0


class StreamingPipeline:
    """Manages the streaming pipeline with multiple stages."""
    
    def __init__(self, config: StreamingConfig):
        self.config = config
        self.link_queue = BoundedQueue(maxsize=config.queue_size)
        self.processing_queue = BoundedQueue(maxsize=config.queue_size)
        self.download_queue = BoundedQueue(maxsize=config.queue_size)
        self.storage_queue = BoundedQueue(maxsize=config.queue_size)
        
        # Worker pools
        self._link_workers: List[threading.Thread] = []
        self._processing_workers: List[threading.Thread] = []
        self._download_workers: List[threading.Thread] = []
        self._storage_workers: List[threading.Thread] = []
        
        # Control flags
        self._running = False
        self._stats = {
            'links_discovered': 0,
            'items_processed': 0,
            'items_downloaded': 0,
            'items_stored': 0,
            'errors': 0
        }
        
    def start(self):
        """Start the streaming pipeline."""
        self._running = True
        Logger.info("Starting streaming pipeline")
        
        # Start worker threads for each stage
        self._start_workers()
        
    def stop(self):
        """Stop the streaming pipeline gracefully."""
        Logger.info("Stopping streaming pipeline")
        self._running = False
        
        # Close all queues
        self.link_queue.close()
        self.processing_queue.close()
        self.download_queue.close()
        self.storage_queue.close()
        
        # Wait for workers to finish
        self._stop_workers()
        
    def _start_workers(self):
        """Start worker threads for each pipeline stage."""
        # Download workers - directly consume from link queue for better performance
        for i in range(self.config.download_cap):
            worker = threading.Thread(
                target=self._optimized_download_worker,
                name=f"download-{i}",
                daemon=True
            )
            worker.start()
            self._download_workers.append(worker)
            
        # Storage workers
        for i in range(self.config.storage_cap):
            worker = threading.Thread(
                target=self._storage_worker,
                name=f"storage-{i}",
                daemon=True
            )
            worker.start()
            self._storage_workers.append(worker)
            
    def _stop_workers(self):
        """Stop all worker threads."""
        for workers in [self._processing_workers, self._download_workers, self._storage_workers]:
            for worker in workers:
                if worker.is_alive():
                    worker.join(timeout=5.0)
    
    def _optimized_download_worker(self):
        """Optimized worker that combines processing and downloading in one step."""
        while self._running:
            try:
                item = self.link_queue.get(timeout=0.01)
                if item is None:
                    continue
                
                # Process the item inline (avoids queue hop)
                processed_item = self._process_item(item)
                if not processed_item:
                    continue
                    
                self._stats['items_processed'] += 1
                
                # Download the item immediately
                # Handle both sync and async _download_item methods
                result = self._download_item(processed_item)
                if asyncio.iscoroutine(result):
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Can't use asyncio.run() with running loop
                            downloaded_item = asyncio.run_coroutine_threadsafe(result, loop).result()
                        else:
                            downloaded_item = loop.run_until_complete(result)
                    except RuntimeError:
                        # No event loop in thread, create new one
                        downloaded_item = asyncio.run(result)
                else:
                    downloaded_item = result
                
                if downloaded_item and not self.download_queue.put(downloaded_item, timeout=0.01):
                    Logger.warning("Download queue full, dropping item")
                    
                self._stats['items_downloaded'] += 1
                
            except Empty:
                continue
            except Exception as e:
                Logger.error(f"Error in optimized download worker: {e}")
                self._stats['errors'] += 1
                
    def _storage_worker(self):
        """Worker thread for storage stage."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            while self._running or not self.download_queue.empty():
                try:
                    item = self.download_queue.get(timeout=0.01)
                    if item is None:
                        if not self._running:
                            break
                        continue

                    # Store the item (to be implemented by subclass)
                    self._store_item(item)
                    self._stats['items_stored'] += 1

                except Empty:
                    if not self._running:
                        break
                    continue
                except Exception as e:
                    Logger.error(f"Error in storage worker: {e}")
                    self._stats['errors'] += 1
        finally:
            try:
                loop.close()
            except Exception:
                pass
                
    def _process_item(self, item: Any) -> Optional[Any]:
        """Process a single item. To be overridden by subclasses."""
        return item
        
    def _download_item(self, item: Any) -> Optional[Any]:
        """Download a single item. To be overridden by subclasses."""
        return item
        
    def _store_item(self, item: Any):
        """Store a single item. To be overridden by subclasses."""
        pass
        
    def get_stats(self) -> Dict[str, int]:
        """Get current pipeline statistics."""
        return self._stats.copy()
        
    def add_link(self, link: Any) -> bool:
        """Add a link to the pipeline for processing."""
        if self.link_queue.put(link, block=False):
            self._stats['links_discovered'] += 1
            return True
        return False
