//! FDTD Processing: field probes (`Common/processfieldprobe.cpp`,
//! `Common/processvoltage.cpp`) and time-to-frequency DFT
//! (`matlab/DFT_time2freq.m` semantics).
//!
//! - `TimeDomainProbe`: samples one field component at one grid point every step.
//! - `FreqDomainProbe`: running discrete Fourier transform (DFT) of the same
//!   samples at a set of user frequencies, matching openEMS's time-domain DFT
//!   accumulation over the recorded interval.

use crate::field::ArrayNIJK;

/// Complex value for DFT accumulators.
#[derive(Debug, Clone, Copy, Default, PartialEq)]
pub struct Complex {
    pub re: f64,
    pub im: f64,
}

impl Complex {
    pub fn norm(&self) -> f64 {
        self.re * self.re + self.im * self.im
    }
    pub fn magnitude(&self) -> f64 {
        self.norm().sqrt()
    }
}

/// Time-domain field probe at a fixed grid position and component.
#[derive(Debug, Clone)]
pub struct TimeDomainProbe {
    pub comp: usize,
    pub pos: [usize; 3],
    /// Sampled values, one per recorded step.
    pub values: Vec<f64>,
}

impl TimeDomainProbe {
    pub fn new(comp: usize, pos: [usize; 3]) -> Self {
        Self {
            comp,
            pos,
            values: Vec::new(),
        }
    }

    /// Record one sample from the voltage (electric, `true`) or current
    /// (magnetic, `false`) field array.
    pub fn record(&mut self, field: &ArrayNIJK) {
        let v = field.get(self.comp, self.pos[0], self.pos[1], self.pos[2]) as f64;
        self.values.push(v);
    }
}

/// Frequency-domain probe: running DFT of a time-domain probe's samples.
#[derive(Debug, Clone)]
pub struct FreqDomainProbe {
    pub freqs: Vec<f64>,
    dt: f64,
    n: usize,
    pub dft: Vec<Complex>,
}

impl FreqDomainProbe {
    /// `dt` must be the simulation timestep; samples are consumed step by step.
    pub fn new(freqs: Vec<f64>, dt: f64) -> Self {
        let k = freqs.len();
        Self {
            freqs,
            dt,
            n: 0,
            dft: vec![Complex::default(); k],
        }
    }

    /// Accumulate one sample taken at time step `n` (call with increasing `n`).
    pub fn push(&mut self, sample: f64) {
        let t = (self.n as f64) * self.dt;
        for (f, acc) in self.freqs.iter().zip(self.dft.iter_mut()) {
            let arg = -2.0 * std::f64::consts::PI * f * t;
            acc.re += sample * arg.cos();
            acc.im += sample * arg.sin();
        }
        self.n += 1;
    }

    /// Complex DFT value at frequency index `idx` (not normalized).
    pub fn get(&self, idx: usize) -> Complex {
        self.dft[idx]
    }

    pub fn magnitude(&self, idx: usize) -> f64 {
        self.dft[idx].magnitude()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_td_probe_records() {
        let dims = [4, 4, 4];
        let mut volt = ArrayNIJK::new(dims);
        volt.set(2, 2, 2, 2, 0.5);
        let mut p = TimeDomainProbe::new(2, [2, 2, 2]);
        p.record(&volt);
        p.record(&volt);
        assert_eq!(p.values, vec![0.5, 0.5]);
    }

    #[test]
    fn test_freq_probe_dft_of_sinusoid() {
        // Sample 10 GHz sinusoid for 32 periods; DFT peak must be at 10 GHz.
        let f_sig = 10e9;
        let dt = 1e-12; // well above Nyquist for 10 GHz? f_nyq = 500 GHz
        let periods = 32.0;
        let t_total = periods / f_sig;
        let n_steps = (t_total / dt) as usize;

        let mut p = FreqDomainProbe::new(vec![5e9, 10e9, 15e9], dt);
        for n in 0..n_steps {
            let t = n as f64 * dt;
            p.push((2.0 * std::f64::consts::PI * f_sig * t).sin());
        }

        let m10 = p.magnitude(1);
        assert!(m10 > 0.0);
        // Main peak far above off-frequency bins (leakage suppressed by
        // integer number of periods).
        assert!(
            m10 > 100.0 * p.magnitude(0),
            "10GHz mag {:e} vs 5GHz {:e}",
            m10,
            p.magnitude(0)
        );
        assert!(
            m10 > 100.0 * p.magnitude(2),
            "10GHz mag {:e} vs 15GHz {:e}",
            m10,
            p.magnitude(2)
        );
        // Amplitude accuracy for a full-period rectangular DFT: |X| = N/2
        let expect = 0.5 * n_steps as f64;
        let rel = (m10 - expect) / expect;
        assert!(rel.abs() < 1e-9, "amplitude error {} at 10 GHz", rel);
    }
}
