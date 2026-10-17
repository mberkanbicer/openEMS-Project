//! `csxcad-core`: Native Rust implementation of CSXCAD
//!
//! Provides data structures for continuous geometric structures, material properties,
//! rectilinear grids (`CSRectGrid`), primitives (boxes, cylinders, spheres), and
//! XML parsing/serialization compatible with openEMS.

use std::collections::HashMap;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum CSXError {
    #[error("XML parsing error: {0}")]
    XmlError(String),
    #[error("Missing attribute: {0}")]
    MissingAttribute(String),
    #[error("Invalid value '{0}' for attribute '{1}'")]
    InvalidAttribute(String, String),
    #[error("Math expression evaluation error: {0}")]
    EvalError(#[from] fparser::ParseError),
    #[error("Math expression evaluation error: {0}")]
    EvalFailure(#[from] fparser::EvalError),
    #[error("Unknown parameter '{0}' in expression")]
    UnknownParameter(String),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum CoordinateSystem {
    #[default]
    Cartesian = 0,
    Cylindrical = 1,
    Spherical = 2,
}

impl CoordinateSystem {
    pub fn from_int(val: i32) -> Self {
        match val {
            1 => CoordinateSystem::Cylindrical,
            2 => CoordinateSystem::Spherical,
            _ => CoordinateSystem::Cartesian,
        }
    }

    pub fn to_int(self) -> i32 {
        self as i32
    }
}

/// Parameter set containing user-defined variables and evaluated constants.
#[derive(Debug, Clone, Default)]
pub struct ParameterSet {
    pub params: HashMap<String, f64>,
}

impl ParameterSet {
    pub fn new() -> Self {
        Self {
            params: HashMap::new(),
        }
    }

    pub fn set(&mut self, key: impl Into<String>, val: f64) {
        self.params.insert(key.into(), val);
    }

    pub fn get(&self, key: &str) -> Option<f64> {
        self.params.get(key).copied()
    }

    pub fn eval_expr(&self, expr_str: &str) -> Result<f64, CSXError> {
        let mut fp = fparser::Parser::new();
        let var_names = fp.parse_and_deduce_variables(expr_str, false)?;
        let values: Vec<f64> = var_names
            .iter()
            .map(|name| {
                self.params
                    .get(name)
                    .copied()
                    .ok_or_else(|| CSXError::UnknownParameter(name.clone()))
            })
            .collect::<Result<_, _>>()?;
        let res = fp.eval(&values)?;
        Ok(res)
    }
}

/// 3D Rectilinear Mesh Grid (`CSRectGrid`).
#[derive(Debug, Clone, PartialEq)]
pub struct CSRectGrid {
    pub delta_unit: f64,
    pub coord_system: CoordinateSystem,
    pub lines: [Vec<f64>; 3], // 0: X, 1: Y, 2: Z
}

impl Default for CSRectGrid {
    fn default() -> Self {
        Self {
            delta_unit: 1.0,
            coord_system: CoordinateSystem::Cartesian,
            lines: [Vec::new(), Vec::new(), Vec::new()],
        }
    }
}

impl CSRectGrid {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_line(&mut self, dir: usize, val: f64) {
        if dir < 3 {
            self.lines[dir].push(val);
            self.lines[dir].sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
            self.lines[dir].dedup_by(|a, b| (*a - *b).abs() < 1e-12);
        }
    }

    pub fn set_lines(&mut self, dir: usize, lines: Vec<f64>) {
        if dir < 3 {
            let mut l = lines;
            l.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
            l.dedup_by(|a, b| (*a - *b).abs() < 1e-12);
            self.lines[dir] = l;
        }
    }

    pub fn get_qty_lines(&self, dir: usize) -> usize {
        if dir < 3 {
            self.lines[dir].len()
        } else {
            0
        }
    }

    /// Calculate Yee-cell cell widths delta[n] = lines[n][i+1] - lines[n][i].
    pub fn get_deltas(&self, dir: usize) -> Vec<f64> {
        if dir >= 3 || self.lines[dir].len() < 2 {
            return Vec::new();
        }
        let l = &self.lines[dir];
        let mut deltas = Vec::with_capacity(l.len() - 1);
        for i in 0..(l.len() - 1) {
            deltas.push((l[i + 1] - l[i]) * self.delta_unit);
        }
        deltas
    }

    /// Dual mesh positions for Yee field staggering (centers of primary cells).
    pub fn get_dual_lines(&self, dir: usize) -> Vec<f64> {
        if dir >= 3 || self.lines[dir].len() < 2 {
            return Vec::new();
        }
        let l = &self.lines[dir];
        let mut dual = Vec::with_capacity(l.len() - 1);
        for i in 0..(l.len() - 1) {
            dual.push(0.5 * (l[i] + l[i + 1]));
        }
        dual
    }
}

/// 3D Box Primitive (`CSPrimBox`).
#[derive(Debug, Clone, PartialEq)]
pub struct CSPrimBox {
    pub priority: i32,
    pub p1: [f64; 3], // start [x, y, z]
    pub p2: [f64; 3], // stop [x, y, z]
}

impl CSPrimBox {
    pub fn new(p1: [f64; 3], p2: [f64; 3], priority: i32) -> Self {
        Self { priority, p1, p2 }
    }

    pub fn bound_box(&self) -> [f64; 6] {
        [
            self.p1[0].min(self.p2[0]),
            self.p1[0].max(self.p2[0]),
            self.p1[1].min(self.p2[1]),
            self.p1[1].max(self.p2[1]),
            self.p1[2].min(self.p2[2]),
            self.p1[2].max(self.p2[2]),
        ]
    }

    pub fn contains_point(&self, p: [f64; 3]) -> bool {
        let b = self.bound_box();
        p[0] >= b[0] && p[0] <= b[1] && p[1] >= b[2] && p[1] <= b[3] && p[2] >= b[4] && p[2] <= b[5]
    }
}

/// 3D Sphere Primitive (`CSPrimSphere`).
#[derive(Debug, Clone, PartialEq)]
pub struct CSPrimSphere {
    pub priority: i32,
    pub center: [f64; 3],
    pub radius: f64,
}

impl CSPrimSphere {
    pub fn new(center: [f64; 3], radius: f64, priority: i32) -> Self {
        Self {
            priority,
            center,
            radius,
        }
    }

    pub fn bound_box(&self) -> [f64; 6] {
        [
            self.center[0] - self.radius,
            self.center[0] + self.radius,
            self.center[1] - self.radius,
            self.center[1] + self.radius,
            self.center[2] - self.radius,
            self.center[2] + self.radius,
        ]
    }

    pub fn contains_point(&self, p: [f64; 3]) -> bool {
        let dx = p[0] - self.center[0];
        let dy = p[1] - self.center[1];
        let dz = p[2] - self.center[2];
        (dx * dx + dy * dy + dz * dz) <= (self.radius * self.radius)
    }
}

/// 3D Cylinder Primitive (`CSPrimCylinder`).
#[derive(Debug, Clone, PartialEq)]
pub struct CSPrimCylinder {
    pub priority: i32,
    pub p1: [f64; 3], // start center
    pub p2: [f64; 3], // stop center
    pub radius: f64,
}

impl CSPrimCylinder {
    pub fn new(p1: [f64; 3], p2: [f64; 3], radius: f64, priority: i32) -> Self {
        Self {
            priority,
            p1,
            p2,
            radius,
        }
    }

    pub fn bound_box(&self) -> [f64; 6] {
        let min_x = self.p1[0].min(self.p2[0]) - self.radius;
        let max_x = self.p1[0].max(self.p2[0]) + self.radius;
        let min_y = self.p1[1].min(self.p2[1]) - self.radius;
        let max_y = self.p1[1].max(self.p2[1]) + self.radius;
        let min_z = self.p1[2].min(self.p2[2]) - self.radius;
        let max_z = self.p1[2].max(self.p2[2]) + self.radius;
        [min_x, max_x, min_y, max_y, min_z, max_z]
    }

    pub fn contains_point(&self, p: [f64; 3]) -> bool {
        let v = [
            self.p2[0] - self.p1[0],
            self.p2[1] - self.p1[1],
            self.p2[2] - self.p1[2],
        ];
        let len_sq = v[0] * v[0] + v[1] * v[1] + v[2] * v[2];
        if len_sq == 0.0 {
            let dx = p[0] - self.p1[0];
            let dy = p[1] - self.p1[1];
            let dz = p[2] - self.p1[2];
            return (dx * dx + dy * dy + dz * dz) <= (self.radius * self.radius);
        }
        let u = [p[0] - self.p1[0], p[1] - self.p1[1], p[2] - self.p1[2]];
        let t = (u[0] * v[0] + u[1] * v[1] + u[2] * v[2]) / len_sq;
        if t < 0.0 || t > 1.0 {
            return false;
        }
        let proj = [
            self.p1[0] + t * v[0],
            self.p1[1] + t * v[1],
            self.p1[2] + t * v[2],
        ];
        let dist_sq = (p[0] - proj[0]).powi(2) + (p[1] - proj[1]).powi(2) + (p[2] - proj[2]).powi(2);
        dist_sq <= self.radius * self.radius
    }
}

/// Geometric primitive enum.
#[derive(Debug, Clone, PartialEq)]
pub enum Primitive {
    Box(CSPrimBox),
    Sphere(CSPrimSphere),
    Cylinder(CSPrimCylinder),
}

/// CSXCAD Material Property (`CSPropMaterial`).
#[derive(Debug, Clone, PartialEq)]
pub struct MaterialProperty {
    pub name: String,
    pub epsilon: [f64; 3],
    pub mue: [f64; 3],
    pub kappa: [f64; 3], // electric conductivity
    pub sigma: [f64; 3], // magnetic conductivity
    pub primitives: Vec<Primitive>,
}

impl MaterialProperty {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            epsilon: [1.0, 1.0, 1.0],
            mue: [1.0, 1.0, 1.0],
            kappa: [0.0, 0.0, 0.0],
            sigma: [0.0, 0.0, 0.0],
            primitives: Vec::new(),
        }
    }
}

/// CSXCAD Metal Property (PEC, `CSPropMetal`).
#[derive(Debug, Clone, PartialEq)]
pub struct MetalProperty {
    pub name: String,
    pub primitives: Vec<Primitive>,
}

impl MetalProperty {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            primitives: Vec::new(),
        }
    }
}

