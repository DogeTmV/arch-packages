# blockforge

A small, Scratch-like visual editor that turns friendly blocks into real,
standalone **C++17** and **Rust 2021** SDL2 programs. Blocks are for designing
the program; the deliverable is ordinary source code and a native executable.
Generated programs never need blockforge, Python, Qt, or Cargo at run time.

## What changed in the editor

blockforge is now organised around objects instead of loose scripts:

- **Spirits:** every character has its own script area, starting position,
  costume, and optional picture. Add one from the built-in spirit library or
  from a PNG/JPG on your computer.
- **Stage:** the stage is an object too. It has its own scripts and a backdrop
  chosen from the built-in stage library or an uploaded picture.
- **My Blocks:** reusable procedures are still available, with typed arguments
  and their own editor.
- **Readable blocks:** labels use plain wording such as `move 10 steps`,
  `if score > 2 then`, `pick random`, and `touching spirit?` instead of code-like
  reporter strings. The palette is divided into short, browsable sections.
- **No source preview:** the bottom dock only shows build output and preview
  output. Generated code appears when you export it.

## Highlights

- **68 visual blocks in 10 sections:** Events, Motion, Looks, Sound, Sensing,
  Control, Operators, Variables, Pen, My Blocks.
- **25 typed expression reporters** with a real tokenizer/parser rather than
  string substitution, so fields stay safe and translatable.
- **Two native targets** switched from the toolbar.
- **Concurrent scripts:** every top-level hat stack becomes a thread, like
  Scratch hats running together. Spirits and the stage can each own scripts.
- **Live preview:** a safe Python interpreter draws backdrops, pictures,
  spirits, and pen marks without starting a compiler or external process.
- **Real build pipeline:** `Build` invokes `g++` or `rustc` through an argument
  list, never through a shell; `Run` launches the resulting binary.
- **Custom save format:** `.bfproj` is a small ZIP container with a readable
  `project.json` and an `assets/` folder. Pictures travel with the project.
- **Separate export:** Export writes `main.cpp` or `main.rs` plus a short
  `README.md` into a folder you choose. Saving a project does not export code.
- **Built-in library:** ready-made spirits and generated stages can be added in
  one click and renamed automatically.
- **Legacy projects:** old version-1 JSON saves still open and are migrated to
  the new targeted-script model.
- **Native/preview parity:** shared expression semantics, thread-local stop,
  Scratch-style repeat rounding, costume and edge clamping, capped pen trails,
  ten-point stars, UTF-8 length, and normalized text output.

## Interface

The dark, high-contrast window has three columns and a compact bottom dock:

- **Left — Blocks:** category sections, search, and draggable block previews.
  Double-click a block to append it to the current script. Sprite-only blocks
  disappear when the Stage is selected.
- **Center — Scripts:** one framed stack per script, with nested slots for
  loops and decisions. A small header switches between the selected object's
  scripts and its My Blocks.
- **Right — Objects and stage:** a list of spirits plus Stage, the scaled live
  stage, variables, and custom blocks. Use the Library button here to add
  presets, or edit a spirit to upload a personal picture.
- **Bottom — Output:** tabs for the build log and preview program output. No
  generated source is shown or regenerated while you type.

The toolbar has New, Open, Save, Export folder, Build, Run, Stop, language, and
Examples. Bundled examples are **Hello Console**, **Bouncing Ball**, **Catch the
Star**, **Pen Spiral**, **Tone Practice**, and **Night Scene**. The last one
shows a stage script switching a built-in backdrop.

## Saving and exporting

- **Save / Save As** writes one portable `.bfproj` file. It contains the project
  manifest and every embedded PNG, including stage backdrops and spirit
  pictures. Validation runs before a save.
- **Export folder** writes generated source for the selected target into a
  directory, together with build instructions. The exported folder is
  self-contained and can be copied to another machine.
- **Build / Run** use temporary files; they never overwrite your project or the
  exported folder.

## Running from source

```bash
cd projects/blockforge
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
./blockforge
```

Open a project with `blockforge project.bfproj`, or choose an initial target with
`blockforge --language rust`. On Arch:

```bash
sudo pacman -S python pyside6 qt6-svg gcc rust sdl2
```

`gcc`, `rust`, and `sdl2` are only needed for compiling and running generated
programs. The editor, preview, and test suite work without them.

## Generated programs

`compiler.py` turns a validated project into a single source file:

- C++17 uses `g++ -std=c++17 -pthread` and links SDL2.
- Rust 2021 uses `rustc --edition=2021` with hand-written SDL2 FFI, no crates,
  and no Cargo project.
- Both runtimes embed RGBA picture bytes from the project, draw backdrops and
  spirit costumes as SDL textures, and fall back to simple geometric shapes.
- Scripts on the stage and on spirits are emitted as ordinary functions and
  run on separate threads.

The source starts with a short header identifying blockforge, the target, and
the project name, so exported code is easy to recognise and edit.

## Preview safety

The in-editor preview evaluates fields from their parsed AST. It never calls
`eval()` or executes project text as Python. Unknown variables, malformed
expressions, oversized pictures, and missing assets are rejected during
validation. Preview output is capped, and stopping the preview clears its
script threads.

## Architecture

| Module | Responsibility |
| --- | --- |
| `core.py` | Block catalog, project model, `.bfproj` persistence, validation |
| `expressions.py` | Expression parser and C++/Rust translators |
| `editing.py` | Pure helpers for nested block insertion/removal/moves |
| `images.py` | Standard-library PNG encode/decode for embedded pictures |
| `library.py` | Built-in spirit and stage presets |
| `compiler.py` | Source generation and build commands |
| `runtime_cpp.py` | Embedded C++ SDL2 runtime |
| `runtime_rust.py` | Embedded Rust SDL2 FFI runtime |
| `preview.py` | Safe step-based stage interpreter |
| `theme.py` | Dark palette, stylesheet, and toolbar glyphs |
| `gui.py` | PySide6 editor window and build/run process handling |
| `examples.py` | Six validated starter projects |

Business logic is Qt-free so the model, images, library, expressions, compiler,
and preview can be tested headlessly. GUI tests use `QT_QPA_PLATFORM=offscreen`.

## Testing

The suite includes real compiler integration tests: generated sources are
written, compiled with `g++`/`rustc`, executed, and checked for behavior such as
loop counts, procedure arguments, stage scripts, embedded pictures, Scratch-style
heading semantics, and preview/native parity. Headless GUI tests cover the
object picker, libraries, picture import, Save/Export split, dialogs, nested
drop targets, stage input, and process cleanup.

```bash
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
```

## License

MIT — see `LICENSE`.
