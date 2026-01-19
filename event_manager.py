"""
Event manager: tracks event metadata and assigns sequential event numbers.
"""
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class EventManager:
    """Manages event metadata and automatic numbering."""
    
    def __init__(self, data_dir: Path = Path("data")):
        self.data_dir = data_dir
        self.events_file = data_dir / "events.json"
        self.data_dir.mkdir(exist_ok=True)
        self.events = self._load_events()
    
    def _load_events(self) -> Dict:
        """Load events metadata from JSON file."""
        if self.events_file.exists():
            with open(self.events_file, 'r') as f:
                return json.load(f)
        return {"events": [], "next_event_num": 1}
    
    def _save_events(self):
        """Save events metadata to JSON file."""
        with open(self.events_file, 'w') as f:
            json.dump(self.events, f, indent=2)
    
    def get_next_event_num(self) -> int:
        """Get the next available event number."""
        return self.events["next_event_num"]
    
    def get_event_by_id(self, event_id: str) -> Optional[Dict]:
        """Look up an event by BCP ID."""
        for event in self.events["events"]:
            if event["event_id"] == event_id:
                return event
        return None
    
    def add_event(self, event_id: str, num_rounds: int, name: str = "") -> int:
        """
        Add a new event and get its event number.
        If event already exists, return its existing number.
        """
        # Check if event already exists
        existing = self.get_event_by_id(event_id)
        if existing:
            print(f"WARNING: Event {event_id} already exists as event #{existing['event_num']}")
            return existing['event_num']
        
        # Create new event
        event_num = self.get_next_event_num()
        event = {
            "event_num": event_num,
            "event_id": event_id,
            "name": name or f"Event {event_num}",
            "num_rounds": num_rounds,
            "scraped_date": datetime.now().isoformat(),
            "csv_file": f"events/event_{event_num:03d}.csv"
        }
        
        self.events["events"].append(event)
        self.events["next_event_num"] = event_num + 1
        self._save_events()
        
        print(f"Registered new event #{event_num}: {event_id}")
        return event_num
    
    def list_events(self):
        """Print all registered events."""
        if not self.events["events"]:
            print("No events registered yet.")
            return
        
        print("\nRegistered Events:")
        print("=" * 80)
        for event in self.events["events"]:
            print(f"  #{event['event_num']:03d}: {event['name']}")
            print(f"         ID: {event['event_id']}")
            print(f"         Rounds: {event['num_rounds']}")
            print(f"         File: {event['csv_file']}")
            print(f"         Scraped: {event['scraped_date'][:10]}")
            print()


if __name__ == "__main__":
    # Test
    manager = EventManager()
    manager.list_events()
