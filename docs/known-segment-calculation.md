# Known Segment Calculation

The implementation-plan sample uses two independent 60-second streams on a
0.8 km segment:

- Motorcycle count: 40 + 35 = 75.
- Motorcycle volume: 75 * 3600 / 60 = 4500 vehicles/hour.
- Motorcycle VKT: 4500 * 0.8 = 3600 vehicle-km/hour.
- Motorcycle CO: 3600 * 14 = 50400 g/hour.

Run the executable sample from `backend/` with:

```text
python -m scripts.known_segment_calculation
```
