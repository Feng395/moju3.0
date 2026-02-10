"""
MCP Client with connection pooling and retry mechanism
"""
import requests
import json
import logging
from typing import Dict, Any, Optional
import asyncio
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP Client (SSE mode)"""
    
    def __init__(
        self, 
        base_url: str, 
        timeout: Optional[int] = None,
        pool_size: Optional[int] = None,
        max_retries: Optional[int] = None
    ):
        """Initialize MCP Client"""
        self.base_url = base_url.rstrip('/')
        
        # Read config from environment variables
        self.timeout = timeout or int(os.getenv('MCP_CLIENT_TIMEOUT', '300'))
        pool_size = pool_size or int(os.getenv('MCP_CLIENT_POOL_SIZE', '30'))
        max_retries = max_retries or int(os.getenv('MCP_CLIENT_MAX_RETRIES', '3'))
        
        # Create Session (connection pool reuse)
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"]
        )
        
        # Configure connection pool adapter
        adapter = HTTPAdapter(
            pool_connections=pool_size,
            pool_maxsize=pool_size,
            max_retries=retry_strategy
        )
        
        # Mount adapter
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        self.session_id = None
        
        logger.info(
            f"MCP Client initialized: {self.base_url}, "
            f"timeout={self.timeout}s, pool={pool_size}, retries={max_retries}"
        )
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP tool"""
        try:
            logger.info(f"Calling MCP tool: {server_name}.{tool_name}")
            logger.debug(f"Arguments: {arguments}")
            
            result = await self._call_tool_direct(tool_name, arguments)
            return result
            
        except Exception as e:
            logger.error(f"MCP tool call failed: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"MCP tool call failed: {str(e)}"
            }
    
    async def _call_tool_direct(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Direct tool call with connection pool"""
        import time
        start_time = time.time()
        
        try:
            url = f"{self.base_url}/call_tool"
            
            request_body = {
                "tool_name": tool_name,
                "arguments": arguments
            }
            
            logger.debug(f"Sending request: {url}")
            logger.debug(f"Body: {json.dumps(request_body, ensure_ascii=False)}")
            
            # Use session (connection pool reuse)
            response = await asyncio.to_thread(
                self.session.post,
                url,
                json=request_body,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Log performance
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Tool call success: {tool_name} ({duration_ms}ms)")
            
            # Slow query warning
            slow_threshold = int(os.getenv('FEATURE_RECOGNITION_SLOW_THRESHOLD', '5000'))
            if duration_ms > slow_threshold:
                logger.warning(
                    f"Slow MCP call: {tool_name} took {duration_ms}ms "
                    f"(threshold: {slow_threshold}ms)"
                )
            
            return result
        
        except requests.HTTPError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"HTTP error: {e.response.status_code} - {e.response.text} "
                f"({duration_ms}ms)"
            )
            return {
                "status": "error",
                "message": f"HTTP error: {e.response.status_code}",
                "detail": e.response.text
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Tool call failed: {e} ({duration_ms}ms)", exc_info=True)
            return {
                "status": "error",
                "message": f"Tool call failed: {str(e)}"
            }
    
    async def close(self):
        """Close client and connection pool"""
        if hasattr(self, 'session') and self.session:
            self.session.close()
        self.session_id = None
        logger.info("MCP client closed (connection pool released)")
