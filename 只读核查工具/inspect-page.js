// 在目标标注页的 DevTools Console 中运行；只读取页面结构并输出 JSON。
// 不发请求，不读 Cookie/存储/输入值，不点击、不画框、不修改 DOM。
(() => {
  "use strict";

  if (location.protocol !== "https:" ||
      !["www.usense.com", "usense.com"].includes(location.hostname) ||
      !["", "443"].includes(location.port) ||
      location.pathname !== "/qieti/annotateUnified") {
    throw new Error("请在 https://www.usense.com/qieti/annotateUnified 标注页运行。");
  }

  const limit = (value, size = 120) => String(value ?? "").slice(0, size);
  const round = value => Math.round(Number(value) * 1000) / 1000;
  const box = element => {
    const r = element.getBoundingClientRect();
    return { x: round(r.x), y: round(r.y), width: round(r.width), height: round(r.height) };
  };
  const name = element => ({
    tag: element.tagName,
    id: limit(element.id),
    classes: limit(element.getAttribute("class"), 240)
  });
  const layout = element => {
    const s = getComputedStyle(element);
    return {
      ...name(element), box: box(element),
      clientWidth: element.clientWidth, clientHeight: element.clientHeight,
      scrollWidth: element.scrollWidth, scrollHeight: element.scrollHeight,
      scrollLeft: element.scrollLeft, scrollTop: element.scrollTop,
      display: s.display, visibility: s.visibility, position: s.position,
      overflowX: s.overflowX, overflowY: s.overflowY,
      transform: s.transform, transformOrigin: s.transformOrigin,
      zoom: s.zoom, objectFit: s.objectFit, objectPosition: s.objectPosition,
      padding: [s.paddingTop, s.paddingRight, s.paddingBottom, s.paddingLeft],
      border: [s.borderTopWidth, s.borderRightWidth, s.borderBottomWidth, s.borderLeftWidth]
    };
  };
  const ancestors = element => {
    const result = [];
    let parent = element.parentElement;
    while (parent && result.length < 6) {
      result.push(layout(parent));
      parent = parent.parentElement;
    }
    return result;
  };
  const originOnly = raw => {
    try {
      const u = new URL(raw, location.origin);
      return ["https:", "http:"].includes(u.protocol) ? u.origin : `[${u.protocol}]`;
    } catch { return "[unavailable]"; }
  };
  const scripts = Array.from(document.scripts).filter(e => e.src).slice(0, 80).map(e => {
    try {
      const u = new URL(e.src, location.origin);
      return ["https:", "http:"].includes(u.protocol)
        ? { origin: u.origin, path: u.pathname }
        : { origin: `[${u.protocol}]` };
    } catch { return { origin: "[unavailable]" }; }
  });
  const images = Array.from(document.images).filter(e => {
    const r = e.getBoundingClientRect();
    return e.naturalWidth >= 300 || r.width >= 150 || r.height >= 150;
  }).slice(0, 100).map((e, index) => ({
    index, ...layout(e), naturalWidth: e.naturalWidth, naturalHeight: e.naturalHeight,
    complete: e.complete, resourceOrigin: originOnly(e.currentSrc || e.src),
    ancestors: ancestors(e)
  }));
  const canvases = Array.from(document.querySelectorAll("canvas")).slice(0, 60).map((e, index) => ({
    index, ...layout(e), backingWidth: e.width, backingHeight: e.height,
    ancestors: ancestors(e)
  }));
  const svg = Array.from(document.querySelectorAll("svg")).filter(e => {
    const r = e.getBoundingClientRect();
    return r.width >= 150 && r.height >= 150;
  }).slice(0, 20).map(e => ({
    ...layout(e), viewBox: e.getAttribute("viewBox"),
    rectangles: Array.from(e.querySelectorAll("rect")).slice(0, 100).map(r => ({
      ...name(r), x: r.getAttribute("x"), y: r.getAttribute("y"),
      width: r.getAttribute("width"), height: r.getAttribute("height"),
      transform: r.getAttribute("transform")
    }))
  }));
  const containers = Array.from(document.querySelectorAll("main,section,article,aside,div"))
    .slice(0, 4000).filter(e =>
      e.scrollHeight > e.clientHeight + 2 || e.scrollWidth > e.clientWidth + 2
    ).slice(0, 40).map(layout);
  const controls = Array.from(document.querySelectorAll("button,[role='button'],.el-button"))
    .slice(0, 100).map(e => ({ ...name(e), box: box(e), label: limit(e.textContent, 60) }));
  const frames = Array.from(document.querySelectorAll("iframe")).slice(0, 20)
    .map(e => ({ ...layout(e), resourceOrigin: originOnly(e.src) }));
  const pageElements = Array.from(document.querySelectorAll(".pdf-page"));
  const annotationElements = Array.from(document.querySelectorAll(".rect-box"))
    .slice(0, 500).map(e => ({
      ...name(e), box: box(e),
      pageElementIndex: pageElements.indexOf(e.closest(".pdf-page")),
      rectIndex: e.getAttribute("data-rect-index"),
      pageIndex: e.closest(".pdf-page")?.getAttribute("data-page-index") ?? null,
      style: {left:e.style.left, top:e.style.top, width:e.style.width,
        height:e.style.height, transform:e.style.transform}
    }));
  const report = {
    schema: "usense-readonly-layout.v1",
    capturedAt: new Date().toISOString(),
    page: { origin: location.origin, path: location.pathname, title: limit(document.title) },
    viewport: {
      width: innerWidth, height: innerHeight, devicePixelRatio,
      scrollX, scrollY,
      visual: window.visualViewport ? {
        width: round(window.visualViewport.width), height: round(window.visualViewport.height),
        scale: window.visualViewport.scale,
        offsetLeft: window.visualViewport.offsetLeft, offsetTop: window.visualViewport.offsetTop
      } : null
    },
    images, canvases, svg, containers, controls, frames, scripts, annotationElements,
    limits: [
      "未执行画框、快捷键、翻页、识别、保存或提交。",
      "未访问 Cookie、浏览器存储、输入值或网络请求头。",
      "只报告已加载的结构；不证明鼠标交互、跨页保留或保存成功。",
      "框坐标仍需结合 object-fit、边框和祖先变换解释。"
    ]
  };
  const json = JSON.stringify(report, null, 2);
  console.log(json);
  return json;
})();
