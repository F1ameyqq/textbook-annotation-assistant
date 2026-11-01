'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../src/annotation/recognition/review_ui.js'),'utf8');
const start=source.indexOf('  function renderCustomerFormulas(draft) {'),end=source.indexOf('\n  function updateSpanLabel(',start);
assert(start>=0&&end>start);
class Element {
 constructor(tag,text){this.tag=tag;this.textContent=text;this.children=[];this.listeners={};this.style={};this.isConnected=true;this.checked=false;}
 append(...items){this.children.push(...items);}
 addEventListener(name,callback){this.listeners[name]=callback;}
 setAttribute(){}
 setPointerCapture(){}
 getBoundingClientRect(){return {left:0,top:0,width:this.width,height:this.height};}
 getContext(){return {drawImage(){},strokeRect(){}};}
}
const find=(root,predicate)=>[root,...root.children.flatMap(child=>find(child,predicate))].filter(predicate);
const region={proposal_id:'new-proposal',zone:'answer',asset_id:'new-source',bbox:[20,20,90,45],adjustment_bounds:[10,10,110,70]};
let answer={platform_status:'NOT_RUN',formula_regions:{regions:[region]},formula_observations:[]},dirty=[];
const images=[],requests=[],messages=[];
const context={state:{head:'current-head'},currentAnswerId:'current-answer',busy:false,currentAnswer:()=>answer,
 node:(tag,cls,text)=>new Element(tag,text),document:{createTextNode:text=>new Element('text',text)},
 button:(label,callback)=>{const item=new Element('button',label);item.callback=callback;return item;},
 Image:class{constructor(){this.naturalWidth=100;this.naturalHeight=60;images.push(this);}},
 sourceUrl:(asset,bounds)=>asset+JSON.stringify(bounds),dirtyDrafts:()=>dirty,feedback:(...args)=>messages.push(args),
 setBusy:value=>{context.busy=value;},request:async(url,body)=>{requests.push({url,body});return {state:{}};},
 applyState:()=>{},getAuthor:()=>({kind:'SYNTHETIC_TEST'}),showError:error=>{throw error;},
 renderDraftEditor:draft=>{draft.rendered=true;},updateDirtyState:()=>{}};
vm.createContext(context);vm.runInContext(source.slice(start,end),context);
const textarea={value:'left OLD right',selectionStart:5,selectionEnd:8};
const draft={block:{role:'answer'},sourceSpan:[0,500],editor:{querySelector:()=>textarea},format:'plain'};
(async()=>{
 const host=context.renderCustomerFormulas(draft),row=find(host,x=>x.tag==='details')[1];row.open=true;row.listeners.toggle();
 const recognize=find(host,x=>x.tag==='button'&&x.textContent==='识别当前公式区域')[0];
 await recognize.callback();assert.equal(requests.length,0,'cannot recognize before visible source');
 images[0].onload();const checked=find(host,x=>x.tag==='input')[0];checked.checked=true;
 dirty=[{}];await recognize.callback();assert.equal(requests.length,0,'must preserve unsaved edits');dirty=[];
 await recognize.callback();assert.equal(requests.length,1);assert.equal(requests[0].url,'/api/formula');
 assert.deepEqual(JSON.parse(JSON.stringify(requests[0].body.adjusted_bbox)),region.bbox);
 context.state.head='new-head';await recognize.callback();assert.equal(requests.length,1,'stale source cannot call');
 context.state.head='current-head';answer.formula_observations=[{proposal_id:region.proposal_id,candidate:{source_bbox:region.bbox,raw_latex:'y^2'}}];
 const retained=context.renderCustomerFormulas(draft),insert=find(retained,x=>x.tag==='button'&&x.textContent==='放入当前草稿选区')[0];
 insert.callback();assert.equal(draft.text,'left $y^2$ right');assert(draft.rendered);assert.equal(requests.length,1);
 const old=draft.text;answer.platform_status='REUSED_ACCEPTED';insert.callback();assert.equal(draft.text,old,'completed question is not modified');
 answer.platform_status='NOT_RUN';answer.formula_observations=[];region.boundary_review_required=true;
 region.boundary_conflicts=[{bbox:[20,40,100,65]}];
 const boundary=context.renderCustomerFormulas(draft),boundaryRow=find(boundary,x=>x.tag==='details')[1];
 assert(find(boundary,x=>typeof x.textContent==='string'&&x.textContent.includes('退出自动批次')).length);
 boundaryRow.open=true;boundaryRow.listeners.toggle();images.at(-1).onload();
 const boundaryCheck=find(boundary,x=>x.tag==='input')[0],boundaryButton=find(boundary,x=>x.tag==='button'&&x.textContent==='识别当前公式区域')[0];
 boundaryCheck.checked=true;await boundaryButton.callback();assert.equal(requests.length,1,'unadjusted cross-question region must not request');
 const canvas=find(boundary,x=>x.tag==='canvas')[0];
 canvas.listeners.pointerdown({clientX:40,clientY:40,pointerId:1});canvas.listeners.pointermove({clientX:280,clientY:100});canvas.listeners.pointerup();
 assert.equal(boundaryCheck.checked,false,'adjustment requires renewed source check');
 boundaryCheck.checked=true;await boundaryButton.callback();assert.equal(requests.length,2,'visible nonoverlapping selection uses the normal API');
 assert.deepEqual(JSON.parse(JSON.stringify(requests[1].body.adjusted_bbox)),[20,20,80,35]);
 region.boundary_review_required=false;region.recognition_blocked=true;region.manual_resolution_required=true;
 const failedRegion=context.renderCustomerFormulas(draft),failedButton=find(failedRegion,x=>x.tag==='button'&&x.textContent==='保留原记录，不再识别')[0];
 assert(failedButton.disabled);assert(find(failedRegion,x=>typeof x.textContent==='string'&&x.textContent.includes('失败记录永久保留')).length);
 await failedButton.callback();assert.equal(requests.length,2,'a retained failed region never requests a shifted crop');
 process.stdout.write('PASS source visibility, dirty-draft preservation, bound request, stale head, cached candidate insertion into current selection, completed-question hold; model/platform=0\n');
 process.stdout.write('PASS cross-question manual notice, unchanged selection blocked, source-visible adjustment, normal API selected bbox; model/platform=0\n');
 process.stdout.write('PASS retained failed region shows manual review and cannot issue any new recognition request; model/platform=0\n');
})().catch(error=>{process.stderr.write(error.stack+'\n');process.exitCode=1;});
