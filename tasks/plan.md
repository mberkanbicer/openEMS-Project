# Plan: Rust Migration of openEMS-Project

## Overview

Audit the pinned openEMS-Project stack, establish original scientific and
compatibility baselines, then migrate each component to Rust in dependency
order. Preserve the existing implementations until their replacements pass
differential, integration, and workflow validation. The repository-level
migration records live in `docs/migration/`; this task list tracks execution.

## Constraints and decisions

- The full source/function audit and original behavior baseline are mandatory
  gates before Rust implementation. No porting begins in the audit phase.
- Do not choose crates, rewrite algorithms, or relax numerical tolerances
  before the relevant behavior and dependencies have been verified.
- Respect the separate repositories, licenses, instructions, and commit rules
  of the seven submodules. Never bump a root pointer to an unpushed change.
- Keep platform, Python/Cython, Matlab/Octave, GUI, file-format, and packaging
  surfaces in scope; do not call a port complete while one is unaccounted for.
- `CLAUDE.md` is not applicable to the current tool environment. Root
  `AGENTS.md` and the migration records remain authoritative.

## Task list

Task criteria and verification are in `todo.md`; dependency order is tracked
there and in the session task database.

### Phase 1: Audit

1. Initial repository/submodule inventory and tracking records — **done**
2. fparser source and behavior audit — **source audit done; optional validation gaps remain**
3. CSXCAD native model, API, XML, and test audit — **done; runtime gaps recorded**
4. CSXCAD Python/Cython and Matlab/Octave API audit — **done; runtime gaps recorded**
5. openEMS FDTD solver and physics-extension audit — **done; simulation gaps recorded**
6. openEMS processing, I/O, NF2FF, SAR, and numerical-tools audit — **done; runtime gaps recorded**
7. openEMS Python/Cython and Matlab/Octave interface audit — **done; runtime gaps recorded**
8. QCSXCAD and AppCSXCAD GUI workflow audit — **done; GUI runtime gaps recorded**
9. hyp2mat parser and conversion workflow audit — **done; runtime gaps recorded**
10. CTB function and numerical behavior audit — **done; exhaustive edge coverage remains**
11. Root orchestration, CI, packaging, and platform-coverage audit — **done; platform runs remain**
12. Consolidate source/function coverage, defects, interfaces, and migration
    dependencies — **done**

### Checkpoint: Audit complete

- Every required source area, interface, format, build option, and platform
  path is accounted for in the matrix.
- Findings are evidence-backed; TODO markers are not treated as defects without
  review.

### Phase 2: Reference and design gates

13. Build and validate the original stack; capture reproducible scientific,
    compatibility, and performance baselines
14. Finalize Rust architecture, dependency/FFI decisions, component mapping,
    acceptance criteria, risks, and migration order
15. Human review and approval of the complete audit, baselines, and Rust plan

### Checkpoint: Migration authorization

- No code port starts until Tasks 12–15 are complete and approved.

### Phase 3: Rust implementation

16. Port fparser and verify expression semantics
17. Port CSXCAD model, geometry, and XML compatibility
18. Port openEMS core solver and physics extensions
19. Port openEMS processing, file output, NF2FF, SAR, and tools
20. Port Python/Cython and Matlab/Octave interfaces
21. Port QCSXCAD and AppCSXCAD user workflows
22. Port hyp2mat and CTB workflows
23. Replace root build, packaging, and cross-component orchestration

### Checkpoint: Full-stack acceptance

- Run differential, unit, integration, scientific, compatibility, end-to-end,
  platform, and performance validation.
- Retain legacy implementations until acceptance is met; document any
  unresolved gaps and do not claim full migration.

## Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Missing or implicit numerical behavior | Incorrect simulation results | Capture original references and intermediate values before porting |
| Native dependencies lack equivalent Rust interfaces | Incomplete Rust-native result or major integration changes | Audit Qt, VTK, HDF5, TinyXML/XML, and Python integration before design approval |
| Public XML/API compatibility is broken | Existing projects and scripts stop working | Treat formats and scripting APIs as contracts; add round-trip and compatibility tests |
| Independent submodule ownership is violated | Unreviewable or unlandable changes | Make and land submodule changes in their own repositories before pointer bumps |
| Platform/toolchain differences cause regressions | Build or workflow failures | Preserve the CI/platform matrix and verify builds on supported targets |
| Task scope exceeds one implementation unit | Incomplete reviews and hidden omissions | Expand migration tasks from the completed source/function matrix into focused units |

## Open questions

- Which environments and dependencies are available for original baseline
  builds and GUI tests?
- What case-specific numerical tolerances are justified by original repeatability
  and analytical references?
- Which native dependencies can be replaced safely, and which require documented
  FFI or retained native runtimes?
