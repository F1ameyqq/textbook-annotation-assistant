'use strict';
(() => {
  const $ = id => document.getElementById(id), G = window.PreboxGeometry;
  const NS = 'http://www.w3.org/2000/svg';
  const kinds = {candidate:'候选区域', question:'题目', stem:'题干', option:'选项', answer:'答案', explanation:'解析', figure:'图形', table:'表格', ignore:'忽略'};
  let state = null, pages = [], pageId = null, selected = null, dirty = false, busy = false, tool = 'select', zoom = .5, gesture = null;
  const undos = new Map(), clone = value => JSON.parse(JSON.stringify(value));
  const page = () => pages.find(p => p.page_id === pageId), box = () => page()?.boxes.find(b => b.box_id === selected);
  function notice(text, error=false) { $('notice').textContent = text; $('notice').hidden = !text; $('notice').classList.toggle('error', error); }
  function button(text, action) { const b = document.createElement('button'); b.type='button'; b.textContent=text; b.addEventListener('click', action); return b; }
  function markDirty() { dirty = true; controls(); }
  function controls() {
    $('saveButton').disabled = busy || !dirty;
    $('reopenButton').disabled = busy;
    $('exportButton').disabled = busy;
    $('imageFileInput').disabled = busy;
    $('jsonFileInput').disabled = busy;
    $('undoButton').disabled = busy || !(undos.get(pageId)?.length);
    $('deleteButton').disabled = busy || !box();
    $('revisionLabel').textContent = state ? `版本 ${state.revision}${dirty?' · 有未保存草稿':''}${busy?' · 正在处理':''}` : '读取中';
  }
  function remember(boxes) { const history = undos.get(pageId) || []; history.push(clone(boxes)); if (history.length>50) history.shift(); undos.set(pageId,history); }
  async function request(path, body) {
    const response = await fetch(path, body ? {method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf_token}, body:JSON.stringify({...body, expected_revision:state.revision})} : {});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error?.message || `请求失败 ${response.status}`);
    return result;
  }
  function adopt(value) {
    state = value; pages = clone(value.pages);
    if (!pages.some(p => p.page_id===pageId)) pageId = pages[0]?.page_id || null;
    selected = null; dirty = false; gesture = null; undos.clear(); render();
  }
  async function history() {
    const result = await request('/api/history'); $('historyList').replaceChildren();
    for (const entry of result.revisions) {
      const b = button(`v${entry.revision} · ${entry.action}`, async () => {
        if (busy || !confirm(`恢复版本 ${entry.revision}？当前未保存编辑将放弃，已保存历史仍保留。`)) return;
        await mutate('/api/restore', {revision:entry.revision}, '已恢复为一个新版本。');
      });
      b.disabled = busy; $('historyList').append(b);
    }
  }
  async function mutate(path, body, success) {
    if (busy) return; busy=true; controls(); notice('正在本机处理，请稍候…');
    try { const result = await request(path,body); adopt(result); notice(success); }
    catch (error) { notice(`${error.message}。本页未保存草稿仍保留；没有显示为保存成功。`,true); }
    finally { busy=false; controls(); }
    try { await history(); } catch (error) { notice(`工作区状态已保留，历史列表暂不可读：${error.message}`,true); }
  }
  function render() {
    $('workspaceLabel').textContent = state ? `${pages.length}页 · 本地草稿` : '正在读取';
    $('pageCount').textContent=pages.length; $('pageList').replaceChildren();
    for (const p of pages) {
      const b = button(`${p.name} · ${p.boxes.length}框`, () => { if(busy)return; pageId=p.page_id;selected=null;render(); });
      b.className='page-item';b.classList.toggle('active',p.page_id===pageId);b.dataset.pageId=p.page_id; $('pageList').append(b);
    }
    const p = page(); $('canvasEmpty').hidden=!!p; $('stageShell').hidden=!p;
    $('canvasHeading').textContent=p ? `${p.name} · ${p.width}×${p.height}` : '尚未导入页面';
    if(p) {
      $('stage').setAttribute('viewBox',`0 0 ${p.width} ${p.height}`);
      $('pageImage').setAttribute('width',p.width); $('pageImage').setAttribute('height',p.height);
      $('pageImage').setAttribute('href',p.image_url); scale();
    }
    renderBoxes(); controls();
  }
  function scale() { const p=page();if(!p)return; $('stage').setAttribute('width',p.width*zoom);$('stage').setAttribute('height',p.height*zoom); }
  function svg(name, attrs) { const element=document.createElementNS(NS,name);for(const [k,v]of Object.entries(attrs))element.setAttribute(k,v);return element; }
  function frames() {
    $('boxLayer').replaceChildren();$('selectionLayer').replaceChildren();
    for(const b of page()?.boxes || []) {
      const [x0,y0,x1,y1]=b.bbox;
      const rect=svg('rect',{x:x0,y:y0,width:x1-x0,height:y1-y0,class:`box-shape${b.box_id===selected?' selected':''}`,'data-box-id':b.box_id});
      const title=svg('title',{});title.textContent=`${kinds[b.kind]} · ${b.bbox.join(', ')}`;rect.append(title);$('boxLayer').append(rect);
    }
    const b=box();if(!b)return;
    const [x0,y0,x1,y1]=b.bbox, size=8/zoom;
    for(const [corner,x,y]of [['nw',x0,y0],['ne',x1,y0],['sw',x0,y1],['se',x1,y1]])
      $('selectionLayer').append(svg('rect',{x:x-size/2,y:y-size/2,width:size,height:size,class:'handle','data-corner':corner}));
  }
  function inspector() {
    const b=box();$('inspector').hidden=!b;$('selectionCount').textContent=`已选 ${b?1:0} 个框`;
    if(!b)return;
    $('boxIdLabel').textContent=b.box_id;$('kindInput').value=b.kind;$('originLabel').textContent=b.origin;
    ['x0','y0','x1','y1'].forEach((n,i)=>{$(n+'Input').value=b.bbox[i];});
  }
  function renderBoxes() {
    frames();inspector();$('boxCount').textContent=page()?.boxes.length || 0;$('boxList').replaceChildren();
    for(const b of page()?.boxes || []) {
      const item=button(`${kinds[b.kind]} · ${b.bbox.join(', ')} · ${b.origin}`,()=>{if(busy)return;selected=b.box_id;renderBoxes();controls();});
      item.className='box-item';item.classList.toggle('active',selected===b.box_id);item.dataset.boxId=b.box_id;$('boxList').append(item);
    }
  }
  function sourcePoint(event) { const p=page();return G.point(event.clientX,event.clientY,$('stage').getBoundingClientRect(),p.width,p.height); }
  $('stage').addEventListener('pointerdown',event=>{
    if(busy || !page() || event.button!==0)return;
    const cursor=sourcePoint(event), id=event.target.dataset.boxId, corner=event.target.dataset.corner;
    const before=clone(page().boxes);
    if(tool==='draw') { selected=null;gesture={mode:'draw',start:cursor,before,pointerId:event.pointerId}; }
    else if(corner && box()) gesture={mode:'resize',corner,start:cursor,before,original:clone(box().bbox),pointerId:event.pointerId};
    else if(id) { selected=id;gesture={mode:'move',start:cursor,before,original:clone(box().bbox),pointerId:event.pointerId}; }
    else {selected=null;renderBoxes();controls();return;}
    $('stage').setPointerCapture(event.pointerId); event.preventDefault();frames();inspector();controls();
  });
  $('stage').addEventListener('pointermove',event=>{
    if(!page())return;
    const cursor=sourcePoint(event);$('coordinateReadout').textContent=`原图坐标：${cursor.map(n=>n.toFixed(1)).join(', ')}`;
    if(!gesture || gesture.pointerId!==event.pointerId)return;
    const p=page();let bbox;
    if(gesture.mode==='draw') {
      bbox=G.normalize(gesture.start,cursor,p.width,p.height);$('drawPreview').hidden=!bbox;
      if(bbox){const [x,y,x1,y1]=bbox;for(const[k,v]of Object.entries({x,y,width:x1-x,height:y1-y}))$('drawPreview').setAttribute(k,v);}
    } else {
      bbox=gesture.mode==='move'?G.move(gesture.original,cursor[0]-gesture.start[0],cursor[1]-gesture.start[1],p.width,p.height):G.resize(gesture.original,gesture.corner,cursor,p.width,p.height);
      if(bbox){box().bbox=bbox;frames();inspector();}
    }
  });
  function endGesture(event,cancel=false) {
    if(!gesture || event.pointerId!==gesture.pointerId)return;
    const p=page(), before=gesture.before;
    if(cancel) p.boxes=before;
    else if(gesture.mode==='draw') {
      const bbox=G.normalize(gesture.start,sourcePoint(event),p.width,p.height);
      if(bbox){selected='manual-'+crypto.randomUUID();p.boxes.push({box_id:selected,bbox,kind:'candidate',origin:'MANUAL',status:'DRAFT'});}
    }
    if(!cancel && JSON.stringify(before)!==JSON.stringify(p.boxes)) {
      const b=box();if(b)b.origin='MANUAL';remember(before);markDirty();
    }
    gesture=null;$('drawPreview').hidden=true;render();
  }
  $('stage').addEventListener('pointerup',e=>endGesture(e));
  $('stage').addEventListener('pointercancel',e=>endGesture(e,true));
  function setTool(value) { tool=value;for(const[id,mode]of [['drawToolButton','draw'],['selectToolButton','select']]){$(id).classList.toggle('active',mode===tool);$(id).setAttribute('aria-pressed',String(mode===tool));} }
  $('drawToolButton').addEventListener('click',()=>setTool('draw'));
  $('selectToolButton').addEventListener('click',()=>setTool('select'));
  $('zoomInput').value=String(zoom);
  function fit() {if(!page())return;zoom=Math.min(2,Math.max(.1,($('stageShell').clientWidth-4)/page().width));$('zoomInput').value='fit';scale();frames();}
  $('zoomInput').addEventListener('change',()=>{if($('zoomInput').value==='fit')fit();else{zoom=Number($('zoomInput').value);scale();frames();}});
  $('fitButton').addEventListener('click',fit);
  $('deleteButton').addEventListener('click',()=>{if(busy||!box())return;remember(page().boxes);page().boxes=page().boxes.filter(b=>b.box_id!==selected);selected=null;markDirty();render();});
  $('undoButton').addEventListener('click',()=>{const previous=undos.get(pageId)?.pop();if(busy||!previous)return;page().boxes=previous;selected=null;markDirty();render();});
  $('kindInput').addEventListener('change',()=>{if(busy||!box())return;remember(page().boxes);box().kind=$('kindInput').value;box().origin='MANUAL';markDirty();renderBoxes();});
  $('applyCoordinatesButton').addEventListener('click',()=>{
    if(busy||!box())return;
    const values=['x0','y0','x1','y1'].map(n=>$(n+'Input').value.trim()), bbox=values.map(Number), p=page();
    if(values.some(x=>!x)||!bbox.every(Number.isFinite)||bbox[0]<0||bbox[1]<0||bbox[2]>p.width||bbox[3]>p.height||bbox[2]-bbox[0]<2||bbox[3]-bbox[1]<2) {notice('坐标无效：须在原图内且至少2×2像素。',true);inspector();return;}
    remember(p.boxes);box().bbox=bbox;box().origin='MANUAL';markDirty();renderBoxes();
  });
  $('saveButton').addEventListener('click',async()=>{
    if(!dirty)return;
    await mutate('/api/save',{pages:pages.map(p=>({page_id:p.page_id,sha256:p.sha256,width:p.width,height:p.height,boxes:p.boxes}))},'草稿已保存，可关闭后重开。');
  });
  $('reopenButton').addEventListener('click',async()=>{
    if(busy || (dirty&&!confirm('放弃当前未保存草稿并重开已保存版本？')))return;
    busy=true;controls();try{adopt(await request('/api/state'));notice('已读取保存版本。');}catch(e){notice(e.message,true);}finally{busy=false;controls();}
  });
  const readData=file=>new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(new Error('图片读取失败'));reader.readAsDataURL(file);});
  $('imageFileInput').addEventListener('change',async event=>{
    const files=[...event.target.files];if(!files.length)return;
    if(busy)return;
    if(dirty){notice('请先保存草稿，再导入图片。',true);event.target.value='';return;}
    busy=true;controls();
    try {
      if(files.length>100||files.some(f=>f.size>25*1024*1024)||files.reduce((s,f)=>s+f.size,0)>55*1024*1024)throw new Error('请分批导入：单图25MB内，单批原图合计55MB内');
      const payload=[];for(const file of files)payload.push({name:file.name,data_base64:await readData(file)});
      busy=false;
      await mutate('/api/import-images',{files:payload},'书页已导入并生成几何候选，请人工检查合框与漏框。');
    }catch(e){notice(e.message,true);}finally{busy=false;controls();event.target.value='';}
  });
  $('jsonFileInput').addEventListener('change',async event=>{
    const file=event.target.files[0];if(!file)return;
    if(busy || (dirty&&!confirm('导入将替换当前页面列表，放弃未保存编辑？已保存历史保留。'))){event.target.value='';return;}
    busy=true;controls();
    try{if(file.size>60*1024*1024)throw new Error('JSON超过60MB，请分成较小工作区');const text=await file.text();busy=false;await mutate('/api/import',{document_text:text},'JSON已按图片身份重新导入；导入框仍是未核准草稿。');}
    catch(e){notice(e.message,true);}finally{busy=false;controls();event.target.value='';}
  });
  $('exportButton').addEventListener('click',()=>{if(dirty){notice('请先保存草稿，再导出当前版本。',true);return;}const a=document.createElement('a');a.href='/api/export';a.download='prebox-draft.json';a.click();});
  $('refreshHistoryButton').addEventListener('click',()=>history().catch(e=>notice(e.message,true)));
  window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
  $('pageImage').addEventListener('error',()=>notice('原图加载失败，请保留草稿并重开工作区检查原图。',true));
  request('/api/state').then(value=>{adopt(value);return history();}).catch(e=>notice(`工作区读取失败：${e.message}`,true));
})();
