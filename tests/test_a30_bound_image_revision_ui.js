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
const elements=new Map(),images=[],requests=[],messages=[];
const context={state:{head:'fresh-image-head',assets:[{asset_id:'fresh-page',sha256:'f'.repeat(64),width:800,height:960}],customer:{region_binding:true,source_occupancy:[]}},currentAnswerId:'fresh-image-answer',busy:false,
 $:id=>{if(!elements.has(id))elements.set(id,new Element('div'));return elements.get(id);},node:(tag,cls,text)=>new Element(tag,text),roleLabel:r=>r,
 document:{createTextNode:t=>new Element('text',t)},button:(label,fn)=>{const el=new Element('button',label);el.callback=fn;return el;},
 Image:class{constructor(){this.naturalWidth=800;this.naturalHeight=960;images.push(this);}},sourceUrl:id=>'/source/'+id,dirtyDrafts:()=>[],feedback:(...x)=>messages.push(x),
 setBusy:v=>{context.busy=v;},request:async(url,body)=>{requests.push({url,body});return {state:{}};},applyState:()=>{},showSource:()=>{},showError:e=>{throw e;}};
const walk=e=>[e,...e.children.flatMap(walk)];vm.createContext(context);vm.runInContext(raw.slice(start,end),context);
context.renderRegionBinding({platform_status:'NOT_RUN',figures:[{region_id:'source-3',asset_id:'fresh-page',bbox:[275,265,410,410],role:'question',content_type:'image'}],blocks:[{role:'question'}]});
const host=elements.get('customer-region-editor'),all=()=>walk(host),find=text=>all().find(e=>e.tag==='button'&&e.textContent===text);
const canvas=all().find(e=>e.tag==='canvas'),checked=all().find(e=>e.tag==='input'&&e.type==='checkbox'),save=find('绑定所选题图');
(async()=>{
 find('调整这张题图的范围').callback();images[1].onload();images[0].onload();checked.checked=true;await save.callback();assert.equal(requests.length,0);
 canvas.listeners.pointerdown({clientX:212,clientY:204,pointerId:1});canvas.listeners.pointermove({clientX:374,clientY:374});canvas.listeners.pointerup();checked.checked=true;await save.callback();
 assert.equal(requests.length,1);assert.equal(requests[0].body.replace_region_id,'source-3');assert.equal(requests[0].body.expected_head,'fresh-image-head');
 assert.equal(requests[0].body.asset_id,'fresh-page');assert.equal(requests[0].body.zone,'question');assert.equal(requests[0].body.source_checked,true);
 context.state.head='fresh-other-head';await save.callback();assert.equal(requests.length,1);
 process.stdout.write('PASS normal image-revision control: old crop cannot be blindly confirmed, new drag carries exact replacement/head/source, stale head blocked; model/platform=0\n');
})().catch(e=>{process.stderr.write(e.stack+'\n');process.exitCode=1;});
