"""
companion/tools/web_controller.py
Module điều khiển trình duyệt và tương tác web.
Cho phép Miku mở URL, tìm kiếm Google/YouTube, và theo dõi tab đang mở.
"""
import asyncio
import logging
import webbrowser
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import json

logger = logging.getLogger("Miku.WebController")

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str

class WebController:
    """
    Điều khiển hoạt động web: mở URL, tìm kiếm, quản lý tab.
    Tích hợp với các công cụ tìm kiếm và phát nhạc.
    """
    
    def __init__(self):
        self.browser_path: Optional[str] = None
        self.current_tabs: List[Dict[str, str]] = []
        self.search_history: List[str] = []
        self._lock = asyncio.Lock()
        
        # Cấu hình search engines
        self.search_engines = {
            "google": "https://www.google.com/search?q={query}",
            "youtube": "https://www.youtube.com/results?search_query={query}",
            "bing": "https://www.bing.com/search?q={query}",
            "duckduckgo": "https://duckduckgo.com/?q={query}",
        }
        
        # API keys (nếu có)
        self.google_api_key = None
        self.google_cse_id = None
        
    async def open_url(self, url: str, new_tab: bool = True) -> bool:
        """Mở URL trong trình duyệt mặc định."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: webbrowser.open(url, new=2 if new_tab else 1)
            )
            
            async with self._lock:
                self.current_tabs.append({
                    "url": url,
                    "title": f"Tab {len(self.current_tabs) + 1}",
                    "opened_at": asyncio.get_event_loop().time()
                })
            
            logger.info(f"Opened URL: {url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to open URL {url}: {e}")
            return False
    
    async def search_google(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """Tìm kiếm Google (sử dụng web scraping hoặc API nếu có)."""
        logger.info(f"Searching Google for: {query}")
        self.search_history.append(query)
        
        # Nếu có API key, dùng API chính thức
        if self.google_api_key and self.google_cse_id:
            return await self._search_google_api(query, num_results)
        
        # Fallback: Mở trang tìm kiếm trong browser
        search_url = self.search_engines["google"].format(query=query.replace(" ", "+"))
        await self.open_url(search_url)
        
        # Trả về kết quả giả định (trong thực tế cần scraping)
        return [
            SearchResult(
                title=f"Kết quả Google cho '{query}'",
                url=search_url,
                snippet="Đã mở trang tìm kiếm Google trong trình duyệt của bạn.",
                source="google_browser"
            )
        ]
    
    async def _search_google_api(self, query: str, num_results: int) -> List[SearchResult]:
        """Tìm kiếm Google qua Custom Search API."""
        try:
            import aiohttp
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.google_api_key,
                "cx": self.google_cse_id,
                "q": query,
                "num": min(num_results, 10)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        for item in data.get("items", []):
                            results.append(SearchResult(
                                title=item.get("title", ""),
                                url=item.get("link", ""),
                                snippet=item.get("snippet", ""),
                                source="google_api"
                            ))
                        return results
                    else:
                        logger.error(f"Google API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error in Google API search: {e}")
            return []
    
    async def search_youtube(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """Tìm kiếm YouTube."""
        logger.info(f"Searching YouTube for: {query}")
        
        search_url = self.search_engines["youtube"].format(query=query.replace(" ", "+"))
        await self.open_url(search_url)
        
        return [
            SearchResult(
                title=f"Kết quả YouTube cho '{query}'",
                url=search_url,
                snippet="Đã mở trang tìm kiếm YouTube.",
                source="youtube_browser"
            )
        ]
    
    async def play_music_mode(self, song_name: str) -> bool:
        """
        Chế độ phát nhạc: Tìm và mở bài hát trên YouTube.
        Có thể tích hợp với mpv để phát nền.
        """
        logger.info(f"Playing music: {song_name}")
        
        # Tìm kiếm bài hát
        search_query = f"{song_name} official audio"
        search_url = self.search_engines["youtube"].format(query=search_query.replace(" ", "+"))
        
        # Mở trong browser
        await self.open_url(search_url)
        
        # Trong tương lai có thể dùng mpv để phát nền
        # await self._play_with_mpv(search_query)
        
        return True
    
    async def _play_with_mpv(self, query: str) -> bool:
        """Phát nhạc nền bằng mpv (không hiển thị video)."""
        try:
            # Cần cài đặt yt-dlp và mpv
            cmd = [
                "mpv",
                "--no-video",
                f"ytsearch:{query}"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            logger.info(f"Started mpv for: {query}")
            return True
            
        except FileNotFoundError:
            logger.warning("mpv not found. Falling back to browser playback.")
            return False
        except Exception as e:
            logger.error(f"Error starting mpv: {e}")
            return False
    
    async def get_current_tab_info(self) -> Optional[Dict[str, Any]]:
        """Lấy thông tin tab đang mở gần nhất."""
        async with self._lock:
            if self.current_tabs:
                return self.current_tabs[-1]
        return None
    
    async def close_tab(self, url_pattern: str) -> bool:
        """Đóng tab dựa trên pattern URL (giả lập)."""
        async with self._lock:
            initial_count = len(self.current_tabs)
            self.current_tabs = [
                tab for tab in self.current_tabs
                if url_pattern not in tab.get("url", "")
            ]
            closed_count = initial_count - len(self.current_tabs)
            
        if closed_count > 0:
            logger.info(f"Closed {closed_count} tabs matching '{url_pattern}'")
            return True
        
        logger.warning(f"No tabs found matching '{url_pattern}'")
        return False
    
    def get_search_history(self, limit: int = 10) -> List[str]:
        """Trả về lịch sử tìm kiếm."""
        return self.search_history[-limit:]
    
    async def clear_history(self):
        """Xóa lịch sử tìm kiếm."""
        async with self._lock:
            self.search_history.clear()
            self.current_tabs.clear()
        logger.info("Cleared web history")

# Singleton instance
web_controller = WebController()
