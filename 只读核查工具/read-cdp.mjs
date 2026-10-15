// 仅连接已经开启的本机 CDP，不启动/关闭浏览器，不忽略证书，不发送输入。
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

const endpoint = new URL('http://127.0.0.1:9347');
const outputArg = process.argv.find(arg => arg.startsWith('--output='));
const captureArg = process.argv.find(arg => arg.startsWith('--capture='));
const resourcesArg = process.argv.find(arg => arg.startsWith('--resources-dir='));
const safeUrl = raw => {
  try {
    const u = new URL(raw);
    return ['http:', 'https:'].includes(u.protocol)
      ? `${u.origin}${u.pathname}` : `${u.protocol}[details omitted]`;
  } catch { return '[unavailable]'; }
};
const isTarget = raw => {
  try {
    const u = new URL(raw);
    return u.protocol === 'https:' && ['www.usense.com', 'usense.com'].includes(u.hostname)
      && ['', '443'].includes(u.port) && u.pathname === '/qieti/annotateUnified';
  } catch { return false; }
};
const getJson = async path => {
  const response = await fetch(new URL(path, endpoint), {
    redirect: 'error', signal: AbortSignal.timeout(5000)
  });
  if (!response.ok) throw new Error(`CDP HTTP ${response.status}`);
  return response.json();
};

