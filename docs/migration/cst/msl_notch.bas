' ============================================================================
' openEMS MSL notch filter - CST reference model (E-009 / CST-001)
'
' Builds the same microstrip notch filter as
'   openEMS/.github/smoketests/python/MSL_NotchFilter.py
' so a CST S-parameter sweep can be compared with the converged openEMS result
' (notch at 3.6700 GHz, |S11| maximum).
'
' HOW TO RUN
'   1. Open CST Studio Suite and create a new "Microwave & RF / Time Domain"
'      project (any name).
'   2. Edit ProjectPath and ExportDir below to existing writable folders.
'   3. Home > Macros > Run Macro... and select this file.
'   4. The macro builds the model, runs the transient solver and saves the
'      project. Export the Touchstone file as described in README.md (the
'      result-tree export is deliberately left to you; the ASCIIExport API
'      differs between CST releases).
'
' This macro could not be executed in the migration environment (no CST
' installation). If an object/property name differs in your CST release, the
' macro stops on that line; README.md contains the same model as a manual
' recipe, which is the authoritative fallback. Please report the failing line
' together with your CST version.
' ============================================================================

Sub Main()
    Dim ProjectPath As String
    Dim ExportDir As String
    Dim FMinGHz As Double
    Dim FMaxGHz As Double
    Dim MeshLinesPerWave As Long

    ' ---------------------------------------------------------------- inputs
    ProjectPath = "C:\openems-cst\msl_notch.cst"   ' <-- edit
    ExportDir = "C:\openems-cst\export\"           ' <-- edit (trailing \)
    FMinGHz = 1.0
    FMaxGHz = 7.0
    MeshLinesPerWave = 20

    ' ---------------------------------------------------------------- units
    With Units
        .Geometry "um"
        .Frequency "GHz"
        .Time "ns"
        .Temperature "Kelvin"
    End With

    ' ----------------------------------------------------------- background
    With Background
        .Reset
        .Type "Normal"
        .Epsilon "1.0"
        .Mu "1.0"
        .ApplyInAllDirections "False"
    End With

    ' ----------------------------------------------------------- boundaries
    ' Ports sit on the x planes, so those boundaries stay "open" rather than
    ' "expanded open"; zmin is the ground plane.
    With Boundary
        .Xmin "open"
        .Xmax "open"
        .Ymin "open"
        .Ymax "open"
        .Zmin "electric"
        .Zmax "open"
        .ApplyInAllDirections "False"
    End With

    ' ------------------------------------------------------------ materials
    With Material
        .Reset
        .Name "RO4350B"
        .Folder ""
        .FrqType "all"
        .Type "Normal"
        .Epsilon "3.66"
        .Mu "1.0"
        .Sigma "0.0"
        .TanD "0.0"
        .Rho "0.0"
        .Create
    End With

    ' ------------------------------------------------------------- substrate
    ' 100 mm x 30 mm x 254 um, y = -9 mm .. +21 mm (stub area included).
    With Brick
        .Reset
        .Name "substrate"
        .Component "dielectric"
        .Material "RO4350B"
        .Xrange "-50000", "50000"
        .Yrange "-9000", "21000"
        .Zrange "0", "254"
        .Create
    End With

    ' --------------------------------------------------------- microstrip line
    ' 600 um wide, 35 um thick PEC (openEMS uses an ideal sheet at z = 254 um).
    With Brick
        .Reset
        .Name "strip"
        .Component "metal"
        .Material "PEC"
        .Xrange "-50000", "50000"
        .Yrange "-300", "300"
        .Zrange "254", "289"
        .Create
    End With

    ' ------------------------------------------------------------- open stub
    ' 600 um wide, 12 mm long, at the centre of the line.
    With Brick
        .Reset
        .Name "stub"
        .Component "metal"
        .Material "PEC"
        .Xrange "-300", "300"
        .Yrange "300", "12300"
        .Zrange "254", "289"
        .Create
    End With

    ' ----------------------------------------------------------------- ports
    ' Waveguide ports over the substrate cross-section at both line ends.
    ' The y span is wider than the strip so the fringing field is included.
    With Port
        .Reset
        .PortNumber "1"
        .Label "port1"
        .NumberOfModes "1"
        .AdjustPolarization "False"
        .PolarizationAngle "0.0"
        .ReferencePlaneDistance "0"
        .TextSize "50"
        .Coordinates "Free"
        .Orientation "x"
        .PortOnBound "False"
        .ClipPickedPortToBound "False"
        .Xrange "-50000", "-50000"
        .Yrange "-3000", "3000"
        .Zrange "0", "254"
        .Create
    End With

    With Port
        .Reset
        .PortNumber "2"
        .Label "port2"
        .NumberOfModes "1"
        .AdjustPolarization "False"
        .PolarizationAngle "0.0"
        .ReferencePlaneDistance "0"
        .TextSize "50"
        .Coordinates "Free"
        .Orientation "x"
        .PortOnBound "False"
        .ClipPickedPortToBound "False"
        .Xrange "50000", "50000"
        .Yrange "-3000", "3000"
        .Zrange "0", "254"
        .Create
    End With

    ' ------------------------------------------------------------ frequency
    With Solver
        .Reset
        .Method "Hexahedral"
        .CalculationType "TD-S"
        .StimulationPort "All"
        .StimulationMode "All"
        .SteadyStateLimit "-40"
        .MeshAdaption "True"
        .RunDiscretizerMode "False"
        .AutoNormImpedance "False"
        .NormingImpedance "50"
        .SParaSymmetry "False"
        .StoreTDResultsInCache "False"
        .FullDeembedding "False"
        .UseBroadbandAdaptation "False"
    End With

    ' The hexahedral mesh is left to the adaptive refinement; the manual recipe
    ' in README.md sets the density explicitly for a mesh-independent run.

    ' The solver uses the project frequency range; set it explicitly.
    Solver.FrequencyRange FMinGHz, FMaxGHz

    ' --------------------------------------------------------------- solve
    Solver.Start

    ' --------------------------------------------------------------- save
    ' Save the project manually (Ctrl+S); export Touchstone as described in
    ' README.md (step 7).
    SelectTreeItem "1D Results\S-Parameters"

    MsgBox "Model built and solved." & vbCrLf & _
           "Export 1D Results > S-Parameters as Touchstone into:" & vbCrLf & _
           ExportDir, vbInformation, "openEMS CST reference"
End Sub
