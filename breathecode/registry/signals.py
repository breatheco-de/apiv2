"""For each signal you want other apps to be able to receive, you have to declare a new variable here like this:"""

from task_manager.django.dispatch import Emisor

emisor = Emisor("breathecode.registry")

asset_slug_modified = emisor.signal("asset_slug_modified")
asset_readme_modified = emisor.signal("asset_readme_modified")
asset_title_modified = emisor.signal("asset_title_modified")
asset_status_updated = emisor.signal("asset_status_updated")
