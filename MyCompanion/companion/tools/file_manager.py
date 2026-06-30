"""
companion/tools/file_manager.py
Quản lý tệp tin: đọc, viết, tìm kiếm, tổ chức file.
Cho phép Miku tương tác với hệ thống file của người dùng.
"""
import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
import fnmatch
import mimetypes

logger = logging.getLogger("Miku.FileManager")

@dataclass
class FileMetadata:
    path: str
    name: str
    size: int
    created: float
    modified: float
    accessed: float
    is_directory: bool
    mime_type: Optional[str]
    extension: Optional[str]

class FileManager:
    """
    Quản lý thao tác với hệ thống file.
    Hỗ trợ tìm kiếm, đọc/ghi, di chuyển, xóa file an toàn.
    """
    
    def __init__(self):
        self.home_dir = Path.home()
        self.download_dir = self.home_dir / "Downloads"
        self.desktop_dir = self.home_dir / "Desktop"
        self.documents_dir = self.home_dir / "Documents"
        self.music_dir = self.home_dir / "Music"
        self.pictures_dir = self.home_dir / "Pictures"
        self.videos_dir = self.home_dir / "Videos"
        self.code_dir = self.home_dir / "Code"
        
        # Các thư mục thường dùng
        self.common_dirs = {
            "home": self.home_dir,
            "downloads": self.download_dir,
            "desktop": self.desktop_dir,
            "documents": self.documents_dir,
            "music": self.music_dir,
            "pictures": self.pictures_dir,
            "videos": self.videos_dir,
            "code": self.code_dir,
        }
        
        # Giới hạn kích thước file đọc (MB)
        self.max_read_size_mb = 10
        
        # Extensions an toàn để đọc
        self.safe_read_extensions = {
            '.txt', '.md', '.py', '.js', '.ts', '.html', '.css', '.json',
            '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.log',
            '.csv', '.xml', '.rst', '.sh', '.bash', '.zsh', '.fish'
        }
        
        self._lock = asyncio.Lock()
    
    def _resolve_path(self, path_str: str) -> Path:
        """Giải quyết đường dẫn, hỗ trợ các shortcut như ~/Downloads."""
        path = Path(path_str)
        
        # Xử lý các shortcut
        if path_str.startswith("~/"):
            path = self.home_dir / path_str[2:]
        elif path_str.startswith("~"):
            path = self.home_dir
        
        # Kiểm tra các tên thư mục phổ biến
        lower_name = path.name.lower()
        if lower_name in self.common_dirs and not path.exists():
            return self.common_dirs[lower_name]
        
        return path.expanduser().resolve()
    
    async def search_files(
        self,
        pattern: str,
        search_dirs: Optional[List[str]] = None,
        max_results: int = 50,
        file_types: Optional[List[str]] = None
    ) -> List[FileMetadata]:
        """
        Tìm kiếm file theo pattern (hỗ trợ wildcard).
        
        Args:
            pattern: Mẫu tìm kiếm (vd: "*.pdf", "report*.docx")
            search_dirs: Danh sách thư mục cần tìm (mặc định: home, documents, downloads)
            max_results: Số kết quả tối đa
            file_types: Lọc theo extension (vd: ['.pdf', '.docx'])
        """
        if search_dirs is None:
            search_dirs = [str(self.home_dir), str(self.documents_dir), str(self.download_dir)]
        
        results = []
        
        for dir_str in search_dirs:
            search_path = self._resolve_path(dir_str)
            if not search_path.is_dir():
                continue
            
            try:
                loop = asyncio.get_event_loop()
                matches = await loop.run_in_executor(
                    None,
                    lambda p=search_path: list(p.rglob(pattern))
                )
                
                for match_path in matches[:max_results - len(results)]:
                    if file_types and match_path.suffix.lower() not in file_types:
                        continue
                    
                    try:
                        metadata = await self.get_file_metadata(str(match_path))
                        if metadata:
                            results.append(metadata)
                    except Exception as e:
                        logger.debug(f"Could not get metadata for {match_path}: {e}")
                    
                    if len(results) >= max_results:
                        break
                        
            except PermissionError:
                logger.warning(f"Permission denied accessing {search_path}")
            except Exception as e:
                logger.error(f"Error searching in {dir_str}: {e}")
        
        logger.info(f"Found {len(results)} files matching '{pattern}'")
        return results
    
    async def get_file_metadata(self, path_str: str) -> Optional[FileMetadata]:
        """Lấy metadata chi tiết của file."""
        path = self._resolve_path(path_str)
        
        if not path.exists():
            logger.warning(f"Path does not exist: {path_str}")
            return None
        
        try:
            stat = path.stat()
            mime_type, _ = mimetypes.guess_type(str(path))
            
            return FileMetadata(
                path=str(path),
                name=path.name,
                size=stat.st_size,
                created=stat.st_ctime,
                modified=stat.st_mtime,
                accessed=stat.st_atime,
                is_directory=path.is_dir(),
                mime_type=mime_type,
                extension=path.suffix.lower() if path.is_file() else None
            )
        except Exception as e:
            logger.error(f"Error getting metadata for {path}: {e}")
            return None
    
    async def read_file(self, path_str: str, max_chars: int = 5000) -> Optional[str]:
        """
        Đọc nội dung file văn bản.
        Chỉ đọc các file an toàn, giới hạn kích thước.
        """
        path = self._resolve_path(path_str)
        
        if not path.is_file():
            logger.error(f"Not a file: {path_str}")
            return None
        
        # Kiểm tra extension an toàn
        if path.suffix.lower() not in self.safe_read_extensions:
            logger.warning(f"Unsafe file type to read: {path.suffix}")
            return f"Cannot read file type '{path.suffix}'. Only text-based formats are supported for safety."
        
        # Kiểm tra kích thước
        try:
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > self.max_read_size_mb:
                logger.warning(f"File too large to read: {size_mb:.2f} MB")
                return f"File is too large ({size_mb:.2f} MB). Maximum allowed is {self.max_read_size_mb} MB."
        except Exception as e:
            logger.error(f"Error checking file size: {e}")
            return None
        
        try:
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                None,
                lambda: path.read_text(encoding='utf-8', errors='ignore')
            )
            
            if len(content) > max_chars:
                content = content[:max_chars] + f"\n\n... (truncated at {max_chars} characters)"
            
            logger.info(f"Read file: {path_str} ({len(content)} chars)")
            return content
            
        except UnicodeDecodeError:
            logger.error(f"Cannot decode file as UTF-8: {path_str}")
            return "Error: File appears to be binary or uses unsupported encoding."
        except PermissionError:
            logger.error(f"Permission denied reading: {path_str}")
            return "Error: Permission denied."
        except Exception as e:
            logger.error(f"Error reading file {path_str}: {e}")
            return f"Error reading file: {str(e)}"
    
    async def write_file(self, path_str: str, content: str, create_dirs: bool = True) -> bool:
        """Ghi nội dung vào file."""
        path = self._resolve_path(path_str)
        
        # An toàn: Không ghi vào các thư mục hệ thống quan trọng
        system_paths = ['/etc', '/usr', '/bin', '/sbin', '/boot']
        if any(str(path).startswith(p) for p in system_paths):
            logger.error(f"Attempted to write to system path: {path}")
            return False
        
        try:
            if create_dirs and not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: path.write_text(content, encoding='utf-8')
            )
            
            logger.info(f"Wrote file: {path_str} ({len(content)} chars)")
            return True
            
        except PermissionError:
            logger.error(f"Permission denied writing to: {path_str}")
            return False
        except Exception as e:
            logger.error(f"Error writing file {path_str}: {e}")
            return False
    
    async def list_directory(self, path_str: str, show_hidden: bool = False) -> List[FileMetadata]:
        """Liệt kê nội dung thư mục."""
        path = self._resolve_path(path_str)
        
        if not path.is_dir():
            logger.error(f"Not a directory: {path_str}")
            return []
        
        results = []
        try:
            loop = asyncio.get_event_loop()
            entries = await loop.run_in_executor(None, lambda: list(path.iterdir()))
            
            for entry in entries:
                if not show_hidden and entry.name.startswith('.'):
                    continue
                
                try:
                    metadata = await self.get_file_metadata(str(entry))
                    if metadata:
                        results.append(metadata)
                except Exception as e:
                    logger.debug(f"Could not get metadata for {entry}: {e}")
            
            # Sắp xếp: thư mục trước, file sau, theo tên
            results.sort(key=lambda x: (not x.is_directory, x.name.lower()))
            
        except PermissionError:
            logger.warning(f"Permission denied listing: {path_str}")
        except Exception as e:
            logger.error(f"Error listing directory {path_str}: {e}")
        
        return results
    
    async def move_file(self, src_str: str, dest_str: str) -> bool:
        """Di chuyển hoặc đổi tên file."""
        src = self._resolve_path(src_str)
        dest = self._resolve_path(dest_str)
        
        if not src.exists():
            logger.error(f"Source does not exist: {src_str}")
            return False
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: shutil.move(str(src), str(dest)))
            logger.info(f"Moved {src_str} -> {dest_str}")
            return True
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            return False
    
    async def delete_file(self, path_str: str, recursive: bool = False) -> bool:
        """Xóa file hoặc thư mục."""
        path = self._resolve_path(path_str)
        
        # An toàn: Không xóa các thư mục quan trọng
        protected_paths = [
            self.home_dir, '/home', '/root', '/etc', '/usr', '/bin', '/sbin'
        ]
        if any(str(path).startswith(p) for p in protected_paths):
            logger.error(f"Attempted to delete protected path: {path}")
            return False
        
        if not path.exists():
            logger.warning(f"Path does not exist: {path_str}")
            return False
        
        try:
            loop = asyncio.get_event_loop()
            if path.is_dir():
                if recursive:
                    await loop.run_in_executor(None, lambda: shutil.rmtree(str(path)))
                else:
                    await loop.run_in_executor(None, lambda: path.rmdir())
            else:
                await loop.run_in_executor(None, lambda: path.unlink())
            
            logger.info(f"Deleted: {path_str}")
            return True
            
        except PermissionError:
            logger.error(f"Permission denied deleting: {path_str}")
            return False
        except Exception as e:
            logger.error(f"Error deleting {path_str}: {e}")
            return False
    
    async def get_recent_files(self, limit: int = 20, days: int = 7) -> List[FileMetadata]:
        """Lấy danh sách file được sửa đổi gần đây."""
        recent = []
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        search_dirs = [
            self.documents_dir,
            self.download_dir,
            self.desktop_dir,
        ]
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            
            try:
                for item in search_dir.rglob('*'):
                    if item.is_file():
                        try:
                            mtime = item.stat().st_mtime
                            if mtime > cutoff_time:
                                metadata = await self.get_file_metadata(str(item))
                                if metadata:
                                    recent.append(metadata)
                        except (OSError, PermissionError):
                            continue
            except Exception as e:
                logger.debug(f"Error scanning {search_dir}: {e}")
        
        # Sắp xếp theo thời gian giảm dần
        recent.sort(key=lambda x: x.modified, reverse=True)
        return recent[:limit]
    
    async def open_with_default_app(self, path_str: str) -> bool:
        """Mở file bằng ứng dụng mặc định của hệ thống."""
        path = self._resolve_path(path_str)
        
        if not path.exists():
            logger.error(f"Path does not exist: {path_str}")
            return False
        
        try:
            import subprocess
            if os.name == 'posix':  # Linux/Mac
                await asyncio.create_subprocess_exec('xdg-open', str(path))
            elif os.name == 'nt':  # Windows
                os.startfile(str(path))
            else:
                logger.error(f"Unsupported OS for opening files: {os.name}")
                return False
            
            logger.info(f"Opened with default app: {path_str}")
            return True
            
        except Exception as e:
            logger.error(f"Error opening file {path_str}: {e}")
            return False

# Singleton instance
file_manager = FileManager()
