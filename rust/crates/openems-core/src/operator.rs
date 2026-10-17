//! openEMS FDTD Operator (`FDTD/operator.h`).
//!
//! Pre-computes equivalent-circuit (EC) update coefficients:
//! - `vv = (1 - dt*G / (2*C)) / (1 + dt*G / (2*C))`
//! - `vi = (dt / C) / (1 + dt*G / (2*C))`
//! - `ii = (1 - dt*R / (2*L)) / (1 + dt*R / (2*L))`
//! - `iv = (dt / L) / (1 + dt*R / (2*L))`
//! and handles CFL Courant stability timestep calculation and PEC/PMC boundary conditions.

use crate::constants::{C0, EPS0, MUE0};
use crate::field::ArrayNIJK;
use csxcad_core::{CSRectGrid, ContinuousStructure, Property};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BoundaryType {
    PEC,
    PMC,
    MUR,
    PML(usize), // UPML with layer thickness
}

#[derive(Debug, Clone)]
pub struct BoundaryConditions {
    // 0: xmin, 1: xmax, 2: ymin, 3: ymax, 4: zmin, 5: zmax
    pub bc: [BoundaryType; 6],
}

impl Default for BoundaryConditions {
    fn default() -> Self {
        Self {
            bc: [
                BoundaryType::PEC,
                BoundaryType::PEC,
                BoundaryType::PEC,
                BoundaryType::PEC,
                BoundaryType::PEC,
                BoundaryType::PEC,
            ],
        }
    }
}

pub struct Operator {
    pub dims: [usize; 3], // [nx, ny, nz]
    pub dt: f64,          // Timestep (seconds)
    pub vv: ArrayNIJK,
    pub vi: ArrayNIJK,
    pub ii: ArrayNIJK,
    pub iv: ArrayNIJK,
    pub bc: BoundaryConditions,
}

impl Operator {
    pub fn new(csx: &ContinuousStructure, bc: BoundaryConditions) -> Self {
        let nx = csx.grid.get_qty_lines(0);
        let ny = csx.grid.get_qty_lines(1);
        let nz = csx.grid.get_qty_lines(2);
        let dims = [nx, ny, nz];

        let dt = Self::calc_cfl_timestep(&csx.grid);

        let mut op = Self {
            dims,
            dt,
            vv: ArrayNIJK::new(dims),
            vi: ArrayNIJK::new(dims),
            ii: ArrayNIJK::new(dims),
            iv: ArrayNIJK::new(dims),
            bc,
        };

        op.calc_ec_coefficients(csx);
        op.apply_boundaries();
        op
    }

    /// Calculate CFL Courant-Friedrichs-Lewy stability limit:
    /// $\Delta t \le \frac{0.99}{c_0 \sqrt{1/\Delta x^2 + 1/\Delta y^2 + 1/\Delta z^2}}$
    pub fn calc_cfl_timestep(grid: &CSRectGrid) -> f64 {
        let deltas_x = grid.get_deltas(0);
        let deltas_y = grid.get_deltas(1);
        let deltas_z = grid.get_deltas(2);

        let min_dx = deltas_x.iter().copied().fold(f64::INFINITY, f64::min);
        let min_dy = deltas_y.iter().copied().fold(f64::INFINITY, f64::min);
        let min_dz = deltas_z.iter().copied().fold(f64::INFINITY, f64::min);

        let inv_sum = 1.0 / (min_dx * min_dx) + 1.0 / (min_dy * min_dy) + 1.0 / (min_dz * min_dz);
        0.99 / (C0 * inv_sum.sqrt())
    }

