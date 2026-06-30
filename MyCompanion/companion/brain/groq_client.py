"""
Groq API Client - Fast LLM Inference
Optimized for free tier usage with smart caching and rate limiting
"""
import asyncio
import time
import json
import hashlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging
from pathlib import Path

try:
    from groq import AsyncGroq
except ImportError:
    AsyncGroq = None

logger = logging.getLogger(__name__)


@dataclass
class CachedResponse:
    """Cached LLM response with TTL"""
    text: str
    emotion: str
    timestamp: float
    ttl: int = 300  # 5 minutes default


class ResponseCache:
    """LRU Cache for LLM responses to save tokens"""
    
    def __init__(self, max_size: int = 100):
        self.cache: Dict[str, CachedResponse] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def _generate_key(self, prompt: str, context: str) -> str:
        """Generate cache key from prompt and context"""
        combined = f"{prompt}:{context}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def get(self, prompt: str, context: str) -> Optional[CachedResponse]:
        """Get cached response if available and not expired"""
        key = self._generate_key(prompt, context)
        if key in self.cache:
            cached = self.cache[key]
            if time.time() - cached.timestamp < cached.ttl:
                self.hits += 1
                logger.debug(f"Cache HIT (rate: {self.hits/(self.hits+self.misses)*100:.1f}%)")
                return cached
            else:
                del self.cache[key]
        self.misses += 1
        return None
    
    def set(self, prompt: str, context: str, text: str, emotion: str, ttl: int = 300):
        """Store response in cache"""
        key = self._generate_key(prompt, context)
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].timestamp)
            del self.cache[oldest_key]
        
        self.cache[key] = CachedResponse(
            text=text,
            emotion=emotion,
            timestamp=time.time(),
            ttl=ttl
        )
        logger.debug(f"Cached response (size: {len(self.cache)}/{self.max_size})")
    
    def clear(self):
        """Clear all cached responses"""
        self.cache.clear()
        logger.info("Response cache cleared")


class GroqClient:
    """
    Async Groq API client with:
    - Free tier optimization (Llama-3-8b-8192)
    - Response caching to minimize token usage
    - Automatic retry with exponential backoff
    - Rate limit handling
    """
    
    # Free models on Groq
    FREE_MODELS = [
        "llama-3.1-8b-instant",      # Fastest, good for chat
        "llama-3.2-1b-preview",       # Ultra-fast, simple tasks
        "llama-3.2-3b-preview",       # Balanced speed/quality
        "gemma2-9b-it",               # Alternative quality
    ]
    
    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        if AsyncGroq is None:
            raise ImportError("groq package not installed. Run: pip install groq")
        
        self.api_key = api_key
        self.model = model if model in self.FREE_MODELS else self.FREE_MODELS[0]
        self.client = AsyncGroq(api_key=api_key)
        self.cache = ResponseCache(max_size=100)
        
        # Rate limiting
        self.requests_per_minute = 30  # Groq free tier limit
        self.request_times: List[float] = []
        self.lock = asyncio.Lock()
        
        # Statistics
        self.total_tokens = 0
        self.total_requests = 0
        self.start_time = time.time()
    
    async def _wait_for_rate_limit(self):
        """Enforce rate limiting"""
        async with self.lock:
            now = time.time()
            # Remove requests older than 1 minute
            self.request_times = [t for t in self.request_times if now - t < 60]
            
            if len(self.request_times) >= self.requests_per_minute:
                wait_time = 60 - (now - self.request_times[0])
                if wait_time > 0:
                    logger.info(f"Rate limit reached, waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
            
            self.request_times.append(time.time())
    
    async def _retry_request(self, func, max_retries: int = 3):
        """Execute function with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                last_exception = e
                if attempt == max_retries - 1:
                    break
                
                # Exponential backoff: 1s, 2s, 4s
                wait_time = (2 ** attempt)
                logger.warning(f"Request failed (attempt {attempt+1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
        
        raise last_exception
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
        use_cache: bool = True,
        force_json: bool = False
    ) -> Dict[str, Any]:
        """
        Get chat completion from Groq API
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Max tokens in response
            use_cache: Whether to check/use response cache
            force_json: Force model to return JSON format
            
        Returns:
            Dict with 'text', 'emotion', 'tokens_used', 'model'
        """
        self.total_requests += 1
        
        # Check cache first
        if use_cache:
            prompt = messages[-1]['content'] if messages else ""
            context = str(messages[:-1]) if len(messages) > 1 else ""
            cached = self.cache.get(prompt, context)
            if cached:
                return {
                    'text': cached.text,
                    'emotion': cached.emotion,
                    'tokens_used': 0,
                    'model': 'cache',
                    'cached': True
                }
        
        await self._wait_for_rate_limit()
        
        # Prepare request
        system_prompt = "You are Miku, a friendly AI companion. Respond naturally and conversationally."
        if force_json:
            system_prompt += " ALWAYS respond in valid JSON format: {\"text\": \"your response\", \"emotion\": \"emotion_code\"}"
        
        full_messages = [{'role': 'system', 'content': system_prompt}] + messages
        
        async def make_request():
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"} if force_json else {"type": "text"},
                stream=False
            )
            return response
        
        try:
            response = await self._retry_request(make_request)
            
            # Parse response
            content = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0
            self.total_tokens += tokens_used
            
            # Extract text and emotion
            if force_json:
                try:
                    parsed = json.loads(content)
                    text = parsed.get('text', content)
                    emotion = parsed.get('emotion', 'neutral')
                except json.JSONDecodeError:
                    text = content
                    emotion = 'neutral'
            else:
                text = content
                emotion = 'neutral'
            
            # Cache the response
            if use_cache and tokens_used > 0:
                prompt = messages[-1]['content'] if messages else ""
                context = str(messages[:-1]) if len(messages) > 1 else ""
                self.cache.set(prompt, context, text, emotion)
            
            result = {
                'text': text,
                'emotion': emotion,
                'tokens_used': tokens_used,
                'model': self.model,
                'cached': False
            }
            
            # Log statistics periodically
            if self.total_requests % 10 == 0:
                elapsed = time.time() - self.start_time
                logger.info(
                    f"Groq stats: {self.total_requests} requests, "
                    f"{self.total_tokens} tokens, "
                    f"{elapsed/60:.1f}min uptime, "
                    f"cache hit rate: {self.cache.hits/(self.cache.hits+self.cache.misses)*100:.1f}%"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return {
                'text': "I'm having trouble connecting right now, but I'm still here!",
                'emotion': 'concerned',
                'tokens_used': 0,
                'model': 'error',
                'cached': False
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        elapsed = time.time() - self.start_time
        return {
            'total_requests': self.total_requests,
            'total_tokens': self.total_tokens,
            'requests_per_minute': self.requests_per_minute,
            'current_rpm': len(self.request_times),
            'cache_size': len(self.cache.cache),
            'cache_hit_rate': self.cache.hits / (self.cache.hits + self.cache.misses) * 100 if (self.cache.hits + self.cache.misses) > 0 else 0,
            'uptime_minutes': elapsed / 60,
            'avg_tokens_per_request': self.total_tokens / self.total_requests if self.total_requests > 0 else 0,
            'model': self.model
        }
    
    def clear_cache(self):
        """Clear response cache"""
        self.cache.clear()
    
    async def test_connection(self) -> bool:
        """Test API connection"""
        try:
            result = await self.chat_completion(
                messages=[{'role': 'user', 'content': 'Say "Hello" in one word'}],
                max_tokens=10,
                use_cache=False
            )
            return result['model'] != 'error'
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