/// Excitation Property (`CSPropExcitation`).
#[derive(Debug, Clone, PartialEq)]
pub struct ExcitationProperty {
    pub name: String,
    pub number: u32,
    pub excit_type: i32,
    pub excite: [f64; 3],
    pub delay: f64,
    pub frequency: f64,
    pub primitives: Vec<Primitive>,
}

impl ExcitationProperty {
    pub fn new(name: impl Into<String>, number: u32) -> Self {
        Self {
            name: name.into(),
            number,
            excit_type: 0,
            excite: [0.0, 0.0, 0.0],
            delay: 0.0,
            frequency: 0.0,
            primitives: Vec::new(),
        }
    }
}

/// Probe Box Property (`CSPropProbeBox`).
#[derive(Debug, Clone, PartialEq)]
pub struct ProbeBoxProperty {
    pub name: String,
    pub number: u32,
    pub probe_type: i32, // 0: Voltage, 1: Current, 2: E-field, 3: H-field
    pub weight: f64,
    pub norm_dir: i32,
    pub primitives: Vec<Primitive>,
}

impl ProbeBoxProperty {
    pub fn new(name: impl Into<String>, number: u32, probe_type: i32) -> Self {
        Self {
            name: name.into(),
            number,
            probe_type,
            weight: 1.0,
            norm_dir: -1,
            primitives: Vec::new(),
        }
    }
}

