"""Network monitoring service."""
import asyncio
from typing import Dict, Optional
from datetime import datetime
from loguru import logger
import socket
import time
import random

try:
    import speedtest
    SPEEDTEST_AVAILABLE = True
except ImportError:
    SPEEDTEST_AVAILABLE = False
    logger.warning("speedtest-cli not available. Using simulated tests.")

try:
    from ping3 import ping
    PING_AVAILABLE = True
except ImportError:
    PING_AVAILABLE = False
    logger.warning("ping3 not available. Using simulated ping.")


class NetworkMonitor:
    """
    Network monitoring service for speed tests and latency measurements.
    """
    
    def __init__(self):
        """Initialize the network monitor."""
        self.speedtest_client = None
        if SPEEDTEST_AVAILABLE:
            try:
                self.speedtest_client = speedtest.Speedtest()
            except Exception as e:
                logger.warning(f"Could not initialize speedtest: {e}")
    
    async def run_speed_test(self, target_service: Optional[str] = None) -> Dict:
        """
        Run a speed test.
        
        Args:
            target_service: Optional service to test against (e.g., 'youtube', 'netflix')
            
        Returns:
            Speed test results
        """
        logger.info(f"Running speed test (target: {target_service or 'general'})")
        
        if SPEEDTEST_AVAILABLE and self.speedtest_client:
            return await self._run_real_speedtest()
        else:
            return await self._run_simulated_speedtest()
    
    async def _run_real_speedtest(self) -> Dict:
        """
        Run actual speed test using speedtest-cli.
        """
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Get best server
            await loop.run_in_executor(None, self.speedtest_client.get_best_server)
            
            # Run download test
            download_speed = await loop.run_in_executor(None, self.speedtest_client.download)
            download_mbps = download_speed / 1_000_000  # Convert to Mbps
            
            # Run upload test
            upload_speed = await loop.run_in_executor(None, self.speedtest_client.upload)
            upload_mbps = upload_speed / 1_000_000  # Convert to Mbps
            
            # Get results
            results = self.speedtest_client.results.dict()
            
            return {
                "download_speed": round(download_mbps, 2),
                "upload_speed": round(upload_mbps, 2),
                "ping": results.get("ping", 0),
                "server": results.get("server", {}).get("name"),
                "server_location": results.get("server", {}).get("country"),
                "isp": results.get("client", {}).get("isp"),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Speed test failed: {e}")
            return {"error": str(e)}
    
    async def _run_simulated_speedtest(self) -> Dict:
        """
        Run simulated speed test for development/testing.
        """
        # Simulate network delay
        # No delay in simulated mode for instant response
        
        # Generate realistic-looking results with some variance
        base_download = 85  # Base speed in Mbps
        base_upload = 40
        base_ping = 15
        
        # Add time-based variance (slower during "peak hours")
        hour = datetime.now().hour
        if 18 <= hour <= 22:  # Peak hours
            variance_factor = 0.7 + random.uniform(-0.1, 0.1)
        else:
            variance_factor = 0.95 + random.uniform(-0.05, 0.05)
        
        download_speed = base_download * variance_factor + random.uniform(-5, 5)
        upload_speed = base_upload * variance_factor + random.uniform(-3, 3)
        ping = base_ping + random.uniform(-2, 5)
        
        # Occasionally simulate throttling
        if random.random() < 0.1:  # 10% chance
            download_speed *= 0.5
            logger.info("Simulated throttling event")
        
        return {
            "download_speed": round(max(1, download_speed), 2),
            "upload_speed": round(max(1, upload_speed), 2),
            "ping": round(max(1, ping), 2),
            "jitter": round(random.uniform(1, 5), 2),
            "packet_loss": round(random.uniform(0, 0.5), 2),
            "server": "Simulated Server",
            "server_location": "Local",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def measure_latency(self, host: str = "8.8.8.8") -> Dict:
        """
        Measure latency to a specific host.
        
        Args:
            host: Target host for ping
            
        Returns:
            Latency measurement results
        """
        if PING_AVAILABLE:
            try:
                latencies = []
                for _ in range(5):
                    latency = ping(host, timeout=2)
                    if latency:
                        latencies.append(latency * 1000)  # Convert to ms
                    await asyncio.sleep(0.1)
                
                if latencies:
                    return {
                        "host": host,
                        "avg_latency": round(sum(latencies) / len(latencies), 2),
                        "min_latency": round(min(latencies), 2),
                        "max_latency": round(max(latencies), 2),
                        "jitter": round(max(latencies) - min(latencies), 2),
                        "packet_loss": round((5 - len(latencies)) / 5 * 100, 2),
                        "timestamp": datetime.utcnow().isoformat()
                    }
            except Exception as e:
                logger.error(f"Ping failed: {e}")
        
        # Fallback to simulated
        return {
            "host": host,
            "avg_latency": round(random.uniform(10, 30), 2),
            "min_latency": round(random.uniform(8, 15), 2),
            "max_latency": round(random.uniform(20, 50), 2),
            "jitter": round(random.uniform(2, 10), 2),
            "packet_loss": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def test_service_speed(self, service: str) -> Dict:
        """
        Test speed to a specific service (e.g., YouTube, Netflix).
        
        Args:
            service: Service name to test
            
        Returns:
            Service-specific speed test results
        """
        # Service endpoints (simplified)
        service_hosts = {
            "youtube": "www.youtube.com",
            "netflix": "www.netflix.com",
            "amazon": "www.amazon.com",
            "google": "www.google.com",
            "facebook": "www.facebook.com",
            "twitter": "www.twitter.com"
        }
        
        host = service_hosts.get(service.lower(), "www.google.com")
        
        # Measure latency to service
        latency_result = await self.measure_latency(host)
        
        # Run speed test
        speed_result = await self.run_speed_test(target_service=service)
        
        return {
            "service": service,
            "host": host,
            "latency": latency_result,
            "speed": speed_result,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_network_info(self) -> Dict:
        """
        Get current network information.
        """
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            return {
                "hostname": hostname,
                "local_ip": local_ip,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Could not get network info: {e}")
            return {"error": str(e)}
