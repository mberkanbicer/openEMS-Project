#![no_main]

use libfuzzer_sys::fuzz_target;

// Parse arbitrary UTF-8 as an fparser expression, optimize it and evaluate it
// with three variables. The parser's own recursion bound and error returns are
// part of what is exercised; any panic, hang or memory error is a finding.
fuzz_target!(|data: &[u8]| {
    if data.len() > 4096 {
        return;
    }
    let Ok(text) = std::str::from_utf8(data) else {
        return;
    };

    let mut parser = fparser::Parser::new();
    if parser.parse(text, "x,y,z", false).is_ok() {
        parser.optimize();
        let _ = parser.eval(&[1.0, 2.0, 3.0]);
        let _ = parser.eval(&[0.0, -0.0, 1.0e300]);
    }

    let mut deduce = fparser::Parser::new();
    let _ = deduce.parse_and_deduce_variables(text, true);
});
