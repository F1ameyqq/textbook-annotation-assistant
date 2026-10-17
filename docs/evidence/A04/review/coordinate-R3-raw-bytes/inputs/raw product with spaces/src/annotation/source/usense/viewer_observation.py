"""Read-only browser render instrumentation and bounded presentation gestures."""
import base64
from annotation.runtime.browser.guard import BrowserSafetyError

DRAW_OBSERVER = r"""(() => {
  const original=CanvasRenderingContext2D.prototype.drawImage;
  const records=new WeakMap(); let sequence=0;
  Object.defineProperty(window,'__a04Draw',{value:canvas=>records.get(canvas)||null});
  CanvasRenderingContext2D.prototype.drawImage=function(image,...args){
    const result=original.call(this,image,...args);
    try {
      const url=new URL(image.currentSrc||image.src,location.href);
      const match=url.pathname.match(/^\/upload_images\/46007447\/46007447_page_(13|14|172)\.jpg$/);
      if(match && image.naturalWidth && this.canvas.closest('.pdf-zone')){
        let src,dst;
        if(args.length===2){src=[0,0,image.naturalWidth,image.naturalHeight];dst=[...args,image.naturalWidth,image.naturalHeight];}
        if(args.length===4){src=[0,0,image.naturalWidth,image.naturalHeight];dst=args;}
        if(args.length===8){src=args.slice(0,4);dst=args.slice(4);}
        const m=this.getTransform();
        if(src&&dst) records.set(this.canvas,{source_index:Number(match[1]),natural_size:[image.naturalWidth,image.naturalHeight],
          draw_source:src,draw_destination:dst,canvas_ctm:[m.a,m.b,m.c,m.d,m.e,m.f],sequence:++sequence});
      }
    }catch(_){} return result;
  };
})();"""

READ_DRAW = r"""zone => {
 const el=document.querySelectorAll('.pdf-zone')[zone], canvas=el?.querySelector('canvas');
 const draw=canvas && window.__a04Draw?.(canvas); if(!draw) return null;
 const r=canvas.getBoundingClientRect(),p=el.getBoundingClientRect();
 return {...draw,canvas_size:[canvas.width,canvas.height],css_rect:[r.x,r.y,r.width,r.height],
    pane_rect:[p.x,p.y,p.width,p.height],viewport:[innerWidth,innerHeight],dpr:devicePixelRatio,
    scroll:[scrollX,scrollY],pane_scroll:[el.scrollLeft,el.scrollTop],
    canvas_css_transform:getComputedStyle(canvas).transform};
}"""


def observe_draw(page, zone_index, image, viewer_page, source_index):
    page.wait_for_function("z => { const c=document.querySelectorAll('.pdf-zone')[z]?.querySelector('canvas'); return c && window.__a04Draw?.(c); }",
                           arg=zone_index,timeout=30000)
    observation=page.evaluate(READ_DRAW,zone_index)
    if (observation["source_index"] != source_index or observation["natural_size"] != [image.width,image.height]
            or observation["canvas_css_transform"] != "none"):
        raise BrowserSafetyError("UI_MISMATCH","verify")
    observation.update(image=image.model_dump(mode="json"),viewer_page=viewer_page)
    fit=min(observation['canvas_size'][0]/image.width,observation['canvas_size'][1]/image.height)
    observation['fit_scale']=fit
    observation['zoom_xy']=[observation['draw_destination'][2]/image.width/fit,
                            observation['draw_destination'][3]/image.height/fit]
    observation['pan_backing']=[observation['canvas_ctm'][4],observation['canvas_ctm'][5]]
    return observation


def zoom_and_pan(page, zone_index):
    canvas=page.locator('.pdf-zone').nth(zone_index).locator('canvas').first
    box=canvas.bounding_box()
    if box is None:
        raise BrowserSafetyError("UI_MISMATCH","navigate")
    x=box['x']+box['width']*.52; y=box['y']+box['height']*.48
    canvas.dispatch_event('wheel',{'deltaY':-100,'clientX':x,'clientY':y,'bubbles':True,'cancelable':True})
    canvas.dispatch_event('mousedown',{'button':1,'buttons':4,'clientX':x,'clientY':y,'bubbles':True,'cancelable':True})
    canvas.dispatch_event('mousemove',{'button':1,'buttons':4,'clientX':x+13,'clientY':y-9,'bubbles':True})
    canvas.dispatch_event('mouseup',{'button':1,'buttons':0,'clientX':x+13,'clientY':y-9,'bubbles':True})
    page.evaluate("() => new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
