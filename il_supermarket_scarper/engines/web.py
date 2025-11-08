import asyncio
import gzip
import io
import json
import os
import threading
import zipfile
import requests
from bs4 import BeautifulSoup
from il_supermarket_scarper.utils import Logger, execute_in_parallel, session_with_cookies
from typing import List, Dict, Any, Optional
from .streaming import StreamingEngine, WebStreamingConfig, StorageType



class WebBase(StreamingEngine):
    """scrape the file of websites that the only why to download them is via web"""

     
    def __init__(self, chain, chain_id, url,
                 streaming_config: Optional[WebStreamingConfig] = None):        
        super().__init__(chain, chain_id, url, streaming_config)
        self.max_retry = streaming_config.max_retry if streaming_config else 2
        self.use_legacy_mode = False  # Flag to completely bypass streaming
        
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
                href = x.a.attrs["href"]
                # If href is already an absolute URL, use it directly
                if href.startswith('http://') or href.startswith('https://'):
                    download_urls.append(href)
                else:
                    download_urls.append(self.url + href)
                file_names.append(href.split(".")[0].split("/")[-1])
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

    def _download_to_memory(self, file_link, file_name):
        """Download file directly to memory without writing to disk."""
        try:
            # Handle Bina-style downloads that need to get SPath first
            # Only do this if the file_link doesn't look like a direct file URL
            # (Bina scrapers use Download.aspx?FileNm=... which returns JSON with SPath)
            # Check for Download.aspx regardless of whether URL is absolute or relative
            if (hasattr(self, 'session_with_cookies_by_chain') and 
                'Download.aspx' in file_link and 'FileNm=' in file_link):
                try:
                    response_content = self.session_with_cookies_by_chain(file_link)
                    # Check if response is gzipped (starts with 0x1f 0x8b)
                    content_bytes_check = response_content.content
                    if len(content_bytes_check) >= 2 and content_bytes_check[0] == 0x1f and content_bytes_check[1] == 0x8b:
                        # Response is gzipped, not JSON - this means it's the actual file
                        Logger.debug(f"SPath response is gzipped file, using directly")
                        actual_url = file_link
                        # Use the response content directly
                        content_bytes = content_bytes_check
                        # Skip the download step below
                        skip_download = True
                    else:
                        # Response is JSON with SPath
                        spath = json.loads(response_content.content)
                        Logger.debug(f"Found spath: {spath}")
                        url = spath[0]["SPath"]
                        # If URL is already complete (starts with http), use it directly
                        if url.startswith('http://') or url.startswith('https://'):
                            actual_url = url
                        else:
                            # Otherwise, construct from base URL if available
                            actual_url = url
                        skip_download = False
                except (json.JSONDecodeError, KeyError, IndexError, UnicodeDecodeError) as e:
                    Logger.warning(f"Could not parse SPath response, using original URL: {e}")
                    actual_url = file_link
                    skip_download = False
            else:
                actual_url = file_link
                skip_download = False
            
            # Download to memory - skip if we already have content from SPath response
            if not skip_download:
                # Try direct requests first (faster for most cases)
                try:
                    response = requests.get(
                        actual_url, stream=True, timeout=30, headers={"Accept-Encoding": None}
                    )
                    response.raise_for_status()
                    content_bytes = response.content
                except Exception as e:
                    # If direct download fails, try using session (for scrapers that need cookies/auth)
                    if hasattr(self, 'session_with_cookies_by_chain'):
                        Logger.debug(f"Direct download failed, trying session: {e}")
                        try:
                            response_obj = self.session_with_cookies_by_chain(actual_url, method="GET", timeout=30)
                            content_bytes = response_obj.content
                        except Exception as session_e:
                            Logger.error(f"Both direct and session download failed: direct={e}, session={session_e}")
                            raise
                    else:
                        raise
            
            if not content_bytes:
                raise ValueError(f"Empty response from {actual_url}")
            
            # Check if it's a gzip file and extract in memory
            # Always check magic bytes first - gzip starts with 0x1f 0x8b
            has_gzip_magic = len(content_bytes) >= 2 and content_bytes[0] == 0x1f and content_bytes[1] == 0x8b
            has_gz_ext = file_link.endswith('.gz') or file_name.endswith('.gz')
            
            # If it has gzip magic bytes OR .gz extension, try to decompress
            if has_gzip_magic or has_gz_ext:
                try:
                    # Decompress as gzip
                    content_bytes = gzip.decompress(content_bytes)
                    Logger.debug(f"Decompressed gzip file, size: {len(content_bytes)} bytes")
                except Exception as e:
                    # If .gz extension but decompression failed, try as zip
                    if has_gz_ext:
                        Logger.debug(f"Gzip decompression failed ({type(e).__name__}: {e}), trying zip")
                        try:
                            with zipfile.ZipFile(io.BytesIO(content_bytes)) as the_zip:
                                zip_info = the_zip.infolist()[0]
                                content_bytes = the_zip.read(zip_info)
                            Logger.debug(f"Extracted zip file, size: {len(content_bytes)} bytes")
                        except Exception as zip_e:
                            Logger.error(f"Could not extract compressed file as gzip ({e}) or zip ({zip_e})")
                            raise zip_e
                    else:
                        # Has magic bytes but decompression failed - this is an error
                        Logger.error(f"File has gzip magic bytes but decompression failed: {e}")
                        raise
            
            # Decode to string (only after decompression)
            # Safety check: if decode fails with gzip magic bytes, we must have missed decompression
            try:
                content = content_bytes.decode('utf-8')
            except UnicodeDecodeError as decode_err:
                # If we get a decode error and see gzip magic bytes, try decompressing
                if len(content_bytes) >= 2 and content_bytes[0] == 0x1f and content_bytes[1] == 0x8b:
                    Logger.warning(f"Got decode error but file has gzip magic bytes, attempting decompression")
                    try:
                        content_bytes = gzip.decompress(content_bytes)
                        content = content_bytes.decode('utf-8')
                        Logger.debug(f"Successfully decompressed and decoded after decode error")
                    except Exception as decomp_err:
                        Logger.error(f"Failed to decompress after decode error: {decomp_err}")
                        raise decode_err
                else:
                    raise
            
            # Check for errors in content
            if "link expired" in content:
                from il_supermarket_scarper.utils import RestartSessionError
                raise RestartSessionError()
            
            return content, True
            
        except Exception as e:
            import traceback
            Logger.error(f"Error downloading {file_link} to memory: {e}")
            Logger.debug(f"Traceback: {traceback.format_exc()}")
            return None, False
    
    def download_item_data(self, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Download a single item using the original save_and_extract method."""
        try:
            original_data = item_data['original_data']
            file_link, file_name = original_data
            
            # Check if using queue storage - download directly to memory
            use_memory = False
            if self.streaming_config:
                storage_type = self.streaming_config.storage.storage_type
                if isinstance(storage_type, StorageType):
                    storage_type_value = storage_type.value
                else:
                    storage_type_value = storage_type
                use_memory = storage_type_value == StorageType.QUEUE.value
            
            content = ''
            result = None
            
            if use_memory:
                # Download directly to memory
                Logger.debug(f"Downloading {file_link} directly to memory for queue")
                content, success = self._download_to_memory(file_link, file_name)
                if success:
                    result = {
                        "file_name": file_name,
                        "downloaded": True,
                        "extract_succefully": True,
                        "error": None,
                        "restart_and_retry": False,
                    }
                else:
                    result = {
                        "file_name": file_name,
                        "downloaded": False,
                        "extract_succefully": False,
                        "error": "Failed to download to memory",
                        "restart_and_retry": False,
                    }
            else:
                # Use disk-based download (original behavior)
                result = self.save_and_extract(original_data)
            
            return {
                'file_name': result['file_name'],
                'content': content,
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
            
            Logger.info(f"Starting streaming processing of {len(links)} links with {self.streaming_config.streaming.download_cap} download workers and {self.streaming_config.streaming.storage_cap} storage workers")
            
            expected_items = len(links)

            # Add links to pipeline for processing in bulk (faster)
            for link in links:
                # Use non-blocking put for faster submission
                self._pipeline.link_queue.put(link, block=False)
                self._pipeline._stats['links_discovered'] += 1
                    
            # Wait for processing to complete
            await self._wait_for_completion(expected_items=expected_items)
            
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
            
    async def _wait_for_completion(self, expected_items: Optional[int] = None, timeout: float = 300.0):
        """Wait for the pipeline to finish processing all items."""
        start_time = asyncio.get_event_loop().time()
        
        check_interval = 0.01
        while (asyncio.get_event_loop().time() - start_time) < timeout:            
            stats = self.get_streaming_stats()
            if expected_items is not None and stats['items_stored'] >= expected_items:
                Logger.info("Reached expected item count, processing complete")
                break

            # Check if all queues are empty and processing is done
            if (self._pipeline and 
                self._pipeline.link_queue.empty() and
                self._pipeline.download_queue.empty()):
                if expected_items is None:
                    Logger.info("All queues empty, processing complete")
                    break
                
            await asyncio.sleep(check_interval)
        else:
            Logger.warning(f"Timeout waiting for pipeline completion after {timeout}s")

    def _scrape(self, limit=None, files_types=None, store_id=None, when_date=None,
                files_names_to_scrape=None, filter_null=False, filter_zero=False,
                suppress_exception=False):
        """Legacy _scrape method that runs streaming scrape synchronously."""
        # If legacy mode is enabled, use the old execute_in_parallel approach
        if self.use_legacy_mode:
            return self._scrape_legacy(
                limit=limit, files_types=files_types, store_id=store_id,
                when_date=when_date, files_names_to_scrape=files_names_to_scrape,
                filter_null=filter_null, filter_zero=filter_zero,
                suppress_exception=suppress_exception
            )
        
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
    
    def _scrape_legacy(self, limit=None, files_types=None, store_id=None, when_date=None,
                      files_names_to_scrape=None, filter_null=False, filter_zero=False,
                      suppress_exception=False):
        """Original non-streaming scrape using execute_in_parallel."""
        try:
            # Use discover_links_streaming to get links (same discovery as streaming, but different download)
            links = self.discover_links_streaming(
                files_types=files_types, store_id=store_id, when_date=when_date,
                filter_null=filter_null, filter_zero=filter_zero,
                files_names_to_scrape=files_names_to_scrape,
                suppress_exception=suppress_exception, limit=limit
            )
            
            Logger.info(f"Legacy mode: Using {self.max_threads} threads for {len(links)} downloads")
            
            # Extract original data for legacy download
            tasks = [link['original_data'] for link in links]
            
            # Download in parallel using old approach with limited threads
            from il_supermarket_scarper.utils import execute_in_parallel
            results = execute_in_parallel(
                self.save_and_extract,
                tasks,
                max_threads=self.max_threads,
            )
            
            return results
            
        except Exception as e:
            if not suppress_exception:
                raise e
            Logger.warning(f"Suppressing legacy scrape exception: {e}")
            return []

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
    
    return WebBase(chain, chain_id, url, streaming_config=config)
