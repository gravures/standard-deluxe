# Changelog
All notable changes to this project will be documented in this file. See [conventional commits](https://www.conventionalcommits.org/) for commit guidelines.

- - -
##  Changelog for release [v0.15.1]
    
    https://github.com/gravures/standard-deluxe/compare/ed7edc44919ade2b47f4701eb25462f6eeffd9fb..v0.15.1
    2026-07-16
  
### Documentation

  - **(deluxe)** adds os badge to readme - ([1c8ce8a](https://github.com/gravures/standard-deluxe/commit/1c8ce8ac87482c008f8bd6a7e72aaa6f8e60ab98)) - [@gravures](https://github.com/gravures)


### Fixes

  - **(cli)** fix cli instance run with --help or --version flags exiting with a positive return code insteed of 0 - ([0ed6b51](https://github.com/gravures/standard-deluxe/commit/0ed6b51bab71eefbd176cf7a6dd85bdc1bff7104)) - [@gravures](https://github.com/gravures)

  - **(prettyPaser)** remove double usage: prefix in subparser help - ([c834eb1](https://github.com/gravures/standard-deluxe/commit/c834eb124d88152fbd9951f5328b2792139bd2d0)) - [@gravures](https://github.com/gravures)



- - -

##  Changelog for release [v0.14.0]
    
    https://github.com/gravures/standard-deluxe/compare/7fc410feb276475f4b6bff24f52246a3924e2ed1..v0.14.0
    2026-07-06
  
### Bug Fixes

  - **(knownfolder)** fix knownfolder HRESULT type and improve test robustness - ([e74315a](https://github.com/gravures/standard-deluxe/commit/e74315aff32a2aa09e3edfd6a423eddddd23372c)) - [@gravures](https://github.com/gravures)
  - **(knownfolder)** Changed wintypes.HRESULT → ctypes.HRESULT (line 89). - ([1cf7edc](https://github.com/gravures/standard-deluxe/commit/1cf7edcd763defefc649336a7fad5cb6b2d4a6d5)) - [@gravures](https://github.com/gravures)


### Features

  - **(knownfolder)** add knownfolder module - ([7fc410f](https://github.com/gravures/standard-deluxe/commit/7fc410feb276475f4b6bff24f52246a3924e2ed1)) - [@gravures](https://github.com/gravures)



- - -

##  Changelog for release [v0.13.0]
    
    https://github.com/gravures/standard-deluxe/compare/798e5ab47c124d4600b73218faa550bbe5ddf045..v0.13.0
    2026-07-05
  
### Bug Fixes

  - **(ansi)** reduce sgr parameters list - ([99025b6](https://github.com/gravures/standard-deluxe/commit/99025b654e90e1dfc79f4b3f9c53dae88f7bd4f4)) - [@gravures](https://github.com/gravures)

  - **(argparser)** add support for python 3.14 color feature - ([57143d0](https://github.com/gravures/standard-deluxe/commit/57143d03d3e0aacbe999ce3b8ded42c21312a4b1)) - [@gravures](https://github.com/gravures)

  - **(cli)** resolve CliError.code winerror fallback on Windows - ([5d2f123](https://github.com/gravures/standard-deluxe/commit/5d2f12303528dc6e2dcc0a4506cbd55ada680f59)) - [@gravures](https://github.com/gravures)
  - **(cli)** fix subcommand handling, add command decorator, upgrade docstrings - ([dd0d2e1](https://github.com/gravures/standard-deluxe/commit/dd0d2e1eeea015659267d6e09279b865fa450c6a)) - [@gravures](https://github.com/gravures)

  - **(console)** fix argparse compatibility with Python 3.13.14+ backported method - ([54a5b62](https://github.com/gravures/standard-deluxe/commit/54a5b6255d1b18ec745e925559b3965068187db0)) - [@gravures](https://github.com/gravures)
  - **(console)** repair ANSI escape handling in text wrapper and strip_escFix two bugs in ANSI text processing:- _STRIP_ESC regex used (\\.\*) instead of proper alternation, breaking  CSI sequence matching and completely failing on OSC sequences- _handle_long_word used len() instead of visible length, causing  escape sequences to be split across line breaksAdd _visible_break_pos() to AnsiTextWrapper for ANSI-aware breaking,override _handle_long_word to measure visible width, and clean updead code and commented-out blocks. - ([acfcb3b](https://github.com/gravures/standard-deluxe/commit/acfcb3b259a51c433fc6185ef34b8e7673b5862f)) - [@gravures](https://github.com/gravures)
  - **(console)** update _all_ - ([756a0b5](https://github.com/gravures/standard-deluxe/commit/756a0b5b89130c680722e5ab0c020471bf5f4f9d)) - [@gravures](https://github.com/gravures)
  - **(console)** minor type hints fixes - ([b9c4a4c](https://github.com/gravures/standard-deluxe/commit/b9c4a4cd4caae184c16a8bad5671170f6c595a47)) - [@gravures](https://github.com/gravures)

  - **AnsiHelpFormatter - ([6e38c07](https://github.com/gravures/standard-deluxe/commit/6e38c070c1546c634b1ac5b657a0a97179c7c726)) - [@gravures](https://github.com/gravures)
  - **ansi.strip_esc()  always returned empty string - ([78bd93a](https://github.com/gravures/standard-deluxe/commit/78bd93ab1bac5632047290ea019da2980b7c2a17)) - [@gravures](https://github.com/gravures)
  - **AnsiTextWrapper class - ([d320e9d](https://github.com/gravures/standard-deluxe/commit/d320e9d7bcbbd0bb1faba631ee6e7abb152c7aee)) - [@gravures](https://github.com/gravures)
  - **malfomatted string in ColorsHelpFormatter._ansi_metavar_parts() - ([989c164](https://github.com/gravures/standard-deluxe/commit/989c164623df6ade1d4a4038160c2f22548a0fe4)) - [@gravures](https://github.com/gravures)
  - **ColorsHelpFormatter _format_action_invocation wasn't be called - ([3fd27cb](https://github.com/gravures/standard-deluxe/commit/3fd27cb071728f51e94df25e230ba09113850532)) - [@gravures](https://github.com/gravures)
  - **fix __all_ ansi module variable named __ALL__ - ([7d0fb56](https://github.com/gravures/standard-deluxe/commit/7d0fb5678846f60696f0741835702b66c6f12052)) - [@gravures](https://github.com/gravures)

### Documentation

  - **(argparser)** rewrite module documentation - ([6758c9f](https://github.com/gravures/standard-deluxe/commit/6758c9f6f25d4897dc9526775f8ae594dcedaa93)) - [@gravures](https://github.com/gravures)


### Features

  - **adds markup for default arguments for AnsiHelpFromatter - ([87b52c6](https://github.com/gravures/standard-deluxe/commit/87b52c67b082c56e02d65bedb7086929b6975d1f)) - [@gravures](https://github.com/gravures)
  - **Makes PrettyHelpFormatter inherit from ColorsHelpFormatter - ([0bee2c5](https://github.com/gravures/standard-deluxe/commit/0bee2c51835b0c9d74ea8996ebe69794c2f340fc)) - [@gravures](https://github.com/gravures)
  - **adss ColorHelpFormatter to argparser module - ([23a3304](https://github.com/gravures/standard-deluxe/commit/23a330483e4603bea93e060b922432d12e20d77b)) - [@gravures](https://github.com/gravures)
  - **adds cli module to console package - ([c71f57f](https://github.com/gravures/standard-deluxe/commit/c71f57ff6a4642f64d156f34f7e09f56f75db235)) - [@gravures](https://github.com/gravures)
  - **Adds wrap.AnsiTextWrapper class to console package - ([1dc7261](https://github.com/gravures/standard-deluxe/commit/1dc7261c8f58e150152a6843c054fbff1306e3ea)) - [@gravures](https://github.com/gravures)
  - **adds new functions to console.ansi module - ([3904d8a](https://github.com/gravures/standard-deluxe/commit/3904d8a2899e128b9c347ba1210d43857b25a3ea)) - [@gravures](https://github.com/gravures)
  - **adds console.argpaser module - ([dca0a2d](https://github.com/gravures/standard-deluxe/commit/dca0a2d08c0b8d53950d81c2fb186a49710eba85)) - [@gravures](https://github.com/gravures)
  - **adds new monorepo console package - ([798e5ab](https://github.com/gravures/standard-deluxe/commit/798e5ab47c124d4600b73218faa550bbe5ddf045)) - [@gravures](https://github.com/gravures)

### Refactoring

  - **(ansi)** [**breaking**] rename a few symbols for consistency, also complete docstrings - ([38d5d39](https://github.com/gravures/standard-deluxe/commit/38d5d396b6fa5c1cdf65369f89b2ec86ceef917d)) - [@gravures](https://github.com/gravures)

  - **wrap.AnsiTextWrapper class - ([36a75a5](https://github.com/gravures/standard-deluxe/commit/36a75a5911621c6f74534a8341a58bc9e6c55e1c)) - [@gravures](https://github.com/gravures)
  - **Merge AnsiHelpFormatter and ColorsHelpFormatter - ([78b3f7f](https://github.com/gravures/standard-deluxe/commit/78b3f7fbd7bdee76c1560068958fec1fd3f670b3)) - [@gravures](https://github.com/gravures)
  - **Refactor HelpFormatters in argpaser module - ([0ce0d57](https://github.com/gravures/standard-deluxe/commit/0ce0d575b3a35a7ced737d6c0b24d73fffd00119)) - [@gravures](https://github.com/gravures)
  - **Refactors console package - ([7848e03](https://github.com/gravures/standard-deluxe/commit/7848e034bb825f03b79e93784aaf6f41c6313c5b)) - [@gravures](https://github.com/gravures)


- - -

##  Changelog for release [v0.12.0]
    
    https://github.com/gravures/standard-deluxe/compare/3c10c2efa88e6578bdcd938bae4cc81dfac155a0..v0.12.0
    2026-07-05
  
### Bug Fixes

  - **(file)** improve cross-platform behavior of file module functions - ([4434845](https://github.com/gravures/standard-deluxe/commit/44348450b8c862dbf34b7d25a6db1a6596cc0dcd)) - [@gravures](https://github.com/gravures)
  - **(file)** minor type hints fixes - ([31327ba](https://github.com/gravures/standard-deluxe/commit/31327bab5c1b7c04b2c0a4c84a22d983f3b8a19b)) - [@gravures](https://github.com/gravures)


### Features

  - **(file)** adds split_drive function to files module - ([7a4dd7d](https://github.com/gravures/standard-deluxe/commit/7a4dd7d0e4083880ca588ad7c90a205bfc21c8d6)) - [@gravures](https://github.com/gravures)
  - **(file)** adds new functions to files module - ([904c865](https://github.com/gravures/standard-deluxe/commit/904c865984d1a29f1e4c3d4b193f88d00c00de09)) - [@gravures](https://github.com/gravures)
  - **(file)** adds files module - ([3c10c2e](https://github.com/gravures/standard-deluxe/commit/3c10c2efa88e6578bdcd938bae4cc81dfac155a0)) - [@gravures](https://github.com/gravures)


### Refactoring

  - **(file)** rename module file - ([3409471](https://github.com/gravures/standard-deluxe/commit/3409471b225e55223cb67d29e58f8fd43121896a)) - [@gravures](https://github.com/gravures)



- - -

##  Changelog for release [v0.11.0]
    
    https://github.com/gravures/standard-deluxe/compare/25a4283eb14980301bf9e995631371784a8ef73e..v0.11.0
    2026-07-05
  
### Features

  - **(version)** [**breaking**] add simple version string parsing with the version module - ([fdc9e4f](https://github.com/gravures/standard-deluxe/commit/fdc9e4fadc960c88384c1920e214482bb2467a73)) - [@gravures](https://github.com/gravures)



- - -

##  Changelog for release [v0.10.0]
    
    https://github.com/gravures/standard-deluxe/compare/45867f39316db4cc1abfc5bcd6fa849bdfda643a..v0.10.0
    2026-07-04
  
### Bug Fixes

  - **(protocols)** fix protocol attribute detection for Python < 3.12 - ([660c2b7](https://github.com/gravures/standard-deluxe/commit/660c2b7ec5132c33f63aa17da32972ff7d66c0c7)) - [@gravures](https://github.com/gravures)


### Features

  - **(protocols)** adds protocols module - ([45867f3](https://github.com/gravures/standard-deluxe/commit/45867f39316db4cc1abfc5bcd6fa849bdfda643a)) - [@gravures](https://github.com/gravures)



- - -

##  Changelog for release [v0.9.0]
    
    https://github.com/gravures/standard-deluxe/compare/5703036de1b832790d02b63868e4604faed54f22..v0.9.0
    2026-07-04
  
### Bug Fixes

  - **(mureq)** fix small type hint issues - ([352a0bf](https://github.com/gravures/standard-deluxe/commit/352a0bfa80b77982d3065b38f6a2a9f13227763f)) - [@gravures](https://github.com/gravures)


### Documentation

  - **(mureq)** include mureq license into sphinx docs - ([83afd3c](https://github.com/gravures/standard-deluxe/commit/83afd3c00068fc214e08d97c453a1046efde0016)) - [@gravures](https://github.com/gravures)


### Features

  - **(mureq)** embed the mureq library - ([e0a4e8e](https://github.com/gravures/standard-deluxe/commit/e0a4e8eccc2ebd92b3ac282bf0da1846757fd6c5)) - [@gravures](https://github.com/gravures)



- - -

##  Changelog for release [v0.8.0]
    
    https://github.com/gravures/standard-deluxe/compare/01ccb9f2f62927a71a6eb4baaa23e9ff11df3cce..v0.8.0
    2026-07-04
  
### Bug Fixes

  - **(command)** fix exception raising removal in Command.__call__ method - ([5ddcfb6](https://github.com/gravures/standard-deluxe/commit/5ddcfb60aeba6a8c47cdbb0edf16d8bdc30f0c0a)) - [@gravures](https://github.com/gravures)

  - **(daemon)** fix daemon restart by caching constructor argumentsStore daemon controller constructor args in a WeakKeyDictionaryso start() can replay them when relaunching the daemon. Addsdouble-check locking for concurrent start() calls and documentscontroller semantics (multiple controllers, system-level singleton). - ([d04e384](https://github.com/gravures/standard-deluxe/commit/d04e384f3b65ce0302a11bce0fcc218e67b5e8ca)) - [@gravures](https://github.com/gravures)

  - **(process)** fix instantiating a Daemon on Windows do not raise AvailabilityError - ([8cf8549](https://github.com/gravures/standard-deluxe/commit/8cf85495e4189d86bd8319dd018da1b75ba8896b)) - [@gravures](https://github.com/gravures)
  - **(process)** set process.user to None on windows - ([d1f1c7c](https://github.com/gravures/standard-deluxe/commit/d1f1c7c6dadf0d357a0492e6dd4e2847a543a0f1)) - [@gravures](https://github.com/gravures)
  - **(process)** stop calling get_real_users on windows - ([4e68864](https://github.com/gravures/standard-deluxe/commit/4e688645e802d3cd50cf7cc38846f669ac4807f4)) - [@gravures](https://github.com/gravures)
  - **(process)** stop importing pwd on windows - ([aa36f96](https://github.com/gravures/standard-deluxe/commit/aa36f96dd7feee524ce1f52a987bd528a8118d07)) - [@gravures](https://github.com/gravures)
  - **(process)** remove custom _is_process_alive, inline os.kill in stop()The _is_process_alive() function used /proc/{pid}/stat parsing forzombie detection which only worked on Linux. On macOS it alwaysreturned True for zombies, causing stop() to hang until timeout.Remove the function entirely and inline os.kill(pid, 0) in the waitloop. The timeout + SIGKILL fallback already handles all edge cases. - ([372a432](https://github.com/gravures/standard-deluxe/commit/372a432c6b59b90ef0605378cba4b58399c427f0)) - [@gravures](https://github.com/gravures)
  - **(process)** change get_real_users to wor on all posix platforms - ([8b6ad44](https://github.com/gravures/standard-deluxe/commit/8b6ad441759f8f8131173502312045e79d8c16ab)) - [@gravures](https://github.com/gravures)
  - **(process)** fix dead loop in daemon stop method - ([773e854](https://github.com/gravures/standard-deluxe/commit/773e8548fed4d208586391465e882e3299a8d342)) - [@gravures](https://github.com/gravures)
  - **(process)** fix inferred returned type in Command.__call__ - ([845ebf1](https://github.com/gravures/standard-deluxe/commit/845ebf1e728e17d4aeba7617899e25df3d19be35)) - [@gravures](https://github.com/gravures)
  - **(process)** adds async call - ([03e21c0](https://github.com/gravures/standard-deluxe/commit/03e21c05b7eae228582d02f8adf4296be1700369)) - [@gravures](https://github.com/gravures)


### Documentation

  - **(process)** update doc for command elevation scenario - ([e7a2fd6](https://github.com/gravures/standard-deluxe/commit/e7a2fd641b98339a5d2fe095ce24250d73fd72e3)) - [@gravures](https://github.com/gravures)
  - **(process)** update docstrings - ([6012a68](https://github.com/gravures/standard-deluxe/commit/6012a684746f4a90cd8e5d56dfafc6b152d5fc47)) - [@gravures](https://github.com/gravures)


### Features

  - **(daemon)** add SIGUSR1/SIGUSR2 user signal support to DaemonThis accurately captures all the changes made:src/deluxe/process.py: Added signal_user1()/signal_user2() controller methods and on_user1()/on_user2() daemon hooks, with SIGUSR1/SIGUSR2 signal handlers in _RealDaemon.daemonize()tests/process_daemon_test.py: Added 7 new tests (unit + integration) for the signal methods and hooksDocstrings: Rewrote IPC section with basic control overview, Python IPC options, and User Signals subsection with code example - ([33972de](https://github.com/gravures/standard-deluxe/commit/33972dea4dcce476cd0b8cb9d992aab4304a3e4f)) - [@gravures](https://github.com/gravures)

  - **(process)** Adds the Daemon abstract bases class to the process module - ([1dd71f7](https://github.com/gravures/standard-deluxe/commit/1dd71f7c228c159d0fd3c2130a588a44cd27c605)) - [@gravures](https://github.com/gravures)

  - **adds process module - ([01ccb9f](https://github.com/gravures/standard-deluxe/commit/01ccb9f2f62927a71a6eb4baaa23e9ff11df3cce)) - [@gravures](https://github.com/gravures)


- - -

##  Changelog for release [v0.7.0]
    
    https://github.com/gravures/standard-deluxe/compare/9b8b4c2da3eab7cd001cf771ebc9afbd42651f58..v0.7.0
    2026-07-03
  
### Bug Fixes

  - **(mappings)** [**breaking**] type hint work and refactor - ([8ad4c48](https://github.com/gravures/standard-deluxe/commit/8ad4c48763ac2e0b8ac0565bd939a25f10804929)) - [@gravures](https://github.com/gravures)


### Documentation

  - **Updates docs string of mappings.FilteredView - ([1259cb8](https://github.com/gravures/standard-deluxe/commit/1259cb8f5e26c44653052f2da8dedabeb7f04efc)) - [@gravures](https://github.com/gravures)

### Features

  - **(environ)** [**breaking**] add environ module and move inside it Mapping.Environment class - ([11c62a8](https://github.com/gravures/standard-deluxe/commit/11c62a86d83c98dc02119dada5ec45b39b70ecd9)) - [@gravures](https://github.com/gravures)

  - **(seq)** add sequences module with OrderedSet types - ([8e58c34](https://github.com/gravures/standard-deluxe/commit/8e58c344480f2ec1d1deeeec6778e63d31328d08)) - [@gravures](https://github.com/gravures)

  - **implements other=None in OrderableDict after and before methods - ([e2cc365](https://github.com/gravures/standard-deluxe/commit/e2cc36537ef4a94ef57b22b3acce615b8830c899)) - [@gravures](https://github.com/gravures)
  - **adds Environment class and ulist function to mappings module - ([7c3d2ea](https://github.com/gravures/standard-deluxe/commit/7c3d2ea38e66509be22fe697861775766b314d3b)) - [@gravures](https://github.com/gravures)
  - **adds mappings module - ([9b8b4c2](https://github.com/gravures/standard-deluxe/commit/9b8b4c2da3eab7cd001cf771ebc9afbd42651f58)) - [@gravures](https://github.com/gravures)

### Refactoring

  - **(envdict)** move ulist function in EnvDict class - ([0e72422](https://github.com/gravures/standard-deluxe/commit/0e72422f1f70637c2a44148f2d200a9e17325b88)) - [@gravures](https://github.com/gravures)

  - **(mappings)** import from deluxe.importers instead of python test.support module - ([533c302](https://github.com/gravures/standard-deluxe/commit/533c3022332401619338dd05451c59e50855decb)) - [@gravures](https://github.com/gravures)

  - **(ulist)** move ulist Environment static method to sequence module - ([592fa39](https://github.com/gravures/standard-deluxe/commit/592fa393c8425190015e080648abf4702437c2b1)) - [@gravures](https://github.com/gravures)



- - -

##  Changelog for release [v0.6.0]
    
    https://github.com/gravures/standard-deluxe/compare/00177bd894071896d225db0da1b0eb02f1e98a35..v0.6.0
    2026-07-03
  
### Documentation

  - **(deluxe)** fix uncommited .rst files - ([e6461dc](https://github.com/gravures/standard-deluxe/commit/e6461dc91feae0b00112bfe915e40816ef3e2e8b)) - [@gravures](https://github.com/gravures)
  - **(deluxe)** fix wrong path to our custom autoapi templates and also upgrade templates to output all module members - ([00177bd](https://github.com/gravures/standard-deluxe/commit/00177bd894071896d225db0da1b0eb02f1e98a35)) - [@gravures](https://github.com/gravures)

  - **(functional)** edit documentation - ([97d327c](https://github.com/gravures/standard-deluxe/commit/97d327c87f468a9d817eb7addac02ec0e932b745)) - [@gravures](https://github.com/gravures)


### Features

  - **(functional)** adds functional module - ([58fec1d](https://github.com/gravures/standard-deluxe/commit/58fec1d4874badc106f0d92c127e0aee171dd4b4)) - [@gravures](https://github.com/gravures)



- - -

##  Changelog for release [v0.5.0]
    
    https://github.com/gravures/standard-deluxe/compare/c6b0f2e945dde41f7065ab8c752ece0185eb2ba2..v0.5.0
    2026-07-03
  
### Bug Fixes

  - **(typing)** minor type hints fixes - ([0e0f3ab](https://github.com/gravures/standard-deluxe/commit/0e0f3aba19a720641c8b7421db1f6fd2a58b3fde)) - [@gravures](https://github.com/gravures)


### Documentation

  - **(importers)** include python license into sphinx docs - ([a85cce7](https://github.com/gravures/standard-deluxe/commit/a85cce797fb948a48d660f641319a454b9be1de0)) - [@gravures](https://github.com/gravures)


### Features

  - **adds importers module - ([f6f62b5](https://github.com/gravures/standard-deluxe/commit/f6f62b5d35deabfad966a1196e9ae643b2dbbdab)) - [@gravures](https://github.com/gravures)

### Refactoring

  - **(importers)** includes needed functions from python test.support.import_helper module - ([cde1abe](https://github.com/gravures/standard-deluxe/commit/cde1abe374692a8ffae7684411ece9854b24fe85)) - [@gravures](https://github.com/gravures)



- - -

##  Changelog for release [v0.4.0]
    
    https://github.com/gravures/standard-deluxe/compare/b3af3fd8a2a005d5158b8635631f5793e714a2c7..v0.4.0
    2026-07-03
  
### Bug Fixes

  - **(MaybeCallable)** remove explicit Monad Protocol inheritance - ([c0f78ee](https://github.com/gravures/standard-deluxe/commit/c0f78ee7c8bc79f3fe4d17f7bb46b6e1b5e53f18)) - [@gravures](https://github.com/gravures)

  - **(enums)** __set_name__ on enum member previously did not work on python < 3.13 - ([2fad8f5](https://github.com/gravures/standard-deluxe/commit/2fad8f5c3d157c16695a2e0388b873bed695b2f4)) - [@gravures](https://github.com/gravures)


### Features

  - **(enums)** adds the enums module - ([4389a70](https://github.com/gravures/standard-deluxe/commit/4389a70d21058579f6d016045d90da59152e6758)) - [@gravures](https://github.com/gravures)


### Refactoring

  - **(enums)** removes MaybeCallable from module, adds test file and update documentation - ([d107446](https://github.com/gravures/standard-deluxe/commit/d1074462385e82ed95121f2de64f5d02bfd87452)) - [@gravures](https://github.com/gravures)



- - -

##  Changelog for release [v0.3.0]
    
    https://github.com/gravures/standard-deluxe/compare/2b17b4d92826d18fe37e0a178e380c123f1c8320..v0.3.0
    2026-07-02
  
### Bug Fixes

  - **(avail)** availabality decorator work also on class now - ([d7e1859](https://github.com/gravures/standard-deluxe/commit/d7e18597044110329d1279427ffe61aa5b952a84)) - [@gravures](https://github.com/gravures)

  - **(availability)** fix bug with supported function algorythm, add default parameters to the availability decorator, refine documentations - ([753b9dc](https://github.com/gravures/standard-deluxe/commit/753b9dc1dec546258c43a9a21d375295baba7188)) - [@gravures](https://github.com/gravures)
  - **(availability)** minor type hint change - ([467340c](https://github.com/gravures/standard-deluxe/commit/467340cdbcba073a9491299fa8815b863d7a5cc4)) - [@gravures](https://github.com/gravures)


### Build system

  - **(deluxe)** [**breaking**] remove monorepo support, bump python version to 3.11, use uv behind pdm. - ([0b98534](https://github.com/gravures/standard-deluxe/commit/0b98534c9ed376775791c60a5e31b5b05b612500)) - [@gravures](https://github.com/gravures)


### Features

  - **adds the deluxe.availability module - ([e12c249](https://github.com/gravures/standard-deluxe/commit/e12c2493d92e44be5ad327e9a9b91ce3e767ae5c)) - [@gravures](https://github.com/gravures)


- - -

##  Changelog for release [v0.2.0]
    
    https://github.com/gravures/standard-deluxe/compare/373c0454049d02ed321a517fb30a86990f680496..v0.2.0
    2026-07-01
  
### Bug Fixes

  - **(cython)** prevent lookup errors if table tool.cython.cythonize.extension do not exist - ([cfbe782](https://github.com/gravures/standard-deluxe/commit/cfbe78282233a607437027112f922a2df4b27f6e)) - [@gravures](https://github.com/gravures)

  - **(types)** fix allowed protocol instantiation in StaticType in some cases - ([cd78fcf](https://github.com/gravures/standard-deluxe/commit/cd78fcfb8e02aab44ebe9bc7fe567a23d984c835)) - [@gravures](https://github.com/gravures)


### Build system

  - **(cython)** adds support for windows extension modules - ([264cd08](https://github.com/gravures/standard-deluxe/commit/264cd0895ea0a5f5dd4b553180bedb7879efa732)) - [@gravures](https://github.com/gravures)
  - **(cython)** add pdm_build hook to handle cython extension build - ([ddb1ded](https://github.com/gravures/standard-deluxe/commit/ddb1ded1ee08c7387b791ce04b18b0db77624a6c)) - [@gravures](https://github.com/gravures)

  - **(deluxe)** [**breaking**] remove monorepo support, bump python version to 3.11, use uv behind pdm. - ([ce27e38](https://github.com/gravures/standard-deluxe/commit/ce27e386fe9f26aed4b72dbc61edeff2e059e9ae)) - [@gravures](https://github.com/gravures)
  - **(deluxe)** [**breaking**] remove monorepo support, bump python version to 3.11, use uv behind pdm. - ([ef0106e](https://github.com/gravures/standard-deluxe/commit/ef0106ea2e07aad03bfbdff33e8049d3917ee118)) - [@gravures](https://github.com/gravures)

  - **(pdm)** integration with cytohn build system - ([3a60c20](https://github.com/gravures/standard-deluxe/commit/3a60c20a388e75144c2fc6bfc6d1849f187c1c13)) - [@gravures](https://github.com/gravures)

  - **update pyright config - ([3c564f1](https://github.com/gravures/standard-deluxe/commit/3c564f14fcb5221c88390af2b99f45bbcfc20c08)) - [@gravures](https://github.com/gravures)
  - **Upgrade python requirement from 3.9 to 3.10 - ([11fcebf](https://github.com/gravures/standard-deluxe/commit/11fcebff8cf25efd79fde8a642667157d8283560)) - [@gravures](https://github.com/gravures)
  - **update buid system and linting tools - ([c50b3bf](https://github.com/gravures/standard-deluxe/commit/c50b3bffa6088a5979074f30bc4d148110fa4216)) - [@gravures](https://github.com/gravures)
  - **set editable backend to path - ([3e900fb](https://github.com/gravures/standard-deluxe/commit/3e900fb26c9bf23ee50239cb9cdbd3c95dc93e41)) - [@gravures](https://github.com/gravures)
  - **put pyproject.toml and pdm.lock in a clean state - ([e737803](https://github.com/gravures/standard-deluxe/commit/e737803c54b9c1044c08fb679f6504fbbfa6ae25)) - [@gravures](https://github.com/gravures)
  - **add editables package to test dependencies - ([e108172](https://github.com/gravures/standard-deluxe/commit/e1081720c371b806165e339fa76a8cebdacbd045)) - [@gravures](https://github.com/gravures)
  - **regenerate pdm.lock file - ([873a997](https://github.com/gravures/standard-deluxe/commit/873a997ba5ff6ccb25afd564927338b20b483a2a)) - [@gravures](https://github.com/gravures)
  - **Moves from Setuptools to PDM - ([373c045](https://github.com/gravures/standard-deluxe/commit/373c0454049d02ed321a517fb30a86990f680496)) - [@gravures](https://github.com/gravures)

### Documentation

  - **(deluxe)** adds python docs to interphinx mapping - ([22a8744](https://github.com/gravures/standard-deluxe/commit/22a874493dd8135c14a55a95667fa6dea52c1c1b)) - [@gravures](https://github.com/gravures)
  - **(deluxe)** migrate sphinx html them from furo to sphinx-immaterial - ([924ea66](https://github.com/gravures/standard-deluxe/commit/924ea663e76e396c1b8c0f81ffbc4557a103b3bc)) - [@gravures](https://github.com/gravures)
  - **(deluxe)** includes README.md, CONTRIBUTING.md LICENSE.md into sphinx doc - ([edb4f63](https://github.com/gravures/standard-deluxe/commit/edb4f633f64b342e9eaf0d83e1566ea7770666b2)) - [@gravures](https://github.com/gravures)


### Features

  - **(types)** [**breaking**] add types module and move into it Multiton class - ([4337160](https://github.com/gravures/standard-deluxe/commit/433716010321aa26d41211dc1236b03516c5930b)) - [@gravures](https://github.com/gravures)


### Refactoring

  - **(types)** types module refactoring - ([bd195de](https://github.com/gravures/standard-deluxe/commit/bd195decf7dd958b75a88a4d58eaa49eac80ee7a)) - [@gravures](https://github.com/gravures)
  - **(types)** [**breaking**] split types module in several private one including a cython extension - ([157923f](https://github.com/gravures/standard-deluxe/commit/157923f90584778d8e60fe388fe2a4c72b63b935)) - [@gravures](https://github.com/gravures)

  - **remove old collections module - ([c9d800f](https://github.com/gravures/standard-deluxe/commit/c9d800f17d2be3e4ddf4d8d2c8509c9117c77650)) - [@gravures](https://github.com/gravures)


- - -

Changelog generated by [cocogitto](https://github.com/cocogitto/cocogitto).