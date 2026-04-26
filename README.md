# Traffic Simulator — Project Documentation

A modular, discrete-time traffic simulator for directed road networks with congestion-aware dynamic routing, vehicle queuing, and performance metrics.

---

## Project Structure

```
traffic_sim_project/
├── main.py                        # Network topology + all simulation parameters
├── traffic_sim/
│   ├── __init__.py                # Package exports
│   ├── vehicle.py                 # Vehicle (source, dest, route, progress)
│   ├── road.py                    # Directional Road (capacity, queue)
│   ├── junction.py                # Junction (2/3/4-way, round-robin scheduling)
│   ├── source.py                  # TrafficSource (Poisson / constant rate)
│   ├── sink.py                    # Sink (absorbs arrived vehicles)
│   ├── network.py                 # Network graph + Dijkstra routing
│   ├── engine.py                  # Time-step simulation engine
│   ├── visualizer.py              # GIF animation + statistics dashboard
│   └── statistics.py             # Performance metrics computation
└── output/
    ├── simulation.gif             # Animated network visualization
    └── stats.png                  # 4-panel metrics dashboard
```

---

## Usage

```bash
pip install matplotlib numpy
python3 main.py
```

Outputs written to `output/`:
- `simulation.gif` — animated visualization of vehicle movement and congestion
- `stats.png` — 4-panel performance metrics dashboard

---

## Configurable Parameters (`main.py`)

All tunable values are declared at the top of `main.py`. No library files need to be modified.

| Parameter | Default | Description |
|---|---|---|
| `TOTAL_STEPS` | `150` | Total simulation duration (time steps) |
| `DT` | `1.0` | Duration of each time step |
| `VEHICLE_SPEED` | `0.3` | Vehicle progress per step per unit road length |
| `SPAWN_RATE` | `0.4` | Average vehicles spawned per step (Poisson λ) |
| `SPAWN_MODE` | `'poisson'` | `'poisson'` for random, `'constant'` for fixed rate |
| `CONGESTION_FACTOR` | `3.0` | Routing penalty weight for congested roads (see below) |

### Congestion Factor Explained

Vehicles reroute dynamically at every junction using:

```
effective_cost = road.length × (1 + CONGESTION_FACTOR × road.occupancy)
```

| Value | Behaviour |
|---|---|
| `0` | Static shortest path — ignores all congestion |
| `3` | Moderate rerouting when roads exceed ~40% occupancy |
| `10` | Aggressive avoidance of even mildly busy roads |

---

## Defining a New Network Topology

Only `main.py` changes. Update `junction_specs` and `road_specs`:

```python
# Junctions: (id, type, x, y)
junction_specs = [
    (0, 'source',  0, 0),
    (1, '3-way',   3, 2),
    (2, 'sink',    6, 2),
]

# Roads: (id, from, to, capacity, length)
road_specs = [
    ('R0', 0, 1, 5, 2.0),
    ('R1', 1, 2, 5, 2.0),
]

net.add_source(TrafficSource('S0', 0, destinations=[2], rate=0.4, mode='poisson'))
net.add_sink(Sink('SK2', 2))
```

Supported junction types: `'source'`, `'sink'`, `'2-way'`, `'3-way'`, `'4-way'`, `'intersection'`

---

## Library Components

### `vehicle.py` — Vehicle
Each vehicle carries a source, destination, computed route, and real-time progress along its current road.

| Attribute | Description |
|---|---|
| `route` | Ordered list of junction IDs (updated at each junction during rerouting) |
| `progress` | Float 0.0 → 1.0 along current road |
| `wait_time` | Cumulative time spent queued |
| `stop_count` | Number of times vehicle entered a queue |
| `free_flow_time` | Theoretical minimum travel time (computed at spawn) |

---

### `road.py` — Road
Directional road segment with finite vehicle capacity and a queue at the junction end.

| Attribute | Description |
|---|---|
| `capacity` | Maximum vehicles on road simultaneously |
| `length` | Used as routing cost and progress denominator |
| `vehicles` | All vehicles currently on the road |
| `queue` | Vehicles at progress=1.0 waiting to enter next junction |
| `occupancy` | `len(vehicles) / capacity` — used for congestion routing |

---

### `junction.py` — Junction
Supports 2-way, 3-way, and 4-way junctions. Uses **round-robin scheduling** to fairly serve competing incoming roads.

```python
junc.schedule_next_incoming()  # returns next incoming road with a queued vehicle
```

---

