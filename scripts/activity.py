"""Render real public GitHub activity as a self-contained SVG (stdlib only)."""
import collections
import datetime
import html
import json
import os
from pathlib import Path
import urllib.request

QUERY = '''query {
  user(login: "LakshmiChaitra") {
    followers { totalCount }
    contributionsCollection {
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount weekday } } }
    }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      totalCount
      nodes { languages(first: 20, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } } }
    }
  }
}'''


def main():
    request = urllib.request.Request(
        'https://api.github.com/graphql',
        data=json.dumps({'query': QUERY}).encode(),
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'Content-Type': 'application/json', 'User-Agent': 'Chaitra-profile'},
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        result = json.load(response)
    if result.get('errors'):
        raise RuntimeError(result['errors'])
    user = result['data']['user']
    calendar = user['contributionsCollection']['contributionCalendar']
    weeks = calendar['weeks']
    days = [d for w in weeks for d in w['contributionDays']]
    longest = run = 0
    for d in days:
        run = run + 1 if d['contributionCount'] else 0
        longest = max(longest, run)
    current = 0
    streak_days = days[:-1] if days and not days[-1]['contributionCount'] else days
    for d in reversed(streak_days):
        if not d['contributionCount']:
            break
        current += 1
    sizes = collections.Counter()
    colors = {}
    for repo in user['repositories']['nodes']:
        for edge in repo['languages']['edges']:
            name = edge['node']['name']
            sizes[name] += edge['size']
            colors[name] = edge['node']['color'] or '#79e2d2'
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="650" viewBox="0 0 1000 650" role="img" aria-labelledby="title desc">',
             '<title id="title">Chaitra’s public GitHub activity</title>',
             '<desc id="desc">Past year of contributions and public non-fork repository language usage. Streaks count contribution days within the displayed year.</desc>',
             '<rect width="1000" height="650" rx="18" fill="#0d1117"/>',
             '<style>text{font-family:Arial,sans-serif;fill:#c9d1d9}.title{font-size:24px;font-weight:700;fill:#79e2d2}.muted{font-size:14px;fill:#8b949e}.number{font-size:30px;font-weight:700;fill:#e6edf3}</style>']

    def text(x, y, value, cls='', extra=''):
        parts.append(f'<text x="{x}" y="{y}" class="{cls}" {extra}>{html.escape(str(value))}</text>')

    text(36, 45, 'A year of building & exploring', 'title')
    total = calendar['totalContributions']
    metrics = [(f'{total:,}', 'Contributions'), (user['repositories']['totalCount'], 'Public original repos'),
               (user['followers']['totalCount'], 'Followers'), (f'{current} days', 'Current streak*')]
    for i, (value, label) in enumerate(metrics):
        x = 36 + i * 239
        text(x, 103, value, 'number')
        text(x, 128, label, 'muted')
    text(36, 173, 'Contribution calendar', 'title')
    palette = ['#161f2c', '#164c51', '#217879', '#38aaa4', '#79e2d2']
    maximum = max((d['contributionCount'] for d in days), default=0)
    for col, week in enumerate(weeks):
        for day in week['contributionDays']:
            count = day['contributionCount']
            level = 0 if count == 0 else min(4, 1 + int((count / max(1, maximum)) ** 0.5 * 3))
            x, y = 36 + col * 17.5, 194 + day['weekday'] * 20
            parts.append(f'<rect x="{x}" y="{y}" width="14" height="16" rx="3" fill="{palette[level]}"><title>{day["date"]}: {count} contributions</title></rect>')
    text(36, 360, f'Best streak*: {longest} days  ·  Most contributions in a day: {maximum}', 'muted')
    text(36, 404, 'Languages in my repositories', 'title')
    top = sizes.most_common(7)
    shown = sum(n for _, n in top)
    other = sum(sizes.values()) - shown
    if other:
        top.append(('Other', other))
        colors['Other'] = '#8b949e'
    total_bytes = sum(sizes.values()) or 1
    offset = 36
    for name, size in top:
        width = size / total_bytes * 928
        parts.append(f'<rect x="{offset:.2f}" y="427" width="{width:.2f}" height="14" fill="{colors[name]}"/>')
        offset += width
    for index, (name, size) in enumerate(top):
        x, y = 36 + (index % 2) * 470, 475 + (index // 2) * 29
        parts.append(f'<circle cx="{x + 5}" cy="{y - 5}" r="5" fill="{colors[name]}"/>')
        text(x + 20, y, f'{name}  {size / total_bytes:.1%}')
    text(36, 610, '*Streaks cover this calendar; current streak allows today to be in progress.', 'muted')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%d %b %Y')
    text(36, 633, f'Updated {stamp} UTC · Public GitHub data · Repository language bytes, not proficiency', 'muted')
    parts.append('</svg>')
    destination = Path(__file__).resolve().parents[1] / 'assets/github-activity.svg'
    destination.write_text('\n'.join(parts))
    print(f'Generated {destination.name}: {total} contributions, {len(sizes)} languages')


if __name__ == '__main__':
    main()
