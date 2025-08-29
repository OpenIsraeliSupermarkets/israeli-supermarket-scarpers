import asyncio
import threading
from bs4 import BeautifulSoup
from il_supermarket_scarper.utils import Logger, execute_in_parallel
from typing import List, Dict, Any, Optional
from .streaming import StreamingEngine, WebStreamingConfig, StorageType



class WebBase(StreamingEngine):
    """scrape the file of websites that the only why to download them is via web"""

     
    def __init__(self, chain, chain_id, url,
                 streaming_config: Optional[WebStreamingConfig] = None):        
        super().__init__(chain, chain_id, url, streaming_config)
        self.max_retry = streaming_config.max_retry if streaming_config else 2
        
    def get_data_from_page(self, req_res):
        """Get the file list from a page - same as original."""
        soup = BeautifulSoup(req_res.text, features="lxml")
        return soup.find_all("tr")[1:]

    def get_request_url(self, files_types=None, store_id=None, when_date=None):
        """Get all links to collect download links from - same as original."""
        return [{"url": self.url, "method": "GET"}]

    def extract_task_from_entry(self, all_trs):
        """Extract download links and file names from page list - same as original."""
        download_urls = []
        file_names = []
        for x in all_trs:
            try:
                download_urls.append(self.url + x.a.attrs["href"])
                file_names.append(x.a.attrs["href"].split(".")[0].split("/")[-1])
            except (AttributeError, KeyError, IndexError, TypeError) as e:
                Logger.warning(f"Error extracting task from entry: {e}")

        return download_urls, file_names

    def filter_bad_files_zip(
        self,
        file_names,
        download_urls,
        filter_null=False,
        filter_zero=False,
        by_function=lambda x: x[0],
    ):
        """apply bad files filtering to zip"""
        files = self.filter_bad_files(
            list(zip(file_names, download_urls)),
            filter_null=filter_null,
            filter_zero=filter_zero,
            by_function=by_function,
        )
        if len(files) == 0:
            return [], []
        return list(zip(*files))

    def apply_limit_zip(
        self,
        file_names,
        download_urls,
        limit=None,
        files_types=None,
        by_function=lambda x: x[0],
        store_id=None,
        when_date=None,
        files_names_to_scrape=None,
        suppress_exception=False,
    ):
        """apply limit to zip"""
        ziped = self.apply_limit(
            list(zip(file_names, download_urls)),
            limit=limit,
            files_types=files_types,
            by_function=by_function,
            store_id=store_id,
            when_date=when_date,
            files_names_to_scrape=files_names_to_scrape,
            suppress_exception=suppress_exception,
        )
        if len(ziped) == 0:
            return [], []
        return list(zip(*ziped))

    def discover_links_streaming(self, files_types=None, store_id=None, when_date=None,
                               filter_null=False, filter_zero=False, 
                               files_names_to_scrape=None, suppress_exception=False,
                               limit=None) -> List[Dict[str, Any]]:
        """Discover links for streaming processing."""
        try:
            # Get URLs to collect links from
            urls_to_collect_link_from = self.get_request_url(
                files_types=files_types, store_id=store_id, when_date=when_date
            )
            
            if len(urls_to_collect_link_from) == 0:
                Logger.warning("No pages to scrape")
                return []

            # Collect all table rows
            all_trs = []
            for url in urls_to_collect_link_from:
                req_res = self.session_with_cookies_by_chain(**url)
                trs = self.get_data_from_page(req_res)
                all_trs.extend(trs)

            Logger.info(f"Found {len(all_trs)} entries")

            # Extract download URLs and file names
            download_urls, file_names = self.extract_task_from_entry(all_trs)
            Logger.info(f"Found {len(download_urls)} download urls")

            # Apply filtering using original engine methods
            if filter_null or filter_zero:
                file_names, download_urls = self.filter_bad_files_zip(
                    file_names, download_urls, filter_null=filter_null, filter_zero=filter_zero
                )
                Logger.info(f"After filtering bad files: Found {len(download_urls)} files")

            # Ensure storage directory exists before filtering (needed for file checks)
            self.make_storage_path_dir()
            
            # Apply limits and filters using original engine methods  
            file_names, download_urls = self.apply_limit_zip(
                file_names, download_urls,
                limit=limit, files_types=files_types,
                store_id=store_id, when_date=when_date,
                files_names_to_scrape=files_names_to_scrape,
                suppress_exception=suppress_exception
            )
            
            Logger.info(f"After applying limit: Found {len(download_urls)} entries")

            # Convert to streaming format
            links = []
            for url, name in zip(download_urls, file_names):
                links.append({
                    'url': url,
                    'file_name': name,
                    'original_data': (url, name)
                })
                
            return links
            
        except Exception as e:
            Logger.error(f"Error discovering links: {e}")
            if not suppress_exception:
                raise e
            return []

    def process_link_data(self, link_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single link - for web engine this is mostly pass-through."""
        # Add any processing metadata
        link_data['processed_at'] = threading.current_thread().name
        return link_data

    def download_item_data(self, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Download a single item using the original save_and_extract method."""
        try:
            original_data = item_data['original_data']
            result = self.save_and_extract(original_data)
            
            return {
                'file_name': result['file_name'],
                'content': '',  # Content is saved to disk by save_and_extract
                'download_result': result,
                'downloaded_at': threading.current_thread().name
            }
        except Exception as e:
            Logger.error(f"Error downloading item {item_data.get('file_name', 'unknown')}: {e}")
            return None

    async def scrape_streaming(self, limit=None, files_types=None, store_id=None, 
                             when_date=None, files_names_to_scrape=None,
                             filter_null=False, filter_zero=False, 
                             suppress_exception=False):
        """Main streaming scrape method."""
        try:
            # Start streaming pipeline
            await self.start_streaming()
            
            # Trigger scraping start events
            self.on_scraping_start(
                limit=limit, files_types=files_types, store_id=store_id,
                files_names_to_scrape=files_names_to_scrape, when_date=when_date,
                filter_nul=filter_null, filter_zero=filter_zero,
                suppress_exception=suppress_exception
            )
            
            # Discover links
            links = self.discover_links_streaming(
                files_types=files_types, store_id=store_id, when_date=when_date,
                filter_null=filter_null, filter_zero=filter_zero,
                files_names_to_scrape=files_names_to_scrape,
                suppress_exception=suppress_exception, limit=limit
            )
            
            Logger.info(f"Starting streaming processing of {len(links)} links")
            
            # Add links to pipeline for processing
            for link in links:
                if not self.add_link_for_processing(link):
                    Logger.warning(f"Failed to add link to pipeline: {link['file_name']}")
                    
            # Wait for processing to complete
            await self._wait_for_completion()
            
            # Get final stats
            stats = self.get_streaming_stats()
            Logger.info(f"Streaming complete: {stats}")
            
            # Create results in original format for compatibility
            results = []
            for i in range(stats['items_stored']):
                results.append({
                    'file_name': f'streamed_item_{i}',
                    'downloaded': True,
                    'extract_succefully': True,
                    'error': None,
                    'restart_and_retry': False
                })
                
            self.on_download_completed(results=results)
            return results
            
        except Exception as e:
            if not suppress_exception:
                raise e
            Logger.warning(f"Suppressing streaming exception: {e}")
            return []
        finally:
            await self.stop_streaming()
            
    async def _wait_for_completion(self, timeout: float = 300.0):
        """Wait for the pipeline to finish processing all items."""
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:            
            # Check if all queues are empty and processing is done
            if (self._pipeline and 
                self._pipeline.link_queue.empty() and
                self._pipeline.processing_queue.empty() and
                self._pipeline.download_queue.empty() and
                self._pipeline.storage_queue.empty()):
                Logger.info("All queues empty, processing complete")
                break
                
            await asyncio.sleep(1.0)
        else:
            Logger.warning(f"Timeout waiting for pipeline completion after {timeout}s")

    def _scrape(self, limit=None, files_types=None, store_id=None, when_date=None,
                files_names_to_scrape=None, filter_null=False, filter_zero=False,
                suppress_exception=False):
        """Legacy _scrape method that runs streaming scrape synchronously."""
        try:
            # Check if we're already in an event loop
            current_loop = asyncio.get_event_loop()
            if current_loop.is_running():
                # We're in an async context, run synchronously to avoid loop conflicts
                return self._scrape_sync(
                    limit=limit, files_types=files_types, store_id=store_id,
                    when_date=when_date, files_names_to_scrape=files_names_to_scrape,
                    filter_null=filter_null, filter_zero=filter_zero,
                    suppress_exception=suppress_exception
                )
            else:
                # No event loop running, we can create one
                return current_loop.run_until_complete(
                    self.scrape_streaming(
                        limit=limit, files_types=files_types, store_id=store_id,
                        when_date=when_date, files_names_to_scrape=files_names_to_scrape,
                        filter_null=filter_null, filter_zero=filter_zero,
                        suppress_exception=suppress_exception
                    )
                )
        except RuntimeError:
            # No event loop exists, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.scrape_streaming(
                        limit=limit, files_types=files_types, store_id=store_id,
                        when_date=when_date, files_names_to_scrape=files_names_to_scrape,
                        filter_null=filter_null, filter_zero=filter_zero,
                        suppress_exception=suppress_exception
                    )
                )
            finally:
                loop.close()

    def _scrape_sync(self, limit=None, files_types=None, store_id=None, when_date=None,
                     files_names_to_scrape=None, filter_null=False, filter_zero=False,
                     suppress_exception=False):
        """Synchronous fallback method when we can't use async."""
        try:
            Logger.info("Running synchronous streaming fallback")
            
            # Discover links synchronously
            links = self.discover_links_streaming(
                files_types=files_types, store_id=store_id, when_date=when_date,
                filter_null=filter_null, filter_zero=filter_zero,
                files_names_to_scrape=files_names_to_scrape,
                suppress_exception=suppress_exception, limit=limit
            )
            
            Logger.info(f"Processing {len(links)} links synchronously")
            
            # Process and download synchronously using parent's execute_in_parallel
            from il_supermarket_scarper.utils import execute_in_parallel
            
            results = execute_in_parallel(
                self.save_and_extract,
                [link['original_data'] for link in links],
                max_threads=self.max_threads,
            )
            
            return results
            
        except Exception as e:
            if not suppress_exception:
                raise e
            Logger.warning(f"Suppressing sync streaming exception: {e}")
            return []


# Backward compatibility factory function
def create_streaming_web_engine(chain, chain_id, url, folder_name=None, max_threads=5,
                               streaming_caps=None, storage_config=None):
    """Factory function to create a streaming web engine with backward compatibility."""
    
    # Create streaming configuration
    if streaming_caps is None:
        streaming_caps = {
            'link_discovery_cap': 100,
            'processing_cap': max_threads * 2,
            'download_cap': max_threads,
            'storage_cap': max_threads // 2 or 1,
            'queue_size': 200
        }
    
    if storage_config is None:
        storage_config = {
            'storage_type': StorageType.DISK.value,
            'config': {'output_dir': folder_name}
        }
    
    config = WebStreamingConfig.from_dict({
        'streaming': streaming_caps,
        'storage': storage_config,
        'max_threads': max_threads
    })
    
    return StreamingWebEngine(chain, chain_id, url, folder_name, config)
