# Extending Release Workflow for Cross-Platform Wheels

## Current State

### Build Matrix

```yaml
strategy:
  matrix:
    python-version: ['3.11.15', '3.12.13', '3.13.14', '3.14.6']
    os: [ubuntu-latest, windows-latest, macos-latest]
```

The release workflow builds wheels for a limited set of platforms: ubuntu/windows/macos with x86_64 architecture only.

### Build System

- **Build Backend**: pdm-backend with custom Cython build hook (`pdm_build.py`)
- **Cython Extensions**: `deluxe._types` compiled from `src/deluxe/_types.pyx`
- **Build Command**: `uv build --all-packages --no-python-downloads`
- **Wheel Type**: Platform-specific (non-pure Python) due to compiled C extensions

### Limitations

1. **Linux**: Only glibc-based distributions (Ubuntu); no musl (Alpine Linux) support
2. **macOS**: Only x86_64 architecture; no ARM64 (Apple Silicon M-series) support
3. **Linux ARM**: No aarch64 support
4. **Windows ARM64**: No support
5. **Wheel Tagging**: No proper `manylinux` or platform-specific wheel tags

---

## Recommended Approach: cibuildwheel

**cibuildwheel** is the industry-standard tool for building Python wheels across multiple platforms. It handles:

- Cross-compilation and wheel building
- Proper wheel tagging (`manylinux`, `musllinux`, platform tags)
- QEMU emulation for cross-architecture builds
- Docker-based isolation for Linux builds

### Benefits

- Automatically handles musl vs glibc for Linux
- Supports macOS ARM natively and via cross-compilation
- Handles Linux ARM via QEMU emulation
- Proper PEP 600 (`manylinux_2_17+`) and PEP 599 (`musllinux_1_1+`) compliance
- Well-maintained and widely used by the Python ecosystem

---

## Implementation Options

### Option 1: Full cibuildwheel Migration (Recommended)

Replace the custom build logic with `cibuildwheel` for all wheel building.

#### Changes Required

1. Add `cibuildwheel` configuration to `pyproject.toml`
2. Replace the `build` job with `cibuildwheel` action
3. Configure platform-specific builds

#### Configuration Example

Add to `pyproject.toml`:

```toml
[tool.cibuildwheel]
build = "cp311-* cp312-* cp313-* cp314-*"
skip = "*-musllinux_i686"  # Optional: skip 32-bit musl

[tool.cibuildwheel.linux]
archs = "x86_64 i686 aarch64"
before-build = "pip install cython"

[tool.cibuildwheel.macos]
archs = "x86_64 arm64"
before-build = "pip install cython"

[tool.cibuildwheel.windows]
archs = "AMD64 x86 ARM64"
before-build = "pip install cython"
```

#### GitHub Actions Workflow

Replace the `build` job in `.github/workflows/release.yml`:

```yaml
build:
  name: Build wheels
  needs: [bump]
  runs-on: ${{ matrix.os }}
  strategy:
    matrix:
      include:
        - os: ubuntu-latest
          arch: x86_64
        - os: ubuntu-latest
          arch: aarch64
        - os: macos-latest
          arch: x86_64
        - os: macos-latest
          arch: arm64
        - os: windows-latest
          arch: AMD64
        - os: windows-latest
          arch: ARM64

  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - uses: pypa/cibuildwheel@v2.22
      env:
        CIBW_ARCHS: ${{ matrix.arch }}
        CIBW_BUILD: "cp311-* cp312-* cp313-* cp314-*"

    - uses: actions/upload-artifact@v4
      with:
        name: wheels-${{ matrix.os }}-${{ matrix.arch }}
        path: ./wheelhouse/*.whl
```

#### Trade-offs

| Aspect | Assessment |
|--------|------------|
| Complexity | Medium (requires config migration) |
| Performance | Excellent (parallel builds, caching) |
| Maintainability | High (community-standard tool) |
| Wheel Quality | Excellent (proper tags, tested) |

#### Potential Issues

- Build hook integration: May need to adjust `pdm_build.py` to work with cibuildwheel's environment
- Docker requirement for Linux builds (uses `manylinux` containers)
- Cross-compilation for ARM may require QEMU setup

---

### Option 2: Extended Matrix with Explicit Runner Selection

Keep the current build approach but expand the matrix with specific runners for each platform/architecture.

#### Matrix Example

