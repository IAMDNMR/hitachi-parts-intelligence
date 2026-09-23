"""
backend/app/modules/dealer/geocode.py

Resolve a user-given place (city or postcode) to coordinates for nearest-
dealer ranking. Order: (1) OpenStreetMap Nominatim (city centre / postcode);
(2) offline fallback: a city that exists in the DealerBranch graph.
The source is always returned so the answer can name it. Never guesses.
"""

from typing import Any, Dict, Optional

import httpx

from app.logging_config.logger import logger

_NOMINATIM = "https://nominatim.openstreetmap.org/search"
_PHOTON = "https://photon.komoot.io/api/"
_HEADERS = {"User-Agent": "HCME-Parts-Intelligence-prototype/1.0"}


def resolve_location(session, place: str, country: Optional[str] = None) -> Optional[Dict[str, Any]]:
    hit = _nominatim(place, (country or "").lower())
    if hit:
        return hit
    # Offline fallback: a city that exists in the dealer graph.
    row = session.run(
        """
        MATCH (d:DealerBranch)
        WHERE toLower(d.city) = toLower($place) AND d.latitude IS NOT NULL
          AND ($country IS NULL OR d.country = toUpper($country))
        RETURN avg(d.latitude) AS lat, avg(d.longitude) AS lon, count(d) AS n
        """,
        place=place, country=country,
    ).single()
    if row and row["n"]:
        return {"name": place, "lat": row["lat"], "lon": row["lon"], "source": "HCME dealer graph (city of existing dealer)"}
    return None


_CACHE: Dict[tuple, Dict[str, Any]] = {}


def _nominatim(place: str, country: str) -> Optional[Dict[str, Any]]:
    """Geocode via OpenStreetMap Nominatim, then Photon (also OSM) as backup.
    Only successful lookups are cached, so a transient failure is retried."""
    key = (place.lower(), country)
    if key in _CACHE:
        return _CACHE[key]
    hit = None
    try:
        params = {"q": place, "format": "json", "limit": 1}
        if country:
            params["countrycodes"] = country
        rows = httpx.get(_NOMINATIM, params=params, headers=_HEADERS, timeout=4.0).json()
        if rows:
            hit = {"name": rows[0].get("display_name", place), "lat": float(rows[0]["lat"]),
                   "lon": float(rows[0]["lon"]), "source": "OpenStreetMap Nominatim geocoding"}
    except Exception as e:
        logger.warning(f"Nominatim geocoding failed for '{place}': {e}")
    if not hit:
        try:
            q = f"{place} {country.upper()}".strip() if country else place
            feats = httpx.get(_PHOTON, params={"q": q, "limit": 1}, headers=_HEADERS, timeout=4.0).json().get("features", [])
            if feats:
                lon, lat = feats[0]["geometry"]["coordinates"]
                props = feats[0].get("properties", {})
                hit = {"name": ", ".join(x for x in (props.get("name"), props.get("country")) if x) or place,
                       "lat": float(lat), "lon": float(lon), "source": "OpenStreetMap Photon geocoding"}
        except Exception as e:
            logger.warning(f"Photon geocoding failed for '{place}': {e}")
    if hit:
        _CACHE[key] = hit
    return hit
