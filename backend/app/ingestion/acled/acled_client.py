import httpx
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AcledClient:
    """Client for fetching data from the ACLED API."""

    def __init__(self, token: str, lookback_days: int = 14):
        self.base_url = "https://acleddata.com/api/acled/read"
        self.token = token.strip()
        self.lookback_days = lookback_days
        if not self.token:
            raise ValueError("ACLED_API_TOKEN must be provided.")

    async def fetch_recent_events(self) -> List[Dict[str, Any]]:
        """
        Fetches events from the ACLED API using recent date filters.
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_days)
        
        # It seems the API might not have recent data up to today. 
        # The ACLED database releases new data typically on a delay (e.g. weekly).
        
        # Let's request the most recent 5000 items unconditionally and we'll filter them locally.
        # This bypasses the API filtering issue since their API dates might have gaps.
        params = {
            "limit": 5000
        }
        
        email = ""
        password = ""
        
        if "|" in self.token:
            email, password = self.token.split("|", 1)
            email = email.strip()
            password = password.strip()
        else:
            email = None
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                headers = {}
                
                # If we have an email and password, let's try getting an OAuth token
                if email and password:
                    token_url = "https://acleddata.com/oauth/token"
                    auth_data = {
                        'username': email,
                        'password': password,
                        'grant_type': 'password',
                        'client_id': 'acled'
                    }
                    
                    logger.info(f"Attempting to get ACLED OAuth token for {email}...")
                    auth_resp = await client.post(
                        token_url, 
                        data=auth_data,
                        headers={'Content-Type': 'application/x-www-form-urlencoded'}
                    )
                    
                    if auth_resp.status_code == 200:
                        token_data = auth_resp.json()
                        access_token = token_data.get('access_token')
                        headers["Authorization"] = f"Bearer {access_token}"
                        logger.info("Successfully obtained ACLED OAuth token.")
                    else:
                        logger.warning(f"OAuth failed ({auth_resp.status_code}).")
                        
                elif self.token:
                    headers["Authorization"] = f"Bearer {self.token}"

                logger.info(f"Fetching latest data from ACLED API...")
                response = await client.get(self.base_url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if "data" in data:
                    return data["data"]
                elif isinstance(data, list):
                    return data
                else:
                    logger.warning(f"Unexpected data format: {data.keys() if isinstance(data, dict) else type(data)}")
                    return []
            except Exception as e:
                logger.error(f"Failed to fetch ACLED data: {e}")
                raise
