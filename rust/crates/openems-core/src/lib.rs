//! `openems-core`: Native Rust implementation of the openEMS FDTD simulation engine.
//!
//! Provides the core electromagnetic calculation components:
//! - Physical constants (`constants`)
//! - Field and coefficient storage (`ArrayNIJK`)
//! - Excitation signal modeling (`Excitation`)
//! - Equivalent circuit FDTD Operator (`Operator`)
//! - Leapfrog staggered time-stepping Engine (`Engine`) with Mur ABC & PEC boundaries.

pub mod constants;
pub mod excitation;
pub mod field;
pub mod operator;
pub mod engine;
pub mod processing;

pub use constants::*;
pub use excitation::*;
pub use field::*;
pub use operator::*;
pub use engine::*;
pub use processing::*;

#[cfg(test)]
mod tests {
    use super::*;
    use csxcad_core::{CSRectGrid, ContinuousStructure};

    #[test]
    fn test_cfl_timestep() {
        let mut grid = CSRectGrid::new();
        grid.delta_unit = 1e-3; // 1 mm
        grid.add_line(0, 0.0);
        grid.add_line(0, 1.0);
        grid.add_line(1, 0.0);
        grid.add_line(1, 1.0);
        grid.add_line(2, 0.0);
        grid.add_line(2, 1.0);

        let dt = Operator::calc_cfl_timestep(&grid);
        // dx = dy = dz = 1e-3 m
        // dt_cfl = 0.99 / (c0 * sqrt(3) / 1e-3) ~ 1.905e-12 s
        assert!(dt > 1.8e-12 && dt < 2.0e-12);
    }

    #[test]
    fn test_fdtd_wave_propagation() {
        // Construct a small 3D resonant grid: 10x10x10 cells
        let mut csx = ContinuousStructure::new();
        csx.grid.delta_unit = 1e-3; // mm
        for i in 0..=10 {
            csx.grid.add_line(0, i as f64);
            csx.grid.add_line(1, i as f64);
            csx.grid.add_line(2, i as f64);
        }

        let bc = BoundaryConditions::default(); // All PEC boundaries
        let op = Operator::new(&csx, bc);
        let mut eng = Engine::new(&op);

        // Center excitation: Gaussian pulse on z-directed voltage
        let mut exc = Excitation::new_gaussian(10e9, 5e9);
        exc.set_timestep(op.dt);

        let excite_pos = [5, 5, 5];
        let excite_comp = 2; // Ez

        // Step for 50 timesteps
        for _ in 0..50 {
            eng.step(&op, Some((&exc, excite_pos, excite_comp)));
        }

        // Energy must be positive and wave must propagate from source point
        let energy = eng.calc_total_energy();
        assert!(energy > 0.0);

        // Verify field disturbance reached neighbor cell
        let vz_neighbor = eng.volt.get(2, 5, 5, 6);
        assert!(vz_neighbor.abs() > 1e-8);
    }

    #[test]
    fn test_pmc_boundary() {
        // PMC: tangential H must stay zero at the boundary faces
        let mut csx = ContinuousStructure::new();
        csx.grid.delta_unit = 1e-3;
        for i in 0..=6 {
            csx.grid.add_line(0, i as f64);
            csx.grid.add_line(1, i as f64);
            csx.grid.add_line(2, i as f64);
        }

        let mut bc = BoundaryConditions::default();
        for b in &mut bc.bc {
            *b = BoundaryType::PMC;
        }

        let op = Operator::new(&csx, bc);

        // xmin/xmax: currents y (1) and z (2) frozen on i = 0 and i = nx-1
        for i in [0usize, op.dims[0] - 1] {
            for j in 0..op.dims[1] {
                for k in 0..op.dims[2] {
                    for n in [1usize, 2] {
                        assert_eq!(op.ii.get(n, i, j, k), 0.0);
                        assert_eq!(op.iv.get(n, i, j, k), 0.0);
                    }
                    // normal component untouched (interior of the other faces;
                    // at face edges the y/z PMC faces legitimately freeze x too)
                    let j0 = op.dims[1] / 2;
                    let k0 = op.dims[2] / 2;
                    assert!(op.iv.get(0, i, j0, k0) > 0.0);
                }
            }
        }

        // Evolve with a source: tangential currents at PMC faces stay exactly 0
        let mut eng = Engine::new(&op);
        let mut exc = Excitation::new_gaussian(20e9, 10e9);
        exc.set_timestep(op.dt);
        for _ in 0..50 {
            eng.step(&op, Some((&exc, [3, 3, 3], 2)));
        }
        for j in 0..op.dims[1] {
            for k in 0..op.dims[2] {
                for n in [1usize, 2] {
                    assert_eq!(eng.curr.get(n, 0, j, k), 0.0);
                    assert_eq!(eng.curr.get(n, op.dims[0] - 1, j, k), 0.0);
                }
            }
        }
    }

    #[test]
    fn test_mur_absorbing_boundary() {
        // Construct 3D grid with MUR boundaries on all 6 faces
        let mut csx = ContinuousStructure::new();
        csx.grid.delta_unit = 1e-3;
        for i in 0..=12 {
            csx.grid.add_line(0, i as f64);
            csx.grid.add_line(1, i as f64);
            csx.grid.add_line(2, i as f64);
        }

        let mut bc = BoundaryConditions::default();
        for b in &mut bc.bc {
            *b = BoundaryType::MUR;
        }

        let op = Operator::new(&csx, bc);
        let mut eng = Engine::new(&op);

        // 20 GHz carrier (lambda = 15 mm ~ box size), 10 GHz cutoff:
        // pulse delay ~4 tau = 63.7 ps (~33 steps), duration ~8 tau (~67 steps)
        let mut exc = Excitation::new_gaussian(20e9, 10e9);
        exc.set_timestep(op.dt);

        let excite_pos = [6, 6, 6];
        let excite_comp = 2; // Ez

        // Inject the full Gaussian pulse
        for _ in 0..150 {
            eng.step(&op, Some((&exc, excite_pos, excite_comp)));
        }

        let energy_after_excite = eng.calc_total_energy();
        assert!(energy_after_excite > 0.0);

        // Run without excitation: waves cross the 13 mm box in ~43 ps (~23 steps),
        // first-order Mur absorbs at each bounce; energy must decay significantly.
        for _ in 0..450 {
            eng.step(&op, None);
        }

        let energy_at_end = eng.calc_total_energy();
        assert!(
            energy_at_end < 0.01 * energy_after_excite,
            "Mur ABC failed to absorb: after_excite={:e}, end={:e}",
            energy_after_excite,
            energy_at_end
        );
    }
}

