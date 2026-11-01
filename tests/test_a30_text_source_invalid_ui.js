'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const raw=fs.readFileSync(path.join(__dirname,'../src/annotation/recognition/review_ui.js'),'utf8');
const start=raw.indexOf('  function renderRegionBinding(answer) {'),end=raw.indexOf('\n  function renderBlock(',start);
class Element{
 constructor(tag,text=''){this.tag=tag;this.textContent=text;this.children=[];this.listeners={};this.style={};this.value='';this.checked=false;}
 append(...items){this.children.push(...items);if(this.tag==='select'&&!this.value)this.value=this.children[0]?.value||'';}
 replaceChildren(){this.children=[];}contains(value){return this.children.includes(value);}
 addEventListener(name,fn){this.listeners[name]=fn;}getBoundingClientRect(){return {left:0,top:0,width:this.width,height:this.height};}
 setPointerCapture(){}getContext(){return {drawImage(){},clearRect(){},strokeRect(){}};}
}
const elements=new Map(),images=[],requests=[];
const context={state:{head:'invalid-boundary-head',assets:[{asset_id:'boundary-page',sha256:'d'.repeat(64),width:600,height:800}],customer:{region_binding:true,source_occupancy:[]}},currentAnswerId:'boundary-answer',busy:false,
 $:id=>{if(!elements.has(id))elements.set(id,new Element('div'));return elements.get(id);},node:(tag,cls,text)=>new Element(tag,text),roleLabel:r=>r,
 document:{createTextNode:t=>new Element('text',t)},button:(label,fn)=>{const el=new Element('button',label);el.callback=fn;return el;},
 Image:class{constructor(){this.naturalWidth=600;this.naturalHeight=800;images.push(this);}},sourceUrl:id=>'/source/'+id,dirtyDrafts:()=>[],feedback:()=>{},
 setBusy:v=>{context.busy=v;},request:async(url,body)=>{requests.push({url,body});return {state:{}};},applyState:()=>{},showSource:()=>{},showError:e=>{throw e;}};
const walk=e=>[e,...e.children.flatMap(walk)];vm.createContext(context);vm.runInContext(raw.slice(start,end),context);
context.renderRegionBinding({platform_status:'NOT_RUN',figures:[{region_id:'source-2',asset_id:'boundary-page',bbox:[30,255,300,360],role:'answer',content_type:'text'}],blocks:[{role:'answer'}]});
const host=elements.get('customer-region-editor'),all=()=>walk(host),find=text=>all().find(e=>e.tag==='button'&&e.textContent===text);
const checked=all().find(e=>e.tag==='input'&&e.type==='checkbox');
(async()=>{
 find('调整这段文字的来源范围').callback();images[1].onload();
 const save=find('保存文字来源范围'),top=all().filter(e=>e.tag==='input'&&e.type==='number')[1];
 const edit=value=>{top.value=value;top.listeners.input();};
 for(const invalid of ['', ' ', '-1', '254.5', '360', '801', 'NaN']){
   edit('254');checked.checked=true;edit(invalid);
   assert.equal(checked.checked,false,'invalid input must clear confirmation: '+JSON.stringify(invalid));
   checked.checked=true;await save.callback();assert.equal(requests.length,0,'invalid input must not submit the previous rectangle');
 }
 edit('254');checked.checked=true;top.value='';await save.callback();
 assert.equal(requests.length,0,'save must inspect current fields even when no input event was delivered');
 assert.equal(checked.checked,false);
 edit('254');checked.checked=true;top.value='253';await save.callback();
 assert.equal(requests.length,0,'a different current rectangle must not reuse the previous confirmation');
 assert.equal(checked.checked,false);
 edit('253');checked.checked=true;await save.callback();assert.equal(requests.length,1);
 assert.deepEqual(JSON.parse(JSON.stringify(requests[0].body.bbox)),[30,253,300,360]);
 assert.equal(requests[0].body.text_complete_checked,true);assert.equal(requests[0].body.replace_text_region_id,'source-2');
 process.stdout.write('PASS new invalid-boundary counterexample: seven invalid inputs clear confirmation and send nothing; save revalidates current fields without events; corrected input requires fresh confirmation and sends exactly once; model/platform=0\n');
})().catch(e=>{process.stderr.write(e.stack+'\n');process.exitCode=1;});
