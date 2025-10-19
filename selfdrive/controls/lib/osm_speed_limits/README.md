# OSM Speed Limit Database

This directory contains OpenStreetMap (OSM) speed limit data by US state.

## Format

Each state has a JSON file named `{STATE}.json` (e.g., `CA.json`, `TX.json`)

**JSON Structure:**
```json
{
  "37.7749,-122.4194": 35,
  "37.7750,-122.4195": 35,
  "37.7751,-122.4196": 45
}
```

- **Key**: `"latitude,longitude"` (rounded to 4 decimal places, ~11m precision)
- **Value**: Speed limit in mph

## Usage

1. Download pre-built state database from repository releases
2. Copy to this directory: `/data/openpilot/selfdrive/controls/lib/osm_speed_limits/`
3. Enable SLC in settings
4. Select your state
5. Set speed offset percentage

## Database Generation

To generate your own database from OSM data:

```bash
# Download state extract from GeoFabrik
wget https://download.geofabrik.de/north-america/us/california-latest.osm.pbf

# Use osm2pgsql or similar tool to extract speed limits
# Grid to 4 decimal places (~11m)
# Export as JSON in the format above
```

## Storage

- Average database size: 50-200MB per state
- Recommended: Only download states you drive in
- Update periodically for accurate data

## Limitations

- OSM data may be outdated
- Not all roads have speed limits in OSM
- GPS accuracy affects lookup (~10m typical)
- Cannot detect temporary speed zones (construction, school zones)
