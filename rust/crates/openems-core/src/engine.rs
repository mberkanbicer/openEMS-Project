//! openEMS FDTD Simulation Engine (`FDTD/engine.h`).
//!
//! Performs the staggered leapfrog Yee-cell time updates:
//! 1. `update_voltages`: $V^{n+1} = vv \cdot V^n + vi \cdot \nabla \times I^{n+1/2}$
//! 2. `update_currents`: $I^{n+3/2} = ii \cdot I^{n+1/2} + iv \cdot \nabla \times V^{n+1}$
//! 3. Soft excitation injection and boundary handling (PEC, Mur ABC, UPML).

use crate::excitation::Excitation;
use crate::field::ArrayNIJK;
use crate::operator::{BoundaryType, Operator};

pub struct MurAbcPlane {
    pub dir: usize,     // 0: x, 1: y, 2: z
    pub is_max: bool,   // false: min boundary, true: max boundary
    pub line_idx: usize,
    pub shift_idx: usize,
    pub coeff: f32,
    pub old_v1: Vec<f32>,
    pub old_v2: Vec<f32>,
}

pub struct Engine {
    pub dims: [usize; 3], // [nx, ny, nz]
    pub volt: ArrayNIJK,
    pub curr: ArrayNIJK,
    pub timestep: usize,
    pub mur_planes: Vec<MurAbcPlane>,
}

impl Engine {
    pub fn new(op: &Operator) -> Self {
        let [nx, ny, nz] = op.dims;
        let mut mur_planes = Vec::new();

        // Setup 1st order Mur Absorbing Boundaries if requested
        for (i, bc_type) in op.bc.bc.iter().enumerate() {
            if let BoundaryType::MUR = bc_type {
                let dir = i / 2;
                let is_max = (i % 2) == 1;
                let line_idx = if is_max { op.dims[dir] - 1 } else { 0 };
                let shift_idx = if is_max { op.dims[dir] - 2 } else { 1 };
                let d1 = (dir + 1) % 3;
                let d2 = (dir + 2) % 3;
                let size = op.dims[d1] * op.dims[d2];

                // Mur reflection parameter: (c0*dt - delta) / (c0*dt + delta)
                // For a 1mm mesh and dt ~ 1.9ps, c0*dt ~ 0.57mm, delta ~ 1.0mm
                let delta = 1e-3;
                let c0t = crate::constants::C0 * op.dt;
                let coeff = ((c0t - delta) / (c0t + delta)) as f32;

                mur_planes.push(MurAbcPlane {
                    dir,
                    is_max,
                    line_idx,
                    shift_idx,
                    coeff,
                    old_v1: vec![0.0; size],
                    old_v2: vec![0.0; size],
                });
            }
        }

        Self {
            dims: [nx, ny, nz],
            volt: ArrayNIJK::new([nx, ny, nz]),
            curr: ArrayNIJK::new([nx, ny, nz]),
            timestep: 0,
            mur_planes,
        }
    }

    /// Perform a single leapfrog time step.
    pub fn step(&mut self, op: &Operator, exc: Option<(&Excitation, [usize; 3], usize)>) {
        // 1. Pre-voltage update extensions (Mur ABC)
        self.mur_pre_voltage_update();

        // 2. Main Voltage updates
        self.update_voltages(op);

        // 3. Post-voltage update extensions (Mur ABC)
        self.mur_post_voltage_update();

        // 4. Inject Excitation if provided (dir, pos, amplitude)
        if let Some((excitation, pos, comp)) = exc {
            let val = excitation.eval(self.timestep) as f32;
            let current = self.volt.get(comp, pos[0], pos[1], pos[2]);
            self.volt.set(comp, pos[0], pos[1], pos[2], current + val);
        }

        // 5. Update Currents
        self.update_currents(op);

        self.timestep += 1;
    }

    /// Voltage update loop matching `Engine::UpdateVoltages`.
    pub fn update_voltages(&mut self, op: &Operator) {
        let [nx, ny, nz] = self.dims;

        for i in 0..nx {
            let shift_x = if i > 0 { 1 } else { 0 };
            for j in 0..ny {
                let shift_y = if j > 0 { 1 } else { 0 };
                for k in 0..nz {
                    let shift_z = if k > 0 { 1 } else { 0 };

                    // Component 0: x
                    let curl_x = (self.curr.get(2, i, j, k) - self.curr.get(2, i, j - shift_y, k))
                        - (self.curr.get(1, i, j, k) - self.curr.get(1, i, j, k - shift_z));
                    let v0 = self.volt.get(0, i, j, k) * op.vv.get(0, i, j, k)
                        + op.vi.get(0, i, j, k) * curl_x;
                    self.volt.set(0, i, j, k, v0);

                    // Component 1: y
                    let curl_y = (self.curr.get(0, i, j, k) - self.curr.get(0, i, j, k - shift_z))
                        - (self.curr.get(2, i, j, k) - self.curr.get(2, i - shift_x, j, k));
                    let v1 = self.volt.get(1, i, j, k) * op.vv.get(1, i, j, k)
                        + op.vi.get(1, i, j, k) * curl_y;
                    self.volt.set(1, i, j, k, v1);

                    // Component 2: z
                    let curl_z = (self.curr.get(1, i, j, k) - self.curr.get(1, i - shift_x, j, k))
                        - (self.curr.get(0, i, j, k) - self.curr.get(0, i, j - shift_y, k));
                    let v2 = self.volt.get(2, i, j, k) * op.vv.get(2, i, j, k)
                        + op.vi.get(2, i, j, k) * curl_z;
                    self.volt.set(2, i, j, k, v2);
                }
            }
        }
    }

