"""
YouTube Bot Integration
=======================

Handles YouTube chat connection, events, and API interactions.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Callable

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False

from ..config import get_config
from .chat_message import ChatMessage, ChatUser, ChatPlatform
from .stream_events import StreamEvent, EventType
from core.event_bus import EventBus

logger = logging.getLogger(__name__)


class YouTubeBotHandler:
    """Handles YouTube bot functionality."""
    
    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.youtube_client = None
        self.is_connected = False
        self.live_chat_id = None
        self.next_page_token = None
        
    async def connect(self):
        """Connect to YouTube live chat."""
        if not YOUTUBE_AVAILABLE:
            logger.warning("Google API client not installed, YouTube integration disabled")
            return
            
        if not self.config.GOOGLE_API_KEY:
            logger.warning("YouTube credentials not configured")
            return
            
        try:
            # Build YouTube API client
            self.youtube_client = build(
                'youtube',
                'v3',
                developerKey=self.config.GOOGLE_API_KEY
            )
            
            # Get live chat ID for the current broadcast
            await self._get_live_chat_id()
            
            if self.live_chat_id:
                self.is_connected = True
                logger.info(f"YouTube bot connected to live chat: {self.live_chat_id}")
                
                # Start polling for messages
                asyncio.create_task(self._poll_chat_messages())
                
        except Exception as e:
            logger.error(f"Error connecting to YouTube: {e}", exc_info=True)
            self.is_connected = False
            
    async def _get_live_chat_id(self):
        """Get the live chat ID for the current broadcast."""
        try:
            # Search for active live stream on channel
            request = self.youtube_client.search().list(
                part='id',
                eventType='live',
                type='video',
                channelId=self.config.YOUTUBE_CHANNEL_ID,
                maxResults=1
            )
            
            response = request.execute()
            
            if response.get('items'):
                video_id = response['items'][0]['id']['videoId']
                
                # Get live chat details
                video_request = self.youtube_client.videos().list(
                    part='liveStreamingDetails',
                    id=video_id
                )
                
                video_response = video_request.execute()
                
                if video_response.get('items'):
                    live_details = video_response['items'][0].get('liveStreamingDetails', {})
                    self.live_chat_id = live_details.get('activeLiveChatId')
                    
                    if not self.live_chat_id:
                        # Try scheduled live chat
                        self.live_chat_id = live_details.get('scheduledStartTime')
                        
        except Exception as e:
            logger.error(f"Error getting live chat ID: {e}")
            
    async def _poll_chat_messages(self):
        """Poll YouTube live chat for new messages."""
        while self.is_connected:
            try:
                if not self.live_chat_id:
                    await asyncio.sleep(5)
                    continue
                    
                request = self.youtube_client.liveChatMessages().list(
                    liveChatId=self.live_chat_id,
                    part='snippet,authorDetails',
                    pageToken=self.next_page_token,
                    maxResults=100
                )
                
                response = request.execute()
                
                # Update next page token and polling interval
                self.next_page_token = response.get('nextPageToken')
                polling_interval = int(response.get('pollingIntervalMillis', 5000)) / 1000
                
                # Process messages
                for item in response.get('items', []):
                    await self._process_message(item)
                
                # Wait before next poll
                await asyncio.sleep(polling_interval)
                
            except HttpError as e:
                if e.resp.status == 404:
                    logger.warning("Live chat not found, reconnecting...")
                    await self._get_live_chat_id()
                else:
                    logger.error(f"YouTube API error: {e}")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error polling YouTube chat: {e}", exc_info=True)
                await asyncio.sleep(5)
                
    async def _process_message(self, message_item):
        """Process a YouTube chat message."""
        try:
            snippet = message_item.get('snippet', {})
            author_details = message_item.get('authorDetails', {})
            
            user = ChatUser(
                id=author_details.get('channelId', ''),
                username=author_details.get('displayName', ''),
                display_name=author_details.get('displayName', ''),
                platform=ChatPlatform.YOUTUBE,
                is_moderator=author_details.get('isChatModerator', False),
                is_subscriber=author_details.get('isChatSponsor', False),
            )
            
            message = ChatMessage(
                id=message_item.get('id', ''),
                user=user,
                content=snippet.get('textMessageDetails', {}).get('messageText', ''),
                timestamp=datetime.utcnow(),
                platform=ChatPlatform.YOUTUBE,
            )
            
            await self.event_bus.publish('chat_message', {
                'message': message,
                'platform': 'youtube'
            })
            
        except Exception as e:
            logger.error(f"Error processing YouTube message: {e}")
            
    async def disconnect(self):
        """Disconnect from YouTube."""
        self.is_connected = False
        logger.info("YouTube bot disconnected")
        
    async def send_message(self, message: str):
        """Send a message to YouTube live chat."""
        if not self.is_connected or not self.youtube_client or not self.live_chat_id:
            logger.warning("Cannot send message: not connected to YouTube")
            return
            
        try:
            request = self.youtube_client.liveChatMessages().insert(
                part='snippet',
                body={
                    'snippet': {
                        'liveChatId': self.live_chat_id,
                        'type': 'textMessageEvent',
                        'textMessageDetails': {
                            'messageText': message
                        }
                    }
                }
            )
            
            response = request.execute()
            logger.debug(f"Sent YouTube message: {message[:50]}...")
            
        except HttpError as e:
            if e.resp.status == 429:
                logger.warning("YouTube rate limit exceeded")
            else:
                logger.error(f"Error sending YouTube message: {e}")
        except Exception as e:
            logger.error(f"Error sending YouTube message: {e}")
            
    async def send_super_chat(self, amount: int, message: str):
        """Handle super chat (for receiving, not sending)."""
        # This would be triggered by incoming super chat events
        event = StreamEvent(
            event_type=EventType.YOUTUBE_SUPERCHAT,
            platform=ChatPlatform.YOUTUBE,
            timestamp=datetime.utcnow(),
            data={
                'amount': amount,
                'message': message,
            },
        )
        
        await self.event_bus.publish('stream_event', {'event': event})