let socket;
try {
  const version = await getJson('/json/version');
  if (!/^Edg\//.test(version.Browser ?? '')) throw new Error('端点不是预期的 Edge');
  const targets = await getJson('/json/list');
  const pages = targets.filter(target => target.type === 'page');
  const candidates = pages.filter(target => isTarget(target.url));
  if (candidates.length !== 1) {
    console.log(JSON.stringify({
      cdpConnected: true, browser: version.Browser, targetPageReady: false,
      reason: '需要且仅能有一个目标标注页',
      pages: pages.map(page => ({ title: page.title, url: safeUrl(page.url) }))
    }, null, 2));
    process.exitCode = 2;
  } else {
    const target = candidates[0];
    const wsUrl = new URL(target.webSocketDebuggerUrl);
    if (wsUrl.protocol !== 'ws:' || !['127.0.0.1', 'localhost', '[::1]'].includes(wsUrl.hostname)
        || wsUrl.port !== endpoint.port || !wsUrl.pathname.startsWith('/devtools/page/')) {
      throw new Error('调试 WebSocket 不属于预期的本机端口');
    }
    socket = new WebSocket(wsUrl);
    const pending = new Map();
    let sequence = 0;
    socket.addEventListener('message', event => {
      const message = JSON.parse(String(event.data));
      const task = pending.get(message.id);
      if (!task) return;
      pending.delete(message.id);
      clearTimeout(task.timer);
      if (message.error) task.reject(new Error(message.error.message));
      else task.resolve(message.result);
    });
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('CDP WebSocket 连接超时')), 5000);
      socket.addEventListener('open', () => { clearTimeout(timer); resolve(); }, { once: true });
      socket.addEventListener('error', () => {
        clearTimeout(timer); reject(new Error('CDP WebSocket 连接失败'));
      }, { once: true });
    });
    const sendReadOnly = (method, params = {}) => {
      if (!['Runtime.evaluate', 'Page.enable', 'Page.getLayoutMetrics', 'Page.captureScreenshot',
        'Page.getResourceTree', 'Page.getResourceContent'].includes(method)) {
        throw new Error('该脚本不允许此 CDP 命令');
      }
      return new Promise((resolve, reject) => {
        const id = ++sequence;
        const timer = setTimeout(() => { pending.delete(id); reject(new Error(`${method} 超时`)); }, 7000);
        pending.set(id, { resolve, reject: error => reject(new Error(`${method}: ${error.message}`)), timer });
        socket.send(JSON.stringify({ id, method, params }));
      });
    };
    await sendReadOnly('Page.enable');
    const probe = await sendReadOnly('Runtime.evaluate', {
      expression: '({origin:location.origin,path:location.pathname,title:document.title,readyState:document.readyState})',
      returnByValue: true, silent: true, timeout: 5000
    });
    const livePage = probe.result?.value;
    if (!livePage || !isTarget(`${livePage.origin}${livePage.path}`)) {
      console.log(JSON.stringify({ cdpConnected: true, targetPageReady: false,
        reason: '当前实际文档尚未进入目标标注页，请用户检查登录或浏览器安全提示', livePage }, null, 2));
      process.exitCode = 2;
    } else {
      const source = (await readFile(new URL('./inspect-page.js', import.meta.url), 'utf8'))
        .replace(/  console\.log\(json\);\r?\n/, '');
      const result = await sendReadOnly('Runtime.evaluate', {
        expression: source, returnByValue: true, silent: true, timeout: 5000
      });
      if (result.exceptionDetails || typeof result.result?.value !== 'string') {
        throw new Error(result.exceptionDetails?.text ?? '未取得结构报告');
      }
      const geometry = JSON.parse(result.result.value);
      const metrics = await sendReadOnly('Page.getLayoutMetrics');
      const runtimeDetails = await sendReadOnly('Runtime.evaluate', {
        expression: `(() => {
          const selectors = ['.pdf-page','.pdf-zone','.pdf-content','.pdf-zones-container','#app'];
          return selectors.flatMap(selector => [...document.querySelectorAll(selector)].slice(0,4).map(element => {
            const chain = []; let component = element.__vueParentComponent;
            while (component && chain.length < 7) {
              chain.push({name:component.type?.name || component.type?.__name || null,
                setupKeys:Object.keys(component.setupState || {}).slice(0,300),
                propKeys:Object.keys(component.props || {}).slice(0,100)});
              component = component.parent;
            }
            const vnodeProps = element.__vnode?.props || {};
            return {selector, classes:element.getAttribute('class'), chain,
              eventHandlers:Object.keys(vnodeProps).filter(key=>/^on[A-Z]/.test(key)).map(key=>({
                event:key,source:typeof vnodeProps[key] === 'function' ? String(vnodeProps[key]).slice(0,1000) : null
              }))};
          }));
        })()`, returnByValue: true, silent: true, timeout: 5000
      });
      if (runtimeDetails.exceptionDetails) throw new Error('读取组件结构失败');
      const componentData = await sendReadOnly('Runtime.evaluate', {
        expression: `(() => {
          const roots = [...document.querySelectorAll('#app')]
            .map(element=>element.__vue_app__?._container?._vnode || element._vnode).filter(Boolean);
          const visited = new Set(), names = [], viewers = [];
          const walk = (vnode, depth=0) => {
            if (!vnode || typeof vnode !== 'object' || depth>50 || visited.size>5000 || visited.has(vnode)) return;
            visited.add(vnode);
            const component = vnode.component;
            if (component) {
              const name = component.type?.name || component.type?.__name || null;
              if (name && !names.includes(name)) names.push(name);
              if (name === 'PdfViewerWithDivUnified') {
                const props = component.props;
                viewers.push({zone:props.zone,preAnnotationEnabled:props.preAnnotationEnabled,
                  selectedRectType:props.selectedRectType,maxQuestionOrder:props.maxQuestionOrder,
                  pages:(props.pages || []).slice(0,3).map(page=>{
                    const blocks = Array.isArray(page.blocks) ? page.blocks : [];
                    const typeCounts = {};
                    for (const block of blocks) { const kind = String(block.type ?? '[missing]').slice(0,40); typeCounts[kind]=(typeCounts[kind]||0)+1; }
                    return {fields:Object.keys(page),imageKind:typeof page.image==='string' ?
                      (page.image.startsWith('data:') ? 'data-url' : 'url-or-path') : typeof page.image,
                      imageStringLength:typeof page.image==='string' ? page.image.length : null,
                      blockCount:blocks.length,typeCounts,
                      blockSamples:blocks.slice(0,12).map(block=>({bbox:block.rect_bbox || block.bbox,
                        type:block.type,textLength:typeof block.text==='string' ? block.text.length : null}))};
                  }),
                  historicalCount:Array.isArray(props.currentPageManualRects)?props.currentPageManualRects.length:null,
                  historicalSamples:(props.currentPageManualRects || []).slice(0,5).map(rect=>({
                    bbox:rect.rect_bbox,type:rect.type,contentType:rect.content_type,
                    isPreAnnotation:rect.is_pre_annotation,pageIndex:rect.page_index,order:rect.order_in_level
                  }))});
              }
              walk(component.subTree,depth+1);
            }
            if (Array.isArray(vnode.children)) for (const child of vnode.children) walk(child,depth+1);
            if (Array.isArray(vnode.dynamicChildren)) for (const child of vnode.dynamicChildren) walk(child,depth+1);
            if (vnode.suspense) {walk(vnode.suspense.activeBranch,depth+1);walk(vnode.suspense.pendingBranch,depth+1);}
          };
          for(const root of roots) walk(root);
          return {rootCount:roots.length,visited:visited.size,componentNames:names,viewers};
        })()`, returnByValue: true, silent: true, timeout: 5000
      });
      if (componentData.exceptionDetails) throw new Error('读取已加载的框选属性失败');
      const report = { cdpConnected: true, browser: version.Browser, targetPageReady: true,
        geometry, layoutMetrics: metrics, runtimeDetails: runtimeDetails.result?.value,
        componentData: componentData.result?.value,
        platformWritesPerformed: false,
        validationBoundary: '只读取结构，未验证画框、翻页保留、识别或保存' };
      if (outputArg) await writeFile(outputArg.slice('--output='.length), JSON.stringify(report, null, 2), 'utf8');
      if (captureArg) {
        const screenshot = await sendReadOnly('Page.captureScreenshot', {
          format: 'png', fromSurface: true, captureBeyondViewport: false
        });
        await writeFile(captureArg.slice('--capture='.length), Buffer.from(screenshot.data, 'base64'));
        report.capture = captureArg.slice('--capture='.length);
      }
      if (resourcesArg) {
        const directory = resourcesArg.slice('--resources-dir='.length);
        await mkdir(directory, { recursive: true });
        const tree = await sendReadOnly('Page.getResourceTree');
        const frameId = tree.frameTree.frame.id;
        const scripts = (tree.frameTree.resources || []).filter(resource => {
          try {
            const u = new URL(resource.url);
            return resource.type === 'Script' && u.origin === 'https://www.usense.com'
              && /^\/qieti\/assets\/[A-Za-z0-9._-]+\.js$/.test(u.pathname);
          } catch { return false; }
        }).slice(0,30);
        report.cachedScripts = [];
        for (const script of scripts) {
          const resource = await sendReadOnly('Page.getResourceContent', {frameId, url:script.url});
          const file = path.join(directory, path.basename(new URL(script.url).pathname));
          await writeFile(file, resource.base64Encoded ? Buffer.from(resource.content,'base64') : resource.content);
          report.cachedScripts.push(file);
        }
      }
      if (outputArg) await writeFile(outputArg.slice('--output='.length), JSON.stringify(report, null, 2), 'utf8');
      console.log(JSON.stringify(outputArg ? {
        cdpConnected: true, targetPageReady: true, report: outputArg.slice('--output='.length),
        images: geometry.images.length, canvases: geometry.canvases.length, platformWritesPerformed: false
      } : report, null, 2));
    }
  }
} catch (error) {
  console.error(JSON.stringify({ error: error.message, cause: error.cause?.code,
    endpoint: endpoint.origin, platformWritesPerformed: false }));
  process.exitCode = 1;
} finally {
  if (socket) socket.close(); // 只断开本脚本的连接，保留浏览器及标签页。
}
