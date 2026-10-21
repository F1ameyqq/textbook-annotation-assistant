# A24 fixed one-question model evidence and corrected-content review

Two separate dispositions are fixed:

1. **ACCEPTED_FIXED_PARTIAL_OCR_FAILURE_AND_OWN_RELEASE_ONLY** for the recorded local model attempt. Its original result remains **FAILED_HOLD**.
2. **ACCEPTED_FINITE_CORRECTED_ONE_QUESTION_CONTENT_ONLY** for reviewed-candidate-v1.json, SHA256 cd4ee0c6a379fa5bf8cc87dccdb010c423a9e2f9a2382336efaa00cefe103b5a. This accepts the explicitly corrected source content of one ordinary single-choice question, with AI visual correction and manual region/answer association disclosed.

No material defect was found in that corrected content. This is neither human-user approval nor native QuestionGraph/platform acceptance. Existing wire REWORK is unchanged; actual save and independent platform readback remain NOT_RUN.

## Fixed intake and provenance

Reviewer 01a15cf8-68e0-7b63-91a3-657a567b344c continued in the same A24 chat. Task SHA256 4c36e04e9e691f8c92f1af0c1e770b6d35ae8462445f86259b1b6efd45977966. New review root: D:/1800-worktrees/a24-model-one-question-review. No active wire author directory was read.

The result manifest (ec45a2c44e262a96b210aa5fd8a00a8a360721a4773cbaede4a7d22596ee3108) contains 36 members; the original startup-failure manifest (895919d656681712574a04d5b691f88de567d2b1610556b21417cb5c621e5262) contains 15. All declared sizes/SHA256 values were verified. Source manifest f730c63cb83258375976a113fcc1d377c0199b9dbe03a9bb0d8be8a00420034e binds four raw B sources at head 6d3d29f16e20f1521a3ff17239ce2830bec903c3; their SHA256 and Git blob SHA1 values match.

The input provenance manifest contains 91 unique supplied/referenced files, snapshotted without normalization under controlled .local/frozen. It includes 21 backend/config files, three model-weight files, six exact PNG inputs, two retained originals, both failure/result sets, correction and task. All input/source files remain unchanged at closure. Raw textbook text, images and model bytes remain controlled local files; public review outputs contain metadata and hashes.

The runtime record identifies dedicated Python 3.12.10, RapidOCR-ONNXRuntime 1.4.4, ONNXRuntime 1.25.1 and the bundled det/cls/rec weights. Declared backend/config and weight bytes independently match their manifest. Package versions/interpreter/native dependencies are fixed runtime-record provenance, not a separately rebuilt or fully hashed binary environment. No backend module, model constructor or product entry was imported by this reviewer.

## Actual fixed local-model evidence

| Layer | Observed fixed evidence |
| --- | --- |
| Original startup | One held helper process, exit 1; local socket.gethostname audit rejection during import; 0 completed RapidOCR construction, 0 engine inputs, 0 recorded ORT runs |
| Startup r1 | New claim/run ID; one held process, exit 1; only local hostname event classification relaxed; original claim/failure retained |
| Engine | One completed cached engine construction, six distinct input calls, one pass per input, no retry; all six raw engine calls returned |
| ORT | 22 recorded InferenceSession.run entries on the three held sessions: detector 6, classifier 8, recognizer 8; per-input totals 3/5/3/5/5/1 |
| Providers | CPUExecutionProvider only on all three initialized sessions |
| Raw B atom counts | 3/4/4/4/4/0; sixth engine result is [null,null], followed by EMPTY_OCR_RESULT_NO_RETRY and FAILED_HOLD |
| Successors | No later input existed after input six; successors_not_run is an empty list, not a successful-answer claim |

The selected existing function is raw tools/route_a_layout.py::ocr_atoms (lines 469-487), using cached get_ocr_engine (461-466). The recording adapter passes each crop's decoded pixels/BGR conversion, not approved stem/options/answer content. The standard backend's detector/classifier/recognizer preprocessing and batch calls explain why engine and ORT counts differ; no additional OCR pass or inferred retry is counted.

