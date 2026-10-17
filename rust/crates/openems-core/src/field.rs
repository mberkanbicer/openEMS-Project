//! 4D Grid Field array `ArrayNIJK<FDTD_FLOAT>` indexed by component `n` (0,1,2 = x,y,z)
//! and 3D spatial index `(i, j, k)`.
//!
//! Stores IEEE 754 single-precision `f32` field values (`volt`, `curr`) and coefficient matrices
//! (`vv`, `vi`, `ii`, `iv`), matching openEMS memory layout and cache alignment.

#[derive(Debug, Clone, PartialEq)]
pub struct ArrayNIJK {
    pub dims: [usize; 3], // numLines: [nx, ny, nz]
    pub data: Vec<f32>,   // 3 * nx * ny * nz elements
}

impl ArrayNIJK {
    pub fn new(dims: [usize; 3]) -> Self {
        let total = 3 * dims[0] * dims[1] * dims[2];
        Self {
            dims,
            data: vec![0.0; total],
        }
    }

    #[inline(always)]
    fn index(&self, n: usize, i: usize, j: usize, k: usize) -> usize {
        let [nx, ny, nz] = self.dims;
        // Component n followed by standard i, j, k stride
        n * (nx * ny * nz) + i * (ny * nz) + j * nz + k
    }

    #[inline(always)]
    pub fn get(&self, n: usize, i: usize, j: usize, k: usize) -> f32 {
        if n >= 3 || i >= self.dims[0] || j >= self.dims[1] || k >= self.dims[2] {
            0.0
        } else {
            self.data[self.index(n, i, j, k)]
        }
    }

    #[inline(always)]
    pub fn set(&mut self, n: usize, i: usize, j: usize, k: usize, val: f32) {
        if n < 3 && i < self.dims[0] && j < self.dims[1] && k < self.dims[2] {
            let idx = self.index(n, i, j, k);
            self.data[idx] = val;
        }
    }

    pub fn fill(&mut self, val: f32) {
        self.data.fill(val);
    }
}
