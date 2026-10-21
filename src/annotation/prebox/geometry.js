/* Shared, pure source-pixel transforms. Browser code and Node regression use this exact implementation. */
(function(root) {
  'use strict';
  const clamp = (n, lo, hi) => Math.min(hi, Math.max(lo, n));
  const round = n => Math.round(n * 1000) / 1000;
  function point(x, y, rect, width, height) {
    if (!(rect.width > 0 && rect.height > 0)) throw new Error('画布尚未加载');
    return [clamp((x-rect.left)*width/rect.width, 0, width), clamp((y-rect.top)*height/rect.height, 0, height)];
  }
  function normalize(a, b, width, height) {
    const box = [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])]
      .map((v, i) => round(clamp(v, 0, i%2 ? height : width)));
    return box[2]-box[0] >= 2 && box[3]-box[1] >= 2 ? box : null;
  }
  function move(box, dx, dy, width, height) {
    dx = clamp(dx, -box[0], width-box[2]); dy = clamp(dy, -box[1], height-box[3]);
    return box.map((v, i) => round(v+(i%2 ? dy : dx)));
  }
  function resize(box, corner, cursor, width, height) {
    const opposite = [corner.includes('w') ? box[2] : box[0], corner.includes('n') ? box[3] : box[1]];
    return normalize(opposite, cursor, width, height);
  }
  const api = {point, normalize, move, resize};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.PreboxGeometry = api;
})(typeof window === 'undefined' ? {} : window);
