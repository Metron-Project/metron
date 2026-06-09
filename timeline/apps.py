from pathlib import Path

import frontmatter
import markdown
from django.apps import AppConfig

from metron import settings

ENTRIES_PATH = Path(settings.BASE_DIR, "timeline", "entries")


class TimelineConfig(AppConfig):
    name = "timeline"

    def ready(self) -> None:
        """Fetch all timeline entries."""
        self.entries = []
        for entry in ENTRIES_PATH.rglob("*.md"):
            # Read and parse the markdown file for metadata and content.
            metadata, content = frontmatter.parse(entry.read_text(encoding="utf-8"))

            md = markdown.Markdown()
            html = md.convert(content)

            # Strip `.md` file extension from filename and split it into the
            # date (for sorting) and slug (for linking).
            key, slug = entry.name[:-3].split("_", 1)

            icon_color = metadata.get("icon_color")
            if not icon_color:
                icon_color = "has-background-primary"

            entry_data = {
                "key": key,
                "slug": slug,
                "title": metadata["title"],
                "date": metadata["date"],
                "icon": metadata["icon"],
                "icon_color": icon_color,
                "content": html,
            }

            self.entries.append(entry_data)

        # Sort the entries in reverse-chronological order.
        self.entries.sort(key=lambda e: e["key"], reverse=True)
