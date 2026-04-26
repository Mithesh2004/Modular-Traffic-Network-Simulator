import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.cm as cm

CONGESTION_CMAP = LinearSegmentedColormap.from_list(
    'congestion', ['#2ecc71', '#f39c12', '#e74c3c'], N=256
)

def congestion_color(occupancy):
    return CONGESTION_CMAP(min(float(occupancy), 1.0))

class Visualizer:
    def __init__(self, network, snapshots, stats, dest_colors):
        self.network   = network
        self.snapshots = snapshots
        self.stats     = stats
        self.dest_colors = dest_colors

    # ------------------------------------------------------------------ helpers
    def _draw_static_base(self, ax):
        ax.set_facecolor('#0d1117')
        for junc in self.network.junctions.values():
            if junc.junction_id in self.network.sinks:
                c, ec = '#f85149', 'white'
                label = f'J{junc.junction_id}\n(sink)'
            elif junc.junction_id in self.network.sources:
                c, ec = '#3fb950', 'white'
                label = f'J{junc.junction_id}\n(src)'
            else:
                c, ec = '#388bfd', '#c9d1d9'
                label = f'J{junc.junction_id}'
            circle = plt.Circle((junc.x, junc.y), 0.30, color=c, ec=ec, lw=1.5, zorder=8)
            ax.add_patch(circle)
            ax.text(junc.x, junc.y, label, color='white', ha='center', va='center',
                    fontsize=6, fontweight='bold', zorder=9, linespacing=1.1)

    # ------------------------------------------------------------------ animate
    def animate(self, output_path='output/simulation.gif', fps=10, step=2):
        fig, ax = plt.subplots(figsize=(11, 8))
        fig.patch.set_facecolor('#0d1117')

        all_x = [j.x for j in self.network.junctions.values()]
        all_y = [j.y for j in self.network.junctions.values()]
        pad = 1.3
        ax.set_xlim(min(all_x)-pad, max(all_x)+pad)
        ax.set_ylim(min(all_y)-pad, max(all_y)+pad)
        ax.set_aspect('equal')
        ax.set_title('Traffic Network Simulation', color='#c9d1d9', fontsize=13, pad=10)
        for spine in ax.spines.values():
            spine.set_edgecolor('#30363d')
        ax.tick_params(colors='#c9d1d9')

        self._draw_static_base(ax)

        road_collection = {'arrows': [], 'labels': []}
        moving_scatter = ax.scatter([], [], s=50, zorder=10,
                                     edgecolors='white', linewidths=0.5)
        queued_scatter = ax.scatter([], [], s=70, marker='s', zorder=11,
                                     edgecolors='white', linewidths=0.8)

        time_txt = ax.text(0.02, 0.97, '', transform=ax.transAxes, color='#c9d1d9',
                           fontsize=10, va='top',
                           bbox=dict(boxstyle='round,pad=0.4', fc='#161b22', ec='#30363d', alpha=0.9))
        stats_txt = ax.text(0.02, 0.88, '', transform=ax.transAxes, color='#c9d1d9',
                            fontsize=8, va='top',
                            bbox=dict(boxstyle='round,pad=0.4', fc='#161b22', ec='#30363d', alpha=0.9))

        sm = cm.ScalarMappable(cmap=CONGESTION_CMAP, norm=plt.Normalize(0, 1))
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.02, aspect=20)
        cbar.set_label('Road Congestion', color='#c9d1d9', fontsize=8)
        cbar.ax.tick_params(colors='#c9d1d9', labelsize=7)
        cbar.set_ticks([0, 0.33, 0.66, 1.0])
        cbar.set_ticklabels(['Free', 'Mild', 'Heavy', 'Full'])

        dest_patches = [mpatches.Patch(color=c, label=f'→ Dest J{d}')
                        for d, c in self.dest_colors.items()]
        type_patches = [
            mpatches.Patch(color='#3fb950', label='Source'),
            mpatches.Patch(color='#f85149', label='Sink'),
            mpatches.Patch(color='#388bfd', label='Junction'),
            plt.scatter([], [], s=50, c='gray', edgecolors='white', lw=0.5, label='Moving ●'),
            plt.scatter([], [], s=70, c='gray', marker='s', edgecolors='white', lw=0.8, label='Queued ■'),
        ]
        ax.legend(handles=dest_patches + type_patches,
                  loc='lower right', facecolor='#161b22',
                  labelcolor='#c9d1d9', fontsize=7, edgecolor='#30363d', framealpha=0.9)

        frames = self.snapshots[::step]

        def update(fd):
            for a in road_collection['arrows']:
                a.remove()
            for a in road_collection['labels']:
                a.remove()
            road_collection['arrows'].clear()
            road_collection['labels'].clear()

            road_states = fd.get('road_states', {})
            for road in self.network.roads.values():
                fj = self.network.junctions[road.from_junction]
                tj = self.network.junctions[road.to_junction]
                rs  = road_states.get(road.road_id, {})
                occ = rs.get('occupancy', 0.0)
                qlen = rs.get('queue_len', 0)
                color = congestion_color(occ)

                dx, dy = tj.x - fj.x, tj.y - fj.y
                dist = max((dx**2 + dy**2)**0.5, 0.001)
                shrink = 0.32 / dist
                arr = ax.annotate('', xy=(tj.x - shrink*dx, tj.y - shrink*dy),
                            xytext=(fj.x + shrink*dx, fj.y + shrink*dy),
                            arrowprops=dict(arrowstyle='->', color=color, lw=2.5,
                                            connectionstyle='arc3,rad=0.05',
                                            mutation_scale=12), zorder=4)
                road_collection['arrows'].append(arr)

                mx, my = (fj.x+tj.x)/2, (fj.y+tj.y)/2
                px, py = -dy/dist, dx/dist
                txt = f'{road.road_id}' + (f' Q:{qlen}' if qlen > 0 else '')
                lbl = ax.text(mx + 0.2*px, my + 0.2*py, txt,
                              color='#e6c77a' if qlen > 0 else '#8b949e',
                              fontsize=6, ha='center', va='center', zorder=6,
                              path_effects=[pe.withStroke(linewidth=1.5, foreground='#0d1117')])
                road_collection['labels'].append(lbl)

            mv = [v for v in fd['vehicles'] if not v['queued']]
            qv = [v for v in fd['vehicles'] if v['queued']]

            moving_scatter.set_offsets([[v['x'], v['y']] for v in mv] or np.empty((0,2)))
            moving_scatter.set_color([v['color'] for v in mv] or [])
            queued_scatter.set_offsets([[v['x'], v['y']] for v in qv] or np.empty((0,2)))
            queued_scatter.set_color([v['color'] for v in qv] or [])

            total_q = sum(rs.get('queue_len', 0) for rs in road_states.values())
            worst = max(road_states.items(),
                        key=lambda x: x[1].get('occupancy', 0), default=(None, {}))
            time_txt.set_text(f'Time: {fd["time"]:.0f}')
            stats_txt.set_text(
                f'Moving : {len(mv)}\n'
                f'Queued : {len(qv)}\n'
                f'Worst  : {worst[0]} ({worst[1].get("occupancy",0)*100:.0f}%)'
            )
            return moving_scatter, queued_scatter, time_txt, stats_txt

        anim = FuncAnimation(fig, update, frames=frames, interval=100, blit=False)
        anim.save(output_path, writer=PillowWriter(fps=fps))
        plt.close()
        print(f"Animation → {output_path}")

    # ------------------------------------------------------------------ stats dashboard
    def plot_statistics(self, metrics_results, output_path='output/stats.png'):
        """
        metrics_results: Statistics().results dict
        4-panel layout:
          [0,0] Vehicle-level bar chart
          [0,1] Road occupancy + congestion time series
          [1,0] Junction metrics bar chart
          [1,1] Network metrics + summary table
        """
        r = metrics_results
        fig = plt.figure(figsize=(14, 10))
        fig.suptitle('Traffic Simulation — Performance Metrics Dashboard',
                     fontsize=14, fontweight='bold', y=0.98)
        fig.patch.set_facecolor('#f6f8fa')
        gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.35)
        axes = [[fig.add_subplot(gs[i, j]) for j in range(2)] for i in range(2)]

        PALETTE = ['#388bfd', '#3fb950', '#f39c12', '#e74c3c', '#9b59b6']

        # ── Panel 1: Vehicle-Level ────────────────────────────────────────────
        ax = axes[0][0]
        ax.set_facecolor('#f0f4f8')
        vkeys  = list(r['vehicle'].keys())
        vvals  = [r['vehicle'][k][0] for k in vkeys]
        vlabels = ['Travel\nDelay', 'Avg\nWait Time', 'Avg\nStops']
        bars = ax.bar(vlabels, vvals, color=PALETTE[:len(vkeys)], edgecolor='white',
                      width=0.5, zorder=3)
        for bar, val in zip(bars, vvals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                    f'{val:.2f}', ha='center', fontsize=9, fontweight='bold')
        ax.set_title('Vehicle-Level Metrics', fontweight='bold')
        ax.set_ylabel('Steps / Count')
        ax.grid(axis='y', alpha=0.4, zorder=0)
        ax.set_axisbelow(True)

        # ── Panel 2: Road/Segment-Level (occupancy + congestion steps) ────────
        ax = axes[0][1]
        ax.set_facecolor('#f0f4f8')
        road_ids   = sorted(r['road'].keys(), key=str)
        mean_occs  = [r['road'][rid]['mean_occupancy'] * 100 for rid in road_ids]
        mean_qlens = [r['road'][rid]['mean_queue_len']        for rid in road_ids]
        cong_steps = [r['road'][rid]['time_in_congestion']    for rid in road_ids]

        x = np.arange(len(road_ids))
        w = 0.26
        bars1 = ax.bar(x - w, mean_occs,  width=w, label='Avg Occupancy (%)',
                       color='#388bfd', edgecolor='white', zorder=3)
        bars2 = ax.bar(x,     mean_qlens, width=w, label='Avg Queue Len',
                       color='#f39c12', edgecolor='white', zorder=3)
        bars3 = ax.bar(x + w, cong_steps, width=w, label='Congestion Steps',
                       color='#e74c3c', edgecolor='white', zorder=3)

        ax.set_xticks(x); ax.set_xticklabels([str(r_) for r_ in road_ids], fontsize=7)
        ax.set_title('Road / Segment-Level Metrics', fontweight='bold')
        ax.set_ylabel('Value')
        ax.legend(fontsize=7, loc='upper right')
        ax.axhline(66, color='#e74c3c', lw=1, ls=':', alpha=0.5)
        ax.grid(axis='y', alpha=0.4, zorder=0); ax.set_axisbelow(True)

        # ── Panel 3: Junction-Level ───────────────────────────────────────────
        ax = axes[1][0]
        ax.set_facecolor('#f0f4f8')
        jids     = sorted(r['junction'].keys(), key=str)
        j_delay  = [r['junction'][j]['avg_delay_per_vehicle'] for j in jids]
        j_maxq   = [r['junction'][j]['max_queue_length']      for j in jids]
        j_util   = [r['junction'][j]['utilisation_pct']       for j in jids]

        x2 = np.arange(len(jids))
        ax2b = ax.twinx()
        ax.bar(x2 - 0.22, j_delay, width=0.22, label='Avg Delay (steps)',
               color='#9b59b6', edgecolor='white', zorder=3)
        ax.bar(x2,         j_maxq,  width=0.22, label='Max Queue Len',
               color='#e74c3c', edgecolor='white', zorder=3)
        ax2b.bar(x2 + 0.22, j_util, width=0.22, label='Utilisation %',
                 color='#3fb950', edgecolor='white', alpha=0.8, zorder=3)

        ax.set_xticks(x2)
        ax.set_xticklabels([f'J{j}' for j in jids], fontsize=8)
        ax.set_title('Junction-Level Metrics', fontweight='bold')
        ax.set_ylabel('Delay / Queue', color='#555')
        ax2b.set_ylabel('Utilisation %', color='#3fb950')
        ax2b.tick_params(axis='y', colors='#3fb950')

        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2b.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, fontsize=7, loc='upper right')
        ax.grid(axis='y', alpha=0.4, zorder=0); ax.set_axisbelow(True)

        # ── Panel 4: Network-Level summary ────────────────────────────────────
        ax = axes[1][1]
        ax.axis('off')
        ax.set_title('Network-Level & Summary', fontweight='bold')

        nv = r['network']
        rows = [
            ['Throughput',         f"{nv['throughput'][0]}",        'vehicles/step'],
            ['Arrival Rate',       f"{nv['arrival_rate'][0]}%",     'of spawned'],
            ['Network Efficiency', f"{nv['network_efficiency'][0]}", '0–1 scale'],
            ['─────────────',      '──────────',                    '──────────'],
            ['Total Spawned',  str(self.stats['total_spawned']),  'vehicles'],
            ['Total Arrived',  str(self.stats['total_arrived']),  'vehicles'],
            ['Avg Travel Time',
             f"{np.mean(self.stats['travel_times']):.2f}" if self.stats['travel_times'] else 'N/A',
             'steps'],
            ['Peak Active',    str(max(self.stats['active_counts'])), 'vehicles'],
        ]
        table = ax.table(cellText=rows,
                         colLabels=['Metric', 'Value', 'Unit'],
                         cellLoc='center', loc='center',
                         colWidths=[0.45, 0.28, 0.27])
        table.auto_set_font_size(False); table.set_fontsize(9.5); table.scale(1, 1.65)
        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor('#0d1117')
                cell.set_text_props(color='white', fontweight='bold')
            elif rows[row-1][0].startswith('─'):
                cell.set_facecolor('#dde3ea')
                cell.set_text_props(color='#888')
            else:
                cell.set_facecolor('#f0f4f8' if row % 2 == 0 else 'white')

        plt.savefig(output_path, dpi=130, bbox_inches='tight')
        plt.close()
        print(f"Stats dashboard → {output_path}")
