'use strict';
let data, current;
const $ = id => document.getElementById(id);
const number = (n,d=0) => n.toLocaleString('en-US',{maximumFractionDigits:d,minimumFractionDigits:d});
const names = ['Random targeting','Likely buyers'];
function scenario(strategy, capacity, audience, margin, cost) {
  const row=data.curves.find(r=>r.strategy===strategy && Math.abs(r.fraction-capacity)<1e-8);
  if(!row) throw new Error('No held-out result for this strategy and capacity.');
  const spend=audience*capacity*cost;
  return {strategy,capacity,audience,margin,cost,targeted_users:audience*capacity,
    additional_purchases:row.gain_per_100k*audience/100000,
    purchase_ci_low:row.ci_low*audience/100000,purchase_ci_high:row.ci_high*audience/100000,
    spend,net_contribution:row.gain_per_100k*audience/100000*margin-spend,
    net_ci_low:row.ci_low*audience/100000*margin-spend,
    net_ci_high:row.ci_high*audience/100000*margin-spend,
    interpretation:'Released-benchmark estimate under fixed fitted models; hypothetical costs and margins; audience scaling assumes the same population mix. Not observed profit.'};
}
function draw(q,strategy){
  const w=760,h=315,left=54,right=16,top=22,bottom=45;
  const max=Math.ceil(Math.max(...data.curves.map(r=>r.ci_high))/25)*25;
  const min=Math.min(0,Math.floor(Math.min(...data.curves.map(r=>r.ci_low))/25)*25);
  const x=v=>left+(w-left-right)*v, y=v=>h-bottom-(h-top-bottom)*(v-min)/(max-min);
  let svg=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Incremental purchase curves for three targeting strategies. A vertical line marks ${q*100}% capacity."><title>Additional purchases per 100,000 eligible users by targeting capacity</title>`;
  for(let i=0;i<=4;i++){const val=min+(max-min)*i/4;svg+=`<line x1="${left}" x2="${w-right}" y1="${y(val)}" y2="${y(val)}" stroke="#e5e6dd"/><text x="${left-10}" y="${y(val)+4}" text-anchor="end" fill="#69756e" font-size="11">${number(val)}</text>`;}
  for(const v of [.05,.2,.4,.6,.8,1])svg+=`<text x="${x(v)}" y="${h-20}" text-anchor="middle" fill="#69756e" font-size="11">${number(v*100)}%</text>`;
  const band=data.curves.filter(r=>r.strategy===strategy);
  const points=band.map(r=>`${x(r.fraction)},${y(r.ci_high)}`).concat([...band].reverse().map(r=>`${x(r.fraction)},${y(r.ci_low)}`)).join(' ');
  svg+=`<polygon points="${points}" fill="#0d7b64" opacity=".08"/>`;
  const colors={'Random targeting':'#8f9da2','Likely buyers':'#d7943c',[data.summary.winner]:'#14a68f'};
  for(const name of [...names,data.summary.winner]){
    const rows=data.curves.filter(r=>r.strategy===name);
    const path=rows.map((r,i)=>`${i?'L':'M'}${x(r.fraction)},${y(r.gain_per_100k)}`).join(' ');
    svg+=`<path d="${path}" fill="none" stroke="${colors[name]}" stroke-width="2.5" ${name==='Random targeting'?'stroke-dasharray="5 5"':''}/>`;
  }
  svg+=`<line x1="${x(q)}" x2="${x(q)}" y1="${top}" y2="${h-bottom}" stroke="#1b332e" stroke-dasharray="3 4" opacity=".5"/>`;
  const r=band.find(r=>Math.abs(r.fraction-q)<1e-8);
  svg+=`<circle cx="${x(q)}" cy="${y(r.gain_per_100k)}" r="5" fill="white" stroke="#0d7b64" stroke-width="2"/></svg>`;
  $('curve-chart').innerHTML=svg;
}
function update(){
 if(!$('scenario-form').checkValidity())return;
 const q=Number($('capacity').value)/100;
 current=scenario($('strategy').value,q,Number($('audience').value),Number($('margin').value),Number($('cost').value));
 $('capacity-label').textContent=number(q*100)+'%';
 $('purchases').textContent=number(current.additional_purchases,1);
 $('purchase-ci').textContent=`95% interval: ${number(current.purchase_ci_low,1)} to ${number(current.purchase_ci_high,1)}`;
 $('spend').textContent=number(current.spend);
 $('target-count').textContent=number(current.targeted_users)+' users targeted';
 $('net').textContent=number(current.net_contribution);
 $('net-ci').textContent=`95% interval: ${number(current.net_ci_low)} to ${number(current.net_ci_high)} units`;
 let note=current.net_ci_low>0?'The scenario interval is above zero under these assumptions.':current.net_ci_high<0?'The scenario interval is below zero under these assumptions.':'The scenario interval includes zero: positive net contribution is not established.';
 $('scenario-note').textContent=note+' These are benchmark-based scenarios, not observed returns or a rollout recommendation.';
 draw(q,current.strategy);
}
async function start(){
 try{
  const response=await fetch('data.json');if(!response.ok)throw new Error('Results could not be loaded.');data=await response.json();
  $('sample-count').textContent=number(data.summary.sample_rows/1e6,2)+' million';
  [...names,data.summary.winner].forEach(name=>{const option=document.createElement('option');option.value=name;option.textContent=name===data.summary.winner?'Selected uplift model':name;$('strategy').append(option);});
  $('strategy').value=data.summary.winner;
  for(const r of data.results){const tr=document.createElement('tr');if(r.selected_on_validation)tr.className='selected-row';
   const cells=[r.strategy+(r.selected_on_validation?' · selected on validation':''),number(r.incremental_per_100k,1),`${number(r.ci_low,1)} to ${number(r.ci_high,1)}`,number(r.ipw_per_100k,1)];
   for(const value of cells){const td=document.createElement('td');td.textContent=value;tr.append(td);}$('results-table').append(tr);
  }
  data.comparisons.forEach((r,i)=>{const el=document.createElement('article');el.className='comparison';const heading=document.createElement('span');heading.textContent=i===0?'Selected uplift vs random targeting':'Selected uplift vs likely buyers';const value=document.createElement('strong');value.textContent=(r.difference_per_100k>=0?'+':'')+number(r.difference_per_100k,1);const p=document.createElement('p');p.textContent=`Additional purchases per 100,000 eligible users. 95% interval: ${number(r.ci_low,1)} to ${number(r.ci_high,1)}. `+(r.ci_low>0?'Evidence of improvement.':'No clear improvement established.');el.append(heading,value,p);$('comparisons').append(el);});
  $('scenario-form').addEventListener('input',update);
  $('reset').addEventListener('click',()=>{$('audience').value='100000';$('capacity').value='20';$('margin').value='50';$('cost').value='0.05';$('strategy').value=data.summary.winner;update();});
  $('export').addEventListener('click',()=>{if(!$('scenario-form').reportValidity())return;const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(current,null,2)],{type:'application/json'}));a.download='marketing-scenario.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);});
  update();
 }catch(error){$('load-error').hidden=false;$('load-error').textContent='Unable to load the analysis. Serve this folder over HTTP and try again. '+error.message;}
}
start();
