"""Base streaming engine with common functionality."""

import asyncio
import threading
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List, Callable
from il_supermarket_scarper.engines.engine import Engine
from il_supermarket_scarper.utils import Logger
from .queues import BoundedQueue, StreamingPipeline
from .storage import StorageInterface, DiskStorage, QueueStorage
from .config import WebStreamingConfig, StorageType


class StreamingEngine(Engine, ABC):
    """Base class for streaming-enabled scrapers."""
    
    def __init__(self, chain, chain_id, url=None,
                 streaming_config: Optional[WebStreamingConfig] = None):
        # Initialize parent Engine
        max_threads = streaming_config.max_threads if streaming_config else 5
        self.url = url
        super().__init__(chain, chain_id,folder_name=streaming_config.storage.config.get('output_dir', None), max_threads=max_threads)
        
        # Streaming-specific initialization
        self.streaming_config = streaming_config or WebStreamingConfig()
        self.streaming_config.validate()
        
        # Initialize streaming components
        self._pipeline: Optional[StreamingWebPipeline] = None
        self._storage: Optional[StorageInterface] = None
        self._running = False
        
        # Statistics
        self._stats = {
            'links_discovered': 0,
            'items_processed': 0,
            'items_downloaded': 0,
            'items_stored': 0,
            'errors': 0
        }
        
    def _create_storage(self) -> StorageInterface:
        """Create storage backend based on configuration."""
        storage_config = self.streaming_config.storage
        
        # Handle both enum and string values
        storage_type = storage_config.storage_type
        if isinstance(storage_type, StorageType):
            storage_type_value = storage_type.value
        else:
            storage_type_value = storage_type
        
        if storage_type_value == StorageType.DISK.value:
            output_dir = storage_config.config.get('output_dir', self.storage_path)
            # Ensure we use the proper subdirectory (same as parent Engine)
            if hasattr(self, 'storage_path') and self.storage_path:
                output_dir = self.storage_path
            return DiskStorage(output_dir)
        elif storage_type_value == StorageType.QUEUE.value:
            queue_handler = storage_config.config['queue_handler']
            return QueueStorage(queue_handler)
        else:
            raise ValueError(f"Unsupported storage type: {storage_type_value}")
            
    def _create_pipeline(self) -> 'StreamingWebPipeline':
        """Create streaming pipeline."""
        return StreamingWebPipeline(
            config=self.streaming_config.streaming,
            storage=self._storage,
            engine=self
        )
        
    async def start_streaming(self):
        """Start the streaming pipeline."""
        if self._running:
            Logger.warning("Streaming pipeline already running")
            return
            
        Logger.info("Starting streaming pipeline")
        self._storage = self._create_storage()
        self._pipeline = self._create_pipeline()
        self._pipeline.start()
        self._running = True
        
    async def stop_streaming(self):
        """Stop the streaming pipeline."""
        if not self._running:
            return
            
        Logger.info("Stopping streaming pipeline")
        self._running = False
        
        if self._pipeline:
            self._pipeline.stop()
            
        if self._storage:
            await self._storage.close()
            
    def add_link_for_processing(self, link_data: Dict[str, Any]) -> bool:
        """Add a link to the streaming pipeline for processing."""
        if not self._running or not self._pipeline:
            Logger.warning("Pipeline not running, cannot add link")
            return False
            
        return self._pipeline.add_link(link_data)
        
    def get_streaming_stats(self) -> Dict[str, int]:
        """Get current streaming statistics."""
        if self._pipeline:
            return self._pipeline.get_stats()
        return self._stats.copy()
        
    @abstractmethod
    def discover_links_streaming(self, **kwargs) -> List[Dict[str, Any]]:
        """Discover links for streaming processing. To be implemented by subclasses."""
        pass
        
    @abstractmethod 
    def process_link_data(self, link_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single link. To be implemented by subclasses."""
        pass
        
    @abstractmethod
    async def download_item_data(self, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Download a single item. To be implemented by subclasses.""" 
        pass


class StreamingWebPipeline(StreamingPipeline):
    """Web-specific streaming pipeline implementation."""
    
    def __init__(self, config, storage: StorageInterface, engine: StreamingEngine):
        super().__init__(config)
        self.storage = storage
        self.engine = engine
        
    def _process_item(self, item: Any) -> Optional[Any]:
        """Process a single item using the engine."""
        try:
            return self.engine.process_link_data(item)
        except Exception as e:
            Logger.error(f"Error processing item: {e}")
            return None
            
    async def _download_item(self, item: Any) -> Optional[Any]:
        """Download a single item using the engine."""
        try:
            return await self.engine.download_item_data(item)
        except Exception as e:
            Logger.error(f"Error downloading item: {e}")
            return None
            
    def _store_item(self, item: Any):
        """Store a single item using the configured storage."""
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            success = loop.run_until_complete(self.storage.store(item))
            if success:
                Logger.debug("Item stored successfully")
            else:
                Logger.warning("Failed to store item")
        except Exception as e:
            Logger.error(f"Error storing item: {e}")


# Backward compatibility adapter
class StreamingWebAdapter(StreamingEngine):
    """Adapter that makes a streaming engine look like the original WebBase."""
    
    def __init__(self, original_engine, streaming_config: Optional[WebStreamingConfig] = None):
        # Copy attributes from original engine
        super().__init__(
            chain=original_engine.chain,
            chain_id=original_engine.chain_id,
            url=getattr(original_engine, 'url', None),
            folder_name=original_engine.storage_path,
            streaming_config=streaming_config
        )
        
        # Copy methods from original
        self._original = original_engine
        
    def discover_links_streaming(self, **kwargs) -> List[Dict[str, Any]]:
        """Discover links using original engine methods."""
        # Use original engine's link discovery
        download_urls, file_names = self._original.collect_files_details_from_site(**kwargs)
        
        # Convert to streaming format
        links = []
        for url, name in zip(download_urls, file_names):
            links.append({
                'url': url,
                'file_name': name,
                'original_data': (url, name)
            })
        return links
        
    def process_link_data(self, link_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process link data - in web engine, this is usually a pass-through."""
        return link_data
        
    async def download_item_data(self, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Download item using original engine's save_and_extract method."""
        try:
            original_data = item_data['original_data']
            result = self._original.save_and_extract(original_data)
            return {
                'file_name': result['file_name'],
                'content': '',  # Content is already saved by save_and_extract
                'download_result': result
            }
        except Exception as e:
            Logger.error(f"Error downloading item: {e}")
            return None
