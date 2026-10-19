"""Machine-checkable guards for published claims. Scientific interpretation stays a documented human review."""


def validate_claims(claims,reports):
    for c in claims:
        report=reports.get(c.get('run_id'))
        if report is None:raise ValueError(f'unknown run: {c.get("run_id")}')
        if c.get('input_mode')!=report['input_mode']:raise ValueError('claim input mode differs from run input mode; raw-question and diagnostic results stay separate')
        kind=c['kind']
        if kind=='metric':
            arm=report['arms'].get(c['arm'],{}).get(c['split'],{})
            if c['metric'] not in arm:raise ValueError(f'metric not in run: {c["metric"]}')
            if arm[c['metric']]!=c['value']:raise ValueError('claimed value differs from run report')
        elif kind=='latency':
            if report['timing_kind']!='fresh_local':raise ValueError('replay timing is not measured latency')
        elif kind=='savings':
            costs=report['costs']
            if costs.get('estimated_api_usd') is None or costs.get('compute_cost_usd') is None:raise ValueError('unknown cost blocks a savings claim')
        elif kind=='noninferiority':
            comparison=next((x for x in report['comparisons'] if x['name']==c['comparison']),None)
            if comparison is None or not comparison.get('ci95'):raise ValueError('noninferiority requires a paired interval')
            if comparison['ci95'][0]==comparison['ci95'][1]:raise ValueError('degenerate interval (no discordant questions) cannot support noninferiority')
            if comparison['inference_status']=='descriptive_only':raise ValueError('descriptive-only interval cannot support noninferiority')
            if comparison['ci95'][0]<=-c['margin']:raise ValueError('interval lower bound does not clear the margin')
        else:raise ValueError(f'unknown claim kind: {kind}')
