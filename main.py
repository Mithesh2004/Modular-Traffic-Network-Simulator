"""
main.py — Network topology + all simulation parameters.
Only this file needs to change for a new topology or tuning run.

Usage: python3 main.py
"""
import numpy as np
np.random.seed(42)

from traffic_sim import (
    Road, Junction, TrafficSource, Sink,
    Network, SimulationEngine, Visualizer, Statistics
)

# ══════════════════════════════════════════════════════════════════
#  SIMULATION PARAMETERS  ← tune these
# ══════════════════════════════════════════════════════════════════
TOTAL_STEPS       = 150     # how long the simulation runs
DT                = 1.0     # time per step (seconds / abstract unit)
VEHICLE_SPEED     = 0.3     # progress per step per unit length
SPAWN_RATE        = 0.4     # avg vehicles spawned per step (Poisson λ)
SPAWN_MODE        = 'poisson'  # 'poisson' or 'constant'

# Congestion-aware routing penalty:
#   effective_cost = road.length * (1 + CONGESTION_FACTOR * road.occupancy)
#   0   → pure shortest path (static, ignores congestion)
#   3   → moderate rerouting around busy roads
#   10  → aggressive avoidance of any congested road
CONGESTION_FACTOR = 3.0
# ══════════════════════════════════════════════════════════════════


def build_network() -> Network:
    net = Network()

    # Junctions: (id, type, x, y)
    junction_specs = [
        (0, 'source',  0, 2),
        (1, '3-way',   2, 4),
        (2, '2-way',   2, 0),
        (3, '3-way',   4, 4),
        (4, '4-way',   4, 1),
        (5, '3-way',   5, 1),
        (6, 'sink',    7, 4),
        (7, 'sink',    7, 1),
    ]
    for jid, jtype, x, y in junction_specs:
        net.add_junction(Junction(jid, jtype, x, y))

    # Roads: (id, from, to, capacity, length)
    road_specs = [
        ('R0', 0, 1, 6, 2.8),   # J0  → J1
        ('R1', 0, 2, 6, 2.8),   # J0  → J2
        ('R2', 1, 3, 5, 2.0),   # J1  → J3
        ('R3', 2, 4, 5, 2.2),   # J2  → J4
        ('R4', 3, 6, 5, 3.0),   # J3  → J6 
        ('R5', 3, 4, 4, 3.0),   # J3  → J4 
        ('R6', 5, 6, 5, 3.2),   # J5  → J6 
        ('R7', 5, 7, 5, 3.0),   # J5  → J7 
        ('R8', 1, 4, 4, 3.6),   # J1  → J4 
        ('R9', 4, 5, 6, 0.5),   # J4  → J5 
    ]
    for rid, frm, to, cap, length in road_specs:
        net.add_road(Road(rid, frm, to, cap, length))

    # Sources: (id, junction, destinations, rate, mode)
    net.add_source(TrafficSource('SRC0', 0,
                                 destinations=[6, 7],
                                 rate=SPAWN_RATE,
                                 mode=SPAWN_MODE))

    # Sinks
    net.add_sink(Sink('SINK6', 6))
    net.add_sink(Sink('SINK7', 7))

    return net


if __name__ == '__main__':
    net = build_network()

    engine = SimulationEngine(
        net,
        total_steps=TOTAL_STEPS,
        dt=DT,
        vehicle_speed=VEHICLE_SPEED,
        congestion_factor=CONGESTION_FACTOR,
    )
    stats = engine.run()

    metrics = Statistics(stats, net, total_steps=TOTAL_STEPS, dt=DT)
    metrics.summary()

    viz = Visualizer(net, engine.snapshots, stats, engine.dest_colors)
    viz.animate('output/simulation.gif', fps=10, step=2)
    viz.plot_statistics(metrics.results, 'output/stats.png')

    print("\nAll outputs saved to output/")
