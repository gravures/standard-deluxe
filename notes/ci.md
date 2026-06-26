# CI/CD - Github Worklows

## Cython Build

### 1. GitHub Actions Runners

All three major runner types include C/C++ compilers by default.

### 2. Available Compilers/Versions

#### ubuntu-latest (Ubuntu 24.04)

- GCC: 12.4.0, 13.3.0, 14.2.0
- Clang: 16.0.6, 17.0.6, 18.1.3
- G++: 13.2.0 (via apt), plus GNU C++ 12/13/14 (same as GCC versions)
- Also preinstalled: make, cmake, pkg-config, libssl-dev, libsqlite3-dev, libyaml-dev, swig

#### Windows-Latest (Windows Server 2025)

- Visual Studio Enterprise 2025 (MSVC) with VC++ components
- GCC 15.2.0 (via MSYS2 at C:\msys64, not on PATH by default)
- LLVM/Clang 20.1.8
- Also preinstalled: CMake, Ninja, vcpkg

#### macos-latest (macOS 15, Apple Silicon)

- Xcode Command Line Tools 16.4.0 (provides clang/clang++ via Apple's toolchain)
- Clang/LLVM 17.0.0 (system), plus 18.1.8 via Homebrew
- GCC 13, 14, 15 via Homebrew (available as gcc-13, gcc-14, gcc-15)
- Also preinstalled: CMake, Ninja, pkg-config

## 3. When Would Explicit Actions Be Needed?

You might need an explicit action for:

- Windows MSVC activation: If you specifically need the MSVC compiler (not MinGW/GCC), you may need ilammy/msvc-dev-cmd or microsoft/setup-msbuild to put MSVC tools on PATH. However, for Cython's use case, the GCC from MSYS2 or the system Clang/LLVM often suffice.
- Specific GCC version: If you need a version newer than what's preinstalled (e.g., GCC 15 on Ubuntu).
- Linux ARM64 cross-compilation: Not available by default on x64 runners.

## 4. For Cython Builds, Is the Default Toolchain Sufficient?

The default toolchain is sufficient. Cython generates .c files from .pyx files, and then pip/setuptools/build compiles them using the system C compiler:

- Ubuntu: gcc (the default cc is GCC) — works out of the box
- macOS: clang from Xcode Command Line Tools — works out of the box
- Windows: cl.exe from MSVC is used by distutils/setuptools when building Python extensions. This is preinstalled and functional on windows-latest. No ilammy/msvc-dev-cmd step is needed for standard Python extension builds because pip and setuptools already know how to locate MSVC on Windows.
Bottom line: For a Cython project building standard C extensions via pip install / python -m build, no additional toolchain installation step is needed on any of the three runner types. The preinstalled compilers are sufficient and are the ones pip/setuptools will find automatically.
