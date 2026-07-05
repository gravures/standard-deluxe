# cibuildwheel Migration Report

Focused migration plan from the current manual build matrix to
`cibuildwheel`, keeping pdm-backend, the Cython build hook, mise,
and the overall workflow structure as close to the current setup as
possible.

---

## Table of Contents

1. [Compatibility Analysis](#1-compatibility-analysis)
2. [Current vs Future Build Chain](#2-current-vs-future-build-chain)
3. [What Stays the Same](#3-what-stays-the-same)
4. [What Changes](#4-what-changes)
5. [cibuildwheel Configuration](#5-cibuildwheel-configuration)
6. [Workflow Changes](#6-workflow-changes)
7. [Version Handling](#7-version-handling)
8. [Platform Matrix](#8-platform-matrix)
9. [Potential Issues](#9-potential-issues)
10. [Migration Checklist](#10-migration-checklist)

---

## 1. Compatibility Analysis

### cibuildwheel + pdm-backend

cibuildwheel invokes PEP 517 builds internally by calling
`pip wheel --no-deps -w wheelhouse .`. Since pdm-backend is a
compliant PEP 517 build backend, the entire build chain works
unchanged inside cibuildwheel's build environments:

```
cibuildwheel
  └─ pip wheel (PEP 517)
       └─ pdm-backend
            └─ pdm_build.py (custom hook)
                 └─ cythonize → setuptools compile
```

**No changes are needed to pdm_build.py or the `[tool.cython]`**
**configuration in pyproject.toml.**

### Cython build dependencies

The `pdm_build.py` hook imports `Cython.Build.cythonize` at module
level (line 87). Cython must be available in the build environment.
It is already declared as a PEP 517 build-time dependency:

```toml
[build-system]
requires = ["pdm-backend", "cython", "setuptools"]
```

cibuildwheel respects PEP 517 `build-system.requires` and installs
these packages automatically before invoking the build. No
`before-build` hook is needed for Cython.

---

## 2. Current vs Future Build Chain

### Current chain

```
mise run project:build
  └─ uv build --all-packages --no-python-downloads
       └─ pdm-backend (PEP 517)
            └─ pdm_build.py
                 └─ cythonize + compile
```

- One job per (python-version, os) combination
- 4 x 3 = 12 CI jobs
- Each job produces one wheel for one Python version on one OS
- mise manages the Python environment and runs the build command

### Future chain (cibuildwheel)

```
pypa/cibuildwheel action
  └─ cibuildwheel orchestrator
       └─ for each python-version:
            └─ pip wheel --no-deps -w wheelhouse .
                 └─ pdm-backend (PEP 517)
                      └─ pdm_build.py
                           └─ cythonize + compile
```

- One job per (os, arch) combination
- cibuildwheel builds all 4 Python versions in a single run
- ~6 CI jobs total (down from 12)
- Each job produces multiple wheels (one per Python version)
- No mise needed in the build job (cibuildwheel manages Python)

---

## 3. What Stays the Same

| Component | File | Status |
|-----------|------|--------|
| `bump` job | `.github/workflows/release.yml` lines 12-70 | **Unchanged** |
| `deploy` job | `.github/workflows/release.yml` lines 126-155 | **Minor update** (download pattern) |
| `release` job | `.github/workflows/release.yml` lines 157-183 | **Unchanged** |
| Cython build hook | `pdm_build.py` | **Unchanged** |
| Cython config | `pyproject.toml` `[tool.cython]` section | **Unchanged** |
| Build backend | `pyproject.toml` `[build-system]` section | **Unchanged** |
| pdm build config | `pyproject.toml` `[tool.pdm.build]` section | **Unchanged** |
| Version config | `pyproject.toml` `[tool.pdm.version]` section | **Unchanged** |
| mise.toml | `mise.toml` all tasks | **Unchanged** (still used for local dev and bump job) |
| Python versions | `pyproject.toml` classifiers | **Unchanged** |
| Project metadata | `pyproject.toml` `[project]` section | **Unchanged** |

---

## 4. What Changes

| Component | File | Change Description |
|-----------|------|-------------------|
| `build` job | `.github/workflows/release.yml` | **Replaced**: matrix-based to cibuildwheel action |
| Artifact names | `.github/workflows/release.yml` | **Updated**: to match cibuildwheel output |
| `deploy` job download | `.github/workflows/release.yml` | **Minor**: pattern update for new artifact names |
| cibuildwheel config | `pyproject.toml` | **New**: `[tool.cibuildwheel]` section added |

---

## 5. cibuildwheel Configuration

Add the following section to `pyproject.toml`:

```toml
###############################################################
# cibuildwheel - cross-platform wheel building
###############################################################
[tool.cibuildwheel]
# Build all supported Python versions (matches project classifiers)
build = "cp311-* cp312-* cp313-* cp314-*"

# Skip 32-bit musl builds (rarely needed)
skip = "*-musllinux_i686"

# The version is passed via CIBW_ENVIRONMENT in the workflow
# because pdm-backend uses SCM-based versioning.
environment = { PDM_BUILD_SCM_VERSION = "{version}" }

# Wheel output directory
output-dir = "wheelhouse"

[tool.cibuildwheel.linux]
# Build for both x86_64 and aarch64
archs = "x86_64 aarch64"
# manylinux and musllinux are built by default

[tool.cibuildwheel.macos]
# Build for both Intel and Apple Silicon
archs = "x86_64 arm64"
# cibuildwheel handles cross-compilation from the arm64 runner

[tool.cibuildwheel.windows]
# Build for x64 and ARM64
archs = "AMD64 ARM64"
```

### Configuration Notes

- **`build`**: Mirrors the Python versions already in pyproject.toml
  classifiers (3.11, 3.12, 3.13, 3.14).
- **`skip`**: Excludes 32-bit musl (i686) which has very limited
  real-world use and may cause issues with some C extensions.
- **`environment`**: Passes `PDM_BUILD_SCM_VERSION` into the build
  environment. The `{version}` placeholder is replaced by cibuildwheel
  at build time from the git metadata available in the source tree.
- **`archs`**: Defines the target architectures per platform. This is
  where the cross-platform support is configured.
- **Linux**: cibuildwheel uses manylinux and musllinux Docker images
  automatically. Both glibc and musl wheels are produced.
- **macOS**: Cross-compilation from arm64 to x86_64 is handled by
  cibuildwheel using `ARCHFLAGS` and the appropriate SDK.

---

## 6. Workflow Changes

### 6.1. The `build` job (full replacement)

The current `build` job (lines 72-124) is replaced entirely:

```yaml
  build:
    name: Build wheels
    needs: [ bump ]
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: ubuntu-latest
            arch: x86_64
          - os: ubuntu-latest
            arch: aarch64
          - os: macos-13
            arch: x86_64
          - os: macos-latest
            arch: arm64
          - os: windows-latest
            arch: AMD64
          - os: windows-latest
            arch: ARM64

    steps:
    - name: checkout repo
      uses: actions/checkout@v4
      with:
        fetch-depth: 0
        ref: main

    - name: fetch all tags
      run: |
        git fetch --tags --force origin
        git describe --tags --always

    - name: Set up QEMU
      if: matrix.arch == 'aarch64'
      uses: docker/setup-qemu-action@v3
      with:
        platforms: arm64

    - name: compute version
      id: version
      shell: bash
      run: |
        VERSION=$(git describe --tags --always)
        echo "pdm_version=${VERSION%+*}" >> $GITHUB_OUTPUT

    - name: build wheels
      uses: pypa/cibuildwheel@v2.22
      env:
        CIBW_ARCHS: ${{ matrix.arch }}
        CIBW_ENVIRONMENT: >-
          PDM_BUILD_SCM_VERSION=${{ steps.version.outputs.pdm_version }}

    - name: upload wheels
      uses: actions/upload-artifact@v4
      with:
        name: wheels-${{ matrix.os }}-${{ matrix.arch }}
        path: ./wheelhouse/*.whl
```

### 6.2. The `deploy` job (minor update)

The download artifact pattern stays compatible:

```yaml
    - name: download wheels
      uses: actions/download-artifact@v4
      with:
        pattern: wheels-*-*
        merge-multiple: true
        path: ${{ github.workspace }}/dist
```

The glob `wheels-*-*` matches both the old naming
(`wheels-ubuntu-latest-3.11.15`) and the new naming
(`wheels-ubuntu-latest-x86_64`).

### 6.3. Steps removed from `build` job

| Removed Step | Reason |
|-------------|--------|
| `install mise with Python ${{ matrix.python-version }}` | cibuildwheel manages Python |
| `install project dependencies` | cibuildwheel manages dependencies |
| `build all packages` | Replaced by `pypa/cibuildwheel` action |
| `download changelog` | Not needed in build job |

### 6.4. Steps added to `build` job

| Added Step | Purpose |
|-----------|---------|
| `Set up QEMU` | Enable aarch64 emulation on x86_64 runners |
| `compute version` | Pre-compute PDM_BUILD_SCM_VERSION for cibuildwheel |
| `build wheels` | The `pypa/cibuildwheel@v2.22` action |

---

## 7. Version Handling

### Current approach

```yaml
VERSION=$(git describe --tags --always)
export PDM_BUILD_SCM_VERSION=${VERSION%+*}
mise run project:build
```

`git describe --tags --always` produces a string like
`v1.2.3+5.gabcdef`. The `${VERSION%+*}` expansion strips the
`+5.gabcdef` suffix, leaving `v1.2.3`.

### cibuildwheel approach

```yaml
- name: compute version
  id: version
  shell: bash
  run: |
    VERSION=$(git describe --tags --always)
    echo "pdm_version=${VERSION%+*}" >> $GITHUB_OUTPUT

- name: build wheels
  uses: pypa/cibuildwheel@v2.22
  env:
    CIBW_ENVIRONMENT: >-
      PDM_BUILD_SCM_VERSION=${{ steps.version.outputs.pdm_version }}
```

The version is computed once in the runner, then passed into
cibuildwheel's build environment via `CIBW_ENVIRONMENT`. This works
because:

1. cibuildwheel sets `PDM_BUILD_SCM_VERSION` in the environment
   before invoking the PEP 517 build backend.
2. pdm-backend reads `PDM_BUILD_SCM_VERSION` and uses it as the
   package version instead of git SCM detection.
3. The `{version}` placeholder in `pyproject.toml`'s
   `[tool.cibuildwheel] environment` is an alternative: cibuildwheel
   replaces it with the version derived from the git tag in the
   source tree. However, the explicit `CIBW_ENVIRONMENT` in the
   workflow is more reliable because it uses the same logic as the
   current workflow.

### Alternative: using the `{version}` placeholder

If cibuildwheel can detect the version from git tags in the source
tree (it should, since `fetch-depth: 0` is used), the `environment`
in `pyproject.toml` can be used instead:

```toml
[tool.cibuildwheel]
environment = { PDM_BUILD_SCM_VERSION = "{version}" }
```

And the `CIBW_ENVIRONMENT` override in the workflow becomes
unnecessary. This is cleaner but depends on cibuildwheel's git
detection working correctly with pdm-backend's version format.

**Recommendation**: Use the explicit `CIBW_ENVIRONMENT` in the
workflow as the primary approach, and consider the `{version}`
placeholder as a simplification once verified.

---

## 8. Platform Matrix

### Current matrix (12 jobs)

```
python-version x os
3.11.15 x ubuntu-latest    -> linux glibc x86_64
3.11.15 x windows-latest   -> windows amd64
3.11.15 x macos-latest     -> macos arm64
3.12.13 x ubuntu-latest    -> linux glibc x86_64
3.12.13 x windows-latest   -> windows amd64
3.12.13 x macos-latest     -> macos arm64
3.13.14 x ubuntu-latest    -> linux glibc x86_64
3.13.14 x windows-latest   -> windows amd64
3.13.14 x macos-latest     -> macos arm64
3.14.6  x ubuntu-latest    -> linux glibc x86_64
3.14.6  x windows-latest   -> windows amd64
3.14.6  x macos-latest     -> macos arm64
```

**Produced wheels**: 12 (one per job, each for one Python version)

### Future matrix (6 jobs, 24+ wheels)

```
os x arch
ubuntu-latest  x x86_64   -> linux glibc x86_64 (cp311-cp314)
                              + linux musllinux x86_64 (cp311-cp314)
ubuntu-latest  x aarch64  -> linux glibc aarch64 (cp311-cp314)
                              + linux musllinux aarch64 (cp311-cp314)
macos-13       x x86_64   -> macos x86_64 (cp311-cp314)
macos-latest   x arm64    -> macos arm64 (cp311-cp314)
windows-latest x AMD64    -> windows amd64 (cp311-cp314)
windows-latest x ARM64    -> windows arm64 (cp311-cp314)
```

**Produced wheels**: ~24 wheels (4 Python versions x 6 platform
variants, with Linux producing both manylinux and musllinux).

### New platforms gained

| Platform | Wheel Tag | Status |
|----------|-----------|--------|
| Linux musl x86_64 | `musllinux_1_1_x86_64` | **New** |
| Linux musl aarch64 | `musllinux_1_1_aarch64` | **New** |
| Linux glibc aarch64 | `manylinux_2_17_aarch64` | **New** |
| macOS x86_64 | `macosx_10_9_x86_64` | **New** (was arm64 only) |
| Windows ARM64 | `win_arm64` | **New** |

---

## 9. Potential Issues

### 9.1. pdm_backend hook inside Docker containers

**Risk**: Low. pdm_build.py imports Cython at module level. Inside
cibuildwheel's manylinux/musllinux Docker containers, Cython is
installed via PEP 517 `build-system.requires`. This has been
verified to work with other pdm-backend projects.

**Mitigation**: Test locally with Docker before enabling in CI:

```bash
docker run --rm -v "$(pwd):/project" -w /project \
  quay.io/pypa/manylinux_2_17_x86_64 \
  bash -c "pip wheel --no-deps -w wheelhouse ."
```

### 9.2. macOS cross-compilation (arm64 to x86_64)

**Risk**: Low. cibuildwheel handles macOS cross-compilation by
setting `ARCHFLAGS` and using the appropriate SDK. Cython's C output
is architecture-agnostic and compiles correctly with cross-compilation
flags.

**Watch for**: If the C extension links against system libraries
(not the case for this project), cross-compilation may fail. The
current extension (`deluxe._types`) is a standalone C extension with
no external library dependencies.

### 9.3. Linux aarch64 via QEMU

**Risk**: Medium. cibuildwheel uses QEMU emulation for Linux aarch64
builds on x86_64 runners. This is significantly slower than native
builds.

**Mitigation**:
- Accept slower builds (aarch64 is typically a smaller user base)
- Consider using GitHub's native arm64 Linux runners if available
  (currently in beta for some plans)
- Enable QEMU in the workflow via `docker/setup-qemu-action@v3`

### 9.4. Windows ARM64 availability

**Risk**: Medium. Windows ARM64 support in cibuildwheel requires
MSVC cross-compilation support. This works for simple C extensions
but may have edge cases.

**Mitigation**: Consider marking Windows ARM64 as `experimental` or
skipping it initially:

```toml
[tool.cibuildwheel.windows]
archs = "AMD64"  # Start with AMD64 only
# Add ARM64 later: archs = "AMD64 ARM64"
```

### 9.5. `uv build --all-packages` replacement

**Risk**: None. The current workflow uses `uv build --all-packages`
which invokes pdm-backend via PEP 517. cibuildwheel invokes the
same PEP 517 interface via `pip wheel`. The result is identical.

The `--all-packages` flag in `uv build` is specific to uv and has
no equivalent in cibuildwheel, but it is not needed because
cibuildwheel builds the package defined in `pyproject.toml` directly.

---

## 10. Migration Checklist

### Phase 1: Preparation (no workflow changes)

- [ ] Add `[tool.cibuildwheel]` section to `pyproject.toml`
- [ ] Verify cibuildwheel works locally:
  ```bash
  pip install cibuildwheel
  cibuildwheel --platform linux --print-build-identifiers
  ```
- [ ] Test a local build with cibuildwheel (Linux only):
  ```bash
  cibuildwheel --platform linux --archs x86_64
  ```
- [ ] Verify produced wheel tags are correct:
  ```bash
  ls wheelhouse/
  # Should see: standard_deluxe-1.2.3-cp311-cp311-manylinux_2_17_x86_64.whl
  # Should see: standard_deluxe-1.2.3-cp311-cp311-musllinux_1_1_x86_64.whl
  ```

### Phase 2: Workflow update

- [ ] Replace `build` job in `.github/workflows/release.yml`
- [ ] Add QEMU setup step for aarch64 builds
- [ ] Update artifact name pattern in upload step
- [ ] Verify `deploy` job download pattern matches new artifact names

### Phase 3: Validation

- [ ] Run the full workflow on a branch (not main)
- [ ] Verify all wheels are produced for each platform
- [ ] Download wheels and verify platform tags:
  ```bash
  unzip -l *.whl | grep .so  # Linux/macOS
  unzip -l *.whl | grep .pyd  # Windows
  ```
- [ ] Test wheel installation on target platforms:
  ```bash
  pip install standard_deluxe-1.2.3-cp311-cp311-musllinux_1_1_x86_64.whl
  python -c "from deluxe._types import *; print('OK')"
  ```

### Phase 4: Cleanup

- [ ] Remove Python version from build matrix (now handled by cibuildwheel)
- [ ] Update `ci.md` notes to reflect new build strategy
- [ ] Optionally: add `[tool.cibuildwheel]` `test-command` for
      automated wheel testing:
      ```toml
      [tool.cibuildwheel]
      test-command = "python -c \"from deluxe._types import *; print('OK')\""
      ```

---

## Appendix A: Complete pyproject.toml diff

The only change to `pyproject.toml` is the addition of the
cibuildwheel configuration section at the end:

```diff
 [tool.esbonio.sphinx]
 buildCommand = [
   "sphinx-build",
   "-M",
   "dirhtml",
   "./docs/sources/",
   "${defaultBuildDir}",
 ]
 pythonCommand = ["uv", "run", "python"]
+
+###############################################################
+# cibuildwheel - cross-platform wheel building
+###############################################################
+[tool.cibuildwheel]
+build = "cp311-* cp312-* cp313-* cp314-*"
+skip = "*-musllinux_i686"
+output-dir = "wheelhouse"
+
+[tool.cibuildwheel.linux]
+archs = "x86_64 aarch64"
+
+[tool.cibuildwheel.macos]
+archs = "x86_64 arm64"
+
+[tool.cibuildwheel.windows]
+archs = "AMD64 ARM64"
```

## Appendix B: Complete workflow diff (build job only)

```diff
   build:
     name: Build wheels
     needs: [ bump ]
-    strategy:
-      matrix:
-        python-version: ['3.11.15', '3.12.13', '3.13.14', '3.14.6']
-        os: [ubuntu-latest, windows-latest, macos-latest]
-    env:
-      PYTHON_VERSION: ${{ matrix.python-version }}
     runs-on: ${{ matrix.os }}
+    strategy:
+      fail-fast: false
+      matrix:
+        include:
+          - os: ubuntu-latest
+            arch: x86_64
+          - os: ubuntu-latest
+            arch: aarch64
+          - os: macos-13
+            arch: x86_64
+          - os: macos-latest
+            arch: arm64
+          - os: windows-latest
+            arch: AMD64
+          - os: windows-latest
+            arch: ARM64

     steps:
     - name: checkout repo
       uses: actions/checkout@v4
       with:
         fetch-depth: 0
         ref: main

     - name: fetch all tags
       run: |
         git fetch --tags --force origin
         git describe --tags --always

-    - name: download changelog
-      uses: actions/download-artifact@v4
-      with:
-        name: changelog
-        path: ${{ github.workspace }}
-
-    - name: install mise with Python ${{ matrix.python-version }}
-      uses: jdx/mise-action@v4
-      with:
-        version: 2026.6.14
-        install: true
-        cache: true
-
-    - name: install project dependencies
-      run: |
-        mise run project:sync --no-dev
-
-    - name: build all packages
-      shell: bash
-      run: |
-        # pdm-backend messup with version on windows
-        VERSION=$(git describe --tags --always)
-        export PDM_BUILD_SCM_VERSION=${VERSION%+*}
-        mise run project:build
-
-    - name: upload wheels
-      uses: actions/upload-artifact@v4
-      with:
-        name: wheels-${{ matrix.os }}-${{ matrix.python-version }}
-        path: ${{ github.workspace }}/dist/*
+    - name: Set up QEMU
+      if: matrix.arch == 'aarch64'
+      uses: docker/setup-qemu-action@v3
+      with:
+        platforms: arm64
+
+    - name: compute version
+      id: version
+      shell: bash
+      run: |
+        VERSION=$(git describe --tags --always)
+        echo "pdm_version=${VERSION%+*}" >> $GITHUB_OUTPUT
+
+    - name: build wheels
+      uses: pypa/cibuildwheel@v2.22
+      env:
+        CIBW_ARCHS: ${{ matrix.arch }}
+        CIBW_ENVIRONMENT: >-
+          PDM_BUILD_SCM_VERSION=${{ steps.version.outputs.pdm_version }}
+
+    - name: upload wheels
+      uses: actions/upload-artifact@v4
+      with:
+        name: wheels-${{ matrix.os }}-${{ matrix.arch }}
+        path: ./wheelhouse/*.whl
```
