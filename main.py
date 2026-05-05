"""
5 Sources: S1, S4 (top-left), S2, S5 (mid-left), S3 (mid-right)
5 Sinks:   K2 (top-right), K3, K4 (bot-left), K1, K5 (bot-right)
6 Internal junctions (circles): J0-J5
All roads are bi-directional (one directional road each way).

Layout (x, y):

  S1(-0.5,4.5)  S4(-0.5,3.5)
        ↘       ↗
  S1,S4 ──► J0(3,4) ──► J1(6,4) ──► K2(9.5,4)
                  ▲│           ▲│
  S2,S5 ──► J2(3,2) ──► J3(6,2) ◄── S3(9.5,2)
                  ▲│           ▲│
  K3,K4  ◄─ J4(3,0) ──► J5(6,0) ──► K1,K5

Usage: python3 main.py
"""
import numpy as np
np.random.seed(42)

from traffic_sim import (
    Road, Junction, TrafficSource, Sink,
    Network, SimulationEngine, Visualizer, Statistics
)

# ═══════════════════════════════════════════════════════
#  SIMULATION PARAMETERS
# ═══════════════════════════════════════════════════════
TOTAL_STEPS       = 400     # how long the simulation runs
DT                = 1.0     # time per step (seconds / abstract unit)
VEHICLE_SPEED     = 0.1     # progress per step per unit length
SPAWN_RATE        = 0.4     # avg vehicles spawned per step (Poisson λ)
SPAWN_MODE        = 'poisson'  # 'poisson' or 'constant'

# Congestion-aware routing penalty:
#   effective_cost = road.length * (1 + CONGESTION_FACTOR * road.occupancy)
#   0   → pure shortest path (static, ignores congestion)
#   10  → aggressive avoidance of any congested road
CONGESTION_FACTOR = 5
# ═══════════════════════════════════════════════════════

# Road parameters
H_LEN  = 3.5   # horizontal road length (junction-to-junction)
V_LEN  = 3.5   # vertical road length
H_CAP  = 8     # capacity of horizontal roads
V_CAP  = 8     # capacity of vertical roads


