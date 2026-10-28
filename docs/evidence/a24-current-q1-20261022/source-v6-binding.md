# A24 当前第 1 题来源绑定补充（2026-10-22，v6）

已取得当前活动节点“1 插题”的 DOM `data-key=1792064001811`。页面控件仍为题目页 `10`、答案页 `173`、序号 `1/22`。

题页和答页不是 `<img>`，而是两个可见 `canvas.pdf-canvas`：题页画布 592×734，答页画布 498×734；各自父节点 `data-page-index=0`。当前页面唯一 `<img>` 是站点 Logo。因此题页/答页没有可记录的 `src/currentSrc/naturalWidth/naturalHeight`，实际来源 URL 在可见 DOM 中未暴露。

依据本机既有来源清单，控件页码可对应两个候选原件：

- viewer 10：`46007447_viewer_10.jpg`，478,123 字节，SHA-256 `eb7cc17e6b58a55a005ce1cdef5bd5058ad258c3dd44dc891b3d830ed3db3626`，既有清单尺寸 1217×1691。
- viewer 173：`46007447_viewer_173.jpg`，428,192 字节，SHA-256 `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be`，既有清单尺寸 1148×1621。

两者只能标为 `LOCAL_MANIFEST_CANDIDATE`：当前 DOM 没有页图 URL，无法把正在显示的 canvas 字节与本机 JPEG 做当前会话的哈希等同证明。`data-key=1792064001811` 同样只是当前 DOM 键，不升格为 canonical `question_id`。

本轮只读取 DOM 属性，没有点击、编辑、识别、验证、保存、提交、上传或导出。