/// Property Enum.
#[derive(Debug, Clone, PartialEq)]
pub enum Property {
    Material(MaterialProperty),
    Metal(MetalProperty),
    Excitation(ExcitationProperty),
    ProbeBox(ProbeBoxProperty),
}

/// Continuous Structure container (`ContinuousStructure`).
#[derive(Debug, Clone, Default)]
pub struct ContinuousStructure {
    pub coord_system: CoordinateSystem,
    pub grid: CSRectGrid,
    pub properties: Vec<Property>,
    pub parameter_set: ParameterSet,
}

impl ContinuousStructure {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_property(&mut self, prop: Property) {
        self.properties.push(prop);
    }
}

/// XML parser & serializer for CSXCAD format.
pub mod xml {
    use super::*;
    use quick_xml::events::{BytesStart, Event};
    use quick_xml::Reader;

    pub fn parse_csx_xml(xml_content: &str) -> Result<ContinuousStructure, CSXError> {
        let mut reader = Reader::from_str(xml_content);
        reader.config_mut().trim_text(true);

        let mut csx = ContinuousStructure::new();
        let mut buf = Vec::new();

        // State tracking
        let mut current_prop: Option<Property> = None;
        let mut in_rect_grid = false;
        let mut current_grid_dir: Option<usize> = None;
        let mut temp_p1 = [0.0; 3];
        let mut temp_p2 = [0.0; 3];
        let mut temp_prio = 0;
        let mut temp_radius = 0.0;

        loop {
            match reader.read_event_into(&mut buf) {
                Ok(Event::Start(ref e)) | Ok(Event::Empty(ref e)) => {
                    let name = String::from_utf8_lossy(e.name().as_ref()).to_string();
                    match name.as_str() {
                        "ContinuousStructure" => {
                            for attr in e.attributes().flatten() {
                                if attr.key.as_ref() == b"CoordSystem" {
                                    if let Ok(val) = std::str::from_utf8(&attr.value) {
                                        if let Ok(n) = val.parse::<i32>() {
                                            csx.coord_system = CoordinateSystem::from_int(n);
                                        }
                                    }
                                }
                            }
                        }
                        "RectilinearGrid" => {
                            in_rect_grid = true;
                            for attr in e.attributes().flatten() {
                                if attr.key.as_ref() == b"DeltaUnit" {
                                    if let Ok(val) = std::str::from_utf8(&attr.value) {
                                        if let Ok(v) = val.parse::<f64>() {
                                            csx.grid.delta_unit = v;
                                        }
                                    }
                                }
                            }
                        }
                        "XLines" => if in_rect_grid { current_grid_dir = Some(0); },
                        "YLines" => if in_rect_grid { current_grid_dir = Some(1); },
                        "ZLines" => if in_rect_grid { current_grid_dir = Some(2); },
                        "Material" => {
                            let mut prop_name = String::new();
                            for attr in e.attributes().flatten() {
                                if attr.key.as_ref() == b"Name" {
                                    prop_name = String::from_utf8_lossy(&attr.value).to_string();
                                }
                            }
                            current_prop = Some(Property::Material(MaterialProperty::new(prop_name)));
                        }
                        "Metal" => {
                            let mut prop_name = String::new();
                            for attr in e.attributes().flatten() {
                                if attr.key.as_ref() == b"Name" {
                                    prop_name = String::from_utf8_lossy(&attr.value).to_string();
                                }
                            }
                            current_prop = Some(Property::Metal(MetalProperty::new(prop_name)));
                        }
                        "Excitation" => {
                            let mut prop_name = String::new();
                            let mut num = 0;
                            let mut excite_type = 0;
                            for attr in e.attributes().flatten() {
                                match attr.key.as_ref() {
                                    b"Name" => prop_name = String::from_utf8_lossy(&attr.value).to_string(),
                                    b"Number" => num = std::str::from_utf8(&attr.value).unwrap_or("0").parse().unwrap_or(0),
                                    b"Type" => excite_type = std::str::from_utf8(&attr.value).unwrap_or("0").parse().unwrap_or(0),
                                    _ => {}
                                }
                            }
                            let mut ep = ExcitationProperty::new(prop_name, num);
                            ep.excit_type = excite_type;
                            current_prop = Some(Property::Excitation(ep));
                        }
                        "ProbeBox" => {
                            let mut prop_name = String::new();
                            let mut num = 0;
                            let mut ptype = 0;
                            for attr in e.attributes().flatten() {
                                match attr.key.as_ref() {
                                    b"Name" => prop_name = String::from_utf8_lossy(&attr.value).to_string(),
                                    b"Number" => num = std::str::from_utf8(&attr.value).unwrap_or("0").parse().unwrap_or(0),
                                    b"Type" => ptype = std::str::from_utf8(&attr.value).unwrap_or("0").parse().unwrap_or(0),
                                    _ => {}
                                }
                            }
                            current_prop = Some(Property::ProbeBox(ProbeBoxProperty::new(prop_name, num, ptype)));
                        }
                        "Property" => {
                            if let Some(Property::Material(ref mut mat)) = current_prop {
                                for attr in e.attributes().flatten() {
                                    if attr.key.as_ref() == b"Epsilon" {
                                        let val_str = String::from_utf8_lossy(&attr.value);
                                        let parts: Vec<f64> = val_str
                                            .split(',')
                                            .filter_map(|s| s.trim().parse::<f64>().ok())
                                            .collect();
                                        if parts.len() == 1 {
                                            mat.epsilon = [parts[0], parts[0], parts[0]];
                                        } else if parts.len() == 3 {
                                            mat.epsilon = [parts[0], parts[1], parts[2]];
                                        }
                                    }
                                }
                            }
                        }
                        "Box" => {
                            temp_p1 = [0.0; 3];
                            temp_p2 = [0.0; 3];
                            temp_prio = 0;
                            for attr in e.attributes().flatten() {
                                if attr.key.as_ref() == b"Priority" {
                                    if let Ok(v) = std::str::from_utf8(&attr.value) {
                                        temp_prio = v.parse().unwrap_or(0);
                                    }
                                }
                            }
                        }
                        "Sphere" => {
                            temp_p1 = [0.0; 3]; // center
                            temp_prio = 0;
                            temp_radius = 0.0;
                            for attr in e.attributes().flatten() {
                                match attr.key.as_ref() {
                                    b"Priority" => {
                                        if let Ok(v) = std::str::from_utf8(&attr.value) {
                                            temp_prio = v.parse().unwrap_or(0);
                                        }
                                    }
                                    b"Radius" => {
                                        if let Ok(v) = std::str::from_utf8(&attr.value) {
                                            temp_radius = v.parse().unwrap_or(0.0);
                                        }
                                    }
                                    _ => {}
                                }
                            }
                        }
                        "Cylinder" => {
                            temp_p1 = [0.0; 3];
                            temp_p2 = [0.0; 3];
                            temp_prio = 0;
                            temp_radius = 0.0;
                            for attr in e.attributes().flatten() {
                                match attr.key.as_ref() {
                                    b"Priority" => {
                                        if let Ok(v) = std::str::from_utf8(&attr.value) {
                                            temp_prio = v.parse().unwrap_or(0);
                                        }
                                    }
                                    b"Radius" => {
                                        if let Ok(v) = std::str::from_utf8(&attr.value) {
                                            temp_radius = v.parse().unwrap_or(0.0);
                                        }
                                    }
                                    _ => {}
                                }
                            }
                        }
                        "P1" | "Center" => {
                            parse_point_attrs(e, &mut temp_p1);
                        }
                        "P2" => {
                            parse_point_attrs(e, &mut temp_p2);
                        }
                        _ => {}
                    }
                }
                Ok(Event::Text(ref e)) => {
                    if let Some(dir) = current_grid_dir {
                        let text = e.unescape().map_err(|err| CSXError::XmlError(err.to_string()))?;
                        let coords: Vec<f64> = text
                            .split(',')
                            .filter_map(|s| s.trim().parse::<f64>().ok())
                            .collect();
                        csx.grid.set_lines(dir, coords);
                    }
                }
                Ok(Event::End(ref e)) => {
                    let name = String::from_utf8_lossy(e.name().as_ref()).to_string();
                    match name.as_str() {
                        "RectilinearGrid" => in_rect_grid = false,
                        "XLines" | "YLines" | "ZLines" => current_grid_dir = None,
                        "Box" => {
                            let prim = Primitive::Box(CSPrimBox::new(temp_p1, temp_p2, temp_prio));
                            add_prim_to_prop(&mut current_prop, prim);
                        }
                        "Sphere" => {
                            let prim = Primitive::Sphere(CSPrimSphere::new(temp_p1, temp_radius, temp_prio));
                            add_prim_to_prop(&mut current_prop, prim);
                        }
                        "Cylinder" => {
                            let prim = Primitive::Cylinder(CSPrimCylinder::new(temp_p1, temp_p2, temp_radius, temp_prio));
                            add_prim_to_prop(&mut current_prop, prim);
                        }
                        "Material" | "Metal" | "Excitation" | "ProbeBox" => {
                            if let Some(prop) = current_prop.take() {
                                csx.add_property(prop);
                            }
                        }
                        _ => {}
                    }
                }
                Ok(Event::Eof) => break,
                Err(e) => return Err(CSXError::XmlError(e.to_string())),
                _ => {}
            }
            buf.clear();
        }

        Ok(csx)
    }

