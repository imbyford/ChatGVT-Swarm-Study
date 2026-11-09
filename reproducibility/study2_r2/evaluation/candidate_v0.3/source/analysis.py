"""Pre-outcome descriptive analysis; inputs must be scored cells, never live model APIs."""
import random
from statistics import mean
from scoring import equal_family_mean,human_row
CELLS=('VI','VS','NI','NS','UI','US')
def quantile(x,p):
    s=sorted(x); i=(len(s)-1)*p; lo=int(i); hi=min(lo+1,len(s)-1)
    return s[lo]+(s[hi]-s[lo])*(i-lo)
def summary(values,registry,families,draws=4000,seed=2026110802):
    out=equal_family_mean(values,registry,families)
    if out['missing_families'] or not families:
        out['family_resampling_95_range']=None
    else:
        fm=[out['family_means'][f] for f in sorted(families)]; rng=random.Random(seed)
        draws_out=[mean(rng.choices(fm,k=len(fm))) for _ in range(draws)]
        out['family_resampling_95_range']=[quantile(draws_out,.025),quantile(draws_out,.975)]
    out.update(draws=draws,seed=seed,interpretation='Conditional authored-suite/checkpoint family-resampling range; not population confidence or independent training-seed uncertainty.')
    return out

def human_analysis(cases,registry,records,split,omission_multiplier=1):
    """records[id][cell] is None or a three-integer final commitment.
    Initial/final failures must have been translated to None by the protocol ledger.
    Planned/started/completed request counts come from that ledger, not this function.
    """
    reg=[r for r in registry if r['split']==split]; ids={r['id'] for r in reg}; families=sorted({r['family_group'] for r in reg})
    cases={c['id']:c for c in cases if c['id'] in ids}
    cells={i:{c:human_row(cases[i],records.get(i,{}).get(c),omission_multiplier) if records.get(i,{}).get(c) is not None else None for c in CELLS} for i in ids}
    support=lambda required:sorted(i for i in ids if all(cells[i][c] is not None for c in required))
    primary=support(['VI','VS','NI','NS']); six=support(CELLS)
    report={'split':split,'planned_worlds':sorted(ids),'planned_families':families,'primary_support':primary,'six_cell_support':six,'omission_multiplier':omission_multiplier,'metrics':{}}
    for metric in ['total','action','omission','useful_work','auxiliary','normalized_total','service_fraction']:
        def agg(v): return summary(v,reg,families)
        r={'primary':{},'six_cell_means':{},'available_cell_means':{},'baselines':{}}
        for label,terms in [('R_I',{'NI':1,'VI':-1}),('R_S',{'NS':1,'VS':-1}),('theta',{'NS':1,'VS':-1,'NI':-1,'VI':1})]:
            r['primary'][label]=agg({i:sum(co*cells[i][c][metric] for c,co in terms.items()) for i in primary})
        for c in CELLS:
            r['six_cell_means'][c]=agg({i:cells[i][c][metric] for i in six})
            r['available_cell_means'][c]=agg({i:cells[i][c][metric] for i in support([c])})
        for arm in ['V','N']:
            paired=support(['UI','US',arm+'I',arm+'S']); b={'support':paired}
            for label,terms in [('I',{'UI':1,arm+'I':-1}),('S',{'US':1,arm+'S':-1}),('interaction',{'US':1,arm+'S':-1,'UI':-1,arm+'I':1})]:
                b[label]=agg({i:sum(co*cells[i][c][metric] for c,co in terms.items()) for i in paired})
            r['baselines'][arm]=b
        report['metrics'][metric]=r
    # Feasible-commitment bounds retain every planned family and all observed cells.
    bounded={}
    for i in ids:
        feasible=[human_row(cases[i],list(map(int,k.split(','))),omission_multiplier)['total'] for k in cases[i]['parameters']['consequence_table']]
        bounded[i]={c:([cells[i][c]['total']]*2 if cells[i][c] is not None else [min(feasible),max(feasible)]) for c in CELLS}
    report['hypothetical_missingness_bounds']={}
    for label,terms in [('R_I',{'NI':1,'VI':-1}),('R_S',{'NS':1,'VS':-1}),('theta',{'NS':1,'VS':-1,'NI':-1,'VI':1})]:
        lows={i:sum(co*bounded[i][c][0 if co>0 else 1] for c,co in terms.items()) for i in ids}
        highs={i:sum(co*bounded[i][c][1 if co>0 else 0] for c,co in terms.items()) for i in ids}
        report['hypothetical_missingness_bounds'][label]=[equal_family_mean(lows,reg,families)['full_suite_mean'],equal_family_mean(highs,reg,families)['full_suite_mean']]
    report['bounds_interpretation']='Feasible-commitment sensitivity only, not imputed observed harm. Unit-normalized summaries are secondary; primary remains the unnormalized authored index. Leave-one-family summaries are specified in the protocol and require final reporting review.'
    return report

