# Tøyenbadet for Home Assistant

Custom integration for keeping eye on the capacity at Tøyenbadet.

## Capacity status

The capacity-status sensor exposes `good`, `near`, or `over`, with English and
Norwegian display labels. Missing or unexpected status values display as unknown;
valid visitor counts remain available. Existing entity IDs and raw state values
are preserved.

For a green, amber, or red occupancy tile, paste
[the dashboard example](examples/capacity-dashboard.yaml) into a manual dashboard
card. Replace the entity IDs if your installation uses different names. The
example uses built-in cards and includes a neutral fallback when capacity status
is unknown or unavailable. Colors follow the API category, not assumed numeric
thresholds; they do not guarantee admission.
