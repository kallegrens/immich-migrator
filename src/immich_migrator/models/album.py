"""Album model representing a collection of assets."""

from datetime import datetime

from pydantic import BaseModel, Field

from .asset import Asset


class Album(BaseModel):
    """Represents an album (collection of assets) from Immich."""

    id: str = Field(pattern=r"^[0-9a-f-]{36}$|^UNALBUMMED_ASSETS$")
    album_name: str = Field(min_length=1)
    asset_count: int = Field(ge=0)
    assets: list[Asset] = Field(default_factory=list)
    created_at: datetime | None = None
    shared: bool = False

    @property
    def is_virtual_unalbummed(self) -> bool:
        """Check if this is the virtual 'Unalbummed Assets' album."""
        return self.id == "UNALBUMMED_ASSETS"

    @classmethod
    def create_unalbummed_album(cls, assets: list[Asset]) -> "Album":
        """Create virtual album for assets not in any album.

        Args:
            assets: List of assets without album membership

        Returns:
            Album instance representing unalbummed assets
        """
        return cls(
            id="UNALBUMMED_ASSETS",
            album_name="Unalbummed Assets",
            asset_count=len(assets),
            assets=assets,
        )