    fn add_prim_to_prop(current_prop: &mut Option<Property>, prim: Primitive) {
        match current_prop {
            Some(Property::Material(ref mut mat)) => mat.primitives.push(prim),
            Some(Property::Metal(ref mut met)) => met.primitives.push(prim),
            Some(Property::Excitation(ref mut exc)) => exc.primitives.push(prim),
            Some(Property::ProbeBox(ref mut pb)) => pb.primitives.push(prim),
            None => {}
        }
    }

    fn parse_point_attrs(e: &BytesStart, pt: &mut [f64; 3]) {
        for attr in e.attributes().flatten() {
            if let Ok(val) = std::str::from_utf8(&attr.value) {
                if let Ok(v) = val.parse::<f64>() {
                    match attr.key.as_ref() {
                        b"X" => pt[0] = v,
                        b"Y" => pt[1] = v,
                        b"Z" => pt[2] = v,
                        _ => {}
                    }
                }
            }
        }
    }

    pub fn to_csx_xml(csx: &ContinuousStructure) -> String {
        let mut out = String::new();
        out.push_str("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n");
        out.push_str(&format!(
            "<ContinuousStructure CoordSystem=\"{}\">\n",
            csx.coord_system.to_int()
        ));

        // RectilinearGrid
        out.push_str(&format!(
            "  <RectilinearGrid DeltaUnit=\"{}\" CoordSystem=\"{}\">\n",
            csx.grid.delta_unit,
            csx.grid.coord_system.to_int()
        ));
        for (i, name) in ["XLines", "YLines", "ZLines"].iter().enumerate() {
            let lines_str = csx.grid.lines[i]
                .iter()
                .map(|v| v.to_string())
                .collect::<Vec<_>>()
                .join(",");
            out.push_str(&format!(
                "    <{} Qty=\"{}\">{}</{}>\n",
                name,
                csx.grid.lines[i].len(),
                lines_str,
                name
            ));
        }
        out.push_str("  </RectilinearGrid>\n");

        // Properties
        out.push_str("  <Properties>\n");
        for prop in &csx.properties {
            match prop {
                Property::Material(mat) => {
                    out.push_str(&format!("    <Material Name=\"{}\">\n", mat.name));
                    out.push_str(&format!(
                        "      <Property Epsilon=\"{},{},{}\" Mue=\"{},{},{}\" Kappa=\"{},{},{}\" Sigma=\"{},{},{}\" />\n",
                        mat.epsilon[0], mat.epsilon[1], mat.epsilon[2],
                        mat.mue[0], mat.mue[1], mat.mue[2],
                        mat.kappa[0], mat.kappa[1], mat.kappa[2],
                        mat.sigma[0], mat.sigma[1], mat.sigma[2]
                    ));
                    write_primitives(&mut out, &mat.primitives);
                    out.push_str("    </Material>\n");
                }
                Property::Metal(met) => {
                    out.push_str(&format!("    <Metal Name=\"{}\">\n", met.name));
                    write_primitives(&mut out, &met.primitives);
                    out.push_str("    </Metal>\n");
                }
                Property::Excitation(exc) => {
                    out.push_str(&format!(
                        "    <Excitation Name=\"{}\" Number=\"{}\" Type=\"{}\" Excite=\"{},{},{}\">\n",
                        exc.name, exc.number, exc.excit_type, exc.excite[0], exc.excite[1], exc.excite[2]
                    ));
                    write_primitives(&mut out, &exc.primitives);
                    out.push_str("    </Excitation>\n");
                }
                Property::ProbeBox(pb) => {
                    out.push_str(&format!(
                        "    <ProbeBox Name=\"{}\" Number=\"{}\" Type=\"{}\" Weight=\"{}\">\n",
                        pb.name, pb.number, pb.probe_type, pb.weight
                    ));
                    write_primitives(&mut out, &pb.primitives);
                    out.push_str("    </ProbeBox>\n");
                }
            }
        }
        out.push_str("  </Properties>\n");
        out.push_str("</ContinuousStructure>\n");
        out
    }

