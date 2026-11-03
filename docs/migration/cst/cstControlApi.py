"""Control CST Microwave Studio (MWS) from Python.

This module is a thin wrapper around the official CST Python libraries
(``cst.interface`` and ``cst.results``). All CST calls live in this one file.

How CST scripting works
    CST is driven from Python by sending VBA code. ``add_to_history`` sends
    VBA that builds the 3D model. ``execute_vba_code`` sends VBA that runs
    right away (for example a parameter sweep).

What this file gives you
    ``CstSession``       starts one CST Design Environment (one CST process).
    ``CstProject``       wraps one MWS project and sends VBA history code.
    ``read_s_parameter`` reads saved S-parameter results.
    ``VIEWS``            the predefined 3D views saved by ``export_all_views``.

Coverage
    Geometry    boxes, cylinders, tubes, spheres, cones, toruses; curves
                (lines, arcs, circles, rectangles, ellipses, polygons,
                splines); extrude, rotate, sweep, cover and loft; booleans,
                transforms and arrays; working coordinate systems.
    Ports       discrete edge ports, discrete face ports, waveguide ports,
                coaxial ports, Floquet ports, plane waves, current ports,
                voltage wires, potentials and lumped elements.
    Materials   library and custom (normal, anisotropic, ohmic sheet),
                plus appearance.
    Mesh        global mesh settings.
    Import/exp  STEP, IGES, SAT, DXF, GDSII, Gerber, STL, OBJ, NASTRAN.
    Solver      time domain, frequency domain (hex / tet), integral equation,
                eigenmode, LF static (electric / magnetic / current), thermal,
                PIC, asymptotic, layer stacking; method, accuracy, excitation,
                optimizers and sensitivity analysis.
    Studies     unit-cell metasurfaces / periodic arrays, plane-wave RCS,
                broadband and parameter sweeps, and biomedical SAR.
    Results     S-parameters, input impedance, VSWR, 1D / 2D results, far
                fields, ASCII export and 3D view rendering.
    Post-proc   far-field array / calculator / plot, near-field scan, AR
                filter, Q-factor, SPICE / MOR extraction, combine results,
                0D results.
    Multiphys   thermal / CHT sources and boundaries, LF statics, coils,
                magnets, charges, mechanics (displacement / traction), rigid
                body motion, particles, signals and predefined fields.

Escape hatch
    ``configure_vba_object`` emits a ``With <object>`` block for any CST VBA
    object; ``add_history`` / ``run_vba`` accept raw VBA. No CST command is out
    of reach even when there is no dedicated wrapper.

Study types
    The same wrapper covers antennas and filters, unit-cell metasurfaces and
    periodic arrays (unit-cell boundaries plus Floquet ports), plane-wave
    illumination, coaxial- and waveguide-fed devices, and biomedical / SAR
    exposure (power-loss monitors plus the SAR object with its averaging
    volume).

Design rules
    DRY   every VBA call goes through ``add_history`` or ``run_vba``.
    KISS  small, focused wrappers instead of a full VBA binding.
    YAGNI no geometry kernel, no result cache and no hidden state.

Sources
    - CST Studio Suite 2026 Online Help, VBA macro language reference:
      "VBA Objects > Sources and Ports" (DiscretePort, DiscreteFacePort, Port,
      FloquetPort, PlaneWave) and "Special VBA Objects" (Transform, Solid,
      basicsolids Sphere/Cone/Torus, Solver, FDSolver, ParameterSweep).
    - CST app note "Scripting the CST Studio Suite with the Python" (2020).
    - CST Python libraries help: Automation and Scripting > Python.

Example
    >>> from cstControlApi import CstSession
    >>> with CstSession() as session:
    ...     project = session.new_mws()
    ...     project.set_units("mm", "GHz")
    ...     project.set_parameter("w", 10)
    ...     project.set_frequency_range(8, 12)
    ...     project.save("patch.cst")
"""

from __future__ import annotations

import glob
import importlib
import math
import os
import re
import sys
import tempfile
import textwrap
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Mapping, Sequence

__all__ = [
    "BOUNDARY_TYPES",
    "DISCRETE_PORT_TYPES",
    "FD_MESH_TYPES",
    "FD_SWEEP_TYPES",
    "LUMPED_ELEMENT_TYPES",
    "MATERIAL_TYPES",
    "PORT_ORIENTATIONS",
    "SOLVERS",
    "VIEWS",
    "CstProject",
    "CstSession",
    "export_result_item",
    "find_library_dir",
    "find_results",
    "find_tree_items",
    "input_impedance",
    "leaf_tree_items",
    "load_cst",
    "plot_lines_png",
    "plot_map_png",
    "power_loss_tree_path",
    "read_1d_result",
    "read_2d_result",
    "read_impedance",
    "read_s_parameter",
    "result_tree",
    "result_tree_vba",
    "s_parameter_tree_item",
    "save_csv",
    "to_db",
    "vswr",
    "validate_result_axis",
    "find_help_dir",
    "search_reference",
    "read_reference",
    "search_examples",
]

# Environment variables that point to the CST installation.
_ENV_LIBRARY_DIR = "CST_PYTHON_LIBRARIES"
_ENV_INSTALL_DIR = "CST_INSTALL_DIR"

# Name of the folder that holds the official CST Python libraries.
_LIBRARY_FOLDER = "python_cst_libraries"

# Default Windows install locations (newest version first after sorting).
_LIBRARY_GLOBS = (
    r"C:\Program Files (x86)\CST Studio Suite *\AMD64\python_cst_libraries",
    r"C:\Program Files\CST Studio Suite *\AMD64\python_cst_libraries",
)

# Predefined 3D views that CST can render. Used by ``export_all_views``.
VIEWS = ("Front", "Back", "Left", "Right", "Top", "Bottom", "Perspective", "Nearest Axis")

# Solver types accepted by ``ChangeSolverType`` in the HF (MWS) domain.
# Other CST domains (LF, EM, PS, ...) use the same command with their own names.
SOLVERS = ("HF Time Domain", "HF Frequency Domain", "HF Eigenmode")

# Boundary types accepted by the ``Boundary`` object (see ``set_boundaries``).
BOUNDARY_TYPES = ("electric", "magnetic", "open", "expanded open", "unit cell",
                  "periodic", "impedance", "normal", "tangential")

# ``Port.Orientation`` keys shared by waveguide ports (see ``add_waveguide_port``).
PORT_ORIENTATIONS = ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")

# ``DiscretePort.Type`` / ``DiscreteFacePort.Type`` excitation types.
DISCRETE_PORT_TYPES = ("Sparameter", "Voltage", "Current")

# ``FDSolver.SetMethod`` mesh and broadband sweep options.
FD_MESH_TYPES = ("Hexahedral", "Tetrahedral", "Surface")
FD_SWEEP_TYPES = ("General purpose", "Fast reduced order model", "Discrete samples only")

# ``LumpedElement.SetType`` keys.
LUMPED_ELEMENT_TYPES = ("rlcserial", "rlcparallel", "short", "open", "diode",
                        "spicecircuit")

# ``Material.Type`` keys in the HF (MWS) domain.
MATERIAL_TYPES = ("PEC", "Normal", "Anisotropic", "Lossy Metal", "Corrugated wall",
                  "Ohmic sheet", "Tensor formula", "Nonlinear")

# Axis helpers shared by the geometry and port helpers.
_AXIS_INDEX = {"x": 0, "y": 1, "z": 2}
# The two transverse axes of each port/cylinder axis, in ``center`` order.
_TRANSVERSE_AXES = {"x": ("y", "z"), "y": ("x", "z"), "z": ("x", "y")}


def find_library_dir() -> Path:
    """Find CST's ``python_cst_libraries`` folder.

    It checks, in order:
      1. the ``CST_PYTHON_LIBRARIES`` environment variable,
      2. the ``CST_INSTALL_DIR`` environment variable,
      3. the default Windows install paths.

    Raises ``FileNotFoundError`` when no folder is found.
    """
    override = os.environ.get(_ENV_LIBRARY_DIR)
    if override and Path(override).is_dir():
        return Path(override)

    install = os.environ.get(_ENV_INSTALL_DIR)
    if install:
        candidate = Path(install) / "AMD64" / _LIBRARY_FOLDER
        if candidate.is_dir():
            return candidate

    for pattern in _LIBRARY_GLOBS:
        for match in sorted(glob.glob(pattern), reverse=True):
            if Path(match).is_dir():
                return Path(match)

    raise FileNotFoundError(
        "Cannot find CST python_cst_libraries. Set the "
        f"{_ENV_LIBRARY_DIR} or {_ENV_INSTALL_DIR} environment variable."
    )


def load_cst():
    """Import the official ``cst`` package and its submodules.

    Adds CST's library folder to ``sys.path`` when the import fails.
    ``cst.interface`` and ``cst.results`` are imported too, because the
    ``cst`` package does not load them on its own.

    The modules are loaded with ``importlib.import_module`` and a string
    name instead of an ``import`` statement. ``cst`` is an optional
    dependency that only exists after CST's library folder is on
    ``sys.path``, so a plain ``import cst`` makes editors and type
    checkers report it as an unresolved import.
    """
    try:
        cst = importlib.import_module("cst")
    except ImportError:
        sys.path.append(str(find_library_dir()))
        cst = importlib.import_module("cst")

    # Load the submodules so ``cst.interface`` and ``cst.results`` are set.
    importlib.import_module("cst.interface")
    importlib.import_module("cst.results")

    return cst


def _vba_value(value: Any) -> str:
    """Return a VBA literal. Text is quoted, numbers stay plain."""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (int, float)):
        return str(value)
    return '"' + str(value).replace('"', '""') + '"'


class _HelpText(HTMLParser):
    """Read text from installed CST help without scripts or style rules."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())


def find_help_dir() -> Path:
    """Find the installed, version-matched CST help. CST_HELP_DIR overrides it."""
    override = os.environ.get("CST_HELP_DIR")
    path = Path(override) if override else find_library_dir().parent.parent / "Online Help"
    if not path.is_dir():
        raise FileNotFoundError("CST help is unavailable. Set CST_HELP_DIR to the installed Online Help directory.")
    return path.resolve()


@lru_cache(maxsize=4)
def _help_files(root: str) -> tuple[Path, ...]:
    path = Path(root)
    folders = (path / "mergedProjects" / "VBA_3D", path / "mergedProjects" / "VBA_DES",
               path / "mergedProjects" / "3D", path / "Python" / "source", path / "PythonTutorial")
    return tuple(file for folder in folders if folder.is_dir() for file in folder.rglob("*")
                 if file.suffix.lower() in {".htm", ".html"} and "whgdata" not in file.parts)


@lru_cache(maxsize=128)
def _help_text(path: str) -> str:
    reader = _HelpText()
    reader.feed(Path(path).read_text(encoding="utf-8", errors="replace"))
    return re.sub(r"[ \t]+", " ", "\n".join(reader.parts))


def search_reference(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Search installed CST VBA, Python, and tutorial references. Return source paths and excerpts."""
    terms = re.findall(r"[a-z0-9]+", query.lower())
    if not terms or not 1 <= limit <= 10:
        raise ValueError("Supply search terms and a limit from 1 to 10")
    root = find_help_dir()
    files = _help_files(str(root))
    # Python identifiers use underscores. Prefer their exact official API pages.
    if "_" in query:
        symbols = [word.lower() for word in query.split() if "_" in word]
        native = []
        for path in files:
            if "Python" not in path.parts and "PythonTutorial" not in path.parts:
                continue
            text = _help_text(str(path))
            if all(symbol in text.lower() for symbol in symbols):
                offset = max(0, text.lower().find(symbols[0]) - 150)
                native.append({"reference": "help/" + path.relative_to(root).as_posix(),
                               "source": str(path), "excerpt": text[offset:offset + 1800]})
                if len(native) == limit:
                    break
        if native:
            return native
    ranked = sorted(files, key=lambda path: sum(term in path.stem.lower() for term in terms), reverse=True)
    found = []
    for path in ranked:
        text = _help_text(str(path))
        combined = str(path.relative_to(root)).lower() + " " + text.lower()
        if all(term in combined for term in terms):
            offset = max(0, text.lower().find(terms[-1]) - 150)
            found.append({"reference": "help/" + path.relative_to(root).as_posix(),
                          "source": str(path), "excerpt": text[offset:offset + 1800]})
            if len(found) == limit:
                break
    return found


def read_reference(reference: str, query: str = "", max_chars: int = 12000) -> dict[str, Any]:
    """Read a returned help or library reference. query selects a relevant section."""
    if not 100 <= max_chars <= 20000:
        raise ValueError("max_chars must be from 100 to 20000")
    kind, relative = reference.split("/", 1)
    help_root = find_help_dir()
    root = {"help": help_root, "library": help_root.parent / "Library"}.get(kind)
    if root is None:
        raise ValueError("Use a reference returned by search_reference or search_examples")
    path = (root / relative).resolve()
    path.relative_to(root.resolve())
    if path.suffix.lower() not in {".htm", ".html", ".bas", ".mcr", ".py"}:
        raise ValueError("This reference is not a text document or macro")
    text = _help_text(str(path)) if path.suffix.lower() in {".htm", ".html"} else path.read_text(encoding="utf-8", errors="replace")
    offset = max(0, text.lower().find(query.lower()) - 400) if query else 0
    return {"source": str(path), "reference": reference, "text": text[offset:offset + max_chars],
            "offset": offset, "total_chars": len(text)}


