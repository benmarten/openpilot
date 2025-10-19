#!/usr/bin/env python3
import numpy as np
import json
import os
from openpilot.common.params import Params
from openpilot.common.conversions import Conversions as CV

# ENHANCED: Feature 4 - Speed Limit Controller (SLC)
MIN_SPEED_LIMIT = 15  # mph
MAX_SPEED_LIMIT = 100  # mph
OSM_DATABASE_PATH = "/data/openpilot/selfdrive/controls/lib/osm_speed_limits/"

class SpeedLimitController:
  def __init__(self):
    self.params = Params()
    self.current_limit = None
    self.osm_data = {}
    self.current_state = None
    self._load_osm_database()

  def _load_osm_database(self):
    """Load OSM database for selected state"""
    state = self.params.get("SpeedLimitControlState", encoding='utf-8')
    if not state:
      return

    if state == self.current_state and self.osm_data:
      return

    db_file = os.path.join(OSM_DATABASE_PATH, f"{state}.json")
    try:
      if os.path.exists(db_file):
        with open(db_file, 'r') as f:
          self.osm_data = json.load(f)
          self.current_state = state
    except Exception as e:
      print(f"Failed to load OSM database for {state}: {e}")
      self.osm_data = {}

  def get_enabled(self):
    return self.params.get_bool("SpeedLimitControlEnabled")

  def get_offset_percent(self):
    return int(self.params.get("SpeedLimitOffset", encoding='utf-8') or "0")

  def get_speed_limit_from_osm(self, lat, lon):
    """Lookup speed limit from OSM database using GPS coordinates"""
    if not self.osm_data:
      self._load_osm_database()
      if not self.osm_data:
        return None

    # Grid-based lookup (4 decimal places = ~11m precision)
    lat_key = round(lat, 4)
    lon_key = round(lon, 4)
    grid_key = f"{lat_key},{lon_key}"

    if grid_key in self.osm_data:
      return self.osm_data[grid_key]

    # Search nearby cells (~50m radius)
    for dlat in [-0.0005, 0, 0.0005]:
      for dlon in [-0.0005, 0, 0.0005]:
        nearby_key = f"{round(lat + dlat, 4)},{round(lon + dlon, 4)}"
        if nearby_key in self.osm_data:
          return self.osm_data[nearby_key]

    return None

  def get_speed_limit(self, sm):
    """
    Get speed limit from OSM database
    Returns: (speed_limit_mph, source) or (None, None)
    """
    if 'gpsLocationExternal' not in sm.alive or not sm.valid['gpsLocationExternal']:
      return (None, None)

    gps = sm['gpsLocationExternal']
    lat = gps.latitude
    lon = gps.longitude

    osm_limit = self.get_speed_limit_from_osm(lat, lon)
    if osm_limit and MIN_SPEED_LIMIT <= osm_limit <= MAX_SPEED_LIMIT:
      return (osm_limit, "osm")

    return (None, None)

  def apply_offset(self, speed_limit_mph):
    offset_percent = self.get_offset_percent()
    multiplier = 1.0 + (offset_percent / 100.0)
    target_mph = speed_limit_mph * multiplier
    return np.clip(target_mph, MIN_SPEED_LIMIT, MAX_SPEED_LIMIT)

  def get_target_speed(self, sm, v_cruise_kph):
    """
    Calculate target cruise speed
    Returns: target speed in kph, or None if SLC inactive
    """
    if not self.get_enabled():
      return None

    speed_limit_mph, source = self.get_speed_limit(sm)

    if speed_limit_mph is None:
      self.current_limit = None
      return None

    self.current_limit = speed_limit_mph
    target_mph = self.apply_offset(speed_limit_mph)
    target_kph = target_mph * CV.MPH_TO_KPH

    return target_kph

  def smooth_transition(self, current_kph, target_kph, dt=0.05):
    """Rate-limited speed transition"""
    if target_kph is None:
      return current_kph

    max_change_rate = float(self.params.get("SpeedLimitTransitionRate", encoding='utf-8') or "2.0")
    max_change_kph = max_change_rate * CV.MPH_TO_KPH * dt

    diff = target_kph - current_kph

    if abs(diff) <= max_change_kph:
      return target_kph
    else:
      return current_kph + np.sign(diff) * max_change_kph
