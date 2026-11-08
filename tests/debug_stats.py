import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import pandas as pd
from graph.visualization import visualization_node

df = pd.read_csv('statistics_data.csv')
metrics = []
for _, row in df.iterrows():
    metrics.append({
        'label': row['Metric'],
        'value': row['Value'],
        'unit': row['Unit'],
        'year': str(row['Year']),
        'geographical_scope': row['Geographical Scope'],
        'data_nature': row['Data Nature'],
        'verification_status': row['Verification Status'],
        'source_org': row['Source Organization'],
        'url': row['Source URL'],
        'evidence_excerpt': row['Evidence Excerpt']
    })

state = {
    'active_agents': ['statistics'],
    'structured_data': {'metrics': metrics, 'trends': [], 'comparisons': []},
    'include_unverified_viz': False,
    'agent_logs': [],
    'agent_timings': {}
}
res = visualization_node(state)
charts = res.get('chart_json', [])
print(f'Generated {len(charts)} charts:')
for i, c in enumerate(charts):
    d = json.loads(c)
    t = d.get('layout', {}).get('title', {})
    text = t.get('text', '') if isinstance(t, dict) else str(t)
    sub = d.get('layout', {}).get('title', {}).get('subtitle', {}).get('text', '') if isinstance(t, dict) else ''
    types = [tr.get('type') for tr in d.get('data', [])]
    print(f'  Chart {i+1}: Title="{text}" Subtitle="{sub}" Types={types}')
