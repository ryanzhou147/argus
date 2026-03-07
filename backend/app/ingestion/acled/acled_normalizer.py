from datetime import datetime
from typing import Dict, Any, Optional

from ...models.enums import EventType
from ..models import NormalizedRecord

class AcledNormalizer:
    """Normalizes raw ACLED event data into the internal NormalizedRecord format."""

    def __init__(self):
        # Map ACLED event_type to internal EventType
        self.type_mapping = {
            "Battles": EventType.GEOPOLITICS,
            "Explosions/Remote violence": EventType.GEOPOLITICS,
            "Protests": EventType.POLICY_REGULATION,
            "Riots": EventType.POLICY_REGULATION,
            "Strategic developments": EventType.GEOPOLITICS,
            "Violence against civilians": EventType.HUMANITARIAN_CRISIS,
        }

    def normalize(self, raw_record: Dict[str, Any]) -> NormalizedRecord:
        """
        Takes a raw dictionary from the ACLED API and returns a NormalizedRecord.
        If the record is malformed, raises ValueError.
        """
        try:
            # Extract basic identifiers
            source_native_id = str(raw_record["event_id_cnty"])
            
            # Map event type
            raw_type = raw_record.get("event_type", "")
            event_type = self.type_mapping.get(raw_type, EventType.GEOPOLITICS)
            
            # Synthesize title
            country = raw_record.get("country", "Unknown Location")
            location = raw_record.get("location", "Unknown City")
            date_str = raw_record.get("event_date", "")
            title = f"{raw_type} in {location}, {country} ({date_str})"
            
            # Parse dates
            try:
                # ACLED typically uses YYYY-MM-DD
                published_at = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                published_at = datetime.now() # Fallback

            # Description
            body = raw_record.get("notes", "No description provided.")
            
            # URL (synthesize if not present since ACLED might not provide direct links to sources consistently in basic responses)
            url = raw_record.get("source", "")
            if not url or not url.startswith("http"):
                 url = f"https://acleddata.com/data-id/{source_native_id}"
            
            # Location
            try:
                lat = float(raw_record.get("latitude"))
                lon = float(raw_record.get("longitude"))
            except (ValueError, TypeError):
                lat = None
                lon = None

            return NormalizedRecord(
                source_native_id=source_native_id,
                title=title,
                body=body,
                url=url,
                published_at=published_at,
                latitude=lat,
                longitude=lon,
                event_type=event_type,
                raw_metadata_json=raw_record,
            )
        except KeyError as e:
            raise ValueError(f"Missing required field in ACLED record: {e}")
