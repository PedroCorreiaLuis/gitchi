"""gitchi — a virtual pet for every git repo."""

from .models import Pet, Rarity, Repo, Species, Stage, Vitals

__all__ = ["Pet", "Rarity", "Repo", "Species", "Stage", "Vitals", "__version__"]
__version__ = "0.5.0"
