"""Atlas: the shared map dataset (Hugging Face ``Apokryf/minimap-of-uce``) and how findings land in it."""

from gitrecon.atlas.paths import domain_path, ip_path
from gitrecon.atlas.update import AtlasUpdate

__all__ = ["AtlasUpdate", "domain_path", "ip_path"]
