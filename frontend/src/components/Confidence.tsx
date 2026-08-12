export function Confidence({value}:{value:number}){const pct=Math.round(value*100);return <div className="w-28"><div className="mb-1 flex justify-between text-[10px]"><span className="eyebrow">Confidence</span><span className="mono font-bold">{pct}%</span></div><div className="bar"><span style={{width:`${pct}%`,background:pct<70?'#d97706':'#17201f'}}/></div></div>}

