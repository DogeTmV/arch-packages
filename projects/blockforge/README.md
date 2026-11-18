# blockforge

A Scratch-inspired visual programming editor that generates real, standalone
**C++17** and **Rust 2021** programs. Blocks are for designing the program; the
deliverable is ordinary source code and a native SDL2 executable. Generated
programs do not need blockforge, Python, or Qt at run time.

## Highlights

- **67 visual blocks in 10 categories**: Events, Motion, Looks, Sound, Sensing,
  Control, Operators, Variables, Pen, and My Blocks.
- **25 typed expression reporters** with a real tokenizer/parser rather than
  string substitution: arithmetic, comparisons, boolean logic, text joining,
  sensing, random numbers, math functions, and conversions.
- **Two native targets** switched from the toolbar. The Generated source tab
  updates live while editing.
- **Concurrent scripts**: every top-level stack becomes a thread in the
  generated program, like Scratch hats running together.
- **Live preview**: a safe Python interpreter draws sprites and pen marks on
  the stage without starting a compiler or external process.
- **Real build pipeline**: `Build` invokes `g++` or `rustc` through an argument
  list, never a shell, and `Run` launches the resulting binary with logs in the
  Build log and Preview output tabs.
- **Versioned JSON projects** with sprites, variables, procedures, nested
  C-slots, and validation before save/build.
- **A complete editor workflow**: New, Open, Save, Save As, examples, target
  selection, source/binary export, project settings, dirty-change prompts, and
  keyboard shortcuts.
- **Editable custom blocks**: typed arguments, live reference updates when a
  procedure is renamed, and a dedicated editor for each procedure body.
- **Native/preview parity**: shared expression semantics, costume and edge
  clamping, ten-point stars, capped pen trails, and consistent text formatting.

## Interface

The window uses a dark, high-contrast theme with three main columns and a
bottom console:

- **Left — Blocks:** category buttons, search, and draggable block previews.
  Double-click a block to append it to the current sprite's script.
- **Center — Workspace:** one framed script per stack. Drag blocks into
  nested slots such as `SUB`, `THEN`, and `ELSE`; reorder by dragging; change
  fields inline. Hat blocks anchor a script.
- **Right — Stage and data:** scaled stage preview, sprite list, variables,
  and custom blocks. Add sprites, variables (`number`, `text`, or `bool`), and
  procedures from this column.
- **Bottom — Console:** tabs for generated C++/Rust source, compiler output,
  and program/preview output.

The toolbar has New, Open, Save, Save As, Examples, target selection, Build,
Run, and Stop. Source and binaries can be exported from the File menu, and the
stage forwards keyboard and mouse input to the live preview. Bundled examples
are **Hello Console**, **Bouncing Ball**, **Catch the Star**, **Pen Spiral**,
and **Tone Practice**.

## Running from source

```bash
cd projects/blockforge
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
./blockforge
```

Open a project with `blockforge project.json`, or choose an initial target with
`blockforge --language rust`. To install dependencies on Arch:

```bash
sudo pacman -S python pyside6 qt6-svg gcc rust sdl2
```

`gcc`, `rust`, and `sdl2` are only needed for compiling and running generated
programs. The editor, preview, source view, and test suite work without them.

## Generated programs

`compiler.py` turns a validated project into a single source file:

- C++17 uses `g++ -std=c++17` and SDL2.
- Rust 2021 uses `rustc --edition=2021` and hand-written SDL2 FFI, with no
  crates or Cargo project.
- Both runtimes provide sprites, directional movement, costumes, drawing,
  keyboard/mouse sensing, tone playback, variables, custom blocks, and script
  threads in a compact embedded runtime.
- The source is written to a temporary directory, compiled, and launched by
  `QProcess` with separate program and argument fields.

The output is intentionally readable: the generated file starts with a header
identifying blockforge, the target, and the project name.

## Preview safety

The in-editor preview evaluates fields from their parsed AST. It never calls
`eval()` or executes project text as Python. Unknown variables and malformed
expressions are rejected during validation, so a project file cannot inject
code into the editor. Preview output is capped, and stopping the preview
clears its script threads.

## Architecture

| Module | Responsibility |
| --- | --- |
| `core.py` | Block catalog, project model, persistence, validation |
| `expressions.py` | Expression parser and C++/Rust translators |
| `editing.py` | Pure helpers for nested block insertion/removal/moves |
| `compiler.py` | Source generation and build commands |
| `runtime_cpp.py` | Embedded C++ SDL2 runtime |
| `runtime_rust.py` | Embedded Rust SDL2 FFI runtime |
| `preview.py` | Safe step-based stage interpreter |
| `theme.py` | Dark palette, stylesheet, and toolbar glyphs |
| `gui.py` | PySide6 editor window and build/run process handling |
| `examples.py` | Five validated starter projects |

Business logic is Qt-free so the model, expressions, compiler, and preview can
be tested headlessly. GUI tests use `QT_QPA_PLATFORM=offscreen`.

## Testing

The suite includes real compiler integration tests: generated sources are
written, compiled with `g++`/`rustc`, executed, and checked for behavior such
as loop counts, variable updates, procedure arguments, Scratch-style heading
semantics, and preview/native parity. Headless GUI tests cover lifecycle and
dirty state, CLI startup, Save As and export, dialogs, nested drop targets,
stage input, and output streaming after the preview cap.

```bash
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
```

`Ran 101 tests ... OK` in this checkout.

## License

MIT — see `LICENSE`.
