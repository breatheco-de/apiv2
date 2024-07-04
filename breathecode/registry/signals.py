"""
For each signal you want other apps to be able to receive, you have to
declare a new variable here like this:
"""

from django import dispatch

asset_slug_modified = dispatch.Signal()
asset_readme_modified = dispatch.Signal()
asset_title_modified = dispatch.Signal()
asset_status_updated = dispatch.Signal()