def search_examples(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Find vendor tutorial pages and supplied VBA macros. Vendor examples are references, not project validation."""
    if not query.strip() or not 1 <= limit <= 10:
        raise ValueError("Supply a query and a limit from 1 to 10")
    help_root = find_help_dir()
    terms = re.findall(r"[a-z0-9]+", query.lower())
    found = []
    for folder, kind in ((help_root / "PythonTutorial", "help"), (help_root.parent / "Library", "library")):
        root = help_root if kind == "help" else folder
        for path in folder.rglob("*"):
            if path.suffix.lower() not in {".html", ".bas", ".mcr"}:
                continue
            if all(term in str(path.relative_to(root)).lower() for term in terms):
                found.append({"reference": kind + "/" + path.relative_to(root).as_posix(), "source": str(path)})
                if len(found) == limit:
                    return found
    return found


def _with_block(object_name: str, lines: Sequence[str]) -> str:
    """Build a VBA ``With ... End With`` block."""
    body = textwrap.indent("\n".join(lines), "    ")
    return f"With {object_name}\n{body}\nEnd With"


def power_loss_tree_path(monitor_name: str) -> str:
    """Return the CST result-tree path of a volume power-loss density result.

    ``monitor_name`` is the name given to the power-loss monitor (for example
    ``"power-loss (f=0.9)"``); the ``[pw]`` suffix is added when missing. SAR
    needs this path so it can find the loss result to integrate.
    """
    leaf = monitor_name if monitor_name.endswith("[pw]") else f"{monitor_name} [pw]"
    return "2D/3D Results\\Power Loss Dens.\\" + leaf


def _try_quiet_mode(env: Any) -> None:
    """Ask CST to hide dialog boxes. Ignore versions without this call."""
    try:
        env.set_quiet_mode(True)
    except Exception:
        pass


class CstSession:
    """One CST Design Environment (one CST process).

    Use it as a context manager so CST closes at the end.

        with CstSession() as session:
            project = session.new_mws()
    """

    def __init__(self) -> None:
        self._env = None

    def start(self) -> "CstSession":
        """Start CST. Does nothing when CST already runs."""
        if self._env is None:
            cst = load_cst()
            self._env = cst.interface.DesignEnvironment()
            _try_quiet_mode(self._env)
        return self

    @property
    def env(self) -> Any:
        """The native CST ``DesignEnvironment`` object."""
        return self.start()._env

    def new_mws(self) -> "CstProject":
        """Create a new Microwave Studio project."""
        return CstProject(self.env.new_mws(), self)

    def open_project(self, path: str | os.PathLike) -> "CstProject":
        """Open an existing ``.cst`` project."""
        return CstProject(self.env.open_project(str(Path(path).resolve())), self)

    def active_project(self) -> "CstProject":
        """Return the project that is active in the CST window."""
        return CstProject(self.env.active_project(), self)

    def list_open_projects(self) -> list[str]:
        """Return the paths of the projects that are open in CST."""
        return list(self.env.list_open_projects())

    def close(self) -> None:
        """Close CST. Save or close all projects first.

        CST sometimes reports a failure while shutting down; that is ignored
        so the caller always finishes cleanly.
        """
        if self._env is not None:
            try:
                self._env.close()
            except Exception:
                pass
            self._env = None

    def __enter__(self) -> "CstSession":
        return self.start()

    def __exit__(self, *exc_info) -> None:
        self.close()


class CstProject:
    """One CST Microwave Studio project.

    The wrapper sends VBA history code to the 3D modeler. Each call adds one
    named entry to the History tree, so the model stays readable.
    """

    def __init__(self, project: Any, session: CstSession) -> None:
        self._project = project
        self._session = session

    # --- native handles -------------------------------------------------

    @property
    def project(self) -> Any:
        """The native CST ``Project`` object."""
        return self._project

    @property
    def modeler(self) -> Any:
        """The native 3D modeler.

        CST names this attribute ``model3d``; some versions use ``modeler``.
        """
        return getattr(self._project, "model3d", None) or self._project.modeler

    @property
    def schematic(self) -> Any:
        """The native schematic. Used for VBA and parameter sweeps."""
        return self._project.schematic

    @property
    def filename(self) -> str:
        """Full path of the project file."""
        return self._project.filename()

    # --- raw VBA --------------------------------------------------------

    def add_history(self, caption: str, vba: str) -> None:
        """Add one named entry to the 3D History tree.

        ``vba`` is raw history code and must not contain ``Sub Main``.
        """
        self.modeler.add_to_history(caption, textwrap.dedent(vba).strip())

    def run_vba(self, body: str, timeout: int | None = None) -> None:
        """Run a VBA block in the schematic right away.

        The block is wrapped in ``Sub Main ... End Sub`` for you.
        """
        body = textwrap.indent(textwrap.dedent(body).strip(), "  ")
        self.schematic.execute_vba_code("Sub Main\n" + body + "\nEnd Sub", timeout=timeout)


    # --- model setup ----------------------------------------------------

    def set_units(
        self,
        geometry: str = "mm",
        frequency: str = "GHz",
        time: str = "ns",
        temperature: str = "Kelvin",
    ) -> None:
        """Set the project units."""
        code = _with_block(
            "Units",
            [
                f'.Geometry("{geometry}")',
                f'.Frequency("{frequency}")',
                f'.Time("{time}")',
                f'.TemperatureUnit("{temperature}")',
            ],
        )
        self.add_history("units", code)

    def set_parameter(self, name: str, value: Any) -> None:
        """Store one design parameter, for example ``w = 10``."""
        code = f"StoreParameter({_vba_value(name)}, {_vba_value(value)})"
        self.add_history(f"parameter {name}", code)

    def set_frequency_range(self, start: Any, stop: Any) -> None:
        """Set the solver frequency range, in the current frequency unit."""
        self.add_history("frequency range", f'Solver.FrequencyRange("{start}", "{stop}")')

    def set_solver(self, kind: str = "HF Frequency Domain") -> None:
        """Choose the solver, for example ``HF Frequency Domain``."""
        self.add_history(f"solver {kind}", f'ChangeSolverType("{kind}")')

    def define_brick(
        self,
        name: str,
        x_range: Sequence[Any],
        y_range: Sequence[Any],
        z_range: Sequence[Any],
        material: str = "PEC",
        component: str = "unitcell",
    ) -> None:
        """Add a box (brick) to the model."""
        code = _with_block(
            "Brick",
            [
                ".Reset",
                f".Name({_vba_value(name)})",
                f".Component({_vba_value(component)})",
                f".Material({_vba_value(material)})",
                f'.Xrange "{x_range[0]}", "{x_range[1]}"',
                f'.Yrange "{y_range[0]}", "{y_range[1]}"',
                f'.Zrange "{z_range[0]}", "{z_range[1]}"',
                ".Create",
            ],
        )
        self.add_history(f"brick {name}", code)

    def define_cylinder(
        self,
        name: str,
        axis: str,
        radius: Any,
        x_range: Sequence[Any],
        y_range: Sequence[Any],
        z_range: Sequence[Any],
        material: str = "PEC",
        component: str = "unitcell",
        inner_radius: Any = 0,
    ) -> None:
        """Add a cylinder (for example a via) to the model.

        ``inner_radius`` > 0 builds a tube (a cylinder with a hole), which is
        how the coaxial dielectric spacer and the outer conductor are modelled.
        """
        code = _with_block(
            "Cylinder",
            [
                ".Reset",
                f".Name({_vba_value(name)})",
                f".Component({_vba_value(component)})",
                f".Material({_vba_value(material)})",
                f".Axis({_vba_value(axis)})",
                f'.OuterRadius "{radius}"',
                f'.InnerRadius "{inner_radius}"',
                f'.Xrange "{x_range[0]}", "{x_range[1]}"',
                f'.Yrange "{y_range[0]}", "{y_range[1]}"',
                f'.Zrange "{z_range[0]}", "{z_range[1]}"',
                ".Create",
            ],
        )
        self.add_history(f"cylinder {name}", code)

    def define_sphere(
        self,
        name: str,
        center: Sequence[Any] = (0, 0, 0),
        radius: Any = 1.0,
        *,
        material: str = "PEC",
        component: str = "unitcell",
        segments: int = 0,
    ) -> None:
        """Add a sphere centred on ``center``."""
        cx, cy, cz = center
        code = _with_block(
            "Sphere",
            [
                ".Reset",
                f".Name({_vba_value(name)})",
                f".Component({_vba_value(component)})",
                f".Material({_vba_value(material)})",
                '.Axis "z"',
                f'.CenterRadius "{radius}"',
                '.TopRadius "0"',
                '.BottomRadius "0"',
                f'.Center "{cx}", "{cy}", "{cz}"',
                f'.Segments "{int(segments)}"',
                ".Create",
            ],
        )
        self.add_history(f"sphere {name}", code)

    def define_cone(
        self,
        name: str,
        axis: str,
        ranges: Sequence[Any],
        bottom_radius: Any,
        top_radius: Any = 0.0,
        *,
        center: Sequence[Any] = (0, 0),
        material: str = "PEC",
        component: str = "unitcell",
        segments: int = 0,
    ) -> None:
        """Add a (possibly truncated) cone along ``axis``.

        ``ranges`` is the axial extent; ``center`` holds the two transverse
        coordinates of the axis (order per axis: x -> (y, z), y -> (x, z),
        z -> (x, y)).
        """
        centers: dict[str, Any] = {"x": 0, "y": 0, "z": 0}
        transverse = _TRANSVERSE_AXES[axis]
        centers[transverse[0]] = center[0]
        centers[transverse[1]] = center[1]
        xc, yc, zc = centers["x"], centers["y"], centers["z"]
        code = _with_block(
            "Cone",
            [
                ".Reset",
                f".Name({_vba_value(name)})",
                f".Component({_vba_value(component)})",
                f".Material({_vba_value(material)})",
                f'.Axis "{axis}"',
                f'.BottomRadius "{bottom_radius}"',
                f'.TopRadius "{top_radius}"',
                f'.Xcenter "{xc}"',
                f'.Ycenter "{yc}"',
                f'.Zcenter "{zc}"',
                f'.{axis.upper()}range "{ranges[0]}", "{ranges[1]}"',
                f'.Segments "{int(segments)}"',
                ".Create",
            ],
        )
        self.add_history(f"cone {name}", code)

    def define_torus(
        self,
        name: str,
        axis: str,
        outer_radius: Any,
        inner_radius: Any,
        *,
        center: Sequence[Any] = (0, 0, 0),
        material: str = "PEC",
        component: str = "unitcell",
        segments: int = 0,
    ) -> None:
        """Add a torus (``outer_radius`` is the big radius, ``inner_radius`` the small one)."""
        cx, cy, cz = center
        code = _with_block(
            "Torus",
            [
                ".Reset",
                f".Name({_vba_value(name)})",
                f".Component({_vba_value(component)})",
                f".Material({_vba_value(material)})",
                f'.Axis "{axis}"',
                f'.OuterRadius "{outer_radius}"',
                f'.InnerRadius "{inner_radius}"',
                f'.Xcenter "{cx}"',
                f'.Ycenter "{cy}"',
                f'.Zcenter "{cz}"',
                f'.Segments "{int(segments)}"',
                ".Create",
            ],
        )
        self.add_history(f"torus {name}", code)

    # --- solids: booleans, transforms and arrays -------------------------

    def boolean(self, operation: str, target: str, *tools: str) -> None:
        """Apply a boolean ``operation`` to solids named ``component:solid``.

        ``operation`` is ``Add``, ``Subtract``, ``Insert`` or ``Intersect``
        (the ``Solid`` VBA object). ``Add`` / ``Subtract`` / ``Intersect`` keep
        the result in ``target`` and delete ``tools``; ``Insert`` keeps both.
        """
        args = ", ".join(f'"{name}"' for name in (target, *tools))
        # CST replaces an entry when its caption is reused. Include operands
        # so consecutive unions/subtractions on different solids remain replayable.
        caption = f"solid {operation.lower()} {target} with {', '.join(tools)}"
        self.add_history(caption, f"Solid.{operation} {args}")

    def transform(
        self,
        name: str,
        how: str,
        *,
        vector: Sequence[Any] = (0, 0, 0),
        center: Sequence[Any] = (0, 0, 0),
        angle: Sequence[Any] = (0, 0, 0),
        scale_factor: Sequence[Any] = (1, 1, 1),
        plane_normal: Sequence[Any] = (0, 0, 1),
        origin: str = "ShapeCenter",
        repetitions: int = 1,
        copy: bool = False,
        group: bool = False,
        objects: str = "Shape",
    ) -> None:
        """Transform one solid, ``how`` = ``Translate``/``Rotate``/``Scale``/``Mirror``.

        Use ``repetitions`` > 1 with ``copy=True`` to build a linear array.
        ``origin`` is ``ShapeCenter``, ``CommonCenter`` or ``Free`` (then
        ``center`` is used).
        """
        lines = [".Reset", f".Name({_vba_value(name)})"]
        if how == "Translate":
            lines.append(f'.Vector "{vector[0]}", "{vector[1]}", "{vector[2]}"')
        elif how == "Rotate":
            lines.append(f'.Angle "{angle[0]}", "{angle[1]}", "{angle[2]}"')
        elif how == "Scale":
            lines.append(
                f'.ScaleFactor "{scale_factor[0]}", "{scale_factor[1]}", "{scale_factor[2]}"')
        elif how == "Mirror":
            lines.append(
                f'.PlaneNormal "{plane_normal[0]}", "{plane_normal[1]}", "{plane_normal[2]}"')
        else:
            raise ValueError(f"unsupported transformation: {how!r}")
        if how != "Translate":
            lines.append(f'.Origin "{origin}"')
            if origin == "Free":
                lines.append(f'.Center "{center[0]}", "{center[1]}", "{center[2]}"')
        lines += [
            f'.MultipleObjects "{_vba_value(copy)}"',
            f'.GroupObjects "{_vba_value(group)}"',
            f'.Repetitions "{int(repetitions)}"',
            f'.Transform "{objects}", "{how}"',
            ".Create",
        ]
        self.add_history(f"transform {how} {name}", _with_block("Transform", lines))

    def translate(self, name: str, vector: Sequence[Any], **kwargs: Any) -> None:
        """Move a solid along ``vector`` (extra keywords go to :meth:`transform`)."""
        self.transform(name, "Translate", vector=vector, **kwargs)

    def rotate(self, name: str, angle: Sequence[Any], **kwargs: Any) -> None:
        """Rotate a solid by the per-axis ``angle`` in degrees."""
        self.transform(name, "Rotate", angle=angle, **kwargs)

    def mirror(self, name: str, plane_normal: Sequence[Any], **kwargs: Any) -> None:
        """Mirror a solid on a plane with the given normal."""
        self.transform(name, "Mirror", plane_normal=plane_normal, **kwargs)

    def scale(self, name: str, scale_factor: Sequence[Any], **kwargs: Any) -> None:
        """Scale a solid by the per-axis ``scale_factor``."""
        self.transform(name, "Scale", scale_factor=scale_factor, **kwargs)

    def rectangular_array(
        self, name: str, vector: Sequence[Any], cells: int,
        *, copy: bool = True, group: bool = False,
    ) -> None:
        """Repeat one solid ``cells`` times along ``vector`` (a linear array)."""
        self.transform(name, "Translate", vector=vector, repetitions=cells,
                       copy=copy, group=group)

    def delete_solid(self, name: str) -> None:
        """Delete a solid (``component:solid`` or ``solid``)."""
        self.add_history(f"delete {name}", f'Solid.Delete "{name}"')

    def rename_solid(self, old: str, new: str) -> None:
        """Rename a solid."""
        self.add_history(f"rename {old}", f'Solid.Rename "{old}", "{new}"')

    def change_material(self, name: str, material: str) -> None:
        """Assign an existing material to a solid."""
        self.add_history(f"material {name}", f'Solid.ChangeMaterial "{name}", "{material}"')

    def change_component(self, name: str, component: str) -> None:
        """Move a solid into an existing component."""
        self.add_history(f"component {name}", f'Solid.ChangeComponent "{name}", "{component}"')

    # --- boundaries, unit cell, symmetry, background ----------------------

    def set_boundaries(
        self,
        xmin: str = "open",
        xmax: str = "open",
        ymin: str = "open",
        ymax: str = "open",
        zmin: str = "open",
        zmax: str = "open",
        apply_all: bool = False,
        open_add_space_factor: float | None = None,
    ) -> None:
        """Set the six boundary faces.

        Valid types are ``electric`` (PEC), ``magnetic`` (PMC), ``open``,
        ``expanded open``, ``unit cell``, ``periodic``, ``impedance``,
        ``normal`` and ``tangential``.
        """
        lines = [
            f'.Xmin "{xmin}"',
            f'.Xmax "{xmax}"',
            f'.Ymin "{ymin}"',
            f'.Ymax "{ymax}"',
            f'.Zmin "{zmin}"',
            f'.Zmax "{zmax}"',
            f'.ApplyInAllDirections "{_vba_value(apply_all)}"',
        ]
        if open_add_space_factor is not None:
            lines.append(f'.OpenAddSpaceFactor "{open_add_space_factor}"')
        self.add_history("boundaries", _with_block("Boundary", lines))

    set_boundary = set_boundaries

    def set_symmetry(self, x: str = "none", y: str = "none", z: str = "none") -> None:
        """Set symmetry planes. Each value is ``none``, ``electric`` or ``magnetic``."""
        code = _with_block(
            "Boundary",
            [f'.Xsymmetry "{x}"', f'.Ysymmetry "{y}"', f'.Zsymmetry "{z}"'],
        )
        self.add_history("symmetry", code)

    def set_unit_cell(
        self,
        scan_theta: float = 0.0,
        scan_phi: float = 0.0,
        zmin: str = "expanded open",
        zmax: str = "expanded open",
        cell_ds1: float | None = None,
        cell_ds2: float | None = None,
        cell_angle: float | None = None,
        fit_to_bounding_box: bool = True,
        open_add_space_factor: float = 0.5,
    ) -> None:
        """Set up one unit cell of a metasurface or a periodic array.

        The X and Y faces become periodic ``unit cell`` walls. ``scan_theta``
        and ``scan_phi`` give the incidence (or scan) angle used by a Floquet
        study.
        """
        lines = [
            '.Xmin "unit cell"',
            '.Xmax "unit cell"',
            '.Ymin "unit cell"',
            '.Ymax "unit cell"',
            f'.Zmin "{zmin}"',
            f'.Zmax "{zmax}"',
            '.Xsymmetry "none"',
            '.Ysymmetry "none"',
            '.Zsymmetry "none"',
            '.ApplyInAllDirections "False"',
            f'.OpenAddSpaceFactor "{open_add_space_factor}"',
            '.XPeriodicShift "0.0"',
            '.YPeriodicShift "0.0"',
            '.ZPeriodicShift "0.0"',
            f'.PeriodicUseConstantAngles "{_vba_value(True)}"',
            f'.SetPeriodicBoundaryAngles "{scan_theta}", "{scan_phi}"',
            '.SetPeriodicBoundaryAnglesDirection "outward"',
            f'.UnitCellFitToBoundingBox "{_vba_value(fit_to_bounding_box)}"',
        ]
        for name, value in (("UnitCellDs1", cell_ds1), ("UnitCellDs2", cell_ds2),
                            ("UnitCellAngle", cell_angle)):
            if value is not None:
                lines.append(f'.{name} "{value}"')
        self.add_history("unit cell boundaries", _with_block("Boundary", lines))

    def set_unit_cell_boundaries(self, transverse: str = "unit cell", z: str = "open") -> None:
        """Set periodic boundaries for one unit cell (simple form)."""
        self.set_boundaries(xmin=transverse, xmax=transverse, ymin=transverse,
                            ymax=transverse, zmin=z, zmax=z)

    def set_background(
        self,
        material_type: str = "Normal",
        epsilon: float = 1.0,
        mu: float = 1.0,
        conductivity: float = 0.0,
        space: float | None = None,
    ) -> None:
        """Set the background material and, optionally, the open-boundary space."""
        lines = [
            ".Reset",
            f'.Type "{material_type}"',
            f'.Epsilon "{epsilon}"',
            f'.Mu "{mu}"',
            f'.ElConductivity "{conductivity}"',
        ]
        if space is not None:
            lines += [f'.{axis}Space "{space}"'
                      for axis in ("Xmin", "Xmax", "Ymin", "Ymax", "Zmin", "Zmax")]
        self.add_history("background", _with_block("Background", lines))

    # --- metasurface / periodic excitation -------------------------------

    def add_floquet_ports(
        self,
        zmin: bool = True,
        zmax: bool = True,
        modes: int = 2,
        theta: float = 0.0,
        phi: float = 0.0,
        circular_polarization: bool = False,
        distance_to_reference_plane: float = 0.0,
    ) -> None:
        """Add Floquet ports on ``Zmin`` and/or ``Zmax`` for a unit-cell study."""
        lines = [
            ".Reset",
            f'.SetDialogTheta "{theta}"',
            f'.SetDialogPhi "{phi}"',
            '.SetCustomizedListFlag "False"',
        ]
        for enabled, position in ((zmin, "Zmin"), (zmax, "Zmax")):
            if not enabled:
                continue
            lines += [
                f'.Port "{position}"',
                f'.SetNumberOfModesConsidered "{modes}"',
                f'.SetDistanceToReferencePlane "{distance_to_reference_plane}"',
                f'.SetUseCircularPolarization "{_vba_value(circular_polarization)}"',
            ]
        self.add_history("floquet ports", _with_block("FloquetPort", lines))

    # --- ports: discrete edge and discrete face --------------------------

    def add_discrete_port(
        self,
        port_number: int,
        point1: Sequence[Any],
        point2: Sequence[Any],
        *,
        kind: str = "Sparameter",
        impedance: Any = 50.0,
        voltage: Any = 1.0,
        current: Any = 1.0,
        radius: Any = 0.0,
        voltage_impedance: Any | None = None,
        wire: str | None = None,
        wire_position: str | None = None,
        invert: bool = False,
        local_coordinates: bool = False,
        monitor: bool = False,
    ) -> None:
        """Add a discrete (edge) port between two global points.

        ``kind`` is ``Sparameter``, ``Voltage`` or ``Current`` (see
        ``DISCRETE_PORT_TYPES``) and selects whether the impedance, the voltage
        or the current value is used. This is the standard lumped / TEM feed:
        antenna inset feeds, coax probes, chip / via ports.

        ``wire`` / ``wire_position`` attach the port to an existing wire and
        ignore ``point1``; ``voltage_impedance`` applies to the transient and
        TLM solvers only.
        """
        x1, y1, z1 = point1
        x2, y2, z2 = point2
        lines = [
            ".Reset",
            f".PortNumber {_vba_value(str(port_number))}",
            f'.Type "{kind}"',
            f'.Impedance "{impedance}"',
            f'.Voltage "{voltage}"',
            f'.Current "{current}"',
            f'.SetP1 "False", "{x1}", "{y1}", "{z1}"',
            f'.SetP2 "False", "{x2}", "{y2}", "{z2}"',
            f'.InvertDirection "{_vba_value(invert)}"',
            f'.LocalCoordinates "{_vba_value(local_coordinates)}"',
        ]
        if voltage_impedance is not None:
            lines.append(f'.VoltagePortImpedance "{voltage_impedance}"')
        if wire is not None:
            lines.append(f'.Wire "{wire}"')
            if wire_position is not None:
                lines.append(f'.Position "{wire_position}"')
        lines += [
            f'.Monitor "{_vba_value(monitor)}"',
            f'.Radius "{radius}"',
            ".Create",
        ]
        self.add_history(f"discrete port {port_number}", _with_block("DiscretePort", lines))

    def add_discrete_face_port(
        self,
        port_number: int,
        point1: Sequence[Any],
        point2: Sequence[Any],
        *,
        kind: str = "Sparameter",
        impedance: Any = 50.0,
        voltage: Any = 1.0,
        current: Any = 1.0,
        label: str = "",
        invert: bool = False,
        local_coordinates: bool = False,
        center_edge: bool = True,
        monitor: bool = False,
    ) -> None:
        """Add a discrete face port between two picked edges.

        The two points only reference the picked edges (``picked=True``).
        Face ports are supported by the integral equation solver, the transient
        solvers and the tetrahedral frequency domain solver; other solvers fall
        back to a Discrete Edge Port. A coaxial or cylindrical face port is
        created this way when the two picked edges are coaxial circles.
        """
        x1, y1, z1 = point1
        x2, y2, z2 = point2
        lines = [
            ".Reset",
            f".PortNumber {_vba_value(str(port_number))}",
            f'.Type "{kind}"',
            f'.Label "{label}"',
            f'.Impedance "{impedance}"',
            f'.VoltageAmplitude "{voltage}"',
            f'.CurrentAmplitude "{current}"',
            f'.SetP1 "True", "{x1}", "{y1}", "{z1}"',
            f'.SetP2 "True", "{x2}", "{y2}", "{z2}"',
            f'.LocalCoordinates "{_vba_value(local_coordinates)}"',
            f'.InvertDirection "{_vba_value(invert)}"',
            f'.CenterEdge "{_vba_value(center_edge)}"',
            f'.Monitor "{_vba_value(monitor)}"',
            ".Create",
        ]
        self.add_history(
            f"discrete face port {port_number}", _with_block("DiscreteFacePort", lines))

    # --- ports: waveguide and coaxial ------------------------------------

    def add_waveguide_port(
        self,
        port_number: int,
        *,
        orientation: str = "zmin",
        coordinates: str = "Free",
        x_range: Sequence[Any] = (0, 0),
        y_range: Sequence[Any] = (0, 0),
        z_range: Sequence[Any] = (0, 0),
        modes: int = 1,
        polarization_angle: Any = 0.0,
        adjust_polarization: bool = False,
        reference_plane_distance: Any = 0.0,
        port_on_bound: bool = True,
        clip_picked_port_to_bound: bool = False,
        text_size: Any = 50.0,
        label: str = "",
        shield: str | None = None,
        single_ended: bool = False,
    ) -> None:
        """Add a waveguide port.

        ``orientation`` is one of ``PORT_ORIENTATIONS`` and sets the excitation
        direction (``"zmin"`` = port on the lower z face, feeding +z). With
        ``coordinates="Free"`` the transversal plane is the rectangle spanned
        by ``x_range``, ``y_range`` and ``z_range`` (one of them is degenerate,
        for example ``z_range=(z, z)``); use ``"Full"`` for the whole domain
        face or ``"Picks"`` for a picked face. Set ``port_on_bound=False`` for
        an internal port. ``shield`` is ``none``, ``PEC`` or ``PMC``.
        """
        lines = [
            ".Reset",
            f".PortNumber {_vba_value(str(port_number))}",
            f'.Label "{label}"',
            f'.NumberOfModes "{int(modes)}"',
            f'.AdjustPolarization "{_vba_value(adjust_polarization)}"',
            f'.PolarizationAngle "{polarization_angle}"',
            f'.ReferencePlaneDistance "{reference_plane_distance}"',
            f'.TextSize "{text_size}"',
            f'.Coordinates "{coordinates}"',
            f'.Orientation "{orientation}"',
            f'.PortOnBound "{_vba_value(port_on_bound)}"',
            f'.ClipPickedPortToBound "{_vba_value(clip_picked_port_to_bound)}"',
            f'.Xrange "{x_range[0]}", "{x_range[1]}"',
            f'.Yrange "{y_range[0]}", "{y_range[1]}"',
            f'.Zrange "{z_range[0]}", "{z_range[1]}"',
        ]
        if shield is not None:
            lines.append(f'.Shield "{shield}"')
        if single_ended:
            lines.append('.SingleEnded "True"')
        lines.append(".Create")
        self.add_history(f"waveguide port {port_number}", _with_block("Port", lines))

    def add_coaxial_port(
        self,
        port_number: int,
        *,
        axis: str = "z",
        plane_position: Any = 0.0,
        center: Sequence[Any] = (0.0, 0.0),
        inner_radius: Any = 0.5,
        dielectric_radius: Any = 1.5,
        outer_radius: Any = 1.6,
        length: Any = 10.0,
        direction: int = 1,
        dielectric: str = "Vacuum",
        conductor: str = "PEC",
        component: str = "ports",
        kind: str = "waveguide",
        modes: int = 1,
        impedance: Any = 50.0,
        orientation: str | None = None,
        port_on_bound: bool = False,
        name_prefix: str = "coax",
    ) -> None:
        """Create a coaxial line and its port in one call.

        Builds three solids along ``axis`` from the ``plane_position`` reference
        plane, extending ``length`` in ``direction`` (+1 or -1): the inner
        conductor (``conductor``), the dielectric spacer (``dielectric``) and
        the outer conductor / shield (``conductor``). ``center`` holds the two
        transverse coordinates of the coax axis (order per axis: x -> (y, z),
        y -> (x, z), z -> (x, y)).

        The port is then added at the reference plane:

        * ``kind="waveguide"`` (default): a waveguide port spanning the coaxial
          cross-section, which CST resolves to its TEM mode - the usual coaxial
          port.
        * ``kind="discrete"``: a discrete edge port from the inner conductor to
          the shield, a 50 ohm lumped model of the coax.

        ``orientation`` defaults to feeding the structure away from the coax
        line (``"{axis}max"`` when the line runs in +axis, else ``"{axis}min"``).
        """
        if axis not in _TRANSVERSE_AXES:
            raise ValueError(f"unknown axis: {axis!r}")
        if kind not in ("waveguide", "discrete"):
            raise ValueError(f"unknown coax port kind: {kind!r}")

        c0, c1 = float(center[0]), float(center[1])
        start = float(plane_position)
        stop = start + int(direction) * float(length)

        def box(radius: Any, lo: Any, hi: Any) -> dict[str, tuple[Any, Any]]:
            low, high = min(lo, hi), max(lo, hi)
            return {
                _TRANSVERSE_AXES[axis][0]: (c0 - radius, c0 + radius),
                _TRANSVERSE_AXES[axis][1]: (c1 - radius, c1 + radius),
                axis: (low, high),
            }

        inner = box(inner_radius, start, stop)
        self.define_cylinder(
            f"{name_prefix}_inner", axis, inner_radius, inner["x"], inner["y"],
            inner["z"], material=conductor, component=component)
        spacer = box(dielectric_radius, start, stop)
        self.define_cylinder(
            f"{name_prefix}_dielectric", axis, dielectric_radius, spacer["x"],
            spacer["y"], spacer["z"], material=dielectric, component=component,
            inner_radius=inner_radius)
        shield = box(outer_radius, start, stop)
        self.define_cylinder(
            f"{name_prefix}_shield", axis, outer_radius, shield["x"], shield["y"],
            shield["z"], material=conductor, component=component,
            inner_radius=dielectric_radius)

        if orientation is None:
            orientation = f"{axis}max" if direction > 0 else f"{axis}min"

        if kind == "waveguide":
            port = box(outer_radius, plane_position, plane_position)
            self.add_waveguide_port(
                port_number, orientation=orientation, coordinates="Free",
                x_range=port["x"], y_range=port["y"], z_range=port["z"],
                modes=modes, port_on_bound=port_on_bound)
            return

        def point(offset: Any) -> tuple[Any, Any, Any]:
            coords = {_TRANSVERSE_AXES[axis][0]: c0 + offset,
                      _TRANSVERSE_AXES[axis][1]: c1, axis: plane_position}
            return (coords["x"], coords["y"], coords["z"])

        self.add_discrete_port(
            port_number, point(inner_radius), point(dielectric_radius),
            kind="Sparameter", impedance=impedance, monitor=True)

    def delete_port(self, port_number: int) -> None:
        """Delete an existing port (waveguide or discrete)."""
        self.add_history(f"delete port {port_number}", f"Port.Delete {int(port_number)}")

    def rename_port(self, old: int, new: int) -> None:
        """Change a port number."""
        self.add_history(f"rename port {old}", f"Port.Rename {int(old)}, {int(new)}")

    def set_port_label(self, port_number: int, label: str) -> None:
        """Set the label of an existing port."""
        self.add_history(f"label port {port_number}",
                         f'Port.RenameLabel {int(port_number)}, "{label}"')

    def set_plane_wave(
        self,
        normal: Sequence[Any] = (-1, 0, 0),
        e_vector: Sequence[Any] = (0, 0, 1),
        polarization: str = "Linear",
        phase_difference: float = 0.0,
        circular_direction: str = "Left",
        axial_ratio: float = 0.0,
    ) -> None:
        """Define a plane wave excitation (metasurface RCS, SAR exposure).

        ``polarization`` is ``Linear``, ``Circular`` or ``Elliptical``.
        """
        nx, ny, nz = normal
        ex, ey, ez = e_vector
        lines = [
            ".Reset",
            f'.Normal "{nx}", "{ny}", "{nz}"',
            f'.EVector "{ex}", "{ey}", "{ez}"',
            f'.Polarization "{polarization}"',
            f'.PhaseDifference "{phase_difference}"',
            f'.CircularDirection "{circular_direction}"',
            f'.AxialRatio "{axial_ratio}"',
            ".Store",
        ]
        self.add_history("plane wave", _with_block("PlaneWave", lines))

    def activate_plane_wave(self, fmin: Any = 1.0, fmax: Any = 2.0,
                            accuracy: float = 1e-4, name: int = 1, mode: int = 1) -> None:
        """Make the plane wave the solver excitation."""
        code = _with_block(
            "Solver",
            [
                ".ResetExcitationList",
                f'.SetExcitation "planewave", "{name}", "{mode}", '
                f'"{accuracy}", "{fmin}", "{fmax}", "True"',
            ],
        )
        self.add_history("plane wave excitation", code)

    # --- materials (tissue, phantom, custom) -----------------------------

    def load_material(self, name: str) -> None:
        """Copy one material from the CST material library into the project."""
        self.add_history(
            f"load material {name}",
            'With MaterialLibrary\n'
            f'  .LoadMaterialFromLibrary ("{name}", "", True)\n'
            'End With',
        )

    def add_material(
        self,
        name: str,
        material_type: str = "Normal",
        epsilon: float = 1.0,
        mu: float = 1.0,
        conductivity: float = 0.0,
        tan_delta: float = 0.0,
        density: float = 0.0,
        colour: Sequence[Any] | None = None,
    ) -> None:
        """Define a simple material, for example a tissue or phantom layer.

        The loss can be given either through ``conductivity`` [S/m] or through
        ``tan_delta``.
        """
        lines = [
            ".Reset",
            f'.Name "{name}"',
            '.Folder ""',
            f'.Type "{material_type}"',
            f'.Epsilon "{epsilon}"',
            f'.Mu "{mu}"',
            f'.Kappa "{conductivity}"',
            f'.TanD "{tan_delta}"',
            f'.Rho "{density}"',
        ]
        if colour is not None:
            r, g, b = colour
            lines.append(f'.Colour "{r}", "{g}", "{b}"')
        lines.append(".Create")
        self.add_history(f"material {name}", _with_block("Material", lines))

    # --- SAR (biomedical exposure) ---------------------------------------

    def add_power_loss_monitor(self, frequency: Any, name: str | None = None,
                               dimension: str = "Volume") -> str:
        """Add a power-loss-density monitor and return its result tree path.

        SAR needs the tree path of the *volume* power loss density result; pass
        the return value to :meth:`add_sar`.
        """
        monitor = name or f"power-loss (f={frequency})"
        self.add_monitor(monitor, "Powerloss", frequency, dimension=dimension)
        return power_loss_tree_path(monitor)

    def add_sar(
        self,
        label: str,
        average_weight_g: float = 10.0,
        volume: Sequence[Any] | None = None,
        power_loss_monitor: str | None = None,
        frequency: Any | None = None,
        options: Sequence[str] = (),
    ) -> None:
        """Create a SAR result with an averaging mass, for example 10 g tissue.

        Call this **after** the solver has produced a power-loss density
        monitor result, otherwise CST reports an invalid monitor.

        ``volume`` is ``(xmin, xmax, ymin, ymax, zmin, zmax)`` in mm.
        ``power_loss_monitor`` is the result tree path of the volume power loss
        density, e.g. the value returned by :meth:`add_power_loss_monitor`. When
        it is omitted but ``frequency`` is given, the standard path of a monitor
        named ``power-loss (f=<frequency>)`` is used. ``options`` are extra SAR
        ``SetOption`` strings such as ``"rescale 1.0"``.
        """
        if power_loss_monitor is None and frequency is not None:
            power_loss_monitor = power_loss_tree_path(f"power-loss (f={frequency})")
        lines = [
            ".Reset",
            f'.SetLabel "{label}"',
            f'.AverageWeight "{average_weight_g}"',
        ]
        if power_loss_monitor is not None:
            lines.append(f'.PowerlossMonitorTreePath "{power_loss_monitor}"')
        if volume is not None:
            x0, x1, y0, y1, z0, z1 = volume
            lines.append(f'.Volume "{x0}", "{x1}", "{y0}", "{y1}", "{z0}", "{z1}"')
        lines += [f'.SetOption "{option}"' for option in options]
        lines.append(".Create")
        self.add_history(f"SAR {label}", _with_block("SAR", lines))

    # --- solver extras ----------------------------------------------------

    def set_mesh_adaption(self, enabled: bool = True) -> None:
        """Turn adaptive mesh refinement on or off."""
        self.add_history("mesh adaption", _with_block(
            "Solver", [f'.MeshAdaption "{_vba_value(enabled)}"']))

    def set_pml_type(self, pml_type: str = "ConvPML") -> None:
        """Set the absorbing boundary type: ``ConvPML``, ``GTPML`` or ``SIBC``."""
        self.add_history("pml type", _with_block(
            "Solver", [f'.SetPMLType "{pml_type}"']))

    def activate_power_loss_monitor(self, enabled: bool = True) -> None:
        """Enable the 1D power-loss monitor (loss and SAR reports)."""
        self.add_history("power loss monitor", _with_block(
            "Solver", [f'.ActivatePowerLoss1DMonitor "{_vba_value(enabled)}"']))

    def set_frequency_samples(self, samples: int) -> None:
        """Set the number of frequency samples of the solver."""
        self.add_history("frequency samples", _with_block(
            "Solver", [f'.FrequencySamples "{samples}"']))

    # --- solver method, accuracy and excitation --------------------------

    def set_solver_method(self, mesh: str = "Hexahedral",
                          sweep: str = "General purpose") -> None:
        """Select the frequency-domain mesh and broadband sweep method.

        ``mesh`` is ``Hexahedral``, ``Tetrahedral`` or ``Surface`` (integral
        equation); ``sweep`` is ``General purpose``, ``Fast reduced order
        model`` or ``Discrete samples only`` (see ``FD_MESH_TYPES`` and
        ``FD_SWEEP_TYPES``). Pass ``""`` to keep a value unchanged.
        """
        code = f'.SetMethod "{mesh}", "{sweep}"'
        self.add_history(f"FD method {mesh}/{sweep}", _with_block("FDSolver", [code]))

    def set_fd_accuracy(self, accuracy: float = 1e-4) -> None:
        """Set the FD solver linear-system accuracy (range 1e-3 .. 1e-12)."""
        code = _with_block("FDSolver", [
            f'.AccuracyHex "{accuracy}"',
            f'.AccuracyTet "{accuracy}"',
            f'.AccuracySrf "{accuracy}"',
        ])
        self.add_history("FD accuracy", code)

    def set_reference_impedance(self, impedance: float | None = None) -> None:
        """Normalise S-parameters to a reference impedance.

        With ``impedance=None`` the S-parameters are normalised to the
        calculated impedance of the stimulation port; a number instead fixes
        the reference impedance.
        """
        lines = [f'.AutoNormImpedance "{_vba_value(impedance is not None)}"']
        if impedance is not None:
            lines.append(f'.NormingImpedance "{impedance}"')
        self.add_history("reference impedance", _with_block("FDSolver", lines))

    def set_stimulation(self, port: Any = "All", mode: Any = "All") -> None:
        """Choose the FD solver excitation (``FDSolver.Stimulation``).

        ``port`` is ``"All"``, ``"All+Floquet"``, ``"Plane Wave"``, a port
        number or ``"List"``; ``mode`` is the matching mode. Use
        ``set_stimulation("Plane Wave", 1)`` to excite a plane wave.
        """
        self.add_history(
            "stimulation",
            _with_block("FDSolver", [f'.Stimulation "{port}", "{mode}"']),
        )

    def set_time_domain(self, **settings: Any) -> None:
        """Set time-domain solver flags on the ``Solver`` object.

        Supported keys: ``mesh_adaption``, ``auto_norm_impedance``,
        ``norming_impedance``, ``use_distributed_computing``,
        ``hardware_acceleration``, ``mpi_parallelization``, ``tdr_computation``
        and ``use_double_precision``. An unknown key raises ``ValueError`` so a
        typo never silently does nothing.
        """
        names = {
            "mesh_adaption": "MeshAdaption",
            "auto_norm_impedance": "AutoNormImpedance",
            "norming_impedance": "NormingImpedance",
            "use_distributed_computing": "UseDistributedComputing",
            "hardware_acceleration": "HardwareAcceleration",
            "mpi_parallelization": "MPIParallelization",
            "tdr_computation": "TDRComputation",
            "use_double_precision": "UseDoublePrecision",
        }
        lines = []
        for key, value in settings.items():
            if key not in names:
                raise ValueError(f"unknown time-domain setting: {key!r}")
            lines.append(f'.{names[key]} "{_vba_value(value)}"')
        if lines:
            self.add_history("time domain settings", _with_block("Solver", lines))

    def add_parameter_sweep(
        self,
        sequence: str,
        parameter: str,
        start: float,
        stop: float,
        *,
        samples: int | None = None,
        step: float | None = None,
        values: Sequence[float] | None = None,
        logarithmic: bool = False,
    ) -> None:
        """Add a parameter-sweep sequence (one parameter, one sweep).

        Give exactly one of ``samples``, ``step`` or ``values`` to describe the
        variation of ``parameter`` between ``start`` and ``stop``. Run the
        sequences afterwards with :meth:`run_parameter_sweep`.
        """
        lines = [f'.AddSequence "{sequence}"']
        if values is not None:
            points = "; ".join(str(value) for value in values)
            lines.append(
                f'.AddParameter_ArbitraryPoints "{sequence}", "{parameter}", "{points}"')
        elif step is not None:
            lines.append(
                f'.AddParameter_Stepwidth "{sequence}", "{parameter}", '
                f'{start}, {stop}, {step}')
        else:
            count = samples if samples is not None else 11
            flag = "True" if logarithmic else "False"
            lines.append(
                f'.AddParameter_Samples "{sequence}", "{parameter}", '
                f'{start}, {stop}, {count}, {flag}')
        self.add_history(f"parameter sweep {sequence}", _with_block("ParameterSweep", lines))

    def run_parameter_sweep(self) -> None:
        """Run every enabled parameter-sweep sequence."""
        self.run_vba("ParameterSweep.Start")

    # --- monitors and images --------------------------------------------

    def add_monitor(
        self,
        name: str,
        field_type: str,
        frequency: Any,
        domain: str = "Frequency",
        dimension: str | None = None,
    ) -> None:
        """Add a field monitor.

        ``field_type`` is one of ``Efield``, ``Hfield``, ``Farfield``,
        ``Powerflow``, ``Surfacecurrent`` and so on. ``domain`` is
        ``Frequency`` or ``Time``. ``dimension`` is ``Volume``, ``Surface``
        or ``Point``; it is left out for far fields.
        """
        lines = [".Reset", f".Name({_vba_value(name)})"]
        if dimension:
            lines.append(f".Dimension({_vba_value(dimension)})")
        lines += [
            f".Domain({_vba_value(domain)})",
            f".FieldType({_vba_value(field_type)})",
            f".Frequency({_vba_value(frequency)})",
            ".Create",
        ]
        self.add_history(f"monitor {name}", _with_block("Monitor", lines))

    def add_farfield_monitor(self, frequency: Any, name: str | None = None) -> None:
        """Add a far-field monitor at one frequency."""
        self.add_monitor(name or f"farfield (f={frequency})", "Farfield", frequency)

    def add_field_monitor(self, kind: str, frequency: Any, name: str | None = None) -> None:
        """Add an E-field or H-field monitor. ``kind`` is ``Efield`` or ``Hfield``."""
        self.add_monitor(
            name or f"{kind.lower()} (f={frequency})", kind, frequency, dimension="Volume"
        )

    def export_image(self, path: str | os.PathLike, width: int = 1200, height: int = 900) -> None:
        """Save a PNG of the current 3D view."""
        self.run_vba(f'Plot.ExportImage "{Path(path).resolve()}", {width}, {height}')

    def export_view(
        self,
        path: str | os.PathLike,
        view: str = "Top",
        width: int = 1200,
        height: int = 900,
    ) -> None:
        """Save a PNG of a predefined view.

        Valid views are ``Top``, ``Bottom``, ``Front``, ``Back``, ``Left``,
        ``Right``, ``Perspective`` and ``Nearest Axis``.
        """
        body = (
            f'Plot.RestoreView "{view}"\n'
            "Plot.ZoomToStructure\n"
            f'Plot.ExportImage "{Path(path).resolve()}", {width}, {height}'
        )
        self.run_vba(body)

    def export_all_views(
        self,
        out_dir: str | os.PathLike,
        prefix: str = "view",
        width: int = 1400,
        height: int = 1050,
        views: Sequence[str] = VIEWS,
        zoom: bool = True,
    ) -> list[Path]:
        """Save one PNG for every view in ``views`` (default: all of ``VIEWS``).

        Each view is also zoomed to the structure so the object fills the
        image. Returns the list of written files.
        """
        folder = Path(out_dir)
        folder.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for view in views:
            slug = view.lower().replace(" ", "_")
            path = folder / f"{prefix}_{slug}.png"
            body = [f'Plot.RestoreView "{view}"']
            if zoom:
                body.append("Plot.ZoomToStructure")
            body.append(f'Plot.ExportImage "{path.resolve()}", {width}, {height}')
            self.run_vba("\n".join(body))
            written.append(path)
        return written

    # --- curves (2D sketch geometry) ------------------------------------

    def new_curve(self, name: str) -> None:
        """Create an empty curve container that can hold curve items."""
        self.add_history(f"curve {name}", f'Curve.NewCurve "{name}"')

    def delete_curve(self, name: str) -> None:
        """Delete a curve and every item it contains."""
        self.add_history(f"delete curve {name}", f'Curve.DeleteCurve "{name}"')

    def rename_curve(self, old: str, new: str) -> None:
        """Rename a curve."""
        self.add_history(f"rename curve {old}", f'Curve.RenameCurve "{old}", "{new}"')

    def define_line(self, name: str, curve: str, x1: Any, y1: Any,
                    x2: Any, y2: Any) -> None:
        """Add a 2D line between (x1, y1) and (x2, y2) to ``curve``."""
        code = _with_block("Line", [
            ".Reset", f'.Name "{name}"', f'.Curve "{curve}"',
            f'.X1 "{x1}"', f'.Y1 "{y1}"', f'.X2 "{x2}"', f'.Y2 "{y2}"', ".Create",
        ])
        self.add_history(f"line {name}", code)

    def define_arc(self, name: str, curve: str, center: Sequence[Any],
                   start: Sequence[Any], end: Sequence[Any] | None = None, *,
                   angle: Any = 0.0, use_angle: bool = False,
                   orientation: str = "CounterClockwise", segments: int = 0) -> None:
        """Add an arc to ``curve`` (end point or ``angle`` with ``use_angle``)."""
        lines = [
            ".Reset", f'.Name "{name}"', f'.Curve "{curve}"',
            f'.Orientation "{orientation}"',
            f'.Xcenter "{center[0]}"', f'.Ycenter "{center[1]}"',
            f'.X1 "{start[0]}"', f'.Y1 "{start[1]}"',
        ]
        if use_angle:
            lines += [f'.Angle "{angle}"', '.UseAngle "True"']
        else:
            if end is None:
                raise ValueError("define_arc needs an end point or use_angle=True")
            lines += [f'.X2 "{end[0]}"', f'.Y2 "{end[1]}"', '.UseAngle "False"']
        lines += [f'.Segments "{int(segments)}"', ".Create"]
        self.add_history(f"arc {name}", _with_block("Arc", lines))

    def define_circle(self, name: str, curve: str, center: Sequence[Any],
                      radius: Any, *, segments: int = 0) -> None:
        """Add a full circle to ``curve``."""
        code = _with_block("Circle", [
            ".Reset", f'.Name "{name}"', f'.Curve "{curve}"', f'.Radius "{radius}"',
            f'.Xcenter "{center[0]}"', f'.Ycenter "{center[1]}"',
            f'.Segments "{int(segments)}"', ".Create",
        ])
        self.add_history(f"circle {name}", code)

    def define_rectangle(self, name: str, curve: str, x_range: Sequence[Any],
                         y_range: Sequence[Any]) -> None:
        """Add a rectangle to ``curve``."""
        code = _with_block("Rectangle", [
            ".Reset", f'.Name "{name}"', f'.Curve "{curve}"',
            f'.Xrange "{x_range[0]}", "{x_range[1]}"',
            f'.Yrange "{y_range[0]}", "{y_range[1]}"', ".Create",
        ])
        self.add_history(f"rectangle {name}", code)

    def define_ellipse(self, name: str, curve: str, center: Sequence[Any],
                       x_radius: Any, y_radius: Any, *, segments: int = 0) -> None:
        """Add an ellipse to ``curve``."""
        code = _with_block("Ellipse", [
            ".Reset", f'.Name "{name}"', f'.Curve "{curve}"',
            f'.XRadius "{x_radius}"', f'.YRadius "{y_radius}"',
            f'.Xcenter "{center[0]}"', f'.Ycenter "{center[1]}"',
            f'.Segments "{int(segments)}"', ".Create",
        ])
        self.add_history(f"ellipse {name}", code)

    def define_polygon(self, name: str, curve: str, points: Sequence[Sequence[Any]],
                       *, relative: bool = False) -> None:
        """Add a polygon (first point then line segments) to ``curve``."""
        lines = [".Reset", f'.Name "{name}"', f'.Curve "{curve}"']
        first, *rest = points
        lines.append(f'.Point "{first[0]}", "{first[1]}"')
        step = "RLine" if relative else "LineTo"
        lines += [f'.{step} "{p[0]}", "{p[1]}"' for p in rest]
        lines.append(".Create")
        self.add_history(f"polygon {name}", _with_block("Polygon", lines))

    def define_spline(self, name: str, curve: str, points: Sequence[Sequence[Any]],
                      *, relative: bool = False) -> None:
        """Add a spline through ``points`` to ``curve``."""
        lines = [".Reset", f'.Name "{name}"', f'.Curve "{curve}"']
        first, *rest = points
        lines.append(f'.Point "{first[0]}", "{first[1]}"')
        step = "RLine" if relative else "LineTo"
        lines += [f'.{step} "{p[0]}", "{p[1]}"' for p in rest]
        lines.append(".Create")
        self.add_history(f"spline {name}", _with_block("Spline", lines))

    # --- solids from curves (extrude, rotate, sweep, cover, loft) -------

    def extrude_curve(self, name: str, curve_item: str, thickness: Any, *,
                      component: str = "unitcell", material: str = "Vacuum",
                      twist: Any = 0.0, taper: Any = 0.0) -> None:
        """Extrude the curve item ``"curve:item"`` along +z by ``thickness``.

        A negative ``thickness`` builds a 2D sheet instead of a solid.
        """
        code = _with_block("ExtrudeCurve", [
            ".Reset", f'.Name "{name}"', f'.Component "{component}"',
            f'.Material "{material}"', f'.Thickness "{thickness}"',
            f'.Twistangle "{twist}"', f'.Taperangle "{taper}"',
            f'.Curve "{curve_item}"', ".Create",
        ])
        self.add_history(f"extrude curve {name}", code)

    def extrude(self, name: str, height: Any, *, mode: str = "pointlist",
                points: Sequence[Sequence[Any]] | None = None,
                component: str = "unitcell", material: str = "Vacuum",
                taper: Any = 0.0, twist: Any = 0.0) -> None:
        """Extrude a polygon (``mode="pointlist"``) or picked faces (``"Picks"``).

        ``points`` are the 2D profile vertices in the working plane.
        """
        lines = [
            ".Reset", f'.Name "{name}"', f'.Component "{component}"',
            f'.Material "{material}"', f'.Mode "{mode}"', f'.Height "{height}"',
        ]
        if points:
            first, *rest = points
            lines.append(f'.Point "{first[0]}", "{first[1]}"')
            lines += [f'.LineTo "{p[0]}", "{p[1]}"' for p in rest]
        lines += [
            f'.Taper "{taper}"', f'.Twist "{twist}"', '.UsePicksForHeight "False"',
            '.DeleteBaseFaceSolid "False"', '.ClearPickedFace "True"', ".Create",
        ]
        self.add_history(f"extrude {name}", _with_block("Extrude", lines))

    def create_rotated(self, name: str, angle: Any, *,
                       mode: str = "pointlist",
                       points: Sequence[Sequence[Any]] | None = None,
                       origin: Sequence[Any] = (0, 0, 0),
                       rvector: Sequence[Any] = (0, 0, 1),
                       height: Any = 0.0, radius_ratio: Any = 1.0, n_steps: int = 0,
                       component: str = "unitcell", material: str = "Vacuum") -> None:
        """Rotate a profile (``points``) or picked faces into a solid of revolution."""
        lines = [
            ".Reset", f'.Name "{name}"', f'.Component "{component}"',
            f'.Material "{material}"', f'.Mode "{mode}"', f'.Angle "{angle}"',
            f'.Origin "{origin[0]}", "{origin[1]}", "{origin[2]}"',
            f'.Rvector "{rvector[0]}", "{rvector[1]}", "{rvector[2]}"',
        ]
        if points:
            first, *rest = points
            lines.append(f'.Point "{first[0]}", "{first[1]}"')
            lines += [f'.LineTo "{p[0]}", "{p[1]}"' for p in rest]
        lines += [
            f'.Height "{height}"', f'.RadiusRatio "{radius_ratio}"',
            f'.NSteps "{int(n_steps)}"', '.DeleteBaseFaceSolid "False"',
            '.ClearPickedFace "True"', ".Create",
        ]
        self.add_history(f"rotate {name}", _with_block("Rotate", lines))

    def sweep_curve(self, name: str, path: str, profile: str, *,
                    component: str = "unitcell", material: str = "Vacuum",
                    twist: Any = 0.0, taper: Any = 0.0) -> None:
        """Sweep the curve item ``profile`` (``"curve:item"``) along ``path``."""
        code = _with_block("SweepCurve", [
            ".Reset", f'.Name "{name}"', f'.Component "{component}"',
            f'.Material "{material}"', f'.Twistangle "{twist}"',
            f'.Taperangle "{taper}"', '.ProjectProfileToPathAdvanced "True"',
            f'.Path "{path}"', f'.Curve "{profile}"', ".Create",
        ])
        self.add_history(f"sweep {name}", code)

    def cover_curve(self, name: str, curve_item: str, *,
                    component: str = "unitcell", material: str = "Vacuum") -> None:
        """Fill a closed curve item into a sheet solid."""
        code = _with_block("CoverCurve", [
            ".Reset", f'.Name "{name}"', f'.Component "{component}"',
            f'.Material "{material}"', f'.Curve "{curve_item}"', ".Create",
        ])
        self.add_history(f"cover {name}", code)

    def loft(self, name: str, *, component: str = "unitcell",
             material: str = "Vacuum", tangency: Any = 0.25) -> None:
        """Loft the currently picked curves into a solid (``CreateNew``)."""
        code = _with_block("Loft", [
            ".Reset", f'.Name "{name}"', f'.Component "{component}"',
            f'.Material "{material}"', f'.Tangency "{tangency}"', ".CreateNew",
        ])
        self.add_history(f"loft {name}", code)

    # --- working coordinate system and anchor points --------------------

    def wcs(self, mode: str = "local") -> None:
        """Switch the working coordinate system to ``local`` or ``global``."""
        self.run_vba(f'WCS.ActivateWCS "{mode}"')

    def wcs_store(self, name: str) -> None:
        """Store the current local coordinate system under ``name``."""
        self.run_vba(f'WCS.Store "{name}"')

    def wcs_restore(self, name: str) -> None:
        """Restore a stored local coordinate system."""
        self.run_vba(f'WCS.Restore "{name}"')

    def wcs_delete(self, name: str) -> None:
        """Delete a stored local coordinate system."""
        self.run_vba(f'WCS.Delete "{name}"')

    def wcs_set_origin(self, x: Any, y: Any, z: Any) -> None:
        """Move the origin of the working coordinate system."""
        self.run_vba(f'WCS.SetOrigin "{x}", "{y}", "{z}"')

    def wcs_set_normal(self, x: Any, y: Any, z: Any) -> None:
        """Set the normal (w axis) of the working coordinate system."""
        self.run_vba(f'WCS.SetNormal "{x}", "{y}", "{z}"')

    def wcs_set_uvector(self, x: Any, y: Any, z: Any) -> None:
        """Set the u axis of the working coordinate system."""
        self.run_vba(f'WCS.SetUVector "{x}", "{y}", "{z}"')

    def wcs_rotate(self, axis: str, angle: Any) -> None:
        """Rotate the working coordinate system about ``u``, ``v`` or ``w``."""
        self.run_vba(f'WCS.RotateWCS "{axis}", "{angle}"')

    def wcs_move(self, mode: str, du: Any, dv: Any, dw: Any) -> None:
        """Shift the working coordinate system in ``local`` or ``global`` axes."""
        self.run_vba(f'WCS.MoveWCS "{mode}", "{du}", "{dv}", "{dw}"')

    def define_anchor_point(self, name: str, position: Sequence[Any],
                            normal: Sequence[Any] = (0, 0, 1),
                            uvector: Sequence[Any] = (1, 0, 0)) -> None:
        """Define a named anchor point (used to assemble components)."""
        args = (position[0], position[1], position[2], normal[0], normal[1],
                normal[2], uvector[0], uvector[1], uvector[2])
        joined = ", ".join(f'"{value}"' for value in args)
        self.run_vba(f'Anchorpoint.Define "{name}", {joined}')

    # --- CAD / mesh import and export -----------------------------------

    def _read_cad(self, object_name: str, path: str | os.PathLike, caption: str,
                  settings: Mapping[str, Any]) -> None:
        """Emit ``With <cad object> ... .Read`` to import a file."""
        lines = [".Reset", f'.FileName "{Path(path).resolve()}"']
        lines += [f'.{key} "{value}"' for key, value in settings.items()]
        lines.append(".Read")
        self.add_history(caption, _with_block(object_name, lines))

    def _write_cad(self, object_name: str, path: str | os.PathLike, caption: str,
                   settings: Mapping[str, Any], write: str | None = None) -> None:
        """Emit ``With <cad object> ... .Write`` to export a file."""
        lines = [".Reset", f'.FileName "{Path(path).resolve()}"']
        lines += [f'.{key} "{value}"' for key, value in settings.items()]
        lines.append(f".Write {write}" if write else ".Write")
        self.add_history(caption, _with_block(object_name, lines))

    def import_step(self, path: str | os.PathLike, *, id: int = 1,
                    version: str = "", healing: bool = False,
                    import_curves: bool = False, scale_to_unit: bool = False) -> None:
        """Import a STEP file (``.stp`` / ``.step``)."""
        self._read_cad("STEP", path, f"import STEP {Path(path).name}", {
            "Id": id, "Version": version, "Healing": _vba_value(healing),
            "ImportCurves": _vba_value(import_curves),
            "ScaleToUnit": _vba_value(scale_to_unit),
        })

    def import_iges(self, path: str | os.PathLike, *, id: int = 1, name: str = "",
                    healing: bool = False, import_curves: bool = False) -> None:
        """Import an IGES file (``.igs``)."""
        self._read_cad("IGES", path, f"import IGES {Path(path).name}", {
            "Id": id, "Name": name, "Healing": _vba_value(healing),
            "ImportCurves": _vba_value(import_curves),
        })

    def import_sat(self, path: str | os.PathLike, *,
                   import_curves: bool = False) -> None:
        """Import an ACIS SAT file."""
        self._read_cad("SAT", path, f"import SAT {Path(path).name}", {
            "ImportCurves": _vba_value(import_curves),
        })

    def import_dxf(self, path: str | os.PathLike, *, id: int = 1,
                   as_curves: bool = False, preserve_holes: bool = True,
                   close_shapes: bool = True) -> None:
        """Import a DXF layout file."""
        self._read_cad("DXF", path, f"import DXF {Path(path).name}", {
            "Id": id, "AsCurves": _vba_value(as_curves),
            "PreserveHoles": _vba_value(preserve_holes),
            "CloseShapes": _vba_value(close_shapes),
        })

    def import_gdsii(self, path: str | os.PathLike, *, id: int = 1,
                     structure: str = "", as_curves: bool = False) -> None:
        """Import a GDSII layout file (``.gds``)."""
        self._read_cad("GDSII", path, f"import GDSII {Path(path).name}", {
            "Id": id, "SelectedStructure": structure,
            "AsCurves": _vba_value(as_curves),
        })

    def import_gerber(self, path: str | os.PathLike, *, aperture_file: str = "",
                      close_shapes: bool = True) -> None:
        """Import a Gerber file (optionally with an aperture file)."""
        self._read_cad("GERBER", path, f"import Gerber {Path(path).name}", {
            "ApertureFileName": aperture_file,
            "CloseShapes": _vba_value(close_shapes),
        })

    def import_stl(self, path: str | os.PathLike, *, id: int = 1, name: str = "",
                   component: str = "default") -> None:
        """Import an STL mesh file."""
        self._read_cad("STL", path, f"import STL {Path(path).name}", {
            "Id": id, "Name": name, "Component": component,
        })

    def import_obj(self, path: str | os.PathLike, *, id: int = 1, name: str = "",
                   scale_factor: Any = 1.0) -> None:
        """Import a Wavefront OBJ file."""
        self._read_cad("OBJ", path, f"import OBJ {Path(path).name}", {
            "Id": id, "Name": name, "ScaleFactor": scale_factor,
        })

    def import_nastran(self, path: str | os.PathLike, *, id: int = 1,
                       import_as_solids: bool = False) -> None:
        """Import a NASTRAN mesh file."""
        self._read_cad("NASTRAN", path, f"import NASTRAN {Path(path).name}", {
            "Id": id, "ImportAsSolids": _vba_value(import_as_solids),
        })

    def export_sat(self, path: str | os.PathLike, name: str) -> None:
        """Export the shape ``name`` (``component:solid``) to ACIS SAT."""
        self._write_cad("SAT", path, f"export SAT {Path(path).name}", {},
                        write=f'"{name}"')

    def export_iges(self, path: str | os.PathLike, name: str) -> None:
        """Export the shape ``name`` to IGES."""
        self._write_cad("IGES", path, f"export IGES {Path(path).name}", {},
                        write=f'"{name}"')

    def export_stl(self, path: str | os.PathLike, name: str, *,
                   component: str = "default") -> None:
        """Export the shape ``name`` to an STL mesh file."""
        code = _with_block("STL", [
            ".Reset", f'.FileName "{Path(path).resolve()}"', f'.Name "{name}"',
            f'.Component "{component}"', '.ExportFromActiveCoordinateSystem "True"',
            ".WriteCAD",
        ])
        self.add_history(f"export STL {Path(path).name}", code)

    def export_dxf(self, path: str | os.PathLike, *, export_curves: bool = False,
                   hole_connection: bool = False) -> None:
        """Export the model layout to a DXF file."""
        self._write_cad("DXF", path, f"export DXF {Path(path).name}", {
            "ExportCurves": _vba_value(export_curves),
            "ExportHoleConnection": _vba_value(hole_connection),
        })

    # --- materials: anisotropic, ohmic sheet, library -------------------

    def add_anisotropic_material(
        self,
        name: str,
        *,
        epsilon: Sequence[Any] = (1.0, 1.0, 1.0),
        mu: Sequence[Any] = (1.0, 1.0, 1.0),
        conductivity: Any = 0.0,
        density: Any = 0.0,
        material_type: str = "Anisotropic",
    ) -> None:
        """Define an anisotropic (or tensor) material with diagonal epsilon / mu."""
        ex, ey, ez = epsilon
        mx, my, mz = mu
        lines = [
            ".Reset", f'.Name "{name}"', '.Folder ""', f'.Type "{material_type}"',
            f'.EpsilonX "{ex}"', f'.EpsilonY "{ey}"', f'.EpsilonZ "{ez}"',
            f'.MuX "{mx}"', f'.MuY "{my}"', f'.MuZ "{mz}"',
            f'.Kappa "{conductivity}"', f'.Rho "{density}"', ".Create",
        ]
        self.add_history(f"material {name}", _with_block("Material", lines))

    def add_ohmic_sheet(self, name: str, resistance: Any, reactance: Any = 0.0,
                        frequency: Any = 1.0, *, density: Any = 0.0) -> None:
        """Define an ohmic sheet material from a surface impedance [Ohm]."""
        lines = [
            ".Reset", f'.Name "{name}"', '.Folder ""', '.Type "Ohmic sheet"',
            f'.OhmicSheetImpedance "{resistance}", "{reactance}"',
            f'.OhmicSheetFreq "{frequency}"', f'.Rho "{density}"', ".Create",
        ]
        self.add_history(f"ohmic sheet {name}", _with_block("Material", lines))

    def set_material_appearance(self, name: str, *, colour: Sequence[Any] | None = None,
                                transparency: Any | None = None,
                                wireframe: bool | None = None) -> None:
        """Change the display of a material (colour, transparency, wireframe)."""
        lines = [f'.Name "{name}"', ".Modify"]
        if colour is not None:
            lines.insert(1, f'.Color "{colour[0]}", "{colour[1]}", "{colour[2]}"')
        if transparency is not None:
            lines.insert(-1, f'.Transparency "{transparency}"')
        if wireframe is not None:
            lines.insert(-1, f'.Wireframe "{_vba_value(wireframe)}"')
        self.add_history(f"material appearance {name}", _with_block("Material", lines))

    # --- global mesh settings -------------------------------------------

    def set_mesh_settings(self, **settings: Any) -> None:
        """Set global mesh settings through the ``Mesh`` object.

        The keyword names are the CST ``Mesh`` method names, for example
        ``set_mesh_settings(LinesPerWavelength=25, RatioLimit=15, Automesh=True,
        MeshType="HexahedralFIT")``.
        """
        if not settings:
            return
        lines = [f'.{key} "{value}"' for key, value in settings.items()]
        self.add_history("mesh settings", _with_block("Mesh", lines))

    # --- discrete elements, extra sources and monitors ------------------

    def add_lumped_element(self, name: str, point1: Sequence[Any],
                           point2: Sequence[Any], *, kind: str = "rlcserial",
                           R: Any = 50.0, L: Any = 0.0, C: Any = 0.0,
                           invert: bool = False, monitor: bool = True,
                           radius: Any = 0.0, folder: str = "") -> None:
        """Add a lumped element (SMD / via / discrete component) of type ``kind``.

        ``kind`` is a ``LumpedElement.SetType`` key: ``rlcserial``,
        ``rlcparallel``, ``short``, ``open``, ``diode`` or ``spicecircuit``.
        """
        x1, y1, z1 = point1
        x2, y2, z2 = point2
        lines = [
            ".Reset", f'.SetType "{kind}"', f'.SetName "{name}"',
            f'.Folder "{folder}"', f'.SetR "{R}"', f'.SetL "{L}"', f'.SetC "{C}"',
            f'.SetP1 "False", "{x1}", "{y1}", "{z1}"',
            f'.SetP2 "False", "{x2}", "{y2}", "{z2}"',
            f'.SetInvert "{_vba_value(invert)}"',
            f'.SetMonitor "{_vba_value(monitor)}"', f'.SetRadius "{radius}"', ".Create",
        ]
        self.add_history(f"lumped element {name}", _with_block("LumpedElement", lines))

    def add_current_port(self, name: str, solid: str, face_id: int,
                         value: Any = 0.0, *, value_type: str = "Current") -> None:
        """Add a current port on one face of a solid (``Current`` or ``Potential``)."""
        code = _with_block("CurrentPort", [
            ".Reset", f'.Name "{name}"', f'.Face "{solid}", "{int(face_id)}"',
            f'.Value "{value}"', f'.ValueType "{value_type}"', ".Create",
        ])
        self.add_history(f"current port {name}", code)

    def add_voltage_wire(self, name: str, curve_item: str, voltage: Any = 1.0,
                         phase: Any = 0.0) -> None:
        """Add a voltage source along a curve item (``"curve:item"``)."""
        code = _with_block("VoltageWire", [
            ".Reset", f'.Name "{name}"', '.Type "CurvePath"', f'.Voltage "{voltage}"',
            f'.Phase "{phase}"', f'.Curve "{curve_item}"', ".Add",
        ])
        self.add_history(f"voltage wire {name}", code)

    def add_potential(self, name: str, value: Any,
                      faces: Sequence[Sequence[Any]], *, value_type: str = "Fixed",
                      phase: Any = 0.0) -> None:
        """Assign a (fixed or floating) electric potential to picked faces.

        ``faces`` is a sequence of ``(solid, face_id)`` pairs.
        """
        lines = [".Reset", f'.Name "{name}"', f'.Value "{value}"', f'.Phase "{phase}"']
        for solid, face_id in faces:
            lines.append(f'.AddFace "{solid}", "{int(face_id)}"')
        lines += [f'.Type "{value_type}"', ".Create"]
        self.add_history(f"potential {name}", _with_block("Potential", lines))

    def add_probe(self, name: str, field: str = "efield",
                  position: Sequence[Any] = (0, 0, 0), *,
                  coordinate_system: str = "Cartesian",
                  orientation: str = "x") -> None:
        """Add a field probe.

        ``field`` is ``efield``, ``hfield``, ``efarfield``, ``hfarfield`` or
        ``rcs``; for farfield probes use three spherical positions instead.
        """
        code = _with_block("Probe", [
            ".Reset", f'.Name "{name}"', ".AutoLabel \"1\"", f'.Field "{field}"',
            f'.SetCoordinateSystemType "{coordinate_system}"',
            f'.Xpos "{position[0]}"', f'.Ypos "{position[1]}"', f'.Zpos "{position[2]}"',
            f'.Orientation "{orientation}"', ".Create",
        ])
        self.add_history(f"probe {name}", code)

    def add_time_monitor(self, name: str, field_type: str = "E-Field", *,
                         t_start: Any = 0.0, t_step: Any = 0.0, t_end: Any = 0.0,
                         use_end: bool = False) -> None:
        """Add a transient time monitor for ``field_type`` (for example ``E-Field``)."""
        code = _with_block("TimeMonitor", [
            ".Reset", f'.Name "{name}"', f'.FieldType "{field_type}"',
            f'.Tstart "{t_start}"', f'.Tstep "{t_step}"', f'.Tend "{t_end}"',
            f'.UseTend "{_vba_value(use_end)}"', ".Create",
        ])
        self.add_history(f"time monitor {name}", code)

    def add_current_monitor(self, name: str, curve_item: str, *,
                            invert: bool = False) -> None:
        """Monitor the current along a curve item (``"curve:item"``)."""
        code = _with_block("CurrentMonitor", [
            ".Reset", f'.Name "{name}"', f'.Curve "{curve_item}"',
            f'.InvertOrientation "{_vba_value(invert)}"', ".Create",
        ])
        self.add_history(f"current monitor {name}", code)

    def add_voltage_monitor(self, name: str, curve_item: str, *,
                            invert: bool = False) -> None:
        """Monitor the voltage along a curve item (``"curve:item"``)."""
        code = _with_block("VoltageMonitor", [
            ".Reset", f'.Name "{name}"', f'.Curve "{curve_item}"',
            f'.InvertOrientation "{_vba_value(invert)}"', ".Create",
        ])
        self.add_history(f"voltage monitor {name}", code)

    # --- solver breadth (LF, EM, thermal, asymptotic, eigen) ------------

    def configure_vba_object(self, object_name: str, *, caption: str | None = None,
                             reset: bool = True, create: bool = False,
                             settings: Mapping[str, Any] | None = None,
                             extra: Sequence[str] = (),
                             component: str | None = None,
                             material: str | None = None) -> None:
        """Emit ``With <object_name> ... End With`` for *any* CST VBA object.

        This is the generic escape hatch for objects or methods without a
        dedicated wrapper here. ``settings`` become ``.Key "value"`` lines in
        order, ``extra`` are raw VBA lines, ``create`` appends ``.Create``.
        """
        lines = [".Reset"] if reset else []
        if component is not None:
            lines.append(f'.Component "{component}"')
        if material is not None:
            lines.append(f'.Material "{material}"')
        for key, value in (settings or {}).items():
            lines.append(f'.{key} "{value}"')
        lines.extend(extra)
        if create:
            lines.append(".Create")
        self.add_history(caption or f"{object_name} settings",
                         _with_block(object_name, lines))

    def _solver_block(self, object_name: str, caption: str,
                      lines: Sequence[str]) -> None:
        """Add a solver-settings history entry (no-op when ``lines`` is empty)."""
        if lines:
            self.add_history(caption, _with_block(object_name, lines))

    def set_eigenmode_solver(self, *, modes: int | None = None,
                             method: str | None = None, mesh: str | None = None,
                             frequency: Any | None = None,
                             consider_static: bool = False, **settings: Any) -> None:
        """Configure the ``EigenmodeSolver``.

        ``method`` is ``AKS`` / ``JDM`` / ``Automatic`` / ``Classical (Lossless)``
        / ``General (Lossy)``; ``mesh`` is ``Hex`` or ``Tet``.
        """
        lines = [".Reset"]
        if modes is not None:
            lines.append(f'.SetNumberOfModes "{int(modes)}"')
        if method is not None or mesh is not None:
            lines.append(f'.SetMethodType "{method or ""}", "{mesh or ""}"')
        if frequency is not None:
            lines.append(f'.SetFrequencyTarget "True", "{frequency}"')
        if consider_static:
            lines.append('.SetConsiderStaticModes "True"')
        lines += [f'.{key} "{value}"' for key, value in settings.items()]
        self._solver_block("EigenmodeSolver", "eigenmode solver", lines)

    def set_asymptotic_solver(self, *, solver_type: str = "SBR",
                              mode: str = "MONOSTATIC_SCATTERING",
                              accuracy: str = "MEDIUM", **settings: Any) -> None:
        """Configure the ``AsymptoticSolver`` (SBR / raytubes, RCS mode, accuracy)."""
        lines = [
            f'.SetSolverType "{solver_type}"', f'.SetSolverMode "{mode}"',
            f'.SetAccuracyLevel "{accuracy}"',
        ]
        lines += [f'.{key} "{value}"' for key, value in settings.items()]
        self._solver_block("AsymptoticSolver", "asymptotic solver", lines)

    def set_electrostatic_solver(self, *, accuracy: Any | None = None,
                                 method: str | None = None,
                                 calculate_capacitance: bool = False,
                                 **settings: Any) -> None:
        """Configure the ``EStaticSolver`` (electrostatics / capacitance matrix)."""
        lines = [".Reset"]
        if accuracy is not None:
            lines.append(f'.Accuracy "{accuracy}"')
        if method is not None:
            lines.append(f'.Method "{method}"')
        if calculate_capacitance:
            lines.append('.CalcCapacitanceMatrix "True"')
        lines += [f'.{key} "{value}"' for key, value in settings.items()]
        self._solver_block("EStaticSolver", "electrostatic solver", lines)

    def set_lf_solver(self, *, equation_type: str | None = None,
                      accuracy: Any | None = None, full_wave: bool = False,
                      frequencies: Sequence[Any] | None = None,
                      **settings: Any) -> None:
        """Configure the ``LFSolver`` (LF frequency domain: MQS / Fullwave)."""
        lines = [".Reset"]
        if equation_type is not None:
            lines.append(f'.EquationType "{equation_type}"')
        if accuracy is not None:
            lines.append(f'.Accuracy "{accuracy}"')
        if full_wave:
            lines.append('.UseFullWaveCalculation "True"')
        for frequency in frequencies or ():
            lines.append(f'.AddFrequency "{frequency}"')
        lines += [f'.{key} "{value}"' for key, value in settings.items()]
        self._solver_block("LFSolver", "LF solver", lines)

    def set_magnetostatic_solver(self, **settings: Any) -> None:
        """Configure the ``MStaticSolver`` (keyword = CST method name)."""
        self._solver_block("MStaticSolver", "magnetostatic solver",
                           [f'.{key} "{value}"'
                            for key, value in settings.items()])

    def set_stationary_current_solver(self, **settings: Any) -> None:
        """Configure the ``StationaryCurrentSolver`` (keyword = CST method name)."""
        self._solver_block("StationaryCurrentSolver", "stationary current solver",
                           [f'.{key} "{value}"'
                            for key, value in settings.items()])

    def set_thermal_solver(self, **settings: Any) -> None:
        """Configure the ``ThermalSolver`` (keyword = CST method name)."""
        self._solver_block("ThermalSolver", "thermal solver",
                           [f'.{key} "{value}"'
                            for key, value in settings.items()])

    def set_pic_solver(self, *, frequency_range: Sequence[Any] | None = None,
                       simulation_time: Any | None = None, **settings: Any) -> None:
        """Configure the ``PICSolver`` (particle-in-cell / multipacting)."""
        lines = [".Reset"]
        if frequency_range is not None:
            lines.append(
                f'.FrequencyRange "{frequency_range[0]}", "{frequency_range[1]}"')
        if simulation_time is not None:
            lines.append(f'.SimulationTime "{simulation_time}"')
        lines += [f'.{key} "{value}"' for key, value in settings.items()]
        self._solver_block("PICSolver", "PIC solver", lines)

    def set_layer_stacking(self, **settings: Any) -> None:
        """Configure the multilayer ``LayerStacking`` solver (keyword = CST method name)."""
        self._solver_block("LayerStacking", "layer stacking",
                           [f'.{key} "{value}"'
                            for key, value in settings.items()])

    def set_optimizer(self, **settings: Any) -> None:
        """Configure the ``Optimizer`` (algorithm, goals; keyword = CST method name)."""
        self._solver_block("Optimizer", "optimizer",
                           [f'.{key} "{value}"'
                            for key, value in settings.items()])

    def set_sensitivity_analysis(self, **settings: Any) -> None:
        """Configure the ``SensitivityAnalysis`` object (keyword = CST method name)."""
        self._solver_block("SensitivityAnalysis", "sensitivity analysis",
                           [f'.{key} "{value}"'
                            for key, value in settings.items()])

    # --- extra post-processing ------------------------------------------

    def calculate_vswr(self) -> None:
        """Start the VSWR post-processing calculation (``Solver``)."""
        self.run_vba("Solver.CalculateVSWR")

    def calculate_zy_matrices(self) -> None:
        """Start the Z / Y matrix post-processing calculation (``Solver``)."""
        self.run_vba("Solver.CalculateZandYMatrices")

    # --- post-processing objects ----------------------------------------

    def _create_item(self, object_name: str, caption: str,
                     lines: Sequence[str], *, create: bool = True,
                     reset: bool = True) -> None:
        """Add a ``With <object> ... End With`` history entry (``Create`` optional)."""
        body = ([".Reset"] if reset else []) + list(lines)
        if create:
            body.append(".Create")
        self.add_history(caption, _with_block(object_name, body))

    def add_farfield_array(self, *, x: Sequence[Any] | None = None,
                           y: Sequence[Any] | None = None,
                           z: Sequence[Any] | None = None,
                           array_type: str = "Rectangular") -> None:
        """Define a far-field array; each entry is ``(number, space, phase)``."""
        enabled = any(values is not None for values in (x, y, z))
        lines = [f'.UseArray "{_vba_value(enabled)}"', f'.Arraytype "{array_type}"']
        for axis, values in (("X", x), ("Y", y), ("Z", z)):
            if values is not None:
                lines.append(f'.{axis}Set "{values[0]}", "{values[1]}", "{values[2]}"')
        self.add_history("farfield array", _with_block("FarfieldArray", lines))

    def set_farfield_calculator(self, *, axes_type: str | None = None,
                                origin: str | None = None,
                                db_unit: str | None = None,
                                scale_linear: bool | None = None,
                                log_norm: Any | None = None,
                                **settings: Any) -> None:
        """Configure the ``FarfieldCalculator`` used by result templates."""
        lines = []
        if axes_type is not None:
            lines.append(f'.SetAxesType "{axes_type}"')
        if origin is not None:
            lines.append(f'.Origin "{origin}"')
        if scale_linear is not None:
            lines.append(f'.SetScaleLinear "{_vba_value(scale_linear)}"')
        if db_unit is not None:
            lines.append(f'.DBUnit "{db_unit}"')
        if log_norm is not None:
            lines.append(f'.SetLogNorm "{log_norm}"')
        lines += [f'.{key} "{value}"' for key, value in settings.items()]
        self.add_history("farfield calculator", _with_block("FarfieldCalculator", lines))

    def set_farfield_plot(self, *, theta_start: Any | None = None,
                          theta_end: Any | None = None, phi_start: Any | None = None,
                          phi_end: Any | None = None, vary: str | None = None,
                          step: Any | None = None, frequency: Any | None = None,
                          **settings: Any) -> None:
        """Configure the ``FarfieldPlot`` (angular range and frequency)."""
        lines = []
        if vary is not None:
            lines.append(f'.Vary "{vary}"')
        if theta_start is not None:
            lines.append(f'.SetThetaStart "{theta_start}"')
        if theta_end is not None:
            lines.append(f'.SetThetaEnd "{theta_end}"')
        if phi_start is not None:
            lines.append(f'.SetPhiStart "{phi_start}"')
        if phi_end is not None:
            lines.append(f'.SetPhiEnd "{phi_end}"')
        if step is not None:
            lines.append(f'.Step "{step}"')
        if frequency is not None:
            lines.append(f'.SetFrequency "{frequency}"')
        lines += [f'.{key} "{value}"' for key, value in settings.items()]
        self.add_history("farfield plot", _with_block("FarfieldPlot", lines))

    def export_farfield_source(self, path: str | os.PathLike, *,
                               broadband: bool = False) -> None:
        """Export the current far-field plot as a (broadband) far-field source."""
        target = Path(path).resolve()
        method = "ASCIIExportAsBroadbandSource" if broadband else "ASCIIExportAsSource"
        self.run_vba(f'FarfieldPlot.{method} "{target}"')

    def add_nearfield_scan(self, farfield_monitor: str, frequency: Any, *,
                           step: Any = 1.0, radius: Any = 1.0, height: Any = 0.0,
                           label: str = "") -> None:
        """Add a near-field (holographic) scan from a far-field monitor."""
        code = _with_block("NearfieldScan", [
            f'.FarfieldMonitor "{farfield_monitor}"', f'.Frequency "{frequency}"',
            f'.Step "{step}"', f'.Radius "{radius}"', f'.Height "{height}"',
            f'.Label "{label}"', ".Create",
        ])
        self.add_history("nearfield scan", code)

    def configure_ar_filter(self, *, kind: str = "s-parameter",
                            algorithm: str = "Basic",
                            first_time: Any | None = None, skip: int | None = None,
                            max_order: int | None = None,
                            window_length: Any | None = None,
                            max_freq: Any | None = None) -> None:
        """Configure the autoregressive (AR) filter for signal deconvolution."""
        lines = [f'.SetType "{kind}"', f'.SetAlgorithmType "{algorithm}"']
        if first_time is not None:
            lines.append(f'.SetFirstTime "{first_time}"')
        if skip is not None:
            lines.append(f'.SetSkip "{int(skip)}"')
        if max_order is not None:
            lines.append(f'.SetMaxOrder "{int(max_order)}"')
        if window_length is not None:
            lines.append(f'.SetWindowLength "{window_length}"')
        if max_freq is not None:
            lines.append(f'.SetMaxFrq "{max_freq}"')
        self.add_history("AR filter", _with_block("Arfilter", lines))

    def initialize_qfactor(self, *, h_field: str | None = None,
                           use_new_method: bool = True,
                           save_3d_data: bool = False) -> None:
        """Initialise the ``QFactor`` post-processing from a loss-free H-field."""
        lines = [f'.UseNewMethod "{_vba_value(use_new_method)}"',
                 f'.Save3DData "{_vba_value(save_3d_data)}"']
        if h_field is not None:
            lines.append(f'.SetHField "{h_field}"')
        self.add_history("Q-factor", _with_block("QFactor", lines))

    def extract_spice_network(self, *, method: str = "TransmissionLine",
                              **settings: Any) -> None:
        """Configure the ``NetworkParameterExtraction`` (SPICE / MOR) object."""
        lines = [f'.Method "{method}"']
        lines += [f'.{key} "{value}"' for key, value in settings.items()]
        self.add_history("network extraction",
                         _with_block("NetworkParameterExtraction", lines))

    def combine_results(self, **settings: Any) -> None:
        """Configure the ``CombineResults`` object (keyword = CST method name)."""
        lines = [f'.{key} "{value}"' for key, value in settings.items()]
        self.add_history("combine results", _with_block("CombineResults", lines))

    def add_result_0d(self, name: str, value: Any, tree_path: str, *,
                      title: str = "", label: str = "", unit: str = "",
                      complex_value: bool = False) -> None:
        """Create a 0D result (a single number) and add it to the result tree."""
        var = "res_" + name.replace(" ", "_")
        setter = (f'{var}.SetDataComplex "{value}"' if complex_value
                  else f'{var}.SetData "{value}"')
        body = "\n".join([
            f'Dim {var} As Object',
            f'Set {var} = Result0D("")',
            f'{var}.Title "{title}"',
            f'{var}.SetDataLabelAndUnit "{label}", "{unit}"',
            setter,
            f'{var}.SetFileName "{name}"',
            f'{var}.Save',
            f'{var}.AddToTree "{tree_path}"',
        ])
        self.run_vba(body)

    # --- thermal / conjugate heat transfer ------------------------------

    def add_heat_source(self, name: str, value: Any, faces: Sequence[Sequence[Any]],
                        *, value_type: str = "Integral", folder: str = "",
                        enabled: bool = True) -> None:
        """Add a heat source on faces (``faces`` is ``(solid, face_id)`` pairs)."""
        lines = [f'.Name "{name}"', f'.Folder "{folder}"']
        for solid, face_id in faces:
            lines.append(f'.Face "{solid}", "{int(face_id)}"')
        lines += [f'.Value "{value}"', f'.ValueType "{value_type}"',
                  f'.Enable "{_vba_value(enabled)}"']
        self._create_item("HeatSource", f"heat source {name}", lines)

    def add_fluid_domain(self, name: str, cavity_material: str, *,
                         faces: Sequence[Sequence[Any]] = (), folder: str = "",
                         invert_normal: bool = False, enabled: bool = True) -> None:
        """Add a fluid domain (cavity) for the conjugate heat transfer solver."""
        lines = [f'.Name "{name}"', f'.Folder "{folder}"',
                 f'.CavityMaterial "{cavity_material}"']
        for solid, face_id in faces:
            lines.append(f'.AddFace "{solid}", "{int(face_id)}"')
        lines += [f'.InvertNormal "{_vba_value(invert_normal)}"',
                  f'.Enable "{_vba_value(enabled)}"']
        self._create_item("FluidDomain", f"fluid domain {name}", lines)

    def set_initial_condition(self, name: str, *,
                              items: Sequence[Sequence[str]] = (),
                              **settings: Any) -> None:
        """Define an initial condition and assign it to ``items``.

        ``items`` entries are ``("solid"|"fluiddomain", objectname)``.
        """
        lines = [f'.Name "{name}"']
        lines += [f'.{key} "{value}"' for key, value in settings.items()]
        for kind, obj in items:
            lines.append(f'.AddItem "{kind}${obj}", "{name}"')
        self._create_item("InitialCondition", f"initial condition {name}", lines)

    def add_interior_boundary(self, kind: str, name: str,
                              faces: Sequence[Sequence[Any]], *,
                              velocity: Sequence[Any] | None = None,
                              pressure: Sequence[Any] | None = None,
                              volume_flow_rate: Any | None = None,
                              folder: str = "", enabled: bool = True) -> None:
        """Add an interior boundary (``"Opening"`` or ``"Lid"``) on faces."""
        lines = [f'.Name "{name}"', f'.Folder "{folder}"']
        for solid, face_id in faces:
            lines.append(f'.AddFace "{solid}", "{int(face_id)}"')
        if velocity is not None:
            lines.append(f'.Set "Velocity", "{velocity[0]}", "{velocity[1]}", '
                         f'"{velocity[2]}", "{velocity[3]}"')
        if pressure is not None:
            lines.append(f'.Set "Pressure", "{pressure[0]}", "{pressure[1]}"')
        if volume_flow_rate is not None:
            lines.append(f'.Set "VolumeFlowRate", "{volume_flow_rate}"')
        lines.append(f'.Enable "{_vba_value(enabled)}"')
        lines.append(f'.Create "{kind}"')
        self.add_history(f"interior boundary {name}",
                         _with_block("InteriorBoundary", lines))

    def add_fan(self, name: str, **settings: Any) -> None:
        """Add a fan (keyword = CST ``Fan`` method name)."""
        self._create_item("Fan", f"fan {name}", [f'.Name "{name}"']
                          + [f'.{k} "{v}"' for k, v in settings.items()])

    def add_heat_pipe(self, name: str, **settings: Any) -> None:
        """Add a heat pipe (keyword = CST ``HeatPipe`` method name)."""
        self._create_item("HeatPipe", f"heat pipe {name}", [f'.Name "{name}"']
                          + [f'.{k} "{v}"' for k, v in settings.items()])

    def add_temperature_source(self, name: str, **settings: Any) -> None:
        """Add a temperature source (keyword = CST method name)."""
        self._create_item("TemperatureSource", f"temperature source {name}",
                          [f'.Name "{name}"']
                          + [f'.{k} "{v}"' for k, v in settings.items()])

    def set_thermal_surface_property(self, name: str, **settings: Any) -> None:
        """Add a thermal surface property (keyword = CST method name)."""
        self._create_item("ThermalSurfaceProperty",
                          f"thermal surface property {name}", [f'.Name "{name}"']
                          + [f'.{k} "{v}"' for k, v in settings.items()])

    def add_thermoelectric_cooler(self, name: str, **settings: Any) -> None:
        """Add a thermoelectric cooler (keyword = CST method name)."""
        self._create_item("ThermoelectricCooler", f"TEC {name}",
                          [f'.Name "{name}"']
                          + [f'.{k} "{v}"' for k, v in settings.items()])

    def set_moving_media(self, name: str, **settings: Any) -> None:
        """Add moving media for CHT (keyword = CST method name)."""
        self._create_item("MovingMedia", f"moving media {name}",
                          [f'.Name "{name}"']
                          + [f'.{k} "{v}"' for k, v in settings.items()])

    def set_conjugate_heat_transfer(self, **settings: Any) -> None:
        """Configure the ``CHTSolver`` (keyword = CST method name)."""
        lines = [f'.{k} "{v}"' for k, v in settings.items()]
        self.add_history("CHT solver", _with_block("CHTSolver", lines))

    def set_thermal_transient_solver(self, **settings: Any) -> None:
        """Configure the ``ThermalTDSolver`` (keyword = CST method name)."""
        lines = [f'.{k} "{v}"' for k, v in settings.items()]
        self.add_history("thermal transient solver",
                         _with_block("ThermalTDSolver", lines))

    # --- LF / MEP physics (coils, magnets, charges, mechanics) ----------

    def add_coil(self, name: str, **settings: Any) -> None:
        """Add a coil (keyword = CST ``Coil`` method name)."""
        self._create_item("Coil", f"coil {name}", [f'.Name "{name}"']
                          + [f'.{key} "{value}"' for key, value in settings.items()])

    def add_coil_group(self, name: str, **settings: Any) -> None:
        """Add a coil group (keyword = CST method name)."""
        self._create_item("CoilGroup", f"coil group {name}", [f'.Name "{name}"']
                          + [f'.{key} "{value}"' for key, value in settings.items()])

    def add_magnet(self, name: str, **settings: Any) -> None:
        """Add a permanent magnet (keyword = CST ``Magnet`` method name)."""
        self._create_item("Magnet", f"magnet {name}", [f'.Name "{name}"']
                          + [f'.{key} "{value}"' for key, value in settings.items()])

    def add_charge(self, name: str, value: Any, faces: Sequence[Sequence[Any]], *,
                   value_type: str = "Integral", charge_type: str = "Volume") -> None:
        """Add a charge source on faces (``(solid, face_id)`` pairs)."""
        lines = [f'.Name "{name}"', f'.Value "{value}"',
                 f'.ValueType "{value_type}"', f'.Type "{charge_type}"']
        for solid, face_id in faces:
            lines.append(f'.Face "{solid}", "{int(face_id)}"')
        self._create_item("Charge", f"charge {name}", lines)

    def add_displacement(self, name: str, value: Sequence[Any],
                         faces: Sequence[Sequence[Any]], *,
                         normal: Any | None = None,
                         use: Sequence[bool] = (True, True, True)) -> None:
        """Add a mechanical displacement boundary condition on faces."""
        lines = [
            f'.Name "{name}"',
            f'.Value "{value[0]}", "{value[1]}", "{value[2]}"',
            f'.UseValue "{_vba_value(use[0])}", "{_vba_value(use[1])}", '
            f'"{_vba_value(use[2])}"',
        ]
        if normal is not None:
            lines.append(f'.NormalValue "{normal}"')
        for solid, face_id in faces:
            lines.append(f'.AddFace "{solid}", "{int(face_id)}"')
        self._create_item("Displacement", f"displacement {name}", lines)

    def add_traction(self, name: str, value: Sequence[Any],
                     faces: Sequence[Sequence[Any]], *,
                     normal: Any | None = None,
                     use: Sequence[bool] = (True, True, True)) -> None:
        """Add a mechanical traction (surface force) boundary condition on faces."""
        lines = [
            f'.Name "{name}"',
            f'.Value "{value[0]}", "{value[1]}", "{value[2]}"',
            f'.UseValue "{_vba_value(use[0])}", "{_vba_value(use[1])}", '
            f'"{_vba_value(use[2])}"',
        ]
        if normal is not None:
            lines.append(f'.NormalValue "{normal}"')
        for solid, face_id in faces:
            lines.append(f'.AddFace "{solid}", "{int(face_id)}"')
        self._create_item("Traction", f"traction {name}", lines)

    def set_contact_properties(self, name: str, **settings: Any) -> None:
        """Add mechanical contact properties (keyword = CST method name)."""
        self._create_item("ContactProperties", f"contact {name}", [f'.Name "{name}"']
                          + [f'.{key} "{value}"' for key, value in settings.items()])

    def add_rigid_body_motion(self, name: str, **settings: Any) -> None:
        """Add a rigid-body motion (keyword = CST ``RigidBodyMotion`` method name)."""
        self._create_item("RigidBodyMotion", f"rigid body motion {name}",
                          [f'.Name "{name}"']
                          + [f'.{key} "{value}"' for key, value in settings.items()])

    def add_motion_gap(self, name: str, **settings: Any) -> None:
        """Add a motion gap (keyword = CST ``MotionGap`` method name)."""
        self._create_item("MotionGap", f"motion gap {name}", [f'.Name "{name}"']
                          + [f'.{key} "{value}"' for key, value in settings.items()])

    def set_structural_mechanics_solver(self, **settings: Any) -> None:
        """Configure the ``StructuralMechanicsSolver`` (keyword = CST method name)."""
        lines = [f'.{key} "{value}"' for key, value in settings.items()]
        self.add_history("structural mechanics solver",
                         _with_block("StructuralMechanicsSolver", lines))

    # --- particles, signals and fields ----------------------------------

    def add_particle_source(self, name: str, **settings: Any) -> None:
        """Add a particle source (keyword = CST ``ParticleSource`` method name)."""
        self._create_item("ParticleSource", f"particle source {name}",
                          [f'.Name "{name}"']
                          + [f'.{key} "{value}"' for key, value in settings.items()])

    def add_particle_interface(self, name: str, **settings: Any) -> None:
        """Add a particle interface (keyword = CST method name)."""
        self._create_item("ParticleInterface", f"particle interface {name}",
                          [f'.Name "{name}"']
                          + [f'.{key} "{value}"' for key, value in settings.items()])

    def add_particle_monitor(self, name: str, **settings: Any) -> None:
        """Add a particle monitor (keyword = CST ``ParticleMonitor`` method name)."""
        self._create_item("ParticleMonitor", f"particle monitor {name}",
                          [f'.Name "{name}"']
                          + [f'.{key} "{value}"' for key, value in settings.items()])

    def add_particle_beam(self, name: str, **settings: Any) -> None:
        """Add a wake-field particle beam (keyword = CST method name)."""
        self._create_item("ParticleBeam", f"particle beam {name}",
                          [f'.Name "{name}"']
                          + [f'.{key} "{value}"' for key, value in settings.items()])

    def set_tracking_solver(self, **settings: Any) -> None:
        """Configure the ``TrackingSolver`` (keyword = CST method name)."""
        lines = [f'.{key} "{value}"' for key, value in settings.items()]
        self.add_history("tracking solver", _with_block("TrackingSolver", lines))

    def add_time_signal(self, name: str, **settings: Any) -> None:
        """Define an excitation time signal (keyword = CST ``TimeSignal`` method name)."""
        self._create_item("TimeSignal", f"time signal {name}", [f'.Name "{name}"']
                          + [f'.{key} "{value}"' for key, value in settings.items()])

    def set_source_field(self, **settings: Any) -> None:
        """Configure a constant ``SourceField`` (keyword = CST method name)."""
        lines = [f'.{key} "{value}"' for key, value in settings.items()]
        self.add_history("source field", _with_block("SourceField", lines))

    def set_predefined_field(self, **settings: Any) -> None:
        """Configure a ``PredefinedField`` (keyword = CST method name)."""
        lines = [f'.{key} "{value}"' for key, value in settings.items()]
        self._create_item("PredefinedField", "predefined field", lines)

    def run_schematic_vba(self, body: str) -> None:
        """Run raw Design Studio (schematic) VBA immediately.

        The Design Studio object model (blocks, nets, tasks, external ports) has
        no dedicated wrappers; drive it through this method when needed.
        """
        self.run_vba(body)

    # --- mesh, dimensions and extra curve types -------------------------

    def set_mesh_adaption3d(self, **settings: Any) -> None:
        """Configure ``MeshAdaption3D`` (keyword = CST method name, e.g. ``MaxPasses``)."""
        lines = [f'.{key} "{value}"' for key, value in settings.items()]
        self.add_history("mesh adaption", _with_block("MeshAdaption3D", lines))

    def add_dimension(self, name: str, **settings: Any) -> None:
        """Add a dimension annotation (keyword = CST ``Dimension`` method name)."""
        self._create_item("Dimension", f"dimension {name}", [f'.Name "{name}"']
                          + [f'.{key} "{value}"' for key, value in settings.items()])

    def define_analytical_curve(self, name: str, curve: str, x_law: str, y_law: str,
                                u_range: Sequence[Any]) -> None:
        """Add a parametric curve ``x = f(u)``, ``y = g(u)`` for ``u`` in ``u_range``."""
        code = _with_block("AnalyticalCurve", [
            ".Reset", f'.Name "{name}"', f'.Curve "{curve}"',
            f'.LawX "{x_law}"', f'.LawY "{y_law}"',
            f'.ParameterRangeU "{u_range[0]}", "{u_range[1]}"', ".Create",
        ])
        self.add_history(f"analytical curve {name}", code)

    def heal_solid(self, **settings: Any) -> None:
        """Run solid healing / repair (keyword = CST ``Solid`` healing method name)."""
        lines = [f'.{key} "{value}"' for key, value in settings.items()]
        self.add_history("heal solid", _with_block("Solid", lines))

    # --- run and save ---------------------------------------------------

    def solver_status(self, timeout: int = 30) -> dict[str, Any]:
        """Read native CST solver state and run information without a new simulation."""
        return {"running": bool(self.modeler.is_solver_running(timeout=timeout)),
                "solver": self.modeler.get_active_solver_name(timeout=timeout),
                "run_info": self.modeler.get_solver_run_info(timeout=timeout)}

    def start_solver(self, timeout: int = 30) -> None:
        """Start the solver asynchronously. Poll solver_status until completion."""
        self.modeler.start_solver(timeout=timeout)

    def abort_solver(self, timeout: int = 30) -> None:
        """Request cancellation of the current or paused native CST solver."""
        self.modeler.abort_solver(timeout=timeout)

    def messages(self) -> Any:
        """Read the native CST message window."""
        return self.project.get_messages()

    def _query_vba(self, lines: Sequence[str]) -> list[list[str]]:
        """Return tab-separated records from a read-only VBA query."""
        descriptor, filename = tempfile.mkstemp(prefix="cst_query_", suffix=".txt")
        os.close(descriptor)
        path = Path(filename)
        try:
            body = ["Dim ff As Integer", "ff = FreeFile", f"Open {_vba_value(filename)} For Output As #ff",
                    *lines, "Close #ff"]
            self.run_vba("\n".join(body), timeout=30)
            return [line.split("\t") for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line]
        finally:
            path.unlink(missing_ok=True)

    def model_snapshot(self) -> dict[str, Any]:
        """Read live units, parameters, boundaries, and solid materials/volumes/bounds.

        Bounds are the documented loose global bounding boxes, not exact surface measurements.
        """
        lines = [
            "Dim i As Long, s As String, ok As Boolean",
            "Dim x1 As Double, x2 As Double, y1 As Double, y2 As Double, z1 As Double, z2 As Double",
            'Print #ff, "unit" & vbTab & "geometry_scale" & vbTab & CStr(Units.GetGeometryUnitToSI)',
            'Print #ff, "unit" & vbTab & "frequency_scale" & vbTab & CStr(Units.GetFrequencyUnitToSI)',
            'Print #ff, "frequency" & vbTab & "min" & vbTab & CStr(Solver.GetFmin)',
            'Print #ff, "frequency" & vbTab & "max" & vbTab & CStr(Solver.GetFmax)',
            "For i = 0 To GetNumberOfParameters - 1",
            '  Print #ff, "parameter" & vbTab & GetParameterName(i) & vbTab & CStr(GetParameterNValue(i))',
            "Next i",
        ]
        for face in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax"):
            lines.append(f'Print #ff, "boundary" & vbTab & "{face}" & vbTab & Boundary.Get{face.capitalize()}')
        lines += [
            "For i = 0 To Solid.GetNumberOfShapes - 1",
            "  s = Solid.GetNameOfShapeFromIndex(i)",
            "  ok = Solid.GetLooseBoundingBoxOfShape(s, x1, x2, y1, y2, z1, z2)",
            '  If Not ok Then Err.Raise vbObjectError + 513, , "Cannot inspect solid " & s',
            '  Print #ff, "solid" & vbTab & s & vbTab & Solid.GetMaterialNameForShape(s) & vbTab & CStr(Solid.GetVolume(s)) & vbTab & CStr(x1) & vbTab & CStr(x2) & vbTab & CStr(y1) & vbTab & CStr(y2) & vbTab & CStr(z1) & vbTab & CStr(z2)',
            "Next i",
        ]
        data: dict[str, Any] = {"units": {}, "frequency": {}, "parameters": {}, "boundaries": {}, "solids": {}}
        for row in self._query_vba(lines):
            number = lambda value: float(value.replace(",", "."))
            if row[0] == "unit":
                data["units"][row[1]] = number(row[2])
            elif row[0] == "frequency":
                data["frequency"][row[1]] = number(row[2])
            elif row[0] == "parameter":
                data["parameters"][row[1]] = number(row[2])
            elif row[0] == "boundary":
                data["boundaries"][row[1]] = row[2].lower()
            elif row[0] == "solid":
                data["solids"][row[1]] = {"material": row[2], "volume": number(row[3]),
                    "bounds": dict(zip(("xmin", "xmax", "ymin", "ymax", "zmin", "zmax"), map(number, row[4:]), strict=True))}
        data["solver"] = self.modeler.get_active_solver_name(timeout=30)
        return data

    def rebuild(self) -> None:
        """Rebuild the model after a parameter change."""
        self.modeler.full_history_rebuild()

    def run_solver(self) -> None:
        """Run the active solver. Blocks until the run finishes."""
        self.modeler.run_solver()

    def save(
        self,
        path: str | os.PathLike | None = None,
        include_results: bool = True,
        allow_overwrite: bool = True,
    ) -> None:
        """Save the project. Saves to a new path when ``path`` is given."""
        if path is None:
            self._project.save(include_results=include_results)
        else:
            self._project.save(
                str(Path(path).resolve()),
                include_results=include_results,
                allow_overwrite=allow_overwrite,
            )

    def close(self, save: bool = False) -> None:
        """Close the project. Save only when asked."""
        if save:
            self.save()
        self._project.close()


def s_parameter_tree_item(name: str) -> str:
    """Return the CST tree path of one S-parameter, for example ``S1,1``."""
    return "1D Results\\S-Parameters\\" + name


# --- reading the result tree -------------------------------------------------

def _result_module(project_path: str | os.PathLike, module: str = "3d"):
    """Open a saved project and return its 3D or schematic result module."""
    cst = load_cst()
    project = cst.results.ProjectFile(str(Path(project_path).resolve()), allow_interactive=True)
    return project.get_3d() if module == "3d" else project.get_schematic()


def result_tree(project_path: str | os.PathLike, module: str = "3d") -> list[str]:
    """Return every item in the result tree of a saved project."""
    return list(_result_module(project_path, module).get_tree_items())


def find_tree_items(tree_items: Sequence[str], *keywords: str) -> list[str]:
    """Return tree items whose path contains all the given keywords."""
    wanted = [word.lower() for word in keywords]
    return [item for item in tree_items if all(word in item.lower() for word in wanted)]


def leaf_tree_items(tree_items: Sequence[str]) -> list[str]:
    """Return the items that are not folders.

    CST can only export leaves, not the folders that hold them.
    """
    folders = {item.rsplit("\\", 1)[0] for item in tree_items if "\\" in item}
    return [item for item in tree_items if item not in folders]


def find_results(project_path: str | os.PathLike, *keywords: str, module: str = "3d") -> list[str]:
    """Return result-tree items whose path contains all the given keywords."""
    return find_tree_items(result_tree(project_path, module), *keywords)


def read_1d_result(
    project_path: str | os.PathLike,
    item: str,
    run_id: int | None = None,
    module: str = "3d",
) -> tuple[list[float], list]:
    """Read one 1D result item and return ``(x, y)``."""
    result_module = _result_module(project_path, module)
    if run_id is None:
        result = result_module.get_result_item(item)
    else:
        result = result_module.get_result_item(item, run_id)
    return list(result.get_xdata()), list(result.get_ydata())


def read_2d_result(project_path: str | os.PathLike, item: str, module: str = "3d") -> dict:
    """Read one 2D (colormap) result item, for example a far field or a field cut.

    Returns a dict with ``x``, ``y``, ``data`` (row-major), labels and units.
    """
    result = _result_module(project_path, module).get_result2d_item(item)
    return {
        "x": list(result.get_xpositions()),
        "y": list(result.get_ypositions()),
        "data": [list(row) for row in result.get_data()],
        "title": result.title,
        "xlabel": result.xlabel,
        "ylabel": result.ylabel,
        "xunit": result.xunit,
        "yunit": result.yunit,
        "dataunit": result.dataunit,
    }


def read_s_parameter(
    project_path: str | os.PathLike,
    name: str = "S1,1",
    run_id: int | None = None,
) -> tuple[list[float], list[complex]]:
    """Read one S-parameter. Returns ``(frequencies, values)``; values are complex."""
    return read_1d_result(project_path, s_parameter_tree_item(name), run_id)


def input_impedance(s11: Sequence[complex], z0: float = 50.0) -> list[complex]:
    """Convert S11 to the input impedance ``Z = z0 * (1 + S11) / (1 - S11)``."""
    return [z0 * (1 + value) / (1 - value) for value in s11]


def read_impedance(
    project_path: str | os.PathLike,
    name: str = "S1,1",
    z0: float = 50.0,
    run_id: int | None = None,
) -> tuple[list[float], list[complex]]:
    """Read S11 and return ``(frequencies, input impedance)``."""
    freqs, s11 = read_s_parameter(project_path, name, run_id)
    return freqs, input_impedance(s11, z0)


def to_db(values: Sequence[complex], floor: float = -240.0) -> list[float]:
    """Return ``20 * log10(|value|)`` in dB for a sequence of complex values.

    Values whose magnitude is (near) zero are clamped to ``floor`` so the
    result stays finite (handy for plotting S-parameters).
    """
    result: list[float] = []
    for value in values:
        magnitude = abs(value)
        result.append(20 * math.log10(magnitude) if magnitude > 1e-12 else floor)
    return result


def vswr(s11: Sequence[complex]) -> list[float]:
    """Return the voltage standing wave ratio from S11."""
    values = []
    for value in s11:
        magnitude = abs(value)
        values.append(float("inf") if magnitude >= 1 else (1 + magnitude) / (1 - magnitude))
    return values


# --- full result tree and ASCII export through CST VBA -----------------------
#
# The python results API can read 1D curves and 2D colormaps. Field monitors
# (E-field, H-field) and far fields are only reachable through CST itself, so
# these two helpers drive CST VBA to list the tree and to export one item.

_TREE_VBA = """
Dim stack(3000) As String
Dim lvl(3000) As Integer
Dim n As Integer, i As Integer, s As String, t As String, p As String
n = 0
stack(n) = "1D Results": lvl(n) = 0: n = n + 1
stack(n) = "2D/3D Results": lvl(n) = 0: n = n + 1
stack(n) = "Farfields": lvl(n) = 0: n = n + 1
t = ""
i = 0
Do While i < n
    p = stack(i)
    t = t + p + vbLf
    If lvl(i) < 6 Then
        s = Resulttree.GetFirstChildName(p)
        Do While Len(s) > 0
            If n < 2999 Then
                stack(n) = s
                lvl(n) = lvl(i) + 1
                n = n + 1
            End If
            s = Resulttree.GetNextItemName(s)
        Loop
    End If
    i = i + 1
Loop
Open "OUTPATH" For Output As #1
Print #1, t
Close #1
"""


def result_tree_vba(project: "CstProject") -> list[str]:
    """Return the full result tree of an open project, using CST VBA.

    Unlike :func:`result_tree` this also lists 2D/3D field results and far
    fields, for example ``2D/3D Results\\E-Field\\efield (f=2.45) [1]``.
    """
    out = Path(tempfile.gettempdir()) / f"cst_result_tree_{os.getpid()}.txt"
    out.unlink(missing_ok=True)
    project.run_vba(_TREE_VBA.replace("OUTPATH", str(out)))
    if not out.exists():
        return []
    text = out.read_text(encoding="utf-8", errors="ignore")
    return [line.strip() for line in text.splitlines() if line.strip()]


def export_result_item(
    project: "CstProject",
    tree_path: str,
    out_path: str | os.PathLike,
    mode: str = "FixedNumber",
    steps: tuple[int, int, int] | None = None,
) -> None:
    """Export one results-tree item to a text/CSV file with CST ASCIIExport.

    Use it for S-parameters, E-field, H-field, far field and any other item.
    ``mode`` is ``FixedWidth`` (default in CST) or ``FixedNumber``.
    ``steps`` sets the sampling grid ``(step_x, step_y, step_z)`` for fields.
    """
    lines = [
        f"SelectTreeItem ({_vba_value(tree_path)})",
        "With ASCIIExport",
        "  .Reset",
        f"  .FileName ({_vba_value(str(Path(out_path).resolve()))})",
        f"  .Mode ({_vba_value(mode)})",
    ]
    if steps:
        for axis, value in zip(("X", "Y", "Z"), steps):
            lines.append(f"  .Step{axis} ({int(value)})")
    lines += [".Execute", "End With"]
    project.run_vba("\n".join(lines))


# --- saving results as CSV and PNG -------------------------------------------

def validate_result_axis(
    x: Sequence[float],
    values: Sequence,
    *,
    name: str = "result",
    reference: Sequence[float] | None = None,
) -> None:
    """Require a finite, increasing axis with one value per sample.

    When reference is supplied, require the same sample coordinates.
    """
    if not len(x) or len(x) != len(values):
        raise ValueError(f"{name}: the axis and values must have the same nonzero length")
    if any(not math.isfinite(value) for value in x):
        raise ValueError(f"{name}: the axis must contain finite numbers")
    if any(right <= left for left, right in zip(x, x[1:])):
        raise ValueError(f"{name}: the axis must increase at each sample")
    if reference is not None and (
        len(x) != len(reference)
        or any(actual != expected for actual, expected in zip(x, reference, strict=True))
    ):
        raise ValueError(f"{name}: the sample coordinates do not match the reference axis")


def save_csv(path: str | os.PathLike, columns: Mapping[str, Sequence]) -> None:
    """Write named columns to a CSV file. The dict keys become the header."""
    import csv

    if not columns:
        raise ValueError("CSV columns must not be empty")
    lengths = {name: len(values) for name, values in columns.items()}
    if not all(lengths.values()) or len(set(lengths.values())) != 1:
        raise ValueError(f"CSV columns must have the same nonzero length: {lengths}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = list(columns)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(zip(*(columns[key] for key in header), strict=True))


def plot_lines_png(
    path: str | os.PathLike,
    x: Sequence,
    series: Mapping[str, Sequence],
    title: str,
    xlabel: str,
    ylabel: str,
    ylim: tuple[float, float] | None = None,
) -> None:
    """Plot one or more x-y curves and save a PNG."""
    if not series:
        raise ValueError("The plot must contain at least one result")
    for label, values in series.items():
        validate_result_axis(x, values, name=label)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 5))
    for label, y in series.items():
        ax.plot(x, y, label=label)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True)
    if ylim is not None:
        ax.set_ylim(*ylim)
    if len(series) > 1:
        ax.legend()
    fig.tight_layout()
    fig.savefig(str(path), dpi=150)
    plt.close(fig)


def plot_map_png(
    path: str | os.PathLike,
    data: Sequence[Sequence[float]],
    extent: tuple[float, float, float, float],
    title: str,
    xlabel: str,
    ylabel: str,
    colorbar_label: str = "",
) -> None:
    """Plot a 2D colormap and save a PNG."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 6))
    image = ax.imshow(data, origin="lower", aspect="auto", extent=extent)
    fig.colorbar(image, ax=ax, label=colorbar_label)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    fig.savefig(str(path), dpi=150)
    plt.close(fig)


