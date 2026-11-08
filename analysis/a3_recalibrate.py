import sys,pickle; sys.path.insert(0,'.')
from lib import *
allS=pickle.load(open('allS.pkl','rb'))
old=pickle.load(open('../../calib/work/bc2.pkl','rb'))
for s in old: s['kind']='a4'; s['rec']='old_'+s['seg']
def thin(S,n):
    if len(S)<=n: return S
    return [S[i] for i in np.linspace(0,len(S)-1,n).round().astype(int)]
def okview(s):
    for side in 'LR':
        o=obj(s[side]['ids'],s['kind'])
        if len(np.unique(o[:,0]))<3 or len(np.unique(o[:,1]))<2: return False
        if s['kind']=='far' and len(o)<8: return False
    return True
new=[]
for rec,S in allS.items(): new+=thin([s for s in S if okview(s)],35)
oldt=thin(old,140)
sets={'all':new+oldt}
# outlier clean on all with per-view error
res={}
for nm,S in sets.items():
    for it in range(1):
        rl,KL,DL,_,_=mono(S,'L'); rr,KR,DR,_,_=mono(S,'R')
        el=per_view_err(S,'L',KL,DL); er=per_view_err(S,'R',KR,DR)
        keep=(el<3*np.median(el))&(er<3*np.median(er)); S=[s for s,k in zip(S,keep) if k]
    r=stereo(S); r['S']=S; res[nm]=r
    pts=np.concatenate([np.array(s['L']['pts']) for s in S])
    sys.stdout.flush(); print(f"{nm:4s} n{len(S)} monoL {r['rl']:.3f} monoR {r['rr']:.3f} stereo {r['rms']:.3f} | L fx {r['KL'][0,0]:.2f} fy {r['KL'][1,1]:.2f} c {r['KL'][0,2]:.1f},{r['KL'][1,2]:.1f} D {np.round(r['DL'].ravel(),4)} | R fx {r['KR'][0,0]:.2f} c {r['KR'][0,2]:.1f},{r['KR'][1,2]:.1f} | B {np.linalg.norm(r['T'])*1000:.2f} rot {np.round(np.degrees(cv2.Rodrigues(r['R'])[0].ravel()),3)} | x {np.percentile(pts[:,0],[0.5,99.5]).round()} y {np.percentile(pts[:,1],[0.5,99.5]).round()}")
# split half on all
S=res['all']['S']
for nm,SS in [('half1',S[::2]),('half2',S[1::2])]:
    r=stereo(SS); print(f"{nm} n{len(SS)} L fx {r['KL'][0,0]:.2f} c {r['KL'][0,2]:.1f},{r['KL'][1,2]:.1f} D {np.round(r['DL'].ravel(),4)} R fx {r['KR'][0,0]:.2f} B {np.linalg.norm(r['T'])*1000:.2f} rot {np.round(np.degrees(cv2.Rodrigues(r['R'])[0].ravel()),3)}")
pickle.dump(res,open('calres.pkl','wb'))
