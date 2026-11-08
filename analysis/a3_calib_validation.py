"""A3 — Independent validation of the factory stereo calibration.

For every stereo frame with a detected ChArUco board (all sessions, both boards):
  * left-camera reprojection residual with intrinsics fixed (PnP per frame)
  * stereo epipolar distance using the factory extrinsics
Residuals are binned by image position (200 px grid) and by radius from the
principal point. The same evaluation is repeated for an independent fisheye
recalibration made from our own frames (a3_recalibrate.py -> recal.pkl).
Run: PYTHONPATH=. python3 a3_calib_validation.py out_dir [recal.pkl]
"""
import sys, os, json, pickle
import numpy as np, pandas as pd, cv2
from odl_calib import best, obj, device_calib, DATA

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
RECAL = sys.argv[2] if len(sys.argv) > 2 else None
RECS = {'124235_00000': 'a4', '124235_00001': 'a4', '124235_00002': 'a4', '124235_00003': 'a4',
        '142800_00000': 'a4', '143229_00000': 'a4', '145221_00000': 'a4', '150437_00000': 'a4',
        '145446_00000': 'far', '145935_00000': 'far', '145719_00000': 'far'}

def models():
    dc = device_calib(); T = dc['T_c1_c0']
    yield 'factory', dict(KL=dc['cam0']['K'], DL=dc['cam0']['D'], KR=dc['cam1']['K'], DR=dc['cam1']['D'], R=T[:3, :3], T=T[:3, 3])
    if RECAL:
        r = pickle.load(open(RECAL, 'rb')); r = r.get('all', r)
        yield 'odl_recalibration', dict(KL=r['KL'], DL=r['DL'], KR=r['KR'], DR=r['DR'], R=r['R'], T=r['T'].ravel())

grid_rows = []; rad_rows = []; summ = []
for name, c in models():
    Tv = c['T']; E = np.array([[0, -Tv[2], Tv[1]], [Tv[2], 0, -Tv[0]], [-Tv[1], Tv[0], 0]]) @ c['R']
    pts = []
    for rec, kind in RECS.items():
        L = json.load(open(f'{DATA}/det_{rec}_left.json')); R = json.load(open(f'{DATA}/det_{rec}_right.json'))
        for a, b in zip(L, R):
            th = 8 if kind == 'far' else 12
            bl = best(a, th); br = best(b, th)
            if bl is None or br is None: continue
            # recording 124235_00003 also shows a target on a curved monitor (upper image) -> excluded
            if rec == '124235_00003' and np.mean(bl['pts'], 0)[1] < 450: continue
            mL = dict(zip(bl['ids'], bl['pts'])); mR = dict(zip(br['ids'], br['pts'])); cc = sorted(set(mL) & set(mR))
            if len(cc) < 6: continue
            pl = np.array([mL[i] for i in cc]); pr = np.array([mR[i] for i in cc])
            ul = cv2.fisheye.undistortPoints(pl.reshape(-1, 1, 2), c['KL'], c['DL']).reshape(-1, 2)
            ur = cv2.fisheye.undistortPoints(pr.reshape(-1, 1, 2), c['KR'], c['DR']).reshape(-1, 2)
            hl = np.c_[ul, np.ones(len(ul))]; hr = np.c_[ur, np.ones(len(ur))]; l = (E @ hl.T).T
            epi = np.abs((hr * l).sum(1)) / np.linalg.norm(l[:, :2], axis=1) * c['KL'][0, 0]
            o = obj(cc, kind)
            ok, rv, tv = cv2.solvePnP(o, ul, np.eye(3), None)
            prj, _ = cv2.fisheye.projectPoints(o.reshape(-1, 1, 3), rv, tv, c['KL'], c['DL'])
            rep = np.linalg.norm(prj.reshape(-1, 2) - pl, axis=1)
            for p, e1, e2 in zip(pl, epi, rep): pts.append((rec, p[0], p[1], e1, e2))
    P = pd.DataFrame(pts, columns=['recording', 'u', 'v', 'epi_px', 'rep_px'])
    cx, cy = c['KL'][0, 2], c['KL'][1, 2]; P['r'] = np.hypot(P.u - cx, P.v - cy)
    for i in range(6):
        for j in range(8):
            s = P[(P.v // 200 == i) & (P.u // 200 == j)]
            grid_rows.append(dict(model=name, cell_row=i, cell_col=j, u_range=f'{j*200}-{j*200+200}', v_range=f'{i*200}-{i*200+200}', n_points=len(s),
                                  epi_median_px=s.epi_px.median() if len(s) >= 30 else np.nan, rep_median_px=s.rep_px.median() if len(s) >= 30 else np.nan))
    for lo, hi in [(0, 200), (200, 400), (400, 550), (550, 700), (700, 1000)]:
        s = P[(P.r >= lo) & (P.r < hi)]
        rad_rows.append(dict(model=name, radius_px=f'{lo}-{hi}', n_points=len(s), epi_median_px=s.epi_px.median(), epi_p90_px=s.epi_px.quantile(.9),
                             rep_median_px=s.rep_px.median(), rep_p90_px=s.rep_px.quantile(.9)))
    summ.append(dict(model=name, n_points=len(P), n_recordings=P.recording.nunique(), epi_median_px=P.epi_px.median(), epi_p90_px=P.epi_px.quantile(.9),
                     rep_median_px=P.rep_px.median(), rep_p90_px=P.rep_px.quantile(.9),
                     coverage_u_p0_5=P.u.quantile(.005), coverage_u_p99_5=P.u.quantile(.995), coverage_v_p0_5=P.v.quantile(.005), coverage_v_p99_5=P.v.quantile(.995)))
    if name == 'factory': P.round(3).to_csv(f'{OUT}/a3_corner_residuals_factory.csv.gz', index=False, compression='gzip')
    per = P[P.r < 400].groupby('recording').epi_px.median().rename('center_epi_median_px').reset_index(); per['model'] = name
    per.to_csv(f'{OUT}/a3_per_recording_center_epi_{name}.csv', index=False)
pd.DataFrame(grid_rows).round(4).to_csv(f'{OUT}/a3_residual_grid.csv', index=False)
pd.DataFrame(rad_rows).round(4).to_csv(f'{OUT}/a3_residual_by_radius.csv', index=False)
pd.DataFrame(summ).round(4).to_csv(f'{OUT}/a3_summary.csv', index=False)
print(pd.DataFrame(summ).round(3).to_string()); print(pd.DataFrame(rad_rows).round(3).to_string())
