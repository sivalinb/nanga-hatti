"""Rebuild the publication figure from measured JSON. Requires requirements-visuals.txt."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator,FuncFormatter
root=Path(__file__).resolve().parents[1]
data=json.loads((root/'benchmarks/reports/latest.json').read_text())
rows=data['results']
labels=[f"{r['mode']} · c={r['concurrency']} · n={r['iterations']}" for r in rows]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none'})
fig,ax=plt.subplots(figsize=(12,5.2),facecolor='#faf8f0')
ax.set_facecolor('#faf8f0')
y=list(range(len(rows)))
ax.barh([v-.16 for v in y],[r['p50_ms'] for r in rows],height=.28,color='#24574b',label='p50 median')
ax.barh([v+.16 for v in y],[r['p95_ms'] for r in rows],height=.28,color='#b45d3e',label='p95 nearest rank')
ax.set_yticks(y,labels);ax.invert_yaxis();ax.set_xscale('log');ax.set_xlim(.5,20000)
ax.xaxis.set_major_locator(LogLocator(base=10));ax.xaxis.set_major_formatter(FuncFormatter(lambda v,p:f'{v:g}'))
ax.set_xlabel('Draft preparation in milliseconds · logarithmic scale');ax.grid(axis='x',alpha=.18)
ax.set_axisbelow(True)
for i,r in enumerate(rows):ax.text(r['p95_ms']*1.13,i+.16,f"{r['p95_ms']:.2f} ms",va='center',fontsize=10)
for sp in ax.spines.values():sp.set_visible(False)
ax.set_title('Nanga Hatti · measured preparation latency',loc='left',fontsize=17,pad=20,fontweight='bold')
ax.legend(loc='lower right',frameon=False)
fig.text(.02,.025,'Darwin arm64 · Python 3.12.14 · human review excluded · serialized SQLite engine · small live sample',fontsize=9,color='#5b665e')
fig.tight_layout(rect=[0,.065,1,1])
fig.savefig(root/'static/assets/benchmark.svg',metadata={'Date':data['created_at'],'Description':data['scope']})
print('Chart generated from benchmarks/reports/latest.json')