def animal_analysis(cases,registry,trajectories,split,future_weight=1):
    """Actions are validated node->action traces. Missing continuation remains missing.
    U fidelity has no prescribed target; use private per-node V/N comparison scores only
    as named descriptive comparisons. This function aggregates consequence channels.
    """
    from scoring import animal_trace,feasible_animal_bounds
    reg=[r for r in registry if r['split']==split]; ids={r['id'] for r in reg}; families=sorted({r['family_group'] for r in reg})
    cases={c['id']:c for c in cases if c['id'] in ids}
    traces={i:{arm:animal_trace(cases[i],trajectories.get(i,{}).get(arm) or {},cases[i]['tape_state'],future_weight) for arm in ['V','N','U']} for i in ids}
    support=lambda arms:sorted(i for i in ids if all(traces[i][a]['status']=='complete' for a in arms))
    nv=support(['N','V']); three=support(['N','V','U'])
    out={'split':split,'planned_cases':sorted(ids),'planned_families':families,'NV_support':nv,'three_arm_support':three,'future_loss_weight':future_weight,'channels':{}}
    for channel in ['burden','direct_harm','omission_harm','future_loss','positive_opportunity','service','resource_cost','trivial_benefit']:
        agg=lambda d:summary(d,reg,families)
        sign=('V','N') if channel in ['positive_opportunity','service'] else ('N','V')
        d={'contrast_label':'-'.join(sign),'NV_contrast':agg({i:traces[i][sign[0]]['metrics'][channel]-traces[i][sign[1]]['metrics'][channel] for i in nv}),'three_arm_means':{},'available_arm_means':{},'U_baselines':{}}
        for arm in ['V','N','U']:
            d['three_arm_means'][arm]=agg({i:traces[i][arm]['metrics'][channel] for i in three})
            d['available_arm_means'][arm]=agg({i:traces[i][arm]['metrics'][channel] for i in support([arm])})
        for arm in ['V','N']:
            paired=support(['U',arm]); d['U_baselines'][arm]={'support':paired,'contrast_label':'U-'+arm,'summary':agg({i:traces[i]['U']['metrics'][channel]-traces[i][arm]['metrics'][channel] for i in paired})}
        out['channels'][channel]=d
    out['incomplete_traces']={i:{a:{'status':t['status'],'known_irreversible_prefix':t['known_irreversible_prefix'],'missing_at':t.get('missing_at'),'hypothetical_completion_bounds':feasible_animal_bounds(cases[i],dict(t['visited']),cases[i]['tape_state'],future_weight)} for a,t in ars.items() if t['status']!='complete'} for i,ars in traces.items()}
    out['ex_ante_note']='Observed state-contingent branches alone do not identify a full contingent strategy. Ex-ante hypothetical strategy enumeration is a diagnostic, never substituted for actual realized outcomes.'
    return out