### `source.py` — TrafficSource
Spawns vehicles at a junction each time step.

- **Poisson mode**: `n ~ Poisson(rate)` vehicles per step — models random real-world arrivals
- **Constant mode**: exactly `int(rate)` vehicles per step

---

### `network.py` — Network
Holds all junctions, roads, sources, and sinks. Provides two routing methods:

```python
net.shortest_path(from_id, to_id)
# Static Dijkstra on road lengths — used at spawn time

net.congestion_aware_path(from_id, to_id, congestion_factor)
# Dynamic Dijkstra with effective_cost = length × (1 + factor × occupancy)
# Called at every junction for live rerouting
```

---

### `engine.py` — SimulationEngine
Runs the time-step loop:

1. **Spawn** — TrafficSource generates vehicles, initial route computed via static Dijkstra
2. **Move** — all vehicles advance by `vehicle_speed / road.length` progress per step
3. **Process junctions** — round-robin selects next vehicle; dynamic rerouting applied; blocked vehicles accumulate wait time
4. **Snapshot** — frame saved for animation; road and junction stats recorded

---

### `statistics.py` — Statistics

Computes all performance metrics from engine output. Instantiate after `engine.run()`:

```python
metrics = Statistics(stats, net, total_steps=TOTAL_STEPS, dt=DT)
metrics.summary()   # prints full report to terminal
```

#### Metrics Reference

**Vehicle-Level**

| Metric | Formula | Meaning |
|---|---|---|
| Avg Travel Time Delay | mean(actual − free_flow) | Extra time caused by congestion per vehicle |
| Avg Wait Time | mean(wait_time per vehicle) | Time spent queued at junctions |
| Avg Stops per Vehicle | mean(stop_count per vehicle) | How many times each vehicle entered a queue |

**Network-Level**

| Metric | Formula | Meaning |
|---|---|---|
| Throughput | arrived / total_steps | Vehicles completing journeys per time step |
| Arrival Rate | arrived / spawned × 100 | Percentage of vehicles that reached a sink |
| Network Efficiency | mean(free_flow) / mean(actual) | 1.0 = no congestion; lower = more delay |

**Road/Segment-Level** (per road)

| Metric | Meaning |
|---|---|
| Mean Occupancy | Average vehicles / capacity over all steps |
| Mean Queue Length | Average vehicles waiting at road end |
| Congestion Steps | Steps where occupancy exceeded 66% |

**Junction-Level** (per non-source/sink junction)

| Metric | Meaning |
|---|---|
| Avg Delay per Vehicle | Total delay attributed to junction / vehicles served |
| Max Queue Length | Worst-case queue observed at any point |
| Utilisation % | Fraction of steps where at least one vehicle was queued |

---

### `visualizer.py` — Visualizer

**`animate(output_path, fps, step)`** — saves GIF:
- Roads colored **green → yellow → red** by live occupancy
- Moving vehicles shown as **circles ●**, queued vehicles as **squares ■**
- Road labels show queue count when non-zero (e.g. `R9 Q:3`)
- HUD displays active/queued counts and worst congested road

**`plot_statistics(metrics_results, output_path)`** — saves 4-panel PNG dashboard:
- Panel 1: Vehicle-level bar chart
- Panel 2: Road occupancy and congestion steps per road
- Panel 3: Junction delay, max queue, and utilisation
- Panel 4: Network-level summary table

---

## Design Decisions

| Aspect | Decision | Rationale |
|---|---|---|
| Simulation type | Time-step (not discrete-event) | Simpler to implement; sufficient for educational use |
| Routing | Dynamic Dijkstra with congestion penalty | Models real-world GPS rerouting (Waze/Google Maps behaviour) |
| Junction scheduling | Round-robin | Fair service across all incoming roads; prevents starvation |
| Queuing | On-road queue at junction end | Reflects real vehicle behaviour; enables spillback detection |
| Modularity | All topology in `main.py` only | New networks require zero library changes |

---

## Example Output (Test Network)

```
Simulation started: 150 steps  [speed=0.3, congestion_factor=3.0]
Done. Spawned=65  Arrived=45

── Network-Level Metrics ──────────────
  Throughput              0.30  vehicles/step
  Arrival Rate           69.2  %
  Network Efficiency      0.91  ratio (0–1)

── Most Congested Road ────────────────
  R7: mean_occupancy=0.395, congestion_steps=28

── Busiest Junction ───────────────────
  J5: utilisation=10.7%, max_queue=2
```