The runner source enforces immutable claim, per-asset uniqueness, six-input cap and no retries; records exact engine-return/polygon/text/score data; and profiles the known Python ONNX session.run code with three held session identities. The 22 count is a session-run entry count supported by completed raw engine returns, not a count of native kernels or independent OS tracing. The selected backend reads bundled local weights/config and verifies missing files rather than downloading them. Fixed audit/result records show no blocked network events, platform/cloud/paid model calls or browser/profile/service creation. This is the bounded code/log layer, not a system-wide network audit.

Independent stdlib data checks reconstructed all B atoms from raw polygons using the declared threshold, rounding, original offset and y/x ordering. Every derived atom file and candidate raw record agrees. All six PNGs were decoded independently with stdlib PNG filters; RGB pixel hashes and the exact BGR input hashes match the recorded calls. Original coordinates are applied exactly once; corrected fragments retain the original bboxes, without a second offset. Coordinator-provided exact JPEG-to-crop pixel equality is retained as fixed evidence; this reviewer additionally checked PNG/call pixels, hashes and visible source relation.

## Independent visual observations and corrected-content decision

Both complete retained originals (viewer 14 and 173) and all six exact input crops were viewed. Section 2, the same section title, basic-question category and printed question number 1 jointly identify the source and matching answer block. The answer page contains multiple other sections and repeated question numbers; the accepted pairing uses its section/category/number context, not number alone or a mathematical solution. Viewer page identifiers are distinct from printed-page labels; no save-page mapping is inferred.

- Stem: the two first-line atoms must be grouped left to right before the second line. The disclosed 1-based raw index order 2/1/3 matches the crop. Printed number is retained as identity metadata, separated from the body. Visible middle dot and empty answer parentheses are restored; bracket/comma typography normalization does not change content.
- Four options: labels and numeric values agree with the source pixels. Left-to-right raw index orders 1/4/2/3, 1/2/3/4, 1/2/4/3 and 3/4/1/2 match the source and explicit corrections. Commas and label/value separation are visibly supported.
- Answer: the sixth raw OCR result is empty. The corrected answer matches the visible source entry under the matching section/category/printed number. It is explicitly visual transcription after empty OCR, not model output, automated pairing or human-user approval.
- Structure: exactly one ordinary single-choice, one stem, four ordered options and one answer, six proposed Q/W/W/W/W/A roles, with separate question-page and answer-page provenance. These source-content roles do not independently adopt a platform policy.

The original raw candidate SHA256 6452f279a70151721115cd1f8bef1d4995a0e296ad10239694fc23bf9acf322d and FAILED_HOLD status are unchanged. The accepted corrected candidate is separately hash-bound; no correction was silently written into raw OCR records. Manual pixel selection, grouping/punctuation repair and answer association remain disclosed. Autonomous question discovery, complete automatic recognition/pairing, other question types, formula work and whole-chapter completion are unproved and were not added as gates for this one content review.

## Release and remaining authority

Frozen supervisor records bind held PIDs 42536 and 53060 to exit 1, no timeout and consumed Popen streams. Startup-r1 release confirmation edf35f9285d0d16e1ce3c42e7000c4a4343525ca5bf58be271ead8165a547841 hash-links its runner release and supervisor result; backend reference clearing is followed by the recorded held-process exit. Acceptance covers those exact owned helper exits only, not unrelated processes. This reviewer acquired no browser/context/service/model runtime and retained no helper.

One reviewer metadata failure was preserved: intake.py omitted the source raw/ path layer and stopped after verifying the 36 result and 15 failure members. New complete_intake.py corrected only that evidence path and byte-checked existing snapshots; no inference or product test was repeated. The original helper and failure record remain in the output manifest.

Reviewer model/backend inference, old suites, browser/profile/config/credentials/network, upload/save and live activation all remain zero. The six actual OCR input calls are spent; no automatic replay authority is created. Earlier readonly live budgets and wire REWORK remain unchanged. Author-owned native conversion, current schema/policy/save-page/old-data preservation/owner integration and the exact authorized live plan remain outstanding. write_eligible=false, production_ready=false, actual_save=NOT_RUN, actual_independent_platform_readback=NOT_RUN. Continue in this same formal chat for the frozen wire revision and later separately authorized real reopen.
