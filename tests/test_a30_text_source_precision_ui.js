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
const context={state:{head:'text-boundary-head',assets:[{asset_id:'boundary-page',sha256:'d'.repeat(64),width:600,height:800}],customer:{region_binding:true,source_occupancy:[]}},currentAnswerId:'boundary-answer',busy:false,
 $:id=>{if(!elements.has(id))elements.set(id,new Element('div'));return elements.get(id);},node:(tag,cls,text)=>new Element(tag,text),roleLabel:r=>r,
 document:{createTextNode:t=>new Element('text',t)},button:(label,fn)=>{const el=new Element('button',label);el.callback=fn;return el;},
 Image:class{constructor(){this.naturalWidth=600;this.naturalHeight=800;images.push(this);}},sourceUrl:id=>'/source/'+id,dirtyDrafts:()=>[],feedback:()=>{},
 setBusy:v=>{context.busy=v;},request:async(url,body)=>{requests.push({url,body});return {state:{}};},applyState:()=>{},showSource:()=>{},showError:e=>{throw e;}};
const walk=e=>[e,...e.children.flatMap(walk)];vm.createContext(context);vm.runInContext(raw.slice(start,end),context);
context.renderRegionBinding({platform_status:'NOT_RUN',figures:[{region_id:'source-2',asset_id:'boundary-page',bbox:[30,58,300,100],role:'answer',content_type:'text'}],blocks:[{role:'answer'}]});
const host=elements.get('customer-region-editor'),all=()=>walk(host),find=text=>all().find(e=>e.tag==='button'&&e.textContent===text);
const canvas=all().find(e=>e.tag==='canvas'),checked=all().find(e=>e.tag==='input'&&e.type==='checkbox');
(async()=>{
 find('调整这段文字的来源范围').callback();images[1].onload();images[0].onload();const save=find('保存文字来源范围');
 checked.checked=true;await save.callback();assert.equal(requests.length,0);
 const numbers=all().filter(e=>e.tag==='input'&&e.type==='number');assert.equal(numbers.length,4);numbers[1].value='62';numbers[1].listeners.input();assert.equal(checked.checked,false);
 checked.checked=true;await save.callback();assert.equal(requests.length,1);
 assert.equal(requests[0].body.replace_text_region_id,'source-2');assert.equal(requests[0].body.text_complete_checked,true);
 assert.equal(requests[0].body.expected_head,'text-boundary-head');assert.equal(requests[0].body.asset_id,'boundary-page');
 assert.equal(requests[0].body.zone,'answer');assert.equal(requests[0].body.replace_region_id,undefined);
 assert.deepEqual(JSON.parse(JSON.stringify(requests[0].body.bbox)),[30,62,300,100]);
 context.state.head='new-head';await save.callback();assert.equal(requests.length,1);
 process.stdout.write('PASS ordinary precise text-boundary control: numeric source-pixel edit, exact unrounded geometry, completeness reset, no image replacement or stale request; model/platform=0\n');
})().catch(e=>{process.stderr.write(e.stack+'\n');process.exitCode=1;});