```yaml
strategy:
  fail-fast: false
  matrix:
    include:
      # Linux glibc x86_64
      - os: ubuntu-latest
        python: '3.11.15'
        arch: x86_64
        manylinux: manylinux_2_17

      # Linux glibc aarch64
      - os: ubuntu-latest
        python: '3.11.15'
        arch: aarch64
        manylinux: manylinux_2_17
        qemu: true

      # Linux musl x86_64
      - os: ubuntu-latest
        python: '3.11.15'
        arch: x86_64
        musl: true

      # macOS x86_64
      - os: macos-13  # Intel runner
        python: '3.11.15'
        arch: x86_64

      # macOS ARM64
      - os: macos-latest  # Apple Silicon runner
        python: '3.11.15'
        arch: arm64

      # Windows AMD64
      - os: windows-latest
        python: '3.11.15'
        arch: AMD64

      # Windows ARM64
      - os: windows-latest
        python: '3.11.15'
        arch: ARM64
```

#### Trade-offs

| Aspect | Assessment |
|--------|------------|
| Complexity | High (manual configuration) |
| Performance | Medium (depends on runner availability) |
| Maintainability | Low (many edge cases to handle) |
| Wheel Quality | Variable (requires manual tagging) |

#### Potential Issues

- GitHub-hosted ARM runners for Linux may require paid plans or self-hosted runners
- musl builds require Alpine containers or cross-compilation
- Wheel tagging becomes manual and error-prone
- QEMU emulation can be slow

---

### Option 3: Hybrid Approach (Local + CI)

Build some platforms locally using Docker/QEMU and push to CI for final assembly and publishing.

#### Changes Required

1. Create Docker images for musl and cross-architecture builds
2. Use CI for testing and publishing
3. Local builds for complex platforms

#### Docker Example (Alpine musl)

```dockerfile
FROM python:3.11-alpine
RUN apk add --no-cache gcc musl-dev cython
COPY . /build
WORKDIR /build
RUN pip wheel --no-deps --wheel-dir /wheelhouse .
```

#### Trade-offs

| Aspect | Assessment |
|--------|------------|
| Complexity | Very High (Docker management) |
| Performance | Variable |
| Maintainability | Low (multiple build systems) |
| Wheel Quality | High (controlled environment) |

#### Potential Issues

- Requires Docker infrastructure management
- CI/CD pipeline becomes more complex
- Harder to debug build failures

---

## Platform-Specific Considerations

### Linux musl (Alpine Linux)

- **Challenge**: musl has different C library; wheels are not compatible with glibc
- **Solution**: Use `cibuildwheel` with `musllinux` images or Alpine Docker
- **Wheel Tag**: `manylinux_2_17_x86_64` vs `musllinux_1_1_x86_64`

### macOS ARM (Apple Silicon M-series)

- **Challenge**: Cross-compilation or native ARM runners
- **Solution**: Use `macos-latest` (ARM64) or `macos-13` (Intel) runners
- **Wheel Tag**: `macosx_11_0_arm64` or `macosx_10_9_x86_64`

### Linux ARM (aarch64)

- **Challenge**: GitHub Actions doesn't have native ARM Linux runners by default
- **Solution**: Use QEMU emulation or self-hosted ARM runners
- **Wheel Tag**: `manylinux_2_17_aarch64`

### Windows ARM64

- **Challenge**: Limited runner support
- **Solution**: Use self-hosted Windows ARM runners
- **Wheel Tag**: `win_arm64`

---

## Recommended Implementation Plan

### Phase 1: Immediate (1-2 days)

1. **Adopt cibuildwheel** (Option 1)
   - Add `[tool.cibuildwheel]` configuration to `pyproject.toml`
   - Update `release.yml` to use `pypa/cibuildwheel@v2.22` action
   - Start with Linux x86_64 and macOS ARM builds

### Phase 2: Short-term (3-5 days)

2. **Expand platform coverage**
   - Add Linux aarch64 via QEMU
   - Add Windows ARM64 support
   - Add musl builds for Alpine compatibility

### Phase 3: Long-term (1 week+)

3. **Optimize and test**
   - Add wheel testing (install and import on each platform)
   - Implement caching for faster builds
   - Add compatibility testing with different glibc/musl versions

---

## Action Items

| Priority | Task | Time Estimate |
|----------|------|---------------|
| High | Review cibuildwheel documentation | 2 hours |
| High | Create pyproject.toml config for cibuildwheel | 1 hour |
| High | Update release.yml build job | 2 hours |
| Medium | Test Linux x86_64 and macOS ARM builds | 3 hours |
| Medium | Add Linux aarch64 support | 2 hours |
| Medium | Add musl support for Alpine | 2 hours |
| Low | Add Windows ARM64 support | 2 hours |
| Low | Implement wheel testing | 3 hours |

---

## References

- [cibuildwheel documentation](https://cibuildwheel.pypa.io/)
- [PEP 600 -manylinux](https://peps.python.org/pep-0600/)
- [PEP 599 -musllinux](https://peps.python.org/pep-0599/)
- [GitHub Actions - pypa/cibuildwheel](https://github.com/pypa/cibuildwheel)
