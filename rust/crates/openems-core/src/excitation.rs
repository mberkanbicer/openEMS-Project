//! FDTD Excitation source waveforms matching openEMS `excitation.h`.

use crate::constants::PI;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExcitationType {
    Gaussian = 0,
    Sinusoidal = 1,
    Dirac = 2,
    Step = 3,
}

#[derive(Debug, Clone)]
pub struct Excitation {
    pub excit_type: ExcitationType,
    pub f0: f64,    // Center frequency
    pub fc: f64,    // Cutoff frequency (f_max - f0)
    pub dt: f64,    // Timestep
    pub delay: f64, // Time delay in seconds
}

impl Excitation {
    pub fn new_gaussian(f0: f64, fc: f64) -> Self {
        let tau = 1.0 / (2.0 * PI * fc.max(1e-12));
        let delay = 4.0 * tau;
        Self {
            excit_type: ExcitationType::Gaussian,
            f0,
            fc,
            dt: 0.0,
            delay,
        }
    }

    pub fn set_timestep(&mut self, dt: f64) {
        self.dt = dt;
    }

    /// Evaluates signal value at time step `ts` (time $t = ts \cdot \Delta t$).
    pub fn eval(&self, ts: usize) -> f64 {
        let t = (ts as f64) * self.dt;
        match self.excit_type {
            ExcitationType::Gaussian => {
                let tau = 1.0 / (2.0 * PI * self.fc.max(1e-12));
                let arg = (t - self.delay) / tau;
                let envelope = (-arg * arg).exp();
                if self.f0 > 0.0 {
                    envelope * (2.0 * PI * self.f0 * (t - self.delay)).sin()
                } else {
                    envelope
                }
            }
            ExcitationType::Sinusoidal => {
                if t >= self.delay {
                    (2.0 * PI * self.f0 * (t - self.delay)).sin()
                } else {
                    0.0
                }
            }
            ExcitationType::Dirac => {
                if ts == 0 { 1.0 } else { 0.0 }
            }
            ExcitationType::Step => {
                if t >= self.delay { 1.0 } else { 0.0 }
            }
        }
    }

    pub fn nyquist_steps(&self) -> usize {
        let f_max = self.f0 + self.fc;
        if f_max > 0.0 && self.dt > 0.0 {
            (1.0 / (2.0 * f_max * self.dt)).floor() as usize
        } else {
            10
        }
    }
}
