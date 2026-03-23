"""
Web Search module for Edit Image Service.
Provides character and reference image search from various sources.
"""

import logging
import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

import httpx
from PIL import Image

logger = logging.getLogger(__name__)


class SearchSource(Enum):
    """Available search sources."""
    DANBOORU = "danbooru"
    GELBOORU = "gelbooru"
    SAFEBOORU = "safebooru"
    MYANIMELIST = "myanimelist"
    ANILIST = "anilist"


@dataclass
class SearchResult:
    """Search result container."""
    source: str
    id: str
    url: str
    preview_url: Optional[str] = None
    tags: List[str] = None
    score: int = 0
    width: int = 0
    height: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class CharacterInfo:
    """Character information container."""
    name: str
    source: str  # Anime/Game source
    tags: List[str]
    description: Optional[str] = None
    image_url: Optional[str] = None
    mal_id: Optional[int] = None
    anilist_id: Optional[int] = None


class DanbooruClient:
    """Client for Danbooru API."""
    
    BASE_URL = "https://danbooru.donmai.us"
    
    def __init__(self, api_key: str = "", username: str = ""):
        self.api_key = api_key
        self.username = username
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_posts(
        self,
        tags: str,
        limit: int = 20,
        page: int = 1,
        rating: Optional[str] = None,  # s=safe, q=questionable, e=explicit
    ) -> List[SearchResult]:
        """
        Search for posts on Danbooru.
        
        Args:
            tags: Space-separated tags to search for
            limit: Maximum number of results
            page: Page number
            rating: Content rating filter
            
        Returns:
            List of SearchResult objects
        """
        params = {
            "tags": tags,
            "limit": min(limit, 100),
            "page": page,
        }
        
        if rating:
            params["tags"] += f" rating:{rating}"
        
        # Add auth if available
        if self.api_key and self.username:
            params["login"] = self.username
            params["api_key"] = self.api_key
        
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/posts.json",
                params=params
            )
            response.raise_for_status()
            
            results = []
            for post in response.json():
                if "file_url" not in post:
                    continue
                    
                results.append(SearchResult(
                    source="danbooru",
                    id=str(post["id"]),
                    url=post.get("file_url", ""),
                    preview_url=post.get("preview_file_url"),
                    tags=post.get("tag_string", "").split(),
                    score=post.get("score", 0),
                    width=post.get("image_width", 0),
                    height=post.get("image_height", 0),
                    metadata={
                        "rating": post.get("rating"),
                        "source": post.get("source"),
                        "created_at": post.get("created_at"),
                    }
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Danbooru search error: {e}")
            return []
    
    async def get_tag_wiki(self, tag: str) -> Optional[Dict]:
        """Get wiki information for a tag."""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/wiki_pages/{tag}.json"
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Wiki fetch error: {e}")
        return None
    
    async def autocomplete_tag(self, query: str, limit: int = 10) -> List[str]:
        """Autocomplete a tag query."""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/autocomplete.json",
                params={"search[query]": query, "limit": limit}
            )
            if response.status_code == 200:
                return [item["value"] for item in response.json()]
        except Exception as e:
            logger.debug(f"Autocomplete error: {e}")
        return []
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class GelbooruClient:
    """Client for Gelbooru API."""
    
    BASE_URL = "https://gelbooru.com/index.php"
    
    def __init__(self, api_key: str = "", user_id: str = ""):
        self.api_key = api_key
        self.user_id = user_id
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_posts(
        self,
        tags: str,
        limit: int = 20,
        page: int = 0,
    ) -> List[SearchResult]:
        """Search for posts on Gelbooru."""
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "json": 1,
            "tags": tags,
            "limit": min(limit, 100),
            "pid": page,
        }
        
        if self.api_key and self.user_id:
            params["api_key"] = self.api_key
            params["user_id"] = self.user_id
        
        try:
            response = await self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            posts = data.get("post", [])
            
            results = []
            for post in posts:
                results.append(SearchResult(
                    source="gelbooru",
                    id=str(post["id"]),
                    url=post.get("file_url", ""),
                    preview_url=post.get("preview_url"),
                    tags=post.get("tags", "").split(),
                    score=post.get("score", 0),
                    width=post.get("width", 0),
                    height=post.get("height", 0),
                    metadata={
                        "rating": post.get("rating"),
                        "source": post.get("source"),
                    }
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Gelbooru search error: {e}")
            return []
    
    async def close(self):
        await self.client.aclose()


class AniListClient:
    """Client for AniList GraphQL API."""
    
    BASE_URL = "https://graphql.anilist.co"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_character(self, name: str) -> List[CharacterInfo]:
        """Search for a character by name."""
        query = """
        query ($search: String) {
            Page(page: 1, perPage: 10) {
                characters(search: $search) {
                    id
                    name {
                        full
                        native
                    }
                    description
                    image {
                        large
                        medium
                    }
                    media {
                        nodes {
                            title {
                                romaji
                                english
                            }
                        }
                    }
                }
            }
        }
        """
        
        try:
            response = await self.client.post(
                self.BASE_URL,
                json={"query": query, "variables": {"search": name}}
            )
            response.raise_for_status()
            
            data = response.json()
            characters = data.get("data", {}).get("Page", {}).get("characters", [])
            
            results = []
            for char in characters:
                media = char.get("media", {}).get("nodes", [])
                source_title = ""
                if media:
                    source_title = media[0].get("title", {}).get("romaji", "")
                
                results.append(CharacterInfo(
                    name=char.get("name", {}).get("full", ""),
                    source=source_title,
                    tags=[],
                    description=char.get("description"),
                    image_url=char.get("image", {}).get("large"),
                    anilist_id=char.get("id"),
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"AniList search error: {e}")
            return []
    
    async def close(self):
        await self.client.aclose()


class JikanClient:
    """Client for Jikan API (MyAnimeList unofficial API)."""
    
    BASE_URL = "https://api.jikan.moe/v4"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_character(self, name: str) -> List[CharacterInfo]:
        """Search for a character by name."""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/characters",
                params={"q": name, "limit": 10}
            )
            response.raise_for_status()
            
            data = response.json()
            characters = data.get("data", [])
            
            results = []
            for char in characters:
                results.append(CharacterInfo(
                    name=char.get("name", ""),
                    source="",  # Need additional API call
                    tags=[],
                    description=char.get("about"),
                    image_url=char.get("images", {}).get("jpg", {}).get("image_url"),
                    mal_id=char.get("mal_id"),
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Jikan search error: {e}")
            return []
    
    async def close(self):
        await self.client.aclose()


class WebSearchManager:
    """
    Unified manager for web search across multiple sources.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the search manager.
        
        Args:
            config: Configuration dict with API keys
        """
        self.config = config or {}
        
        # Initialize clients
        self.danbooru = DanbooruClient(
            api_key=self.config.get("danbooru_api_key", ""),
            username=self.config.get("danbooru_username", ""),
        )
        self.gelbooru = GelbooruClient(
            api_key=self.config.get("gelbooru_api_key", ""),
            user_id=self.config.get("gelbooru_user_id", ""),
        )
        self.anilist = AniListClient()
        self.jikan = JikanClient()
    
    async def search_images(
        self,
        query: str,
        sources: List[SearchSource] = None,
        limit: int = 20,
        include_nsfw: bool = True,
    ) -> Dict[str, List[SearchResult]]:
        """
        Search for images across multiple sources.
        
        Args:
            query: Search query (tags or keywords)
            sources: List of sources to search
            limit: Maximum results per source
            include_nsfw: Include NSFW results
            
        Returns:
            Dict mapping source name to list of results
        """
        if sources is None:
            sources = [SearchSource.DANBOORU, SearchSource.GELBOORU]
        
        results = {}
        tasks = []
        
        # Prepare search tasks
        rating = None if include_nsfw else "s"
        
        if SearchSource.DANBOORU in sources:
            tasks.append(("danbooru", self.danbooru.search_posts(
                query, limit=limit, rating=rating
            )))
        
        if SearchSource.GELBOORU in sources:
            tasks.append(("gelbooru", self.gelbooru.search_posts(
                query, limit=limit
            )))
        
        # Execute searches concurrently
        for source_name, task in tasks:
            try:
                results[source_name] = await task
            except Exception as e:
                logger.error(f"Search failed for {source_name}: {e}")
                results[source_name] = []
        
        return results
    
    async def search_character(
        self,
        name: str,
        sources: List[SearchSource] = None,
    ) -> Dict[str, List[CharacterInfo]]:
        """
        Search for character information.
        
        Args:
            name: Character name to search
            sources: List of sources to search
            
        Returns:
            Dict mapping source name to list of character info
        """
        if sources is None:
            sources = [SearchSource.ANILIST, SearchSource.MYANIMELIST]
        
        results = {}
        
        if SearchSource.ANILIST in sources:
            try:
                results["anilist"] = await self.anilist.search_character(name)
            except Exception as e:
                logger.error(f"AniList search error: {e}")
                results["anilist"] = []
        
        if SearchSource.MYANIMELIST in sources:
            try:
                results["myanimelist"] = await self.jikan.search_character(name)
            except Exception as e:
                logger.error(f"MAL search error: {e}")
                results["myanimelist"] = []
        
        return results
    
    async def get_reference_for_character(
        self,
        character_name: str,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """
        Get reference images and info for a character.
        
        This combines character search and image search.
        
        Args:
            character_name: Name of the character
            limit: Max images to retrieve
            
        Returns:
            Dict with character info and reference images
        """
        # Convert to Danbooru-style tag
        tag = character_name.lower().replace(" ", "_")
        
        # Search for images and character info concurrently
        image_task = self.search_images(tag, limit=limit)
        char_task = self.search_character(character_name)
        
        images, char_info = await asyncio.gather(image_task, char_task)
        
        # Combine all images
        all_images = []
        for source_images in images.values():
            all_images.extend(source_images)
        
        # Sort by score
        all_images.sort(key=lambda x: x.score, reverse=True)
        
        # Get best character info
        best_char = None
        for source_chars in char_info.values():
            if source_chars:
                best_char = source_chars[0]
                break
        
        return {
            "character": best_char,
            "images": all_images[:limit],
            "tags": list(set(tag for img in all_images for tag in img.tags[:10])),
        }
    
    async def build_prompt_for_character(
        self,
        character_name: str,
        additional_tags: List[str] = None,
    ) -> str:
        """
        Build an optimized prompt for generating a character.
        
        Args:
            character_name: Name of the character
            additional_tags: Extra tags to include
            
        Returns:
            Formatted prompt string
        """
        reference = await self.get_reference_for_character(character_name, limit=10)
        
        # Extract common tags
        tag_counts = {}
        for img in reference["images"]:
            for tag in img.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Get most common tags (excluding character name)
        common_tags = sorted(
            [(tag, count) for tag, count in tag_counts.items()
             if character_name.lower() not in tag.lower()],
            key=lambda x: x[1],
            reverse=True
        )[:15]
        
        # Build prompt
        tag = character_name.lower().replace(" ", "_")
        prompt_parts = [tag]
        
        # Add character traits from common tags
        trait_tags = [t[0] for t in common_tags if any(
            x in t[0] for x in ["hair", "eyes", "outfit", "dress", "uniform"]
        )]
        prompt_parts.extend(trait_tags[:5])
        
        # Add additional tags
        if additional_tags:
            prompt_parts.extend(additional_tags)
        
        # Add quality tags
        prompt_parts.extend(["masterpiece", "best quality", "detailed"])
        
        return ", ".join(prompt_parts)
    
    async def close(self):
        """Close all HTTP clients."""
        await self.danbooru.close()
        await self.gelbooru.close()
        await self.anilist.close()
        await self.jikan.close()


# Global search manager
_search_manager: Optional[WebSearchManager] = None


def get_search_manager(config: Optional[Dict] = None) -> WebSearchManager:
    """Get or create the global search manager."""
    global _search_manager
    if _search_manager is None:
        _search_manager = WebSearchManager(config)
    return _search_manager