    fn calc_ec_coefficients(&mut self, csx: &ContinuousStructure) {
        let [nx, ny, nz] = self.dims;
        let dt = self.dt;

        let deltas_x = csx.grid.get_deltas(0);
        let deltas_y = csx.grid.get_deltas(1);
        let deltas_z = csx.grid.get_deltas(2);

        for i in 0..nx {
            for j in 0..ny {
                for k in 0..nz {
                    let dx = if i < deltas_x.len() { deltas_x[i] } else { 1.0 };
                    let dy = if j < deltas_y.len() { deltas_y[j] } else { 1.0 };
                    let dz = if k < deltas_z.len() { deltas_z[k] } else { 1.0 };

                    // Determine material at this cell
                    let (eps_r, kappa) = self.sample_material(csx, i, j, k);

                    // Direction 0: x
                    let area_x = dy * dz;
                    let len_x = dx;
                    let c_x = EPS0 * eps_r[0] * area_x / len_x;
                    let g_x = kappa[0] * area_x / len_x;
                    let l_x = MUE0 * area_x / len_x;
                    let r_x = 0.0;

                    self.set_cell_ec(0, i, j, k, dt, c_x, g_x, l_x, r_x);

                    // Direction 1: y
                    let area_y = dx * dz;
                    let len_y = dy;
                    let c_y = EPS0 * eps_r[1] * area_y / len_y;
                    let g_y = kappa[1] * area_y / len_y;
                    let l_y = MUE0 * area_y / len_y;
                    let r_y = 0.0;

                    self.set_cell_ec(1, i, j, k, dt, c_y, g_y, l_y, r_y);

                    // Direction 2: z
                    let area_z = dx * dy;
                    let len_z = dz;
                    let c_z = EPS0 * eps_r[2] * area_z / len_z;
                    let g_z = kappa[2] * area_z / len_z;
                    let l_z = MUE0 * area_z / len_z;
                    let r_z = 0.0;

                    self.set_cell_ec(2, i, j, k, dt, c_z, g_z, l_z, r_z);
                }
            }
        }
    }

    fn sample_material(&self, csx: &ContinuousStructure, i: usize, j: usize, k: usize) -> ([f64; 3], [f64; 3]) {
        let x = csx.grid.lines[0].get(i).copied().unwrap_or(0.0);
        let y = csx.grid.lines[1].get(j).copied().unwrap_or(0.0);
        let z = csx.grid.lines[2].get(k).copied().unwrap_or(0.0);
        let pt = [x, y, z];

        for prop in &csx.properties {
            match prop {
                Property::Material(m) => {
                    for prim in &m.primitives {
                        match prim {
                            csxcad_core::Primitive::Box(b) => {
                                if b.contains_point(pt) {
                                    return (m.epsilon, m.kappa);
                                }
                            }
                            csxcad_core::Primitive::Sphere(s) => {
                                if s.contains_point(pt) {
                                    return (m.epsilon, m.kappa);
                                }
                            }
                            csxcad_core::Primitive::Cylinder(c) => {
                                if c.contains_point(pt) {
                                    return (m.epsilon, m.kappa);
                                }
                            }
                        }
                    }
                }
                Property::Metal(m) => {
                    for prim in &m.primitives {
                        match prim {
                            csxcad_core::Primitive::Box(b) => {
                                if b.contains_point(pt) {
                                    return ([1.0, 1.0, 1.0], [1e8, 1e8, 1e8]); // PEC modeled as high conductivity
                                }
                            }
                            _ => {}
                        }
                    }
                }
                _ => {}
            }
        }
        ([1.0, 1.0, 1.0], [0.0, 0.0, 0.0])
    }

    fn set_cell_ec(
        &mut self,
        n: usize,
        i: usize,
        j: usize,
        k: usize,
        dt: f64,
        c: f64,
        g: f64,
        l: f64,
        r: f64,
    ) {
        if c > 0.0 {
            let denom = 1.0 + dt * g / (2.0 * c);
            self.vv.set(n, i, j, k, ((1.0 - dt * g / (2.0 * c)) / denom) as f32);
            self.vi.set(n, i, j, k, ((dt / c) / denom) as f32);
        } else {
            self.vv.set(n, i, j, k, 0.0);
            self.vi.set(n, i, j, k, 0.0);
        }

        if l > 0.0 {
            let denom = 1.0 + dt * r / (2.0 * l);
            self.ii.set(n, i, j, k, ((1.0 - dt * r / (2.0 * l)) / denom) as f32);
            self.iv.set(n, i, j, k, ((dt / l) / denom) as f32);
        } else {
            self.ii.set(n, i, j, k, 0.0);
            self.iv.set(n, i, j, k, 0.0);
        }
    }