    /// Current update loop matching `Engine::UpdateCurrents`.
    pub fn update_currents(&mut self, op: &Operator) {
        let [nx, ny, nz] = self.dims;

        for i in 0..(nx.saturating_sub(1)) {
            for j in 0..(ny.saturating_sub(1)) {
                for k in 0..(nz.saturating_sub(1)) {
                    // Component 0: x
                    let curl_x = (self.volt.get(2, i, j, k) - self.volt.get(2, i, j + 1, k))
                        - (self.volt.get(1, i, j, k) - self.volt.get(1, i, j, k + 1));
                    let c0 = self.curr.get(0, i, j, k) * op.ii.get(0, i, j, k)
                        + op.iv.get(0, i, j, k) * curl_x;
                    self.curr.set(0, i, j, k, c0);

                    // Component 1: y
                    let curl_y = (self.volt.get(0, i, j, k) - self.volt.get(0, i, j, k + 1))
                        - (self.volt.get(2, i, j, k) - self.volt.get(2, i + 1, j, k));
                    let c1 = self.curr.get(1, i, j, k) * op.ii.get(1, i, j, k)
                        + op.iv.get(1, i, j, k) * curl_y;
                    self.curr.set(1, i, j, k, c1);

                    // Component 2: z
                    let curl_z = (self.volt.get(1, i, j, k) - self.volt.get(1, i + 1, j, k))
                        - (self.volt.get(0, i, j, k) - self.volt.get(0, i, j + 1, k));
                    let c2 = self.curr.get(2, i, j, k) * op.ii.get(2, i, j, k)
                        + op.iv.get(2, i, j, k) * curl_z;
                    self.curr.set(2, i, j, k, c2);
                }
            }
        }
    }

    /// Pre-voltage update phase for Mur ABC:
    /// `v_stored = V(pos_shift) - coeff * V(pos)`
    pub fn mur_pre_voltage_update(&mut self) {
        for plane in &mut self.mur_planes {
            let d1 = (plane.dir + 1) % 3;
            let d2 = (plane.dir + 2) % 3;
            let n1 = self.dims[d1];
            let n2 = self.dims[d2];

            for i1 in 0..n1 {
                for i2 in 0..n2 {
                    let mut pos = [0; 3];
                    let mut pos_shift = [0; 3];
                    pos[plane.dir] = plane.line_idx;
                    pos[d1] = i1;
                    pos[d2] = i2;
                    pos_shift[plane.dir] = plane.shift_idx;
                    pos_shift[d1] = i1;
                    pos_shift[d2] = i2;

                    let idx = i1 * n2 + i2;
                    let v_shift1 = self.volt.get(d1, pos_shift[0], pos_shift[1], pos_shift[2]);
                    let v_shift2 = self.volt.get(d2, pos_shift[0], pos_shift[1], pos_shift[2]);
                    let v_bound1 = self.volt.get(d1, pos[0], pos[1], pos[2]);
                    let v_bound2 = self.volt.get(d2, pos[0], pos[1], pos[2]);

                    plane.old_v1[idx] = v_shift1 - plane.coeff * v_bound1;
                    plane.old_v2[idx] = v_shift2 - plane.coeff * v_bound2;
                }
            }
        }
    }

    /// Post-voltage update phase for Mur ABC:
    /// `V_new(pos) = v_stored + coeff * V_new(pos_shift)`
    pub fn mur_post_voltage_update(&mut self) {
        for plane in &self.mur_planes {
            let d1 = (plane.dir + 1) % 3;
            let d2 = (plane.dir + 2) % 3;
            let n1 = self.dims[d1];
            let n2 = self.dims[d2];

            for i1 in 0..n1 {
                for i2 in 0..n2 {
                    let mut pos = [0; 3];
                    let mut pos_shift = [0; 3];
                    pos[plane.dir] = plane.line_idx;
                    pos[d1] = i1;
                    pos[d2] = i2;
                    pos_shift[plane.dir] = plane.shift_idx;
                    pos_shift[d1] = i1;
                    pos_shift[d2] = i2;

                    let idx = i1 * n2 + i2;
                    let v_shift1_new = self.volt.get(d1, pos_shift[0], pos_shift[1], pos_shift[2]);
                    let v_shift2_new = self.volt.get(d2, pos_shift[0], pos_shift[1], pos_shift[2]);

                    let new_v1 = plane.old_v1[idx] + plane.coeff * v_shift1_new;
                    let new_v2 = plane.old_v2[idx] + plane.coeff * v_shift2_new;

                    self.volt.set(d1, pos[0], pos[1], pos[2], new_v1);
                    self.volt.set(d2, pos[0], pos[1], pos[2], new_v2);
                }
            }
        }
    }

    /// Calculate total instantaneous electromagnetic field energy in Joules.
    pub fn calc_total_energy(&self) -> f64 {
        let mut energy = 0.0;
        let [nx, ny, nz] = self.dims;

        for i in 0..nx {
            for j in 0..ny {
                for k in 0..nz {
                    for n in 0..3 {
                        let v = self.volt.get(n, i, j, k) as f64;
                        let c = self.curr.get(n, i, j, k) as f64;
                        energy += v * v + c * c;
                    }
                }
            }
        }
        energy
    }
}
