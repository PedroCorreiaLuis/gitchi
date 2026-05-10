"""tama — a virtual pet for every git repo."""

from .models import Pet, Repo, Species, Stage, Vitals

__all__ = ["Pet", "Repo", "Species", "Stage", "Vitals", "__version__"]
__version__ = "0.2.0"
