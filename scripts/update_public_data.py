"""Fetch auditable public attention metrics. Standard library only; never invent points."""
from __future__ import annotations

import argparse
import concurrent.futures
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SHANGHAI = timezone(timedelta(hours=8))
UA = 'MarketOpportunityRadar/1.1 (https://github.com/yxt1017/market-opportunity-radar)'


def get_json(url):
    headers = {'User-Agent': UA, 'Accept': 'application/json'}
    if urllib.parse.urlsplit(url).hostname == 'api.github.com':
        headers['Accept'] = 'application/vnd.github+json'
        headers['X-GitHub-Api-Version'] = '2022-11-28'
        token = os.environ.get('GITHUB_TOKEN')
        if token:
            headers['Authorization'] = 'Bearer ' + token
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=25) as response:
                data = response.read(4_000_001)
                if len(data) > 4_000_000:
                    raise ValueError('Response too large')
                return json.loads(data)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise ValueError('Upstream HTTP ' + str(exc.code)) from None
            time.sleep(min(20, 2 ** (attempt + 1)))
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise ValueError('Upstream network timeout/unavailable') from None
            time.sleep(2 ** (attempt + 1))


def digest(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def resolve_article(title):
    url = 'https://zh.wikipedia.org/w/api.php?' + urllib.parse.urlencode({
        'action': 'query', 'titles': title, 'redirects': '1', 'converttitles': '1', 'format': 'json'
    })
    data = get_json(url)
    pages = list(data.get('query', {}).get('pages', {}).values())
    if len(pages) != 1 or 'missing' in pages[0] or pages[0].get('ns') != 0:
        raise ValueError('Wikipedia article unavailable; no substitute value generated')
    return pages[0]['title']


def wikipedia(entry, now):
    title = resolve_article(entry['article'])
    end = now.astimezone(timezone.utc).date() - timedelta(days=1)
    start = end - timedelta(days=34)
    url = ('https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/'
           'zh.wikipedia.org/all-access/user/' + urllib.parse.quote(title, safe='')
           + '/daily/' + start.strftime('%Y%m%d00') + '/' + end.strftime('%Y%m%d00'))
    response = get_json(url)
    items = response.get('items')
    if not isinstance(items, list) or not items:
        raise ValueError('Empty pageview response')
    source_url = 'https://zh.wikipedia.org/wiki/' + urllib.parse.quote(title, safe='')
    rows = []
    for item in items:
        value = item.get('views')
        day = datetime.strptime(item['timestamp'], '%Y%m%d%H').date()
        if not isinstance(value, int) or isinstance(value, bool) or value < 0 or not start <= day <= end:
            raise ValueError('Invalid pageview point')
        if item.get('article') != title or item.get('agent') != 'user' or item.get('access') != 'all-access':
            raise ValueError('Unexpected pageview scope')
        rows.append({
            'observed_date': day.isoformat(), 'platform': '维基百科', 'keyword': entry['keyword'],
            'opportunity_type': entry['type'], 'metric_type': 'wiki_pageviews', 'metric_value': value,
            'source_type': 'public_api', 'source_name': 'Wikimedia Analytics API',
            'source_scope': 'zh.wikipedia.org / ' + title + ' / all-access / user / UTC日',
            'source_url': source_url, 'notes': '百科条目阅读次数；不是搜索量、独立读者或购买需求。',
            'is_demo': 0, 'fetched_at': now.isoformat(), 'api_url': url, 'response_sha256': digest(response)
        })
    return rows, {'api_url': url, 'source_url': source_url, 'resolved_article': title, 'response_sha256': digest(response)}


def github(entry, now):
    url = 'https://api.github.com/repos/' + entry['repo']
    response = get_json(url)
    value = response.get('stargazers_count')
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError('Invalid GitHub star count')
    if response.get('full_name', '').lower() != entry['repo'].lower() or response.get('private') is not False:
        raise ValueError('Unexpected repository identity or visibility')
    # Deliberately retain no names, emails, issues, readme content, or credentials.
    evidence = {k: response.get(k) for k in ('full_name', 'html_url', 'stargazers_count', 'forks_count', 'archived')}
    return [{
        'observed_date': now.astimezone(SHANGHAI).date().isoformat(), 'platform': 'GitHub',
        'keyword': entry['keyword'], 'opportunity_type': entry['type'], 'metric_type': 'github_stars',
        'metric_value': value, 'source_type': 'public_api', 'source_name': 'GitHub REST API',
        'source_scope': entry['repo'] + ' / stars总数 / 北京时间每日快照',
        'source_url': response['html_url'], 'notes': '累计Star关注数，不是用户数或付费需求；无历史回填，日差是净变化。',
        'is_demo': 0, 'fetched_at': now.isoformat(), 'api_url': url, 'response_sha256': digest(evidence)
    }], {'api_url': url, 'source_url': response['html_url'], 'response_sha256': digest(evidence), 'evidence': evidence}


def merge_history(old, incoming, cutoff):
    fields = ('observed_date', 'platform', 'keyword', 'opportunity_type', 'metric_type', 'source_type', 'source_name', 'source_scope')
    points = {}
    for row in [*old, *incoming]:
        if row['observed_date'] >= cutoff and row.get('source_type') == 'public_api' and row.get('is_demo') == 0:
            points[tuple(row[f] for f in fields)] = row
    return sorted(points.values(), key=lambda r: (r['observed_date'], r['platform'], r['keyword']))


def pack_dataset(result):
    """Deduplicate provenance and series fields without losing original fetch evidence."""
    packed = {k: v for k, v in result.items() if k != 'rows'}
    packed['schema_version'] = 2
    packed['observation_count'] = len(result['rows'])
    groups, receipts, receipt_ids = {}, [], {}
    for row in result['rows']:
        receipt = tuple(row.get(k) for k in ('fetched_at', 'api_url', 'response_sha256'))
        if receipt not in receipt_ids:
            receipt_ids[receipt] = len(receipts)
            receipts.append(dict(zip(('fetched_at', 'api_url', 'response_sha256'), receipt)))
        base = {k: v for k, v in row.items() if k not in ('observed_date','metric_value','fetched_at','api_url','response_sha256')}
        identity = json.dumps(base, ensure_ascii=False, sort_keys=True)
        if identity not in groups:
            groups[identity] = {'base': base, 'points': []}
        groups[identity]['points'].append([row['observed_date'],row['metric_value'],receipt_ids[receipt]])
    packed.update(series=list(groups.values()), receipts=receipts)
    return packed


def unpack_dataset(data):
    if data.get('schema_version') != 2:
        return data
    return {**data, 'rows': [{**s['base'], **data['receipts'][receipt], 'observed_date': day, 'metric_value': value}
                           for s in data['series'] for day,value,receipt in s['points']]}


def collect(config, previous, now, workers=3):
    jobs = [(provider, entry) for provider in ('wikipedia', 'github') for entry in config[provider]]
    statuses, incoming = [], []
    previous_status = {s['id']: s for s in previous.get('sources', [])}
    def one(job):
        provider, entry = job
        identity = provider + ':' + entry.get('article', entry.get('repo', ''))
        old = previous_status.get(identity, {})
        state = {'id': identity, 'provider': provider, 'keyword': entry['keyword'], 'opportunity_type': entry['type'],
                 'attempted_at': now.isoformat(), 'last_success_at': old.get('last_success_at'), 'latest_observation': old.get('latest_observation')}
        try:
            rows, evidence = (wikipedia if provider == 'wikipedia' else github)(entry, now)
            state.update(evidence)
            state.update(status='ok', last_success_at=now.isoformat(), latest_observation=max(r['observed_date'] for r in rows), fetched_count=len(rows))
            return rows, state
        except Exception as exc:
            # Only sanitized error text reaches the public artifact.
            state.update(status='error', error=str(exc) if isinstance(exc, ValueError) else type(exc).__name__, fetched_count=0)
            for field in ('api_url', 'source_url', 'resolved_article'):
                if field in old:
                    state[field] = old[field]
            return [], state
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for rows, state in pool.map(one, jobs):
            incoming.extend(rows)
            statuses.append(state)
    history = merge_history(previous.get('rows', []), incoming, (now.date()-timedelta(days=90)).isoformat())
    successful = sum(s['status'] == 'ok' for s in statuses)
    return {'schema_version': 1, 'generated_at': now.isoformat(), 'schedule': '每天北京时间 11:23，GitHub 调度可能延迟',
            'status': 'ok' if successful == len(jobs) else 'partial' if successful else 'error',
            'successful_sources': successful, 'total_sources': len(jobs), 'sources': statuses, 'rows': history,
            'scope_notice': '固定观察清单的公开关注信号；不是电商平台搜索量、销量或利润榜。百科日数据以UTC统计；GitHub为北京时间每日快照。'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT/'docs/data/public.json')
    args = parser.parse_args()
    config = json.loads((ROOT/'config/public_watchlist.json').read_text(encoding='utf-8'))
    previous = unpack_dataset(json.loads(args.output.read_text(encoding='utf-8'))) if args.output.exists() else {}
    result = collect(config, previous, datetime.now(SHANGHAI))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix('.tmp')
    temporary.write_text(json.dumps(pack_dataset(result), ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf-8')
    temporary.replace(args.output)
    print(json.dumps({k: result[k] for k in ('generated_at', 'status', 'successful_sources', 'total_sources')}, ensure_ascii=False))
    for source in result['sources']:
        if source['status'] != 'ok':
            print(source['id'], source['error'])
    # Keep status artifacts deployable, and make GitHub's final health step fail after deployment.
    if result['status'] != 'ok':
        print('::warning::Some sources failed; retained dated history without fabricated replacement data.')


if __name__ == '__main__':
    main()
