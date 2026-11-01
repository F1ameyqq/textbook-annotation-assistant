'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const raw=fs.readFileSync(path.join(__dirname,'../src/annotation/recognition/review_ui.js'),'utf8');
const start=raw.indexOf('  function renderRegionBinding(answer) {'),end=raw.indexOf('\n  function renderBlock(',start);
assert(start>=0&&end>start);
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.listeners={};this.style={};this.value='';this.width=680;this.height=400;this.checked=false;this.drawn=[];}
 append(...items){this.children.push(...items);if(this.tag==='select'&&!this.value)this.value=this.children[0]?.value||'';}
 replaceChildren(){this.children=[];}
 contains(value){return this.children.includes(value);}
 addEventListener(name,fn){this.listeners[name]=fn;}
 getBoundingClientRect(){return {left:0,top:0,width:this.width,height:this.height};}
 setPointerCapture(){}
 getContext(){return {drawImage:image=>this.drawn.push(image.src),clearRect:()=>this.drawn.push('CLEAR'),strokeRect(){}};}
}
const elements=new Map(),images=[],requests=[],messages=[];
const context={state:{head:'head-1',customer:{region_binding:true}},currentAnswerId:'answer-1',busy:false,
 $:id=>{if(!elements.has(id))elements.set(id,new Element('div'));return elements.get(id);},
 node:tag=>new Element(tag),roleLabel:role=>role,document:{createTextNode:()=>new Element('text')},
 button:(label,callback)=>{const el=new Element('button');el.callback=callback;return el;},
 Image:class{constructor(){this.naturalWidth=1000;this.naturalHeight=1400;images.push(this);}},
 sourceUrl:id=>'/source/'+id,dirtyDrafts:()=>[],feedback:(...args)=>messages.push(args),
 setBusy:value=>{context.busy=value;},request:async(url,body)=>{requests.push({url,body});return {state:{}};},
 applyState:()=>{},showError:()=>{throw Error('unexpected UI error');}};
vm.createContext(context);vm.runInContext(raw.slice(start,end),context);
context.renderRegionBinding({figures:[{asset_id:'page-A'},{asset_id:'page-B'},{asset_id:'page-C'}],blocks:[{role:'question'}]});
const host=elements.get('customer-region-editor'),[select,zone,canvas,note,label,save]=host.children,checked=label.children[0];
const draw=()=>{canvas.listeners.pointerdown({clientX:20,clientY:30,pointerId:1});canvas.listeners.pointermove({clientX:130,clientY:180});canvas.listeners.pointerup();checked.checked=true;};
(async()=>{
 assert(save.disabled);select.value='page-B';select.listeners.change();images[1].onload();assert.equal(canvas.drawn.at(-1),'/source/page-B');
 images[0].onload();images[0].onerror();assert.equal(canvas.drawn.at(-1),'/source/page-B');assert.notEqual(note.textContent,'无法读取来源原页。');
 draw();select.value='page-C';select.listeners.change();assert(save.disabled);assert(!checked.checked);checked.checked=true;
 await save.callback();assert.equal(requests.length,0);images[2].onload();draw();await save.callback();
 assert.equal(requests.length,1);assert.equal(requests[0].body.asset_id,'page-C');assert.equal(requests[0].body.answer_id,'answer-1');
 assert.equal(requests[0].body.expected_head,'head-1');
 select.value='page-A';select.listeners.change();context.state.head='head-2';images[3].onload();checked.checked=true;await save.callback();
 assert.equal(requests.length,1);assert(save.disabled);
 process.stdout.write('PASS current asset/generation bound: out-of-order load/error, loading submit, exact loaded asset, stale head; browser/network/model=0\n');
})().catch(error=>{process.stderr.write(error.stack+'\n');process.exitCode=1;});