    fn write_primitives(out: &mut String, prims: &[Primitive]) {
        for prim in prims {
            match prim {
                Primitive::Box(b) => {
                    out.push_str(&format!("      <Box Priority=\"{}\">\n", b.priority));
                    out.push_str(&format!(
                        "        <P1 X=\"{}\" Y=\"{}\" Z=\"{}\" />\n",
                        b.p1[0], b.p1[1], b.p1[2]
                    ));
                    out.push_str(&format!(
                        "        <P2 X=\"{}\" Y=\"{}\" Z=\"{}\" />\n",
                        b.p2[0], b.p2[1], b.p2[2]
                    ));
                    out.push_str("      </Box>\n");
                }
                Primitive::Sphere(s) => {
                    out.push_str(&format!(
                        "      <Sphere Priority=\"{}\" Radius=\"{}\">\n",
                        s.priority, s.radius
                    ));
                    out.push_str(&format!(
                        "        <Center X=\"{}\" Y=\"{}\" Z=\"{}\" />\n",
                        s.center[0], s.center[1], s.center[2]
                    ));
                    out.push_str("      </Sphere>\n");
                }
                Primitive::Cylinder(c) => {
                    out.push_str(&format!(
                        "      <Cylinder Priority=\"{}\" Radius=\"{}\">\n",
                        c.priority, c.radius
                    ));
                    out.push_str(&format!(
                        "        <P1 X=\"{}\" Y=\"{}\" Z=\"{}\" />\n",
                        c.p1[0], c.p1[1], c.p1[2]
                    ));
                    out.push_str(&format!(
                        "        <P2 X=\"{}\" Y=\"{}\" Z=\"{}\" />\n",
                        c.p2[0], c.p2[1], c.p2[2]
                    ));
                    out.push_str("      </Cylinder>\n");
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_relative_eq;

    #[test]
    fn test_grid_lines_and_deltas() {
        let mut grid = CSRectGrid::new();
        grid.delta_unit = 1e-3; // mm
        grid.add_line(0, 0.0);
        grid.add_line(0, 10.0);
        grid.add_line(0, 25.0);

        assert_eq!(grid.get_qty_lines(0), 3);
        let deltas = grid.get_deltas(0);
        assert_eq!(deltas.len(), 2);
        assert_relative_eq!(deltas[0], 0.010); // 10mm = 0.010m
        assert_relative_eq!(deltas[1], 0.015); // 15mm = 0.015m

        let dual = grid.get_dual_lines(0);
        assert_eq!(dual.len(), 2);
        assert_relative_eq!(dual[0], 5.0);
        assert_relative_eq!(dual[1], 17.5);
    }

    #[test]
    fn test_xml_roundtrip() {
        let mut csx = ContinuousStructure::new();
        csx.grid.delta_unit = 1e-6; // um
        csx.grid.set_lines(0, vec![0.0, 100.0, 200.0]);
        csx.grid.set_lines(1, vec![-50.0, 0.0, 50.0]);
        csx.grid.set_lines(2, vec![0.0, 254.0]);

        let mut ro4350b = MaterialProperty::new("RO4350B");
        ro4350b.epsilon = [3.66, 3.66, 3.66];
        ro4350b.primitives.push(Primitive::Box(CSPrimBox::new(
            [0.0, -50.0, 0.0],
            [200.0, 50.0, 254.0],
            0,
        )));
        csx.add_property(Property::Material(ro4350b));

        let mut pec = MetalProperty::new("PEC");
        pec.primitives.push(Primitive::Box(CSPrimBox::new(
            [0.0, -10.0, 254.0],
            [200.0, 10.0, 254.0],
            999,
        )));
        csx.add_property(Property::Metal(pec));

        let xml_str = xml::to_csx_xml(&csx);
        let parsed = xml::parse_csx_xml(&xml_str).unwrap();

        assert_relative_eq!(parsed.grid.delta_unit, 1e-6);
        assert_eq!(parsed.grid.lines[0], vec![0.0, 100.0, 200.0]);
        assert_eq!(parsed.properties.len(), 2);

        match &parsed.properties[0] {
            Property::Material(m) => {
                assert_eq!(m.name, "RO4350B");
                assert_relative_eq!(m.epsilon[0], 3.66);
                assert_eq!(m.primitives.len(), 1);
            }
            _ => panic!("Expected MaterialProperty"),
        }
    }

    #[test]
    fn test_sphere_and_cylinder_primitives() {
        let sphere = CSPrimSphere::new([0.0, 0.0, 0.0], 5.0, 1);
        assert!(sphere.contains_point([0.0, 0.0, 4.9]));
        assert!(!sphere.contains_point([0.0, 0.0, 5.1]));

        let cyl = CSPrimCylinder::new([0.0, 0.0, 0.0], [0.0, 0.0, 10.0], 2.0, 1);
        assert!(cyl.contains_point([1.5, 0.0, 5.0]));
        assert!(!cyl.contains_point([2.5, 0.0, 5.0]));
        assert!(!cyl.contains_point([0.0, 0.0, 11.0]));

        let mut csx = ContinuousStructure::new();
        let mut mat = MaterialProperty::new("Dielectric");
        mat.primitives.push(Primitive::Sphere(sphere));
        mat.primitives.push(Primitive::Cylinder(cyl));
        csx.add_property(Property::Material(mat));

        let xml_str = xml::to_csx_xml(&csx);
        let parsed = xml::parse_csx_xml(&xml_str).unwrap();
        assert_eq!(parsed.properties.len(), 1);
        if let Property::Material(m) = &parsed.properties[0] {
            assert_eq!(m.primitives.len(), 2);
            match &m.primitives[0] {
                Primitive::Sphere(s) => assert_relative_eq!(s.radius, 5.0),
                _ => panic!("Expected Sphere"),
            }
            match &m.primitives[1] {
                Primitive::Cylinder(c) => assert_relative_eq!(c.radius, 2.0),
                _ => panic!("Expected Cylinder"),
            }
        }
    }
}