def build_network() -> Network:
    net = Network()
     # Junctions: (id, type, x, y)
    junction_specs = [
        # Internal junctions
        (0,  '3-way',    3,    4  ),  # J0 top-left internal
        (1,  '3-way',    6,    4  ),  # J1 top-right internal
        (2,  '4-way',    3,    2  ),  # J2 mid-left internal
        (3,  '4-way',    6,    2  ),  # J3 mid-right internal
        (4,  '3-way',    3,    0  ),  # J4 bot-left internal
        (5,  '3-way',    6,    0  ),  # J5 bot-right internal
        # Sources
        (6,  'source',  -0.5,  4.5),  # S1 — top-left upper
        (7,  'source',  -0.5,  3.5),  # S4 — top-left lower
        (8,  'source',  -0.5,  2.5),  # S2 — mid-left upper
        (9,  'source',  -0.5,  1.5),  # S5 — mid-left lower
        (10, 'source',   9.5,  2.0),  # S3 — mid-right
        # Sinks
        (11, 'sink',     9.5,  4.0),  # K2 — top-right
        (12, 'sink',    -0.5, -0.5),  # K3 — bot-left upper
        (13, 'sink',    -0.5, -1.5),  # K4 — bot-left lower
        (14, 'sink',     9.5,  0.5),  # K1 — bot-right upper
        (15, 'sink',     9.5, -0.5),  # K5 — bot-right lower
    ]
    for jid, jtype, x, y in junction_specs:
        net.add_junction(Junction(jid, jtype, x, y))
        
        
    # Roads: (id, from, to, capacity, length)
    road_specs = [
        # ── Sources → J0 (S1, S4) ───────────────────────────
        ('R00',   6,  0, H_CAP, 3.5),  # S1  → J0
        ('R01',   0,  6, H_CAP, 3.5),  # J0  → S1  (reverse)
        ('R_S4',  7,  0, H_CAP, 3.5),  # S4  → J0
        ('R_S4b', 0,  7, H_CAP, 3.5),  # J0  → S4  (reverse)

        # ── Sources → J2 (S2, S5) ───────────────────────────
        ('R06',   8,  2, H_CAP, 3.5),  # S2  → J2
        ('R07',   2,  8, H_CAP, 3.5),  # J2  → S2  (reverse)
        ('R_S5',  9,  2, H_CAP, 3.5),  # S5  → J2
        ('R_S5b', 2,  9, H_CAP, 3.5),  # J2  → S5  (reverse)

        # ── Source → J3 (S3) ────────────────────────────────
        ('R10',  10,  3, H_CAP, 3.5),  # S3  → J3
        ('R11',   3, 10, H_CAP, 3.5),  # J3  → S3  (reverse)

        # ── J1 → Sink K2 ────────────────────────────────────
        ('R04',   1, 11, H_CAP, 3.5),  # J1  → K2
        ('R05',  11,  1, H_CAP, 3.5),  # K2  → J1  (reverse)

        # ── J4 → Sinks K3, K4 ───────────────────────────────
        ('R13',   4, 12, H_CAP, 3.5),  # J4  → K3
        ('R12',  12,  4, H_CAP, 3.5),  # K3  → J4  (reverse)
        ('R_K4',  4, 13, H_CAP, 3.5),  # J4  → K4
        ('R_K4b',13,  4, H_CAP, 3.5),  # K4  → J4  (reverse)

        # ── J5 → Sinks K1, K5 ───────────────────────────────
        ('R16',   5, 14, H_CAP, 3.5),  # J5  → K1
        ('R17',  14,  5, H_CAP, 3.5),  # K1  → J5  (reverse)
        ('R_K5',  5, 15, H_CAP, 3.5),  # J5  → K5
        ('R_K5b',15,  5, H_CAP, 3.5),  # K5  → J5  (reverse)

        # ── Internal: Horizontal ────────────────────────────
        ('R02',   0,  1, H_CAP, H_LEN),  # J0 → J1
        ('R03',   1,  0, H_CAP, H_LEN),  # J1 → J0
        ('R08',   2,  3, H_CAP, H_LEN),  # J2 → J3
        ('R09',   3,  2, H_CAP, H_LEN),  # J3 → J2
        ('R14',   4,  5, H_CAP, H_LEN),  # J4 → J5
        ('R15',   5,  4, H_CAP, H_LEN),  # J5 → J4

        # ── Internal: Vertical left (J0 ↕ J2 ↕ J4) ─────────
        ('R18',   0,  2, V_CAP, V_LEN),  # J0 ↓ J2
        ('R19',   2,  0, V_CAP, V_LEN),  # J2 ↑ J0
        ('R20',   2,  4, V_CAP, V_LEN),  # J2 ↓ J4
        ('R21',   4,  2, V_CAP, V_LEN),  # J4 ↑ J2

        # ── Internal: Vertical right (J1 ↕ J3 ↕ J5) ────────
        ('R22',   1,  3, V_CAP, V_LEN),  # J1 ↓ J3
        ('R23',   3,  1, V_CAP, V_LEN),  # J3 ↑ J1
        ('R24',   3,  5, V_CAP, V_LEN),  # J3 ↓ J5
        ('R25',   5,  3, V_CAP, V_LEN),  # J5 ↑ J3
    ]
    for rid, frm, to, cap, length in road_specs:
        net.add_road(Road(rid, frm, to, cap, length))

    # 5 sources, 5 sinks — each named individually
    # Vehicle color = destination sink (5 distinct colors auto-assigned)
    sinks = [11, 12, 13, 14, 15]  # K2, K3, K4, K1, K5
    net.add_source(TrafficSource('S1', 6,  destinations=sinks, rate=SPAWN_RATE, mode=SPAWN_MODE))
    net.add_source(TrafficSource('S4', 7,  destinations=sinks, rate=SPAWN_RATE, mode=SPAWN_MODE))
    net.add_source(TrafficSource('S2', 8,  destinations=sinks, rate=SPAWN_RATE, mode=SPAWN_MODE))
    net.add_source(TrafficSource('S5', 9,  destinations=sinks, rate=SPAWN_RATE, mode=SPAWN_MODE))
    net.add_source(TrafficSource('S3', 10, destinations=sinks, rate=SPAWN_RATE, mode=SPAWN_MODE))

    net.add_sink(Sink('K2', 11))
    net.add_sink(Sink('K3', 12))
    net.add_sink(Sink('K4', 13))
    net.add_sink(Sink('K1', 14))
    net.add_sink(Sink('K5', 15))

    return net


if __name__ == '__main__':
    net = build_network()
    engine = SimulationEngine(net, total_steps=TOTAL_STEPS, dt=DT,
                              vehicle_speed=VEHICLE_SPEED,
                              congestion_factor=CONGESTION_FACTOR)
    stats = engine.run()

    metrics = Statistics(stats, net, total_steps=TOTAL_STEPS, dt=DT)
    metrics.summary()

    viz = Visualizer(net, engine.snapshots, stats, engine.dest_colors)
    viz.animate('output/simulation.gif', fps=8, step=1)
    viz.plot_statistics(metrics.results, 'output/stats.png')
    print("\nAll outputs saved to output/")