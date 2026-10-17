"""Original-patch / actual canvas / independent CSS screenshot checks."""
import base64
import copy
import json
from pathlib import Path

from PIL import Image
from annotation.delivery.usense_readonly.coordinates import (
    ViewerMapping, CoordinateError, binding_from_file, check_reference_points,
)
from annotation.delivery.usense_readonly.pixel_reference import locate_patch
from .viewer_observation import observe_draw, zoom_and_pan


def check_case(page, output, viewer_page, zone, source_index, refs, label, *, renderer_mode='PLATFORM'):
    from .collector import save_json
    output=Path(output)
    original_path=output/f'assets/page-{viewer_page}.jpg'
    image=binding_from_file(original_path,f'asset-a04-book-46007447-viewer-{viewer_page}')
    selection=refs['pages'][str(viewer_page)]
    if image.sha256 != selection['sha256'] or [image.width,image.height] != selection['size']:
        raise CoordinateError('REFERENCE_ORIGINAL_CHANGED')
    observation=observe_draw(page,zone,image,viewer_page,source_index)
    canvas=page.locator('.pdf-zone').nth(zone).locator('canvas').first
    canvas_url=canvas.evaluate("c=>c.toDataURL('image/png')")
    prefix=f'evidence/coordinates/page-{viewer_page}-{label}'
    target=output/(prefix+'-canvas.png');target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(base64.b64decode(canvas_url.split(',',1)[1],validate=True))
    screenshot=output/(prefix+'-pane.png')
    pane=page.locator('.pdf-zone').nth(zone)
    pane.screenshot(path=str(screenshot),scale='css')
    original=Image.open(original_path);painted=Image.open(target);shot=Image.open(screenshot)
    dx,dy,dw,dh=observation['draw_destination'];a,b,c,d,e,f=observation['canvas_ctm']
    draw_scale=(dw*a/image.width,dh*d/image.height)
    pane_x,pane_y,pane_w,pane_h=observation['pane_rect']
    css_w,css_h=observation['css_rect'][2:]
    cw,ch=observation['canvas_size']
    shot_scale=(draw_scale[0]*css_w/cw*shot.width/pane_w,draw_scale[1]*css_h/ch*shot.height/pane_h)
    measurements=[]
    for box in selection['patches']:
        center=[(box[0]+box[2])/2,(box[1]+box[3])/2]
        canvas_match=locate_patch(original,painted,box,draw_scale)
        css_match=locate_patch(original,shot,box,shot_scale)
        # Screenshot pixels are located independently. The pane clip, not the
        # canvas origin or tested mapper, converts them to viewport CSS points.
        measured_css=[pane_x+css_match['center'][0]*pane_w/shot.width,
                      pane_y+css_match['center'][1]*pane_h/shot.height]
        measurements.append({'original':center,'original_patch':box,'measured_canvas':canvas_match['center'],
                             'measured_css':measured_css,'canvas_match':canvas_match,'css_match':css_match})
    mapping=ViewerMapping(image,viewer_page,source_index,observation)
    save_json(output/(prefix+'-measurements.json'),{'observation':observation,
              'independent_measurements':measurements,'verification':'PENDING'})
    checks=check_reference_points(mapping,measurements)
    # These are only local negative probes using actual retained pixels. No
    # erroneous point or mutation is sent to the live platform.
    rejected=[]
    for name,field,index,delta in [('wrong-canvas-offset','canvas_ctm',4,20),
                                  ('wrong-css-origin','css_rect',0,20),
                                  ('wrong-scale','draw_destination',2,dw*.1)]:
        wrong=copy.deepcopy(observation);wrong[field][index]+=delta
        try:
            check_reference_points(ViewerMapping(image,viewer_page,source_index,wrong),measurements)
        except CoordinateError as error:
            rejected.append({'case':name,'code':error.code})
        else:
            raise CoordinateError('WRONG_MAPPING_NOT_REJECTED')
    report={'mode':'OBSERVED','renderer_mode':renderer_mode,'platform_observation':renderer_mode=='PLATFORM',
            'original_provenance':'LIVE' if renderer_mode=='PLATFORM' else 'HISTORICAL',
            'label':label,'image':image.model_dump(mode='json'),
            'observation':observation,'mapping':mapping.describe(),'independent_measurements':measurements,
            'checks':checks,'negative_local_probes':rejected,
            'tolerances':{'canvas_and_css_pixels':2.5,'original_pixels':8},
            'reference_method':'predetermined original crops; whole-canvas and whole-pane sparse pixel matching; no predicted translation search',
            'content_quality':'NOT_ASSESSED'}
    save_json(output/(prefix+'.json'),report)
    return report


def probe_page(page,output,viewer_page,zone,source_index,refs):
    if str(viewer_page) not in refs['pages']:
        return []
    baseline=check_case(page,output,viewer_page,zone,source_index,refs,'baseline')
    zoom_and_pan(page,zone)
    changed=check_case(page,output,viewer_page,zone,source_index,refs,'zoom-pan')
    before=baseline['mapping'];after=changed['mapping']
    if (before['canvas_scale']==after['canvas_scale'] or before['canvas_offset']==after['canvas_offset']):
        raise CoordinateError('VIEWER_GESTURE_NOT_OBSERVED')
    return [baseline,changed]