    fn apply_boundaries(&mut self) {
        let [nx, ny, nz] = self.dims;

        // PMC boundary conditions: tangential H = 0 at the boundary face.
        // Currents (H) tangential to the face live in the two components in the
        // face plane; zero their update coefficients on the boundary line.
        // xmin / xmax: tangential components are y (1) and z (2)
        if let BoundaryType::PMC = self.bc.bc[0] {
            for n in [1usize, 2] {
                for j in 0..ny {
                    for k in 0..nz {
                        self.ii.set(n, 0, j, k, 0.0);
                        self.iv.set(n, 0, j, k, 0.0);
                    }
                }
            }
        }
        if let BoundaryType::PMC = self.bc.bc[1] {
            for n in [1usize, 2] {
                for j in 0..ny {
                    for k in 0..nz {
                        self.ii.set(n, nx - 1, j, k, 0.0);
                        self.iv.set(n, nx - 1, j, k, 0.0);
                    }
                }
            }
        }
        // ymin / ymax: tangential components are x (0) and z (2)
        if let BoundaryType::PMC = self.bc.bc[2] {
            for n in [0usize, 2] {
                for i in 0..nx {
                    for k in 0..nz {
                        self.ii.set(n, i, 0, k, 0.0);
                        self.iv.set(n, i, 0, k, 0.0);
                    }
                }
            }
        }
        if let BoundaryType::PMC = self.bc.bc[3] {
            for n in [0usize, 2] {
                for i in 0..nx {
                    for k in 0..nz {
                        self.ii.set(n, i, ny - 1, k, 0.0);
                        self.iv.set(n, i, ny - 1, k, 0.0);
                    }
                }
            }
        }
        // zmin / zmax: tangential components are x (0) and y (1)
        if let BoundaryType::PMC = self.bc.bc[4] {
            for n in [0usize, 1] {
                for i in 0..nx {
                    for j in 0..ny {
                        self.ii.set(n, i, j, 0, 0.0);
                        self.iv.set(n, i, j, 0, 0.0);
                    }
                }
            }
        }
        if let BoundaryType::PMC = self.bc.bc[5] {
            for n in [0usize, 1] {
                for i in 0..nx {
                    for j in 0..ny {
                        self.ii.set(n, i, j, nz - 1, 0.0);
                        self.iv.set(n, i, j, nz - 1, 0.0);
                    }
                }
            }
        }

        // Apply PEC boundary conditions (tangential E = 0, vv = 0, vi = 0)
        // xmin
        if let BoundaryType::PEC = self.bc.bc[0] {
            for j in 0..ny {
                for k in 0..nz {
                    self.vv.set(1, 0, j, k, 0.0);
                    self.vi.set(1, 0, j, k, 0.0);
                    self.vv.set(2, 0, j, k, 0.0);
                    self.vi.set(2, 0, j, k, 0.0);
                }
            }
        }
        // xmax
        if let BoundaryType::PEC = self.bc.bc[1] {
            for j in 0..ny {
                for k in 0..nz {
                    self.vv.set(1, nx - 1, j, k, 0.0);
                    self.vi.set(1, nx - 1, j, k, 0.0);
                    self.vv.set(2, nx - 1, j, k, 0.0);
                    self.vi.set(2, nx - 1, j, k, 0.0);
                }
            }
        }
        // ymin
        if let BoundaryType::PEC = self.bc.bc[2] {
            for i in 0..nx {
                for k in 0..nz {
                    self.vv.set(0, i, 0, k, 0.0);
                    self.vi.set(0, i, 0, k, 0.0);
                    self.vv.set(2, i, 0, k, 0.0);
                    self.vi.set(2, i, 0, k, 0.0);
                }
            }
        }
        // ymax
        if let BoundaryType::PEC = self.bc.bc[3] {
            for i in 0..nx {
                for k in 0..nz {
                    self.vv.set(0, i, ny - 1, k, 0.0);
                    self.vi.set(0, i, ny - 1, k, 0.0);
                    self.vv.set(2, i, ny - 1, k, 0.0);
                    self.vi.set(2, i, ny - 1, k, 0.0);
                }
            }
        }
        // zmin
        if let BoundaryType::PEC = self.bc.bc[4] {
            for i in 0..nx {
                for j in 0..ny {
                    self.vv.set(0, i, j, 0, 0.0);
                    self.vi.set(0, i, j, 0, 0.0);
                    self.vv.set(1, i, j, 0, 0.0);
                    self.vi.set(1, i, j, 0, 0.0);
                }
            }
        }
        // zmax
        if let BoundaryType::PEC = self.bc.bc[5] {
            for i in 0..nx {
                for j in 0..ny {
                    self.vv.set(0, i, j, nz - 1, 0.0);
                    self.vi.set(0, i, j, nz - 1, 0.0);
                    self.vv.set(1, i, j, nz - 1, 0.0);
                    self.vi.set(1, i, j, nz - 1, 0.0);
                }
            }
        }
    }
}
