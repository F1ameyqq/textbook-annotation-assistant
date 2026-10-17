"""Independent source-patch localization in retained canvas/screenshot pixels.

No ViewerMapping or forward/inverse coordinate formula is imported here. The
matcher searches the entire retained image, not a mapper-predicted neighborhood.
It checks local texture, not OCR/content/semantic quality.
"""
import math
import heapq
from PIL import Image

from .coordinates import CoordinateError


def locate_patch(original, target, box, scale):
    """Return a measured patch center using an exhaustive sparse texture search.

    Scale is taken from the separately observed browser draw call and screenshot
    pixel ratio, not from the mapping being tested. Translation is unconstrained.
    """
    sx, sy = scale
    x1, y1, x2, y2 = box
    width, height = round((x2-x1)*sx), round((y2-y1)*sy)
    if min(width, height) < 12 or width > target.width or height > target.height:
        raise CoordinateError("REFERENCE_PATCH_TOO_SMALL")
    patch = original.crop(box).convert("L").resize((width, height), Image.Resampling.BILINEAR)
    target = target.convert("L")
    data = patch.load(); pixels = target.load()
    # Stable spatially distributed bright/dark probes; no expected x/y used.
    buckets = []
    for gy in range(5):
        for gx in range(8):
            pts = [(data[x,y],x,y) for y in range(gy*height//5,(gy+1)*height//5)
                   for x in range(gx*width//8,(gx+1)*width//8)]
            if pts:
                buckets.extend((min(pts),max(pts)))
    probes = sorted(set(buckets))
    if sum(1 for value,_,_ in probes if value < 180) < 10:
        raise CoordinateError("REFERENCE_TEXTURE_WEAK")
    limit = float("inf"); best = None
    candidates = []
    def score(x,y,cutoff):
        total = 0
        for index,(value,px,py) in enumerate(probes,1):
            total += abs(pixels[x+px,y+py]-value)
            if total > cutoff*len(probes):
                return float("inf")
        return total/len(probes)
    # A 2px coarse search followed by exhaustive 1px refinement. This scans all
    # target locations and remains sensitive to a wrong page/offset/scale.
    for y in range(0,target.height-height+1,2):
        for x in range(0,target.width-width+1,2):
            cutoff=-candidates[0][0] if len(candidates)==32 else float('inf')
            value=score(x,y,cutoff)
            if math.isfinite(value):
                heapq.heappush(candidates,(-value,x,y))
                if len(candidates)>32:heapq.heappop(candidates)
    if not candidates:
        raise CoordinateError("REFERENCE_NOT_FOUND")
    for _,bx,by in candidates:
        for y in range(max(0,by-2),min(target.height-height,by+2)+1):
            for x in range(max(0,bx-2),min(target.width-width,bx+2)+1):
                value=score(x,y,limit)
                if value < limit:
                    limit=value;best=(x,y)
    if limit > 35:
        raise CoordinateError("REFERENCE_NOT_FOUND")
    return {"center":[best[0]+width/2,best[1]+height/2],"mean_absolute_probe_error":limit,
            "patch_size":[width,height],"search":"whole-target coarse2 then local1",
            "probe_count":len(probes)}
