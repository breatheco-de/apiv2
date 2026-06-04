"""Base classes for monitoring reports."""

from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Any, Optional

from django.utils import timezone


class BaseReport(ABC):
    """Base class for all monitoring reports."""

    report_type: str = "base"

    def __init__(self, report_date: Optional[date] = None, academy_id: Optional[int] = None):
        self.report_date = report_date or (timezone.now() - timedelta(days=1)).date()
        self.academy_id = academy_id
        self.stdout = None  # Set by management command for logging

    def log(self, message: str, style: str = "SUCCESS"):
        """Log to stdout if available (from management command)."""
        if self.stdout:
            style_fn = getattr(self.stdout.style, style, self.stdout.style.SUCCESS)
            self.stdout.write(style_fn(message))

    @abstractmethod
    def fetch_data(self) -> dict[str, Any]:
        """Fetch raw data from BigQuery or other sources."""
        pass

    @abstractmethod
    def process_data(self, raw_data: dict[str, Any]) -> list[Any]:
        """Process raw data and return model instances to save."""
        pass

    @abstractmethod
    def save_reports(self, reports: list[Any]) -> int:
        """Save processed reports to database. Returns count saved."""
        pass

    def generate(self) -> int:
        """Main entry point. Returns number of reports generated."""
        self.log(f"Starting {self.report_type} report for {self.report_date}")

        raw_data = self.fetch_data()
        self.log(f"Fetched data for {len(raw_data.get('user_ids', []))} users")

        reports = self.process_data(raw_data)
        self.log(f"Processed {len(reports)} reports")

        count = self.save_reports(reports)
        self.log(f"Saved {count} reports")

        return count

