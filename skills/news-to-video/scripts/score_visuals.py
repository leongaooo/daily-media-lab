"""Audit editorial visual choices offline. Never infers ratings or calls APIs."""
import argparse
import json
import math
from pathlib import Path

WEIGHTS = dict(relevance=30, appeal=30, narrative=25, readability=15)
GATES = ('facts', 'source', 'layout', 'execution')

def assess(project):
    if 'visual_selection_version' not in project:
        return dict(status='legacy-not-assessed', errors=[], warnings=['Legacy project: no scores inferred'], scenes=[])
    errors, warnings, rows = [], [], []
    if project['visual_selection_version'] != 1:
        errors.append('Unsupported visual_selection_version')
    streak = 0
    for i, scene in enumerate(project.get('scenes', [])):
        prefix = f'Scene {i+1}: '
        spec = scene.get('visual_selection', {})
        if spec.get('exempt_reason'):
            if i not in (0, len(project['scenes'])-1) or scene.get('presenter') != 'host':
                errors.append(prefix+'exemption only allowed for explicit first/last host')
            rows.append(dict(scene=i, exempt_reason=spec['exempt_reason']))
            streak = 0
            continue
        if not spec.get('goal'):
            errors.append(prefix+'missing visual goal')
        candidates = spec.get('candidates', [])
        if not candidates or not any(c.get('uses_image') is True for c in candidates) or not any(c.get('uses_image') is False for c in candidates):
            errors.append(prefix+'compare at least one image and one non-image candidate')
        rated, ids = [], set()
        for c in candidates:
            cid = c.get('id')
            if not isinstance(cid, str) or not cid or cid in ids:
                errors.append(prefix+'missing or duplicate candidate id')
            ids.add(cid if isinstance(cid, str) else '')
            scores = c.get('scores', {})
            valid = all(type(scores.get(k)) in (int, float) and math.isfinite(scores[k]) and 0 <= scores[k] <= 5 for k in WEIGHTS)
            gates = c.get('gates', {})
            if not valid or not all(type(gates.get(k)) is bool for k in GATES) or type(c.get('uses_image')) is not bool or not c.get('reason'):
                errors.append(prefix+f'incomplete ratings/gates/reason for {cid}')
                continue
            eligible = all(gates[k] for k in GATES)
            rated.append(dict(id=cid, uses_image=c['uses_image'], score=round(sum(scores[k]/5*w for k,w in WEIGHTS.items()),2), eligible=eligible, reason=c['reason']))
        selected = next((c for c in rated if c['id']==spec.get('selected')), None)
        eligible = [c for c in rated if c['eligible']]
        if not selected or not selected['eligible']:
            errors.append(prefix+'selected candidate missing or fails gates')
        recommended = None
        if eligible:
            best = max(c['score'] for c in eligible)
            near_images = [c for c in eligible if c['uses_image'] and c['score'] >= best-5]
            recommended = max(near_images or eligible, key=lambda c:c['score'])
            if selected and selected['id'] != recommended['id'] and not spec.get('override_reason'):
                errors.append(prefix+'selection differs from recommendation; explain override_reason')
        if selected and not selected['uses_image']:
            streak += 1
            warnings.append(prefix+'non-image selected; review documented picture alternative')
        else:
            streak = 0
        if streak >= 3:
            warnings.append(prefix+'three consecutive non-image scenes; revisit scene-setting opportunity')
        rows.append(dict(scene=i, goal=spec.get('goal'), candidates=rated, selected=spec.get('selected'), recommended=recommended['id'] if recommended else None, override_reason=spec.get('override_reason')))
    if not project.get('scenes'):
        errors.append('No scenes to assess')
    return dict(status='failed' if errors else 'passed', scoring='editor supplied, not audience measurement', weights=WEIGHTS, errors=errors, warnings=warnings, scenes=rows)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report = assess(json.loads(Path(args.project).read_text(encoding='utf-8-sig')))
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(status=report['status'],errors=len(report['errors']),warnings=len(report['warnings']))))
    raise SystemExit(1 if report['errors'] else 0)
